# Tasks · CNT-04

| ID | Tarea | EXECUTOR | MODEL | SECURITY_SENSITIVE | EGRESS_SAFE | RETRY_MAX | FILES | TEST | DONE_WHEN |
|---|---|---|---|---|---|---|---|---|---|
| T001 | Reconciliación, arqueología, fuentes, decisiones OD-CNT04-01/02, spec, plan y gate | CLAUDE | n-a | no | n-a | 0 | FUENTES, spec, plan, tasks | — | gate PASS |
| T002 | C1 backend: modelo y guard, migración 0117, servicio, API y cableado (main, setup, mfa, auditoría, SoD, fijaciones) | DEEPSEEK | deepseek-v4-pro | sí | sí | 2 | models.py, 0117, service_contratos_supervision.py, api_contratos_supervision.py, main.py, setup/api.py, mfa_policy.py, audit_catalog_entries.py, service_sod.py, 3 fijaciones de cabeza y 3 de recuento | alembic, ruff, mypy, pytest de fijaciones | verde |
| T003 | C2 pruebas PG de CNT-04 | DEEPSEEK | deepseek-v4-pro | sí | sí | 2 | tests/test_gov_cnt04_supervisor.py | pytest PG | verde |
| T004 | C3 sección de supervisión y Vitest | DEEPSEEK | deepseek-v4-pro | no | sí | 2 | SupervisionContrato(.test).tsx, api.ts, ContratoPage.tsx | tsc, eslint, vitest | verde |
| T005 | C4 E2E al final del recorrido de CNT-01 | DEEPSEEK | deepseek-v4-pro | no | sí | 2 | e2e/gobierno-contratos.spec.ts | E2E | 1/1 sin reintentos |
| T006 | Fixtures OpenAPI, convergencia, PG completa una vez, matrices, publicación, UAT y cierre | CLAUDE | n-a | no | n-a | 0 | evidence, matrices | suites, humo | HEAD == origin |

Estado (2026-11-15): T001–T005 completas. T002 C1+C2+C4a+C6+C7; T003 C2+C4a+C6+C7+C8; T004 C3+C4b+C6+C7+C8+C9+C10; T005 C7+C8+C9. Hubo 10 llamadas (9.ª y 10.ª autorizadas por la dueña).
Convergencia: convergido; FR-01..16 y C04-01..18 cubiertos (evidence/TRACEABILITY.md). T006: PG completa sin fallos nuevos (36 = línea base); publicación y UAT en evidence/CIERRE.md.
