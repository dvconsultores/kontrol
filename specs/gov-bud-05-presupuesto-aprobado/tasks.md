# Tasks · BUD-05

Tope: 8 llamadas (objetivo 3–5), máximo 2 reintentos por subproblema real, agrupadas por frontera semántica.

| Id | Tarea | EXECUTOR | MODEL | SECURITY_SENSITIVE | EGRESS_SAFE | RETRY_MAX | FILES | TEST | DONE_WHEN |
|---|---|---|---|---|---|---|---|---|---|
| T001 | Reconciliación, recuento del universo de compuertas, descubrimiento, decisión de la dueña, Spec, plan y gate | CLAUDE | n-a | no | n-a | 0 | specs/gov-bud-05-presupuesto-aprobado/* | recuento | CONSTITUTION_GATE PASS |
| T002 | C1: modelos, migración 0109, historia, catálogo (+8), esquemas, API, main y fijaciones de cabeza y catálogo | DEEPSEEK | deepseek-v4-pro | sí | sí | 2 | models.py, 0109, audit_catalog_entries.py, schemas_presupuesto_aprobado.py, api_presupuesto_aprobado.py, main.py, 4 pruebas fijadas | alembic; import | verde |
| T003 | C2: service_presupuesto_aprobado.py, cuadre en aprobar/reconducir, fotografía y guardas IN_USE/CONFLICT | DEEPSEEK | deepseek-v4-pro | sí | sí | 2 | service_presupuesto_aprobado.py, service_presupuesto.py, service_presupuesto_fuentes.py | ruff, mypy | contrato |
| T004 | C3: pruebas PG de AC-01..07 | DEEPSEEK | deepseek-v4-pro | sí | sí | 2 | tests/test_gov_bud05.py | pytest PG | verde |
| T005 | C4: frontend y Vitest | DEEPSEEK | deepseek-v4-pro | no | sí | 2 | src/modules/gobierno/presupuesto/* | tsc, eslint, vitest | verde |
| T006 | C5: E2E | DEEPSEEK | deepseek-v4-pro | no | sí | 2 | e2e/gobierno-presupuesto-aprobado.spec.ts | E2E sin reintentos | AC-08 |
| T007 | Integración, suites una vez, publicación, UAT, matrices y cierre | CLAUDE | n-a | no | n-a | 0 | evidence, docs | suites, humo | HEAD == origin/develop |

## Estado (2026-11-14)

T001–T006 ✔ (llamadas y reintentos en `evidence/ATTEMPT_LOG.md`). T007 ✔ (evidencia en `evidence/CIERRE.md`).
