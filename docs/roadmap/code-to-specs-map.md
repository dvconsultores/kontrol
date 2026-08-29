# MATRIZ CÓDIGO → 56 SPECS

## Backend — módulos (15) · 275 endpoints · 14.820 LOC

| Módulo | Endpoints | Tablas principales | Spec(s) | Auditoría | Estado |
|---|---:|---|---|---|---|
| `identity_access` | 9 | users, roles, permissions, role_permissions, user_roles, user_scopes, sessions, password_resets | 002, 003 | ✔ 1 | ◐ MFA ausente |
| `organization` | 10 | companies, branches, establishments, warehouses, locations | 007, 008 | **✖ 0** | ◐ |
| `master_data` | 18 | parties, customers, suppliers, carriers, drivers, products, services, taxonomy_nodes, attributes, units, presentations, barcodes… (23) | 009, 010, 011, 012 | **✖ 0** | ◐ |
| `inventory` | 34 | inventory_movements, inventory_balances, inventory_lots, product_serials, reservations, transfers, stock_counts, adjustments, cost_layers, costing_profiles, movement_types | 021-026 | ✔ 4 | ✔ núcleo |
| `purchasing` | 40 | purchase_requisitions, supplier_quotes, purchase_orders, goods_receipts, supplier_invoices, triple_matches, ap_* , purchase_returns | 015-017, 019, 027, 028 | ✔ 11 | ✔ |
| `sales` | 36 | sales_quotes, sales_orders, pick_lists, shipments, sales_invoices, sales_credit/debit_notes, sales_returns | 029-037 | ✔ 10 | ◐ |
| `treasury` | 38 | financial_banks, financial_accounts, cashboxes, cash_sessions, bank_transactions, reconciliations, treasury_transfers, igft_events, currencies, exchange_rates | 013, 038, 041 | ✔ 5 | ✔ |
| `fiscal` | 32 | tax_rule_versions, tax_profiles, tax_calculations, fiscal_number_series, control_numbers, fiscal_documents, print_events, credit_debit_notes, withholding_rules, fiscal_periods, tax_return_batches, legal_sources | 014, 039-043 | ✔ 5 | ◐ LEGAL |
| `regulatory` | 26 | regulatory_authorities, permit_types, permit_instances, official_documents, regulatory_profiles, regulatory_evaluations, contingencias, approval_requests, vehicles, drivers | 044, 045(parc.) | ✔ 4 | ✔ |
| `reporting` | 10 | report_definitions, report_exports, report_jobs | 049, 050 | ✔ 1 | ◐ |
| `licensing` | 6 | license_states, license_central_config, license_sync_runs, license_entitlement_snapshots, license_events, license_renewal_requests, license_artifacts, installations | 004, 048(parc.) | — | ✔ |
| `homologation` | 10 | homologation_records, homologation_events, release_versions | 056 | — | ✔ |
| `audit` | 1 | audit_events | 006, 051 | — | ◐ |
| `system` | 3 | system_settings, outbox_events, file_metadata, idempotency_records, feature_flags | 006, 046, 048 | — | ◐ |
| `setup` | 2 | — | 001, 052 | — | ✔ |

## Frontend — 12 módulos · 78 rutas · 77 páginas · 15.356 LOC

| Carpeta | Rutas | Spec(s) | Observación |
|---|---:|---|---|
| `src/modules/organizacion` | 4 | 007, 008 | Sin centros de costo ni unidades de negocio |
| `src/modules/maestros` | 6 | 009, 010, 011, 014 | Sin maestros comerciales |
| `src/modules/inventario` | 11 | 021-026 | Sin picking por ubicación |
| `src/modules/compras` | 8 | 015-017, 019, 027, 028, 036 | Sin importaciones ni incidencias |
| `src/modules/ventas` | 7 | 029-037 | Sin cola, ruta, confirmación ni liberación |
| `src/modules/tesoreria` | 6 | 013, 038, 041 | — |
| `src/modules/fiscal` | 7 | 014, 039-043 | Sin contingencia |
| `src/modules/regulatorio` | 5 | 044, 045(parc.) | — |
| `src/modules/reportes` | 3 | 049, 050, 051 | — |
| `src/modules/licenciamiento` | 4 | 004 | — |
| `src/modules/homologacion` | 3 | 056 | — |
| `src/modules/seguridad` | 3 | 002, 003 | Sin MFA ni alcances |
| `src/pages` (sueltas) | 9 | 001, 004, 049, 051 | Dashboard, login, setup, diagnóstico |
| `src/design-system`, `src/components`, `src/layout` | — | 005 | Componentes compartidos uniformes |

## Pruebas → Specs

| Archivo | Casos | Spec cubierta |
|---|---:|---|
| `tests/test_services.py`, `test_security.py` | — | 001, 002, 003 |
| `test_maestros.py` | — | 009, 010 |
| `test_inventory.py` | — | 023, 024, 025 |
| `test_purchasing.py` | — | 015-017, 027, 028 |
| `test_sales.py` | — | 029, 030, 034, 037 |
| `test_treasury.py` | — | 013, 038, 041 |
| `test_fiscal.py` | — | 039-043 |
| `test_regulatory.py` | — | 044 |
| `test_reporting.py` | — | 049, 050 |
| `test_license.py`, `test_licensing_central.py` | — | 004 |
| `test_homologation.py` | — | 056 |
| `test_process_flows.py` | — | P-01, seguridad, enforcement |
| `test_audit_integration.py` | — | 006, 051 |
| `test_idempotency_concurrency.py` | 6 | 030, 034, 028 |
| `test_security_integration.py` | 8 | 055 |
| `test_migrations_offline.py` | 3 | 001, 052 |
| `test_password_reset.py` | — | 002 |
| **pytest total** | **223** | — |
| `src/components/*.test.tsx` (5 archivos) | 12 | 005 |
| `src/lib/format.test.ts` | 4 | 005 |
| `src/tests/audit-completeness.test.ts` | 5 (G1-G4) | 054 |
| **vitest total** | **210** | — |
| `e2e/route-crawl.spec.ts`, `accessibility.spec.ts`, `smoke.spec.ts` | — | 054 |

### Observación sobre la cobertura frontend

Los 210 casos de vitest se concentran en **7 archivos**, todos de componente o de puerta
(`DataTable`, `Button`, `AsyncButton`, `AsyncCombobox`, `FormField`, `format`, `audit-completeness`).
**No existe una sola prueba de página de negocio.** La cifra 210 mide la robustez del design system,
no la de las 77 pantallas.

## Código sin Spec (`IMPLEMENTED_WITHOUT_SPEC`)

| Código | Spec maestra que debería gobernarlo |
|---|---|
| `customers.price_list / zone / payment_term / salesperson` (texto libre) | 012 |
| `purchase_requisitions.cost_center_id`, `user_scopes.cost_center_id` (String sin FK) | 007 |
| `regulatory.approval_requests` + aprobaciones ad-hoc en 4 módulos | 045 |
| `system.file_metadata` (tabla sin endpoint) | 046 |
| `licensing/service.py:375` cliente `urllib.request` | 048 |
| `system.outbox_events` (sin publicador) | 048 |
| `system.feature_flags` (sin consumidor) | 001 |
