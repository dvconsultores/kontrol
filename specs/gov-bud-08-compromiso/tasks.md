# Tasks · BUD-08

Tope: 8 llamadas (objetivo 3–5), máximo 2 reintentos por subproblema real. Sin excepción heredada.

| Id | Tarea | EXECUTOR | MODEL | SECURITY_SENSITIVE | EGRESS_SAFE | RETRY_MAX | FILES | TEST | DONE_WHEN |
|---|---|---|---|---|---|---|---|---|---|
| T001 | Reconciliación, línea base, descubrimiento, Spec, plan, gate y vectores | CLAUDE | n-a | no | n-a | 0 | specs/gov-bud-08-* | línea base | gate PASS |
| T002 | C1: modelos y triggers, migración 0113, permiso commit, auditoría, esquemas, router y fijaciones | DEEPSEEK | deepseek-v4-pro | sí | sí | 2 | models, 0113, setup/api, mfa_policy, audit_catalog_entries, schemas/api_presupuesto_compromiso, main, fijaciones | alembic, ruff | verde |
| T003 | C2: service_presupuesto_compromiso y cambios en service_presupuesto_certificacion | DEEPSEEK | deepseek-v4-pro | sí | sí | 2 | service_presupuesto_compromiso.py, service_presupuesto_certificacion.py | ruff, mypy | vectores |
| T004 | C3: pruebas PG con los vectores A–J, concurrencia, SoD, límite, soporte, inmutabilidad y aislamiento | DEEPSEEK | deepseek-v4-pro | sí | sí | 2 | tests/test_gov_bud08.py | pytest PG | verde |
| T005 | C4: pantalla Compromisos, columnas de BUD-06 y Vitest | DEEPSEEK | deepseek-v4-pro | no | sí | 2 | src/modules/gobierno/presupuesto/* | tsc, eslint, vitest | verde |
| T006 | C5: E2E | DEEPSEEK | deepseek-v4-pro | no | sí | 2 | e2e/gobierno-presupuesto-compromiso.spec.ts | E2E | B08-22 |
| T007 | Integración, suites una vez, publicación, UAT, matrices y cierre | CLAUDE | n-a | no | n-a | 0 | evidence, docs | suites, humo | HEAD == origin |

## Estado (2026-11-15)

T001–T007 completas. Evidencia: `evidence/CIERRE.md`, `evidence/ATTEMPT_LOG.md` y `evidence/OWNER_UAT_CARD.md`.

La PG completa detectó un defecto de aislamiento: las 4 rutas GET comprobaban la licencia del módulo antes que la empresa. Lo corrigió la llamada C9, autorizada por la dueña, y se reverificó con test_iso_barridos más BUD-08 y BUD-06: 26/26.
