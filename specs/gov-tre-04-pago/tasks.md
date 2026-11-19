# Tareas · GOV-TRE-04

| ID | Tarea | EXECUTOR | MODEL | SECURITY_SENSITIVE | EGRESS_SAFE | RETRY_MAX | FILES | TEST | DONE_WHEN |
|---|---|---|---|---|---|---|---|---|---|
| T001 | Reconciliación, arqueología, N37, spec, plan y gate | CLAUDE | n-a | no | n-a | — | specs/gov-tre-04-pago/* | — | gate PASS |
| T002 | Datos: modelos (11 tablas), migración 0126, proyección, CTL-01 TRE-04, permisos, MFA, auditoría, guardas | DEEPSEEK | v4-pro | yes (diseño fijado) | yes | 2 | models.py, 0126, proyeccion_obligaciones.py, service_sod.py, schemas_sod.py, setup/api.py, mfa_policy.py, audit_catalog_entries.py, tests de guardas | alembic ida/vuelta/ida; guardas | 1 cabeza; guardas en verde |
| T003 | Servicio y API de medios, políticas y numeración | DEEPSEEK | v4-pro | yes (MFA) | yes | 2 | service_tesoreria_pago_politicas.py, schemas_tesoreria_pago.py, api_tesoreria_pago_politicas.py, main.py | T005 | verde |
| T004 | Servicio y API del pago (maker-checker, autoridad, duplicados, concurrencia) + guarda TRE-03 | DEEPSEEK | v4-pro | yes (autoridad, MFA, tenant) | yes | 2 | service_tesoreria_pago.py, api_tesoreria_pago.py, main.py, service_tesoreria_orden_pago.py | T005 | verde |
| T005 | Pruebas backend §46 | DEEPSEEK | v4-pro | no | yes | 2 | tests/test_gov_tre04_pago.py | PG | verde en PG y SQLite |
| T006 | Frontend políticas y medios + registro | DEEPSEEK | v4-pro | no | yes | 2 | src/modules/gobierno/tesoreria/pagos/*, router, Sidebar, pantallas | tsc | 0 |
| T007 | Frontend pagos | DEEPSEEK | v4-pro | no | yes | 2 | idem | tsc | 0 |
| T008 | Vitest §48 | DEEPSEEK | v4-pro | no | yes | 2 | *.test.tsx | vitest | verde |
| T009 | E2E §49–§55 y humo | DEEPSEEK | v4-pro | no | yes | 2 | e2e/gobierno-pagos.spec.ts, e2e/helpers/pagos.ts, e2e/uat-humo-gobierno.spec.ts | e2e-run | verde |
| T010 | Auditoría, mutaciones, OpenAPI, hardcode, PG completa, tarjeta, matrices, DAG y cierre | CLAUDE | n-a | no | n-a | — | specs/…/evidence, docs/roadmap/… | — | §70 |

Presupuesto DeepSeek: T002 1, T003 1, T004 2, T005 1, T006 1, T007 1, T008 1, T009 1, más 3 de reserva para correcciones agrupadas. Tope duro 12.

## Estado al cierre (2026-11-19)

T001–T010: **hechas**. T005 se dividió en C5a y C5b; T006–T009 en FE1–FE5, VT, E2E-a y E2E-b, y las correcciones medidas en FIX-1 a FIX-10 (ver `evidence/ATTEMPT_LOG.md`). Evidencia: `evidence/CIERRE.md`.
