# DATA MODEL — 004-COMPRAS-CUENTAS-POR-PAGAR

| Campo | Valor |
|---|---|
| Iniciativa | 004-compras-cuentas-por-pagar |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Responsable | Arquitecto de datos |
| Ruta | `specs/004-compras-cuentas-por-pagar/data-model.md` |
| Fuente | DOC-03 §8-9, §12-13; DOC-02 §6, §9 |

## 1. Principios (heredados de 001/002/003/DOC-03)

- UUID interno; códigos de negocio separados; multiempresa (`company_id` en cada agregado).
- Moneda de denominación/fiscal/pago separadas; tasa **histórica** por documento (P4).
- Snapshot por línea: producto, precio, impuesto y tasa aplicados (P4/P8).
- Documentos postados **inmutables**; corrección mediante reverso/nota vinculada (P5).
- Saldos de CxP calculados desde documentos y aplicaciones; nunca se editan.
- Reglas de aprobación y retención **versionadas**; prohibido hardcodear (P8).

## 2. Entidades — Requisición, cotización y orden

| Entidad | Campos mínimos | Notas |
|---|---|---|
| `PurchaseRequisition` | id, company_id, requester_id, cost_center_id, need_date, status, approval | DRAFT → SUBMITTED → APPROVED/REJECTED |
| `RequisitionLine` | requisition_id, product_id/service_id, quantity, unit_id, notes | |
| `SupplierQuote` | id, company_id, supplier_id, validity, currency, terms, status | Ofertas |
| `QuoteLine` | quote_id, product_id, quantity, unit_price, discount, tax_ref, delivery | |
| `PurchaseOrder` | id, company_id, code, supplier_id, terms, expected_date, currency, approval, status | DOC-03 §13 máquina de estados |
| `PurchaseOrderLine` | order_id, product_id/service_id, quantity_ordered, quantity_received, unit_price, tax_ref, snapshot | Cantidades y snapshot |

Reglas: aprobación por regla versionada (monto/categoría/excepción); OC no sustituye recepción ni factura.

## 3. Entidades — Recepción y factura del proveedor

| Entidad | Campos mínimos | Notas |
|---|---|---|
| `GoodsReceipt` | id, company_id, order_id, warehouse_id, status, quality_status | Invoca 003 `receive` |
| `GoodsReceiptLine` | receipt_id, order_line_id, product_id, quantity_accepted, quantity_rejected, lot_id, serial_id, quality | Lotes/seriales/vencimiento/calidad |
| `SupplierInvoice` | id, company_id, supplier_id, invoice_number, control_number, issue_date, currency, tax_total, status | Unique duplicidad |
| `SupplierInvoiceLine` | invoice_id, order_line_id/receipt_line_id, product_id, quantity, unit_price, tax_amount, snapshot | |

Regla: Unique `(company_id, supplier_id, invoice_number, control_number)` con excepciones documentadas; estados DOC-03 §13.

## 4. Entidades — Conciliación triple y devoluciones

| Entidad | Campos mínimos | Notas |
|---|---|---|
| `TripleMatch` | id, company_id, order_line_id, receipt_line_id, invoice_line_id, variance_qty, variance_price, variance_tax, resolution, approval | Diferencias explícitas |
| `Return` | id, company_id, source_document, reason, condition, inventory_destination, status | Devolución (física via 003) |
| `ReturnLine` | return_id, product_id, quantity, condition | |
| `SupplierCreditNote` | id, company_id, supplier_id, invoice_ref, number, amount, currency, status | Reduce CxP; no sustituida por devolución física |

## 5. Entidades — CxP (open items, pagos, aplicaciones)

| Entidad | Campos mínimos | Notas |
|---|---|---|
| `OpenItem` | id, company_id, party_id, source_document, type PAYABLE, currency, original, applied, balance, due_date, status | Saldo calculado |
| `Payment` | id, company_id, party_id, direction OUT, date, currency, amount, status, idempotency_key | Pago registrado en 004 (006 concilia) |
| `PaymentInstrument` | payment_id, method, account/cashbox, currency, amount, rate, reference, value_date | Medios/monedas |
| `Application` | id, company_id, source (payment/credit/advance/withholding), target open_item, amounts (source/target/fiscal), rate, date | Atómica; no excede saldo |
| `Advance` | id, company_id, party_id, direction OUT, currency, amount, available, status | Anticipo a proveedor |
| `PaymentSchedule` | id, company_id, party_id, due_date, amount, status | Programación |
| `AgingView` | derivado: buckets 0-30/31-60/61-90/>90 | Consulta |

Reglas: `balance = original − applied`; aplicación atómica con bloqueo; idempotencia en pago; saldo CxP = facturas + débitos − pagos − retenciones − créditos.

## 6. Entidades — Retención (referida a reglas versionadas)

| Entidad | Campos mínimos | Notas |
|---|---|---|
| `Withholding` | id, company_id, party_id, source_event, documents, rule_ref, base, rate_ref, amount, certificate, period, status | Estados DOC-03 §13 |
| `WithholdingRule` (referencia) | IVA/ISLR, concepto, condiciones, base, tarifa, mínimo, sustraendo, vigencia | Regla versionada; motor fiscal en 007 |

Regla: la retención se calcula por regla versionada (referencia a 007), no por porcentaje hardcodeado.

## 7. Reglas de integridad críticas

| Regla | Restricción |
|---|---|
| Factura proveedor | Unique `(company, supplier, invoice_number, control_number)` con excepciones documentadas |
| Aplicación | No excede saldo de origen ni destino; operación atómica y bloqueo concurrente |
| Nota | No ajusta por encima de cantidades/base/IVA pendientes del original |
| Inmutabilidad | No UPDATE/DELETE físico de documentos postados; reverso/nota vinculada |
| Saldo CxP | Calculado desde documentos y aplicaciones; nunca se edita |
| Multiempresa | FK críticas confirman misma empresa/tenant |
| Vigencia (reglas) | No solapar versiones activas incompatibles para la misma clave |
| Snapshot | Cada línea conserva producto/precio/impuesto/tasa aplicados |
