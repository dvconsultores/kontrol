# MATRIZ DE MIGRACIÓN POR TABLA — ARCH-MC-001

Las 166 tablas del modelo. Ninguna queda sin clasificar.

## approvals (8)

| Tabla | Modelo | Estado actual | Alcance objetivo | Forma | Autoridad | Acción |
|---|---|---|---|---|---|---|
| `approval_decisions` | `ApprovalDecision` | sin columna de ámbito | `COMPANY_SCOPE` | DERIVED | `step_id` → `approval_steps` | Declarar y probar la ruta; sin columna nueva |
| `approval_delegations` | `ApprovalDelegation` | company_id + FK | `COMPANY_SCOPE` | DIRECT | companies.id | Verificar datos y consultas |
| `approval_events` | `ApprovalEvent` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `approval_levels` | `ApprovalLevel` | sin columna de ámbito | `COMPANY_SCOPE` | DERIVED | `rule_id` → `approval_rules` | Declarar y probar la ruta; sin columna nueva |
| `approval_policies` | `ApprovalPolicy` | company_id + FK | `COMPANY_SCOPE` | DIRECT | companies.id | Verificar datos y consultas |
| `approval_requests` | `ApprovalRequest` | company_id + FK | `COMPANY_SCOPE` | DIRECT | companies.id | Verificar datos y consultas |
| `approval_rules` | `ApprovalRule` | sin columna de ámbito | `COMPANY_SCOPE` | DERIVED | `policy_id` → `approval_policies` | Declarar y probar la ruta; sin columna nueva |
| `approval_steps` | `ApprovalStep` | sin columna de ámbito | `COMPANY_SCOPE` | DERIVED | `request_id` → `approval_requests` | Declarar y probar la ruta; sin columna nueva |

## audit (1)

| Tabla | Modelo | Estado actual | Alcance objetivo | Forma | Autoridad | Acción |
|---|---|---|---|---|---|---|
| `audit_events` | `AuditEvent` | company_id (texto) = tenant_id | `TENANT_SCOPE` | DIRECT | tenants.id | Declarar alcance; sin cambio de datos |

## documents (8)

| Tabla | Modelo | Estado actual | Alcance objetivo | Forma | Autoridad | Acción |
|---|---|---|---|---|---|---|
| `document_categories` | `DocumentCategory` | company_id + FK | `COMPANY_SCOPE` | DIRECT | companies.id | Verificar datos y consultas |
| `document_links` | `DocumentLink` | company_id + FK | `COMPANY_SCOPE` | DIRECT | companies.id | Verificar datos y consultas |
| `document_types` | `DocumentType` | company_id + FK | `COMPANY_SCOPE` | DIRECT | companies.id | Verificar datos y consultas |
| `document_versions` | `DocumentVersion` | company_id + FK | `COMPANY_SCOPE` | DIRECT | companies.id | Verificar datos y consultas |
| `documents` | `Document` | company_id + FK | `COMPANY_SCOPE` | DIRECT | companies.id | Verificar datos y consultas |
| `file_security_scans` | `FileSecurityScan` | sin columna de ámbito | `COMPANY_SCOPE` | DERIVED | `stored_file_id` → `stored_files` | Declarar y probar la ruta; sin columna nueva |
| `legacy_document_references` | `LegacyDocumentReference` | company_id (texto) = tenant_id | `TENANT_SCOPE` | DIRECT | tenants.id | Renombrar `company_id`→`tenant_id` con FK a tenants |
| `stored_files` | `StoredFile` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |

## fiscal (13)

| Tabla | Modelo | Estado actual | Alcance objetivo | Forma | Autoridad | Acción |
|---|---|---|---|---|---|---|
| `control_number_batches` | `ControlNumberBatch` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `control_numbers` | `ControlNumber` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `credit_debit_notes` | `CreditDebitNote` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `fiscal_documents` | `FiscalDocument` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `fiscal_number_series` | `FiscalNumberSeries` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `fiscal_periods` | `FiscalPeriod` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `legal_sources` | `LegalSource` | sin columna de ámbito | `INSTALLATION_SCOPE` | DIRECT | — | Declarar alcance; sin cambio de datos |
| `print_events` | `PrintEvent` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `tax_calculations` | `TaxCalculation` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `tax_profiles` | `TaxProfile` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `tax_return_batches` | `TaxReturnBatch` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `tax_rule_versions` | `TaxRuleVersion` | sin columna de ámbito | `GLOBAL_SCOPE` | DIRECT | — | Declarar alcance; sin cambio de datos |
| `withholding_rules` | `WithholdingRule` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |

## homologation (3)

| Tabla | Modelo | Estado actual | Alcance objetivo | Forma | Autoridad | Acción |
|---|---|---|---|---|---|---|
| `homologation_events` | `HomologationEvent` | sin columna de ámbito | `INSTALLATION_SCOPE` | DIRECT | — | Declarar alcance; sin cambio de datos |
| `homologation_records` | `HomologationRecord` | sin columna de ámbito | `INSTALLATION_SCOPE` | DIRECT | — | Declarar alcance; sin cambio de datos |
| `release_versions` | `ReleaseVersion` | sin columna de ámbito | `INSTALLATION_SCOPE` | DIRECT | — | Declarar alcance; sin cambio de datos |

## identity_access (8)

| Tabla | Modelo | Estado actual | Alcance objetivo | Forma | Autoridad | Acción |
|---|---|---|---|---|---|---|
| `password_resets` | `PasswordReset` | sin columna de ámbito | `TENANT_SCOPE` | DIRECT | tenants.id | Declarar alcance; sin cambio de datos |
| `permissions` | `Permission` | sin columna de ámbito | `GLOBAL_SCOPE` | DIRECT | — | Declarar alcance; sin cambio de datos |
| `role_permissions` | `RolePermission` | sin columna de ámbito | `TENANT_SCOPE` | DIRECT | tenants.id | Declarar alcance; sin cambio de datos |
| `roles` | `Role` | company_id (texto) = tenant_id | `TENANT_SCOPE` | DIRECT | tenants.id | Renombrar `company_id`→`tenant_id` con FK a tenants |
| `sessions` | `Session` | sin columna de ámbito | `TENANT_SCOPE` | DIRECT | tenants.id | Declarar alcance; sin cambio de datos |
| `user_roles` | `UserRole` | company_id (texto) = tenant_id | `TENANT_SCOPE` | DIRECT | tenants.id | Declarar alcance; sin cambio de datos |
| `user_scopes` | `UserScope` | company_id (texto) = tenant_id | `TENANT_SCOPE` | DIRECT | tenants.id | Declarar alcance; sin cambio de datos |
| `users` | `User` | tenant_id | `TENANT_SCOPE` | DIRECT | tenants.id | Declarar alcance; sin cambio de datos |

## inventory (13)

| Tabla | Modelo | Estado actual | Alcance objetivo | Forma | Autoridad | Acción |
|---|---|---|---|---|---|---|
| `cost_layers` | `CostLayer` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `costing_profiles` | `CostingProfile` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `inventory_adjustments` | `InventoryAdjustment` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `inventory_balances` | `InventoryBalance` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `inventory_lots` | `InventoryLot` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `inventory_movements` | `InventoryMovement` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `movement_types` | `MovementType` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `product_serials` | `ProductSerial` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `reservations` | `Reservation` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `stock_count_lines` | `StockCountLine` | sin columna de ámbito | `COMPANY_SCOPE` | DERIVED | `count_id` → `stock_counts` | Declarar y probar la ruta; sin columna nueva |
| `stock_counts` | `StockCount` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `transfer_lines` | `TransferLine` | sin columna de ámbito | `COMPANY_SCOPE` | DERIVED | `transfer_id` → `transfers` | Declarar y probar la ruta; sin columna nueva |
| `transfers` | `Transfer` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |

## licensing (7)

| Tabla | Modelo | Estado actual | Alcance objetivo | Forma | Autoridad | Acción |
|---|---|---|---|---|---|---|
| `license_artifacts` | `LicenseArtifact` | sin columna de ámbito | `INSTALLATION_SCOPE` | DIRECT | — | Declarar alcance; sin cambio de datos |
| `license_central_config` | `LicenseCentralConfig` | sin columna de ámbito | `INSTALLATION_SCOPE` | DIRECT | — | Declarar alcance; sin cambio de datos |
| `license_entitlement_snapshots` | `LicenseEntitlementSnapshot` | sin columna de ámbito | `INSTALLATION_SCOPE` | DIRECT | — | Declarar alcance; sin cambio de datos |
| `license_events` | `LicenseEvent` | sin columna de ámbito | `INSTALLATION_SCOPE` | DIRECT | — | Declarar alcance; sin cambio de datos |
| `license_renewal_requests` | `LicenseRenewalRequest` | sin columna de ámbito | `INSTALLATION_SCOPE` | DIRECT | — | Declarar alcance; sin cambio de datos |
| `license_states` | `LicenseState` | sin columna de ámbito | `INSTALLATION_SCOPE` | DIRECT | — | Declarar alcance; sin cambio de datos |
| `license_sync_runs` | `LicenseSyncRun` | sin columna de ámbito | `INSTALLATION_SCOPE` | DIRECT | — | Declarar alcance; sin cambio de datos |

## master_data (24)

| Tabla | Modelo | Estado actual | Alcance objetivo | Forma | Autoridad | Acción |
|---|---|---|---|---|---|---|
| `attribute_applicabilities` | `AttributeApplicability` | sin columna de ámbito | `COMPANY_SCOPE` | DERIVED | `attribute_id` → `attribute_definitions` | Declarar y probar la ruta; sin columna nueva |
| `attribute_definitions` | `AttributeDefinition` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `attribute_values` | `AttributeValue` | sin columna de ámbito | `COMPANY_SCOPE` | DERIVED | `item_id` → `catalog_items` | Declarar y probar la ruta; sin columna nueva |
| `barcodes` | `Barcode` | sin columna de ámbito | `COMPANY_SCOPE` | DERIVED | `item_id` → `catalog_items` | Declarar y probar la ruta; sin columna nueva |
| `carriers` | `Carrier` | sin columna de ámbito | `COMPANY_SCOPE` | DERIVED | `party_id` → `parties` | Declarar y probar la ruta; sin columna nueva |
| `catalog_items` | `CatalogItem` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `customers` | `Customer` | sin columna de ámbito | `COMPANY_SCOPE` | DERIVED | `party_id` → `parties` | Declarar y probar la ruta; sin columna nueva |
| `drivers` | `Driver` | sin columna de ámbito | `COMPANY_SCOPE` | DERIVED | `party_id` → `parties` | Declarar y probar la ruta; sin columna nueva |
| `parties` | `Party` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `party_addresses` | `PartyAddress` | sin columna de ámbito | `COMPANY_SCOPE` | DERIVED | `party_id` → `parties` | Declarar y probar la ruta; sin columna nueva |
| `party_bank_accounts` | `PartyBankAccount` | sin columna de ámbito | `COMPANY_SCOPE` | DERIVED | `party_id` → `parties` | Declarar y probar la ruta; sin columna nueva |
| `party_contacts` | `PartyContact` | sin columna de ámbito | `COMPANY_SCOPE` | DERIVED | `party_id` → `parties` | Declarar y probar la ruta; sin columna nueva |
| `presentations` | `Presentation` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `product_presentation_versions` | `ProductPresentationVersion` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `product_templates` | `ProductTemplate` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `product_variants` | `ProductVariant` | sin columna de ámbito | `COMPANY_SCOPE` | DERIVED | `parent_product_id` → `catalog_items` | Declarar y probar la ruta; sin columna nueva |
| `products` | `Product` | sin columna de ámbito | `COMPANY_SCOPE` | DERIVED | `item_id` → `catalog_items` | Declarar y probar la ruta; sin columna nueva |
| `profile_versions` | `ProfileVersion` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `service_templates` | `ServiceTemplate` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `services` | `Service` | sin columna de ámbito | `COMPANY_SCOPE` | DERIVED | `item_id` → `catalog_items` | Declarar y probar la ruta; sin columna nueva |
| `suppliers` | `Supplier` | sin columna de ámbito | `COMPANY_SCOPE` | DERIVED | `party_id` → `parties` | Declarar y probar la ruta; sin columna nueva |
| `taxonomy_nodes` | `TaxonomyNode` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `unit_conversions` | `UnitConversion` | sin columna de ámbito | `GLOBAL_SCOPE` | DIRECT | — | Declarar alcance; sin cambio de datos |
| `units_of_measure` | `UnitOfMeasure` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |

## purchasing (21)

| Tabla | Modelo | Estado actual | Alcance objetivo | Forma | Autoridad | Acción |
|---|---|---|---|---|---|---|
| `ap_advances` | `Advance` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `ap_applications` | `Application` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `ap_open_items` | `OpenItem` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `ap_payment_instruments` | `PaymentInstrument` | sin columna de ámbito | `COMPANY_SCOPE` | DERIVED | `payment_id` → `ap_payments` | Declarar y probar la ruta; sin columna nueva |
| `ap_payment_schedules` | `PaymentSchedule` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `ap_payments` | `Payment` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `ap_withholdings` | `Withholding` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `goods_receipt_lines` | `GoodsReceiptLine` | sin columna de ámbito | `COMPANY_SCOPE` | DERIVED | `receipt_id` → `goods_receipts` | Declarar y probar la ruta; sin columna nueva |
| `goods_receipts` | `GoodsReceipt` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `purchase_order_lines` | `PurchaseOrderLine` | sin columna de ámbito | `COMPANY_SCOPE` | DERIVED | `order_id` → `purchase_orders` | Declarar y probar la ruta; sin columna nueva |
| `purchase_orders` | `PurchaseOrder` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `purchase_requisition_lines` | `RequisitionLine` | sin columna de ámbito | `COMPANY_SCOPE` | DERIVED | `requisition_id` → `purchase_requisitions` | Declarar y probar la ruta; sin columna nueva |
| `purchase_requisitions` | `PurchaseRequisition` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `purchase_return_lines` | `PurchaseReturnLine` | sin columna de ámbito | `COMPANY_SCOPE` | DERIVED | `return_id` → `purchase_returns` | Declarar y probar la ruta; sin columna nueva |
| `purchase_returns` | `PurchaseReturn` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `supplier_credit_notes` | `SupplierCreditNote` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `supplier_invoice_lines` | `SupplierInvoiceLine` | sin columna de ámbito | `COMPANY_SCOPE` | DERIVED | `invoice_id` → `supplier_invoices` | Declarar y probar la ruta; sin columna nueva |
| `supplier_invoices` | `SupplierInvoice` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `supplier_quote_lines` | `QuoteLine` | sin columna de ámbito | `COMPANY_SCOPE` | DERIVED | `quote_id` → `supplier_quotes` | Declarar y probar la ruta; sin columna nueva |
| `supplier_quotes` | `SupplierQuote` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `triple_matches` | `TripleMatch` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |

## regulatory (11)

| Tabla | Modelo | Estado actual | Alcance objetivo | Forma | Autoridad | Acción |
|---|---|---|---|---|---|---|
| `official_documents` | `OfficialDocument` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `official_registrations` | `OfficialRegistration` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `permit_instances` | `PermitInstance` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `permit_types` | `PermitType` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `regulatory_approval_requests` | `RegulatoryApprovalRequest` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `regulatory_authorities` | `RegulatoryAuthority` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `regulatory_contingencies` | `RegulatoryContingency` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `regulatory_evaluations` | `RegulatoryEvaluation` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `regulatory_profiles` | `RegulatoryProfile` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `transport_drivers` | `TransportDriver` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `transport_vehicles` | `TransportVehicle` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |

## reporting (3)

| Tabla | Modelo | Estado actual | Alcance objetivo | Forma | Autoridad | Acción |
|---|---|---|---|---|---|---|
| `report_definitions` | `ReportDefinition` | company_id (texto) = tenant_id | `TENANT_SCOPE` | DIRECT | tenants.id | Renombrar `company_id`→`tenant_id` con FK a tenants |
| `report_exports` | `ReportExport` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `report_jobs` | `ReportJob` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |

## sales (14)

| Tabla | Modelo | Estado actual | Alcance objetivo | Forma | Autoridad | Acción |
|---|---|---|---|---|---|---|
| `pick_list_lines` | `PickListLine` | sin columna de ámbito | `COMPANY_SCOPE` | DERIVED | `picklist_id` → `pick_lists` | Declarar y probar la ruta; sin columna nueva |
| `pick_lists` | `PickList` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `sales_credit_notes` | `SalesCreditNote` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `sales_debit_notes` | `SalesDebitNote` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `sales_invoice_lines` | `SalesInvoiceLine` | sin columna de ámbito | `COMPANY_SCOPE` | DERIVED | `invoice_id` → `sales_invoices` | Declarar y probar la ruta; sin columna nueva |
| `sales_invoices` | `SalesInvoice` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `sales_order_lines` | `SalesOrderLine` | sin columna de ámbito | `COMPANY_SCOPE` | DERIVED | `order_id` → `sales_orders` | Declarar y probar la ruta; sin columna nueva |
| `sales_orders` | `SalesOrder` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `sales_quote_lines` | `SalesQuoteLine` | sin columna de ámbito | `COMPANY_SCOPE` | DERIVED | `quote_id` → `sales_quotes` | Declarar y probar la ruta; sin columna nueva |
| `sales_quotes` | `SalesQuote` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `sales_return_lines` | `SalesReturnLine` | sin columna de ámbito | `COMPANY_SCOPE` | DERIVED | `return_id` → `sales_returns` | Declarar y probar la ruta; sin columna nueva |
| `sales_returns` | `SalesReturn` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `shipment_lines` | `ShipmentLine` | sin columna de ámbito | `COMPANY_SCOPE` | DERIVED | `shipment_id` → `shipments` | Declarar y probar la ruta; sin columna nueva |
| `shipments` | `Shipment` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |

## system (4)

| Tabla | Modelo | Estado actual | Alcance objetivo | Forma | Autoridad | Acción |
|---|---|---|---|---|---|---|
| `feature_flags` | `FeatureFlag` | sin columna de ámbito | `INSTALLATION_SCOPE` | DIRECT | — | Declarar alcance; sin cambio de datos |
| `idempotency_records` | `IdempotencyRecord` | company_id (texto) = tenant_id | `TENANT_SCOPE` | DIRECT | tenants.id | Renombrar `company_id`→`tenant_id` con FK a tenants |
| `outbox_events` | `OutboxEvent` | company_id (texto) = tenant_id | `TENANT_SCOPE` | DIRECT | tenants.id | Renombrar `company_id`→`tenant_id` con FK a tenants |
| `system_settings` | `SystemSetting` | tenant_id | `INSTALLATION_SCOPE` | DIRECT | — | Declarar alcance; sin cambio de datos |

## treasury (15)

| Tabla | Modelo | Estado actual | Alcance objetivo | Forma | Autoridad | Acción |
|---|---|---|---|---|---|---|
| `bank_transactions` | `BankTransaction` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `cash_session_movements` | `CashSessionMovement` | sin columna de ámbito | `COMPANY_SCOPE` | DERIVED | `session_id` → `cash_sessions` | Declarar y probar la ruta; sin columna nueva |
| `cash_sessions` | `CashSession` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `cashboxes` | `Cashbox` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `currencies` | `Currency` | company_id (texto) = tenant_id | `TENANT_SCOPE` | DIRECT | tenants.id | Renombrar `company_id`→`tenant_id` con FK a tenants |
| `exchange_rates` | `ExchangeRate` | company_id (texto) = tenant_id | `TENANT_SCOPE` | DIRECT | tenants.id | Renombrar `company_id`→`tenant_id` con FK a tenants |
| `financial_accounts` | `FinancialAccount` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `financial_banks` | `FinancialBank` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `fiscal_rules` | `FiscalRule` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `igft_events` | `IgftEvent` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `payment_methods` | `PaymentMethod` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `reconciliation_lines` | `ReconciliationLine` | sin columna de ámbito | `COMPANY_SCOPE` | DERIVED | `reconciliation_id` → `reconciliations` | Declarar y probar la ruta; sin columna nueva |
| `reconciliations` | `Reconciliation` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `treasury_instruments` | `TreasuryInstrument` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |
| `treasury_transfers` | `TreasuryTransfer` | company_id (texto) = tenant_id | `COMPANY_SCOPE` | DIRECT | companies.id | Backfill + FK + NOT NULL + reescribir writers |

## — (13)

| Tabla | Modelo | Estado actual | Alcance objetivo | Forma | Autoridad | Acción |
|---|---|---|---|---|---|---|
| `branches` | `—` | company_id + FK | `COMPANY_SCOPE` | DIRECT | companies.id | Verificar datos y consultas |
| `companies` | `—` | tenant_id | `INSTALLATION_SCOPE` | DIRECT | — | Declarar alcance; sin cambio de datos |
| `establishments` | `—` | sin columna de ámbito | `COMPANY_SCOPE` | DERIVED | `branch_id` → `branches` | Declarar y probar la ruta; sin columna nueva |
| `installations` | `—` | sin columna de ámbito | `INSTALLATION_SCOPE` | DIRECT | — | Declarar alcance; sin cambio de datos |
| `location_types` | `—` | company_id + FK | `COMPANY_SCOPE` | DIRECT | companies.id | Verificar datos y consultas |
| `tenants` | `—` | sin columna de ámbito | `INSTALLATION_SCOPE` | DIRECT | — | Declarar alcance; sin cambio de datos |
| `warehouse_aisles` | `—` | company_id + FK | `COMPANY_SCOPE` | DIRECT | companies.id | Verificar datos y consultas |
| `warehouse_levels` | `—` | company_id + FK | `COMPANY_SCOPE` | DIRECT | companies.id | Verificar datos y consultas |
| `warehouse_locations` | `—` | company_id + FK | `COMPANY_SCOPE` | DIRECT | companies.id | Verificar datos y consultas |
| `warehouse_racks` | `—` | company_id + FK | `COMPANY_SCOPE` | DIRECT | companies.id | Verificar datos y consultas |
| `warehouse_zones` | `—` | company_id + FK | `COMPANY_SCOPE` | DIRECT | companies.id | Verificar datos y consultas |
| `warehouses` | `—` | company_id + FK | `COMPANY_SCOPE` | DIRECT | companies.id | Verificar datos y consultas |
| `zone_types` | `—` | company_id + FK | `COMPANY_SCOPE` | DIRECT | companies.id | Verificar datos y consultas |
