# Checkpoint, re-reproducción y gate material (2026-10-19)
HEAD = origin = `ecd756a` · `develop` · limpio · 0 commits posteriores · bases de corrida 0 · puertos libres.
`OBS09_EXTERNAL_EVIDENCE_AVAILABLE = 0` → **RUTA B** (corrección B1). La raíz `kontrol-doc-*` del 2026-10-18 04:02 es previa y
no se toca.

## Re-reproducción previa a la corrección (sonda desechable; PostgreSQL de QA; analizador detenido con Event y analizador real)
| Campo | Controlado | Real (clamscan) |
|---|---|---|
| PRE_FIX_CONNECTION_CHECKED_OUT_DURING_SCAN | **1** | **1** |
| PRE_FIX_TRANSACTION_ACTIVE_DURING_SCAN | **1** (`idle in transaction`, sin `xid`) | 1 (`in_transaction` en la frontera) |
| PRE_SCAN_ORM_NEW / DIRTY / DELETED | 0 / 0 / 0 | 0 / 0 / 0 |
| PRE_SCAN_DML_STATEMENTS | **0** (solo `SELECT`) | **0** (solo `SELECT`) |
| PRE_SCAN_FLUSH_WRITES | 0 | 0 |
| Checkouts entre la frontera y el análisis | 0 | 0 |
| Resultado | 200 · 1 versión · auditoría de subida | 200 · 1 versión · auditoría de subida |

## Clarify confirmado en el código
- `get_session_factory`: `expire_on_commit=False`, `autoflush=False` → EXPIRE_ON_COMMIT_FALSE = 1.
- Los modelos documentales no declaran relaciones perezosas; `service.upload_version` usa atributos ya cargados de
  `document`, `doc_type` y `actor` → POST_BOUNDARY_LAZY_LOAD_BEFORE_SCAN = 0 (medido después en la prueba).
- Punto de frontera en `documents/api.py::upload_version`: después de `_get_document`, `_get_type` y del bloque de
  idempotencia (que devuelve el acierto sin analizar); antes del `try` que llama a `service.upload_version`.
- Guarda: estado ORM pendiente (`db.new`, `db.dirty`, `db.deleted`) → `RuntimeError`, que el manejador global
  (`_unhandled_handler`) convierte en 500 `INTERNAL_ERROR` saneado y `get_db` revierte al cerrar: la escritura inesperada no
  se confirma y el análisis no empieza.
- Fase posterior: `service.upload_version` vuelve a abrir transacción en su primera sentencia, y todas sus escrituras
  terminan en el `commit` final de siempre.

## Gate
ROOT_CAUSE_PROVEN 1 · SAFE_BOUNDARY_PROVEN 1 · OWNER_SPEC_CONFIRMED 1 (046) · PRE_SCAN_ORM_NEW / DIRTY / DELETED 0 / 0 / 0 ·
PRE_SCAN_DML_STATEMENTS 0 · PRE_SCAN_FLUSH_WRITES 0 · EXPIRE_ON_COMMIT_FALSE 1 · POST_BOUNDARY_LAZY_LOAD_BEFORE_SCAN 0 ·
SECURITY / ATOMICITY / FAIL_CLOSED / IDEMPOTENCY_PRESERVABLE 1 / 1 / 1 / 1 · OWNER_DECISION_REQUIRED 0 · MATERIAL_OQ 0 ·
UNKNOWN 0 → **implementación autorizada**.
