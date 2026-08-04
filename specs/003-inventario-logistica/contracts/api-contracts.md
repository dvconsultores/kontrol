# CONTRATOS DE API — 003-INVENTARIO-LOGISTICA (v1)

| Campo | Valor |
|---|---|
| Iniciativa | 003-inventario-logistica |
| Versión | 1.0 (borrador documental) |
| Ruta | `specs/003-inventario-logistica/contracts/api-contracts.md` |
| Fuente | DOC-03 §14 (convenciones) |

> Convenciones heredadas de 001: REST/JSON versionada; IDs opacos; timestamps ISO 8601 con zona; errores con `code`, `message`, `field_errors`, `correlation_id`; listados con `q`, `status`, `sort`, `page`, `page_size`; `allowed_actions` en backend; POST críticos con `Idempotency-Key`; transiciones por endpoints explícitos.

## 1. Existencias y kardex

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/v1/inventory/balances` | Existencias con filtros `q`, `product_id`, `warehouse_id`, `location_id`, `lot_id`, `serial_id`, `state`, `status`, `sort`, `page`, `page_size` |
| GET | `/api/v1/inventory/balances/{id}` | Detalle de balance (on_hand, reserved, available) |
| GET | `/api/v1/inventory/balances/summary` | Resumen por producto/almacén |
| GET | `/api/v1/inventory/movements` | Kardex: historial por producto/lote/serial/almacén con paginación |
| GET | `/api/v1/inventory/movements/{id}` | Detalle de movimiento (incluye reverso) |
| POST | `/api/v1/inventory/movements/reverse` | Reverso vinculado de un movimiento (`Idempotency-Key` requerida) |

## 2. Lotes y seriales

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/v1/inventory/lots` | Lotes con filtros (producto, estado, vencimiento, proveedor) |
| POST | `/api/v1/inventory/lots` | Crear lote (unicidad según política) |
| POST | `/api/v1/inventory/lots/{id}/transition` | Transición de estado autorizada |
| GET | `/api/v1/inventory/serials` | Seriales/IMEI con filtros (producto, estado, lote, almacén) |
| POST | `/api/v1/inventory/serials` | Crear serial (unicidad según política) |

## 3. Reservas

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/v1/inventory/reservations` | Reservar inventario (documento origen, líneas lote/serial, `Idempotency-Key`) |
| POST | `/api/v1/inventory/reservations/{id}/release` | Liberar reserva |
| POST | `/api/v1/inventory/reservations/{id}/expire` | Expirar reserva (por política) |
| GET | `/api/v1/inventory/reservations` | Reservas activas/históricas |

## 4. Transferencias

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/v1/inventory/transfers` | Crear solicitud de transferencia (DRAFT) |
| POST | `/api/v1/inventory/transfers/{id}/submit` | Enviar a aprobación |
| POST | `/api/v1/inventory/transfers/{id}/approve` | Aprobar |
| POST | `/api/v1/inventory/transfers/{id}/confirm-ship` | Confirmar envío (→ IN_TRANSIT) |
| POST | `/api/v1/inventory/transfers/{id}/confirm-receipt` | Confirmar recepción (→ PARTIALLY_RECEIVED/RECEIVED), diferencias |
| POST | `/api/v1/inventory/transfers/{id}/close` | Cerrar |
| GET | `/api/v1/inventory/transfers` | Listado con estados |

## 5. Conteos y ajustes

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/v1/inventory/counts` | Crear plan de conteo (alcance, política de congelamiento) |
| POST | `/api/v1/inventory/counts/{id}/freeze` | Congelar/leer |
| POST | `/api/v1/inventory/counts/{id}/lines` | Registrar líneas contadas |
| POST | `/api/v1/inventory/counts/{id}/submit` | Enviar diferencias |
| POST | `/api/v1/inventory/counts/{id}/approve` | Aprobar → genera ajustes |
| POST | `/api/v1/inventory/adjustments` | Crear ajuste (motivo, evidencia, costo) |
| POST | `/api/v1/inventory/adjustments/{id}/submit` | Enviar a revisión (Costos/auditor) |
| POST | `/api/v1/inventory/adjustments/{id}/approve` | Aprobar → genera movimiento |

## 6. Almacenes y ubicaciones

| Método | Ruta | Descripción |
|---|---|---|
| GET/POST | `/api/v1/inventory/warehouses` | Listar/crear almacenes |
| GET/PATCH | `/api/v1/inventory/warehouses/{id}` | Detalle/actualizar (versión/ETag) |
| POST | `/api/v1/inventory/warehouses/{id}/deactivate` | Desactivar (sin relaciones) |
| GET/POST | `/api/v1/inventory/locations` | Listar/crear ubicaciones |
| GET/PATCH | `/api/v1/inventory/locations/{id}` | Detalle/actualizar |

## 7. Costos

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/v1/inventory/cost-layers` | Capas de costo por producto/almacén |
| GET | `/api/v1/inventory/cost-layers/valuation` | Valoración del inventario según método del perfil |
| GET/POST | `/api/v1/inventory/costing-profiles` | Perfiles de costeo versionados |

## 8. Integración v1 (para 004/005)

Servicios de dominio invocables por compras/ventas (no duplican lógica de saldos):

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/v1/inventory/operations/receive` | Entrada por recepción (origen: GoodsReceipt 004); crea lotes/seriales, capas y balance |
| POST | `/api/v1/inventory/operations/reserve` | Reserva por orden aprobada (origen: SalesOrder 005) |
| POST | `/api/v1/inventory/operations/release` | Liberación (cancelación/vencimiento) |
| POST | `/api/v1/inventory/operations/pick` | Confirmación de picking (ubicación/lote/serial) |
| POST | `/api/v1/inventory/operations/ship` | Salida (→ tránsito o entregado-no-facturado); valida FEFO/bloqueos; calcula costo de salida |

Todas aceptan `Idempotency-Key`; responden con `movement_ids` y `reservation_ids` generados.
