# Tasks · TRE-09

| ID | Tarea | EXECUTOR | MODEL | SECURITY_SENSITIVE | EGRESS_SAFE | RETRY_MAX | FILES | TEST | DONE_WHEN |
|---|---|---|---|---|---|---|---|---|---|
| T001 | Reconciliación, arqueología, Spec, plan, gate y vectores | CLAUDE | n-a | no | n-a | 0 | specs/gov-tre-09-* | — | gate PASS |
| T002 | C1: monedas, modelo, 0114, capacidades, MFA, auditoría, ResourceKind, esquemas, router y fijaciones | DEEPSEEK | deepseek-v4-pro | sí | sí | 2 | models, 0114, monedas, setup/api, mfa_policy, audit_catalog_entries, resources, schemas_tasas, api_tasas, main, fijaciones | alembic, ruff | verde |
| T003 | C2: service_tasas, consumidor BUD-08 con vista previa, normalización en BUD-01 y BUD-06 | DEEPSEEK | deepseek-v4-pro | sí | sí | 2 | service_tasas, service/api/schemas compromiso, service_presupuesto, service_presupuesto_certificacion | ruff, mypy | vectores |
| T004 | C3: pruebas PG de los vectores A–J, ciclo de vida, maker-checker, evidencia, concurrencia, aislamiento, inmutabilidad y auditoría; ajuste del vector G–I de BUD-08 | DEEPSEEK | deepseek-v4-pro | sí | sí | 2 | tests/test_gov_tre09.py, tests/test_gov_bud08.py | pytest PG con iso | verde |
| T005 | C4: pantalla Tasas oficiales, menú, conversión en Compromisos y Vitest | DEEPSEEK | deepseek-v4-pro | no | sí | 2 | src/modules/gobierno/tesoreria/tasas/*, presupuesto/*, router, Sidebar, pantallas | tsc, eslint, vitest | verde |
| T006 | C5: E2E y pantalla en el humo UAT | DEEPSEEK | deepseek-v4-pro | no | sí | 2 | e2e/gobierno-tasas-oficiales.spec.ts, e2e/uat-humo-gobierno.spec.ts | E2E | T09-18 |
| T007 | Integración, suites una vez, publicación, UAT, matrices y cierre | CLAUDE | n-a | no | n-a | 0 | evidence, docs | suites, humo | HEAD == origin |

## Estado (2026-11-15)

| ID | Estado | Evidencia |
|---|---|---|
| T001 | COMPLETE | spec.md, plan.md (gate PASS) |
| T002 | COMPLETE | C1 + C6 (reintento); alembic ida/vuelta |
| T003 | COMPLETE | C2 + C6; C11 (reintento de concurrencia) |
| T004 | COMPLETE | C3 + C7 + C8 + C9; PG 25/25 |
| T005 | COMPLETE | C4 + C8 + C9 + C10; Vitest 2047/2047 |
| T006 | COMPLETE | C5 + C9 + C11; E2E 1/1, Axe en 3 anchos |
| T007 | COMPLETE | PG completa 5525/36/18 sin fallos nuevos; evidence/CIERRE.md |
