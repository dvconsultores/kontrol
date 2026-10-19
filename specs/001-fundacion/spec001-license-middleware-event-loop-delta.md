# SPEC 001 · Delta dirigida — LICENSE-MIDDLEWARE-BLOCKS-EVENT-LOOP

Dueña: Spec 001 (fundación; middleware de licencia, FR-001-053). Diagnóstico de origen: Spec 054,
`specs/012-auditoria-integral-e2e/spec054-e2e-pool-exhaustion-diagnosis-delta.md` (E2E-POOL-EXHAUSTION-UNDER-HOST-PAGING,
ROOT CAUSE PROVEN). Fecha 2026-10-19, `develop`, HEAD de partida `55dbd9c`. Evidencia: `evidence/license-middleware-event-loop/`.

## 1. Specify
`LicenseMiddleware.dispatch` es `async` y llama de forma síncrona a `self._get_mode()`, que espera una conexión del pool en el
bucle de eventos. Con el pool saturado, el servidor se congela hasta el `TimeoutError` de 30 s.

## 2. Clarify
- La corrección es mínima: `mode = await run_in_threadpool(self._get_mode)`.
- No cambia nada de la semántica: `WRITE_METHODS`, `LICENSE_EXEMPT_PREFIXES`, `READ_ONLY` y `SECURITY_SUSPENSION`, sus 423,
  códigos, mensajes y cuerpo, el orden (bloquear antes de la lógica de escritura) ni las lecturas, que no consultan el modo.
- Sin caché, sin alternativa, sin memoización, sin reintentos y sin fail-open.
- `DOCUMENT-UPLOAD-HOLDS-DB-CONNECTION-DURING-SCAN` (Spec 046) se registra como deuda aparte y no se absorbe.

## 3. Plan
- **Producto.** `app/core/middleware.py`: importar `run_in_threadpool` desde `starlette.concurrency` y esperar `_get_mode`
  en el threadpool.
- **Prueba nueva.** `tests/test_license_middleware_event_loop.py`, en los dos motores y sin skip, con tres partes:
  - contrato de licencia sobre una app mínima;
  - mecanismo determinista con `threading.Event`;
  - regresión X3 con uvicorn real y pool 5 + 10, con retenedoras sincronizadas por `Event` y `Semaphore`, sin `sleep`.

## 4. Constitution gate
- Seguridad y licencia: semántica intacta ✔.
- P21: PostgreSQL y SQLite, sin degradar ✔.
- Sin esquema, migraciones, pool, timeouts ni analizador ✔.
- Sin fail-open ✔. OBS-09 sin solape ✔.

## 5. Tareas
| Tarea | EXECUTOR | MODEL | FILES | DONE_WHEN |
|---|---|---|---|---|
| L01 re-reproducción, gate, briefs | CLAUDE | n-a | delta, evidencia | gate material |
| L02a producto | DEEPSEEK | deepseek-v4-flash | `app/core/middleware.py` | AUDIT_PASS, ruff, mypy |
| L02b prueba de regresión | DEEPSEEK | deepseek-v4-pro | `tests/test_license_middleware_event_loop.py` | dos motores, rojo contra HEAD |
| L03 mutaciones, certificación, converge | CLAUDE | n-a | evidencia | gate de cierre |
SECURITY_SENSITIVE sí (licencia): el diseño y la auditoría son de Claude, la escritura de DeepSeek. RETRY_MAX 2.

## 6. Gate material — `material-gate.md`
Todos los criterios están en 1 / 0 según corresponde → **implementación autorizada**.

## 7. Implementación (DeepSeek escribe, Claude audita) — `orchestration.md`
- **Producto:** `from starlette.concurrency import run_in_threadpool` y `mode = await run_in_threadpool(self._get_mode)`.
- **Prueba nueva:** `tests/test_license_middleware_event_loop.py`, con 17 pruebas: contrato L01-L06, mecanismo L07-L10 y
  uvicorn real U01-U04.
- **Orquestación:** 5 llamadas ($0,028), 2 rechazos y la reclasificación L02c.
## 8. Pruebas, mutaciones, certificación — `directed-tests.md`, `mutation-campaign.md`, `certification.md`
- **Dirigidas:** 17/17 en los dos motores, solas y en orden inverso. Contra HEAD fallan justo L07, L09, L10 y U01.
- **Mutaciones:** 11/11 muertas.
- **Licencia existente:** 55/55 sin cambio.
- **Sonda X3:** 3,06 s y 404 (antes 30,26 s y 500).
- **Suites:** SQLite 1876/0/1046 ×2, PostgreSQL 2896/0/26 y E2E 284/0/0 con 0 `QueuePool`. OpenAPI queda en 544/533/11.
## 9. Convergencia — `convergence.md`: **CLOSED / CONVERGED** (2026-10-19). Cierra también
E2E-POOL-EXHAUSTION-UNDER-HOST-PAGING (Spec 054).
Deuda separada registrada y no absorbida: `DOCUMENT-UPLOAD-HOLDS-DB-CONNECTION-DURING-SCAN` (Spec 046). Una carga documental
retiene la conexión de la petición durante clamscan, lo que aumenta la probabilidad de saturar el pool. Ya no congela el
servidor, pero puede hacer esperar a otras peticiones.
