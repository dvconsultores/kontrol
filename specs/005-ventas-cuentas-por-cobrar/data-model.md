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
