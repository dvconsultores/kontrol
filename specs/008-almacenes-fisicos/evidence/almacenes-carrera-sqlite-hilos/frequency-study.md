# Estudio de frecuencia (acotado, como pide el encargo)

Todas las corridas son procesos nuevos de pytest, en serie, sin nada más corriendo contra el repositorio. Series crudas en
`frequency-series-before.txt` (antes de la corrección) y `frequency-series-after.txt` (después).

| Serie | Qué | Antes de la corrección | Después |
|---|---|---|---|
| A | prueba sola ×20, sin sonda | **8/20 FAIL** (corridas 2, 5, 6, 10, 11, 15, 17, 19): `[200]` ×6, `[]` ×1, `[409]` ×1 | **20/20 PASS** |
| A' | prueba sola ×20, con la sonda `acs_sonda` (eventos de motor) | **4/20 FAIL** (corridas 1, 7, 13, 20); topología en `connection-topology.md` | — |
| B | módulo `tests/test_warehouse_structure.py` ×10 | **4/10 FAIL** (corridas 3, 4, 7, 10), siempre la misma prueba | **10/10 PASS** (43 pruebas cada una) |
| C | suite SQLite completa ×2 | no repetida antes: el fallo ya estaba reproducido en A y B, y la suite completa ya lo había mostrado dos veces en ciclos anteriores (43/1582 el 2026-10-13 en `TEST-PG-UN-SCHEMA-POR-PRUEBA`, con esta prueba entre los fallos; 42/1609 en `LISTADOS-SIN-TOPE`, sin ella) | ×2 tras la corrección, como certificación |
| PG | prueba sola sobre PostgreSQL | 5/5 PASS (registro histórico de la fila del roadmap) | **20/20 PASS**; suites de almacenes + ACS en PostgreSQL 116/116; suite completa ×1 en `full-suites.md` |

Lectura: la frecuencia varía con la carga de la máquina y con la sonda (los eventos de motor alteran el entrelazado),
pero el fallo está presente en todas las series sin corrección y nunca sobre PostgreSQL. El registro histórico de la fila
del roadmap (9/20 en `42cd793`, 17/25 en un árbol posterior) es coherente con A. No hay «reintento hasta verde»: las
series de después se corren una vez cada una, con el número de corridas fijado de antemano, y se informan enteras.
