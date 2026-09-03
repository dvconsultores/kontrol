# SPEC 030 — INFORME DE LA MIGRACIÓN `0043_spec030_reservation`

| Campo | Valor |
|---|---|
| Revisa | `0042_spec029_origin` |
| Clasificación | `SAFE_MIGRATION` (columnas, índices, checks, renombrado de estados, permiso) + `MANUAL_REVIEW_REQUIRED` (pedidos en vuelo sin reserva; reservas ambiguas) |
| Reversible | sí: `downgrade` devuelve `RELEASED → RESERVED`, retira columnas, índices y checks. No reconstruye `CREDIT_PENDING` (no se inventa) |
| Verificación | instalación limpia `upgrade head` → `downgrade 0042` → `upgrade head` sobre PostgreSQL 18.6; `tests/test_spec030_migration_0043.py` (7 casos con datos sembrados en 0042); `tests/test_migrations_offline.py` |

## Esquema

| Tabla | Cambio |
|---|---|
| `sales_orders` | `status_reason` (500), `submitted_at`, `released_at` |
| `companies` | `reservation_ttl_days` (nullable) |
| `reservations` | `source_type`, `source_order_id` (FK `sales_orders`), `source_line_id` (FK `sales_order_lines`), `trigger`, `oversell` (default `false`), `released_at`, `released_by`, `release_reason`; `ix_reservations_source_order`; `uq_reservations_active_line` (parcial: `status='ACTIVE' AND source_line_id IS NOT NULL`); `ck_reservations_quantity_positive` |
| `inventory_balances` | `uq_inventory_balances_key` (con `COALESCE` en `location_id`, `lot_id`, `serial_id`); `ck_inventory_balances_reserved_nonneg` |
| `permissions` / `role_permissions` | `ventas:submit`, concedido a `ADMIN` (patrón 0013) |

Los `CHECK` se crean con SQL directo: `op.create_check_constraint` aplicaría la convención de nombres
del metadata y produciría `ck_reservations_ck_reservations_…`, distinto del nombre del ORM. Detectado
en el ciclo `downgrade/upgrade` de la instalación limpia y corregido; el `downgrade` retira ambos
nombres por si una base intermedia lo tuviera.

## Datos: clasificación de las reservas existentes (§78, sin origen inventado)

| Clase | Regla | Resultado |
|---|---|---|
| `ORDER_RECONSTRUCTIBLE` | `source_document = 'SALES_ORDER:{id}'` y el pedido existe | `source_type = SALES_ORDER`, `source_order_id`, `trigger = LEGACY_CREDIT_APPROVAL`; `source_line_id` **solo** si el pedido tiene exactamente una línea de ese producto |
| `CRITICAL_AMBIGUOUS` | el pedido existe y tiene varias líneas del producto | línea `NULL`; id listado en el log para revisión manual |
| `LEGACY_UNVERIFIED` | patrón de pedido, pedido inexistente | `trigger = LEGACY_CREDIT_APPROVAL`; sin `source_type` |
| `MANUAL` | sin patrón de pedido | `source_type = MANUAL`, `trigger = MANUAL` |
| `BASE_ASSUMED` | `base_quantity` nulo | `base_quantity = quantity`, factor 1, `uom_source = LEGACY_ASSUMED_BASE` |

Las reservas ya `RELEASED` por el despacho antiguo se quedan así: la semántica con la que nacieron
no se reinterpreta (P5).

## Datos: estados del pedido (§79)

`RESERVED → RELEASED` (equivalencia contractual) · `APPROVED → RELEASED` (nunca observable) ·
`CREDIT_PENDING → SUBMITTED` (emitido a la espera de crédito). Los dos últimos grupos carecen de
reserva bajo la nueva semántica: **la migración no reserva por ellos**; imprime sus ids con la nota
«revisión manual». El operador los revierte a borrador y los reemite, o los cancela.

## Guardas de integridad antes de crear restricciones

- `quantity <= 0` en reservas → la migración **falla** con instrucción (no se puede añadir el check
  sobre datos que lo violan).
- Claves de saldo duplicadas → la migración **falla** con instrucción de recomputar y revisar.
- `qty_reserved < 0` → se corrige a 0 y `qty_available = qty_on_hand`, informando la cuenta: un
  reservado negativo es un contador roto, no un dato.

## Log de referencia (instalación limpia)

```
[0043 spec030] reservas clasificadas: {'ORDER_RECONSTRUCTIBLE': 0, 'CRITICAL_AMBIGUOUS': 0, 'LEGACY_UNVERIFIED': 0, 'MANUAL': 0, 'BASE_ASSUMED': 0}
```

Con datos sembrados (`test_spec030_migration_0043.py`): 1 reconstruible (con línea), 1 ambigua (sin
línea, listada), 1 no verificada, 1 manual, 4 con base asumida; `RESERVED → RELEASED: 1`,
`CREDIT_PENDING → SUBMITTED: 1 (revisión manual)`.
