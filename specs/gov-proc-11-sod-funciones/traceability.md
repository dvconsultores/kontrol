# TRACEABILITY · PROC-11

| Requisito | Implementación | Prueba |
|---|---|---|
| FR-001 Catálogo de funciones | `service_sod_funciones.FUNCIONES`, `catalogo()`; `api_sod_funciones.catalogo` | `test_catalogo_publica_pagador_no_disponible`; FSP-02 |
| FR-002 Matriz versionada | `GovernmentSoDRoleRule` + `0103_gov_proc11_sod_funciones`; `crear()`; índice `uq_gov_sod_role_rules_par_vigente` | `test_regla_vida_completa`, `test_regla_invalida_422` |
| FR-003 Activación con MFA | `activar()` con `gobierno_sod:activate`; `_evitar_solapamiento` | `test_regla_vida_completa`, `test_par_vigente_no_se_solapa` |
| FR-004 Ocupación calculada | `ocupacion()` con `usuarios_equivalentes`/`funcionarios_de_actor` (ORG-06) | `test_conflicto_previo_visible_por_periodo` |
| FR-005 Detección | `conflictos_de_ocupaciones`, `conflictos_de_expediente` | `test_conflicto_previo_visible_por_periodo`; FSP-01 |
| FR-006 Bloqueo preventivo | `verificar_antes_de_asumir_funcion` + guardas en PROC-03/06/07/08 | `test_bloqueo_al_asumir_funcion_incompatible`; E2E PROC-11 |
| FR-007 Consulta por período | `conflictos_por_periodo`, `_periodo` | `test_periodo_invalido_422` |
| FR-008 Consulta por expediente | `conflictos_del_expediente`, `SeccionFuncionesIncompatibles` | `ExpedienteFunciones.test.tsx`; E2E PROC-11 |
| FR-009 Exportación | `exportar_csv` + `GOV_SOD_ROLE_CONFLICTS_EXPORTED` | `test_exportacion_csv_deja_evento`; FSP-06 |
| FR-010 Permisos y aislamiento | `require_permission("gobierno_sod", …)`, filtro por `company_id` | `test_otro_ente_no_ve_ni_consulta`, `test_sin_capacidad_403`; FSP-04 |
| FR-011 Concurrencia | `_para_escribir` (If-Match) y bloqueo `FOR UPDATE` | `test_regla_vida_completa` (versiones), FSP-05 |
| FR-012 Auditoría | 5 entradas del catálogo cerrado + historia inmutable | `test_regla_vida_completa`, `test_historia_inmutable` |
| FR-013 Interfaz | `FuncionesSodPage`, menú, ruta y pantalla registrada | FSP-01..06; E2E (Axe y 1280/390/320) |

## Criterios de aceptación

| Criterio | Evidencia |
|---|---|
| SC-001 crear y activar con MFA | `test_regla_vida_completa`; E2E PROC-11 (UI) |
| SC-002 bloqueo sin mutación + auditoría | `test_bloqueo_al_asumir_funcion_incompatible`; E2E PROC-11 (`GOV_SOD_ROLE_CONFLICT`) |
| SC-003 conflicto previo visible | `test_conflicto_previo_visible_por_periodo`; E2E PROC-11 (UI) |
| SC-004 aislamiento y permisos | `test_otro_ente_no_ve_ni_consulta`, `test_sin_capacidad_403` |
| SC-005 exportación | `test_exportacion_csv_deja_evento` |
| SC-006 pantalla y ficha accesibles | E2E PROC-11 (Axe serio/crítico = 0; 1280/390/320 sin desborde) |

## Requisitos ↔ compuertas

| Compuerta | Dónde se cumple |
|---|---|
| BACKEND_COMPLETE | servicio, modelos y migración `0103` |
| DATABASE_COMPLETE | tablas, checks, índices parciales y triggers de no borrado |
| API_COMPLETE | 8 rutas bajo `/gobierno/sod/funciones` |
| FRONTEND_COMPLETE | pantalla, formulario, acciones, conflictos, CSV |
| MENU_COMPLETE | Gobierno › Contrataciones › Funciones incompatibles |
| PROCESS_COMPLETE | matriz + detección + bloqueo + consulta + exportación |
| FIELDS_COMPLETE | función, regla, vigencia, evidencia, actor |
| ROLES_COMPLETE | Control Interno (view/manage/activate); Unidad Contratante consume el bloqueo |
| DOCUMENT_COMPLETE | NOT_APPLICABLE justificado: PROC-11 no produce documento propio; la evidencia son los registros del expediente y la bitácora |
| REPORTING_COMPLETE | listado por período + CSV |
| AUDIT_COMPLETE | 5 eventos CTL-02 |
| SECURITY_COMPLETE | capacidades, MFA en activación, aislamiento, backend autoridad |
| CONCURRENCY_COMPLETE | If-Match en alta/activación/cierre; `FOR UPDATE` del expediente en la guarda |
| SCREEN_COMPLETE | `FuncionesSodPage` + bloque en la ficha del expediente |
| E2E_COMPLETE | `e2e/gobierno-sod-funciones.spec.ts` |
| RESPONSIVE_COMPLETE | 1280/390/320 sin desbordamiento (E2E) |
| ACCESSIBILITY_COMPLETE | Axe sin violaciones serias/críticas (E2E) |
