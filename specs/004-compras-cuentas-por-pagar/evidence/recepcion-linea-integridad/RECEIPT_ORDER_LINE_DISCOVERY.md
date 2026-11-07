# Recepción: línea de la orden y producto · descubrimiento

Medido sobre el árbol local (`f442ffc`) antes de implementar.

| # | Pregunta | Respuesta | Evidencia |
|---|---|---|---|
| 1 | ¿La recepción expone `order_id`? | Sí, en listado y detalle | `GoodsReceiptSummary.order_id` |
| 2 | ¿La consulta actual contiene esa orden? | No es fiable. `/purchasing/orders` trae 20 por defecto y lo más reciente primero | `list_orders`, `page_size` 20 |
| 3 | ¿`PurchaseOrderSummary` incluye `lines`? | Sí, en `api/types.ts`. La interfaz local de la pantalla lo ocultaba | `order_dict` |
| 4 | ¿Cada línea incluye `product_id`? | Sí | `order_dict` |
| 5 | ¿`quantity_ordered`? | Sí | `order_dict` |
| 6 | ¿`quantity_received`? | Sí; acumula lo aceptado en unidad base | `accept_receipt` |
| 7 | ¿`needs_inventory`? | Sí; decide si aceptar mueve inventario, no si se puede recibir | `accept_receipt` |
| 8 | ¿Qué información humana hay? | Código y nombre del producto, y cantidades | `GET /maestros/catalogos/items/{id}` |
| 9 | ¿Productos ya cargados? | Solo los 20 primeros activos. No sirve: uno inactivo o posterior quedaría sin nombre | `list_items` |
| 10 | ¿Hace falta API nueva? | No. `GET /purchasing/orders/{id}` y `GET /maestros/catalogos/items/{id}` ya existen | — |
| 11 | ¿Líneas paginadas? | No: `order_dict` las devuelve todas | `order_dict` |
| 12 | ¿Saldo pendiente? | `quantity_ordered − quantity_received`, sin negativos | `_sobrante_observado` |
| 13 | ¿Se permiten sobrantes? | Sí: se registran, no se impiden | FR-019-012, `overage_base_quantity` |
| 14 | ¿Qué política gobierna la sobrerrecepción? | Ninguna tolerancia documentada; CL-004-12 sigue pendiente. 019 observa, 020 y 021 tratan | `spec019-implementation-cycle.md` §14-15 |

## Autoridades

- `RECEIPT_LINE_SELECTION_AUTHORITY = RECEIPT_PURCHASE_ORDER`: las opciones salen de la orden de `receipt.order_id`.
- `PRODUCT_SELECTION_AUTHORITY = ORDER_LINE`: `PurchaseOrderLine.product_id`. El contrato sigue llevando `product_id`, y el backend exige que coincida.
- `ORDER_LINE_ELIGIBILITY_RULE = ALL_LINES_OF_RECEIPT_ORDER`: una línea recibida del todo se ofrece con «pendiente 0». Ocultarla sería una regla que el backend no tiene y bloquearía registrar un sobrante.
- `OVER_RECEIPT_POLICY = REGISTER_NOT_PREVENT`.

## Mercancía equivocada

Si llega físicamente otro producto, el proceso no lo recibe como si fuera el de la línea ni como otro distinto contra esa línea. Se rechaza la cantidad y se usa la incidencia `REFERENCIA_INCORRECTA` de la Spec 020, o el tipo `SKU` del conteo de la Spec 021. Ambos existen. El invariante no los bloquea: ambos actúan sobre una línea recibida, no cambian su producto.

## Otra vía para conocer el identificador

Ninguna. Ninguna pantalla de Compras muestra los identificadores de línea de orden. `OPERATOR_CAN_COMPLETE_WITHOUT_INTERNAL_ID = 0`.

## Reproducción

**Interfaz:** 18 de 18 pruebas en rojo contra la pantalla real. `INTERNAL_ORDER_LINE_ID_REQUIRED = 1`, `VISIBLE_ORDER_LINE_SELECTOR = 0`, `PRODUCT_REQUIREMENT_VIOLATED = 1`, `RC-UI = PROVEN`.

**Backend:** BT-02, BT-06 y BT-10 en rojo. Medida directa, con línea A y producto B de la misma empresa:

| Medida | Resultado |
|---|---|
| Respuesta | Aceptada |
| Línea persistida | `order_line = A`, `product = B` |
| Movimiento al aceptar | Producto B, al costo unitario de la línea A (10,00) |
| Lote y serial | Creados para B |
| `quantity_received` | A = 5, B = 0 |
| Estado de la orden | `PARTIALLY_RECEIVED` |

`ORDER_LINE_PRODUCT_MISMATCH_ACCEPTED = 1`, `RC-INTEGRITY = PROVEN`.

## Protecciones existentes revalidadas a nivel de servicio

Línea de otra orden, línea de otra empresa, línea inexistente, producto de otra empresa y presentación de otro producto (`CONVERSION_NOT_RESOLVABLE`): todas pasan sin cambios.

## Efecto de arnés descartado

BT-11 cayó con `TypeError` en `_sync_order_status`. No es defecto de producto: en una sola sesión de prueba, la línea no tocada conserva el `0.0` float del constructor; cada petición real lee `Decimal`. Se corrigió en la fixture.
