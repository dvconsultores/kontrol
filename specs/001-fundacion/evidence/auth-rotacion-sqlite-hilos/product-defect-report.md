# Informe para la dueña · `AUTH-ROTACION-SQLITE-HILOS — BLOCKED BY PRODUCT DECISION`

## La carrera exacta

Dos `POST /auth/refresh` con la misma cookie. En cada uno, `rotate_session` hace:

```
SELECT sessions.* WHERE id = :sid [FOR UPDATE]      -- SQLite ignora FOR UPDATE
-- comprueba revoked_at IS NULL y el hash
UPDATE sessions SET revoked_at = now WHERE id = :sid
INSERT INTO sessions (…nueva…)
UPDATE sessions SET refresh_token_hash = … WHERE id = :nueva
COMMIT                                              -- y después el evento de auditoría + COMMIT
```

Interleaving I1 (T1 lee, T2 lee, T1 escribe y confirma, T2 escribe y confirma): sobre **PostgreSQL** el `FOR UPDATE` de
T2 espera al `COMMIT` de T1, relee `revoked_at` ya puesto y responde **401 `SESSION_REVOKED`** (20/20). Sobre **SQLite** no
hay bloqueo de fila ni de lectura: T2 escribe sobre una lectura obsoleta, SQLite solo serializa las dos escrituras por el
`busy_timeout` del driver, **las dos confirman** (5/5 controladas, 18/20 naturales) y queda una sesión viva huérfana: el
síntoma de REM-AUTH-ROUTE-CRAWL-001 (484 sesiones vivas) reaparece, limitado a SQLite.

## Impacto

| Entorno | Exposición |
|---|---|
| Producción (PostgreSQL, P21) | **ninguna**: el bloqueo de fila funciona; la remediación de 2026-08-30 sigue vigente |
| Despliegue sobre SQLite | doble rotación posible + sesiones huérfanas; no hay despliegue así |
| Evidencia / suite | la prueba de concurrencia en SQLite es intermitente (15/20 falla) y, aun con el arnés corregido, pasaría por sincronización y no por garantía; el comentario del servicio afirma una serialización que no existe |

## Opciones (ninguna implementada; se presentan para decidir)

| Opción | Qué | Producto | Migración | Motores | Pruebas | Valoración |
|---|---|---|---|---|---|---|
| **A · UPDATE condicional (CAS) + rowcount** | en `rotate_session`, revocar con `UPDATE sessions SET revoked_at = :now WHERE id = :sid AND revoked_at IS NULL` y exigir `rowcount == 1`; si 0 → 401 `SESSION_REVOKED`. Se conserva `with_for_update()` | sí, ~6 líneas en un servicio de seguridad (CLAUDE_ONLY) | no | garantía **independiente del motor**: SQLite serializa las escrituras y la segunda actualiza 0 filas | la prueba objetivo sin cambios + una prueba con I1 forzada sobre `motor_para_hilos` (determinista) + PostgreSQL ×20 | **Recomendada**: refuerza (no relaja) la rotación, cierra la ventana también donde no hay `FOR UPDATE`, y hace demostrable la carrera en los dos motores |
| B · versión optimista | columna `version` en `sessions` + comprobación | sí | **sí** (esquema) | ambos | — | descartada: migración y esquema prohibidos; A da lo mismo sin columna |
| C · `BEGIN IMMEDIATE` en el motor de producto para SQLite | la transacción toma el bloqueo al empezar | sí (configuración del motor) | no | solo SQLite; afecta a toda escritura de la app | exploración (c): 20/20 `[200, 401]` | no recomendada: semántica por motor en el producto para un motor que no es de producción |
| D · contrato PostgreSQL-only | `pytestmark`/`skipif(not PG)` en la prueba de concurrencia (precedente: `test_license_import_race.py`, `test_spec004_installation_race.py`, `test_roles_create.py`); SQLite conserva la cobertura secuencial (token usado → 401, sesión huérfana → no, servicio directo → 401) | 0 | no | la garantía queda declarada como de PostgreSQL | la prueba sigue corriendo ×20 en PostgreSQL | aceptable como mínimo: evidencia honesta, sin producto; deja el comentario del servicio por corregir (es texto, dueña 002) y la ventana abierta en SQLite |
| E2 · arnés con `BEGIN IMMEDIATE` solo en pruebas | (c) aplicado al fixture | 0 | no | SQLite de pruebas | 20/20 natural | **descartada**: confianza falsa (el producto en SQLite seguiría permitiendo las dos) |

En cualquier opción conviene además (sin decidir aquí): adoptar `motor_para_hilos` en el fixture del módulo para que las
dos peticiones tengan conexión propia (capa 1) y la prueba mida el producto y no el arnés.

**Recomendación**: **A** (y, si la dueña prefiere producto 0, **D**). A es una tarea pequeña pero de seguridad y
concurrencia: CLAUDE_ONLY, con vectores (I1 forzada en los dos motores, token usado, sesión expirada, hash distinto,
usuario inactivo) y mutaciones (quitar la condición `revoked_at IS NULL`, ignorar el rowcount, quitar `with_for_update`,
cambiar el 401 por 200).
