# Orquestación Claude + DeepSeek — B1

Regla permanente 1: Claude diseñó y escribió los briefs, DeepSeek escribió todo el código y todas las pruebas, y Claude
auditó, aplicó tal cual y certificó. Claude no escribió código de producto ni pruebas.

| Llamada | Tarea | Modelo | Tokens (entrada/salida) | Coste | Auditoría |
|---|---|---|---|---|---|
| 1 | F02a producto (`documents/api.py`) | deepseek-v4-flash | 2009/474 | $0,000396 | AUDIT_PASS; aplicado tal cual |
| 2 | F02b prueba, intento | deepseek-v4-pro | 4650/7140 | $0,008124 | AUDIT_REJECT |
| 3 | F02b corrección 1 | deepseek-v4-pro | 13486/6617 | $0,011513 | AUDIT_REJECT (medido: 5/9, ruff 1) |
| 4 | F02b corrección 2 (último reintento) | deepseek-v4-pro | 8027/6287 | $0,008851 | aplicado; 9/9 ×2 motores; una aserción de B09 perdida |
| 5 | F02c (división de F02b): aserción de orden de B09 | deepseek-v4-flash | 918/358 | $0,000211 | AUDIT_PASS; aplicado tal cual |

Total: 5 llamadas, 29 090/20 876 tokens, **$0,029095**. Reintentos: 2 (F02b, máximo alcanzado). Rechazos: 2. Aceptados: 3.
Reclasificación: tras agotar los dos reintentos de F02b, la única desviación restante (se borraron las dos copias de
`assert idx_idempotencia < idx_if_guard`, y el brief pedía conservar una) se separó como subtarea F02c para
deepseek-v4-flash. No hubo parche manual de Claude.

## Motivos de rechazo

- **Intento (R01–R12):**
  - imports de módulos inexistentes (`app.core.initialize`, `app.core.setup`, `app.core.storage`, `app.core.deps`) y
    `Session` tomada de otro módulo;
  - código de error leído en `["error"]["code"]`, cuando la API lo pone en la raíz;
  - el GET de versiones tratado como `{"items"}`, cuando devuelve una lista;
  - `DELETE` crudo de tablas y raíz de almacenamiento fija;
  - eventos espurios al montar;
  - ventana de medida que incluía el login y el alta del documento;
  - «último commit» buscado en todo el rango;
  - B09 tomando la última aparición de `if idempotency_key` y de `db.commit()`;
  - avisos de ruff.

  **Causa parcial imputable a Claude:** el brief no fijaba el bloque de imports reales.
- **Corrección 1** (medida en un fichero temporal, ya borrado): SQLite y PostgreSQL 5/9, ruff F401 (`text`).
  - B05 y B06 daban 500 en vez de 422 porque el analizador controlado esperaba `soltar` y nadie lo liberaba. Es un
    defecto de la prueba, no del producto: la traza acaba en `assert self.soltar.wait(timeout=60)`.
  - B03 tomaba el `begin` posterior al commit.
  - B09 seguía tomando la última aparición.

## Egress

Cada llamada: EGRESS_CHECK_COMPLETE_BEFORE_CALL = 1, LOCAL_PATHS_SANITIZED = 1, SECRET_EXPOSURE = 0.
ENV_FILES=0 SECRETS=0 PROD_URLS=0 TOKENS=0 PRIVATE_KEYS=0 REAL_PII=0 REAL_PAYROLL=0 BANK_DATA=0.

- Antes de cada envío se buscaron en los contenidos el nombre de usuario, `/home`, el puerto y la URL de PostgreSQL de
  QA, y contraseñas.
- La única coincidencia fue la contraseña sintética de fixture, ya versionada en las pruebas.
- Las salidas de pytest enviadas en las correcciones se sanearon: la ruta de la prueba se sustituyó por `<prueba>` y no
  salió ninguna ruta local.
