# Re-reproducción previa y gate material

## Re-reproducción previa a la corrección
Misma sonda desechable que el diagnóstico: uvicorn real, `create_app()`, motor con los parámetros de producción y PostgreSQL
de QA. El detalle está en `pre-fix-reproduction.json`.
| Campo | Valor |
|---|---|
| PRE_FIX_X3_REPRODUCED | **1** |
| PRE_FIX_WRITE_STATUS · DURATION | **500** · **30,03 s** |
| PRE_FIX_HOLDERS_DURATION | **30,26 s**, para retenciones de 3 s |
| PRE_FIX_POOL_TIMEOUT | 30 s (`QueuePool` 5 + 10) |
| PRE_FIX_CHECKOUT_CHECKIN | 144 = 144, 0 prestadas al final |
| Controles | C1 3,05 s · C2 3,05 s · X2 hasta 20 sin error · X4 (contrafactual) 3,04 s |

## Invariantes del threadpool y del contexto
| Campo | Valor | Fuente |
|---|---|---|
| API real | `starlette.concurrency.run_in_threadpool(func, *args)` → `await anyio.to_thread.run_sync(func, *args)` | starlette 0.41.3 |
| GET_MODE_SESSION_CREATED_IN_WORKER | 1 | `app/main.py::_get_mode` crea la sesión dentro de la función |
| GET_MODE_DB_IO_IN_WORKER | 1 | `current_mode(db)` (y su posible `db.commit()` del modo en caché) dentro de la misma función |
| GET_MODE_SESSION_CLOSED_IN_WORKER | 1 | `finally: db.close()` dentro de la misma función |
| GET_MODE_RETURNS_DB_FREE_VALUE | 1 | devuelve `str`: `get_status(db)["mode"]`, `"PENDING"` o `SECURITY_SUSPENSION` |
| GET_MODE_USES_CONTEXTVARS | 0 | no hay `ContextVar` en `app/` |
| THREADPOOL_CONTEXT_PROPAGATION_CONFIRMED | 1 | anyio 4.14.2: `copy_context()` en `run_sync_in_worker_thread`; la prueba L08 lo verifica |
| REQUEST_CONTEXT_SEMANTICS_UNCHANGED | 1 | `_get_mode` no recibe la petición ni la empresa, y la decisión sigue en `dispatch` |

## Gate
ROOT_CAUSE_PROVEN 1 · OWNER_SPEC_CONFIRMED 1 (001, FR-001-053) · SOLUTION_SCOPE_BOUNDED 1 (una importación y una línea) ·
MIDDLEWARE_SEMANTICS_UNCHANGED 1 · LICENSE_ERROR_CONTRACT_UNCHANGED 1 · POOL_CONFIG_CHANGE_REQUIRED 0 ·
SESSION_MODEL_CHANGE_REQUIRED 0 · SCANNER_CHANGE_REQUIRED 0 · OWNER_DECISION_REQUIRED 0 · MATERIAL_OQ 0 · UNKNOWN 0 →
**implementación autorizada**.
