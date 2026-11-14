# Tasks · BUD-03 + BUD-04

Tope: 8 llamadas (objetivo 3-5), 2 reintentos por causa real, agrupadas por frontera semántica.

| Id | Tarea | EXECUTOR | MODEL | SECURITY_SENSITIVE | EGRESS_SAFE | RETRY_MAX | FILES | TEST | DONE_WHEN |
|---|---|---|---|---|---|---|---|---|---|
| T001 | Reconciliación, reclasificación de BUD-02 REPORTING, recuento, Spec, plan, gate | CLAUDE | n-a | no | n-a | 0 | specs/gov-bud-03-04-plan-fuentes/*, docs/roadmap | recuento | CONSTITUTION_GATE PASS |
| T002 | C1 datos: modelos, migración 0108, catálogo (+13), fijaciones de cabeza | DEEPSEEK | deepseek-v4-pro | sí | sí | 2 | models.py, 0108, audit_catalog_entries.py, 4 pruebas fijadas | alembic up/down/up; catálogo | verde |
| T003 | C2 servicios, esquemas, API y fotografía | DEEPSEEK | deepseek-v4-pro | sí | sí | 2 | service_presupuesto_plan.py, service_presupuesto_fuentes.py, schemas_presupuesto_plan.py, api_presupuesto_plan.py, main.py, service_presupuesto.py | ruff, mypy | contrato |
| T004 | C3 pruebas PG de AC-01..07 | DEEPSEEK | deepseek-v4-pro | sí | sí | 2 | tests/test_gov_bud03_04.py | pytest PG | verde |
| T005 | C4 frontend: PlanEjercicio, FuentesEjercicio, integración en el detalle y Vitest | DEEPSEEK | deepseek-v4-pro | no | sí | 2 | src/modules/gobierno/presupuesto/* | tsc, eslint, vitest | verde |
| T006 | C5 E2E | DEEPSEEK | deepseek-v4-pro | no | sí | 2 | e2e/gobierno-presupuesto-plan-fuentes.spec.ts | E2E sin reintentos | AC-08 |
| T007 | Integración, suites una vez, publicación, UAT, matrices, cierre | CLAUDE | n-a | no | n-a | 0 | evidence, docs | suites, humo | HEAD == origin/develop |

## Estado (2026-11-14)

T001–T007 ✔. Evidencia en `evidence/CIERRE.md`; llamadas e intentos en `evidence/ATTEMPT_LOG.md`.
