# Reproducción ANTES · `GET /organization/warehouses` (W06) y `GET /sales/pick-lists` (W07)

Guion de medición de Claude fuera del repositorio (`repro.py`): mundo sintético en proceso (`TestClient`), una empresa
D1 con **1 100 listas de preparación** y **300 almacenes**, y una empresa C2 con 50 listas y 1 almacén que **no deben
aparecer**. Latencias en proceso (sin red); bytes del cuerpo JSON. Nada real.

## SQLite en memoria

```
motor=sqlite · empresa D1: 1100 listas, 300 almacenes · empresa C2: 50 listas, 1 almacén
/sales/pick-lists                                       → 200 items= 1100 total=1100 page=1 page_size=1100 limit=None bytes=  203550     27.8 ms
/sales/pick-lists?page=1&page_size=20                   → 200 items= 1100 total=1100 page=1 page_size=1100 limit=None bytes=  203550     23.1 ms
/sales/pick-lists?page=2&page_size=100                  → 200 items= 1100 total=1100 page=1 page_size=1100 limit=None bytes=  203550     23.8 ms
/sales/pick-lists?page_size=101                         → 200 items= 1100 total=1100 page=1 page_size=1100 limit=None bytes=  203550     22.9 ms
/sales/pick-lists?page=0                                → 200 items= 1100 total=1100 page=1 page_size=1100 limit=None bytes=  203550     23.5 ms
/sales/pick-lists?page=abc                              → 200 items= 1100 total=1100 page=1 page_size=1100 limit=None bytes=  203550     23.7 ms
/organization/warehouses                                → 200 items=   50 total=300 page=None page_size=None limit=50 bytes=   29185     17.3 ms
/organization/warehouses?limit=1                        → 200 items=    1 total=300 page=None page_size=None limit=1 bytes=     626      8.8 ms
/organization/warehouses?limit=50                       → 200 items=   50 total=300 page=None page_size=None limit=50 bytes=   29185     11.2 ms
/organization/warehouses?limit=100                      → 200 items=  100 total=300 page=None page_size=None limit=100 bytes=   58336     14.3 ms
/organization/warehouses?limit=101                      → 200 items=  101 total=300 page=None page_size=None limit=101 bytes=   58920     14.2 ms
/organization/warehouses?limit=100000                   → 200 items=  300 total=300 page=None page_size=None limit=100000 bytes=  175139     27.8 ms
/organization/warehouses?limit=0                        → 200 items=    0 total=300 page=None page_size=None limit=0 bytes=      45      6.4 ms
/organization/warehouses?limit=-1                       → 200 items=  300 total=300 page=None page_size=None limit=-1 bytes=  175135     27.4 ms
/organization/warehouses?limit=abc                      → 422 items=    - total=None page=None page_size=None limit=None bytes=     238      5.6 ms code=VALIDATION_ERROR
/organization/warehouses?offset=0                       → 200 items=   50 total=300 page=None page_size=None limit=50 bytes=   29185     10.6 ms
/organization/warehouses?offset=100000                  → 200 items=    0 total=300 page=None page_size=None limit=50 bytes=      51      6.0 ms
/organization/warehouses?offset=-1                      → 200 items=   50 total=300 page=None page_size=None limit=50 bytes=   29186     10.9 ms
```

## PostgreSQL (`ktest`, schema del arnés)

```
motor=postgresql · empresa D1: 1100 listas, 300 almacenes · empresa C2: 50 listas, 1 almacén
/sales/pick-lists                                       → 200 items= 1100 total=1100 page=1 page_size=1100 limit=None bytes=  203550     28.6 ms
/sales/pick-lists?page=1&page_size=20                   → 200 items= 1100 total=1100 page=1 page_size=1100 limit=None bytes=  203550     24.5 ms
/sales/pick-lists?page=2&page_size=100                  → 200 items= 1100 total=1100 page=1 page_size=1100 limit=None bytes=  203550     24.9 ms
/sales/pick-lists?page_size=101                         → 200 items= 1100 total=1100 page=1 page_size=1100 limit=None bytes=  203550     24.7 ms
/sales/pick-lists?page=0                                → 200 items= 1100 total=1100 page=1 page_size=1100 limit=None bytes=  203550     23.6 ms
/sales/pick-lists?page=abc                              → 200 items= 1100 total=1100 page=1 page_size=1100 limit=None bytes=  203550     25.0 ms
/organization/warehouses                                → 200 items=   50 total=300 page=None page_size=None limit=50 bytes=   29185     21.3 ms
/organization/warehouses?limit=1                        → 200 items=    1 total=300 page=None page_size=None limit=1 bytes=     626     12.2 ms
/organization/warehouses?limit=50                       → 200 items=   50 total=300 page=None page_size=None limit=50 bytes=   29185     14.9 ms
/organization/warehouses?limit=100                      → 200 items=  100 total=300 page=None page_size=None limit=100 bytes=   58336     18.5 ms
/organization/warehouses?limit=101                      → 200 items=  101 total=300 page=None page_size=None limit=101 bytes=   58920     17.9 ms
/organization/warehouses?limit=100000                   → 200 items=  300 total=300 page=None page_size=None limit=100000 bytes=  175139     31.6 ms
/organization/warehouses?limit=0                        → 200 items=    0 total=300 page=None page_size=None limit=0 bytes=      45      8.7 ms
    rows = db.execute(query.order_by(Warehouse.code).limit(limit).offset(offset)).scalars().all()
    result: Result[Any] = compile_state_cls.orm_execute_statement(
/organization/warehouses?limit=-1                       → 500 items=    - total=None page=None page_size=None limit=None bytes=     165     21.7 ms code=INTERNAL_ERROR
/organization/warehouses?limit=abc                      → 422 items=    - total=None page=None page_size=None limit=None bytes=     238      7.7 ms code=VALIDATION_ERROR
/organization/warehouses?offset=0                       → 200 items=   50 total=300 page=None page_size=None limit=50 bytes=   29185     13.5 ms
/organization/warehouses?offset=100000                  → 200 items=    0 total=300 page=None page_size=None limit=50 bytes=      51      7.8 ms
    rows = db.execute(query.order_by(Warehouse.code).limit(limit).offset(offset)).scalars().all()
    result: Result[Any] = compile_state_cls.orm_execute_statement(
/organization/warehouses?offset=-1                      → 500 items=    - total=None page=None page_size=None limit=None bytes=     165      9.0 ms code=INTERNAL_ERROR
```

## Lectura

| Registro | Valor |
|---|---|
| `WAREHOUSE_ROUTE` / `SERVICE` | `organization/warehouse_api.py:276-299` `search_warehouses` (consulta en la propia ruta; `st.warehouses_dependencies` por página) |
| `CURRENT_DEFAULT_LIMIT` / `CURRENT_MAX_LIMIT` / `CURRENT_OFFSET` | 50 / **ninguno** / 0, sin validación (`limit: int = 50, offset: int = 0`) |
| `CURRENT_ORDER` | `Warehouse.code` |
| `COMPANY_SCOPE_FILTER` | `Warehouse.company_id.in_(_alcance(ctx))` antes de contar y cortar ✔ |
| `TOTAL_COUNT_AVAILABLE` | sí (`count` sobre la subconsulta filtrada) |
| **`WAREHOUSE_UNBOUNDED = PROVEN`** | `limit=100000` → 200 con las 300 filas (175 KB); `limit=101` → 200 con 101; `limit=0` → 200 vacío; `limit=-1` → SQLite 300 filas / **PostgreSQL 500 `INTERNAL_ERROR`** (`LIMIT must not be negative`); `offset=-1` → **PostgreSQL 500**; `limit=abc` → 422 (FastAPI) |
| `PICKLIST_ROUTE` / `RESPONSE` | `sales/api.py:481-490` `list_pick_lists` → `{items, total: len(items), page: 1, page_size: len(items) or 1}` (sobre con los nombres del canon pero **sin paginar**) |
| `CURRENT_PARAMETERS` | solo `order_id`; `page`/`page_size` se ignoran (`page=0`, `page=abc` → 200 con todo) |
| `CURRENT_ORDER` | `PickList.created_at.desc()` sin desempate |
| `COMPANY_SCOPE_FILTER` | `PickList.company_id == ctx.company_id` ✔ (las 50 de C2 no aparecen: `total` 1 100) |
| **`PICKLIST_UNPAGINATED = PROVEN`** | 1 100 filas, **203 550 bytes**, ≈ 25 ms en proceso, en ambos motores |
| `CURRENT_QA_ROWS` | > 1 100 en la base de QA (hoja de ruta); aquí 1 100 sintéticas |

`REPRODUCED = YES` en los dos objetivos; además el almacén responde 500 (no 422) a valores negativos en PostgreSQL.
