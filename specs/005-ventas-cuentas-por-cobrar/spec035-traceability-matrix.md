# SPEC 035 · TRAZABILIDAD DE IMPLEMENTACIÓN

| Requisito | Autoridad | Implementación | Prueba | Estado |
|---|---|---|---|---|
| IMP-035-001 · solo un pedido facturado pasa a despacho | ¶101 | `create_shipment` exige `INVOICED` | `test_no_se_despacha_sin_factura_emitida` | ✔ |
| IMP-035-002 · la compuerta exige confirmación independiente | ¶103 | `validate_shipment` | `test_no_se_despacha_sin_confirmacion_independiente` | ✔ |
| IMP-035-003 · exige factura **emitida**, no generada | ¶103 · ¶95≠¶97 | `factura.status != "EMITTED"` | `test_no_se_despacha_sin_factura_emitida` | ✔ |
| IMP-035-004 · la comprueba por registro, no por estado | lección Spec 033 | consulta `OrderConfirmation` y `SalesInvoice` | ídem | ✔ |
| IMP-035-005 · exige destino y responsable del traslado | ¶105 | `DISPATCH_TRANSPORT_REQUIRED` | `test_hay_que_decir_a_donde_va_y_quien_se_la_lleva` | ✔ |
| IMP-035-006 · consulta la evaluación regulatoria | Spec 044 | `regulatory_service.evaluate_shipment` | `test_la_compuerta_comprueba_las_tres_cosas` | ✔ |
| IMP-035-007 · un requisito faltante bloquea | Spec 044 | `DISPATCH_REGULATORY_BLOCKED` | `test_un_requisito_regulatorio_faltante_bloquea_la_salida` | ✔ |
| IMP-035-008 · un requisito vencido bloquea | Spec 044 | ídem | `test_un_requisito_vencido_tambien_bloquea` | ✔ |
| IMP-035-009 · los requisitos son concurrentes, no alternativos | §43 del ciclo | `_required_kinds` recorre todos | `test_cada_requisito_se_evalua_por_separado` | ✔ |
| IMP-035-010 · la aplicabilidad viene del perfil, no del nombre | §39 del ciclo | `_applicable_profiles` | ídem | ✔ |
| IMP-035-011 · no se emiten permisos oficiales | maestro Spec 044 | — | `test_el_despacho_no_emite_permisos_ni_verifica_en_linea` | ✔ |
| IMP-035-012 · no se simula verificación en línea | §50 del ciclo | — | ídem | ✔ |
| IMP-035-013 · la salida es en cantidad **base** | §63 del ciclo | `line.base_quantity` | `test_la_salida_es_en_cantidad_base_y_desde_preparado` | ✔ |
| IMP-035-014 · la salida sale de `PREPARADO` | Spec 032 | `reclassify` desde el Área de Confirmación | ídem | ✔ |
| IMP-035-015 · la arista está declarada con su dueña | matriz `D0-10` fila 61 | `ACTIVE_TRANSITIONS` | `test_la_arista_de_despacho_esta_declarada_con_su_dueña` | ✔ |
| IMP-035-016 · `DESPACHADO → VENDIDO` no se activa | Proceso 9 no la escribe | — | ídem | ✔ |
| IMP-035-017 · no se inventan estados de mercancía | `D0-10` | — | ídem | ✔ |
| IMP-035-018 · la salida consume la reserva | `POL-D0-002` §8 | `fulfill_reservation` | `test_la_cadena_completa_despacha_y_la_mercancia_sale` | ✔ |
| IMP-035-019 · el pedido llega a `SHIPPED` tras la salida | ¶104-107 | `confirm_shipment` | ídem | ✔ |
| IMP-035-020 · solo `INVOICED` puede despachar | ¶103 | `ORDER_TRANSITIONS` | `test_solo_se_despacha_lo_facturado` | ✔ |
| IMP-035-021 · el despacho guarda su factura | ¶106 | `Shipment.invoice_id` | `test_el_despacho_guarda_con_que_factura_sale` | ✔ |
| IMP-035-022 · lote y serial se preservan | §60-61 del ciclo | copiados a la línea y al movimiento | `_despacho` + `reclassify` | ✔ |
| IMP-035-023 · el despacho es idempotente | §74 del ciclo | `dispatched_at` antes del estado | `test_despachar_dos_veces_no_saca_dos_veces` | ✔ |
| IMP-035-024 · un pedido no se despacha dos veces | §64 del ciclo | índice único parcial | `test_un_pedido_no_se_despacha_dos_veces` | ✔ |
| IMP-035-025 · dos despachadores no duplican la salida | §76 del ciclo | bloqueo del pedido + idempotencia | `test_dos_despachadores_no_sacan_la_mercancia_dos_veces` | ✔ |
| IMP-035-026 · el contexto de empresa es la autoridad | ARCH-MC-001 | `_company` y `_lock_order` | `test_no_se_despacha_bajo_otra_empresa` | ✔ |
| IMP-035-027 · el despacho no factura ni devuelve | §18, §84 del ciclo | — | `test_el_despacho_no_factura_ni_devuelve` | ✔ |
| IMP-035-028 · la migración es aditiva | doctrina | FK anulables, sin backfill | `test_la_migracion_es_aditiva_y_no_inventa_historia` | ✔ |
| IMP-035-029 · la aprobación precede a los efectos | ¶104 | comprobaciones antes de aprobar | `test_la_compuerta_ya_no_aprueba_sin_mirar` | ✔ |
| IMP-035-030 · lo que sale no se escribe a mano | §21 del ciclo | `_lineas_consolidadas` desde el plan cerrado | `test_el_despacho_sin_lineas_toma_las_que_se_consolidaron` | ✔ |
| IMP-035-031 · el almacén de origen es el del pedido | ¶101 | `origin_warehouse_id` implícito | ídem | ✔ |
| IMP-035-032 · el transporte indicado es de la empresa | ¶105 · ARCH-MC-001 | `_require_vehicle` · `_require_driver` | `test_no_se_despacha_con_el_vehiculo_de_otra_empresa` | ✔ |
| IMP-035-033 · la cola solo trae pedidos facturados | ¶101 | `dispatch_queue` filtra `INVOICED` | `test_la_cola_de_despacho_solo_trae_pedidos_facturados` | ✔ |
| IMP-035-034 · el duplicado da conflicto legible, y la base lo impide | §64 del ciclo | `ORDER_ALREADY_SHIPPED` + índice único parcial | `test_un_pedido_no_se_despacha_dos_veces` | ✔ |

## Delta de infraestructura de test/harness

No son requisitos funcionales y no se cuentan como tales: son la evidencia del
defecto de test que la primera regresión completa destapó, y de la invariante
que impide que vuelva. Los requisitos de la Spec 034 y de la Spec 035 no
cambian por este incidente.

| Evidencia | Causa raíz | Implementación | Prueba | Estado |
|---|---|---|---|---|
| INF-035-001 · la frontera 034→035 es semántica | frontera posicional hasta `def create_shipment(` | cabecera canónica de la 035 en `service.py` | `test_facturar_no_despacha` | ✔ |
| INF-035-002 · lo mismo en `api.py` | bloques 032/033/034 terminaban en `@router.post("/shipments"` | cabeceras de la 032 y la 035 en `api.py` | `test_los_permisos_*_existen_en_el_catalogo` | ✔ |
| INF-035-003 · las tres formas de recortar viven en un solo sitio | cinco copias locales de `_bloque` | `tests/spec_blocks.py` | `test_las_tres_formas_de_recortar_hacen_lo_que_dicen` | ✔ |
| INF-035-004 · la frontera no depende del nombre ni del sitio de la función pública | — | `bloque_de_spec` | `test_la_frontera_no_depende_del_nombre_ni_del_sitio_de_la_funcion_publica` | ✔ |
| INF-035-005 · el recorte viejo sí reproducía el defecto | — | — | `test_la_estrategia_posicional_anterior_si_habria_fallado` | ✔ |
| INF-035-006 · sin marcador estable el guardia se niega a adivinar | — | `bloque_de_spec` lanza | `test_sin_marcador_estable_el_guardia_se_niega_a_adivinar` | ✔ |
| INF-035-007 · ningún guardia del tramo recorta a mano | la clase entera del defecto | — | `test_ningun_guardia_del_tramo_recorta_por_su_cuenta` (×5) | ✔ |
| INF-035-008 · cada Spec del tramo tiene cabecera única en ambos módulos | — | cabeceras 031-035 | `test_cada_spec_del_tramo_tiene_su_cabecera_*` · `test_las_cabeceras_son_unicas_y_no_colisionan` | ✔ |

## Cobertura

| | |
|---|---:|
| Requisitos funcionales | 34 |
| Con implementación y prueba | **34** |
| Huérfanos | **0** |
| Cobertura | **100 %** |
| Evidencia de test/harness | 8 |
| Con prueba | **8** |
