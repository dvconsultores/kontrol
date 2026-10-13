# Inventario transversal de listados (Discovery 01) · HEAD 6202994

Fuente: lectura estática de `app/modules/**/api*.py` (177 operaciones `GET` candidatas; se excluyen detalles por id,
singletons, salud, diagnóstico, saldos y descargas). Clasificación por estilo de paginación del servidor. Este inventario
determina la convención; **no autoriza a modificar todos los endpoints** (FR-LT-014).

| Clase | Nº | Qué es | Ejemplos |
|---|---|---|---|
| `CON_TOPE_Y_SOBRE` (canónico) | **17** | `page: Query(1, ge=1)`, `page_size: Query(20, ge=1, le=100)`, `{items,total,page,page_size}`, `count` antes de cortar, orden en SQL | `organization/companies`, `audit/events`, `inventory/{balances,movements,lots,transfers}`, `master_data/{terceros,items,items/search}`, `purchasing/{requisitions,orders,supplier-invoices}`, `sales/{orders,invoices}`, `notifications/{notifications,tasks,alerts}`, `treasury/exchange-rates/observations` |
| `CON_SOBRE_SIN_TOPE` (estilo `limit/offset`, sin máximo) | **8** | `limit: int = 50|100, offset: int = 0` sin `Query(ge/le)`; sobre `{total, limit, offset, items}` | **`organization/warehouses`** (objetivo), `organization/locations`, `organization/locations/ordered` (defecto 100), `organization/warehouse_api.py:974`, `master_data/uom_api.py:189` (`maestros/unidades`), `approvals/inbox`, `documents/api.py:347` |
| `SIN_PAGINAR` con sobre falso | **79** | `{items, total: len(items), page: 1, page_size: len(items) or 1}`: nombres del canon, sin cortar nunca | **`sales/pick-lists`** (objetivo), `sales/{quotes,shipments,credit-notes,debit-notes,returns,devoluciones,open-items,collections,…}`, `fiscal/*` (12), `treasury/*` (23), `regulatory/*` (11), `purchasing/{quotes,receipts,incidencias,triple-match,returns,credit-notes,open-items,payments}`, `inventory/{movement-types,serials,reservations,counts,adjustments,cost-layers,costing-profiles,putaway/*}`, `reporting/{exports,jobs}`, `homologation/{records,releases}` |
| `CON_TOPE_LISTA_SIMPLE` | 0 | — | — |
| `N_A` (lista simple corta o recurso singular/derivado) | resto | listas de catálogo pequeñas sin sobre (`list[...]`), colas, pendientes, saldos, descargas | `notifications/{sources,rules,preferences,priorities}`, `organization/{branches,establishments}`, `sales/picking/cola`, `*/pendientes`, `*/aging`, `*/dashboard` |
| `UNKNOWN` | **0** | — | — |

Scope de implementación de este ciclo: **solo** `GET /organization/warehouses` (tope y validación de `limit`/`offset`) y
`GET /sales/pick-lists` (paginación canónica). Los otros 7 `limit/offset` y los otros 78 sobres falsos se registran como
`ADDITIONAL_UNBOUNDED_LISTING` en el delta (§13) para la dueña: son del mismo tipo de deuda, con dueñas distintas
(fiscal 007/039–043 intocables, tesorería 006, regulación 008-regulacion, compras 004, ventas 005…) y consumidores que
habría que inventariar uno a uno; no se corrigen «de paso».

Columnas del encargo para los dos objetivos:

| | `GET /organization/warehouses` | `GET /sales/pick-lists` |
|---|---|---|
| OWNER_SPEC | 008 (almacenes físicos) | 031 (picking; delta en `specs/005-ventas-cuentas-por-cobrar/`) |
| RESPONSE_MODEL / RAW_LIST_OR_ENVELOPE | `dict` → sobre `{total, limit, offset, items}` | `dict` → sobre `{items, total, page, page_size}` (falso) |
| LIMIT_PARAM / DEFAULT / MIN / MAX | `limit` / 50 / **ninguno** / **ninguno** | — (`page_size` ignorado) |
| OFFSET_PARAM / DEFAULT · PAGE_PARAM | `offset` / 0 (sin mínimo) · — | — · — (`page` ignorado) |
| ORDER_BY / DIRECTION | `code` asc | `created_at` desc, sin desempate |
| TOTAL_COUNT | sí, en SQL antes de cortar | `len(items)` |
| COMPANY_SCOPED / TENANT_SCOPED | sí (`_alcance(ctx)`) / sí (vía contexto) | sí (`ctx.company_id`) / sí |
| AUTH / PERMISSION | Bearer / `organization:view` | Bearer / sesión (`get_current_user`) |
| OPENAPI | `limit` y `offset` enteros sin límites; esquema 200 `{}` | solo `order_id`; esquema 200 `{}` |
| KNOWN_CONSUMERS | 12 pantallas, 10 suites E2E, 3 guiones QA, 2 suites backend | 1 pantalla (`PreparacionPage`), 3 suites E2E, 0 QA, 0 suites backend con GET |
| CLASSIFICATION | CON_SOBRE_SIN_TOPE | SIN_PAGINAR |
