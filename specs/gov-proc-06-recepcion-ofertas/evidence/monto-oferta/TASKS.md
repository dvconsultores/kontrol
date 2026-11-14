# OMA · Tareas, clasificación y separación de frentes

## Separación P1 / P2

- **P1_VERTICAL:** BUD-05, sin publicar.
- **P2_VERTICAL:** PROC06_MONTO_OFERTA.
- **EXPECTED_OVERLAP:** 0. BUD-05 vive en presupuesto (`service_presupuesto*`, `gov_budget_*`); OMA vive en contrataciones.

| SHARED_FILE | WHY_SHARED | SEMANTIC_COLLISION_RISK | MERGE_STRATEGY |
|---|---|---|---|
| `models.py` | Modelo nuevo al final | Bajo: solo adición | Fusión ordinaria |
| `alembic/versions/` | Migración 0110 | Medio: P1 podría publicar 0110 | Reencadenar la de P2 detrás de la de P1, sin tocar la publicada |
| `setup/api.py`, `mfa_policy.py`, catálogo de auditoría | Permiso y eventos nuevos | Bajo: una línea cada uno | Fusión ordinaria; recontar si P1 añade algo |
| Pruebas de recuento y de cabeza (catálogo, delegación, MFA, 3 de cabeza) | Literales | Medio: P1 también los mueve | Recalcular tras la fusión |
| Matrices de Gobierno | Estado de OBS-PROC08-MONTO-01, PROC-09 y REP-03 | Bajo: filas distintas | Fusión ordinaria; recontar |
| Fixtures OpenAPI y operaciones | Ruta nueva | Bajo | Regenerar con `qa/fixtures_de_frontend.py` |

## Tareas

| Tarea | Qué | EXECUTOR | MODEL | SECURITY_SENSITIVE | EGRESS_SAFE | RETRY_MAX | FILES | TEST | DONE_WHEN |
|---|---|---|---|---|---|---|---|---|---|
| T001 | Arqueología, delta, decisiones, gate, plan y briefs | CLAUDE | n-a | NO | n-a | n-a | delta y evidencia | — | Gate PASS |
| T002 | Backend núcleo: modelo, 0110, servicio, esquemas, API, registros y recuentos | DEEPSEEK | deepseek-v4-pro | YES (permiso diseñado por Claude) | YES | 2 | 15 ficheros (brief A) | ruff, mypy, Alembic y n10 | Contrato del brief A |
| T003 | Consumidores: PROC-10 (moneda y monto), REP-03 (monto y CSV), PROC-08 (monto por oferta) y ajuste de las pruebas existentes de REP-03 | DEEPSEEK | deepseek-v4-pro | NO (fórmula fijada por Claude en OMA-10 y OMA-11) | YES | 2 | `service_garantias.py`, `service_reporte_contrataciones.py`, `service_decision.py`, `test_gov_rep03_contrataciones.py` | Pruebas de PROC-10 y REP-03 | OMA-09..11 |
| T004 | Pruebas de backend OMA-01..14 | DEEPSEEK | deepseek-v4-pro | NO | YES | 2 | `tests/test_gov_proc06_montos.py` | PG | Todas pasan y las mutaciones mueren |
| T005 | Frontend: `OfertaMonto.tsx`, ficha de la oferta, decisión, reporte y Vitest | DEEPSEEK | deepseek-v4-pro | NO | YES | 2 | `contrataciones/*` | Vitest, typecheck y lint | SCREEN_CONTRACT |
| T006 | E2E del monto (declarar, corregir, consumidores) con Axe a 1280, 390 y 320, más el ajuste de la E2E de REP-03 | DEEPSEEK | deepseek-v4-pro | NO | YES | 2 | `e2e/gobierno-monto-oferta.spec.ts`, `e2e/gobierno-reporte-contrataciones.spec.ts` | Playwright | PASS |
| T007 | Auditoría, QA, matrices, UAT, cierre y publicación | CLAUDE | n-a | — | n-a | n-a | — | QA final | Informe |

Gate previo a delegar: BLOCKER = CRITICAL = CONTRADICTIONS = OWNER CONFLICT = 0; MATERIAL OQ = 0 (OQ-OMA-01 y 02 se declaran sin construir); UNKNOWN = 0.
