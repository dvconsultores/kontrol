# CTL-07 · Trazabilidad

| Requisito o criterio | Implementación | Prueba |
|---|---|---|
| FR-01 / AC-01 duplicidad | `service_alertas._duplicidades` | `test_duplicidad_por_par`; E2E, paso 3 |
| FR-02 / AC-02 proveedor relacionado (enmascarado) | `_proveedores_relacionados`, `enmascarar_documento` | `test_proveedor_relacionado_con_documento_enmascarado`; E2E, paso 4 |
| FR-03 / AC-03 autoaprobación | `_autoaprobaciones` (GOV_SOD_CONFLICT_BLOCKED y GOV_SOD_ROLE_CONFLICT_BLOCKED) | `test_autoaprobacion_desde_eventos_sod`; E2E con el conflicto real de PROC-11 |
| FR-04 / AC-04 no disponibles | `TIPOS` (disponible False, motivo y requisito) | `test_tipos_y_aviso`; Vitest 1; E2E «No disponible» |
| FR-05 sujetos sin UUID | `_alerta` y `_salida` | `test_duplicidad_por_par` (UUID_RE); Vitest 1 |
| FR-06 / AC-06 revisión única, inmutable y auditada | `revisar_alerta`, `GovernmentAtypicalAlertReview`, migración 0109 (disparadores) | `test_revision_valida_y_auditada`, `test_revision_inmutable`; E2E, pasos 8 y 9 |
| FR-07 / AC-05 sin autorrevisión | `revisar_alerta` (`_usuarios` y `_funcionarios`), `es_sujeto` | `test_autorrevision_y_doble_revision`; Vitest 3 y 6; E2E (pantalla y API 409) |
| FR-08 filtros y recuentos | `listar_alertas` (tipos con total y pendientes); filtros de la pantalla | `test_revision_valida_y_auditada` (estado); Vitest 8 |
| FR-09 aviso | `AVISO` | `test_tipos_y_aviso`; E2E |
| AC-05 rechazos sin escritura | validaciones antes del `add` | `test_rechazos_no_escriben`, `test_permisos` |
| AC-07 aislamiento | filtros por `company_id` y `tenant_id` | `test_aislamiento_entre_empresas`; mutación del filtro de empresa (muere) |
| AC-08 concurrencia | UNIQUE(company_id, clave) e IntegrityError → 409 | `test_carrera_de_revisiones` (`tests/concurrency.carrera`) |
| AC-09 inmutabilidad | disparadores `trg_gov_atypical_alert_reviews_no_*` | `test_revision_inmutable` |
| AC-10 responsive y accesibilidad | pantalla (región accesible y `flex-wrap`) | E2E: 1280, 390 y 320 con Axe |
| OD-CTL07-11 revisada que ya no se detecta | alerta sintética desde la revisión | `test_revisada_que_ya_no_se_detecta`; Vitest 7 |

Requisitos huérfanos: 0. Tareas huérfanas: 0. Trazabilidad: 100 %.
