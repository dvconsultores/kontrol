# Tasks · BUD-06

Tope: 8 llamadas (objetivo 3–5), máximo 2 reintentos por subproblema real.

| Id | Tarea | EXECUTOR | MODEL | SECURITY_SENSITIVE | EGRESS_SAFE | RETRY_MAX | FILES | TEST | DONE_WHEN |
|---|---|---|---|---|---|---|---|---|---|
| T001 | Reconciliación, línea base, descubrimiento, Spec, plan, gate y vectores | CLAUDE | n-a | no | n-a | 0 | specs/gov-bud-06-* | línea base | gate PASS |
| T002 | C1: modelo, migración 0112, permiso certify (catálogo, MFA, siembra), catálogo de auditoría (+2), esquemas, router y fijaciones | DEEPSEEK | deepseek-v4-pro | sí | sí | 2 | models, 0112, setup/api, mfa_policy, audit_catalog_entries, schemas/api_presupuesto_certificacion, main, fijaciones | alembic | verde |
| T003 | C2: service_presupuesto_certificacion (fórmula, emisión con bloqueos, PDF y almacenamiento, anulación, documento, opciones de firmante y expediente) | DEEPSEEK | deepseek-v4-pro | sí | sí | 2 | service_presupuesto_certificacion.py | ruff, mypy | vectores |
| T004 | C3: pruebas PG (vectores A–F, concurrencia, estados, autoridad, MFA, documento) | DEEPSEEK | deepseek-v4-pro | sí | sí | 2 | tests/test_gov_bud06.py | pytest PG | verde |
| T005 | C4: pantalla y Vitest | DEEPSEEK | deepseek-v4-pro | no | sí | 2 | src/modules/gobierno/presupuesto/* | tsc, eslint, vitest | verde |
| T006 | C5: E2E | DEEPSEEK | deepseek-v4-pro | no | sí | 2 | e2e/gobierno-presupuesto-certificacion.spec.ts | E2E | B06-18 |
| T007 | Integración, suites una vez, publicación, UAT, matrices y cierre | CLAUDE | n-a | no | n-a | 0 | evidence, docs | suites, humo | HEAD == origin |

## Estado (2026-11-14)

T001–T007 completadas. Evidencia en `evidence/CIERRE.md` y `evidence/ATTEMPT_LOG.md`: 9 llamadas, la 9.ª con autorización expresa de la dueña.
