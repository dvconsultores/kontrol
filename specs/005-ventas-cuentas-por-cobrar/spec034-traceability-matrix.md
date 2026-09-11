# SPEC 034 · TRAZABILIDAD DE IMPLEMENTACIÓN

| Requisito | Autoridad | Implementación | Prueba | Estado |
|---|---|---|---|---|
| IMP-034-001 · solo se factura un pedido con confirmación vigente | ¶89 · `B-060` | `_confirmacion_vigente` | `test_no_se_solicita_facturacion_de_un_pedido_sin_confirmar` | ✔ |
| IMP-034-002 · la compuerta mira el registro, no solo el estado | contrato 033 | ídem | `test_no_basta_con_poner_el_pedido_en_confirmado_a_mano` | ✔ |
| IMP-034-003 · la confirmación se revalida en cada acto | `B-060` | en solicitar, generar y emitir | `test_no_se_factura_sin_confirmacion_independiente` | ✔ |
| IMP-034-004 · la solicitud es explícita y con autor | ¶84 · `B-060` | `billing_requested_at/by` | `test_la_solicitud_deja_quien_y_cuando` | ✔ |
| IMP-034-005 · sin solicitud no hay factura | ¶92 | `BILLING_NOT_REQUESTED` | `test_no_se_genera_factura_sin_solicitud` | ✔ |
| IMP-034-006 · la factura se asocia al pedido | ¶96 · `B-007` | `SalesInvoice.order_id` | `test_la_factura_sale_del_pedido_y_queda_atada_a_el` | ✔ |
| IMP-034-007 · y a la confirmación sobre la que se emitió | `B-060` | `confirmation_id` | ídem | ✔ |
| IMP-034-008 · un pedido no se factura dos veces | `B-007` | servicio **e** índice único | `test_un_pedido_no_se_factura_dos_veces` | ✔ |
| IMP-034-009 · la base lo impide aunque el servicio falle | `B-007` | `uq_sales_invoices_order` | mutación verificada | ✔ |
| IMP-034-010 · dos facturadores no generan dos facturas | §66 del ciclo | bloqueo del pedido + índice | `test_dos_facturadores_no_generan_dos_facturas` | ✔ |
| IMP-034-011 · el precio es el congelado del pedido | Spec 029 · §32 | `_precio_de` | `test_el_maestro_de_hoy_no_reescribe_una_venta_cerrada` | ✔ |
| IMP-034-012 · el descuento es el congelado | §33 del ciclo | `linea.discount` | ídem | ✔ |
| IMP-034-013 · la factura no consulta el maestro actual | §43 del ciclo | — | `test_el_precio_es_el_congelado_del_pedido` | ✔ |
| IMP-034-014 · unidad, presentación y factor se conservan | Spec 011 · §41 | copiados de la línea | `test_la_factura_conserva_unidad_presentacion_y_base` | ✔ |
| IMP-034-015 · el factor no se recalcula | `P23` | — | ídem | ✔ |
| IMP-034-016 · caja ×12 conserva 2 comercial y 24 base | §42 del ciclo | `quantity` y `base_quantity` | `test_la_caja_de_doce_se_factura_como_dos_cajas_de_veinticuatro_unidades` | ✔ |
| IMP-034-017 · el impuesto lo resuelve la regla versionada | Spec 039 · §35 | `fiscal_service.calculate_tax` | `test_el_impuesto_lo_resuelve_la_regla_versionada` | ✔ |
| IMP-034-018 · ninguna tasa escrita en esta Spec | §35 del ciclo | — | `test_ninguna_tasa_de_impuesto_nace_aqui` | ✔ |
| IMP-034-019 · las líneas sin clasificación fiscal son visibles | ¶93 | `lines_without_tax` | `billing_invoice_dict` | ✔ |
| IMP-034-020 · el correlativo lo asigna la Spec 042 | §27 del ciclo | `emit_document` | `test_emitir_consume_correlativo_y_numero_de_control` | ✔ |
| IMP-034-021 · el número de control lo asigna la Spec 042 | §28 del ciclo | ídem | ídem | ✔ |
| IMP-034-022 · la 034 no lleva contador propio | §27 del ciclo | — | `test_la_numeracion_no_es_de_esta_spec` | ✔ |
| IMP-034-023 · emitir dos veces no gasta dos números | §65, §67 del ciclo | idempotencia por `INVOICE:{id}` | `test_emitir_dos_veces_no_gasta_dos_numeros` | ✔ |
| IMP-034-024 · no se emite una factura sin pedido | `B-007` | `INVOICE_WITHOUT_ORDER` | `test_no_se_emite_una_factura_sin_pedido` | ✔ |
| IMP-034-025 · el documento fiscal nace al emitir, no antes | ¶97 · §29 | `issue_invoice` | `test_emitir_consume_correlativo_y_numero_de_control` | ✔ |
| IMP-034-026 · el pedido queda `INVOICED` | ¶99 · `ADR-D0-012` | `ORDER_TRANSITIONS` | ídem | ✔ |
| IMP-034-027 · `READY_FOR_BILLING` e `INVOICED` conservan la reserva | `POL-D0-002` §8 | `ORDER_RESERVED_STATES` | `test_el_pedido_llega_a_facturado_y_no_mas_alla` | ✔ |
| IMP-034-028 · facturar no cambia `qty_on_hand` | §16 del ciclo | — | `test_facturar_no_mueve_una_sola_unidad` | ✔ |
| IMP-034-029 · facturar no toca la reserva | §17 del ciclo | — | ídem · `test_facturar_no_toca_inventario_ni_reserva` | ✔ |
| IMP-034-030 · facturar no crea movimientos | §16 del ciclo | — | ídem | ✔ |
| IMP-034-031 · la 034 no ejecuta picking ni confirma | §15-16 del ciclo | — | `test_facturar_no_ejecuta_picking_ni_confirma` | ✔ |
| IMP-034-032 · la 034 no despacha | §18 del ciclo | — | `test_facturar_no_despacha` | ✔ |
| IMP-034-033 · no se construye un segundo ledger de cobro | `FR-005-040` · §19 | — | `test_no_se_construye_un_segundo_libro_de_cuentas_por_cobrar` | ✔ |
| IMP-034-034 · el estado de facturación es consultable | ¶103 | `order_invoice_dict` | `test_el_estado_de_facturacion_es_consultable_para_el_despacho` | ✔ |
| IMP-034-035 · `DISPATCHED` queda para la 035 | `ADR-D0-012` | no se añade | `test_el_pedido_llega_a_facturado_y_no_mas_alla` | ✔ |
| IMP-034-036 · el contexto de empresa es la autoridad | ARCH-MC-001 | `ctx.company_id` | `test_la_facturacion_no_cruza_empresas` | ✔ |
| IMP-034-037 · los permisos existen en el catálogo | §77 del ciclo | `ventas:view/quality/create/approve` | `test_los_permisos_de_facturacion_existen_en_el_catalogo` | ✔ |
| IMP-034-038 · la solicitud la firma quien verifica | ¶83 | `ventas:quality` | `test_la_solicitud_la_firma_quien_verifica` | ✔ |
| IMP-034-039 · la migración es aditiva y no inventa historia | `B-007` | FK anulable, sin backfill | `test_la_migracion_es_aditiva_y_no_inventa_historia` | ✔ |
| IMP-034-040 · el veredicto no lo envía el cliente | §74 del ciclo | totales calculados en backend | `test_el_veredicto_lo_calcula_el_backend` (033) · API sin campos de total | ✔ |
| IMP-034-041 · emitir la factura abre su cuenta por cobrar | proceso de ventas «9. Emitir factura → **10. Crear CxC**» | `_abrir_cuenta_por_cobrar`, idempotente, en los dos caminos | `test_la_nota_reduce_la_cuenta_por_cobrar` (036) · `test_la_nota_de_debito_aumenta_la_cuenta_por_cobrar` (036) | ✔ **delta 2026-09-11** |

## Cobertura

| | |
|---|---:|
| Requisitos | 41 |
| Con implementación y prueba | **41** |
| Huérfanos | **0** |
| Cobertura | **100 %** |
