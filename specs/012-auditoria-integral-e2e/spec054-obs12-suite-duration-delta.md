# SPEC 054 · Delta dirigida — OBS-12 · SUITE-DURATION-VARIABILITY

Dueña: 054 (QA, arnés y certificación; carpeta `specs/012-auditoria-integral-e2e`). Fecha: 2026-10-15. HEAD de partida
`8d140ba`. Decisión `[X] OBS-12` ratificada (ciclo de **medición, atribución y observabilidad del QA**; no de optimización).
Evidencia en `evidence/obs12-suite-duration/`. Producto 0, pruebas de producto 0 (salvo etapa 2 justificada), reloj 0,
timeouts 0, `busy_timeout` 0, sleep/retry/skip/xfail 0, reorden 0, paralelismo 0, analizador sin debilitar. OBS-11 cerrada.

## 1. Checkpoint — `checkpoint.md`
`FIXED_HARNESS_STORAGE` = `<tmp>/kontrol-test-storage` (no es residuo). Residuos efímeros 0.

## 2. `/speckit.specify` — SOLICITUD/CAMBIO
Caracterizar por qué una SQLite completa tardó ≈ 2946 s cuando las comparables tardan ≈ 587–610 s, y fijar un **contrato de
medición reproducible** que distinga duración normal de anomalía de anfitrión sin cambiar producto ni añadir esperas.
Requisitos FR-O12-001…035 (del encargo): duración monotónica (001–003), perfil por prueba (004–005), telemetría de
anfitrión saneada (006–009), nada de timeouts/busy_timeout/sleep/retry/skip/xfail/reorden/paralelismo/producto/reloj/
analizador (010–020), coste del analizador sin comparación inválida (021–023), inventario de esperas (024–026),
clasificación con UNKNOWN 0 (027–028), cierre por caracterización (029), STOP ante defecto de producto o decisión material
(030–032), MASTER57/SPEC057/NEXT sin cambio (033–035).

## 3. `/speckit.clarify`
| Paso | Resultado | Evidencia |
|---|---|---|
| Histórico | 9 corridas inventariadas; 2946 s = único atípico, `HOST_TELEMETRY = UNAVAILABLE` en todas | `historical-duration-inventory.md` |
| Órdenes canónicas | SQLite/PG/E2E, `addopts=-q`, sin caché, precondición del analizador, ciclo de bases | `canonical-commands.md` |
| Esperas | sin espera incondicional larga en el camino verde; techos de hilos/subprocesos; `busy_timeout` 5 s por defecto sin fijar; sondeos de 50–200 ms | `wait-timeout-inventory.md` |
| Analizador | un proceso `clamscan` por análisis, carga de firmas por proceso; ≈ 7–8 s por análisis; preflight 14,5 s; aprovisionamiento fuera de la suite; comparación con analizador apagado **inválida** | `scanner-cost-model.md` |
| Métricas | `/proc/loadavg`, `/proc/meminfo`, `/proc/stat`, `/proc/diskstats`, `getrusage`; sin `/usr/bin/time`; sin red | `system-metrics-capability.md` |
| pytest | 9.0.3; `--durations=0` con setup/call/teardown; necesita resumen visible (`-o addopts= -q`) | `canonical-commands.md` |
| Clasificación | 15 clases del encargo; `CLOCK` no se usa (OBS-11 cerrada); UNKNOWN 0 al converger | `measurement-plan.md` |

## 4. `/speckit.plan` — W01…W28
W01–W09 (reconciliación, dueña, inventarios, diseño del muestreador y del perfil) hechos en clarify; W10–W11 corridas
instrumentadas (una por motor); W12 coste del analizador por envoltorio de medición; W13 top 30; W14–W15 correlaciones;
W16 estrategia del atípico (no se busca repitiendo suites); W17 matriz; W18 gate material; W19–W22 contrato de medición y
pruebas/mutaciones si hay código de QA; W23–W28 certificación, analyze, trazabilidad, convergencia.

## 5. CONSTITUTION GATE (pre-diagnóstico) — G01…G33
HEAD 8d140ba · develop · OBS-12 ratificada · dueña 054 probada (precedente: `qa/e2e_corrida.py` con `desvio_de_reloj` y
`huella_de_red` saneada) · histórico, órdenes, esperas, analizador, métricas y pytest mapeados · planes SQLite/PG listos ·
experimento del analizador semánticamente válido (envoltorio que no cambia el análisis) · producto/pruebas/reloj/timeouts/
busy_timeout/sleep/retry/skip/xfail/reorden/paralelismo/analizador 0 · BLOCKER = CRITICAL = CONTRADICTIONS = OWNER
CONFLICT = 0 · huérfanos 0 · MATERIAL OQ 0 · UNKNOWN 0 en el alcance planificado · trazabilidad 100 % ·
`DIAGNOSTIC_PLAN_READY = YES`.

## 6. `/speckit.checklist`
Todas las casillas del encargo marcadas con la evidencia de §3 y §5 (histórico, almacén fijo distinguido, órdenes, preflight,
esperas, busy timeouts, hilos, coste del analizador, `--durations`, métricas, saneado, corridas planificadas, experimento
válido, top 30, correlación de carga, prohibiciones a 0, MATERIAL OQ 0, UNKNOWN 0, trazabilidad 100 %).

## 7. `/speckit.tasks`
| ID | Requisito | Ejecutor / modelo | Sensible | Egress | Ficheros | Acción | DONE_WHEN | Prueba / mutación | Evidencia |
|---|---|---|---|---|---|---|---|---|---|
| T01 | FR-001…005, 024 | CLAUDE / n-a | no | n-a | ninguno | inventarios histórico, órdenes, esperas | tablas completas sin invención | — | clarify |
| T02 | FR-006…009, 021–023 | CLAUDE / n-a | no | n-a | ninguno | capacidad de métricas y modelo del analizador | fuentes probadas | — | clarify |
| T03 | FR-001…009 | CLAUDE / n-a | no | n-a | `<scratch>/o12/*` (fuera del repo) | diseño del plan de medición e instrumentación externa | muestreador y envoltorio probados | — | `measurement-plan.md` |
| T04 | FR-003…007 | CLAUDE / n-a | no | n-a | ninguno | SQLite completa instrumentada | perfil + telemetría + rusage | — | `sqlite-profile.md`, `top30-sqlite.md`, `host-load-sqlite.md` |
| T05 | ídem | CLAUDE / n-a | no | n-a | ninguno | PostgreSQL completa instrumentada | ídem | — | `postgres-profile.md`, `top30-postgres.md`, `host-load-postgres.md` |
| T06 | FR-027…030 | CLAUDE / n-a | no | n-a | ninguno | atribución y gate material | UNKNOWN 0; verdicto A–E | — | `classification-matrix.md`, `historical-outlier-analysis.md`, `implementation-decision.md` |
| T07 | FR-001…009, 029 | CLAUDE / n-a (CLAUDE_ONLY: diseño del contrato del arnés) | no | n-a | `qa/…`, `resources/backend/tests/test_…` (solo si la etapa 2 lo justifica) | contrato de medición del QA | O12-01…20 verdes; ≥ 10 mutaciones | directas + mutaciones | `qa-measurement-contract.md`, `directed-tests.md`, `mutation-campaign.md` |
| T08 | FR-033…035 | CLAUDE / n-a | no | n-a | roadmap, next-spec-decision, master | certificación y convergencia | suites 0 rojos; docs; commit; push | — | `convergence.md` |
`RETRY_MAX: 2` en todas; `DEEPSEEK CALLS = 0` (interpretación de rendimiento, esperas y arnés: CLAUDE_ONLY).

## 8. `/speckit.analyze` (pre-diagnóstico)
OBS12_SELECTED YES · SPEC054_OWNER PROVEN · HISTORICAL_TIMING MAPPED · CANONICAL_COMMANDS PROVEN · WAIT_INVENTORY COMPLETE ·
SCANNER_COST_MODEL MAPPED · SYSTEM_METRICS MAPPED · MEASUREMENT_PLAN FROZEN · SCANNER_COMPARISON_VALIDITY FROZEN ·
PRODUCT_CHANGE_AUTHORIZED NO · PRODUCT_TEST_CHANGE_AUTHORIZED NO · CLOCK/TIMEOUT/BUSY_TIMEOUT/RETRY/SLEEP/SKIP/XFAIL/
REORDER/PARALLELIZATION/SCANNER_WEAKENING 0 · BLOCKER/CRITICAL/CONTRADICTIONS/OWNER CONFLICT/huérfanos/MATERIAL OQ/
UNKNOWN 0 · TRACEABILITY 100 %. **AUTORIZACIÓN EXPRESA — ETAPA 1 consumida (solo medición).**

## 9. Etapa 1 — medición (sin cambio de fuentes; instrumentación externa al repositorio)
| Corrida | Monotónico | pytest interno | Recuentos | Analizador | Anfitrión | Evidencia |
|---|---|---|---|---|---|---|
| SQLite completa | **581,6 s** (desvío de reloj 0) | 553,7 s | 1698/1/1046 (el único fallo es el artefacto del envoltorio de medición en `test_clam_04_05_06…`; funcionalmente 1699/0/1046) | 48 análisis · 307 s (53 %) · 6,39 s de mediana | load1 1,9 (máx 2,5) en 12 CPU · CPU 12 % · MemAvailable mín 2,1 GB · E/S mínima | `sqlite-profile.md`, `top30-sqlite.md`, `host-load-sqlite.md` |
| PostgreSQL completa | **1356,5 s** | 1324,5 s | 2718/1/26 (mismo artefacto; funcionalmente 2719/0/26) | 80 análisis · 511 s (38 %) · 6,38 s | load1 1,8 (máx 3,0) · CPU 13,5 % · MemAvailable mín 2,0 GB · swap del escritorio 5,2 GB sin paginación efectiva | `postgres-profile.md`, `top30-postgres.md`, `host-load-postgres.md` |
Coste del analizador (`scanner-cost-experiment.md`): estable, 6,4 s por proceso `clamscan` (carga de firmas), legítimo;
`SCANNER_OFF_COMPARISON_INVALID = YES`. Esperas (`wait-timeout-inventory.md` + perfil): ningún techo consumido; `busy_timeout`
nunca alcanzado. Clasificación (`classification-matrix.md`): SCANNER_COST 55 % / 39 %, PROCESS_STARTUP 15 %, esperas
legítimas < 2 %, coste estructural PGLIFE ≈ 330 s en PostgreSQL, resto repartido; **UNKNOWN = 0; ACTIVE_PATHOLOGICAL_DELAY = 0**.
Atípico histórico (`historical-outlier-analysis.md`): `HISTORICAL_OUTLIER_WITH_INSUFFICIENT_HOST_TELEMETRY` (`NOT_REPRODUCED`;
carga, presión de memoria o medida con reloj de pared sospechadas, ninguna demostrable; nada inventado).

## 10. Gate material y etapa 2 — `implementation-decision.md`
Salidas: D (producto) NO · C (espera defectuosa) NO · E (coste del analizador estable) SÍ, se registra · A (atípico) no
reproducido, telemetría insuficiente · **B (brecha de observabilidad) SÍ** → `PRODUCT/TEST_SEMANTICS/TIMEOUT/SCANNER/
PARALLELIZATION_CHANGE_REQUIRED = NO` → **AUTORIZACIÓN EXPRESA — ETAPA 2 consumida** (solo observabilidad del QA).

## 11. `/speckit.implement` — contrato de medición (`qa-measurement-contract.md`)
- `qa/suite_tiempos.py` (nuevo): envuelve la orden canónica con `--durations=0`, duración monotónica + desvío de reloj
  (`e2e_corrida.desvio_de_reloj`), recuentos y rc de pytest (el rc de la herramienta **es** el de pytest), metadatos del
  analizador (`clamav_qa.asegurar`/`variables`), top 30 por prueba, muestreador de anfitrión saneado (`/proc`: carga,
  memoria, swap, paginación, CPU, disco), `getrusage`, residuos efímeros (almacén fijo aparte), indicador de anomalía no
  bloqueante sin umbral duro; evidencia en `qa/backend-runs/<run_id>/`.
- `resources/backend/tests/test_suite_tiempos_qa.py` (nuevo): O12-01…20 con dobles.
- `.gitignore`: `qa/backend-runs/`. `.claude/CLAUDE.md`: orden canónica de certificación backend con telemetría.
- Producto 0 · pruebas de producto 0 · `conftest.py` 0 · reloj 0 · timeouts 0 · `busy_timeout` 0 · sleep/retry/skip/xfail 0 ·
  reorden 0 · paralelismo 0 · analizador sin debilitar. `DEEPSEEK CALLS = 0` (CLAUDE_ONLY: diseño del arnés).

## 12. Pruebas, mutaciones y certificación
Dirigidas 20/20 (`directed-tests.md`); mutaciones 13/13 (`mutation-campaign.md`); certificación por la propia herramienta
con analizador real: `sqlite-certification-1.md`, `sqlite-certification-2.md`, `postgres-certification.md`; E2E canónica
`global-e2e.md`; OpenAPI `openapi.md`.
