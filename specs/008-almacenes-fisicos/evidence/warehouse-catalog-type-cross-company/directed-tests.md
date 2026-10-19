# Pruebas dirigidas — `tests/test_warehouse_catalog_scope.py` (28) y O01-07/08/09
Mundo propio en los dos motores, sin skip: T1 tiene las empresas A y B, T2 tiene la C; hay tipos de ubicación y de zona en
cada empresa; los usuarios son `ua`, `uab` y `sinrol`.
| Grupo | Pruebas | Resultado |
|---|---|---|
| ubicación: propio, ajeno, otro tenant, inexistente idéntico | C01–C04 | PASS ×2 motores |
| alta masiva: propio, ajeno, ajeno en vista previa | C05, C06, C06b | PASS |
| PATCH de ubicación: propio, `null`, ajeno sin cambio ni versión nueva | C07, C08 | PASS |
| zona: propio, ajeno, otro tenant, inexistente idéntico | C09–C12 | PASS |
| PATCH de zona: propio, ajeno sin cambio | C13, C14 | PASS |
| `null` y campo omitido | C15, C16 | PASS |
| precedencia: 401, 403, almacén, ubicación y zona ajenos, VERSION_CONFLICT, LOCATION_CODE_REQUIRED, LOCATION_PATTERN_INVALID, STRUCTURE_LEVEL_DISABLED | C17–C20, C22, C22b, C23 | PASS |
| contexto: `uab` en B acepta tipos de B; en A los rechaza | C24, C25 | PASS |
| contrato AST: las cinco llamadas, y la validación antes de mutar o de la vista previa | C28, C29 | PASS |

DIRECTED_TOTAL 28 · PASS 28 · FAIL 0 · SKIP 0, en cada motor. Cada prueba pasa sola (28/28 ×2) y el módulo pasa en orden
inverso (28/28 ×2).

**Rojo contra el producto de `HEAD`.** Se restauró por copia explícita con `cmp`, sin `git stash`. Fallan 13 de 28: C02, 03,
04, 06, 06b, 08, 10, 11, 12, 14, 25, 28 y 29. Son justo las que capturan la fuga.

**OBS-01.** O01-07, O01-08 y O01-09 neutralizan `_exige_tipo_propio` con `monkeypatch`, solo dentro de la prueba, para seguir
alcanzando la clave foránea real. Sus aserciones del 500 no cambian: 14/14.

**Cercanas.** Integridad, sucursales y estructura dan 64 passed / 1 skipped en SQLite. En PostgreSQL, con N10, dan 76 passed.
ruff está limpio y mypy no añade errores.
