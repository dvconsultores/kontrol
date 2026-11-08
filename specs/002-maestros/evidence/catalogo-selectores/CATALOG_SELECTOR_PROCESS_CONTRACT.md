# Selectores de catálogo · contrato por proceso

El único filtro real del modelo es `item_type` (`PRODUCT` o `SERVICE`). No existen indicadores de comprable o vendible: no se inventan.

| PROCESS | ALLOWED_ITEM_TYPES | ACTIVE_ONLY | INVENTORY_REQUIRED | PURCHASABLE | SELLABLE | OTHER_FILTER | SOURCE_REQUIREMENT |
|---|---|---|---|---|---|---|---|
| Transferencias, Seriales, Ajustes, Conteos, Lotes, Reservas, Movimientos | PRODUCT | Sí | Sí | — | — | — | `inventory._require_product` rechaza lo que no sea `PRODUCT` (Spec 003). Hoy la pantalla ofrece servicios que el backend rechaza |
| Órdenes, cotizaciones y facturas de compra | PRODUCT y SERVICE | Sí | No | — | — | — | `purchasing._require_product` solo exige la empresa; data-model 004: `product_id/service_id` |
| Devolución de compra | PRODUCT y SERVICE (sin cambio) | Sí | — | — | — | — | Sin validación en backend; se conserva el comportamiento y se registra la deuda |
| Cotización, orden y factura de venta | PRODUCT y SERVICE | Sí | No | — | — | — | FR-005-034 (líneas mixtas; el servicio no afecta inventario); `needs_inventory` en la orden |

`ACTIVE_ONLY` lo garantiza el endpoint de búsqueda. Antes también: todas pedían `status=ACTIVE`.
