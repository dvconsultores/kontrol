# Tasks · GOV-BUD-09 Causado

Todas las tareas DEEPSEEK: `RETRY_MAX: 2` · `EGRESS_SAFE: yes` (sin secretos ni datos reales). Tope del ciclo: 8 llamadas.

| Id | Tarea | EXECUTOR | MODEL | SECURITY_SENSITIVE | FILES | TEST | DONE_WHEN |
|---|---|---|---|---|---|---|---|
| T001 | Reconciliación, arqueología, decisiones OD-BUD09-01/02, spec, plan y gate | CLAUDE | n-a | no | specs/gov-bud-09-causado/* | — | gate PASS |
| T002 | Modelos, migración 0123, catálogo CTL-01 (proceso BUD-09 + resolvedor), catálogo de auditoría, permisos (`cause`, `cause_policy`) + MFA, guarda de anulación de BUD-08 | DEEPSEEK | v4-pro | yes (permisos/MFA; diseño fijado por Claude) | models.py, alembic/versions/0123_*, service_sod.py, audit_catalog_entries.py, setup/api.py, mfa_policy.py, service_presupuesto_compromiso.py | upgrade/downgrade/upgrade; guardas de catálogo | alembic 1 cabeza; guardas en verde |
| T003 | Servicio, esquemas y API de políticas, configuración y causados (R1–R6, controles, formalizar, anular, CSV, frontera TRE-03) | DEEPSEEK | v4-pro | yes (autoridad, MFA, tenant) | service_presupuesto_causado.py, schemas_presupuesto_causado.py, api_presupuesto_causado.py, main.py | T004 | pruebas T004 en verde |
| T004 | Pruebas backend (encargo §31) + carrera en PG + inmutabilidad en PG | DEEPSEEK | v4-pro | no | tests/test_gov_bud09_*.py | pytest SQLite + PG | verde en ambos motores |
| T005 | Frontend: API, páginas Causados, detalle y Políticas; menú, router y pantallas | DEEPSEEK | v4-pro | no | src/modules/gobierno/presupuesto/causados/*, router.tsx, Sidebar.tsx, pantallas.ts | T006 | tsc/eslint |
| T006 | Vitest (encargo §33) | DEEPSEEK | v4-pro | no | *.test.tsx | vitest | verde |
| T007 | E2E `gobierno-causado` + humo UAT + inventarios | DEEPSEEK | v4-pro | no | e2e/gobierno-causado.spec.ts, e2e/uat-humo-gobierno.spec.ts | e2e-run | 1/1 |
| T008 | Auditoría, mutaciones, PG completa, OpenAPI, OWNER_UAT_CARD, matrices, DAG y cierre | CLAUDE | n-a | no | specs/…/evidence, docs/roadmap/… | — | gate §42 |

## Estado (2026-11-17)

T001–T008: COMPLETE. Evidencia en `evidence/CIERRE.md`; llamadas y auditoría en `evidence/ATTEMPT_LOG.md`. T004 se verifica en PG; en SQLite las pruebas de BUD-09 se saltan por diseño (P21).
