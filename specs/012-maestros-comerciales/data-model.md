# MODELO DE DATOS — SPEC 012

Nueve entidades. Ninguna nace con filas.

```
PaymentTerm ──┐
CommercialZone┤
SalesChannel ─┤
              ├── CustomerCommercialTerms ── (FK) ── Customer  [existente]
CreditPolicy ─┘

PriceList ── PriceListVersion ── PriceListItem
                    │
                    └── (congelada en) ── *_lines.price_source_version_id

DiscountPolicy ── (excedida) ──> ApprovalRequest  [Spec 045, sin cambios]

PricePrecedence  (orden declarado por empresa)

SalesCommissionPolicy   ← RESERVADA, sin implementar
```

## 1. `payment_terms`

| Campo | Tipo | Nota |
|---|---|---|
| `company_id` | FK | por empresa |
| `code`, `name` | texto | únicos por empresa |
| `kind` | enum | `CASH`, `DAYS`, `INSTALLMENTS`, `ADVANCE` |
| `days` | int? | para `DAYS` |
| `installments` | JSON? | `[{offset_days, percent}]` para `INSTALLMENTS` |
| `advance_percent` | Numeric? | para `ADVANCE` |
| `due_offset_from` | enum | `ISSUE_DATE`, `DELIVERY_DATE`, `RECEPTION_DATE` |
| `legacy_value` | texto? | la cadena original que lo originó, si vino del legado |
| `status` | enum | `ACTIVE`, `INACTIVE` |

**Nace vacía.** «Contado» no viene de fábrica.

## 2. `commercial_zones`

| Campo | Tipo | Nota |
|---|---|---|
| `company_id`, `code`, `name` | — | — |
| `parent_id` | FK? | jerarquía opcional de territorio |
| `salesperson_id` | FK? | usuario asignado |
| `route` | texto? | — |
| `legacy_value` | texto? | — |

> **No** es `warehouse_zones`. Ninguna FK entre ambas. Ninguna vista común.

## 3. `sales_channels`

`company_id`, `code`, `name`, `status`. Nace vacía.

## 4. `price_lists`

| Campo | Tipo | Nota |
|---|---|---|
| `company_id`, `code`, `name` | — | — |
| `currency` | FK → `currencies` | **el maestro existente**, no uno nuevo |
| `segment` | texto? | opcional |
| `channel_id` | FK? | — |
| `source` | texto? | quién la cargó y de dónde (`FR-012-008`) |
| `status` | enum | — |

## 5. `price_list_versions`

| Campo | Tipo | Nota |
|---|---|---|
| `price_list_id` | FK | — |
| `version_number` | int | correlativo **del servidor** |
| `valid_from`, `valid_to` | date | `valid_to` nulo = abierta |
| `status` | enum | `DRAFT`, `ACTIVE`, `SUPERSEDED`, `ARCHIVED` |
| `approved_by`, `approved_at` | — | — |

**Restricción:** dos versiones de la misma lista no solapan vigencia. Índice
único parcial o exclusión por rango, como hizo 011 con las presentaciones.

## 6. `price_list_items`

| Campo | Tipo | Nota |
|---|---|---|
| `version_id` | FK | — |
| `item_id` | FK? | producto concreto |
| `category_id` | FK? | o categoría — **uno de los dos, no ambos** |
| `presentation_id` | FK? | Spec 011 |
| `uom_id` | FK? | Spec 011 |
| `min_quantity` | Numeric? | rango de volumen |
| `unit_price` | **`Numeric(18,4)`** | jamás `float` |

## 7. `price_precedence`

| Campo | Tipo | Nota |
|---|---|---|
| `company_id` | FK | la precedencia es **por empresa** |
| `order_index` | int | — |
| `source_kind` | enum | `CUSTOMER_CONTRACT`, `CUSTOMER_LIST`, `SEGMENT_LIST`, `BRANCH_LIST`, `COMPANY_LIST` |
| `enabled` | bool | — |

KONTROL puede **sembrar el orden por defecto documentado en `ADR-D0-005`** como
punto de partida editable. Eso no viola `P8`: el valor es dato en tabla, no
código, y la empresa lo reordena.

## 8. `discount_policies`

| Campo | Tipo | Nota |
|---|---|---|
| `company_id`, `code`, `name` | — | — |
| `scope` | enum | `LINE`, `DOCUMENT` |
| `applies_to` | enum | `ROLE`, `ITEM`, `CATEGORY`, `ALL` |
| `applies_ref` | texto? | — |
| `max_percent` | Numeric? | **sin valor por defecto** |
| `requires_approval_above` | Numeric? | umbral que dispara la Spec 045 |
| `stackable` | bool | — |
| `incompatible_with` | JSON? | — |
| `version` | int | — |

## 9. `credit_policies`

`company_id`, `code`, `credit_limit`, `exposure_calculation`, `block_on_overdue`,
`grace_days`, `version`.

> Distinta de `payment_terms` (`R-D0-05-4`): una dice **cuándo se paga**, la otra
> **cuánto riesgo se admite**.

## 10. `customer_commercial_terms`

Extiende, no duplica (`FR-012-051`):

`customer_id` (FK único) · `price_list_id` · `payment_term_id` ·
`commercial_zone_id` · `sales_channel_id` · `credit_policy_id` ·
`salesperson_id` · `blocked_by`, `blocked_at`, `block_reason`.

Los cuatro textos de `customers` **se conservan** como `legacy_*`.

## 11. Snapshot en las líneas transaccionales

Columnas añadidas a `sales_quote_lines`, `sales_order_lines`,
`sales_invoice_lines` y equivalentes:

| Campo | Nota |
|---|---|
| `price_source_version_id` | **la versión que produjo el precio** |
| `price_source_item_id` | el ítem concreto de esa versión |
| `pricing_source` | `RESOLVED`, `MANUAL_JUSTIFIED`, `LEGACY_FREETEXT` |
| `discount_policy_id`, `discount_policy_version` | — |
| `discount_approval_request_id` | si hizo falta aprobación |
| `payment_term_snapshot` | JSON congelado |

Todas **anulables**: las líneas existentes no se inventan.

## 12. Reservada

`sales_commission_policies` — declarada en el modelo, **sin implementar**
(`FR-012-090`). Existe para que añadirla luego no obligue a rediseñar.

## 13. Borrado y desactivación

| Entidad | Se borra si | Si no |
|---|---|---|
| `PriceListVersion` | nunca, si algún documento la referencia | `ARCHIVED` |
| `PaymentTerm` | nunca, si algún cliente o documento la usa | `INACTIVE` |
| `DiscountPolicy` | nunca, si algún descuento la registró | versión nueva |

Mismo criterio que 008, 011 y 046: **la historia no se borra**.
