# Tasks · CNT-03

| ID | Tarea | EXECUTOR | MODEL | SECURITY_SENSITIVE | EGRESS_SAFE | RETRY_MAX | FILES | TEST | DONE_WHEN |
|---|---|---|---|---|---|---|---|---|---|
| T001 | Reconciliación, fuentes, decisiones OD-CNT03-01..04, spec, plan y gate | CLAUDE | n-a | no | n-a | 0 | FUENTES, spec, plan, tasks | — | gate PASS |
| T002 | C1: 8 modelos y triggers, migración 0118, permiso, MFA, SoD, auditoría y fijaciones | DEEPSEEK | deepseek-v4-pro | sí | sí | 2 | models.py, 0118, setup/api.py, mfa_policy.py, service_sod.py, audit_catalog_entries.py, 7 fijaciones | alembic up/down, ruff, mypy, fijaciones | verde |
| T003 | C2: servicio, esquemas, API y main | DEEPSEEK | deepseek-v4-pro | sí | sí | 2 | service_contratos_ejecucion.py, schemas_contratos_ejecucion.py, api_contratos_ejecucion.py, main.py | ruff, mypy, sonda PG | verde |
| T004 | C3: pruebas PG (C03-01..19) | DEEPSEEK | deepseek-v4-pro | sí | sí | 2 | tests/test_gov_cnt03_ejecucion.py | pytest PG | verde |
| T005 | C4: frontend (api, página, enlace, ruta) y Vitest | DEEPSEEK | deepseek-v4-pro | no | sí | 2 | contratos/api.ts, EjecucionContratoPage(.test).tsx, ContratoPage.tsx, router.tsx | tsc, eslint, vitest | verde |
| T006 | C5: E2E del sponsor (16 pasos, 1280/390/320, Axe) | DEEPSEEK | deepseek-v4-pro | no | sí | 2 | e2e/gobierno-contratos.spec.ts | E2E | 1/1 sin reintentos |
| T007 | Fixtures OpenAPI, convergencia, PG completa una vez, matrices, publicación, UAT local y cierre | CLAUDE | n-a | no | n-a | 0 | evidence, matrices | suites, humo | HEAD == origin | ✔

**Estado (2026-11-15):** T001–T007 completas. PG completa: 0 fallos nuevos. Detalle en evidence/CIERRE.md.
