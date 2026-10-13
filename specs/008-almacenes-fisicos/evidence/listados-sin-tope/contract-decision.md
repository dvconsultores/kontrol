# Decisión de contrato (W17/W18) · sin blocker

| Decisión | Valor | Fuente |
|---|---|---|
| Almacenes: `limit` | `Query(50, ge=1, le=100)`: defecto 50 (contrato WHL vigente), tope **100** (canon de plataforma), 422 fuera de rango | `pagination-convention.md`, `limit-convention.md` |
| Almacenes: `offset` | `Query(0, ge=0)`: 422 si negativo (antes 500 en PostgreSQL) | validación canónica |
| Almacenes: sobre, orden, filtros, alcance | `{total, limit, offset, items}`, `code` asc, `q/branch_id/status/company_id`, `_alcance(ctx)` — **sin cambio** | WHL |
| Pick-lists: parámetros | `order_id`, `page: Query(1, ge=1)`, `page_size: Query(20, ge=1, le=100)` | canon |
| Pick-lists: sobre | `{items, total, page, page_size}`; `total` = `count` en SQL sobre la consulta ya filtrada por empresa y `order_id`, antes de cortar | canon, FR-001-179 |
| Pick-lists: orden | `created_at desc, id asc` en SQL (negocio actual + desempate del precedente de empresas) | `organization/api.py:100` |
| Pick-lists: corte | `offset((page-1)*page_size).limit(page_size)` en SQL; nunca en Python | FR-LT / M-09 |
| Consumidores que necesitan todo | recorren páginas con el máximo (100): `listAllWarehouses` (frontend, espejo de `listAllCompanies`), `todasLasListasDePreparacion` (E2E) | FR-001-188 |
| Estilo `limit/offset` de almacenes y de otros 7 listados; 78 sobres falsos restantes | **no se cambian**: observación `ADDITIONAL_UNBOUNDED_LISTING` para las dueñas | FR-LT-014 |
| Alcance de empresa | sin cambio: contexto validado → filtro de empresa → filtros → `count` → orden → corte | FR-LT-007/008 |

`LIMIT_MAX_RATIFIED = YES` · `ENVELOPE_RATIFIED = YES` · `OVER_LIMIT = 422` · `ORDERING_CONTRACT = PROVEN` ·
`TENANT_SCOPE_PRESERVED = PROVEN` · `MATERIAL OQ = 0` · ningún STOP (A–H) se activa.
