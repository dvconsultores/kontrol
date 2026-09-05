# SPEC 031 · TRAZABILIDAD DE IMPLEMENTACIÓN (POST `D0-15`)

| Requisito | Regla `D0-15` | Implementación | Prueba | Estado |
|---|---|---|---|---|
| IMP-031-001 · solo entra en la cola lo `RELEASED` | R-D0-15-1 | `picking_queue` filtra por `ORDER_HANDOFF_STATE` | `test_solo_entra_en_la_cola_lo_liberado_y_con_reserva_viva` | ✔ |
| IMP-031-002 · y con reserva activa | R-D0-15-1 | subconsulta sobre `Reservation.status == ACTIVE` | ídem | ✔ |
| IMP-031-003 · orden primario `released_at ASC` | R-D0-15-2 | `order_by(released_at.asc(), …)` | `test_la_cola_ordena_por_entrada_no_por_emision` · guardia | ✔ |
| IMP-031-004 · desempate `id ASC` | R-D0-15-3 | `order_by(…, SalesOrder.id.asc())` | `test_el_desempate_es_estable_y_no_lo_decide_la_base` | ✔ |
| IMP-031-005 · nunca `code` ni orden natural | R-D0-15-3 | — | `test_la_cola_ordena_por_el_sello_de_entrada` | ✔ |
| IMP-031-006 · sin prioridad de cliente, manual, SLA ni ruta | R-D0-15-4 | ningún campo de prioridad | `test_no_hay_prioridad_inventada` | ✔ |
| IMP-031-007 · el pedido revertido pierde su puesto | R-D0-15-2 | consecuencia de `released_at = None` en la 030 | documentada en `d0-15-checkpoint` | ✔ |
| IMP-031-008 · la reserva sigue siendo de almacén | R-D0-14-1 | la 031 no la escribe | `test_planificar_no_mueve_una_sola_unidad` | ✔ |
| IMP-031-009 · la asignación es operativa y por ubicación | R-D0-15-22 | `PickListLine.location_id` + `state` + `sequence` | `test_la_demanda_se_reparte_entre_ubicaciones` | ✔ |
| IMP-031-010 · solo lo ubicado y vendible es candidato | R-D0-10-3 | `located_sellable_balances` | `test_solo_lo_ubicado_y_vendible_es_candidato` | ✔ |
| IMP-031-011 · ubicación nula nunca es candidata | §36 | `location_id.isnot(None)` | ídem | ✔ |
| IMP-031-012 · ubicación de otro almacén bloqueada | R-D0-14-9 | `location_in_warehouse` | e2e · `test_no_se_asigna_una_ubicacion_de_otra_empresa_ni_de_otro_almacen` | ✔ |
| IMP-031-013 · ubicación de otra empresa bloqueada | ARCH-MC-001 | ídem, resuelto bajo contexto | ídem | ✔ |
| IMP-031-014 · la asignación es en unidad base | R-D0-09-1 | `_base_de(reserva)` usa `base_quantity` | `test_la_caja_de_doce_se_asigna_en_veinticuatro` | ✔ |
| IMP-031-015 · asignado ≤ reservado de la línea | §34 | `_asignado_a_linea` bajo bloqueo | `test_no_se_puede_asignar_mas_de_lo_reservado` | ✔ |
| IMP-031-016 · asignado ≤ existencia localizada | §35 | `_asignado_en_identidad` con saldo bloqueado | `test_dos_planes_no_se_llevan_la_misma_existencia` | ✔ |
| IMP-031-017 · división entre ubicaciones | R-D0-15-5 | varias `PickListLine` por línea | `test_la_demanda_se_reparte_entre_ubicaciones` | ✔ |
| IMP-031-018 · `DRAFT` admite asignación parcial | R-D0-15-6 | sin compuerta al asignar | `test_no_se_confirma_un_plan_incompleto` | ✔ |
| IMP-031-019 · el remanente es explícito | R-D0-15-7 | `plan_dict.remaining_base_quantity` | ídem | ✔ |
| IMP-031-020 · un `DRAFT` no es ejecutable | R-D0-15-6 | `confirmable` y la compuerta | ídem | ✔ |
| IMP-031-021 · con `DRAFT` el pedido sigue `RELEASED` | R-D0-15-18 | delta A sobre `create_picklist` | `test_crear_un_borrador_no_saca_el_pedido_de_la_cola` | ✔ |
| IMP-031-022 · confirmar exige remanente 0 | R-D0-15-8 | `confirm_plan` compara por línea | `test_no_se_confirma_un_plan_incompleto` | ✔ |
| IMP-031-023 · confirmar revalida la existencia | R-D0-15-9 | `PICKING_LOCATION_DRIFTED` | guardia + servicio | ✔ |
| IMP-031-024 · confirmar mueve el pedido a `PREPARING` | R-D0-15-18 | `confirm_plan` | `test_confirmar_completo_mueve_el_pedido_a_preparacion` | ✔ |
| IMP-031-025 · `CLOSED` no lo escribe la 031 | R-D0-15-10 | no existe camino a `CLOSED` | `test_la_031_no_ejecuta_el_picking_fisico` | ✔ |
| IMP-031-026 · cancelar libera las asignaciones | R-D0-15-12 | terminal ⇒ deja de estar viva | `test_cancelar_un_plan_confirmado_devuelve_el_pedido_a_la_cola` | ✔ |
| IMP-031-027 · cancelar devuelve el pedido a la cola | R-D0-15-19 | delta B, arista `PREPARING → RELEASED` | ídem | ✔ |
| IMP-031-028 · cancelar no libera la reserva | R-D0-15-13 | — | ídem · `test_la_031_no_libera_la_reserva_comercial` | ✔ |
| IMP-031-029 · invalidar exige precondición perdida | R-D0-15-11 | `PICKING_PLAN_STILL_VALID` | `test_invalidar_exige_que_la_precondicion_este_perdida` | ✔ |
| IMP-031-030 · cancelar e invalidar exigen motivo | §21 | `_motivo` | `test_cancelar_e_invalidar_exigen_motivo` | ✔ |
| IMP-031-031 · planificar no cambia `qty_on_hand` | R-D0-15-14 | — | `test_planificar_no_mueve_una_sola_unidad` | ✔ |
| IMP-031-032 · planificar no cambia `qty_reserved` | R-D0-15-14 | — | ídem | ✔ |
| IMP-031-033 · planificar no crea movimientos | R-D0-15-14 | — | ídem · `test_planificar_no_escribe_inventario` | ✔ |
| IMP-031-034 · la ruta es la de la Spec 008 | R-D0-15-20 | `_orden_fisico` sobre `physical_order_query` | `test_las_candidatas_salen_en_orden_de_recorrido` · guardia | ✔ |
| IMP-031-035 · sin algoritmo de ruta alternativo | R-D0-15-20 | — | `test_la_ruta_es_la_de_la_spec_008` | ✔ |
| IMP-031-036 · recorrido determinista | §50 | desempate por `id` de línea | `test_el_recorrido_es_estable` | ✔ |
| IMP-031-037 · sin FIFO, FEFO ni prioridad de lote | R-D0-15-21 | — | `test_no_hay_politica_de_lote_ni_de_serial` | ✔ |
| IMP-031-038 · lote y serial se preservan | §38 | la identidad del saldo se copia a la asignación | servicio `_saldo_candidato` | ✔ |
| IMP-031-039 · asignar es idempotente | §54 | semántica de **fijar**, no sumar | `test_asignar_fija_no_suma` | ✔ |
| IMP-031-040 · un solo plan vivo por pedido | §54 | índice único parcial | `test_el_estado_del_plan_esta_restringido_en_la_base` | ✔ |
| IMP-031-041 · concurrencia sobre la misma ubicación | §56 | `with_for_update` sobre el saldo | `test_dos_transacciones_no_asignan_la_misma_existencia` | ✔ |
| IMP-031-042 · candidatas obsoletas se revalidan | §59 | se recomprueba al asignar y al confirmar | servicio + e2e | ✔ |
| IMP-031-043 · el contexto de empresa es la autoridad | ARCH-MC-001 | `ctx.company_id`, nunca el cuerpo | `test_la_cola_no_cruza_empresas` | ✔ |
| IMP-031-044 · los permisos existen en el catálogo | §65 | `ventas:view` y `ventas:create` | `test_los_permisos_del_picking_existen_en_el_catalogo` | ✔ |
| IMP-031-045 · el estado del plan tiene `CHECK` | §62 | migración `0049` y ORM | `test_el_estado_del_plan_esta_restringido_en_la_base` | ✔ |
| IMP-031-046 · la migración no inventa historia | doctrina | sin backfill | `test_la_migracion_no_inventa_historia` | ✔ |
| IMP-031-047 · la deuda de `uom.py` no se absorbe | §27 | no se toca | anotada, dueña Spec 011 | ✔ |
| IMP-031-048 · la 032 solo consume `CONFIRMED` válido | R-D0-15-17 | contrato documentado | `spec032-handoff-after-spec031.md` | ✔ |

## Cobertura

| | |
|---|---:|
| Requisitos | 48 |
| Con implementación y prueba | **48** |
| Huérfanos | **0** |
| Cobertura | **100 %** |
