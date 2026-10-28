# Mutaciones · campaña 05 (2026-10-28)

Runner de Claude (`mutar05.py`, fuera del repo): un mutante por SEARCH único, su orden propia, purga de `__pycache__` (PYTHONDONTWRITEBYTECODE=1) y restauración verificada por sha256. D07 corre contra PostgreSQL: las pruebas de tasas CSV se omiten en SQLite.

| ID | Mutación | Estado | Prueba que lo mata | Restaurado |
|---|---|---|---|---|
| Q01 | verificador desactivado | **KILLED** | FAILED tests/test_strict_query_contract.py::test_q01_desconocido_422 - Assert... | sí |
| Q02 | desconocido con valor vacío aceptado | **KILLED** | FAILED tests/test_strict_query_contract.py::test_q03_vacio_y_sin_igual - Asse... | sí |
| Q03 | comparación sin mayúsculas | **KILLED** | FAILED tests/test_strict_query_contract.py::test_q04_mayusculas_y_parecidos | sí |
| Q04 | se ignoran los parámetros de subdependencias | **KILLED** | FAILED tests/test_strict_query_contract.py::test_q13_dependencias_y_subdependencias | sí |
| Q05 | exención arbitraria (maestros) | **KILLED** | FAILED tests/test_strict_query_contract.py::test_q01_desconocido_422 - Assert... | sí |
| Q06 | solo GET | **KILLED** | FAILED tests/test_strict_query_contract.py::test_q09_post_patch_delete - Asse... | sí |
| Q07 | se saltan POST y PATCH | **KILLED** | FAILED tests/test_strict_query_contract.py::test_q09_post_patch_delete - Asse... | sí |
| Q08 | eco de valores en field_errors | **KILLED** | FAILED tests/test_strict_query_contract.py::test_q01_desconocido_422 - Assert... | sí |
| Q09 | verificador antes de la autenticación | **KILLED** | FAILED tests/test_strict_query_contract.py::test_q10_sin_token_401 - Assertio... | sí |
| Q10 | desconocidos sin orden lexicográfico | **KILLED** | FAILED tests/test_strict_query_contract.py::test_q05_varios_ordenados - Asser... | sí |
| D01 | instante sin zona leído como UTC | **KILLED** | FAILED tests/test_naive_datetime_input.py::test_d01_cuerpo_sin_zona - Asserti... | sí |
| D02 | solo cuerpo: la consulta de notificaciones vuelve a datetime | **KILLED** | FAILED tests/test_naive_datetime_input.py::test_d02_consulta_sin_zona - Asser... | sí |
| D03 | solo consulta: el cuerpo de la delegación vuelve a datetime | **KILLED** | FAILED tests/test_naive_datetime_input.py::test_d01_cuerpo_sin_zona - Asserti... | sí |
| D04 | NAIVE_DATETIME solo para errores de primer nivel (anidados → VALIDATION_ERROR) | **KILLED** | FAILED tests/test_naive_datetime_input.py::test_d09_anidado_y_lista_sintetico | sí |
| D05 | sin normalizar a UTC | **KILLED** | FAILED tests/test_naive_datetime_input.py::test_d09_anidado_y_lista_sintetico | sí |
| D06 | BUSINESS_DATE rechazada por accidente | **KILLED** | FAILED tests/test_naive_datetime_input.py::test_d11_fecha_de_negocio_intacta | sí |
| D07 | regla CSV de tasas rota (hora sin zona como UTC) | **KILLED** | FAILED tests/test_business_civil_date_rates.py::test_el_csv_con_hora_sin_zona_es_hora_de_caracas | sí |
| E01 | q sin la empresa en el join | **KILLED** | FAILED tests/test_inventory_balances_search.py::test_e01_busca_por_nombre_sin_mayusculas | sí |
| E02 | q no se compone con el almacén | **KILLED** | FAILED tests/test_inventory_balances_search.py::test_e05_compone_con_filtros | sí |
| T01 | la búsqueda de taxonomía incluye inactivos | **KILLED** | FAILED tests/test_taxonomy_search.py::test_t03_busqueda_por_s_ordenada_por_nombre | sí |
| U01 | la UI vuelve a enviar un parámetro no declarado (company_id) | **KILLED** | × Contrato de consulta del frontend (FR-001-271) > QC-01: no hay violaciones de consulta 8ms | sí |
| U02 | la página no vuelve a 1 al buscar | **KILLED** | × ExistenciasPage · búsqueda de servidor > EXS-F-04 · paginar avanza y una nueva búsqueda vuelve a page=1 1187 | sí |
| U03 | guarda desactivada (no compara nombres) | **KILLED** | × Contrato de consulta del frontend (FR-001-271) > QC-05: detecta un parámetro no declarado en una cadena plan | sí |

**TOTAL = 23 · KILLED = 23 · EQUIVALENT = 0 · BEHAVIORALLY_SURVIVING = 0 · INVALID = 0.**

En la primera pasada D07 «sobrevivió» con «2 passed, 7 skipped»: las pruebas que lo matan no corrían en SQLite. Contra PostgreSQL muere por `test_el_csv_con_hora_sin_zona_es_hora_de_caracas`. Se informa en vez de contarlo como superviviente.

Líneas base, sin mezclar: 02D 91/89/2/0 · 02E 12/11/1/0 · 03 35/35/0/0 · 04 24/24/0/0 · **05 23/23/0/0**.
