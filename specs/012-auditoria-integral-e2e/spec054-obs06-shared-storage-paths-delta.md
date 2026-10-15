# SPEC 054 · Delta dirigida — OBS-06 · HARNESS-SHARED-STORAGE-PATHS

Dueña: 054 (arnés). Fecha: 2026-10-15. HEAD de partida `7a15f2e`. Decisión `[X] OBS-06` ratificada (diagnóstico acotado;
aislamiento del arnés solo si se demuestra). Evidencia en `evidence/obs06-shared-storage-paths/`. Producto 0, migraciones 0,
esquema 0, timeouts 0, sleep/retry/skip/xfail 0, reorden 0, paralelismo 0, analizador intacto, OBS-07/09 no absorbidas.

## 1. Checkpoint — `checkpoint.md` · 2. Dueña — `owner-matrix.md`
## 3. `/speckit.specify` — SOLICITUD/CAMBIO
Determinar si las rutas fijas de prueba `KONTROL_STORAGE_PATH`/`KONTROL_BACKUP_PATH` comparten estado entre procesos,
sesiones y corridas y, si se demuestra, sustituir **solo el espacio de nombres del arnés** por uno aislado por proceso:
creado antes de que la configuración lo consuma, estable en la sesión, compartido por todos los actores del proceso,
invisible a otros procesos, limpiado con seguridad, sin cambiar la semántica del producto ni las aserciones documentales
ni de exportación, e integrado con la telemetría de residuos de OBS-12. Requisitos FR-O06-001…036 (del encargo).
## 4. `/speckit.clarify`
| Paso | Resultado | Evidencia |
|---|---|---|
| Definiciones | única definición compartida entre procesos de pytest: `conftest.py:32-33` (eco en `test_migrations_offline.py`); el resto de rutas fijas son de QA manual con otros nombres; el producto por defecto `/data/*` | `path-definition-inventory.md` |
| Ciclo de vida | env al importar el conftest; `Settings` cacheada en la colección (`app.main`); documentos capturan el proveedor en el primer uso; `pytest_configure` precede a todo | `configuration-lifetime.md` |
| Consumidores | documentos (`documents/AAAA/MM/DD/<token>`), reporting (`exports/report-<clave>-<marca 1 s>`), `backup_path` **sin consumidor** | `consumer-matrix.md` |
| Escritores | `test_reporting.py` (marca de tiempo, 3 ficheros por corrida) y `test_n9_integrity.py` (proveedor por defecto); el resto usa raíces propias | `writer-inventory.md` |
| Limpieza | creador: producto; limpiador: nadie; persistencia no intencional; UNKNOWN 0 | `cleanup-contract.md` |
| Precedente | volumen de instalación en el mismo conftest: `pytest_configure` + `mkdtemp` + stash + `pytest_unconfigure` + sondas | `process-isolation-precedent.md` |
| OBS-12 | `almacen_fijo_presente`; cambio esperado si se confirma | `obs12-residue-contract.md` |
| Contrato producto/arnés | `PRODUCT_STORAGE_CONTRACT` = ruta base configurable por variable, leída por `get_settings()`; `TEST_HARNESS_CONTRACT` = inyección antes de la primera `Settings`; `CONFLICT = NO` | `configuration-lifetime.md` |
| Diagnóstico | D1–D8 diseñados, sin ejecutar | `diagnostic-plan.md` |
## 5. `/speckit.plan` — W01…W35 (del encargo): W01–W10 hechos en clarify; W11–W18 sondas; W19 matriz; W20–W22 diseño,
pruebas y mutaciones; W23–W27 certificación y OBS-12; W28 clasificación (todas CLAUDE_ONLY); W29–W35 analyze,
trazabilidad, diagnóstico, gate, implementación, certificación, convergencia.
## 6. CONSTITUTION GATE (pre-diagnóstico) — G01…G40
HEAD 7a15f2e · develop · OBS-06 ratificada · dueña 054 probada · definiciones, ciclo de vida, consumidores, escritores,
limpieza, precedente, OBS-12 y contrato producto/arnés mapeados · D1–D8 diseñados · producto/migración/esquema/timeout/
retry/sleep/skip/xfail/reorden/paralelismo/analizador 0 · BLOCKER = CRITICAL = CONTRADICTIONS = OWNER CONFLICT = 0 ·
huérfanos 0 · MATERIAL OQ 0 · UNKNOWN 0 · trazabilidad 100 % · `DIAGNOSTIC_PLAN_READY = YES`.
## 7. `/speckit.checklist` — todas las casillas del encargo marcadas con §4 y §6.
## 8. `/speckit.tasks`
| ID | Requisito | Ejecutor | Sensible | Egress | Ficheros | DONE_WHEN | Prueba / mutación | Evidencia |
|---|---|---|---|---|---|---|---|---|
| T01 | FR-001…004 | CLAUDE | no | n-a | ninguno | inventarios completos | — | clarify |
| T02 | FR-005…010, 014 | CLAUDE | no | n-a | ninguno | ciclo de vida y limpieza probados | — | clarify |
| T03 | FR-005…008 | CLAUDE | no | n-a | sondas temporales | D1, D2, D3, D6, D8 con veredicto | — | `d1…d3, d6, d8` |
| T04 | FR-009…010, 017…020 | CLAUDE | no | n-a | sondas temporales | D4, D5, D7 | — | `d4, d5, d7` |
| T05 | FR-027 | CLAUDE | no | n-a | ninguno | matriz con UNKNOWN 0 | — | `root-cause-matrix.md` |
| T06 | FR-011…020 | CLAUDE (CLAUDE_ONLY: aislamiento, limpieza) | no | n-a | `tests/conftest.py`, `tests/sondas_almacen/*`, `tests/test_almacen_de_pruebas.py` | O06 verdes | O06 + mutaciones | `implementation.md` |
| T07 | FR-031…032 | CLAUDE | no | n-a | `qa/suite_tiempos.py`, `tests/test_suite_tiempos_qa.py` | O06-18, O12 verdes | mutación M-09 | `obs12-telemetry.md` |
| T08 | FR-033 | CLAUDE | no | n-a | — | ≥ 10 mutaciones | — | `mutation-campaign.md` |
| T09 | FR-034…036 | CLAUDE | no | n-a | roadmap | suites 0 rojos; commit; push | — | `convergence.md` |
`RETRY_MAX: 2`; `DEEPSEEK CALLS = 0`.
## 9. `/speckit.analyze` (pre-diagnóstico)
OBS06_SELECTED YES · SPEC054_OWNER PROVEN · PATH_DEFINITIONS COMPLETE · SETTINGS_LIFETIME PROVEN · CONSUMER_MATRIX
COMPLETE · WRITER_MATRIX COMPLETE · CLEANUP_CONTRACT PROVEN · PRODUCT/HARNESS_STORAGE_CONTRACT PROVEN · OBS12_RESIDUE_CONTRACT
PROVEN · DIAGNOSTIC_PLAN FROZEN · PRODUCT_CHANGE_AUTHORIZED NO · MIGRATION/SCHEMA/TIMEOUT/RETRY/SLEEP/SKIP/XFAIL/REORDER/
PARALLELIZATION/SCANNER 0 · BLOCKER/CRITICAL/CONTRADICTIONS/OWNER CONFLICT/huérfanos/MATERIAL OQ/UNKNOWN 0 · TRACEABILITY
100 %. **AUTORIZACIÓN EXPRESA — ETAPA 1 consumida (diagnóstico acotado con marcadores sintéticos).**

## 10. Etapa 1 — diagnóstico (sondas temporales, eliminadas; marcadores sintéticos retirados)
| Sonda | Resultado | Evidencia |
|---|---|---|
| D1 | `STORAGE_PATH_EQUAL = YES`, `BACKUP_PATH_EQUAL = YES` en procesos consecutivos y simultáneos; es el almacén fijo histórico | `d1-path-identity.md` |
| D2 | `A_SEES_B = YES`, `B_SEES_A = YES` (almacén y respaldos) | `d2-cross-process-visibility.md` |
| D3 | fórmula real `report-<clave>-<marca de 1 s>`: B sobrescribe a A sin error | `d3-collision.md` |
| D4 | `CROSS_RUN_PERSISTENCE = YES`; ningún contrato lo exige | `d4-session-persistence.md` |
| D5 | +2 exportaciones por grupo; 121 ficheros acumulados en tres días | `d5-post-suite-residue.md` |
| D6 | raíces únicas por proceso, sin visibilidad, misma raíz dentro del proceso, eliminadas al terminar | `d6-isolated-root-control.md` |
| D7 | la limpieza solo toca la raíz propia | `d7-cleanup-ownership.md` |
| D8 | `pytest_configure` precede a `Settings`, `app.main`, `TestClient` y al proveedor documental | `d8-settings-ordering.md` |
Causa raíz (`root-cause-matrix.md`): **SHARED_PATH_LEAK + STALE_STATE_ACROSS_RUNS + CROSS_PROCESS_COLLISION +
HARNESS_CLEANUP_DEFECT**, demostradas de forma independiente; `SETTINGS_CAPTURE_DEFECT` y `PRODUCT_PATH_CONTRACT`
descartadas; UNKNOWN 0.
## 11. Gate material y etapa 2 — `implementation-decision.md`
`PRODUCT/MIGRATION/SCHEMA/TEST_SEMANTICS_CHANGE_REQUIRED = NO`, `OWNER_DECISION_REQUIRED = NO` → **AUTORIZACIÓN EXPRESA —
ETAPA 2 consumida** (solo arnés).
## 12. `/speckit.implement` — `implementation.md`, `obs12-telemetry.md`
Una raíz por proceso de pytest (`kontrol-test-almacen-<aleatorio>/{storage,backups}`) creada en `pytest_configure` y
eliminada en `pytest_unconfigure`; sondas permanentes y O06-01…20; OBS-12 con `modo_almacen`, `almacen_por_proceso` y
`almacen_fijo_legado_presente`. Producto 0.
## 13. Pruebas, mutaciones y certificación
O06-01…20 y regresiones (`directed-tests.md`), 14/14 mutaciones (`mutation-campaign.md`), SQLite 1739/0/1046 ×2
(`sqlite-full-1.md` con suspensión del equipo registrada, `sqlite-full-2.md` NORMAL), PostgreSQL 2759/0/26 (`postgres-full.md`),
E2E 284/0/0 (`global-e2e.md`), OpenAPI 544/533/11 (`openapi.md`), OBS-12 (`obs12-telemetry.md`).
## 14. Analyze final, trazabilidad y convergencia
`final-analyze.md` (todo 0; trazabilidad 100 %), `traceability-matrix.md`, `convergence.md`: **CLOSED / CONVERGED 2026-10-15**.
El almacén fijo histórico `<tmp>/kontrol-test-storage` queda como legado (no se borra en este ciclo).
