# Recepción · contrato final de campos

| Campo | SOURCE_OF_TRUTH | USER_EDITABLE | DERIVED | REQUIRED | NULLABLE | VALIDATION | OWNER_SPEC |
|---|---|---|---|---|---|---|---|
| `code` | Operador | Sí | No | Sí | No | API | 004 |
| `order_id` | Búsqueda de órdenes recibibles | Elige | No | Sí | No | `ORDER_NOT_RECEIVABLE` | 004 |
| `warehouse_id` | Almacenes activos de la empresa | Elige | No | Sí | No | `WAREHOUSE_NOT_FOUND`, `WAREHOUSE_NOT_ELIGIBLE` | 004/008 |
| `packing_list_ref` | Documento | Sí | No | No | Sí | Texto | 019 |
| `supplier_invoice_ref` | Documento | Sí | No | No | Sí | Texto | 019 |
| `packages_declared` | Documento | Sí | No | No | Sí | ≥ 0 | 019 |
| `unloading_scheduled_at` | Operador | Sí | No | No | Sí | Hora de Caracas | 019 |
| `arrival_at` | Sistema al confirmar | No | Sí | No | Sí | Una vez | 019 |
| `packages_received` | Conteo | Sí | No | No | Sí | ≥ 0 | 019 |
| Comparaciones de inspección | Operador | Sí | No | No | Sí: no comparado | Una por comparación | 019 |
| `order_line_id` | Orden de la recepción | Elige | No | Sí | No | `PURCHASE_ORDER_LINE_NOT_FOUND` | 019 |
| `product_id` | `PurchaseOrderLine.product_id` | No | Sí | Sí | No | `RECEIPT_LINE_PRODUCT_MISMATCH`, `RECEIPT_LINE_INTEGRITY` | 019 |
| `presentation_id` | Presentaciones del producto | Elige | No | No | Sí: unidad base | `CONVERSION_NOT_RESOLVABLE` | 011 |
| `physical_condition` | Operador | Sí | No | No | Sí: no observado | Máx. 24 | 019 |
| `damaged_quantity` | Operador | Sí | No | No | Sí | ≥ 0, ≤ recibido | 019 |
| `damage_notes` | Operador | Sí | No | No | Sí | Máx. 2000 | 019 |
| `identification_ok` | Operador | Sí | No | No | Sí: no observada | Booleano | 019 |
| `reference_ok` | Operador | Sí | No | No | Sí: no observada | Booleano | 019 |
| `lot_number` | Operador | Sí | No | No | Sí | Máx. 120 | 019 |
| `expiry_date` | Operador | Sí | No | No | Sí | Fecha | 019 |
| `serials` | Operador | Sí | No | No | Sí | Lista | 019 |
| `quantity_received` | Operador | Sí | No | Sí | No | > 0 | 019 |
| `quantity_accepted` | Operador, o lo recibido | Sí | Si vacío | Sí | No | ≥ 0 | 019 |
| `quantity_rejected` | Recibido − aceptado | No | Sí | Sí | No | Aceptado + rechazado ≤ recibido | 019 |

Ningún campo lo inventa la pantalla.
