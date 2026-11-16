# Tasks · CNT-09

| ID | Tarea | EXECUTOR | MODEL | SECURITY_SENSITIVE | EGRESS_SAFE | RETRY_MAX | FILES | TEST | DONE_WHEN |
|---|---|---|---|---|---|---|---|---|---|
| T001 | Reconciliación, fuentes, spec, plan y gate | CLAUDE | n-a | no | n-a | 0 | FUENTES, spec, plan, tasks | — | gate PASS |
| T002 | D1: modelo, migración 0120, servicio, API, registro, catálogo, mensajes, auditoría y fijaciones | DEEPSEEK | deepseek-v4-pro | no | sí | 2 | models.py, 0120, service_contratos_alertas.py, api_contratos_alertas.py, schemas, main.py, registry.py, catalogo.py, messages.py, audit_catalog_entries.py, 4 fijaciones | alembic, ruff, mypy, fijaciones | verde |
| T003 | D2: pruebas PG (C09-01..19) | DEEPSEEK | deepseek-v4-pro | no | sí | 2 | tests/test_gov_cnt09_alertas.py | pytest PG | verde |
| T004 | D3: frontend y Vitest | DEEPSEEK | deepseek-v4-pro | no | sí | 2 | notificaciones/api.ts, es.ts, AlertasPage, AlertasContrato, AlertasPoliticaPage, ContratoPage, router, pantallas, Sidebar, pruebas | tsc, eslint, vitest | verde |
| T005 | D4: E2E del sponsor | DEEPSEEK | deepseek-v4-pro | no | sí | 2 | e2e/gobierno-contratos.spec.ts | E2E | 1/1 sin reintentos |
| T006 | Fixtures OpenAPI, convergencia, PG completa una vez, matrices, publicación, UAT y cierre | CLAUDE | n-a | no | n-a | 0 | evidence, matrices | suites, humo | HEAD == origin |
