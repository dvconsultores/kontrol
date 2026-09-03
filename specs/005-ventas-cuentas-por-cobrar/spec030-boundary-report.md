# SPEC 030 — INFORME DE FRONTERAS

| Frontera | Cómo se respeta | Evidencia |
|---|---|---|
| **029** (cotización y conversión no reservan) | el disparador es posterior a `DRAFT`; la conversión sigue creando `DRAFT` sin reserva | `test_spec029_quote_order.py::test_convertir_no_reserva_inventario` (verde en la regresión) |
| **031** (cola y ruta de picking) | 030 entrega `RELEASED` + reservas `ACTIVE` por `source_line_id` en `order_dict`; no crea `PickList`, no asigna ubicación | `test_liberar_a_preparacion_no_crea_picking_factura_ni_cxc_y_despachar_consume` (conteo de `pick_lists`); `Reservation` sin `location_id` |
| **032** (extracción) | 030 no escribe estados de custodia; `PICKING_SHORTAGE` queda reservado como motivo para 032 | sin `record_movement` en el ciclo del pedido salvo despacho (035, ya existente) |
| **033** (confirmación independiente) | ninguna transición nueva entre `PREPARING` y `SHIPPED` | máquina de estados |
| **034** (facturación) | ninguna factura al liberar; la facturación no toca reservas | conteo de `sales_invoices` |
| **035** (despacho) | solo cambia la semántica del consumo (`FULFILLED` en vez de `RELEASED`), decidida en D0-03 | `test_liberar_a_preparacion_…` |
| **CxC** | ninguna partida abierta al liberar | conteo de `ap_open_items` |
| **045** | un solo motor; ventas pregunta y obedece | `credit-approval-integration-report.md` |
| **003/023** | un solo motor de inventario; 030 añade columnas, índices y bloqueo **sobre** él | `inventory/service.py` (sin contador paralelo) |
| **011** | `to_base` es la única autoridad de conversión; sin recálculo | `test_la_reserva_se_hace_en_cantidad_base_y_no_cambia_si_cambia_el_factor` |
| **Backorder / parcial / abastecimiento cruzado / FEFO** | no existen estados, colas ni rutas que los insinúen | `test_multilinea_…`, guardia estructural |
| **Planificador** | ninguno; `expire-reservations` es un endpoint idempotente | `test_no_hay_planificador_local` |
