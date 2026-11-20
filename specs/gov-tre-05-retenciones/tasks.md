# Tareas · GOV-TRE-05

| ID | Tarea | EXECUTOR | MODEL | SECURITY_SENSITIVE | EGRESS_SAFE | RETRY_MAX | FILES | TEST | DONE_WHEN |
|---|---|---|---|---|---|---|---|---|---|
| T001 | Reconciliación, arqueología N37/N38, decisiones de la dueña, spec, plan y gate | CLAUDE | n-a | no | n-a | — | specs/gov-tre-05-retenciones/* | — | gate PASS |
| T002 | Modelos (8 tablas), constantes, migración 0129 con guardas PG | DEEPSEEK | v4-pro | yes (diseño fijado) | yes | 2 | models.py, alembic/versions/0129_gov_tre05_retencion.py | alembic ida/vuelta/ida | 1 cabeza; CHECK migración = modelos |
| T003 | Registro: permisos, MFA, auditoría (15), CTL-01 TRE-05, contadores | DEEPSEEK | v4-pro | yes | yes | 2 | setup/api.py, mfa_policy.py, audit_catalog_entries.py, service_sod.py, schemas_sod.py, pruebas de contadores y cabeza | guardas | verde |
| T004 | Servicio y API de configuración, catálogo y políticas | DEEPSEEK | v4-pro | yes (MFA) | yes | 2 | service_tesoreria_retencion_politicas.py, schemas_tesoreria_retencion.py, api_tesoreria_retencion_politicas.py, main.py | T007 | verde |
| T005 | Motor puro, proyección, liquidación (calcular, ajustar, aprobar, anular, listar, CSV) e integración TRE-04 | DEEPSEEK | v4-pro | yes (autoridad, MFA, tenant) | yes | 2 | motor_retenciones.py, proyeccion_retenciones.py, service_tesoreria_retencion.py, service_tesoreria_pago*.py | T007 | verde |
| T006 | Comprobantes (numeración, instantánea, PDF, anular/sustituir) y API de liquidaciones y comprobantes | DEEPSEEK | v4-pro | yes | yes | 2 | service_tesoreria_retencion_comprobantes.py, api_tesoreria_retencion.py, main.py | T007 | verde |
| T007 | Pruebas backend §46 (30 casos) | DEEPSEEK | v4-pro | no | yes | 2 | tests/test_gov_tre05_retencion.py | PG + SQLite | verde |
| T008 | Frontend: api.ts, políticas, catálogo, numeración y registro (router, Sidebar, pantallas) | DEEPSEEK | v4-pro | no | yes | 2 | src/modules/gobierno/tesoreria/retenciones/*, router.tsx, Sidebar.tsx, pantallas.ts | tsc | 0 |
| T009 | Frontend: sección del pago y página Retenciones | DEEPSEEK | v4-pro | no | yes | 2 | RetencionesPago.tsx, RetencionesPage.tsx, PagoPage.tsx | tsc | 0 |
| T010 | Vitest §48 | DEEPSEEK | v4-pro | no | yes | 2 | *.test.tsx | vitest | verde |
| T011 | E2E §49–§55 y humo | DEEPSEEK | v4-pro | no | yes | 2 | e2e/gobierno-retenciones.spec.ts, e2e/helpers/retenciones.ts, e2e/uat-humo-gobierno.spec.ts | e2e-run | verde |
| T012 | Auditoría, mutaciones M1–M10, OpenAPI, hardcode, PG completa, tarjeta, matrices, DAG y cierre | CLAUDE | n-a | no | n-a | — | specs/…/evidence, docs/roadmap/… | — | §67 |

Presupuesto DeepSeek: T002 1, T003 1, T004 1, T005 2, T006 1, T007 2, T008 1, T009 1, T010 1, T011 2, más 6 de reserva para correcciones agrupadas y 1 para integrar P2. Tope duro 20.
