# Certificación real de copia y restauración (AD-B11, §77–§83)

Orden canónica, desde la raíz y con el Python del backend:

```
eval "$(resources/backend/.venv/bin/python qa/clamav_qa.py entorno)"
KONTROL_TEST_DB_URL=<PostgreSQL de QA> KONTROL_PG_BIN_DIR=<clientes pg> \
    resources/backend/.venv/bin/python qa/backup_restore_cert.py
```

Datos 100 % sintéticos. Secretos efímeros por corrida, solo en el entorno de los subprocesos y nunca en argv ni en la evidencia:
- contraseña del administrador;
- clave de copia;
- `KONTROL_SECRET_KEY` de origen y otra distinta de destino;
- anillo MFA;
- clave de firma de licencia;
- clave TOTP;
- tokens.

Bases `kbk_src_<run>` y `kbk_dst_<run>` en el PostgreSQL de QA. Ningún recurso ajeno: puertos libres elegidos al vuelo y procesos parados por PID. Evidencia en `qa/backup-runs/<run>/`, fuera de Git.

## Secuencia demostrada

1. **Origen.** Base migrada a la cabeza (0061) y siembra con:
   - `setup.initialize` real: tenant A, empresa A1 y administrador;
   - tenant B con su empresa;
   - licencia firmada con la clave efímera de la corrida.
2. **Actividad real por la API del origen:**
   - alta MFA (inicio de sesión, alta y confirmación con TOTP);
   - tipo documental con análisis obligatorio (ClamAV real);
   - documento y subida de un PDF sintético;
   - exportación CSV.
3. **Copia en vivo** con `python -m app.ops.backup create`, con el origen en marcha.
4. **Escritura posterior** a la copia: documento «Posterior a la copia».
5. **Verificación independiente** con `python -m app.ops.backup verify`.
6. **Custodia** de la clave de instalación fuera de la copia, y barrido del paquete: no contiene en claro ni la contraseña, ni la clave de copia, ni `PGDMP`, ni el marcador del PDF.
7. **Desastre.**
   - Se para el origen.
   - `DROP DATABASE` del origen y borrado de su almacén y su volumen.
   - Centinela C-00: el origen ya no es accesible.
8. **Restauración** en una base nueva y vacía y en una raíz nueva, con los secretos reprovisionados y una `KONTROL_SECRET_KEY` nueva: `python -m app.ops.backup restore`.
9. **Arranque del destino** en otro proceso, solo con el entorno del destino.
10. **Comprobaciones funcionales contra el destino.**

| Check | Qué demuestra |
|---|---|
| C-00 | La fuente está destruida antes de restaurar (independencia de la fuente) |
| C-01 | Inicio de sesión con `MFA_REQUIRED` y verificación con el TOTP original: el factor restaurado sigue activo y el anillo reprovisionado lo descifra |
| C-02 | La empresa A es visible y la del tenant B no (aislamiento de tenant) |
| C-03 | El documento se descarga con el mismo sha256 |
| C-04 | La exportación se descarga con el mismo sha256 |
| C-05 | Lo escrito tras la instantánea no existe (404): punto de corte |
| C-06 | Escritura nueva en el destino y su evento de auditoría `DOCUMENT_CREATED` |
| C-07 | `UPDATE` y `DELETE` sobre `audit_events` rechazados por los triggers |
| C-08 | Parámetro de consulta desconocido → 422 `UNKNOWN_QUERY_PARAMETER`; instante sin zona → 422 `NAIVE_DATETIME` |
| C-09 | El token anterior al desastre devuelve 401 |
| C-10 | Licencia reverificada al arrancar: `FULL_ACCESS` |
| C-11 | `INSTALLATION_RESTORED` = 2 (uno por tenant) e `INSTALLATION_BACKUP_CREATED` = 0 (se registró en el origen después de la instantánea) |
| C-12 | EDGE-21: `license_id`, `mode`, `period_start` y `period_end` del destino son los del punto de copia, y `last_reliable_date` no retrocede |
| C-13 | EDGE-21: importar en el destino una licencia de período anterior se rechaza con `LICENSE_PERIOD_DOWNGRADE` y el estado no cambia |
| S-01 | Ningún secreto de la corrida aparece en el manifiesto ni en los registros |
| M-01 | Las métricas de RPO y RTO están presentes |

Limpieza: destino parado, bases borradas, trabajo borrado, 0 bases residuales y puertos libres.

## Corridas

| Corrida | Veredicto | Nota |
|---|---|---|
| 20261028T192523Z-a0a4be | FAIL | C-08: el encargo de Claude usó `GET /audit/events?desde=`, que es una fecha, no un instante. Se corrigió el guion; el producto estaba bien |
| 20261028T192857Z-647a0d | **PASS** | Antes de endurecer el veredicto (T07C). RTO 34,4 s, de los cuales 30 s fueron la espera determinista del paso TOTP |
| 20261028T194351Z, 194427Z, 194534Z, 194643Z | — | Corridas de los mutantes M06-22..M06-25 (ver `mutaciones.md`) |
| 20261028T194821Z-a8fdf8 | **PASS** | Antes de la convergencia (sin C-12/C-13); validador: VALIDO |
| 20261028T230008Z-9657d0 | **PASS** | **Corrida de cierre** con el código final, incluidos la corrección del manifiesto de licencia (T050) y C-12/C-13 (T051); validador externo (C-00..C-13, S-01, M-01): VALIDO |

## Métricas (corrida de cierre 20261028T230008Z-9657d0)

| Métrica | Valor |
|---|---|
| RTO (inicio de la restauración → primer inicio de sesión autenticado en el destino) | 34,9 s (de los que unos 30 s son la espera determinista al paso TOTP siguiente; sin ella, 5,1 s en la corrida a8fdf8) |
| Restauración por CLI | 1,30 s |
| Copia por CLI | 0,20 s (conjunto sintético; paquete de 768 000 bytes, sha256 `f4a145fa…`) |
| Ventana perdida (instantánea → desastre) | 1,31 s |
| Objetivo de RTO (FR-001-083 / NFR-001-008) | ≤ 4 h → **MET** |
| Objetivo de RPO | ≤ 15 min → **DEPENDS_ON_BACKUP_SCHEDULE**: el RPO real es el intervalo entre copias; sin planificación automática ni WAL/PITR (deuda BACKUP-SCHEDULE-RPO, tarea T052) el objetivo no se cumple con copias manuales |

Los tiempos son de un conjunto sintético pequeño en la estación de QA. No extrapolan el RTO de una instalación con datos reales; esa medida corresponde al ejercicio en el anfitrión de destino (runbook §3 y §8).
