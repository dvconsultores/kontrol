# DATA MODEL — 003-INVENTARIO-LOGISTICA

| Campo | Valor |
|---|---|
| Iniciativa | 003-inventario-logistica |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Responsable | Arquitecto de datos |
| Ruta | `specs/003-inventario-logistica/data-model.md` |
| Fuente | DOC-03 §5, §12-13; DOC-02 §8 |

## 1. Principios (heredados de 001/002/DOC-03)

- UUID interno; códigos de negocio separados; multiempresa (`company_id` en cada agregado).
- RIF, cédulas, teléfonos, cuentas, códigos, **seriales e IMEI son texto**.
- Movimientos de inventario **inmutables**; corrección mediante reverso vinculado (Constitución P5).
- Los saldos **no se editan**; se calculan desde movimientos. `InventoryBalance` es cache reconstruible.
- Tipos de movimiento, métodos de costeo, políticas FEFO y estados: versionados, no hardcodeados (P8).
- Datos críticos (lotes, seriales, vencimientos, costos) en estructura **columnar**; prohibido JSON/EAV libre.
- Auditoría uniforme (`created_at/by`, `updated_at/by`); versión/ETag en entidades editables.

## 2. Entidades — Custodia (maestros)

| Entidad | Campos mínimos | Notas |
|---|---|---|
| `Warehouse` | id, company_id, branch_id, establishment_id, code, name, type, allow_negative, use_locations, use_picking, status | Custodia de inventario (DOC-02 §3) |
| `Location` | id, warehouse_id, aisle, rack, zone, capacity, restrictions, picking_flag, status | Pasillo/estante/zona (DOC-02 §3) |

Regla: almacén y ubicación pertenecen a una sola empresa/sucursal/establecimiento.

## 3. Entidades — Movimientos y balance

| Entidad | Campos mínimos | Notas |
|---|---|---|
| `MovementType` | id, company_id/global, code, name, direction (IN/OUT/INTERNAL), version, status | Tipos versionados, no hardcodeados |
| `InventoryMovement` | id, company_id, warehouse_id, location_id, product_id, movement_type_id, quantity, unit_id, unit_cost, currency, fiscal_rate, document_ref, occurred_at, reversed_by_id, status | Movimiento balanceado e inmutable |
| `InventoryBalance` | id, company_id, warehouse_id, location_id, product_id, lot_id, serial_id, state, qty_on_hand, qty_reserved, qty_available, last_rebuilt_at | Proyección/cache reconstruible |

Reglas: `quantity != 0`; reverso vinculado (`reversed_by_id`); `available = on_hand − reserved` (salvo política).

## 4. Entidades — Lotes, seriales y vencimiento

| Entidad | Campos mínimos | Notas |
|---|---|---|
| `InventoryLot` | id, company_id, product_id, lot_number, manufacture_date, expiry_date, supplier_id, receipt_ref, status | Unicidad según política |
| `ProductSerial` | id, company_id, product_id, serial, imei1, imei2, mac, lot_id, status, warehouse_id, purchase_line_id, sale_line_id, warranty_until | Unicidad por tenant/producto o global; historial completo |

Reglas: lote único por producto/proveedor/fabricante según política; serial/IMEI único según definición del perfil; vencimiento coherente (fabricación ≤ vencimiento); estados DISPONIBLE/RESERVADO/TRANSITO/CUARENTENA/VENCIDO/RECHAZADO/DESECHO.

## 5. Entidades — Reservas, transferencias, conteos y ajustes

| Entidad | Campos mínimos | Notas |
|---|---|---|
| `Reservation` | id, company_id, source_document, product_id, warehouse_id, lot_id, serial_id, quantity, status, expires_at | Reserva sin cambio físico |
| `Transfer` | id, company_id, origin_warehouse, destination_warehouse, request_ref, shipment_ref, receipt_ref, status | Máquina de estados DOC-03 §13 |
| `TransferLine` | transfer_id, product_id, lot_id, serial_id, quantity_sent, quantity_received, difference, destination_state | Diferencias con destino |
| `StockCount` | id, company_id, warehouse_id, plan_ref, scope, freeze_policy, status | Conteo |
| `StockCountLine` | count_id, product_id, location_id, lot_id, expected_qty, counted_qty, variance | Diferencia |
| `InventoryAdjustment` | id, company_id, reason, evidence_ref, cost, approver_id, status | Motivo/evidencia/costo/aprobación |

Reglas: reservas ≤ disponible salvo política; ajuste genera movimiento (nunca edición de saldo); segregación: crea Almacén, revisa Costos/auditor, aprueba Aprobador.

## 6. Entidades — Costos

| Entidad | Campos mínimos | Notas |
|---|---|---|
| `CostLayer` | id, company_id, product_id, warehouse_id, receipt_ref, quantity_in, quantity_remaining, unit_cost, currency, fiscal_rate, landed_cost, status | Capas de costo |
| `CostingProfile` (versión) | company_id/product_id, method (AVERAGE/FIFO), currency, effective_from/to, status | Método versionado; default promedio ponderado |

Regla: el costo de salida se calcula desde las capas (promedio o FIFO según perfil) en el momento de la salida; moneda y tasa históricas; decimal exacto.

## 7. Reglas de integridad críticas

| Regla | Restricción |
|---|---|
| Movimiento balanceado | `quantity != 0`; entradas y salidas consistentes por documento |
| Inmutabilidad | No UPDATE/DELETE físico de movimientos; solo reverso vinculado |
| Serial/IMEI | Unique por tenant/producto o global según política; historial completo |
| Lote | Unique por producto/proveedor/fabricante según política; vencimiento coherente |
| Reserva | No excede disponible salvo política aprobada; operación atómica y bloqueo concurrente |
| Balance | `available = on_hand − reserved`; cache reconstruible desde movimientos |
| Multiempresa | FK críticas confirman misma empresa/tenant |
| Vigencia (perfiles/políticas) | No solapar versiones activas incompatibles para la misma clave |
| Costo | Capas con `quantity_remaining ≥ 0`; método versionado sin reescritura histórica |
