# QUERY_PARAMETER_INVENTORY — línea base en 49540a6 (2026-10-28)

Generado por Claude desde `create_app().routes` (`get_flat_dependant`) y el barrido de línea base. Una fila por operación.

Columnas comunes a todas las filas:
- OWNER_SPEC: el módulo dueño del endpoint; el contrato transversal es de la Spec 001.
- MANUAL_QUERY_READERS: 0 (no hay `request.query_params` ni `request.url.query` en `app/`).
- EXCEPTIONS: ninguna.
- FIX_REQUIRED: sí, por el mecanismo central (AD-1).
- TEST: `test_strict_query_contract.py` (GUARD-Q-01 estructural y GUARD-Q-02 barrido).

Operaciones: **555** · con parámetros de consulta declarados: **84**.

| Ruta | Método | Módulo | DECLARED_QUERY_PARAMS | DECLARING_SOURCE | CURRENT_UNKNOWN_BEHAVIOR |
|---|---|---|---|---|---|
| `/` | GET | main | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/alerts` | GET | notifications.api | page, page_size, severity, source_type, status | ruta | IGNORADO (200=200) |
| `/api/v1/approvals/delegations` | GET | approvals.api | — | — | IGNORADO (200=200) |
| `/api/v1/approvals/delegations` | POST | approvals.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/approvals/delegations/{delegation_id}/revoke` | POST | approvals.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/approvals/evaluate` | POST | approvals.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/approvals/inbox` | GET | approvals.api | limit, offset, only_overdue, process_type | ruta | IGNORADO (200=200) |
| `/api/v1/approvals/policies` | GET | approvals.api | process_type, status | ruta | IGNORADO (200=200) |
| `/api/v1/approvals/policies` | POST | approvals.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/approvals/policies/{policy_id}` | GET | approvals.api | — | — | IGNORADO (200=200) |
| `/api/v1/approvals/policies/{policy_id}` | PATCH | approvals.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/approvals/policies/{policy_id}/activate` | POST | approvals.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/approvals/policies/{policy_id}/close` | POST | approvals.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/approvals/policies/{policy_id}/rules` | POST | approvals.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/approvals/policies/{policy_id}/rules/{rule_id}/levels` | POST | approvals.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/approvals/process-types` | GET | approvals.api | — | — | IGNORADO (200=200) |
| `/api/v1/approvals/requests` | GET | approvals.api | process_type, status | ruta | IGNORADO (200=200) |
| `/api/v1/approvals/requests` | POST | approvals.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/approvals/requests/by-document` | GET | approvals.api | document_id, document_type | ruta | IGNORADO (200=200) |
| `/api/v1/approvals/requests/{request_id}` | GET | approvals.api | — | — | IGNORADO (200=200) |
| `/api/v1/approvals/requests/{request_id}/cancel` | POST | approvals.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/approvals/steps/{step_id}/approve` | POST | approvals.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/approvals/steps/{step_id}/reject` | POST | approvals.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/approvals/steps/{step_id}/return` | POST | approvals.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/audit/events` | GET | audit.api | action, company_id, desde, entity_id, entity_type, hasta, page, page_size, request_id, scope, username | ruta | AUTH_PRECEDE (403) |
| `/api/v1/audit/filters` | GET | audit.api | — | — | AUTH_PRECEDE (403) |
| `/api/v1/auth/change-password` | POST | identity_access.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/auth/login` | POST | identity_access.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/auth/logout` | POST | identity_access.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/auth/me` | GET | identity_access.api | — | — | IGNORADO (200=200) |
| `/api/v1/auth/mfa` | DELETE | identity_access.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/auth/mfa` | GET | identity_access.api | — | — | IGNORADO (200=200) |
| `/api/v1/auth/mfa/enrollment` | POST | identity_access.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/auth/mfa/enrollment/confirm` | POST | identity_access.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/auth/mfa/recovery-codes` | POST | identity_access.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/auth/mfa/verify` | POST | identity_access.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/auth/operations` | GET | identity_access.api | — | — | IGNORADO (200=200) |
| `/api/v1/auth/password-reset/confirm` | POST | identity_access.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/auth/password-reset/request` | POST | identity_access.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/auth/reauth` | POST | identity_access.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/auth/refresh` | POST | identity_access.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/auth/sessions` | GET | identity_access.api | — | — | IGNORADO (200=200) |
| `/api/v1/auth/sessions/{session_id}` | DELETE | identity_access.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/authority/company` | GET | identity_access.api | — | — | IGNORADO (200=200) |
| `/api/v1/comercial/canales` | GET | commercial.api | — | — | IGNORADO (200=200) |
| `/api/v1/comercial/canales` | POST | commercial.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/comercial/clientes/{customer_id}/condiciones` | PUT | commercial.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/comercial/condiciones-pago` | GET | commercial.api | — | — | IGNORADO (200=200) |
| `/api/v1/comercial/condiciones-pago` | POST | commercial.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/comercial/descuento/validar` | POST | commercial.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/comercial/listas-precio` | GET | commercial.api | — | — | IGNORADO (200=200) |
| `/api/v1/comercial/listas-precio` | POST | commercial.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/comercial/listas-precio/{price_list_id}` | GET | commercial.api | — | — | IGNORADO (200=200) |
| `/api/v1/comercial/listas-precio/{price_list_id}/versiones` | POST | commercial.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/comercial/listas-precio/{price_list_id}/versiones/{version_id}/items` | GET | commercial.api | — | — | IGNORADO (200=200) |
| `/api/v1/comercial/listas-precio/{price_list_id}/versiones/{version_id}/items` | POST | commercial.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/comercial/listas-precio/{price_list_id}/versiones/{version_id}/transicion` | POST | commercial.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/comercial/politicas-credito` | GET | commercial.api | — | — | IGNORADO (200=200) |
| `/api/v1/comercial/politicas-credito` | POST | commercial.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/comercial/politicas-descuento` | GET | commercial.api | — | — | IGNORADO (200=200) |
| `/api/v1/comercial/politicas-descuento` | POST | commercial.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/comercial/precedencia` | GET | commercial.api | — | — | IGNORADO (200=200) |
| `/api/v1/comercial/precedencia` | PUT | commercial.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/comercial/precio/resolver` | POST | commercial.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/comercial/zonas` | GET | commercial.api | — | — | IGNORADO (200=200) |
| `/api/v1/comercial/zonas` | POST | commercial.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/documentos` | GET | documents.api | document_type_id, expiring_before, limit, offset, q, resource_id, resource_type, status | ruta | IGNORADO (200=200) |
| `/api/v1/documentos` | POST | documents.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/documentos/categorias` | GET | documents.api | — | — | IGNORADO (200=200) |
| `/api/v1/documentos/categorias` | POST | documents.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/documentos/por-recurso/{resource_type}/{resource_id}` | GET | documents.api | — | — | IGNORADO (200=200) |
| `/api/v1/documentos/salud/almacenamiento` | GET | documents.api | — | — | IGNORADO (200=200) |
| `/api/v1/documentos/tipos` | GET | documents.api | — | — | IGNORADO (200=200) |
| `/api/v1/documentos/tipos` | POST | documents.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/documentos/tipos/{type_id}` | PATCH | documents.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/documentos/vinculos/{link_id}` | DELETE | documents.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/documentos/{document_id}` | DELETE | documents.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/documentos/{document_id}` | GET | documents.api | — | — | IGNORADO (200=200) |
| `/api/v1/documentos/{document_id}` | PATCH | documents.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/documentos/{document_id}/archive` | POST | documents.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/documentos/{document_id}/descargar` | GET | documents.api | — | — | IGNORADO (200=200) |
| `/api/v1/documentos/{document_id}/preview` | GET | documents.api | — | — | IGNORADO (200=200) |
| `/api/v1/documentos/{document_id}/versiones` | GET | documents.api | — | — | IGNORADO (200=200) |
| `/api/v1/documentos/{document_id}/versiones` | POST | documents.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/documentos/{document_id}/versiones/{version_id}/descargar` | GET | documents.api | — | — | IGNORADO (200=200) |
| `/api/v1/documentos/{document_id}/vinculos` | POST | documents.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/fiscal/books/{tax_type}` | GET | fiscal.api | period | ruta | IGNORADO (200=200) |
| `/api/v1/fiscal/control-batches` | GET | fiscal.api | — | — | IGNORADO (200=200) |
| `/api/v1/fiscal/control-batches` | POST | fiscal.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/fiscal/control-numbers` | GET | fiscal.api | batch_id, state | ruta | IGNORADO (200=200) |
| `/api/v1/fiscal/credit-debit-notes` | GET | fiscal.api | original_document | ruta | IGNORADO (200=200) |
| `/api/v1/fiscal/credit-debit-notes` | POST | fiscal.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/fiscal/documents` | GET | fiscal.api | status | ruta | IGNORADO (200=200) |
| `/api/v1/fiscal/documents/emit` | POST | fiscal.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/fiscal/documents/{document_id}` | GET | fiscal.api | — | — | IGNORADO (200=200) |
| `/api/v1/fiscal/documents/{document_id}/print` | POST | fiscal.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/fiscal/legal-sources` | GET | fiscal.api | — | — | IGNORADO (200=200) |
| `/api/v1/fiscal/legal-sources` | POST | fiscal.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/fiscal/legal-sources/{source_id}/activate` | POST | fiscal.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/fiscal/number-series` | GET | fiscal.api | — | — | IGNORADO (200=200) |
| `/api/v1/fiscal/number-series` | POST | fiscal.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/fiscal/periods` | GET | fiscal.api | tax_type | ruta | IGNORADO (200=200) |
| `/api/v1/fiscal/periods` | POST | fiscal.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/fiscal/periods/{period_id}/transition` | POST | fiscal.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/fiscal/tax-calculations` | GET | fiscal.api | — | — | IGNORADO (200=200) |
| `/api/v1/fiscal/tax-calculations` | POST | fiscal.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/fiscal/tax-profiles` | POST | fiscal.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/fiscal/tax-return-batches` | GET | fiscal.api | — | — | IGNORADO (200=200) |
| `/api/v1/fiscal/tax-return-batches` | POST | fiscal.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/fiscal/tax-rule-versions` | GET | fiscal.api | tax_code | ruta | IGNORADO (200=200) |
| `/api/v1/fiscal/tax-rule-versions` | POST | fiscal.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/fiscal/tax-rule-versions/{rule_id}/approve` | POST | fiscal.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/fiscal/withholding-rules` | GET | fiscal.api | tax_type | ruta | IGNORADO (200=200) |
| `/api/v1/fiscal/withholding-rules` | POST | fiscal.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/fiscal/withholdings` | GET | fiscal.api | tax_type | ruta | IGNORADO (200=200) |
| `/api/v1/fiscal/withholdings/calculate` | POST | fiscal.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/fiscal/withholdings/{withholding_id}/certificate` | POST | fiscal.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/fiscal/withholdings/{withholding_id}/transition` | POST | fiscal.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/health/live` | GET | system.api | — | — | IGNORADO (200=200) |
| `/api/v1/health/ready` | GET | system.api | — | — | IGNORADO (200=200) |
| `/api/v1/homologation/records` | GET | homologation.api | — | — | IGNORADO (200=200) |
| `/api/v1/homologation/records` | POST | homologation.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/homologation/records/{record_id}` | GET | homologation.api | — | — | IGNORADO (200=200) |
| `/api/v1/homologation/records/{record_id}/evaluate` | POST | homologation.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/homologation/records/{record_id}/submit` | POST | homologation.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/homologation/releases` | GET | homologation.api | — | — | IGNORADO (200=200) |
| `/api/v1/homologation/releases` | POST | homologation.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/homologation/releases/{release_id}/promote` | POST | homologation.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/homologation/releases/{release_id}/release` | POST | homologation.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/homologation/timeline` | GET | homologation.api | — | — | IGNORADO (200=200) |
| `/api/v1/inventory/adjustments` | GET | inventory.api | status | ruta | IGNORADO (200=200) |
| `/api/v1/inventory/adjustments` | POST | inventory.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/inventory/adjustments/{adjustment_id}/transition` | POST | inventory.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/inventory/balances` | GET | inventory.api | location_id, lot_id, page, page_size, product_id, serial_id, state, warehouse_id | ruta | IGNORADO (200=200) |
| `/api/v1/inventory/balances/recompute` | POST | inventory.api | warehouse_id | ruta | IGNORADO (sin mecanismo; framework) |
| `/api/v1/inventory/balances/{balance_id}` | GET | inventory.api | — | — | IGNORADO (200=200) |
| `/api/v1/inventory/cost-layers` | GET | inventory.api | product_id, warehouse_id | ruta | IGNORADO (200=200) |
| `/api/v1/inventory/costing-profiles` | GET | inventory.api | — | — | IGNORADO (200=200) |
| `/api/v1/inventory/costing-profiles` | POST | inventory.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/inventory/counts` | GET | inventory.api | status | ruta | IGNORADO (200=200) |
| `/api/v1/inventory/counts` | POST | inventory.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/inventory/counts/{count_id}/lines` | POST | inventory.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/inventory/counts/{count_id}/transition` | POST | inventory.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/inventory/lots` | GET | inventory.api | expiry_before, page, page_size, product_id, status | ruta | IGNORADO (200=200) |
| `/api/v1/inventory/lots` | POST | inventory.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/inventory/lots/{lot_id}/transition` | POST | inventory.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/inventory/movement-types` | GET | inventory.api | — | — | IGNORADO (200=200) |
| `/api/v1/inventory/movement-types` | POST | inventory.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/inventory/movements` | GET | inventory.api | page, page_size, product_id, q, warehouse_id | ruta | IGNORADO (200=200) |
| `/api/v1/inventory/movements` | POST | inventory.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/inventory/movements/reverse` | POST | inventory.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/inventory/movements/{movement_id}` | GET | inventory.api | — | — | IGNORADO (200=200) |
| `/api/v1/inventory/operations/receive` | POST | inventory.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/inventory/operations/ship` | POST | inventory.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/inventory/putaway` | POST | inventory.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/inventory/putaway/pendientes` | GET | inventory.api | warehouse_id | ruta | IGNORADO (200=200) |
| `/api/v1/inventory/putaway/ubicaciones` | GET | inventory.api | warehouse_id | ruta | IGNORADO (200=200) |
| `/api/v1/inventory/reservations` | GET | inventory.api | product_id, status | ruta | IGNORADO (200=200) |
| `/api/v1/inventory/reservations` | POST | inventory.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/inventory/reservations/expire` | POST | inventory.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/inventory/reservations/{reservation_id}/release` | POST | inventory.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/inventory/serials` | GET | inventory.api | product_id, q, status | ruta | IGNORADO (200=200) |
| `/api/v1/inventory/serials` | POST | inventory.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/inventory/transfers` | GET | inventory.api | page, page_size, status | ruta | IGNORADO (200=200) |
| `/api/v1/inventory/transfers` | POST | inventory.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/inventory/transfers/{transfer_id}/transition` | POST | inventory.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/inventory/valuation` | GET | inventory.api | product_id, warehouse_id | ruta | IGNORADO (200=200) |
| `/api/v1/license/activate` | POST | licensing.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/license/detail` | GET | licensing.api | — | — | AUTH_PRECEDE (403) |
| `/api/v1/license/history` | GET | licensing.api | — | — | AUTH_PRECEDE (403) |
| `/api/v1/license/import` | POST | licensing.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/license/installation-request` | GET | licensing.api | — | — | AUTH_PRECEDE (403) |
| `/api/v1/license/renewal-request` | POST | licensing.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/license/status` | GET | licensing.api | — | — | IGNORADO (200=200) |
| `/api/v1/licensing/central-config` | GET | licensing.api | — | — | AUTH_PRECEDE (403) |
| `/api/v1/licensing/central-config` | PUT | licensing.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/licensing/entitlement-snapshots` | GET | licensing.api | — | — | AUTH_PRECEDE (403) |
| `/api/v1/licensing/entitlements` | GET | licensing.api | — | — | AUTH_PRECEDE (403) |
| `/api/v1/licensing/mode-transition` | POST | licensing.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/licensing/offline-status` | GET | licensing.api | — | — | AUTH_PRECEDE (403) |
| `/api/v1/licensing/overview` | GET | licensing.api | — | — | AUTH_PRECEDE (403) |
| `/api/v1/licensing/renewal-requests` | GET | licensing.api | — | — | AUTH_PRECEDE (403) |
| `/api/v1/licensing/renewal-requests` | POST | licensing.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/licensing/renewal-requests/{request_id}/transition` | POST | licensing.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/licensing/sync` | POST | licensing.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/licensing/sync-runs` | GET | licensing.api | — | — | AUTH_PRECEDE (403) |
| `/api/v1/maestros/catalogos/atributos` | GET | master_data.api | — | — | IGNORADO (200=200) |
| `/api/v1/maestros/catalogos/atributos` | POST | master_data.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/maestros/catalogos/items` | GET | master_data.api | page, page_size, q, status | ruta | IGNORADO (200=200) |
| `/api/v1/maestros/catalogos/items` | POST | master_data.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/maestros/catalogos/items/search` | GET | master_data.api | item_type, page, page_size, q | ruta | IGNORADO (200=200) |
| `/api/v1/maestros/catalogos/items/{item_id}` | GET | master_data.api | — | — | IGNORADO (200=200) |
| `/api/v1/maestros/catalogos/taxonomia` | GET | master_data.api | parent_id | ruta | IGNORADO (200=200) |
| `/api/v1/maestros/catalogos/taxonomia` | POST | master_data.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/maestros/catalogos/unidades` | GET | master_data.api | — | — | IGNORADO (200=200) |
| `/api/v1/maestros/catalogos/unidades` | POST | master_data.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/maestros/catalogos/unidades/{unit_id}/conversiones` | POST | master_data.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/maestros/conversion/preview` | POST | master_data.uom_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/maestros/perfiles` | GET | master_data.api | profile_type | ruta | IGNORADO (200=200) |
| `/api/v1/maestros/perfiles` | POST | master_data.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/maestros/presentaciones/{presentation_id}` | DELETE | master_data.uom_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/maestros/presentaciones/{presentation_id}` | GET | master_data.uom_api | — | — | IGNORADO (200=200) |
| `/api/v1/maestros/presentaciones/{presentation_id}` | PATCH | master_data.uom_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/maestros/presentaciones/{presentation_id}/activate` | POST | master_data.uom_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/maestros/presentaciones/{presentation_id}/deactivate` | POST | master_data.uom_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/maestros/presentaciones/{presentation_id}/versiones` | GET | master_data.uom_api | — | — | IGNORADO (200=200) |
| `/api/v1/maestros/presentaciones/{presentation_id}/versiones` | POST | master_data.uom_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/maestros/productos/{product_id}/presentaciones` | GET | master_data.uom_api | status | ruta | IGNORADO (200=200) |
| `/api/v1/maestros/productos/{product_id}/presentaciones` | POST | master_data.uom_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/maestros/productos/{product_id}/unidad-base` | PATCH | master_data.uom_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/maestros/terceros` | GET | master_data.api | page, page_size, q, status | ruta | IGNORADO (200=200) |
| `/api/v1/maestros/terceros` | POST | master_data.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/maestros/terceros/{party_id}` | GET | master_data.api | — | — | IGNORADO (200=200) |
| `/api/v1/maestros/terceros/{party_id}/deactivate` | POST | master_data.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/maestros/terceros/{party_id}/roles/{role}` | POST | master_data.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/maestros/unidades` | GET | master_data.uom_api | dimension, limit, offset, q, scope, status | ruta | IGNORADO (200=200) |
| `/api/v1/maestros/unidades` | POST | master_data.uom_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/maestros/unidades/{unit_id}` | DELETE | master_data.uom_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/maestros/unidades/{unit_id}` | GET | master_data.uom_api | — | — | IGNORADO (200=200) |
| `/api/v1/maestros/unidades/{unit_id}` | PATCH | master_data.uom_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/maestros/unidades/{unit_id}/activate` | POST | master_data.uom_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/maestros/unidades/{unit_id}/conversiones` | GET | master_data.uom_api | — | — | IGNORADO (200=200) |
| `/api/v1/maestros/unidades/{unit_id}/conversiones-fisicas` | POST | master_data.uom_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/maestros/unidades/{unit_id}/deactivate` | POST | master_data.uom_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/notifications` | GET | notifications.api | category, created_from, created_to, page, page_size, severity, source_type, state | ruta | IGNORADO (200=200) |
| `/api/v1/notifications/counts` | GET | notifications.api | — | — | IGNORADO (200=200) |
| `/api/v1/notifications/preferences` | GET | notifications.api | — | — | NO_SONDEABLE (SQLite bool_or) |
| `/api/v1/notifications/preferences` | PUT | notifications.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/notifications/rules` | GET | notifications.api | — | — | AUTH_PRECEDE (403) |
| `/api/v1/notifications/rules` | POST | notifications.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/notifications/rules/{rule_id}/deactivate` | POST | notifications.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/notifications/sources` | GET | notifications.api | — | — | AUTH_PRECEDE (403) |
| `/api/v1/notifications/{notification_id}` | GET | notifications.api | — | — | IGNORADO (200=200) |
| `/api/v1/notifications/{notification_id}/archive` | POST | notifications.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/notifications/{notification_id}/read` | POST | notifications.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/organization/aisles/{node_id}` | DELETE | organization.warehouse_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/organization/aisles/{node_id}` | GET | organization.warehouse_api | — | — | AUTH_PRECEDE (403) |
| `/api/v1/organization/aisles/{node_id}` | PATCH | organization.warehouse_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/organization/aisles/{node_id}/activate` | POST | organization.warehouse_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/organization/aisles/{node_id}/deactivate` | POST | organization.warehouse_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/organization/branches` | GET | organization.api | — | — | AUTH_PRECEDE (403) |
| `/api/v1/organization/branches` | POST | organization.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/organization/companies` | GET | organization.api | page, page_size, q | ruta | IGNORADO (200=200) |
| `/api/v1/organization/companies` | POST | organization.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/organization/establishments` | GET | organization.api | branch_id | ruta | AUTH_PRECEDE (403) |
| `/api/v1/organization/establishments` | POST | organization.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/organization/levels/{node_id}` | DELETE | organization.warehouse_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/organization/levels/{node_id}` | GET | organization.warehouse_api | — | — | AUTH_PRECEDE (403) |
| `/api/v1/organization/levels/{node_id}` | PATCH | organization.warehouse_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/organization/levels/{node_id}/activate` | POST | organization.warehouse_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/organization/levels/{node_id}/deactivate` | POST | organization.warehouse_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/organization/location-types` | GET | organization.warehouse_api | company_id | ruta | AUTH_PRECEDE (403) |
| `/api/v1/organization/location-types` | POST | organization.warehouse_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/organization/location-types/{item_id}` | PATCH | organization.warehouse_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/organization/locations` | GET | organization.warehouse_api | aisle_id, level_id, limit, location_type_id, offset, q, rack_id, status, warehouse_id, zone_id | ruta | AUTH_PRECEDE (403) |
| `/api/v1/organization/locations` | POST | organization.warehouse_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/organization/locations/bulk` | POST | organization.warehouse_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/organization/locations/ordered` | GET | organization.warehouse_api | limit, location_type_id, offset, status, warehouse_id | ruta | AUTH_PRECEDE (403) |
| `/api/v1/organization/locations/{location_id}` | DELETE | organization.warehouse_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/organization/locations/{location_id}` | GET | organization.warehouse_api | — | — | AUTH_PRECEDE (403) |
| `/api/v1/organization/locations/{location_id}` | PATCH | organization.warehouse_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/organization/locations/{location_id}/activate` | POST | organization.warehouse_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/organization/locations/{location_id}/block` | POST | organization.warehouse_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/organization/locations/{location_id}/deactivate` | POST | organization.warehouse_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/organization/racks/{node_id}` | DELETE | organization.warehouse_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/organization/racks/{node_id}` | GET | organization.warehouse_api | — | — | AUTH_PRECEDE (403) |
| `/api/v1/organization/racks/{node_id}` | PATCH | organization.warehouse_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/organization/racks/{node_id}/activate` | POST | organization.warehouse_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/organization/racks/{node_id}/deactivate` | POST | organization.warehouse_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/organization/warehouses` | GET | organization.warehouse_api | branch_id, company_id, limit, offset, q, status | ruta | AUTH_PRECEDE (403) |
| `/api/v1/organization/warehouses` | POST | organization.warehouse_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/organization/warehouses/{warehouse_id}` | DELETE | organization.warehouse_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/organization/warehouses/{warehouse_id}` | GET | organization.warehouse_api | — | — | AUTH_PRECEDE (403) |
| `/api/v1/organization/warehouses/{warehouse_id}` | PATCH | organization.warehouse_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/organization/warehouses/{warehouse_id}/activate` | POST | organization.warehouse_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/organization/warehouses/{warehouse_id}/aisles` | GET | organization.warehouse_api | parent_id, status | ruta | AUTH_PRECEDE (403) |
| `/api/v1/organization/warehouses/{warehouse_id}/aisles` | POST | organization.warehouse_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/organization/warehouses/{warehouse_id}/deactivate` | POST | organization.warehouse_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/organization/warehouses/{warehouse_id}/levels` | GET | organization.warehouse_api | parent_id, status | ruta | AUTH_PRECEDE (403) |
| `/api/v1/organization/warehouses/{warehouse_id}/levels` | POST | organization.warehouse_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/organization/warehouses/{warehouse_id}/racks` | GET | organization.warehouse_api | parent_id, status | ruta | AUTH_PRECEDE (403) |
| `/api/v1/organization/warehouses/{warehouse_id}/racks` | POST | organization.warehouse_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/organization/warehouses/{warehouse_id}/structure` | GET | organization.warehouse_api | depth, limit, offset, status | ruta | AUTH_PRECEDE (403) |
| `/api/v1/organization/warehouses/{warehouse_id}/structure-levels` | PATCH | organization.warehouse_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/organization/warehouses/{warehouse_id}/zones` | GET | organization.warehouse_api | parent_id, status | ruta | AUTH_PRECEDE (403) |
| `/api/v1/organization/warehouses/{warehouse_id}/zones` | POST | organization.warehouse_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/organization/zone-types` | GET | organization.warehouse_api | company_id | ruta | AUTH_PRECEDE (403) |
| `/api/v1/organization/zone-types` | POST | organization.warehouse_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/organization/zone-types/{item_id}` | PATCH | organization.warehouse_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/organization/zones/{node_id}` | DELETE | organization.warehouse_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/organization/zones/{node_id}` | GET | organization.warehouse_api | — | — | AUTH_PRECEDE (403) |
| `/api/v1/organization/zones/{node_id}` | PATCH | organization.warehouse_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/organization/zones/{node_id}/activate` | POST | organization.warehouse_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/organization/zones/{node_id}/deactivate` | POST | organization.warehouse_api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/purchasing/advances` | POST | purchasing.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/purchasing/aging` | GET | purchasing.api | party_id | ruta | IGNORADO (200=200) |
| `/api/v1/purchasing/applications` | POST | purchasing.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/purchasing/credit-notes` | GET | purchasing.api | — | — | IGNORADO (200=200) |
| `/api/v1/purchasing/credit-notes` | POST | purchasing.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/purchasing/credit-notes/{note_id}/post` | POST | purchasing.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/purchasing/incidencias` | GET | purchasing.api | incident_type, status | ruta | IGNORADO (200=200) |
| `/api/v1/purchasing/open-items` | GET | purchasing.api | party_id, status | ruta | IGNORADO (200=200) |
| `/api/v1/purchasing/orders` | GET | purchasing.api | page, page_size, status | ruta | IGNORADO (200=200) |
| `/api/v1/purchasing/orders` | POST | purchasing.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/purchasing/orders/{order_id}` | GET | purchasing.api | — | — | IGNORADO (200=200) |
| `/api/v1/purchasing/orders/{order_id}/lines` | POST | purchasing.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/purchasing/orders/{order_id}/transition` | POST | purchasing.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/purchasing/payment-schedules` | POST | purchasing.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/purchasing/payments` | GET | purchasing.api | status | ruta | IGNORADO (200=200) |
| `/api/v1/purchasing/payments` | POST | purchasing.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/purchasing/payments/{payment_id}/transition` | POST | purchasing.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/purchasing/quotes` | GET | purchasing.api | supplier_id | ruta | IGNORADO (200=200) |
| `/api/v1/purchasing/quotes` | POST | purchasing.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/purchasing/quotes/{quote_id}/lines` | POST | purchasing.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/purchasing/receipts` | GET | purchasing.api | status | ruta | IGNORADO (200=200) |
| `/api/v1/purchasing/receipts` | POST | purchasing.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/purchasing/receipts/{receipt_id}` | GET | purchasing.api | — | — | IGNORADO (200=200) |
| `/api/v1/purchasing/receipts/{receipt_id}/accept` | POST | purchasing.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/purchasing/receipts/{receipt_id}/arrival` | POST | purchasing.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/purchasing/receipts/{receipt_id}/conciliacion` | GET | purchasing.api | — | — | IGNORADO (200=200) |
| `/api/v1/purchasing/receipts/{receipt_id}/confirm` | POST | purchasing.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/purchasing/receipts/{receipt_id}/confirmacion-inventario` | GET | purchasing.api | — | — | IGNORADO (200=200) |
| `/api/v1/purchasing/receipts/{receipt_id}/confirmacion-inventario` | POST | purchasing.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/purchasing/receipts/{receipt_id}/incidencias` | GET | purchasing.api | — | — | IGNORADO (200=200) |
| `/api/v1/purchasing/receipts/{receipt_id}/incidencias` | POST | purchasing.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/purchasing/receipts/{receipt_id}/incidencias/resultado` | GET | purchasing.api | — | — | IGNORADO (200=200) |
| `/api/v1/purchasing/receipts/{receipt_id}/incidencias/{incident_id}` | GET | purchasing.api | — | — | IGNORADO (200=200) |
| `/api/v1/purchasing/receipts/{receipt_id}/incidencias/{incident_id}/cancel` | POST | purchasing.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/purchasing/receipts/{receipt_id}/incidencias/{incident_id}/escalate` | POST | purchasing.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/purchasing/receipts/{receipt_id}/incidencias/{incident_id}/resolve` | POST | purchasing.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/purchasing/receipts/{receipt_id}/inspection` | POST | purchasing.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/purchasing/receipts/{receipt_id}/lines` | POST | purchasing.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/purchasing/receipts/{receipt_id}/lines/{line_id}/conteo` | POST | purchasing.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/purchasing/receipts/{receipt_id}/quality` | POST | purchasing.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/purchasing/requisitions` | GET | purchasing.api | page, page_size, status | ruta | IGNORADO (200=200) |
| `/api/v1/purchasing/requisitions` | POST | purchasing.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/purchasing/requisitions/{req_id}/lines` | POST | purchasing.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/purchasing/requisitions/{req_id}/transition` | POST | purchasing.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/purchasing/returns` | GET | purchasing.api | — | — | IGNORADO (200=200) |
| `/api/v1/purchasing/returns` | POST | purchasing.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/purchasing/returns/{return_id}/lines` | POST | purchasing.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/purchasing/supplier-invoices` | GET | purchasing.api | page, page_size, status | ruta | IGNORADO (200=200) |
| `/api/v1/purchasing/supplier-invoices` | POST | purchasing.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/purchasing/supplier-invoices/{invoice_id}` | GET | purchasing.api | — | — | IGNORADO (200=200) |
| `/api/v1/purchasing/supplier-invoices/{invoice_id}/lines` | POST | purchasing.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/purchasing/supplier-invoices/{invoice_id}/transition` | POST | purchasing.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/purchasing/triple-match` | GET | purchasing.api | invoice_id | ruta | IGNORADO (200=200) |
| `/api/v1/purchasing/withholdings` | POST | purchasing.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/purchasing/withholdings/{withholding_id}/transition` | POST | purchasing.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/regulatory/approval-requests` | GET | regulatory.api | — | — | IGNORADO (200=200) |
| `/api/v1/regulatory/approval-requests` | POST | regulatory.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/regulatory/approval-requests/{request_id}/transition` | POST | regulatory.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/regulatory/authorities` | GET | regulatory.api | — | — | IGNORADO (200=200) |
| `/api/v1/regulatory/authorities` | POST | regulatory.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/regulatory/contingencies` | GET | regulatory.api | — | — | IGNORADO (200=200) |
| `/api/v1/regulatory/contingencies` | POST | regulatory.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/regulatory/contingencies/{contingency_id}/end` | POST | regulatory.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/regulatory/drivers` | GET | regulatory.api | — | — | IGNORADO (200=200) |
| `/api/v1/regulatory/drivers` | POST | regulatory.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/regulatory/evaluations` | GET | regulatory.api | shipment_id | ruta | IGNORADO (200=200) |
| `/api/v1/regulatory/evaluations` | POST | regulatory.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/regulatory/evaluations/{evaluation_id}/override` | POST | regulatory.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/regulatory/official-documents` | GET | regulatory.api | kind | ruta | IGNORADO (200=200) |
| `/api/v1/regulatory/official-documents` | POST | regulatory.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/regulatory/official-registrations` | GET | regulatory.api | — | — | IGNORADO (200=200) |
| `/api/v1/regulatory/official-registrations` | POST | regulatory.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/regulatory/permit-types` | GET | regulatory.api | — | — | IGNORADO (200=200) |
| `/api/v1/regulatory/permit-types` | POST | regulatory.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/regulatory/permits` | GET | regulatory.api | status | ruta | IGNORADO (200=200) |
| `/api/v1/regulatory/permits` | POST | regulatory.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/regulatory/permits/{permit_id}/transition` | POST | regulatory.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/regulatory/profiles` | GET | regulatory.api | — | — | IGNORADO (200=200) |
| `/api/v1/regulatory/profiles` | POST | regulatory.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/regulatory/vehicles` | GET | regulatory.api | — | — | IGNORADO (200=200) |
| `/api/v1/regulatory/vehicles` | POST | regulatory.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/reporting/audit/timeline` | GET | reporting.api | action, entity_type, user_id | ruta | AUTH_PRECEDE (403) |
| `/api/v1/reporting/dashboard` | GET | reporting.api | — | — | AUTH_PRECEDE (403) |
| `/api/v1/reporting/exports` | GET | reporting.api | report_key | ruta | IGNORADO (200=200) |
| `/api/v1/reporting/exports` | POST | reporting.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/reporting/exports/{export_id}/download` | GET | reporting.api | — | — | IGNORADO (200=200) |
| `/api/v1/reporting/jobs` | GET | reporting.api | report_key | ruta | IGNORADO (200=200) |
| `/api/v1/reporting/jobs` | POST | reporting.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/reporting/jobs/{job_id}` | GET | reporting.api | — | — | IGNORADO (200=200) |
| `/api/v1/reporting/jobs/{job_id}/run` | POST | reporting.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/reporting/reports/{key}` | GET | reporting.api | period | ruta | IGNORADO (200=200) |
| `/api/v1/roles` | GET | identity_access.api | — | — | AUTH_PRECEDE (403) |
| `/api/v1/roles` | POST | identity_access.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/aging` | GET | sales.api | party_id | ruta | IGNORADO (200=200) |
| `/api/v1/sales/applications` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/collections` | GET | sales.api | status | ruta | IGNORADO (200=200) |
| `/api/v1/sales/collections` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/collections/{collection_id}/transition` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/confirmacion/pendientes` | GET | sales.api | — | — | IGNORADO (200=200) |
| `/api/v1/sales/confirmacion/{order_id}` | GET | sales.api | — | — | IGNORADO (200=200) |
| `/api/v1/sales/confirmacion/{order_id}` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/confirmacion/{order_id}/facturable` | GET | sales.api | — | — | IGNORADO (200=200) |
| `/api/v1/sales/credit-notes` | GET | sales.api | — | — | IGNORADO (200=200) |
| `/api/v1/sales/credit-notes` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/credit-notes/{note_id}/apply` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/credit-notes/{note_id}/post` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/customer-advances` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/cxc/aplicaciones/{application_id}/revertir` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/cxc/clientes/{customer_id}/creditos` | GET | sales.api | — | — | IGNORADO (200=200) |
| `/api/v1/sales/cxc/clientes/{customer_id}/estado-de-cuenta` | GET | sales.api | — | — | IGNORADO (200=200) |
| `/api/v1/sales/cxc/clientes/{customer_id}/saldo` | GET | sales.api | — | — | IGNORADO (200=200) |
| `/api/v1/sales/cxc/creditos/{note_id}/aplicar` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/cxc/documentos/{open_item_id}/aplicaciones` | GET | sales.api | — | — | IGNORADO (200=200) |
| `/api/v1/sales/debit-notes` | GET | sales.api | — | — | IGNORADO (200=200) |
| `/api/v1/sales/debit-notes` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/despacho/pendientes` | GET | sales.api | — | — | IGNORADO (200=200) |
| `/api/v1/sales/despacho/{order_id}/despacho` | GET | sales.api | — | — | IGNORADO (200=200) |
| `/api/v1/sales/devoluciones` | GET | sales.api | status | ruta | IGNORADO (200=200) |
| `/api/v1/sales/devoluciones` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/devoluciones/elegibles/{invoice_id}` | GET | sales.api | — | — | IGNORADO (200=200) |
| `/api/v1/sales/devoluciones/{return_id}` | GET | sales.api | — | — | IGNORADO (200=200) |
| `/api/v1/sales/devoluciones/{return_id}/decidir` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/devoluciones/{return_id}/recibir` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/devoluciones/{return_id}/reingresar` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/devoluciones/{return_id}/verificar` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/facturacion/pendientes` | GET | sales.api | — | — | IGNORADO (200=200) |
| `/api/v1/sales/facturacion/{invoice_id}/emitir` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/facturacion/{order_id}/factura` | GET | sales.api | — | — | IGNORADO (200=200) |
| `/api/v1/sales/facturacion/{order_id}/generar` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/facturacion/{order_id}/solicitar` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/invoices` | GET | sales.api | page, page_size, status | ruta | IGNORADO (200=200) |
| `/api/v1/sales/invoices` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/invoices/{invoice_id}/lines` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/invoices/{invoice_id}/transition` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/notas/acreditable/{invoice_id}` | GET | sales.api | — | — | IGNORADO (200=200) |
| `/api/v1/sales/notas/credito/{invoice_id}/generar` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/notas/credito/{note_id}` | GET | sales.api | — | — | IGNORADO (200=200) |
| `/api/v1/sales/notas/credito/{note_id}/emitir` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/notas/debito/{invoice_id}/generar` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/notas/debito/{note_id}` | GET | sales.api | — | — | IGNORADO (200=200) |
| `/api/v1/sales/notas/debito/{note_id}/emitir` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/open-items` | GET | sales.api | party_id, status | ruta | IGNORADO (200=200) |
| `/api/v1/sales/orders` | GET | sales.api | page, page_size, status | ruta | IGNORADO (200=200) |
| `/api/v1/sales/orders` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/orders/expire-reservations` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/orders/{order_id}` | GET | sales.api | — | — | IGNORADO (200=200) |
| `/api/v1/sales/orders/{order_id}/cancel` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/orders/{order_id}/lines` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/orders/{order_id}/reject` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/orders/{order_id}/release` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/orders/{order_id}/revert` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/orders/{order_id}/submit` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/orders/{order_id}/transition` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/pick-lists` | GET | sales.api | order_id, page, page_size | ruta | IGNORADO (200=200) |
| `/api/v1/sales/pick-lists` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/picking/cola` | GET | sales.api | warehouse_id | ruta | IGNORADO (200=200) |
| `/api/v1/sales/picking/{plan_id}` | GET | sales.api | — | — | IGNORADO (200=200) |
| `/api/v1/sales/picking/{plan_id}/asignaciones` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/picking/{plan_id}/cancelar` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/picking/{plan_id}/candidatas` | GET | sales.api | order_line_id | ruta | IGNORADO (200=200) |
| `/api/v1/sales/picking/{plan_id}/confirmar` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/picking/{plan_id}/consolidar` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/picking/{plan_id}/invalidar` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/picking/{plan_id}/preparacion` | GET | sales.api | — | — | IGNORADO (200=200) |
| `/api/v1/sales/picking/{plan_id}/recoger` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/quotes` | GET | sales.api | customer_id | ruta | IGNORADO (200=200) |
| `/api/v1/sales/quotes` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/quotes/{quote_id}` | GET | sales.api | — | — | IGNORADO (200=200) |
| `/api/v1/sales/quotes/{quote_id}/convertir` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/quotes/{quote_id}/lines` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/quotes/{quote_id}/transition` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/returns` | GET | sales.api | — | — | IGNORADO (200=200) |
| `/api/v1/sales/returns` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/returns/{return_id}/lines` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/settings/reservation` | GET | sales.api | — | — | IGNORADO (200=200) |
| `/api/v1/sales/settings/reservation` | PUT | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/shipments` | GET | sales.api | status | ruta | IGNORADO (200=200) |
| `/api/v1/sales/shipments` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/shipments/{shipment_id}/confirm` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/shipments/{shipment_id}/validate` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/withholdings-suffered` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/sales/withholdings-suffered/{withholding_id}/transition` | POST | sales.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/setup/initialize` | POST | setup.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/setup/status` | GET | setup.api | — | — | IGNORADO (200=200) |
| `/api/v1/system/diagnostics` | GET | system.api | — | — | AUTH_PRECEDE (403) |
| `/api/v1/tasks` | GET | notifications.api | due_from, due_to, overdue, page, page_size, priority, scope, source_type, status | ruta | IGNORADO (200=200) |
| `/api/v1/tasks/priorities` | GET | notifications.api | — | — | IGNORADO (200=200) |
| `/api/v1/tasks/priorities` | POST | notifications.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/tasks/{task_id}` | GET | notifications.api | — | — | IGNORADO (200=200) |
| `/api/v1/tasks/{task_id}/cancel` | POST | notifications.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/tasks/{task_id}/complete` | POST | notifications.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/tasks/{task_id}/reassign` | POST | notifications.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/tasks/{task_id}/start` | POST | notifications.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/treasury/accounts` | GET | treasury.api | — | — | IGNORADO (200=200) |
| `/api/v1/treasury/accounts` | POST | treasury.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/treasury/accounts/{account_id}/balance` | GET | treasury.api | — | — | IGNORADO (200=200) |
| `/api/v1/treasury/bank-transactions` | GET | treasury.api | account_id | ruta | IGNORADO (200=200) |
| `/api/v1/treasury/bank-transactions` | POST | treasury.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/treasury/banks` | GET | treasury.api | — | — | IGNORADO (200=200) |
| `/api/v1/treasury/banks` | POST | treasury.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/treasury/cash-position` | GET | treasury.api | — | — | IGNORADO (200=200) |
| `/api/v1/treasury/cash-sessions` | GET | treasury.api | status | ruta | IGNORADO (200=200) |
| `/api/v1/treasury/cash-sessions` | POST | treasury.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/treasury/cash-sessions/{session_id}` | GET | treasury.api | — | — | IGNORADO (200=200) |
| `/api/v1/treasury/cash-sessions/{session_id}/arqueo` | POST | treasury.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/treasury/cash-sessions/{session_id}/close` | POST | treasury.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/treasury/cash-sessions/{session_id}/movements` | POST | treasury.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/treasury/cash-sessions/{session_id}/pre-close` | POST | treasury.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/treasury/cash-sessions/{session_id}/reject` | POST | treasury.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/treasury/cashboxes` | GET | treasury.api | — | — | IGNORADO (200=200) |
| `/api/v1/treasury/cashboxes` | POST | treasury.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/treasury/currencies` | GET | treasury.api | — | — | IGNORADO (200=200) |
| `/api/v1/treasury/currencies` | POST | treasury.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/treasury/exchange-rates` | POST | treasury.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/treasury/exchange-rates/import` | POST | treasury.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/treasury/exchange-rates/import-batches` | GET | treasury.api | — | — | IGNORADO (200=200) |
| `/api/v1/treasury/exchange-rates/observations` | GET | treasury.api | base_currency, date_from, date_to, page, page_size, quote_currency, source_id, status | ruta | IGNORADO (200=200) |
| `/api/v1/treasury/exchange-rates/observations` | POST | treasury.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/treasury/exchange-rates/observations/{observation_id}/approve` | POST | treasury.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/treasury/exchange-rates/observations/{observation_id}/correct` | POST | treasury.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/treasury/exchange-rates/resolve` | GET | treasury.api | base_currency, effective_at, quote_currency, rate_type, source_code | ruta | IGNORADO (200=200) |
| `/api/v1/treasury/executions/egresos` | POST | treasury.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/treasury/executions/ingresos` | POST | treasury.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/treasury/fiscal-rules` | GET | treasury.api | — | — | IGNORADO (200=200) |
| `/api/v1/treasury/fiscal-rules` | POST | treasury.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/treasury/fx-conversions` | GET | treasury.api | — | — | IGNORADO (200=200) |
| `/api/v1/treasury/fx-conversions` | POST | treasury.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/treasury/fx-policies` | GET | treasury.api | — | — | IGNORADO (200=200) |
| `/api/v1/treasury/fx-policies` | POST | treasury.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/treasury/fx-policies/{policy_id}/activate` | POST | treasury.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/treasury/igft-events` | GET | treasury.api | event_type | ruta | IGNORADO (200=200) |
| `/api/v1/treasury/igft-events/evaluate` | POST | treasury.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/treasury/instruments` | GET | treasury.api | — | — | IGNORADO (200=200) |
| `/api/v1/treasury/instruments` | POST | treasury.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/treasury/payment-methods` | GET | treasury.api | — | — | IGNORADO (200=200) |
| `/api/v1/treasury/payment-methods` | POST | treasury.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/treasury/rate-policies` | GET | treasury.api | — | — | IGNORADO (200=200) |
| `/api/v1/treasury/rate-policies` | POST | treasury.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/treasury/rate-policies/{policy_id}/activate` | POST | treasury.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/treasury/rate-sources` | GET | treasury.api | — | — | IGNORADO (200=200) |
| `/api/v1/treasury/rate-sources` | POST | treasury.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/treasury/rate-sources/{source_id}/status` | POST | treasury.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/treasury/reconciliation-lines/{line_id}/resolve` | POST | treasury.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/treasury/reconciliations` | GET | treasury.api | status | ruta | IGNORADO (200=200) |
| `/api/v1/treasury/reconciliations` | POST | treasury.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/treasury/reconciliations/{reconciliation_id}` | GET | treasury.api | — | — | IGNORADO (200=200) |
| `/api/v1/treasury/reconciliations/{reconciliation_id}/lines` | POST | treasury.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/treasury/reconciliations/{reconciliation_id}/match` | POST | treasury.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/treasury/reconciliations/{reconciliation_id}/transition` | POST | treasury.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/treasury/refunds` | GET | treasury.api | status | ruta | IGNORADO (200=200) |
| `/api/v1/treasury/refunds` | POST | treasury.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/treasury/refunds/{refund_id}` | GET | treasury.api | — | — | IGNORADO (200=200) |
| `/api/v1/treasury/refunds/{refund_id}/decide` | POST | treasury.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/treasury/refunds/{refund_id}/settle` | POST | treasury.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/treasury/transfers` | GET | treasury.api | — | — | IGNORADO (200=200) |
| `/api/v1/treasury/transfers` | POST | treasury.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/users` | GET | identity_access.api | — | — | AUTH_PRECEDE (403) |
| `/api/v1/users` | POST | identity_access.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/users/{user_id}/mfa/reset` | POST | identity_access.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/users/{user_id}/roles` | POST | identity_access.api | — | — | IGNORADO (sin mecanismo; framework) |
| `/api/v1/users/{user_id}/roles/{role_id}` | DELETE | identity_access.api | — | — | IGNORADO (sin mecanismo; framework) |
