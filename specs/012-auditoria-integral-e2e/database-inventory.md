# Inventario de Base de Datos — Spec 012 (pasada 2)

Modelos SQLAlchemy inventariados: **144 tablas** · 1678 columnas.
Nota: la herramienta reporta sobre metadata ORM (SQLite no concluye tipos reales PG).

## Resumen por prefijo de módulo

| Módulo (prefijo) | Tablas |
|---|---|
| `ap_*` | 7 |
| `approval_*` | 1 |
| `attribute_*` | 3 |
| `audit_*` | 1 |
| `bank_*` | 1 |
| `barcodes_*` | 1 |
| `branches_*` | 1 |
| `carriers_*` | 1 |
| `cash_*` | 2 |
| `cashboxes_*` | 1 |
| `catalog_*` | 1 |
| `companies_*` | 1 |
| `control_*` | 2 |
| `cost_*` | 1 |
| `costing_*` | 1 |
| `credit_*` | 1 |
| `currencies_*` | 1 |
| `customers_*` | 1 |
| `drivers_*` | 1 |
| `establishments_*` | 1 |
| `exchange_*` | 1 |
| `feature_*` | 1 |
| `file_*` | 1 |
| `financial_*` | 2 |
| `fiscal_*` | 4 |
| `goods_*` | 2 |
| `homologation_*` | 2 |
| `idempotency_*` | 1 |
| `igft_*` | 1 |
| `installations_*` | 1 |
| `inventory_*` | 4 |
| `legal_*` | 1 |
| `license_*` | 7 |
| `locations_*` | 1 |
| `movement_*` | 1 |
| `official_*` | 2 |
| `outbox_*` | 1 |
| `parties_*` | 1 |
| `party_*` | 3 |
| `password_*` | 1 |
| `payment_*` | 1 |
| `permissions_*` | 1 |
| `permit_*` | 2 |
| `pick_*` | 2 |
| `presentations_*` | 1 |
| `print_*` | 1 |
| `product_*` | 3 |
| `products_*` | 1 |
| `profile_*` | 1 |
| `purchase_*` | 6 |
| `reconciliation_*` | 1 |
| `reconciliations_*` | 1 |
| `regulatory_*` | 4 |
| `release_*` | 1 |
| `report_*` | 3 |
| `reservations_*` | 1 |
| `role_*` | 1 |
| `roles_*` | 1 |
| `sales_*` | 10 |
| `service_*` | 1 |
| `services_*` | 1 |
| `sessions_*` | 1 |
| `shipment_*` | 1 |
| `shipments_*` | 1 |
| `stock_*` | 2 |
| `supplier_*` | 5 |
| `suppliers_*` | 1 |
| `system_*` | 1 |
| `tax_*` | 4 |
| `taxonomy_*` | 1 |
| `tenants_*` | 1 |
| `transfer_*` | 1 |
| `transfers_*` | 1 |
| `transport_*` | 2 |
| `treasury_*` | 2 |
| `triple_*` | 1 |
| `unit_*` | 1 |
| `units_*` | 1 |
| `user_*` | 2 |
| `users_*` | 1 |
| `warehouses_*` | 1 |
| `withholding_*` | 1 |

## Drift ORM ↔ Alembic

- Head de migraciones: `0013_seed_business_permissions` (single head, sin ramas).
- Cadena 0001→0013 compila offline en dialecto PostgreSQL (`tests/test_migrations_offline.py`, 3 PASS).
- Money/tasas: **54 columnas Float restantes** (18 dinero crítico — ver KAUD-011); el resto en Numeric(18,2)/(14,6).
- `DateTime(timezone=True)` en ORM (48 usos); el reporte `DATETIME` (334) es falso positivo de SQLite.
- 1 columna BIGINT: `fiscal_number_series.next_number` (contador de correlativos).
- Verificación final de drift real (alembic check / upgrade) **pendiente en PostgreSQL** (ambiente autorizado).

## Tablas (muestra por módulo)

### `ap_*` (7)

- `ap_advances`
- `ap_applications`
- `ap_open_items`
- `ap_payment_instruments`
- `ap_payment_schedules`
- `ap_payments`
- `ap_withholdings`

### `approval_*` (1)

- `approval_requests`

### `attribute_*` (3)

- `attribute_applicabilities`
- `attribute_definitions`
- `attribute_values`

### `audit_*` (1)

- `audit_events`

### `bank_*` (1)

- `bank_transactions`

### `barcodes_*` (1)

- `barcodes`

### `branches_*` (1)

- `branches`

### `carriers_*` (1)

- `carriers`

### `cash_*` (2)

- `cash_session_movements`
- `cash_sessions`

### `cashboxes_*` (1)

- `cashboxes`

### `catalog_*` (1)

- `catalog_items`

### `companies_*` (1)

- `companies`

### `control_*` (2)

- `control_number_batches`
- `control_numbers`

### `cost_*` (1)

- `cost_layers`

### `costing_*` (1)

- `costing_profiles`

### `credit_*` (1)

- `credit_debit_notes`

### `currencies_*` (1)

- `currencies`

### `customers_*` (1)

- `customers`

### `drivers_*` (1)

- `drivers`

### `establishments_*` (1)

- `establishments`

### `exchange_*` (1)

- `exchange_rates`

### `feature_*` (1)

- `feature_flags`

### `file_*` (1)

- `file_metadata`

### `financial_*` (2)

- `financial_accounts`
- `financial_banks`

### `fiscal_*` (4)

- `fiscal_documents`
- `fiscal_number_series`
- `fiscal_periods`
- `fiscal_rules`

### `goods_*` (2)

- `goods_receipt_lines`
- `goods_receipts`

### `homologation_*` (2)

- `homologation_events`
- `homologation_records`

### `idempotency_*` (1)

- `idempotency_records`

### `igft_*` (1)

- `igft_events`

### `installations_*` (1)

- `installations`

### `inventory_*` (4)

- `inventory_adjustments`
- `inventory_balances`
- `inventory_lots`
- `inventory_movements`

### `legal_*` (1)

- `legal_sources`

### `license_*` (7)

- `license_artifacts`
- `license_central_config`
- `license_entitlement_snapshots`
- `license_events`
- `license_renewal_requests`
- `license_states`
- `license_sync_runs`

### `locations_*` (1)

- `locations`

### `movement_*` (1)

- `movement_types`

### `official_*` (2)

- `official_documents`
- `official_registrations`

### `outbox_*` (1)

- `outbox_events`

### `parties_*` (1)

- `parties`

### `party_*` (3)

- `party_addresses`
- `party_bank_accounts`
- `party_contacts`

### `password_*` (1)

- `password_resets`

### `payment_*` (1)

- `payment_methods`

### `permissions_*` (1)

- `permissions`

### `permit_*` (2)

- `permit_instances`
- `permit_types`

### `pick_*` (2)

- `pick_list_lines`
- `pick_lists`

### `presentations_*` (1)

- `presentations`

### `print_*` (1)

- `print_events`

### `product_*` (3)

- `product_serials`
- `product_templates`
- `product_variants`

### `products_*` (1)

- `products`

### `profile_*` (1)

- `profile_versions`

### `purchase_*` (6)

- `purchase_order_lines`
- `purchase_orders`
- `purchase_requisition_lines`
- `purchase_requisitions`
- `purchase_return_lines`
- `purchase_returns`

### `reconciliation_*` (1)

- `reconciliation_lines`

### `reconciliations_*` (1)

- `reconciliations`

### `regulatory_*` (4)

- `regulatory_authorities`
- `regulatory_contingencies`
- `regulatory_evaluations`
- `regulatory_profiles`

### `release_*` (1)

- `release_versions`

### `report_*` (3)

- `report_definitions`
- `report_exports`
- `report_jobs`

### `reservations_*` (1)

- `reservations`

### `role_*` (1)

- `role_permissions`

### `roles_*` (1)

- `roles`

### `sales_*` (10)

- `sales_credit_notes`
- `sales_debit_notes`
- `sales_invoice_lines`
- `sales_invoices`
- `sales_order_lines`
- `sales_orders`
- `sales_quote_lines`
- `sales_quotes`
- `sales_return_lines`
- `sales_returns`

### `service_*` (1)

- `service_templates`

### `services_*` (1)

- `services`

### `sessions_*` (1)

- `sessions`

### `shipment_*` (1)

- `shipment_lines`

### `shipments_*` (1)

- `shipments`

### `stock_*` (2)

- `stock_count_lines`
- `stock_counts`

### `supplier_*` (5)

- `supplier_credit_notes`
- `supplier_invoice_lines`
- `supplier_invoices`
- `supplier_quote_lines`
- `supplier_quotes`

### `suppliers_*` (1)

- `suppliers`

### `system_*` (1)

- `system_settings`

### `tax_*` (4)

- `tax_calculations`
- `tax_profiles`
- `tax_return_batches`
- `tax_rule_versions`

### `taxonomy_*` (1)

- `taxonomy_nodes`

### `tenants_*` (1)

- `tenants`

### `transfer_*` (1)

- `transfer_lines`

### `transfers_*` (1)

- `transfers`

### `transport_*` (2)

- `transport_drivers`
- `transport_vehicles`

### `treasury_*` (2)

- `treasury_instruments`
- `treasury_transfers`

### `triple_*` (1)

- `triple_matches`

### `unit_*` (1)

- `unit_conversions`

### `units_*` (1)

- `units_of_measure`

### `user_*` (2)

- `user_roles`
- `user_scopes`

### `users_*` (1)

- `users`

### `warehouses_*` (1)

- `warehouses`

### `withholding_*` (1)

- `withholding_rules`

