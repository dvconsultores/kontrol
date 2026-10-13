# Pruebas hostiles (W20/W29) · `tests/test_listados_sin_tope.py` · 1 100 listas y 7 almacenes en D1, 50 listas y 1 almacén en C2

| LT | Qué comprueba | Resultado |
|---|---|---|
| LT-01 | `limit=100` aceptado; defecto `limit` 50, `offset` 0; sobre exacto `{total, limit, offset, items}` | PASS |
| LT-02/03 | `limit=101`, `100000`, `0`, `-1`, `abc`, `offset=-1`, `offset=x` → **422 `VALIDATION_ERROR`** (antes: 200 con todo, o 500 en PostgreSQL) | PASS (×7) |
| LT-03b | `offset` más allá del final: página vacía con el mismo `total`; páginas de 3 sin solape ni omisión (3, 3, 1) | PASS |
| LT-04/05 | sobre exacto `{items, total, page, page_size}`; primera página 20 de 1 100; campos de cada item | PASS |
| LT-06/07 | 12 páginas de 100 sin duplicados ni omisiones; última parcial; 55 páginas de 20 + la 56 vacía; `page_size=99` | PASS |
| LT-08 | `page=999` → `{items: [], total: 1100, page: 999, page_size: 100}` | PASS |
| LT-09 | `page_size=100` aceptado | PASS |
| LT-10 | `page_size=101`, `0`, `-5`, `abc`, `page=0`, `-1`, `abc` → 422 | PASS (×7) |
| LT-11 | orden = `created_at desc, id asc` calculado fuera de SQL; repetible; cinco grupos de diez con el mismo instante ordenados por `id` | PASS |
| LT-12/13 | D1: 1 100 / C2: 50; códigos de cada empresa; almacenes de C2: 1 | PASS |
| LT-14 | cabecera `X-Kontrol-Company` con la empresa de otro tenant → 404 `COMPANY_NOT_FOUND`, sin `items` ni `total` | PASS |
| LT-15 | `order_id` filtra: `total` 1 / 1 item; `order_id` inexistente → página vacía `total` 0 | PASS |
| LT-23/24 | > 1 000 listas: una página de 20 y cuerpo < 6 KB (la colección entera pesaba 203 550 B); 100 ítems < 25 KB | PASS |
| LT-SQL | la sentencia de `pick_lists` lleva `LIMIT`/`OFFSET` y hay `count`; la fuente de `list_pick_lists` usa `.offset(`/`.limit(`/`func.count()` y no rebana en Python | PASS |
| LT-16 | `POST /sales/pick-lists` duplicado → 409 `PICKLIST_DUPLICATE` (suite `test_picklist_duplicada`, 10 pruebas) | PASS |

Dirigidas: SQLite `test_listados_sin_tope + test_warehouse_list_cost + test_warehouse_structure + test_picklist_duplicada`
→ 88 ejecutadas, 0 fallos, 4 omitidas preexistentes (solo PostgreSQL). PostgreSQL con además `test_spec031_picking`,
`test_spec032_picking_execution`, `test_openapi_security` → 165 ejecutadas, **0 fallos, 0 omitidas**.
