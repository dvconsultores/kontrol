# Experimentos (sondas desechables, no versionadas; PostgreSQL de QA; motor con los parámetros de producción; clamscan real del QA)
| Id | Condición | Resultado medido |
|---|---|---|
| D1 | una carga real (clamscan) | 200 en 6,29 s; conexión prestada durante los 6,25 s del análisis; la primera operación de base es la dependencia de licencia de escritura |
| D2 | análisis detenido con `Event` (sin `sleep`) | `checked_out = 1`; `pg_stat_activity`: `idle in transaction`, transacción abierta, **sin `xid`** (sin escrituras); `pg_locks`: solo `AccessShareLock` de tabla e índice (companies, documents, document_types, installations, license_states, permissions…), **ningún bloqueo de fila**; 0 `stored_files`, 0 versiones, 0 auditoría, 0 ficheros en almacén mientras dura |
| D2b | análisis detenido que devuelve INFECTED | 422 `FILE_INFECTED`; el `INSERT audit_events` de `DOCUMENT_SCAN_REJECTED` se **revierte**: 0 filas (la auditoría de rechazo no persiste) |
| D3 | 1 / 2 / 5 / 10 cargas reales concurrentes (uvicorn real) | todas 200; conexiones prestadas = análisis simultáneos (1/2/5/10); p50 6,26 / 6,77 / 8,43 / 18,64 s; 0 agotamientos (por debajo de 15) |
| D4 | primera operación | `SELECT installations` de `get_license_mode` (licencia de escritura), antes que la autenticación |
| D5 | estado durante el análisis | transacción activa, solo lecturas, sin datos sin confirmar, sin bloqueos de fila |
| D6 | orden | análisis **antes** de almacenar y de toda escritura: FILE/METADATA/AUDIT_EXISTS_BEFORE_SCAN = 0/0/0 (solo el temporal) |
| D7a | archivar el documento durante el análisis | el archivo responde 200 en 0,02 s (no lo bloquea nada); la carga termina en 200 y el documento queda **ACTIVE**: **actualización perdida** (la carga escribe su copia rancia «DRAFT → ACTIVE» sobre el ARCHIVED) |
| D7b | borrar el documento durante el análisis | el borrado responde 200 en 0,01 s; la carga termina en **500 INTERNAL_ERROR** (FK) y deja **1 binario huérfano** en el almacén |
| D8 | aislamiento | `read committed` |
| D9 | contrafactual (solo en la sonda): confirmar la transacción de solo lectura antes del servicio | `checked_out = 0` durante el análisis; 200; versión y auditoría persistidas; dos transacciones cortas en lugar de una larga |
| D9b | contrafactual + INFECTED | 422 `FILE_INFECTED`; 0 versiones; 0 ficheros |
Las sondas se eliminaron del árbol (TEMP_PROBES = 0, POOL_TELEMETRY_HOOKS = 0, SCANNER_TEST_HOOKS = 0: `set_scanner(None)`).
