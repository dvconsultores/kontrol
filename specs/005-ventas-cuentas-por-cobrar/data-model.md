# DATA MODEL — 005-VENTAS-CUENTAS-POR-COBRAR

| Campo | Valor |
|---|---|
| Iniciativa | 005-ventas-cuentas-por-cobrar |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Responsable | Arquitecto de datos |
| Ruta | `specs/005-ventas-cuentas-por-cobrar/data-model.md` |
| Fuente | DOC-03 §8, §12-13; DOC-02 §7, §9 |

## 1. Principios (heredados de 001/002/003/004/DOC-03)

- UUID interno; códigos de negocio separados; multiempresa (`company_id` en cada agregado).
- Moneda de denominación/fiscal/pago separadas; tasa **histórica** por documento (P4).
- Snapshot por línea: producto, precio, impuesto y tasa aplicados (P4/P8).
- Facturas emitidas y cobros **inmutables**; corrección por nota/anulación vinculada (P5).
- Saldos de CxC calculados desde documentos y aplicaciones; nunca se editan.
- Reglas de crédito y aprobación **versionadas**; prohibido hardcodear (P8).
- **CxC reutiliza el motor de 004** (`ap_open_items`, `ap_applications`, `ap_advances`, `ap_withholdings`).

## 2. Entidades — Cotización, pedido y orden de venta

| Entidad | Campos mínimos | Notas |
|---|---|---|
| `SalesQuote` | id, company_id, customer_id, price_list, validity, currency, status | No reserva inventario |
| `SalesQuoteLine` | quote_id, product_id/service_id, quantity, unit_price, discount, tax_ref | |
| `SalesOrder` | id, company_id, customer_id, credit_decision, margin, reservation, status | Máquina de estados DOC-03 §13 |
| `SalesOrderLine` | order_id, product_id/service_id, quantity, unit_price, discount, tax_ref, snapshot | |

Reglas: cotización sin reserva; OV pasa por CREDIT_PENDING; reserva al aprobar (via 003).

## 3. Entidades — Despacho (integración con 003)

| Entidad | Campos mínimos | Notas |
|---|---|---|
| `PickList` | id, company_id, order_id, warehouse_id, allocation lines, status | Vía 003 |
| `PickListLine` | picklist_id, product_id, lot_id, serial_id, quantity | Confirmación ubicación/lote/serial |
| `Shipment` | id, company_id, order_id, origin/destination, transport, regulatory dossier, lines, status | Salida → tránsito/entregado-no-facturado |

Regla: el despacho se bloquea si falta documento, vence o no coincide (DOC-01 §5); regulación funcional en 008.

## 4. Entidades — Factura de venta y notas

| Entidad | Campos mínimos | Notas |
|---|---|---|
| `SalesInvoice` | id, company_id, customer_id, base_fiscal (VES), tax_snapshot, status | Snapshot fiscal; emisión fiscal en 007 |
| `SalesInvoiceLine` | invoice_id, product_id/service_id, quantity, unit_price, tax_amount, base_fiscal, snapshot | Líneas mixtas |
| `SalesCreditNote` | id, company_id, customer_id, invoice_ref, number, amount, status | Reduce CxC |
| `SalesDebitNote` | id, company_id, customer_id, invoice_ref, number, amount, status | Aumenta CxC |
| `SalesReturn` | id, company_id, order/invoice ref, reason, condition, inventory_destination, status | Física vía 003 |

Regla: factura emitida inmutable; corrección por nota/anulación vinculada; la devolución física no sustituye la nota de crédito.

## 5. Entidades — CxC (reutiliza el motor de 004)

| Entidad | Campos mínimos | Notas |
|---|---|---|
| `OpenItem` (RECEIVABLE) | party_id, source_document, original, applied, balance, due_date, status | Tabla de 004; `item_type=RECEIVABLE` |
| `Cobro` = `Payment` (IN) | party_id, amount, instruments, idempotency_key, status | Dirección IN |
| `Application` | source (cobro/anticipo/nota/retención sufrida) → open_item | Tabla de 004; atómica |
| `Advance` (cliente) | party_id, direction IN, amount, available, status | Anticipo de cliente |
| `Withholding` (sufrida) | party_id, tax_type, base, amount, period, status | Retención sufrida |

Reglas: `balance = original − applied`; saldo CxC = documentos + débitos − cobros − retenciones − créditos; aplicación atómica con bloqueo; cobro idempotente.

## 6. Reglas de integridad críticas

| Regla | Restricción |
|---|---|
| Factura de venta | Emitida inmutable; nota/anulación vinculada; snapshot fiscal |
| Aplicación | No excede saldo de origen ni destino; operación atómica y bloqueo concurrente |
| Nota | No ajusta por encima de montos pendientes del original |
| Reserva | Al aprobar la OV (via 003); no altera existencia física |
| Despacho | Bloqueado si falta documento/venció/no coincide |
| Saldo CxC | Calculado desde documentos y aplicaciones; nunca se edita |
| Multiempresa | FK críticas confirman misma empresa/tenant |
| Snapshot | Cada línea conserva producto/precio/impuesto/tasa |

---

# DATA MODEL — SPEC 030 · DELTA CONCEPTUAL (D0-03 CLOSED, 2026-09-02)

Sin migración en este ciclo. Describe lo que la Spec 030 deberá materializar.

| Entidad | Cambio | Regla |
|---|---|---|
| `Reservation` (003) | + `source_type` (`SALES_ORDER`/`MANUAL`), `source_id`, `source_line_id` (FK `sales_order_lines`, nullable), `trigger` (`ORDER_CONFIRMATION`/`MANUAL`/`LEGACY_CREDIT_APPROVAL`), `oversell` bool, `released_at`, `released_by`, `release_reason`; se conserva `source_document` texto | índice único parcial `(source_line_id) WHERE status='ACTIVE'`; `CHECK (quantity > 0)`; campos Spec 011 obligatorios cuando `source_type = SALES_ORDER` |
| `InventoryBalance` (003) | sin columnas nuevas | índice único sobre `(company_id, warehouse_id, COALESCE(location_id,''), product_id, COALESCE(lot_id,''), COALESCE(serial_id,''), state)`; `CHECK (qty_reserved >= 0)` |
| `SalesOrder` (005) | `status`: valores `RELEASED` (rename de `RESERVED`), `EXPIRED`; + `reverted_reason`/`cancel_reason` (o en auditoría) | `warehouse_id` obligatorio al confirmar con inventario (regla de servicio, no `NOT NULL`: los borradores pueden no tenerlo) |
| Configuración de empresa | `reservation_ttl_days` entero nullable | defecto `NULL`; dónde vive (tabla de configuración por empresa o `settings` JSON gobernado) lo decide el plan de 030 respetando P8 |
| Permisos | `ventas:submit` | separado de `ventas:approve` |
| Auditoría | acciones `RESERVATION_CREATED/RELEASED/EXPIRED/FULFILLED`, `SALES_ORDER_REVERTED` | carga según `d0-03-reservation-decision.md` §7 |

Alcance de empresa: `Reservation` sigue siendo entidad directa (`__scope__ = COMPANY` con
`company_id`), igual al `company_id` del pedido y del almacén; no se añade `company_id` a ninguna
entidad derivada.

## Materializado por la Spec 030 (migración `0043_spec030_reservation`, 2026-09-02)

| Entidad | Planificado (D0-03) | Materializado |
|---|---|---|
| `Reservation` | `source_type`, `source_id`, `source_line_id`, `trigger`, `oversell`, `released_at/by`, `release_reason` | `source_type`, **`source_order_id`** (FK), `source_line_id` (FK), `trigger`, `oversell`, `released_at`, `released_by`, `release_reason`; `uq_reservations_active_line`; `ck_reservations_quantity_positive` |
| `InventoryBalance` | unicidad de clave; `CHECK ≥ 0` | `uq_inventory_balances_key` (COALESCE); `ck_inventory_balances_reserved_nonneg` |
| `SalesOrder` | `RELEASED`, `EXPIRED`; `reverted_reason/cancel_reason` | `RELEASED`, `EXPIRED`, sin `CREDIT_PENDING`; **`status_reason`** (un solo motivo visible), `submitted_at`, `released_at` |
| Configuración de empresa | `reservation_ttl_days` (ubicación por decidir) | `companies.reservation_ttl_days` |
| Permisos | `ventas:submit` | ídem, concedido a ADMIN |
| Auditoría | eventos de reserva | `RESERVATION_CREATED/RELEASED/EXPIRED/FULFILLED`, `SALES_ORDER_REVERTED`, `COMPANY_RESERVATION_POLICY_CHANGED` |
