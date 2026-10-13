# Convención de paginación · fuente de autoridad

| Registro | Valor | Fuente |
|---|---|---|
| `CANONICAL_ENVELOPE` | `{items, total, page, page_size}` | `specs/001-fundacion/contracts/api-contracts.md:11` («Listados con `q`, `status`, `sort`, `page`, `page_size`»), transcrito y ratificado en `specs/001-fundacion/spec001-empresas-sobre-delta.md` §5 (EMPRESAS-SIN-SOBRE, convergida) y `spec001-auditoria-paginacion-delta.md` §3 (AUDITORIA-PAGINACION-CLIENTE, convergida) |
| `CANONICAL_PAGE_BASE` / `CANONICAL_LIMIT_DEFAULT` | `page` desde **1** · `page_size` **20** | ídem (`PAGE_BASE = 1 · DEFAULT_PAGE_SIZE = 20`) |
| `CANONICAL_LIMIT_MAX` | **100** (`page_size` `le=100`) | ídem (`MAX_PAGE_SIZE = 100`; FR-001-177 «100 máximo») |
| `OVER_LIMIT_BEHAVIOR` | **422** `VALIDATION_ERROR` (validación `Query(ge=…, le=…)` de FastAPI; AC-047: `page=0`, `page_size=101`, `page=x` → 422) — nunca recorte silencioso | ídem |
| Página más allá del final | 200 con `items: []` y el mismo `total` | AC-043/046; `spec001-auditoria-paginacion-delta.md` PAG-E2E-04 |
| `total` | el conjunto visible tras tenant, alcance del usuario y filtros, **antes** de cortar la página; mismo predicado que `items` | FR-001-179 |
| `ORDERING_REQUIREMENT` | orden determinista en la base con desempate por `id` | precedente ratificado en el listado de empresas: `order_by(Company.created_at, Company.id)` (`organization/api.py:100`) |
| Consumidores que necesitan todo | recorren las páginas que el contrato declara, con el tamaño máximo | FR-001-188 |
| `SOURCE_OF_AUTHORITY` | Spec fundacional 001 (contrato transversal) + dos deltas convergidas que lo transcriben como canon | — |

Implementación canónica en el producto: 17 listados con `page: int = Query(1, ge=1)`, `page_size: int = Query(20, ge=1,
le=100)` (empresas, auditoría, existencias, movimientos, lotes, transferencias, terceros, artículos, requisiciones,
órdenes de compra, facturas de compra, pedidos y facturas de venta, notificaciones, tareas, alertas, observaciones de tasa).

`CONVENTION_IDENTIFIED = YES` · `ENVELOPE_RATIFIED = YES` · `LIMIT_MAX_RATIFIED = YES` (100) · `OVER_LIMIT = 422` ratificado.
