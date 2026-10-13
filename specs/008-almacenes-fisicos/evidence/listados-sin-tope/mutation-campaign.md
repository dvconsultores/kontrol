# Campaña de mutaciones · LISTADOS-SIN-TOPE

Guion de Claude fuera del repositorio (`mutar_lt.py`): sustitución exacta sobre copia, purga de `__pycache__`,
`PYTHONDONTWRITEBYTECODE=1`, backend sobre PostgreSQL (`test_listados_sin_tope`, `test_picklist_duplicada`), frontend con
Vitest (`organization.test.ts`); restauración desde la copia comprobada byte a byte. GOOD → PASS · MUTATED → FAIL ·
RESTORED → PASS.

| Mutante | Fichero | Cambio | Lo mata |
|---|---|---|---|
| M-01 | `warehouse_api.py` | `limit` sin `le=100` | LT-02 (`limit=101`, `100000`) |
| M-02 | `warehouse_api.py` | `le=200` | LT-02 (`limit=101`) |
| M-03 | `warehouse_api.py` | `limit = min(limit, 100)` **manteniendo** `le=100` | **mal formado** (sigue siendo 422): sustituido por M-03b |
| M-03b | `warehouse_api.py` | sin `le` y recorte silencioso `min(limit, 100)` | LT-02 (espera 422, recibe 200) |
| M-04 | `sales/api.py` | `total = len(items)` | LT-04/05, 06/07, 08, 12/13 |
| M-05 | `sales/api.py` | `offset(0)` | LT-06/07, 08, 11 |
| M-06 | `sales/api.py` | orden sin desempate por `id` | LT-11 |
| M-07 | `sales/api.py` | `count` sin filtro de empresa | LT-04/05, 06/07, 08, 12/13 |
| M-08 | `sales/api.py` | consulta sin empresa, filtro de empresa en Python tras cortar | LT-04/05, 06/07, 08, 09 (y 12/13) |
| M-09 | `sales/api.py` | traer todo y rebanar en Python | LT-SQL (sin `LIMIT` en la sentencia; rebanado en la fuente) |
| M-10 | `src/api/organization.ts` | el ayudante trata la respuesta como array | 4 pruebas de `listAllWarehouses` |
| M-11 | `src/api/organization.ts` | el ayudante se queda con la primera página | «230 → 3 llamadas» |
| M-12 | `sales/service.py` (temporal) | el duplicado deja de ser `PICKLIST_DUPLICATE` | `test_picklist_duplicada` (4) |

## Salida

```
GOOD backend (PG) 0 []
GOOD frontend 0 []
M-01 almacenes sin máximo: KILLED rc=1
    FAILED tests/test_listados_sin_tope.py::test_lt_02_03_fuera_de_contrato_es_422_y_nunca_500[limit=101]
    FAILED tests/test_listados_sin_tope.py::test_lt_02_03_fuera_de_contrato_es_422_y_nunca_500[limit=100000]
M-02 máximo equivocado (200): KILLED rc=1
    FAILED tests/test_listados_sin_tope.py::test_lt_02_03_fuera_de_contrato_es_422_y_nunca_500[limit=101]
M-03b recorte silencioso en vez de 422 (sin le y con min): KILLED rc=1
    FAILED tests/test_listados_sin_tope.py::test_lt_02_03_fuera_de_contrato_es_422_y_nunca_500[limit=101]
    FAILED tests/test_listados_sin_tope.py::test_lt_02_03_fuera_de_contrato_es_422_y_nunca_500[limit=100000]
M-04 pick-lists sin total real: KILLED rc=1
    FAILED tests/test_listados_sin_tope.py::test_lt_04_05_el_sobre_es_el_del_contrato_y_la_primera_pagina_trae_20_de_1100
    FAILED tests/test_listados_sin_tope.py::test_lt_06_07_las_paginas_no_se_solapan_y_la_ultima_es_parcial
    FAILED tests/test_listados_sin_tope.py::test_lt_08_mas_alla_del_final_viene_vacia_con_el_mismo_total
    FAILED tests/test_listados_sin_tope.py::test_lt_12_13_items_y_total_son_solo_de_la_empresa_en_la_que_se_opera
M-05 offset ignorado: KILLED rc=1
    FAILED tests/test_listados_sin_tope.py::test_lt_06_07_las_paginas_no_se_solapan_y_la_ultima_es_parcial
    FAILED tests/test_listados_sin_tope.py::test_lt_08_mas_alla_del_final_viene_vacia_con_el_mismo_total
    FAILED tests/test_listados_sin_tope.py::test_lt_11_el_orden_es_el_del_contrato_mas_reciente_primero_e_id_como_desempate_y_se_repite
M-06 orden sin desempate: KILLED rc=1
    FAILED tests/test_listados_sin_tope.py::test_lt_11_el_orden_es_el_del_contrato_mas_reciente_primero_e_id_como_desempate_y_se_repite
M-07 total de todas las empresas: KILLED rc=1
    FAILED tests/test_listados_sin_tope.py::test_lt_04_05_el_sobre_es_el_del_contrato_y_la_primera_pagina_trae_20_de_1100
    FAILED tests/test_listados_sin_tope.py::test_lt_06_07_las_paginas_no_se_solapan_y_la_ultima_es_parcial
    FAILED tests/test_listados_sin_tope.py::test_lt_08_mas_alla_del_final_viene_vacia_con_el_mismo_total
    FAILED tests/test_listados_sin_tope.py::test_lt_12_13_items_y_total_son_solo_de_la_empresa_en_la_que_se_opera
M-08 paginar antes de filtrar por empresa: KILLED rc=1
    FAILED tests/test_listados_sin_tope.py::test_lt_04_05_el_sobre_es_el_del_contrato_y_la_primera_pagina_trae_20_de_1100
    FAILED tests/test_listados_sin_tope.py::test_lt_06_07_las_paginas_no_se_solapan_y_la_ultima_es_parcial
    FAILED tests/test_listados_sin_tope.py::test_lt_08_mas_alla_del_final_viene_vacia_con_el_mismo_total
    FAILED tests/test_listados_sin_tope.py::test_lt_09_el_maximo_se_acepta - Asse...
M-09 traer todo y rebanar en Python: KILLED rc=1
    FAILED tests/test_listados_sin_tope.py::test_lt_sql_el_corte_viaja_en_la_sentencia_y_no_se_rebana_en_python
M-10 el frontend trata la respuesta como array: KILLED rc=1
    × listAllWarehouses > con más almacenes que una página, recorre todas las páginas con el máximo del contrato y devuelve el conjunto entero 3ms
    × listAllWarehouses > con pocos almacenes, una sola página basta 1ms
    × listAllWarehouses > sin almacenes, devuelve vacío sin pedir una segunda página 1ms
    × listAllWarehouses > nunca pide un limit fuera de contrato 0ms
M-11 el consumidor se queda con la primera página: KILLED rc=1
    × listAllWarehouses > con más almacenes que una página, recorre todas las páginas con el máximo del contrato y devuelve el conjunto entero 8ms
    FAIL  src/api/organization.test.ts > listAllWarehouses > con más almacenes que una página, recorre todas las páginas con el máximo del contrato y devuelve el co
M-12 el duplicado deja de ser 409 PICKLIST_DUPLICATE: KILLED rc=1
    FAILED tests/test_picklist_duplicada.py::test_pl_01_02_03_el_segundo_plan_vivo_es_un_409_de_dominio_y_no_deja_rastro
    FAILED tests/test_picklist_duplicada.py::test_pl_11_12_bajo_concurrencia_entra_exactamente_uno_y_el_resto_es_409[2]
    FAILED tests/test_picklist_duplicada.py::test_pl_11_12_bajo_concurrencia_entra_exactamente_uno_y_el_resto_es_409[10]
    FAILED tests/test_picklist_duplicada.py::test_pl_14_si_la_carrera_llega_al_indice_la_respuesta_es_el_mismo_409_y_la_sesion_sigue_viva
RESTORED backend (PG) 0 []
RESTORED frontend 0 []
RESUMEN: 12 / 12 muertas
```

**12/12 muertas** (M-01, M-02, M-03b, M-04…M-12); M-03 mal formado, declarado y sustituido. Tras la campaña: 0 copias `.good`, `service.py` sin diff. El helper E2E `todasLasListasDePreparacion` no tiene prueba unitaria propia (vive en una suite Playwright); su contrato lo certifican las dos globales E2E.
