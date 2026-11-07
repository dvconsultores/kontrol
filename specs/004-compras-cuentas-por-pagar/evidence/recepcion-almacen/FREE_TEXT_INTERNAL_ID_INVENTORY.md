# Identificadores internos escritos a mano

| Pantalla | Campo | Clasificación | Motivo |
|---|---|---|---|
| Recepciones | Línea de la orden | REAL_DEFECT | Obligatorio para recibir. La orden ya trae `lines` en `PurchaseOrderSummary`: el dato existe. Bloquea el proceso |
| Devoluciones de venta | Factura | POSSIBLE_DEFECT | Obligatorio, sin revisar si la factura se puede llegar a conocer por otra vía |
| Notas de venta | Factura | POSSIBLE_DEFECT | Igual |
| Listas de precio | Artículo | POSSIBLE_DEFECT | Obligatorio; existe catálogo |
| Lotes | Proveedor | POSSIBLE_DEFECT | Opcional; existe maestro |
| Valorización | Producto | POSSIBLE_DEFECT | Opcional, «global si vacío» |

Ninguno se corrigió en este ciclo.

## Actualización 2026-11-07 (ciclo RECEPCION-LINEA-ORDEN-INTEGRIDAD-01)

Recepciones · Línea de la orden: corregido en local. El resto sigue sin corregir y sin clasificar más allá de lo anterior.

Identificador mostrado, no pedido: la columna «Orden» de la tabla de Recepciones enseña los ocho primeros caracteres de `order_id`. Es lectura, no bloquea operar, y queda como deuda de presentación.
