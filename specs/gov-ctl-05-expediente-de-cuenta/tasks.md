# Tasks · CTL-05

| Id | Tarea | EXECUTOR | MODEL | SECURITY_SENSITIVE | EGRESS_SAFE | RETRY_MAX | FILES | TEST | DONE_WHEN |
|---|---|---|---|---|---|---|---|---|---|
| T001 | Fuentes, decisiones, spec y plan, con la compuerta | CLAUDE | n-a | no | n-a | 0 | specs/gov-ctl-05-expediente-de-cuenta/* | revisión | Compuerta PASS |
| T002 ✔ | C1, backend: modelo y disparadores, migración 0098, servicio, esquemas, API, cableado (catálogo, MFA, setup, PROCESOS, main) y pruebas PG | DEEPSEEK | deepseek-v4-pro | sí (permisos, aislamiento) | sí | 2 | models.py, alembic 0098, service_rendicion.py, schemas_rendicion.py, api_rendicion.py, main.py, setup/api.py, mfa_policy.py, audit_catalog_entries.py, service_auditoria.py, tests/test_gov_ctl05_rendicion.py y las pruebas transversales | pytest PG CTL-05 y transversales; ruff; mypy | Verde en PG; OpenAPI solo con altas |
| T003 ✔ | C2, frontend: menú, pantallas, API cliente, responsive y Vitest | DEEPSEEK | deepseek-v4-pro | no | sí | 2 | src/modules/gobierno/rendicion/*, api.ts, pantallas.ts, rutas y menú | tsc, eslint, vitest dirigido, build | Verde |
| T004 ✔ | C3, E2E de usuario con 3 negativas, Axe y responsive; pantalla en el humo UAT | DEEPSEEK | deepseek-v4-pro | no | sí | 2 | e2e/gobierno-rendicion.spec.ts, e2e/uat-humo-gobierno.spec.ts | qa/e2e-run.py --con-analizador | 1/1 PASS |
| T005 ✔ | Integración: fetch, merge, Alembic, fixtures, OpenAPI, commit, push, UAT, tarjeta y matrices | CLAUDE | n-a | no | n-a | 0 | fixtures, docs/roadmap | diff de OpenAPI, humo | HEAD == origin/develop |
