# SPEC 010 · Delta dirigida — OBS-11 · LICENSING-CENTRAL-SYNC-TIME-ASSERTION

Dueña: 010 (licenciamiento central; FR-010-003). Apoyo: 054 (enlace cruzado en
`specs/012-auditoria-integral-e2e/spec054-obs11-sync-time-anchor-delta.md`). Fecha: 2026-10-15. HEAD de partida `d122d6b`.
Decisión `[X] OBS-11` ratificada. Evidencia en `evidence/obs11-sync-time-anchor/`. Producto 0, reloj canónico 0, migraciones 0,
esquema 0, OBS-12 no absorbida.

## 1. Checkpoint — `checkpoint.md`
## 2. `/speckit.specify` — FR-O11-001…026 (del encargo)
## 3. `/speckit.clarify`
| Paso | Resultado | Evidencia |
|---|---|---|
| Dueña | Spec 010 (carpeta; inventario fila 004 «Licenciamiento») | `owner-matrix.md` |
| Aserción exacta | `state.last_reliable_date.replace(tzinfo=UTC) == SERVER_TIME`, con `SERVER_TIME` = importación + 5 min | `exact-assertion.md` |
| Procedencia | activación = `_now()` del servicio; sync aplica `server_time` solo si es posterior (monótono) | `timestamp-provenance.md` |
| Invariante | el reloj confiable toma el instante del servidor cuando es posterior y nunca retrocede; precondición oculta: activación < `SERVER_TIME` | `intended-invariant.md` |
| Vida de la referencia | importación del módulo usada como frontera de una operación posterior: **YES**; falla con edad > 5 min | `module-start-lifetime.md` |
| Precisión | sin tolerancia necesaria (valor exacto sin µs del servidor falso) | `timestamp-provenance.md` |
| Hermanos | `AHORA`/`HOY` en otros módulos son fechas civiles, no fronteras de operación | `sibling-pattern-inventory.md` |
| OBS-12 | solo amplifica H1 | `obs12-context.md` |
## 4. `/speckit.plan`, gate, checklist, tasks
W01–W30; G01–G30 cumplidos para el diagnóstico (producto, migración, esquema, sleep, retry, skip, xfail, tolerancia 0);
tareas T01–T08 CLAUDE_ONLY; `DEEPSEEK CALLS = 0`. Diagnóstico autorizado (etapa 1): aislada ×20 por motor, matriz de
envejecimiento determinista (monkeypatch de la referencia **propiedad de la prueba** en una copia temporal, sin sleep),
control de frontera de operación, control de verdadero negativo (servidor más atrasado que la activación).
## 5. Diagnóstico (etapa 1) — resultados
| Control | SQLite | PostgreSQL | Evidencia |
|---|---|---|---|
| aislada ×20 | 20/20 | 20/20 | `isolated-baseline.md` |
| envejecimiento determinista (0 s…60 min, monkeypatch, sin sleep) | FAIL desde 5 min | FAIL desde 5 min (idéntico) | `aged-control.md` |
| frontera de operación | 8/8 | 8/8 | `operation-boundary-control.md` |
| verdadero negativo (servidor −10 min) | PASS, conserva la activación | PASS | `true-negative-control.md` |
| precisión / zona | igualdad exacta con referencia válida | ídem | `precision-analysis.md` |
`ROOT_CAUSE_CLASS = TEST_TIME_ANCHOR_DEFECT` · `PRODUCT_DEFECT = NO` · `IMPLEMENTATION_ALLOWED = YES` (`root-cause.md`,
`implementation-decision.md`). Gate material: `MATERIAL_DECISION_REQUIRED = 0`.
## 6. Implementación (etapa 2, solo pruebas) — `implementation.md`
`tests/test_licensing_central.py`: sin `SERVER_TIME`; `_TransporteFalso` captura `self.server_time` al construirse y lo usa en
respuesta y desafío; la prueba objetivo compara con `transporte.server_time`. Nuevo `tests/test_licensing_sync_time_anchor.py`
(O11-01…06). Producto, reloj canónico, protocolo, migraciones y esquema: 0.
## 7. Pruebas y evidencia
Dirigidas (`directed-tests.md`), mutaciones 13/13 (`mutation-campaign.md`), SQLite ×2 1699/0/1046 (`sqlite-full-1.md`,
`sqlite-full-2.md`), PostgreSQL 2719/0/26 (`postgres-full.md`), E2E 284/0/0 con analizador (`global-e2e.md`), OpenAPI
544/533/11 (`openapi.md`), reloj canónico (`canonical-clock-contract.md`), OBS-12 (`obs12-context.md`).
## 8. Analyze final, trazabilidad y convergencia
`final-analyze.md` (0/0/0/0; `DEEPSEEK CALLS = 0`), `traceability-matrix.md` (100 %), `convergence.md`: **CONVERGED 2026-10-15**.
