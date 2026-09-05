# SPEC 032 · TRAZABILIDAD DE IMPLEMENTACIÓN

| Requisito | Autoridad | Implementación | Prueba | Estado |
|---|---|---|---|---|
| IMP-032-001 · solo un plan `CONFIRMED` es ejecutable | `R-D0-15-17` | `_plan_ejecutable` | `test_no_se_prepara_un_plan_que_no_esta_confirmado` | ✔ |
| IMP-032-002 · el pedido debe estar en `PREPARING` | `ADR-D0-012` | ídem | ídem | ✔ |
| IMP-032-003 · la ruta viene de la 031 y no se replanifica | `R-D0-15-20` | se recorre `pick_list_lines` | `test_no_se_replanifica_al_encontrar_diferencia` | ✔ |
| IMP-032-004 · cada recogida referencia una asignación válida | — | `line_id` acotado al plan | `test_no_se_prepara_bajo_otra_empresa` | ✔ |
| IMP-032-005 · la cantidad es base | `R-D0-09-1` | `base_quantity` en todo | `test_la_caja_de_doce_llega_preparada_en_veinticuatro` | ✔ |
| IMP-032-006 · lo recogido no pisa lo planificado | DOCX ¶47, ¶53 | `picked_base_quantity` aparte | `test_lo_recogido_no_pisa_lo_planificado` | ✔ |
| IMP-032-007 · recoger de más está bloqueado | `R-D0-10-7` deny-by-default | `PICKING_OVER_PICK` | `test_no_se_puede_recoger_de_mas` | ✔ |
| IMP-032-008 · recoger de menos exige motivo | DOCX ¶47-53 | `PICKING_DISCREPANCY_REASON_REQUIRED` + `CHECK` | `test_recoger_de_menos_exige_motivo_y_libera_la_diferencia` | ✔ |
| IMP-032-009 · los motivos son los cinco del proceso | DOCX ¶48-52 | `PICK_DISCREPANCY_KINDS` | `test_los_motivos_son_los_cinco_del_proceso` | ✔ |
| IMP-032-010 · recoger cero es explícito | — | motivo obligatorio, sin cierre | `test_recoger_cero_es_explicito_y_no_cierra_nada` | ✔ |
| IMP-032-011 · cantidad negativa rechazada | — | `PICKING_QUANTITY_INVALID` + `CHECK` | `test_no_se_admite_cantidad_negativa` | ✔ |
| IMP-032-012 · la extracción pasa por el motor de la 023 | `R-D0-10` | `reclassify` | `test_la_extraccion_pasa_por_el_motor_canonico` | ✔ |
| IMP-032-013 · `DISPONIBLE → PICKING` declarada con dueña | matriz `D0-10` | `ACTIVE_TRANSITIONS` | `test_las_dos_aristas_del_picking_estan_declaradas_con_su_dueña` | ✔ |
| IMP-032-014 · `PICKING → PREPARADO` declarada con dueña | ídem | ídem | ídem | ✔ |
| IMP-032-015 · ni `PICKING` ni `PREPARADO` son vendibles | `ADR-D0-010` | `SELLABLE_STATES` | `test_ni_picking_ni_preparado_son_vendibles` | ✔ |
| IMP-032-016 · **el compromiso no se resta dos veces** | `D0-03` §0 «y aún no extraídas» | `consume_on_pick` | `test_recoger_no_resta_dos_veces_el_mismo_compromiso` | ✔ |
| IMP-032-017 · el despacho no resta lo ya extraído | ídem | `_close_reservation` | `test_despachar_no_borra_el_compromiso_del_otro_pedido` | ✔ |
| IMP-032-018 · el picking corto libera la diferencia | `POL-D0-002` §8 | `release_picking_shortage` | `test_recoger_de_menos_exige_motivo_y_libera_la_diferencia` | ✔ |
| IMP-032-019 · la reserva se consume en el despacho | `POL-D0-002` §8, `FR-030-054` | intacta en la 032 | `test_la_032_no_crea_ni_libera_reservas_por_su_cuenta` | ✔ |
| IMP-032-020 · nada sale del almacén al preparar | `POL-D0-002` §8 | sin `SALIDA_DESPACHO` | `test_preparar_no_saca_mercancia_del_almacen` | ✔ |
| IMP-032-021 · lote y serial se preservan | §37-38 del ciclo | identidad copiada | `test_la_identidad_de_lote_y_serial_se_preserva` | ✔ |
| IMP-032-022 · sin FIFO/FEFO ni sustitución | `R-D0-15-21` | — | `test_no_hay_seleccion_inventada_ni_sustitucion` | ✔ |
| IMP-032-023 · una parada se recoge una vez | §54 del ciclo | `PICKING_ALREADY_PICKED` + bloqueo de fila | `test_una_parada_se_recoge_una_vez` | ✔ |
| IMP-032-024 · dos operarios no duplican la extracción | §49 del ciclo | `with_for_update` | `test_dos_operarios_no_recogen_la_misma_parada` | ✔ |
| IMP-032-025 · no se consolida un recorrido a medias | DOCX ¶41 | `PICKING_ROUTE_INCOMPLETE` | `test_no_se_consolida_un_recorrido_a_medias` | ✔ |
| IMP-032-026 · consolidar concentra y traslada | DOCX ¶55-58 | `reclassify` + `putaway` al área | `test_recorrido_completo_y_consolidacion` | ✔ |
| IMP-032-027 · el Área de Confirmación es del mismo almacén | `R-D0-14-9` | `location_in_warehouse` | `test_el_area_de_confirmacion_es_del_mismo_almacen` | ✔ |
| IMP-032-028 · lo consolidado sale de lo recogido | DOCX ¶55 | `prepared_base_quantity` | `test_se_consolida_con_diferencia_y_no_se_certifica_nada` | ✔ |
| IMP-032-029 · el plan se cierra al consolidar | `R-D0-15-10` | `CLOSED` solo ahí | `test_solo_la_consolidacion_cierra_el_plan` | ✔ |
| IMP-032-030 · el pedido llega a `PREPARED` | `ADR-D0-012` | `ORDER_TRANSITIONS` | `test_el_pedido_llega_a_preparado_y_no_mas_alla` | ✔ |
| IMP-032-031 · `PREPARED` conserva la reserva | `POL-D0-002` §8 | `ORDER_RESERVED_STATES` | ídem | ✔ |
| IMP-032-032 · la 032 no confirma independientemente | DOCX ¶61 | — | `test_la_032_no_hace_el_control_independiente` | ✔ |
| IMP-032-033 · la 032 no factura ni despacha | fronteras 034/035 | — | `test_la_032_no_factura_ni_despacha` | ✔ |
| IMP-032-034 · el contexto de empresa es la autoridad | ARCH-MC-001 | `ctx.company_id` | `test_no_se_prepara_bajo_otra_empresa` | ✔ |
| IMP-032-035 · los permisos existen en el catálogo | §78 del ciclo | `ventas:view` / `ventas:create` | `test_los_permisos_de_la_preparacion_existen_en_el_catalogo` | ✔ |
| IMP-032-036 · la migración no inventa historia | doctrina | sin backfill | `test_la_migracion_no_inventa_historia` | ✔ |
| IMP-032-037 · la 033 recibe hechos, no un veredicto | DOCX ¶59, ¶61 | `preparation_dict` | `test_se_consolida_con_diferencia_y_no_se_certifica_nada` | ✔ |

## Cobertura

| | |
|---|---:|
| Requisitos | 37 |
| Con implementación y prueba | **37** |
| Huérfanos | **0** |
| Cobertura | **100 %** |
