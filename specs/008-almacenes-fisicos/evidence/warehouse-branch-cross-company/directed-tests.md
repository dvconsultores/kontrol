# Pruebas dirigidas — `tests/test_warehouse_branch_scope.py` (B-01…17) y O01-06 adaptada
Mundo propio en los dos motores, sin skip. Tenant T1 tiene las empresas A y B; el tenant T2 tiene la empresa C. Las
sucursales son A1, B1 y C1. Los usuarios son `ua` (solo A), `uab` (A y B) y `sinrol`.
| Id | Qué prueba | SQLite | PG |
|---|---|---|---|
| B-01 | alta en A con A1 → 200, persistida | PASS | PASS |
| B-02 | alta en A con B1 → 404 `BRANCH_NOT_FOUND`, 0 filas | PASS | PASS |
| B-03 | alta en A con C1 (otro tenant) → 404, 0 filas | PASS | PASS |
| B-04 | inexistente → 404 idéntico a la ajena (sin oráculo) | PASS | PASS |
| B-05 | sin sucursal → 200 | PASS | PASS |
| B-06…B-10 | PATCH: a A1 → 200; a B1/C1 → 404 sin cambio ni versión nueva; `null` desliga; sin el campo no toca | PASS | PASS |
| B-11/B-12 | `uab` en B con B1 → 200; `uab` en A con B1 → 404 (manda el contexto) | PASS | PASS |
| B-13/B-14 | 401 y 403 antes; almacén de B desde A → 404 `WAREHOUSE_NOT_FOUND` | PASS | PASS |
| B-15 | contrato AST: ayudante, llamadas, `if` con `model_fields_set` antes del bucle de mutación | PASS | PASS |
| B-16/B-17 | orden: `COMPANY_NOT_FOUND` y `WAREHOUSE_CODE_REQUIRED` antes que `BRANCH_NOT_FOUND` | PASS | PASS |
| O01-06 | sucursal inexistente → 404 `BRANCH_NOT_FOUND` sin llegar a la base, sin fuga, 0 filas | PASS | PASS |

DIRECTED_TOTAL 17 (+1 adaptada) · PASS 17 · FAIL 0 · SKIP 0, en cada motor. Cada prueba pasa sola (17/17 ×2) y el módulo pasa
en orden inverso (17/17 ×2).

Rojo antes de la corrección, con el producto de `HEAD`: fallan B-02, 03, 04, 07, 08, 12, 15 y O01-06, justo las del defecto.

Cercanas: `test_warehouse_integrity` y `test_warehouse_structure` dan 64 passed / 1 skipped en SQLite y 65 en PostgreSQL.
`test_n10_cross_company_writes` está verde en PostgreSQL. ruff está limpio y mypy no añade errores.
