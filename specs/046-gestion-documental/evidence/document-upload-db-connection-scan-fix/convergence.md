# Convergencia — B1

| Requisito del encargo | Evidencia | Estado |
|---|---|---|
| La frontera B1 va después de documento, tipo e idempotencia y antes del servicio | `api.py` (+6 líneas), B09 AST, M02/M03/M04 KILLED | ✔ |
| Guarda que falla cerrada ante escrituras pendientes (500 genérico, sin 500 manual) | B08, M05/M06 KILLED | ✔ |
| Sin DML antes de la frontera, medido | B02; reproducción previa (0 DML, 0 flush con escrituras) | ✔ |
| `EXPIRE_ON_COMMIT_FALSE` = 1 | `get_session_factory()` y la prueba usan `expire_on_commit=False`; M07 (rollback, que expira) KILLED | ✔ |
| Sin lazy load ni checkout antes del análisis | B01 (0 checkouts entre el commit y `scan_start`), M08 KILLED | ✔ |
| 0 conexiones durante el análisis (controlado y real) | B01, B04; rojo en HEAD `assert 1 == 0` | ✔ |
| Escrituras posteriores atómicas | B03 | ✔ |
| INFECTED y SCAN_FAILED: mismo 422 | B05, B06, M10/M14 KILLED | ✔ |
| Idempotencia y VERSION_CONFLICT conservados | B07, M11 KILLED; M12 KILLED en PostgreSQL (`test_la_misma_clave_en_carrera_devuelve_la_version_ganadora`) | ✔ |
| Sin revalidación, bloqueos ni SELECT FOR UPDATE (TOCTOU_INTRODUCED = 0) | diff de producto | ✔ |
| Tres deudas ajenas sin absorber y con su comportamiento intacto | `service.py` sin diff; B05 no afirma nada sobre la auditoría de rechazo | ✔ |
| Rutas prohibidas intactas | `git diff --stat`: solo `documents/api.py` en producto | ✔ |
| Mutaciones ≥ 12 | 14/14 KILLED, 0 SURVIVED, 14/14 RESTORED | ✔ |
| SQLite ×2 | 1885/0/1046 ×2 | ✔ |
| PostgreSQL ×1 | 2904/**1**/26: fallo previo de la herramienta QA (autovacuum), atribuido con X1/X2 | **✘ no verde** |
| E2E ×1 | 284/0/0, 0 QueuePool | ✔ |
| OpenAPI | 544/533/11 | ✔ |

**Estado:** IMPLEMENTED — POSTGRESQL CERTIFICATION NOT GREEN (1 PRE-EXISTING QA-HARNESS FAILURE ATTRIBUTED).

- No se declara CLOSED / CONVERGED: el encargo exige todo en verde, y aceptar la atribución es decisión de la dueña.
- Toda la convergencia de B1 está demostrada.
- La deuda nueva E2E-HARNESS-PROTECTED-FINGERPRINT-COUNTS-AUTOVACUUM (dueña 054) queda abierta.
