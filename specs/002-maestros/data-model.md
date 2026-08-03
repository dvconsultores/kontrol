# DATA MODEL — 002-MAESTROS

| Campo | Valor |
|---|---|
| Iniciativa | 002-maestros |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Responsable | Arquitecto de datos |
| Ruta | `specs/002-maestros/data-model.md` |
| Fuente | DOC-03 §3-4, §12 |

## 1. Principios (heredados de 001/DOC-03)

- UUID interno; códigos de negocio separados; multiempresa (`company_id` en cada agregado).
- RIF, cédulas, teléfonos, cuentas, códigos, seriales e IMEI son **texto**.
- Soft delete solo en maestros permitidos; documentos futuros usan estados.
- Auditoría uniforme (`created_at/by`, `updated_at/by`).
- Versiones para perfiles y reglas; snapshots JSON solo como copia histórica.
- Constraints e índices implementan reglas críticas; idempotencia y versión/ETag.

## 2. Entidades — Terceros

| Entidad | Campos mínimos | Notas |
|---|---|---|
| `Party` | id, company_id, code, person_type, nationality/residence, legal_name, trade_name, tax_id (RIF), economic_activity, status | Entidad común |
| `PartyAddress` | party_id, type, country, state, city, municipality, postal_code, address, fiscal, delivery, validity | |
| `PartyContact` | party_id, name, role, phone, email, preferred, validity | |
| `PartyBankAccount` | party_id, bank, account_type, currency, account_number, beneficiary, verified, evidence | |
| `Customer` | party_id, salesperson, zone, price_list, payment_term, credit_days, credit_limit, blocked, reason | extensión |
| `Supplier` | party_id, category, buyer, payment_term, default_currency, approval_status, withholding_profile | extensión |
| `Carrier` | party_id, registration, insurance, permits | extensión |
| `Driver` | party_id, license, categories, expiry, restrictions | extensión |

Reglas: Unique `(company_id, tax_id, role)` con excepciones documentadas; RIF validado por formato.

## 3. Entidades — Taxonomía y atributos

| Entidad | Campos mínimos | Notas |
|---|---|---|
| `TaxonomyNode` | id, company_id/global, parent_id, level (SECTOR/RUBRO/CATEGORIA/FAMILIA/LINEA/TIPO), code, name, applies_to, status | Árbol jerárquico |
| `AttributeDefinition` | id, code, data_type, unit, required, multiple, options (JSON), validation, searchable, permissions | Gobernado |
| `AttributeApplicability` | attribute_id, rubric/category/template, condition, order, section | |
| `AttributeValue` | item_id, attribute_id, typed_value, validity | Índices para buscables |
| `ProductTemplate` | code, name, behaviors (inventory, lot, serial, expiry, variants, warranty, decimals, buy/sell/rent), version, status | |
| `ServiceTemplate` | code, name, billing mode, recurrence, scheduling, contract, materials, acceptance, version, status | |

Regla: datos críticos nunca en EAV libre (inventario, impuestos, lotes, seriales, regulación).

## 4. Entidades — Catálogo

| Entidad | Campos mínimos | Notas |
|---|---|---|
| `CatalogItem` | id, company_id, type (PRODUCT/SERVICE), code, name, short/long description, category_id, base_unit, tax_profile_id, status | Base común |
| `Product` | item_id, product_template_id, inventory_profile_id, traceability_profile_id, regulatory_profile_id, manufacturer, origin_country | |
| `Service` | item_id, service_template_id, billing_unit, duration, recurrence, delivery_mode, contract_required, evidence_required | |
| `UnitOfMeasure` | dimension, code, symbol, decimals, status | |
| `UnitConversion` | from_id, to_id, factor, rounding, validity | |
| `Presentation` | product_id, name, unit_id, content, barcode, buy/sell/storage flags | |
| `Barcode` | product/presentation, symbology, value, primary, validity | Unique por empresa/presentación |
| `ProductVariant` | parent_product_id, combination, code, barcode, status | |

## 5. Entidades — Perfiles versionados

| Entidad | Campos mínimos | Notas |
|---|---|---|
| `ProfileVersion` (base) | id, company_id, profile_type (INVENTORY/TRACEABILITY/FISCAL/REGULATORY), code, name, payload JSON, effective_from/to, status, approval | Versionado |
| `InventoryProfile` | version_id, stockable, lot, serial, expiry, variants, weight, kit, decimals | |
| `TraceabilityProfile` | version_id, level (none/lot/serial/imei), fefo, warranty, cold_chain, origin_destination | |
| `FiscalProfile` | version_id, tax_classification, exempt/exonerated/not_subject, islr_concept_ref, rules_by_operation | Referencia a reglas |
| `RegulatoryProfile` | version_id, requires_seniat_dispatch, requires_sica, requires_sigesai, requires_sacs, requires_animal_health, requires_plant_health, requires_cold_chain, requires_lot, requires_expiry, requires_origin_unit, requires_destination_auth, requires_vehicle, requires_driver, requires_other | Referencia a Spec 008 |

## 6. Reglas de integridad críticas

| Regla | Restricción |
|---|---|
| Duplicidad de RIF | Unique `(company_id, tax_id, role)` con excepciones documentadas |
| Barcode | Unique por empresa/presentación |
| Conversión | factor > 0; no solapar vigencias para la misma clave |
| Versiones de perfil | no solapar `effective_from/to` incompatibles |
| Multiempresa | FK críticas confirman misma empresa/tenant |
| Concurrencia | `version`/ETag en maestros editables; 409 en conflicto |

## 7. Estados

| Objeto | Estados |
|---|---|
| `Party` | DRAFT → PENDING_APPROVAL → ACTIVE → INACTIVE; REJECTED |
| `Supplier` | DRAFT → PENDING_APPROVAL → APPROVED → ACTIVE → INACTIVE; REJECTED |
| `CatalogItem` | DRAFT → ACTIVE → INACTIVE |
| `TaxonomyNode` | DRAFT → ACTIVE → INACTIVE |
| `ProfileVersion` | DRAFT → APPROVED → ACTIVE → SUPERSEDED |

## 8. Convenciones

- Timestamps ISO 8601 con zona; servidor como autoridad.
- Decimal exacto para cantidades/precios.
- Índices: FK multiempresa, `party.tax_id`, `catalog_item.code`, `barcode.value`, `taxonomy.code`, atributos buscables.

## 9. Estado de aprobación

| Elemento | Estado |
|---|---|
| Entidades | ✔ |
| Reglas de integridad | ✔ |
| Máquinas de estado | ✔ |
| Aprobación | Pendiente |
