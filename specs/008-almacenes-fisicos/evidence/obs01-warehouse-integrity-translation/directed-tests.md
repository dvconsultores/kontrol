# Pruebas dirigidas — `tests/test_warehouse_integrity.py` (O01-01…14)
| Id | Qué prueba | SQLite | PostgreSQL |
|---|---|---|---|
| 01 | almacén repetido → 409 `WAREHOUSE_CODE_DUPLICATE`, mensaje exacto, sin fuga, 1 fila, original intacto | PASS | PASS |
| 02 | ubicación repetida → 409 `LOCATION_CODE_DUPLICATE` | PASS | PASS |
| 03 | zona repetida → 409 `ZONE_CODE_DUPLICATE` | PASS | PASS |
| 04 | tipos de zona y de ubicación repetidos → 409 `ZONE_TYPE_/LOCATION_TYPE_CODE_DUPLICATE` | PASS | PASS |
| 05 | alta masiva que repite el código en la tanda → 409, 0 filas | PASS | PASS |
| 06 | almacén con `branch_id` inexistente → 500 `INTERNAL_ERROR` genérico, sin fuga, 0 filas | PASS | PASS |
| 07 | ubicación con `location_type_id` inexistente → 500, 0 filas | PASS | PASS |
| 08 | zona con `zone_type_id` inexistente → 500, 0 filas | PASS | PASS |
| 09 | tras 409 y 500 la siguiente alta prospera; filas previas intactas | PASS | PASS |
| 10 | clasificador con errores reales del motor: única ✔, otra restricción ✗, foránea ✗, NOT NULL ✗, clave primaria ✗; control: el helper antiguo solo reconoce PostgreSQL | PASS | PASS |
| 11 | `restriccion_unica`: forma; `LookupError`; `TypeError` | PASS | PASS |
| 12 | 401 sin sesión y 404 de almacén inexistente antes que cualquier 409 | PASS | PASS |
| 13 | usuario sin rol → 403 (ni 409 ni 500) | PASS | PASS |
| 14 | contrato AST: sin `_integrity`, 5 manejadores `rollback → if not es_violacion_unica_de: raise → raise ConflictError`, sin `except Exception` | PASS | PASS |
Módulo 14/14 en cada motor · cada prueba sola 14/14 en cada motor · orden inverso 14/14 (SQLite, verificado con `-vv`) y
14/14 (PostgreSQL) · con `test_warehouse_structure.py` 47 passed / 1 skipped (SQLite) y 48 passed (PostgreSQL) · la carrera
`test_concurrencia_de_codigo_resuelta_por_constraint` 5/5 en SQLite con el producto nuevo: el perdedor recibe el 409 por la
rama SQLite (sin ella, M01, la carrera falla). ruff limpio; mypy sin errores nuevos (15 preexistentes, idénticos a `HEAD`).
En SQLite el módulo activa `PRAGMA foreign_keys=ON` solo en su motor, para obtener un error de clave foránea **real**; sin
dobles de `IntegrityError`.
