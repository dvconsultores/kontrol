# CTL-10 POST-CLOSURE-01 · mutaciones

Herramienta de Claude `mutar2.py`, con restauración verificada por sha256. Solo cuenta como muerte un fallo de una prueba con nombre.

## Resultado final: 35 mutantes · 35 muertos · 0 equivalentes · 0 supervivientes

Primera corrida: 29 muertos y 6 supervivientes (F02, F05, A04, A05, A06, A07). Eran huecos reales: el CSV con contexto, volver por el menú, el año decimal, y un falso verde: un `<select>` con un valor inexistente también se lee como `""`. M3 añadió pruebas de comportamiento y los seis murieron.

| ID | Mutación | Resultado | Prueba que falla |
|---|---|---|---|
| B01 | enlace de hallazgos sin contexto | KILLED | tests/test_gov_ctl10_lista_contexto.py::test_lc01_ruta_lista_de_hallazgos_lleva_contexto |
| B02 | enlace con riesgo incorrecto | KILLED | tests/test_gov_ctl10_lista_contexto.py::test_lc01_ruta_lista_de_hallazgos_lleva_contexto |
| B03 | enlace sin abiertos | KILLED | tests/test_gov_ctl10_lista_contexto.py::test_lc01_ruta_lista_de_hallazgos_lleva_contexto |
| B04 | enlace de actos sin contexto | KILLED | tests/test_gov_ctl10_lista_contexto.py::test_lc02_ruta_lista_de_actos_lleva_contexto |
| B05 | enlace de actos con estado incorrecto | KILLED | tests/test_gov_ctl10_lista_contexto.py::test_lc02_ruta_lista_de_actos_lleva_contexto |
| B06 | abiertos no filtra | KILLED | tests/test_gov_ctl10_lista_contexto.py::test_lc03_poblacion_del_filtro |
| B07 | abiertos invertido | KILLED | tests/test_gov_ctl10_lista_contexto.py::test_lc03_poblacion_del_filtro |
| B08 | riesgo_minimo no filtra | KILLED | tests/test_gov_ctl10_lista_contexto.py::test_lc03_poblacion_del_filtro |
| B09 | riesgo exacto y no igual o superior | KILLED | tests/test_gov_ctl10_lista_contexto.py::test_lc03_poblacion_del_filtro |
| B10 | riesgos_desde excluye el minimo | KILLED | tests/test_gov_ctl10_lista_contexto.py::test_lc03_poblacion_del_filtro |
| B11 | CSV sin contexto | KILLED | tests/test_gov_ctl10_lista_contexto.py::test_lc08_exportar_respeta_el_filtro |
| B12 | lista sin contexto | KILLED | tests/test_gov_ctl10_lista_contexto.py::test_lc03_poblacion_del_filtro |
| B13 | lista de otra empresa | KILLED | tests/test_gov_ctl10_lista_contexto.py::test_lc06_otra_empresa_no_ve |
| T01 | pendientes truncados en 5 | KILLED | tests/test_gov_ctl10_lista_contexto.py::test_lc10_mas_de_cinco_pendientes |
| T02 | muestra de 6 | KILLED | tests/test_gov_ctl10_lista_contexto.py::test_lc10_mas_de_cinco_pendientes |
| T03 | muestra sin limite | KILLED | tests/test_gov_ctl10_lista_contexto.py::test_lc10_mas_de_cinco_pendientes |
| T04 | muestra incompleta | KILLED | tests/test_gov_ctl10_lista_contexto.py::test_lc10_mas_de_cinco_pendientes |
| T05 | total con la muestra y no el recuento | KILLED | tests/test_gov_ctl10_lista_contexto.py::test_lc10_mas_de_cinco_pendientes |
| F01 | consulta sin contexto | KILLED | HallazgosPage > HCTX-01 renderiza filtros de cierre y riesgo desde la ruta 31ms |
| F02 | CSV sin contexto | KILLED | HallazgosPage > HCTX-08 exporta aplicando el contexto seleccionado 1041ms |
| F03 | quitar filtro no hace nada | KILLED | HallazgosPage > HCTX-04 quita el filtro de cierre desde el botón de contexto 1047ms |
| F04 | limpiar filtros conserva el contexto | KILLED | HallazgosPage > HCTX-05 quita todos los filtros desde el botón de contexto 1048ms |
| F05 | sin remontar al cambiar la URL | KILLED | HallazgosPage > HCTX-09 volver por el menu limpia los filtros de la URL 1102ms |
| F06 | riesgo sin validar | KILLED | HallazgosPage > HCTX-02 ignora riesgos no permitidos y muestra listado base 30ms |
| F07 | claves heredadas aceptadas | KILLED | HallazgosPage > HCTX-07 ignora riesgos heredados de Object.prototype 21ms |
| F08 | abiertos no se envia | KILLED | HallazgosPage > HCTX-01 renderiza filtros de cierre y riesgo desde la ruta 31ms |
| F09 | riesgo no se envia | KILLED | HallazgosPage > HCTX-01 renderiza filtros de cierre y riesgo desde la ruta 31ms |
| F10 | aviso sin riesgo | KILLED | HallazgosPage > HCTX-01 renderiza filtros de cierre y riesgo desde la ruta 32ms |
| A01 | anio de la URL ignorado | KILLED | ActosPage > contexto de la URL > ACTX-01 aplica anio y estado de la URL 22ms |
| A02 | estado de la URL ignorado | KILLED | ActosPage > contexto de la URL > ACTX-01 aplica anio y estado de la URL 22ms |
| A03 | anio fuera de rango en el selector | KILLED | ActosPage > contexto de la URL > ACTX-04 valida año 2040 y permite limpiar estado 18ms |
| A04 | anio sin validar | KILLED | ActosPage > contexto de la URL > ACTX-07 ignora un anio decimal 1008ms |
| A05 | estado sin validar | KILLED | ActosPage > contexto de la URL > ACTX-08 un estado no valido no filtra la lista 1021ms |
| A06 | estado heredado aceptado | KILLED | ActosPage > contexto de la URL > ACTX-06 ignora estado heredado 1019ms |
| A07 | sin remontar al cambiar la URL | KILLED | ActosPage > contexto de la URL > ACTX-09 volver por el menu limpia los filtros de la URL 1034ms |
