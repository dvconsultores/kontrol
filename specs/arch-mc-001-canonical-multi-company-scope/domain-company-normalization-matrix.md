# MATRIZ DE NORMALIZACIÓN POR DOMINIO — ARCH-MC-001

Las 133 entidades de alcance de empresa, agrupadas por dominio y ola.

| Dominio | Entidades | Directas | Derivadas | Riesgo | Ola |
|---|---:|---:|---:|---|---:|
| **master_data** | 23 | 10 | 13 | Medio — identidad compartida | 2 |
| **fiscal** | 11 | 11 | 0 | **Crítico** — RIF, series, libros | 3 |
| **purchasing** | 21 | 14 | 7 | Alto — obligaciones | 4 |
| **inventory** | 13 | 11 | 2 | Alto — existencias | 5 |
| **sales** | 14 | 8 | 6 | Alto — facturación | 6 |
| **treasury** | 13 | 11 | 2 | Alto — dinero | 7 |
| **regulatory** | 11 | 11 | 0 | Alto — permisos por RIF | 8 |
| **approvals** | 8 | 4 | 4 | Bajo | 9 |
| **documents** | 7 | 6 | 1 | Medio | 9 |
| **reporting** | 2 | 2 | 0 | Bajo | 9 |
| **—** | 10 | 9 | 1 | Bajo | 9 |
| **Total** | **133** | **97** | **36** | | |

## Detalle por dominio

### master_data — ola 2 · Medio — identidad compartida

| Entidad | Alcance actual | Forma objetivo | Autoridad | Migración |
|---|---|---|---|---|
| `AttributeApplicability` | sin columna de ámbito | DERIVED | `attribute_id` → `attribute_definitions` | Declarar y probar la ruta; sin columna nueva |
| `AttributeDefinition` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `AttributeValue` | sin columna de ámbito | DERIVED | `item_id` → `catalog_items` | Declarar y probar la ruta; sin columna nueva |
| `Barcode` | sin columna de ámbito | DERIVED | `item_id` → `catalog_items` | Declarar y probar la ruta; sin columna nueva |
| `Carrier` | sin columna de ámbito | DERIVED | `party_id` → `parties` | Declarar y probar la ruta; sin columna nueva |
| `CatalogItem` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `Customer` | sin columna de ámbito | DERIVED | `party_id` → `parties` | Declarar y probar la ruta; sin columna nueva |
| `Driver` | sin columna de ámbito | DERIVED | `party_id` → `parties` | Declarar y probar la ruta; sin columna nueva |
| `Party` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `PartyAddress` | sin columna de ámbito | DERIVED | `party_id` → `parties` | Declarar y probar la ruta; sin columna nueva |
| `PartyBankAccount` | sin columna de ámbito | DERIVED | `party_id` → `parties` | Declarar y probar la ruta; sin columna nueva |
| `PartyContact` | sin columna de ámbito | DERIVED | `party_id` → `parties` | Declarar y probar la ruta; sin columna nueva |
| `Presentation` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `ProductPresentationVersion` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `ProductTemplate` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `ProductVariant` | sin columna de ámbito | DERIVED | `parent_product_id` → `catalog_items` | Declarar y probar la ruta; sin columna nueva |
| `Product` | sin columna de ámbito | DERIVED | `item_id` → `catalog_items` | Declarar y probar la ruta; sin columna nueva |
| `ProfileVersion` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `ServiceTemplate` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `Service` | sin columna de ámbito | DERIVED | `item_id` → `catalog_items` | Declarar y probar la ruta; sin columna nueva |
| `Supplier` | sin columna de ámbito | DERIVED | `party_id` → `parties` | Declarar y probar la ruta; sin columna nueva |
| `TaxonomyNode` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `UnitOfMeasure` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |

### fiscal — ola 3 · **Crítico** — RIF, series, libros

| Entidad | Alcance actual | Forma objetivo | Autoridad | Migración |
|---|---|---|---|---|
| `ControlNumberBatch` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `ControlNumber` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `CreditDebitNote` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `FiscalDocument` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `FiscalNumberSeries` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `FiscalPeriod` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `PrintEvent` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `TaxCalculation` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `TaxProfile` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `TaxReturnBatch` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `WithholdingRule` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |

### purchasing — ola 4 · Alto — obligaciones

| Entidad | Alcance actual | Forma objetivo | Autoridad | Migración |
|---|---|---|---|---|
| `Advance` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `Application` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `OpenItem` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `PaymentInstrument` | sin columna de ámbito | DERIVED | `payment_id` → `ap_payments` | Declarar y probar la ruta; sin columna nueva |
| `PaymentSchedule` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `Payment` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `Withholding` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `GoodsReceiptLine` | sin columna de ámbito | DERIVED | `receipt_id` → `goods_receipts` | Declarar y probar la ruta; sin columna nueva |
| `GoodsReceipt` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `PurchaseOrderLine` | sin columna de ámbito | DERIVED | `order_id` → `purchase_orders` | Declarar y probar la ruta; sin columna nueva |
| `PurchaseOrder` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `RequisitionLine` | sin columna de ámbito | DERIVED | `requisition_id` → `purchase_requisitions` | Declarar y probar la ruta; sin columna nueva |
| `PurchaseRequisition` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `PurchaseReturnLine` | sin columna de ámbito | DERIVED | `return_id` → `purchase_returns` | Declarar y probar la ruta; sin columna nueva |
| `PurchaseReturn` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `SupplierCreditNote` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `SupplierInvoiceLine` | sin columna de ámbito | DERIVED | `invoice_id` → `supplier_invoices` | Declarar y probar la ruta; sin columna nueva |
| `SupplierInvoice` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `QuoteLine` | sin columna de ámbito | DERIVED | `quote_id` → `supplier_quotes` | Declarar y probar la ruta; sin columna nueva |
| `SupplierQuote` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `TripleMatch` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |

### inventory — ola 5 · Alto — existencias

| Entidad | Alcance actual | Forma objetivo | Autoridad | Migración |
|---|---|---|---|---|
| `CostLayer` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `CostingProfile` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `InventoryAdjustment` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `InventoryBalance` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `InventoryLot` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `InventoryMovement` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `MovementType` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `ProductSerial` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `Reservation` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `StockCountLine` | sin columna de ámbito | DERIVED | `count_id` → `stock_counts` | Declarar y probar la ruta; sin columna nueva |
| `StockCount` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `TransferLine` | sin columna de ámbito | DERIVED | `transfer_id` → `transfers` | Declarar y probar la ruta; sin columna nueva |
| `Transfer` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |

### sales — ola 6 · Alto — facturación

| Entidad | Alcance actual | Forma objetivo | Autoridad | Migración |
|---|---|---|---|---|
| `PickListLine` | sin columna de ámbito | DERIVED | `picklist_id` → `pick_lists` | Declarar y probar la ruta; sin columna nueva |
| `PickList` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `SalesCreditNote` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `SalesDebitNote` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `SalesInvoiceLine` | sin columna de ámbito | DERIVED | `invoice_id` → `sales_invoices` | Declarar y probar la ruta; sin columna nueva |
| `SalesInvoice` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `SalesOrderLine` | sin columna de ámbito | DERIVED | `order_id` → `sales_orders` | Declarar y probar la ruta; sin columna nueva |
| `SalesOrder` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `SalesQuoteLine` | sin columna de ámbito | DERIVED | `quote_id` → `sales_quotes` | Declarar y probar la ruta; sin columna nueva |
| `SalesQuote` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `SalesReturnLine` | sin columna de ámbito | DERIVED | `return_id` → `sales_returns` | Declarar y probar la ruta; sin columna nueva |
| `SalesReturn` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `ShipmentLine` | sin columna de ámbito | DERIVED | `shipment_id` → `shipments` | Declarar y probar la ruta; sin columna nueva |
| `Shipment` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |

### treasury — ola 7 · Alto — dinero

| Entidad | Alcance actual | Forma objetivo | Autoridad | Migración |
|---|---|---|---|---|
| `BankTransaction` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `CashSessionMovement` | sin columna de ámbito | DERIVED | `session_id` → `cash_sessions` | Declarar y probar la ruta; sin columna nueva |
| `CashSession` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `Cashbox` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `FinancialAccount` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `FinancialBank` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `FiscalRule` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `IgftEvent` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `PaymentMethod` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `ReconciliationLine` | sin columna de ámbito | DERIVED | `reconciliation_id` → `reconciliations` | Declarar y probar la ruta; sin columna nueva |
| `Reconciliation` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `TreasuryInstrument` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `TreasuryTransfer` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |

### regulatory — ola 8 · Alto — permisos por RIF

| Entidad | Alcance actual | Forma objetivo | Autoridad | Migración |
|---|---|---|---|---|
| `OfficialDocument` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `OfficialRegistration` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `PermitInstance` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `PermitType` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `RegulatoryApprovalRequest` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `RegulatoryAuthority` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `RegulatoryContingency` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `RegulatoryEvaluation` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `RegulatoryProfile` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `TransportDriver` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `TransportVehicle` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |

### approvals — ola 9 · Bajo

| Entidad | Alcance actual | Forma objetivo | Autoridad | Migración |
|---|---|---|---|---|
| `ApprovalDecision` | sin columna de ámbito | DERIVED | `step_id` → `approval_steps` | Declarar y probar la ruta; sin columna nueva |
| `ApprovalDelegation` | company_id + FK | DIRECT | companies.id | Verificar datos y consultas |
| `ApprovalEvent` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `ApprovalLevel` | sin columna de ámbito | DERIVED | `rule_id` → `approval_rules` | Declarar y probar la ruta; sin columna nueva |
| `ApprovalPolicy` | company_id + FK | DIRECT | companies.id | Verificar datos y consultas |
| `ApprovalRequest` | company_id + FK | DIRECT | companies.id | Verificar datos y consultas |
| `ApprovalRule` | sin columna de ámbito | DERIVED | `policy_id` → `approval_policies` | Declarar y probar la ruta; sin columna nueva |
| `ApprovalStep` | sin columna de ámbito | DERIVED | `request_id` → `approval_requests` | Declarar y probar la ruta; sin columna nueva |

### documents — ola 9 · Medio

| Entidad | Alcance actual | Forma objetivo | Autoridad | Migración |
|---|---|---|---|---|
| `DocumentCategory` | company_id + FK | DIRECT | companies.id | Verificar datos y consultas |
| `DocumentLink` | company_id + FK | DIRECT | companies.id | Verificar datos y consultas |
| `DocumentType` | company_id + FK | DIRECT | companies.id | Verificar datos y consultas |
| `DocumentVersion` | company_id + FK | DIRECT | companies.id | Verificar datos y consultas |
| `Document` | company_id + FK | DIRECT | companies.id | Verificar datos y consultas |
| `FileSecurityScan` | sin columna de ámbito | DERIVED | `stored_file_id` → `stored_files` | Declarar y probar la ruta; sin columna nueva |
| `StoredFile` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |

### reporting — ola 9 · Bajo

| Entidad | Alcance actual | Forma objetivo | Autoridad | Migración |
|---|---|---|---|---|
| `ReportExport` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `ReportJob` | company_id (texto) = tenant_id | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |

### — — ola 9 · Bajo

| Entidad | Alcance actual | Forma objetivo | Autoridad | Migración |
|---|---|---|---|---|
| `—` | company_id + FK | DIRECT | companies.id | Verificar datos y consultas |
| `—` | sin columna de ámbito | DERIVED | `branch_id` → `branches` | Declarar y probar la ruta; sin columna nueva |
| `—` | company_id + FK | DIRECT | companies.id | Verificar datos y consultas |
| `—` | company_id + FK | DIRECT | companies.id | Verificar datos y consultas |
| `—` | company_id + FK | DIRECT | companies.id | Verificar datos y consultas |
| `—` | company_id + FK | DIRECT | companies.id | Verificar datos y consultas |
| `—` | company_id + FK | DIRECT | companies.id | Verificar datos y consultas |
| `—` | company_id + FK | DIRECT | companies.id | Verificar datos y consultas |
| `—` | company_id + FK | DIRECT | companies.id | Verificar datos y consultas |
| `—` | company_id + FK | DIRECT | companies.id | Verificar datos y consultas |
