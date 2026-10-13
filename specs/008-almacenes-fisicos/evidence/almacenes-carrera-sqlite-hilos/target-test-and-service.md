# La prueba objetivo y el servicio (HEAD ffdbaf6)

## `tests/test_warehouse_structure.py::test_concurrencia_de_codigo_resuelta_por_constraint`

| Registro | Valor |
|---|---|
| Qué ejercita | **ubicaciones**, no almacenes: dos hilos hacen `POST /organization/locations` con el mismo `code` «RACE-1» en el mismo almacén |
| `THREAD_COUNT` / `BARRIER` | 2 · `threading.Barrier(2)` antes del `POST` |
| `SESSION_FACTORY` / `SESSION_PER_THREAD` | el `get_db` sobrescrito del mundo del módulo (`factory()` por petición → una `Session` por hilo) |
| `ENGINE` / `POOL_CLASS` / `CHECK_SAME_THREAD` / `SQLITE_URL` | `make_engine()` → `sqlite+pysqlite:///:memory:` · **`StaticPool`** · `check_same_thread=False` |
| Cliente | `TestClient(app)` (relanza las excepciones del servidor: un 500 revienta el hilo) |
| `ASSERTIONS` | `sorted(results) == [200, 409]` y `GET …/locations?q=RACE-1` → `total == 1` |
| `EXPECTED_SUCCESS_COUNT` / `CONFLICT_COUNT` / `HTTP` / `DOMAIN_CODE` / `FINAL_ROW_COUNT` | 1 · 1 · 200 + 409 · `LOCATION_CODE_DUPLICATE` · 1 |

## Servicio (`app/modules/organization/warehouse_api.py::create_location_full`, 779-812)

| Registro | Valor |
|---|---|
| `PRECHECK` | ninguno por código: valida almacén y cadena, genera código si falta; **la garantía es la base** (P25) |
| `PG_LOCK` | ninguno (no hay `pg_advisory_xact_lock` aquí) |
| `SAVEPOINT` / `FLUSH_SITE` / `COMMIT_OWNER` | sin savepoint · `db.add(location)` → **`db.commit()`** dentro de `try` → `except IntegrityError: db.rollback(); raise _integrity(…)` |
| `UNIQUE_TRANSLATOR` | `_integrity(exc, "LOCATION_CODE_DUPLICATE", …)` → `ConflictError` 409 **para cualquier `IntegrityError`** (no usa `es_violacion_unica`; `del exc`) |
| `SQLITE_PATH` / `PG_PATH` | el mismo código; en SQLite la violación llega como `sqlite3.IntegrityError` → 409; en PostgreSQL como `psycopg2.IntegrityError` → 409 |

## Restricción

`CONSTRAINT_NAME = uq_warehouse_locations_wh_code` · `COLUMNS = (warehouse_id, code)` · `COMPANY_SCOPED` vía `warehouse_id` ·
`PARTIAL` no · `MIGRATION = 0017_warehouse_structure` · existe igual en modelos y migración (P26); SQLite la impone como
`UNIQUE constraint failed: warehouse_locations.warehouse_id, warehouse_locations.code`.

## `es_violacion_unica`

Solo reconoce `pgcode 23505` + `diag.constraint_name` (PostgreSQL); con SQLite devuelve `False`. Este servicio no la usa:
traduce cualquier `IntegrityError` del `commit` a 409 (observación para la dueña 008, fuera de este ciclo: no es la causa).
