# Campaña de mutaciones · TEST-PG-UN-SCHEMA-POR-PRUEBA

Guion de Claude fuera del repositorio (`mutar_pgs.py`): sustitución exacta sobre copia, purga de `__pycache__`,
`PYTHONDONTWRITEBYTECODE=1`, PostgreSQL salvo M-08 (SQLite), restauración desde la copia comprobada byte a byte.
GOOD → PASS · MUTATED → FAIL · RESTORED → PASS, en los dos motores.

| Mutante | Fichero | Cambio | Debe matarlo |
|---|---|---|---|
| M-01 | `tests/conftest.py` | `sesion_de_prueba` vuelve a crear motor + schema por prueba | PGS-09, 11, 10, 07, 26 |
| M-02 | `tests/conftest.py` | la transacción externa se confirma en vez de deshacerse | PGS-03…06b |
| M-03 | `tests/conftest.py` | `join_transaction_mode="control_fully"`: los `commit` escapan | PGS-03…06b |
| M-04 | `tests/conftest.py` | una sola sesión para todo el módulo (`scope="module"`) | PGS-03…06b |
| M-05 | `tests/conftest.py` | sesión ligada al motor, no a la conexión | PGS-03…06b |
| M-06 | `tests/conftest.py` | el schema del módulo se saca del ámbito PGLIFE (no se suelta) | PGS-11, 10, 07, 26 |
| M-07 | `tests/conftest.py` | el schema se comparte entre módulos (`scope="session"`) | PGS-07, 28 |
| M-08 | `tests/conftest.py` | SQLite reutiliza una base entre pruebas | PGS-09 y sondas (SQLite) |
| M-09 | `tests/conftest.py` | la conexión de la prueba no se devuelve (`conexion.close()` quitado) | **EQUIVALENTE**: al cerrar la fixture el objeto se recolecta y la conexión vuelve al pool; `test_approvals` (40) pasa. Sustituido por M-09b |
| M-09b | `tests/pg_harness.py` (temporal) | PGLIFE no suelta el ámbito (`cerrar_ambito` sin `_liberar`) | PGS-11, 10, 07, 26 |
| M-10 | `tests/conftest.py` | `pytest_collection_modifyitems` que reordena | PGS-10, 23, 28 |
| M-11 | `tests/test_sales.py` | `pytestmark = pytest.mark.skip` | PGS-27 |
| M-12 | `app/core/database.py` (temporal) | el producto asume `create_savepoint` / `join_transaction_mode` | PGS-28 |

## Salida

```
GOOD (PG) 0 []
GOOD (SQLite) 0 []
M-01 schema por prueba otra vez (PG): KILLED rc=1
    FAILED tests/test_pg_sesion_aislada.py::test_pgs_09_postgresql_un_schema_por_modulo_y_sqlite_una_base_por_prueba
    FAILED tests/test_pg_sesion_aislada.py::test_pgs_11_una_sonda_entera_no_deja_schema_y_cada_prueba_parte_de_cero
    FAILED tests/test_pg_sesion_aislada.py::test_pgs_10_cuando_una_prueba_falla_el_schema_del_modulo_se_suelta_igual
    FAILED tests/test_pg_sesion_aislada.py::test_pgs_07_dos_modulos_del_mismo_proceso_no_comparten_schema
    FAILED tests/test_pg_sesion_aislada.py::test_pgs_26_dos_procesos_a_la_vez_trabajan_en_schemas_distintos
M-02 la transacción externa se confirma: KILLED rc=1
    FAILED tests/test_pg_sesion_aislada.py::test_pgs_03_b_no_ve_las_filas_ni_la_actualizacion_de_a_y_borra_lo_suyo
    FAILED tests/test_pg_sesion_aislada.py::test_pgs_04_el_commit_del_producto_queda_dentro_del_ambito
    FAILED tests/test_pg_sesion_aislada.py::test_pgs_05_c_parte_de_cero_tras_el_borrado_y_tras_el_producto
    FAILED tests/test_pg_sesion_aislada.py::test_pgs_06_una_segunda_sesion_del_ambito_ve_lo_confirmado_en_el_ambito
    FAILED tests/test_pg_sesion_aislada.py::test_pgs_06b_y_la_prueba_siguiente_tampoco_ve_lo_de_la_segunda_sesion
M-03 los commit escapan (control_fully): KILLED rc=1
    FAILED tests/test_pg_sesion_aislada.py::test_pgs_03_b_no_ve_las_filas_ni_la_actualizacion_de_a_y_borra_lo_suyo
    FAILED tests/test_pg_sesion_aislada.py::test_pgs_04_el_commit_del_producto_queda_dentro_del_ambito
    FAILED tests/test_pg_sesion_aislada.py::test_pgs_05_c_parte_de_cero_tras_el_borrado_y_tras_el_producto
    FAILED tests/test_pg_sesion_aislada.py::test_pgs_06_una_segunda_sesion_del_ambito_ve_lo_confirmado_en_el_ambito
    FAILED tests/test_pg_sesion_aislada.py::test_pgs_06b_y_la_prueba_siguiente_tampoco_ve_lo_de_la_segunda_sesion
M-04 una sola sesión para todo el módulo: KILLED rc=1
    FAILED tests/test_pg_sesion_aislada.py::test_pgs_03_b_no_ve_las_filas_ni_la_actualizacion_de_a_y_borra_lo_suyo
    FAILED tests/test_pg_sesion_aislada.py::test_pgs_04_el_commit_del_producto_queda_dentro_del_ambito
    FAILED tests/test_pg_sesion_aislada.py::test_pgs_05_c_parte_de_cero_tras_el_borrado_y_tras_el_producto
    FAILED tests/test_pg_sesion_aislada.py::test_pgs_06_una_segunda_sesion_del_ambito_ve_lo_confirmado_en_el_ambito
    FAILED tests/test_pg_sesion_aislada.py::test_pgs_06b_y_la_prueba_siguiente_tampoco_ve_lo_de_la_segunda_sesion
M-05 sesión ligada al motor, no a la conexión: KILLED rc=1
    FAILED tests/test_pg_sesion_aislada.py::test_pgs_03_b_no_ve_las_filas_ni_la_actualizacion_de_a_y_borra_lo_suyo
    FAILED tests/test_pg_sesion_aislada.py::test_pgs_04_el_commit_del_producto_queda_dentro_del_ambito
    FAILED tests/test_pg_sesion_aislada.py::test_pgs_05_c_parte_de_cero_tras_el_borrado_y_tras_el_producto
    FAILED tests/test_pg_sesion_aislada.py::test_pgs_06_una_segunda_sesion_del_ambito_ve_lo_confirmado_en_el_ambito
    FAILED tests/test_pg_sesion_aislada.py::test_pgs_06b_y_la_prueba_siguiente_tampoco_ve_lo_de_la_segunda_sesion
M-06 el schema del módulo no se suelta: KILLED rc=1
    FAILED tests/test_pg_sesion_aislada.py::test_pgs_11_una_sonda_entera_no_deja_schema_y_cada_prueba_parte_de_cero
    FAILED tests/test_pg_sesion_aislada.py::test_pgs_10_cuando_una_prueba_falla_el_schema_del_modulo_se_suelta_igual
    FAILED tests/test_pg_sesion_aislada.py::test_pgs_07_dos_modulos_del_mismo_proceso_no_comparten_schema
    FAILED tests/test_pg_sesion_aislada.py::test_pgs_26_dos_procesos_a_la_vez_trabajan_en_schemas_distintos
M-07 el schema se comparte entre módulos (sesión): KILLED rc=1
    FAILED tests/test_pg_sesion_aislada.py::test_pgs_07_dos_modulos_del_mismo_proceso_no_comparten_schema
    FAILED tests/test_pg_sesion_aislada.py::test_pgs_28_nada_de_esto_se_sostiene_reordenando_pruebas_ni_tocando_el_producto
M-08 SQLite reutiliza una base entre pruebas: KILLED rc=1
    FAILED tests/test_pg_sesion_aislada.py::test_pgs_09_postgresql_un_schema_por_modulo_y_sqlite_una_base_por_prueba
    FAILED tests/test_pg_sesion_aislada.py::test_pgs_11_una_sonda_entera_no_deja_schema_y_cada_prueba_parte_de_cero
    FAILED tests/test_pg_sesion_aislada.py::test_pgs_10_cuando_una_prueba_falla_el_schema_del_modulo_se_suelta_igual
    FAILED tests/test_pg_sesion_aislada.py::test_pgs_07_dos_modulos_del_mismo_proceso_no_comparten_schema
    FAILED tests/test_pg_sesion_aislada.py::test_pgs_26_dos_procesos_a_la_vez_trabajan_en_schemas_distintos
M-09 la conexión de la prueba no se devuelve: SURVIVED rc=0
M-10 reordenación en el conftest: KILLED rc=1
    FAILED tests/test_pg_sesion_aislada.py::test_pgs_10_cuando_una_prueba_falla_el_schema_del_modulo_se_suelta_igual
    FAILED tests/test_pg_sesion_aislada.py::test_pgs_23_el_orden_inverso_y_una_prueba_sola_dan_lo_mismo
    FAILED tests/test_pg_sesion_aislada.py::test_pgs_28_nada_de_esto_se_sostiene_reordenando_pruebas_ni_tocando_el_producto
M-11 una suite se omite: KILLED rc=1
    FAILED tests/test_pg_sesion_aislada.py::test_pgs_27_las_doce_suites_usan_la_sesion_del_arnes_y_ninguna_crea_un_schema_por_prueba
M-12 el producto asume el modo de transacción del arnés: KILLED rc=1
    FAILED tests/test_pg_sesion_aislada.py::test_pgs_28_nada_de_esto_se_sostiene_reordenando_pruebas_ni_tocando_el_producto
RESTORED (PG) 0 []
RESTORED (SQLite) 0 []
RESUMEN: 11 / 12 muertas
M-09 declarado EQUIVALENTE: sin conexion.close() la conexión vuelve al pool al recolectarse el objeto al cerrar la fixture; test_approvals (40 pruebas) pasa.
GOOD (PG) 0 []
GOOD (SQLite) 0 []
M-09b PGLIFE no suelta el ámbito (cerrar_ambito sin _liberar): KILLED rc=1
    FAILED tests/test_pg_sesion_aislada.py::test_pgs_11_una_sonda_entera_no_deja_schema_y_cada_prueba_parte_de_cero
    FAILED tests/test_pg_sesion_aislada.py::test_pgs_10_cuando_una_prueba_falla_el_schema_del_modulo_se_suelta_igual
    FAILED tests/test_pg_sesion_aislada.py::test_pgs_07_dos_modulos_del_mismo_proceso_no_comparten_schema
    FAILED tests/test_pg_sesion_aislada.py::test_pgs_26_dos_procesos_a_la_vez_trabajan_en_schemas_distintos
RESTORED (PG) 0 []
RESTORED (SQLite) 0 []
RESUMEN: 1 / 1 muertas
```

**12/12 muertas** (M-01…M-08, M-09b, M-10…M-12); M-09 equivalente, declarado y sustituido. Tras la campaña `git status` solo muestra los ficheros del ciclo; `pg_harness.py` y `app/` sin diff. Los mutantes que no sueltan schemas (M-01, M-06, M-07, M-09b) dejaron 18 schemas `t_*` con la marca del arnés (333 MB): se purgaron con la herramienta oficial `qa/pg-test-residuos.py --purgar` (conexiones 0; schemas `t_` después: 0).
