# SPEC 046 · Delta de corrección — DOCUMENT-UPLOAD-HOLDS-DB-CONNECTION-DURING-SCAN (B1)

Dueña: Spec 046. Apoyo: Spec 001. Diagnóstico de origen (no se reescribe):
`spec046-document-upload-db-connection-scan-diagnosis-delta.md`. Fecha 2026-10-19, `develop`, HEAD de partida `ecd756a`.
Evidencia: `evidence/document-upload-db-connection-scan-fix/`.

## 1. Specify
La carga documental analiza el fichero dentro de una transacción de solo lectura que retiene una conexión del pool sin
proteger nada.

## 2. Clarify
- Frontera B1 en el endpoint, después de todas las comprobaciones previas (licencia, autenticación, permiso, empresa,
  documento, tipo e idempotencia) y antes de `service.upload_version`:
  1. guarda que falla cerrada ante estado ORM pendiente (`RuntimeError` → 500 `INTERNAL_ERROR` del manejador global);
  2. `db.commit()` de la fase de solo lectura.
- No se tocan `get_db`, `sessionmaker`, el pool, el servicio, el analizador ni el almacenamiento.
- No se añade revalidación ni bloqueos (TOCTOU_INTRODUCED = 0).
- Las tres deudas previas no se absorben: archivado, borrado y auditoría de rechazo.

## 3. Plan · 4. Constitution gate
- **Producto:** `documents/api.py`, unas pocas líneas.
- **Prueba nueva:** `tests/test_document_upload_connection_boundary.py`, en los dos motores, sin skip ni sleep, con el
  analizador controlado por `Event` y el analizador real.
- **Gate:** seguridad ✔ · atomicidad ✔ · fail-closed ✔ · OpenAPI sin cambio ✔ · OBS-09 sin solape ✔.

## 5. Tareas
| Tarea | EXECUTOR | MODEL | FILES | DONE_WHEN |
|---|---|---|---|---|
| F01 re-reproducción, gate, briefs | CLAUDE | n-a | delta, evidencia | gate |
| F02a producto | DEEPSEEK | deepseek-v4-flash | `app/modules/documents/api.py` | AUDIT_PASS, ruff, mypy |
| F02b prueba | DEEPSEEK | deepseek-v4-pro | `tests/test_document_upload_connection_boundary.py` | dos motores, rojo contra HEAD |
| F02c aserción de orden de B09 (división de F02b tras dos reintentos) | DEEPSEEK | deepseek-v4-flash | `tests/test_document_upload_connection_boundary.py` | AUDIT_PASS, B09 |
| F03 mutaciones, certificación, converge | CLAUDE | n-a | evidencia | gate de cierre |

## 6. Gate material — `checkpoint-and-gate.md`
Todos los criterios se cumplen → **implementación autorizada**.

## 7. Implementación
- **Producto (F02a):** `upload_version` lleva, tras la idempotencia, la guarda
  `if db.new or db.dirty or db.deleted: raise RuntimeError(...)` y `db.commit()`. Son 6 líneas, aplicadas tal cual;
  ruff limpio y mypy sin errores nuevos.
- **Prueba (F02b + F02c):** B01–B09, en los dos motores, con el analizador controlado por `Event` y el real.
  - DeepSeek escribió todo: 5 llamadas, $0,029095.
  - Hubo 2 rechazos y una reclasificación por división.
  - Detalle en `orchestration.md`.

## 8. Pruebas y mutaciones
- **Prueba nueva:** 9/9 en SQLite y PostgreSQL, en módulo, en orden inverso y cada una sola. Contra el `api.py` de
  HEAD fallan B01, B03, B04, B08 y B09.
- **Mutaciones:** 14/14 KILLED, 0 SURVIVED, 14/14 RESTORED.
- Detalle en `directed-tests.md` y `mutations.json`.

## 9. Certificación — `certification.md`
- SQLite: 1885/0/1046 ×2.
- PostgreSQL: 2904/1/26.
  - El único fallo, `test_e2ecorrida_01`, es previo y ajeno: autovacuum en la huella de `ktest`.
  - Se atribuyó con X1/X2, ver `postgres-failure-attribution.md`.
- E2E: 284/0/0, con 0 QueuePool bajo mayor presión del equipo.
- OpenAPI: 544/533/11.

## 10. Convergencia — `convergence.md`
**IMPLEMENTED — POSTGRESQL CERTIFICATION NOT GREEN (1 PRE-EXISTING QA-HARNESS FAILURE ATTRIBUTED).**

- Todos los requisitos de B1 están demostrados.
- El cierre (CLOSED / CONVERGED) espera la decisión de la dueña sobre la atribución, o una corrida PostgreSQL verde
  tras corregir E2E-HARNESS-PROTECTED-FINGERPRINT-COUNTS-AUTOVACUUM.
- Las tres deudas documentales siguen OPEN, sin absorber.

## 11. Cierre final (2026-10-19, ciclo de la Spec 054)

La dueña aceptó la atribución:
- ATTRIBUTION_ACCEPTED = 1;
- B1_PRODUCT_REGRESSION = 0;
- B1_CLOSURE_GATE_WAIVED = 0.

Se corrigió la huella de la herramienta QA (`spec054-e2e-protected-fingerprint-autovacuum-delta.md`) y la certificación
PostgreSQL completa salió en verde sobre el producto de B1 sin cambios:
- PostgreSQL: **2915/0/26**, con `test_e2ecorrida_01` PASS;
- SQLite: 1885/0/1056 ×2;
- E2E: **284/0/0**, 0 QueuePool, limpieza LIMPIA;
- OpenAPI: 544/533/11.

Se reutilizan:
- las 9 pruebas dirigidas en los dos motores;
- las 14/14 mutaciones;
- la evidencia de ciclo de vida de conexiones de §7–§9.

**DOCUMENT-UPLOAD-HOLDS-DB-CONNECTION-DURING-SCAN = CLOSED / CONVERGED.**
- B1_POSTGRES_FINAL_CERTIFICATION = PASS.
- El producto de B1 no se tocó.
- Las tres deudas documentales siguen OPEN.

Detalle: `evidence/document-upload-db-connection-scan-fix/final-closure.md`.
