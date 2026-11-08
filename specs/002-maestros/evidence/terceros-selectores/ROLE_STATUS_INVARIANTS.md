# Invariantes de rol y estado del tercero

## Autoridad única (backend)

`app/modules/master_data/service.py`:

```
require_eligible_party(db, *, company_id: str, party_id: str, role: str | None, require_active: bool) -> Party
```

Se evalúa en este orden:

1. Si el tercero no existe o pertenece a otra empresa, devuelve `NotFoundError("PARTY_NOT_FOUND")` (404). Es el mismo contrato de hoy
   y no revela si el tercero existe en otra empresa.
2. Si `role` no es `None` y no está entre `party.roles` (comparando en mayúsculas), devuelve `ConflictError("PARTY_ROLE_REQUIRED")` (409).
3. Si `require_active` es verdadero y `party.status != "ACTIVE"`, devuelve `ConflictError("PARTY_INACTIVE")` (409). Sigue la convención
   de `SERIES_INACTIVE`, `CURRENCY_INACTIVE` y `COMPANY_INACTIVE`.

Todas las mutaciones de la matriz (`PROCESS_CONTRACT.md`) pasan por esta función. Las lecturas (`customer_balance`, `customer_statement`
y `customer_credits`) conservan la comprobación de empresa sin rol ni estado: la historia sigue siendo consultable.

| Llamador | role | require_active |
|---|---|---|
| sales `create_quote`, `create_order`, `create_invoice` | CLIENTE | sí |
| sales `create_credit_note`, `create_debit_note` | CLIENTE | no |
| purchasing `create_quote`, `create_order`, `create_invoice` | PROVEEDOR | sí |
| purchasing `create_credit_note`, `create_schedule` | PROVEEDOR | no |
| `register_payment(direction)` | `OUT` → PROVEEDOR, `IN` → CLIENTE | no |
| `register_advance(direction)` | `OUT` → PROVEEDOR, `IN` → CLIENTE | sí |
| `create_withholding(party_role=…)` | lo fija el llamador: purchasing y fiscal → PROVEEDOR; `sales /withholdings-suffered` → CLIENTE | no |
| regulatory `create_driver`, `create_vehicle(owner_party_id)` | ninguno | sí |

## Filtro de la API (UX, no autoridad)

`GET /maestros/terceros` recibe `role` (opcional, patrón `^[A-Za-z_]{1,32}$`). La comparación es en mayúsculas contra el JSON de
`roles` (`UPPER(CAST(roles AS TEXT)) LIKE '%"CLIENTE"%'`), igual en SQLite y PostgreSQL. Sin `role` el resultado no cambia, así que el
cambio es compatible. `status` ya existe. El frontend lo usa para no ofrecer terceros no elegibles, pero la autoridad es el backend.

## Historia

Ninguna regla se aplica a documentos existentes ni se recalcula nada. Un tercero desactivado después sigue apareciendo en sus documentos,
y el selector resuelve su etiqueta por id (`GET /maestros/terceros/{id}`) aunque ya no se ofrezca para una selección nueva.
