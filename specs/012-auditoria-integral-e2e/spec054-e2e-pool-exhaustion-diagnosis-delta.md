# SPEC 054 · Delta de diagnóstico — E2E-POOL-EXHAUSTION-UNDER-HOST-PAGING

Dueña del diagnóstico: Spec 054 (auditoría E2E y arnés). Dueña del defecto y de la corrección: Spec 001 (fundación,
middleware de licencia, FR-001-053). Fecha 2026-10-19, `develop`, HEAD `5b8f86b`. Sin cambio de producto, de pruebas ni de
QA. Evidencia: `evidence/e2e-pool-exhaustion-diagnosis/`.

## 1. Specify
En la E2E sobre `f93232b` (273/7) aparecieron 4 `QueuePool limit of size 5 overflow 10 reached` en el middleware de licencia,
y 7 pantallas de módulos ajenos vencieron su espera de 30 s. Sobre el mismo código, otra E2E dio 284/0/0.

## 2. Clarify
Ciclo de diagnóstico: se demuestra la causa y no se corrige. OWNER_DECISION_REQUIRED 0.

## 3. Plan
Primero un inventario del motor, las sesiones y el middleware. Después la sonda desechable con uvicorn real y telemetría
de pool: línea base, escalones, mecanismo, controles y contrafactual.

## 4. Constitution gate
Sin producto, pruebas, QA, esquema, pool ni timeouts: ✔. Producción 0: ✔. OBS-09 sin solape: ✔.

## 5. Tareas
| Tarea | EXECUTOR | Resultado |
|---|---|---|
| D01 inventario | CLAUDE | `architecture-inventory.md`, `pool-lifecycle.md` |
| D02 experimentos | CLAUDE (sonda desechable, no versionada) | `experiment-matrix.md`, `experiment-results.json` |
| D03 causa raíz y diseño | CLAUDE | `root-cause.md`, `recommended-design.md` |
DEEPSEEK_CALLS 0: no hubo código versionado que escribir.

## 6. Resultado
**DIAGNOSIS COMPLETE — ROOT CAUSE PROVEN: `EVENT_LOOP_BLOCKED_BY_SYNC_DB_IN_ASYNC_MIDDLEWARE`.**
`LicenseMiddleware.dispatch`, que es `async`, espera de forma síncrona una conexión en el bucle de eventos. Con el pool
saturado, el bucle no puede cerrar las sesiones que devolverían conexiones, y todo se congela 30 s hasta el `TimeoutError`.

| Experimento | Resultado |
|---|---|
| X3 | reproducido: 500 a los 30,05 s y retenedoras de 3 s que tardan 30,28 s |
| C1, C2 | controles sin fallo |
| X4 | contrafactual sin fallo |
| Fugas | 0 |

## 7. Siguiente
La corrección mínima es descargar `_get_mode` al threadpool, con dueña la 001; está en `recommended-design.md`. Queda para un
ciclo propio con material gate. El estado de la observación es **ROOT CAUSE PROVEN — FIX NOT IMPLEMENTED (OPEN)**.

## 8. Corrección (añadido 2026-10-19; el diagnóstico anterior no se reescribe)
La corrigió la Spec 001: `specs/001-fundacion/spec001-license-middleware-event-loop-delta.md` (LICENSE-MIDDLEWARE-BLOCKS-EVENT-LOOP).
Tras la corrección, X3 se comporta como el contrafactual X4, y la E2E dio 284/0/0 con 0 `QueuePool` bajo mayor presión de
memoria. Estado de la observación: **CLOSED / CONVERGED**.
