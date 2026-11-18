# Tareas · GOV-TRE-03

| ID | Tarea | EXECUTOR | MODEL | SECURITY_SENSITIVE | FILES | TEST | DONE_WHEN |
|---|---|---|---|---|---|---|---|
| T001 | Reconciliación, arqueología, spec, plan y gate | CLAUDE | n-a | no | specs/gov-tre-03-orden-pago/* | — | gate PASS |
| T002 | Datos: modelos, migración 0124, proyección neutral, BUD-09 (proyección y guarda de anulación), catálogo CTL-01 TRE-03, permisos, MFA, auditoría, guardas de cabeza y recuentos | DEEPSEEK | v4-pro | yes (permisos/MFA; diseño fijado) | models.py, 0124, proyeccion_obligaciones.py, service_presupuesto_causado.py, service_sod.py, schemas_sod.py, setup/api.py, mfa_policy.py, audit_catalog_entries.py, tests de guardas | alembic ida/vuelta/ida; guardas | 1 cabeza; guardas en verde |
| T003 | Servicio, esquemas, API y main.py de TRE-03 | DEEPSEEK | v4-pro | yes (autoridad, MFA, tenant) | service_tesoreria_orden_pago.py, schemas_tesoreria_orden_pago.py, api_tesoreria_orden_pago.py, main.py | T004 | T004 en verde |
| T004 | Pruebas backend §39–§40 | DEEPSEEK | v4-pro | no | tests/test_gov_tre03_orden_pago.py | PG | verde en PG |
| T005 | Frontend: api.ts, páginas y registro, con Vitest §42 | DEEPSEEK | v4-pro | no | src/modules/gobierno/tesoreria/ordenes-pago/*, router.tsx, Sidebar.tsx, pantallas.ts | vitest | verde |
| T006 | E2E §43 y humo | DEEPSEEK | v4-pro | no | e2e/gobierno-tesoreria-orden-pago.spec.ts, e2e/uat-humo-gobierno.spec.ts | e2e-run | 1/1 |
| T007 | Auditoría, mutaciones, OpenAPI, PG completa, tarjeta, matrices, DAG y cierre | CLAUDE | n-a | no | specs/…/evidence, docs/roadmap/… | — | gate §51 |

Presupuesto DeepSeek: T002 = 1, T003 = 2, T004 = 1, T005 = 2 y T006 = 1, más 1 de reserva para correcciones agrupadas. Tope duro: 8.
