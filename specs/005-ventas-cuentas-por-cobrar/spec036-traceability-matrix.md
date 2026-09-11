# SPEC 036 · TRAZABILIDAD DE IMPLEMENTACIÓN

| Requisito | Autoridad | Implementación | Prueba | Estado |
|---|---|---|---|---|
| IMP-036-001 · la solicitud no mueve inventario | norma §15 «Solicitud» es el primer acto | `request_return` | `test_la_solicitud_no_mueve_una_sola_unidad` | ✔ |
| IMP-036-002 · la recepción devuelve la custodia | `D0-10` `DESPACHADO → DEVUELTO` · 036 | `receive_return` | `test_recibir_devuelve_la_custodia_pero_no_la_disponibilidad` | ✔ |
| IMP-036-003 · recibir no hace vendible | `R-D0-10-3` «vendible es exclusivamente `DISPONIBLE`» | ídem | ídem | ✔ |
| IMP-036-004 · la verificación precede al reingreso | norma §15 · `D0-10` «requiere la inspección previa» | `inspect_return` | `test_la_entrada_de_inventario_es_el_cuarto_acto_y_respeta_el_dictamen` | ✔ |
| IMP-036-005 · la aprobación precede al reingreso | norma §15 «Aprobación → Entrada de inventario» | `decide_return` | `test_no_se_reingresa_sin_aprobacion` | ✔ |
| IMP-036-006 · solo la entrada de inventario crea existencia | norma §15 | `reenter_return` | `test_la_entrada_de_inventario_es_el_cuarto_acto…` | ✔ |
| IMP-036-007 · los destinos son los dos que `D0-10` concede | `D0-10` `DEVUELTO → DISPONIBLE · RECHAZADO` | `RETURN_DISPOSITIONS` | `test_el_destino_de_la_mercancia_devuelta_no_se_inventa` | ✔ |
| IMP-036-008 · no se inventan estados de mercancía | `D0-10` | `ACTIVE_TRANSITIONS` | `test_no_se_inventan_estados_de_mercancia` | ✔ |
| IMP-036-009 · el dictamen lo valida el backend | doctrina | `RETURN_DISPOSITION_INVALID` | `test_el_cliente_no_elige_el_estado_de_la_mercancia` | ✔ |
| IMP-036-010 · lo aceptado puede ser menos que lo recibido | «verificación física» | `accepted_base_quantity` | `test_la_entrada_de_inventario_es_el_cuarto_acto…` | ✔ |
| IMP-036-011 · la devolución es en cantidad **base** | Spec 011 · lección de la 035 | `_base_de_linea` | `test_devolver_una_caja_de_doce_reingresa_doce` | ✔ |
| IMP-036-012 · el factor se congela de la factura | Spec 011 | `conversion_factor_snapshot` copiado | ídem | ✔ |
| IMP-036-013 · no se devuelve más de lo despachado | regla de integridad «pendientes del original» | `RETURN_EXCEEDS_DISPATCHED` | `test_no_se_devuelve_mas_de_lo_despachado` | ✔ |
| IMP-036-014 · el tope es acumulativo | ídem | `_devuelto_acumulado` | `test_dos_devoluciones_no_suman_mas_de_lo_despachado` | ✔ |
| IMP-036-015 · las canceladas no cuentan | ídem | filtro de estado | `test_una_devolucion_cancelada_libera_lo_que_reservaba` | ✔ |
| IMP-036-016 · no se devuelve lo que no salió | ¶106 · `D0-10` | `RETURN_NOT_DISPATCHED` | `return_eligibility` | ✔ |
| IMP-036-017 · la reserva `FULFILLED` no se toca | `D0-03` §H «nueva fila, nunca reactivación» | — | `test_la_devolucion_no_reabre_la_reserva_consumida` | ✔ |
| IMP-036-018 · el pedido no revierte su historia | `D0-03` · `ADR-D0-012` | — | ídem · `test_la_devolucion_no_revierte_el_pedido` | ✔ |
| IMP-036-019 · aceptar la devolución no emite la nota | maestro «la devolución física no sustituye una nota de crédito» | actos separados | `test_aceptar_la_devolucion_no_emite_la_nota` | ✔ |
| IMP-036-020 · la nota referencia la factura original | norma §5 «Referenciar la factura original» | `SalesCreditNote.invoice_id` | `credit_note_dict` | ✔ |
| IMP-036-021 · el impuesto se reparte proporcionalmente | norma §5 «recalcular proporcionalmente base imponible e IVA» | `proporcion` sobre `linea.tax_amount` | `test_la_nota_reparte_el_impuesto_de_la_factura_en_proporcion` | ✔ |
| IMP-036-022 · se mantiene la clasificación tributaria original | norma §5 | no se llama a `calculate_tax` | `test_la_nota_conserva_la_clasificacion_de_la_factura_aunque_la_regla_cambie` | ✔ |
| IMP-036-023 · no se acredita por encima de lo pendiente | regla de integridad «Nota» | `CREDIT_EXCEEDS_INVOICE` | `test_no_se_acredita_por_encima_de_lo_pendiente` | ✔ |
| IMP-036-024 · la nota puede existir sin devolución | norma §5, ocho causas | `return_id` anulable | `test_la_nota_existe_sin_devolucion` | ✔ |
| IMP-036-025 · la nota lleva consecutivo propio | norma §5 «Tener consecutivo propio» | Spec 042 | `test_la_nota_lleva_consecutivo_y_control_propios` | ✔ |
| IMP-036-026 · la nota lleva número de control | norma §5 | Spec 042 | ídem | ✔ |
| IMP-036-027 · no gasta el correlativo de las facturas | numeración por tipo | `SERIES_DOCUMENT_TYPE_MISMATCH` | `test_la_nota_no_se_emite_con_la_serie_de_las_facturas` | ✔ |
| IMP-036-028 · emitir es idempotente | doctrina · Spec 042 | `issued_at` primero | `test_emitir_dos_veces_no_gasta_dos_numeros` | ✔ |
| IMP-036-029 · `CREDITED` solo al acreditar entera | `INVOICE_TRANSITIONS`, estado terminal | comprobación de pendiente | `test_la_factura_queda_acreditada_solo_cuando_se_acredita_entera` | ✔ |
| IMP-036-030 · la nota ajusta la cuenta por cobrar | norma §15 «Ajuste de cuenta por cobrar» | `_aplicar_nota_a_cxc` | `test_la_nota_reduce_la_cuenta_por_cobrar` | ✔ |
| IMP-036-031 · la factura original no se reescribe | doctrina fiscal | — | `test_la_factura_original_no_se_reescribe` | ✔ |
| IMP-036-032 · la nota de débito no toca inventario | norma §15, su flujo no tiene etapa física | — | `test_la_nota_de_debito_no_toca_el_inventario` | ✔ |
| IMP-036-033 · la nota de débito exige su factura | norma §6 «no puede utilizarse como una factura independiente» | `DEBIT_NOTE_WITHOUT_INVOICE` | `test_la_nota_de_debito_no_es_una_factura_independiente` | ✔ |
| IMP-036-034 · la nota de débito crea su propio documento por cobrar | norma §15 «Cuenta por cobrar» | `OpenItem` propio | `test_la_nota_de_debito_aumenta_la_cuenta_por_cobrar` | ✔ |
| IMP-036-035 · el motivo es obligatorio | norma §5 «Indicar el motivo» | `CAUSE_REQUIRED` | `generate_credit_note` | ✔ |
| IMP-036-036 · el contexto de empresa es la autoridad | `ARCH-MC-001` | `_company` en cada entrada | `test_no_se_devuelve_una_factura_de_otra_empresa` | ✔ |
| IMP-036-037 · recibir es idempotente | doctrina | `received_at` primero | `test_recibir_dos_veces_no_devuelve_la_mercancia_dos_veces` | ✔ |
| IMP-036-038 · reingresar es idempotente | doctrina | `reentered_at` primero | `test_reingresar_dos_veces_no_crea_existencia_dos_veces` | ✔ |
| IMP-036-039 · denegar exige motivo | doctrina de los controles | `RETURN_REJECTION_REASON_REQUIRED` | `test_denegar_una_devolucion_exige_motivo…` | ✔ |
| IMP-036-040 · la 036 no cobra ni devuelve dinero | Spec 038 es la dueña | — | `test_la_036_no_cobra_ni_devuelve_dinero` | ✔ |
| IMP-036-041 · la migración es aditiva | doctrina | columnas anulables, sin backfill | `test_la_migracion_es_aditiva_y_no_inventa_historia` | ✔ |
| IMP-036-042 · los permisos existen en el catálogo | `ARCH-MC-001` | solo permisos declarados | `test_los_permisos_de_la_devolucion_existen_en_el_catalogo` | ✔ |

## Deltas dirigidos sobre otras Specs

| Delta | Dueña | Por qué |
|---|---|---|
| `emit_document` acepta `CREDIT_NOTE` y `DEBIT_NOTE` | **042** | El modelo declaraba los tres tipos desde el principio y el motor solo sabía emitir el primero: el tipo estaba escrito a mano. Sin esto la 036 habría tenido que numerar por su cuenta |
| La serie se comprueba contra el tipo de documento | **042** | Una nota podía gastar el correlativo de las facturas |
| `issue_invoice` abre la cuenta por cobrar | **034** | «9. Emitir factura → **10. Crear CxC**» solo ocurría por el camino heredado. Las facturas emitidas por el proceso real nacían sin documento por cobrar, y se descubrió al ir a aplicarles una nota y no encontrar nada que ajustar |
| El bucle de paginación de `billing.spec.ts` | **034** | `isDisabled()` sobre un paginador inexistente agota el tiempo de la prueba cuando la cola cabe en una página |

## Cobertura

| | |
|---|---:|
| Requisitos funcionales | 42 |
| Con implementación y prueba | **42** |
| Huérfanos | **0** |
| Cobertura | **100 %** |
