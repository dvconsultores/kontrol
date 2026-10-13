# Campaña de mutaciones · TEST-VOLUMEN-DE-INSTALACION-COMPARTIDO

Guion de Claude fuera del repositorio (`mutar_tv.py`): cada mutante se aplica por sustitución exacta sobre una copia,
se purgan todos los `__pycache__`, se corre `pytest` con `PYTHONDONTWRITEBYTECODE=1` sobre las pruebas que deben
matarlo, y el fichero se restaura **desde la copia** (nunca `git checkout`) comprobando byte a byte. SQLite.
GOOD → PASS · MUTATED → FAIL · RESTORED → PASS.

| Mutante | Fichero | Cambio | Debe matarlo |
|---|---|---|---|
| M-01 | `tests/conftest.py` | la raíz vuelve a ser `tempfile.gettempdir()/kontrol-test-license` (fija) | TV-01, TV-04, TV-23 |
| M-02 | `tests/conftest.py` | el volumen hijo es la propia raíz (dos ámbitos, el mismo directorio) | TV-05, TV-06, TV-02b… |
| M-03 | `tests/conftest.py` | `_fijar_volumen` no limpia la caché de `get_settings` | TV-06, TV-07, TV-10 |
| M-04 | `tests/conftest.py` | al salir no se restaura la variable | TV-07 |
| M-05 | `tests/conftest.py` | al salir no se elimina el hijo | TV-08 |
| M-06 | `tests/conftest.py` | el hijo nace con una `installation_private_key.pem` | TV-02, TV-02b |
| M-07 | `tests/conftest.py` | `pytest_configure` reutiliza la raíz heredada del entorno | TV-01, TV-04 |
| M-08 | `tests/conftest.py` | `pytest_unconfigure` no elimina la raíz | TV-03, TV-09 |
| M-09 | `tests/sondas_volumen/informar.py` | la sonda deja de crear su propia clave | TV-01…TV-04, TV-09 |
| M-10 | `tests/sondas_volumen/informar.py` | el informe de la sonda lleva el PEM | TV-11 |
| M-11 | `app/modules/licensing/service.py` (temporal) | la clave nace 0644 | TV-10, TV-02, TV-04 |
| M-12 | `tests/conftest.py` | `pytest_collection_modifyitems` que reordena | TV-23 |

## Salida

```
GOOD rc=0 fallos=[]
M-01 raíz fija kontrol-test-license: KILLED rc=1
    FAILED tests/test_volumen_de_instalacion.py::test_tv_01_dos_procesos_consecutivos_reciben_raices_distintas_y_ninguna_es_fija
    FAILED tests/test_volumen_de_instalacion.py::test_tv_04_dos_procesos_a_la_vez_escriben_claves_distintas_y_ninguno_pisa_la_del_otro
    FAILED tests/test_volumen_de_instalacion.py::test_tv_23_sin_reordenacion_de_pruebas_ni_ruta_fija_en_el_arnes
    ERROR tests/test_volumen_de_instalacion.py::test_tv_23_sin_reordenacion_de_pruebas_ni_ruta_fija_en_el_arnes
M-02 el hijo es la propia raíz: KILLED rc=1
    FAILED tests/test_volumen_de_instalacion_ambito.py::test_tv_02b_el_volumen_hijo_empieza_vacio
    FAILED tests/test_volumen_de_instalacion_ambito.py::test_tv_05_los_settings_apuntan_al_volumen_del_ambito
    FAILED tests/test_volumen_de_instalacion_ambito.py::test_tv_06_al_cambiar_de_ambito_los_settings_no_conservan_el_anterior
    FAILED tests/test_volumen_de_instalacion_ambito.py::test_tv_07_al_salir_la_variable_y_los_settings_vuelven_a_como_estaban
    FAILED tests/test_volumen_de_instalacion_ambito.py::test_tv_08_al_salir_el_volumen_desaparece_tambien_si_dentro_hubo_una_excepcion
    FAILED tests/test_volumen_de_instalacion.py::test_tv_01_dos_procesos_consecutivos_reciben_raices_distintas_y_ninguna_es_fija
M-03 sin cache_clear al fijar: KILLED rc=1
    FAILED tests/test_volumen_de_instalacion_ambito.py::test_tv_06_al_cambiar_de_ambito_los_settings_no_conservan_el_anterior
    FAILED tests/test_volumen_de_instalacion_ambito.py::test_tv_07_al_salir_la_variable_y_los_settings_vuelven_a_como_estaban
    FAILED tests/test_volumen_de_instalacion_ambito.py::test_tv_10_la_clave_sintetica_nace_dentro_del_volumen_con_0600_y_muere_con_el
M-04 sin restaurar la variable al salir: KILLED rc=1
    FAILED tests/test_volumen_de_instalacion_ambito.py::test_tv_06_al_cambiar_de_ambito_los_settings_no_conservan_el_anterior
    FAILED tests/test_volumen_de_instalacion_ambito.py::test_tv_07_al_salir_la_variable_y_los_settings_vuelven_a_como_estaban
    FAILED tests/test_volumen_de_instalacion_ambito.py::test_tv_08_al_salir_el_volumen_desaparece_tambien_si_dentro_hubo_una_excepcion
M-05 sin eliminar el hijo: KILLED rc=1
    FAILED tests/test_volumen_de_instalacion_ambito.py::test_tv_08_al_salir_el_volumen_desaparece_tambien_si_dentro_hubo_una_excepcion
    FAILED tests/test_volumen_de_instalacion_ambito.py::test_tv_10_la_clave_sintetica_nace_dentro_del_volumen_con_0600_y_muere_con_el
M-06 clave prepoblada en el hijo: KILLED rc=1
    FAILED tests/test_volumen_de_instalacion_ambito.py::test_tv_02b_el_volumen_hijo_empieza_vacio
    FAILED tests/test_volumen_de_instalacion_ambito.py::test_tv_10_la_clave_sintetica_nace_dentro_del_volumen_con_0600_y_muere_con_el
    FAILED tests/test_volumen_de_instalacion.py::test_tv_02_el_volumen_de_un_modulo_empieza_vacio_y_la_clave_cae_dentro
    FAILED tests/test_volumen_de_instalacion.py::test_tv_03_la_sesion_b_no_ve_la_clave_de_la_sesion_a_y_a_no_deja_rastro
    FAILED tests/test_volumen_de_instalacion.py::test_tv_04_dos_procesos_a_la_vez_escriben_claves_distintas_y_ninguno_pisa_la_del_otro
    FAILED tests/test_volumen_de_instalacion.py::test_tv_12_el_resultado_no_depende_del_orden_de_los_modulos
M-07 el hijo reutiliza la raíz heredada: KILLED rc=1
    FAILED tests/test_volumen_de_instalacion.py::test_tv_01_dos_procesos_consecutivos_reciben_raices_distintas_y_ninguna_es_fija
    FAILED tests/test_volumen_de_instalacion.py::test_tv_02_el_volumen_de_un_modulo_empieza_vacio_y_la_clave_cae_dentro
    FAILED tests/test_volumen_de_instalacion.py::test_tv_03_la_sesion_b_no_ve_la_clave_de_la_sesion_a_y_a_no_deja_rastro
    FAILED tests/test_volumen_de_instalacion.py::test_tv_04_dos_procesos_a_la_vez_escriben_claves_distintas_y_ninguno_pisa_la_del_otro
    FAILED tests/test_volumen_de_instalacion.py::test_tv_09_cuando_la_prueba_falla_el_volumen_y_la_raiz_desaparecen_igual
    FAILED tests/test_volumen_de_instalacion.py::test_tv_11_las_sondas_no_cuentan_mas_que_huellas
M-08 la raíz sobrevive a la sesión: KILLED rc=1
    FAILED tests/test_volumen_de_instalacion.py::test_tv_03_la_sesion_b_no_ve_la_clave_de_la_sesion_a_y_a_no_deja_rastro
    FAILED tests/test_volumen_de_instalacion.py::test_tv_09_cuando_la_prueba_falla_el_volumen_y_la_raiz_desaparecen_igual
M-09 la sonda ya no crea su clave: KILLED rc=1
    FAILED tests/test_volumen_de_instalacion.py::test_tv_01_dos_procesos_consecutivos_reciben_raices_distintas_y_ninguna_es_fija
    FAILED tests/test_volumen_de_instalacion.py::test_tv_02_el_volumen_de_un_modulo_empieza_vacio_y_la_clave_cae_dentro
    FAILED tests/test_volumen_de_instalacion.py::test_tv_03_la_sesion_b_no_ve_la_clave_de_la_sesion_a_y_a_no_deja_rastro
    FAILED tests/test_volumen_de_instalacion.py::test_tv_04_dos_procesos_a_la_vez_escriben_claves_distintas_y_ninguno_pisa_la_del_otro
    FAILED tests/test_volumen_de_instalacion.py::test_tv_09_cuando_la_prueba_falla_el_volumen_y_la_raiz_desaparecen_igual
    FAILED tests/test_volumen_de_instalacion.py::test_tv_11_las_sondas_no_cuentan_mas_que_huellas
M-10 el informe lleva el PEM: KILLED rc=1
    FAILED tests/test_volumen_de_instalacion.py::test_tv_09_cuando_la_prueba_falla_el_volumen_y_la_raiz_desaparecen_igual
    FAILED tests/test_volumen_de_instalacion.py::test_tv_11_las_sondas_no_cuentan_mas_que_huellas
M-11 clave 0644 (producto, temporal): KILLED rc=1
    FAILED tests/test_volumen_de_instalacion_ambito.py::test_tv_10_la_clave_sintetica_nace_dentro_del_volumen_con_0600_y_muere_con_el
    FAILED tests/test_volumen_de_instalacion.py::test_tv_02_el_volumen_de_un_modulo_empieza_vacio_y_la_clave_cae_dentro
    FAILED tests/test_volumen_de_instalacion.py::test_tv_04_dos_procesos_a_la_vez_escriben_claves_distintas_y_ninguno_pisa_la_del_otro
M-12 reordenación en el conftest: KILLED rc=1
    FAILED tests/test_volumen_de_instalacion.py::test_tv_23_sin_reordenacion_de_pruebas_ni_ruta_fija_en_el_arnes
RESTORED rc=0 fallos=[]

RESUMEN: 12 / 12 muertas
```

**12/12 muertas**; ninguna equivalente; ninguna sustituida. Tras la campaña, `git status` solo muestra los ficheros del ciclo (producto restaurado: `git diff app/` vacío). Los mutantes M-05 y M-08 dejaron, por diseño, 11 raíces `kontrol-test-license-*` con claves sintéticas en el temporal: se eliminaron a mano al terminar la campaña (no son residuo del arnés: con el arnés íntegro, RESTORED deja 0).
