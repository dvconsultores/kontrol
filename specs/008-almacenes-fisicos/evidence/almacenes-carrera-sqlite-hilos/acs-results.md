# ACS-01…12 · resultados dirigidos

| Id | Qué | SQLite | PostgreSQL |
|---|---|---|---|
| ACS-01 | una conexión DBAPI por hilo concurrente | PASS | PASS |
| ACS-02 | lo confirmado por A lo lee B por otra conexión | PASS | PASS |
| ACS-03 | lo no confirmado no se ve, ni tras el rollback | PASS | PASS |
| ACS-04 | dos INSERT simultáneos de la misma clave → un éxito, un `IntegrityError`, una fila | PASS | PASS |
| ACS-05 | bloqueo de SQLite = `OperationalError`, no `IntegrityError`; `es_violacion_unica` lo rechaza; tras deshacer, el duplicado real sí es `IntegrityError` | PASS | PASS (biblioteca estándar; no depende del motor de la corrida) |
| ACS-06 | directorio `kontrol-test-sqlite-acs-limpieza-*` con `base.db` dentro del contexto, ninguno después, pool vacío (PG: ningún directorio) | PASS | PASS |
| ACS-07 | limpieza aunque el contexto falle | PASS | PASS |
| ACS-08 | contrato estático (primitiva sin `timeout/StaticPool/:memory:/sleep/PRAGMA/isolation_level/poolclass`; `make_engine()` intacto; prueba objetivo intacta; barrera de ACS-04 presente) | PASS | PASS |
| ACS-09 | prueba objetivo sola ×20 | 20/20 | — |
| ACS-10 | módulo ×10 | 10/10 | — |
| ACS-11 | prueba objetivo sola ×20 | — | 20/20 |
| ACS-12 | suites de almacenes (`test_warehouse_list_cost`, `test_warehouse_migration_0018`, `test_warehouse_structure`, `test_warehouse_view_pure`) + ACS | — | 116 passed in 42,0 s |

Orden base: `.venv/bin/python -m pytest <objetivo> -q -o addopts= -p no:cacheprovider` (con `-o addopts=` para que el
`-q` de `pyproject.toml` no se sume al de la orden y se vea la línea de resumen). Series crudas en
`frequency-series-after.txt`. Tras cada serie: 0 directorios `kontrol-test-sqlite-*`.

Incidencia del arnés de medición, no del producto ni de las pruebas: una primera versión de la serie leía el veredicto de
la línea de resumen de pytest, que con `-q -q` no existe, y etiquetaba FAIL corridas que habían pasado (`.  [100%]`); se
detuvo, se corrigió la clasificación y se repitió entera. El módulo interrumpido a la fuerza dejó un directorio
`kontrol-test-sqlite-warehouse-structure-*` (la limpieza del `finally` no corre si matan el proceso), eliminado a mano; una
corrida normal deja 0. Es el mismo límite que tiene el volumen de instalación por proceso.

Gates estáticos: `ruff check` limpio en los tres ficheros; `mypy` del producto 154 errores en 18 ficheros (línea base,
producto sin tocar; `git diff --stat -- app/ alembic/` vacío); los tres ficheros de prueba no aportan errores de `mypy`
(`--explicit-package-bases`: los 154 son todos de `app/`).
