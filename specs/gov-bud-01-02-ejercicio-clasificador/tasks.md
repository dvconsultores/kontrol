# Tasks · BUD-01 + BUD-02

Tope del ciclo: 8 llamadas (objetivo 2-4), 2 reintentos por subproblema, 1 llamada reservada para integrar con P2.

| Id | Tarea | EXECUTOR | MODEL | SECURITY_SENSITIVE | EGRESS_SAFE | RETRY_MAX | FILES | TEST | DONE_WHEN |
|---|---|---|---|---|---|---|---|---|---|
| T001 ✔ | Reconciliación, decisión D-GOV-02 registrada, Spec, plan, gate | CLAUDE | n-a | no | n-a | 0 | specs/gov-bud-decision-02/OWNER_DECISION.md, specs/gov-bud-01-02-ejercicio-clasificador/* | revisión | CONSTITUTION_GATE PASS |
| T002 ✔ | B1 · capa de datos y registros: migración 0106, modelos, permisos, MFA, ResourceKind (+ cardinalidad y semilla N9), catálogo de auditoría (+ conteo 509), mapeo en CTL-04 | DEEPSEEK | deepseek-v4-pro | sí (permisos, MFA, aislamiento) | sí | 2 | alembic/versions/0106_gov_bud01_ejercicio.py, models.py, setup/api.py, mfa_policy.py, documents/resources.py, tests/test_n9_resourcekinds.py, tests/n9_resource_seeds.py, audit_catalog_entries.py, tests/test_audit_catalog_backup.py, service_auditoria.py | alembic up/down/up en PG; catálogo; N9 | todo verde |
| T003 ✔ | B2 · servicio, esquemas, API, include en main y pruebas PG de AC-01..09 | DEEPSEEK | deepseek-v4-pro | sí | sí | 2 | service_presupuesto.py, schemas_presupuesto.py, api_presupuesto.py, main.py, tests/test_gov_bud01_ejercicio.py | pytest PG; ruff; mypy en la línea base | AC-01..09 verdes |
| T004 ✔ | F1 · frontend: lista, detalle con secciones, router, Sidebar, pantallas, Vitest | DEEPSEEK | deepseek-v4-pro | no | sí | 2 | src/modules/gobierno/presupuesto/*, router, Sidebar, pantallas | tsc, eslint, vitest con Node 22 | verde |
| T005 ✔ | F2 · E2E y humo UAT | DEEPSEEK | deepseek-v4-pro | no | sí | 2 | e2e/gobierno-presupuesto.spec.ts, e2e/uat-humo-gobierno.spec.ts | E2E sin reintentos, 2/2 con 4 workers | AC-10 |
| T006 ✔ | Integración: fixtures, suites completas una vez, alembic fresh/upgrade/downgrade, publicación, UAT, matrices, cierre | CLAUDE | n-a | no | n-a | 0 | evidence, docs/roadmap | suites, humo | HEAD == origin/develop, UAT accesible |
