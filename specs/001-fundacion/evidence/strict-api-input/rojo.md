# Rojo atribuible por tarea (2026-10-28)

Primero se aplicaron solo las pruebas. Los fallos son del hueco que se corrige, nunca del entorno.

| Tarea | Prueba | Rojo | Controles verdes en rojo | Verde con el producto |
|---|---|---|---|---|
| C05-T01 / T02 | `test_strict_query_contract.py` | 13 fallan: Q-01, 03..07, 09, 11, N-01, N-02 y GUARD-Q-02 por aserción; Q-13 y GUARD-Q-01 por el import perezoso del módulo que falta | Q-02, Q-08, Q-10, Q-12 y GUARD-Q-03 | 18/18 |
| C05-T03 / T04 | `test_naive_datetime_input.py` | 8 fallan: D-01, 02, 03, 06 y 07 por aserción; GUARD-D-01 con los 16 campos `datetime` desnudos; D-09 y D-10 por el import perezoso | D-04, D-05, D-08, D-11 y D-12 | 13/13 |
| C05-T05 | `test_inventory_balances_search.py` | 8 fallan. E-07 falla porque `q` aún no está declarado (422 del contrato ya activo) y porque falta `product_name` | — | 8/8 |
| C05-T06 | `ExistenciasPage.test.tsx` | 6 de 7 fallan con la página antigua | EXS-F-05 | 8/8 (tras separar F-06) |
| C05-T09 / T11 | `query-contract.test.ts` | QC-01 señala `ProductoNuevoPage` (Rubro: `q` y `page_size` no declarados), un hallazgo real | QC-02..10 | 10/10 |
| C05-T11 | `test_taxonomy_search.py` | 6 de 7 fallan: la ruta no existía (404) | T-06 | 7/7 |

**Fragilidad anotada (no es verde falso):** GUARD-Q-02 cae en rojo con `AttributeError` (`list.get`) en vez de una violación legible, porque aceptar el desconocido devuelve el cuerpo en lista. Deuda GUARD-Q02-CUERPO-LISTA (LOW).
