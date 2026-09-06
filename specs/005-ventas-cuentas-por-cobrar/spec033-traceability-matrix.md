# SPEC 033 · TRAZABILIDAD DE IMPLEMENTACIÓN

| Requisito | Autoridad | Implementación | Prueba | Estado |
|---|---|---|---|---|
| IMP-033-001 · solo un pedido `PREPARED` entra al control | ¶62, `ADR-D0-012` | `_pedido_preparado` | `test_no_se_confirma_un_pedido_que_no_esta_preparado` | ✔ |
| IMP-033-002 · la confirmación referencia la preparación concreta | `R-D0-12-1` | `picklist_id` obligatorio | `test_la_confirmacion_es_una_entidad_y_no_un_booleano` | ✔ |
| IMP-033-003 · sin preparación consolidada no hay control | ¶62 | `CONFIRMATION_NO_PREPARATION` | `_pedido_preparado` | ✔ |
| IMP-033-004 · «independiente» es separación funcional | ¶90, `R-D0-12-5` | segregación por defecto | `test_quien_preparo_no_puede_confirmar` | ✔ |
| IMP-033-005 · la separación se comprueba en el backend | §73 del ciclo | `_segregacion_permitida` | `test_la_segregacion_se_comprueba_en_el_backend` | ✔ |
| IMP-033-006 · la política es por empresa y su defecto exige separación | `R-D0-12-5` | `Company.confirmation_same_user_allowed` | `test_el_defecto_de_la_politica_es_exigir_separacion` · `test_la_empresa_puede_permitirlo_a_conciencia` | ✔ |
| IMP-033-007 · preparadores = quien recogió y quien consolidó | ¶90 | `_preparadores` | `test_los_preparadores_incluyen_a_todos_los_que_tocaron` | ✔ |
| IMP-033-008 · **se compara contra el pedido, no contra la preparación** | `R-D0-12-2` | `_requerido_de` | `test_se_compara_contra_el_pedido_y_no_contra_la_preparacion` | ✔ |
| IMP-033-009 · el requerido no sale de la reserva encogida | `R-D0-12-2` | ídem | ídem | ✔ |
| IMP-033-010 · las tres cifras no se colapsan | §29 del ciclo | tres columnas | `test_las_tres_cifras_no_se_colapsan` · `test_el_control_guarda_las_tres_cifras` | ✔ |
| IMP-033-011 · se verifica producto y SKU | ¶65-66 | identidad de la línea | `test_una_linea_no_pedida_no_pasa_inadvertida` | ✔ |
| IMP-033-012 · se verifica cantidad en unidad base | ¶67 | `Decimal` exacto | `test_la_caja_de_doce_se_verifica_en_veinticuatro` | ✔ |
| IMP-033-013 · se verifica presentación | ¶68 | `presentation_ok` contra el snapshot | `test_la_presentacion_y_la_condicion_forman_parte_del_control` | ✔ |
| IMP-033-014 · se verifica condición para despacho | ¶69 | `condition_ok` | ídem | ✔ |
| IMP-033-015 · una línea faltante no pasa | — | `LINEA_FALTANTE` | `test_el_dictamen_es_determinista_y_ordenado` | ✔ |
| IMP-033-016 · una línea sobrante no pasa | — | `LINEA_SOBRANTE` | `test_una_linea_no_pedida_no_pasa_inadvertida` | ✔ |
| IMP-033-017 · el control es completo, no parcial | `R-D0-12-3` | `CONFIRMATION_INCOMPLETE` | `test_el_control_es_completo_o_no_es_control` | ✔ |
| IMP-033-018 · el veredicto lo calcula el backend | §74 del ciclo | `_dictamen_de_linea` | `test_el_veredicto_lo_calcula_el_backend` | ✔ |
| IMP-033-019 · el dictamen es determinista | §78 del ciclo | orden fijo de dimensiones | `test_el_dictamen_es_determinista_y_ordenado` | ✔ |
| IMP-033-020 · conforme → `CONFIRMED` | `R-D0-12-4`, ¶81 | `confirm_order` | `test_el_pedido_conforme_queda_formalmente_confirmado` | ✔ |
| IMP-033-021 · no conforme → regresa a preparación | `R-D0-12-3`, ¶77 | `PREPARED → PREPARING` | `test_el_pedido_no_conforme_regresa_a_preparacion` | ✔ |
| IMP-033-022 · el rechazo se conserva | `R-D0-12-3` | `attempt` incremental | `test_el_rechazo_se_conserva_cuando_hay_segundo_intento` | ✔ |
| IMP-033-023 · un pedido no se confirma dos veces | §93 del ciclo | índice único parcial | `test_un_pedido_no_se_confirma_dos_veces_ni_en_la_base` · `test_no_se_confirma_dos_veces` | ✔ |
| IMP-033-024 · dos verificadores no dejan dos veredictos | §56 del ciclo | bloqueo del pedido | `test_dos_verificadores_no_dejan_dos_veredictos` | ✔ |
| IMP-033-025 · la confirmación es entidad, no booleano | `R-D0-12-1` | `OrderConfirmation` | `test_la_confirmacion_es_una_entidad_y_no_un_booleano` | ✔ |
| IMP-033-026 · el estado está restringido en la base | §52 del ciclo | `CHECK` | `test_el_estado_y_los_motivos_estan_restringidos_en_la_base` | ✔ |
| IMP-033-027 · una línea no conforme dice en qué dimensión | ¶75 | `CHECK` de motivo | ídem | ✔ |
| IMP-033-028 · los motivos son las dimensiones del proceso | ¶65-69 | `CONFIRMATION_DIFFERENCE_KINDS` | `test_los_motivos_son_las_dimensiones_que_el_proceso_verifica` | ✔ |
| IMP-033-029 · no se reutiliza la incidencia de compras | §88 del ciclo | — | `test_no_se_reutiliza_la_incidencia_de_compras` | ✔ |
| IMP-033-030 · el control no toca inventario ni reserva | §37-38 del ciclo | — | `test_verificar_no_mueve_una_sola_unidad` · `test_el_control_no_toca_inventario_ni_reserva` | ✔ |
| IMP-033-031 · el control no ejecuta ni replanifica el picking | §16 del ciclo | — | `test_el_control_no_ejecuta_ni_replanifica_el_picking` | ✔ |
| IMP-033-032 · el control no factura ni despacha | §17-18 del ciclo | — | `test_el_control_no_factura_ni_despacha` | ✔ |
| IMP-033-033 · el control no renegocia la venta | §67 del ciclo | — | `test_el_control_no_modifica_la_venta` | ✔ |
| IMP-033-034 · la elegibilidad para facturar tiene una sola autoridad | ¶83, ¶89 | `billing_eligibility` | `test_la_elegibilidad_para_facturar_tiene_una_sola_autoridad` | ✔ |
| IMP-033-035 · un pedido no conforme no es facturable | §34, §55 del ciclo | ídem | `test_el_pedido_no_conforme_regresa_a_preparacion` | ✔ |
| IMP-033-036 · `READY_FOR_BILLING` queda para la 034 | `ADR-D0-012` | no se añade | `test_el_pedido_llega_a_confirmado_y_no_mas_alla` | ✔ |
| IMP-033-037 · `CONFIRMED` conserva la reserva | `POL-D0-002` §8 | `ORDER_RESERVED_STATES` | ídem | ✔ |
| IMP-033-038 · el contexto de empresa es la autoridad | ARCH-MC-001 | `ctx.company_id` | `test_el_control_no_cruza_empresas` | ✔ |
| IMP-033-039 · los permisos existen en el catálogo | §72 del ciclo | `ventas:quality` / `ventas:view` | `test_los_permisos_del_control_existen_en_el_catalogo` | ✔ |
| IMP-033-040 · la migración no inventa historia | doctrina | sin backfill | `test_la_migracion_no_inventa_historia` | ✔ |

## Cobertura

| | |
|---|---:|
| Requisitos | 40 |
| Con implementación y prueba | **40** |
| Huérfanos | **0** |
| Cobertura | **100 %** |
