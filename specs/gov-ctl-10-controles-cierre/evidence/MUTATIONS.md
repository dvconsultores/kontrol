# GOV-CTL-10 · mutaciones (T037, herramienta de Claude `mutar2.py`)

**Método:** un SEARCH único por mutante; purga de `__pycache__` y `PYTHONDONTWRITEBYTECODE=1`; restauración verificada por sha256 tras cada uno. La revisión exige una prueba con nombre: un fallo de arranque no cuenta como muerte.

## Resultado final: 48 mutantes · 48 muertos · 0 equivalentes · 0 supervivientes

Primera corrida: 40 «muertos» y 8 supervivientes. Tres de esos muertos (S01, S02, S06) eran falsos: `test_gov_ctl10_seguridad.py` no arrancaba solo, por falta de `pytest_plugins`. Se corrigió el fichero y se añadieron `ga19`, `ga20`, `ga21`, `ga22`, `ed07`, `PC-13`, `GES-CIE` y la prueba del panel en el programa. Los 11 se repitieron y murieron por una prueba con nombre.

| ID | Mutación | Resultado | Prueba que falla |
|---|---|---|---|
| G01 | sin guarda en estructura | KILLED | tests/test_gov_ctl10_guarda.py::test_ga01_estructura_hallazgo_alto_bloquea |
| G02 | sin guarda en programa | KILLED | tests/test_gov_ctl10_guarda.py::test_ga07_programa_acto_emitido_bloquea |
| G03 | umbral conteo > | KILLED | tests/test_gov_ctl10_guarda.py::test_ga01_estructura_hallazgo_alto_bloquea |
| G04 | umbral muestra > | KILLED | tests/test_gov_ctl10_guarda.py::test_ga01_estructura_hallazgo_alto_bloquea |
| G05 | cuenta cerrados | KILLED | tests/test_gov_ctl10_guarda.py::test_ga02_tras_cerrar_hallazgo_cierra_y_audita_allow |
| G06 | hallazgos de otra empresa | KILLED | tests/test_gov_ctl10_guarda.py::test_ga06_hallazgo_otra_empresa_no_cuenta |
| G07 | actos de otra empresa | KILLED | tests/test_gov_ctl10_guarda.py::test_ga19_acto_de_otra_empresa_no_bloquea |
| G08 | actos eficaces cuentan | KILLED | tests/test_gov_ctl10_guarda.py::test_ga08_tras_hacer_eficaz_acto_cierra |
| G09 | sin limite inferior | KILLED | tests/test_gov_ctl10_guarda.py::test_ga08_tras_hacer_eficaz_acto_cierra |
| G10 | sin limite superior | KILLED | tests/test_gov_ctl10_guarda.py::test_ga20_acto_del_ejercicio_siguiente_no_bloquea |
| G11 | nunca bloquea | KILLED | tests/test_gov_ctl10_guarda.py::test_ga01_estructura_hallazgo_alto_bloquea |
| G12 | no audita el permitido | KILLED | tests/test_gov_ctl10_guarda.py::test_ga02_tras_cerrar_hallazgo_cierra_y_audita_allow |
| G13 | bloqueo audita otra accion | KILLED | tests/test_gov_ctl10_guarda.py::test_ga03_bloqueo_audita_blocked_y_no_cierra |
| G14 | codigo de error | KILLED | tests/test_gov_ctl10_guarda.py::test_ga01_estructura_hallazgo_alto_bloquea |
| G15 | politica vencida efectiva | KILLED | tests/test_gov_ctl10_guarda.py::test_ga21_politica_vencida_real_no_bloquea |
| G16 | politica futura efectiva | KILLED | tests/test_gov_ctl10_guarda.py::test_ga13_politica_futura_no_bloquea |
| G17 | ruta de muestra de acto | KILLED | tests/test_gov_ctl10_guarda.py::test_ga07_programa_acto_emitido_bloquea |
| G18 | SoD despues de CTL-10 | KILLED | tests/test_gov_ctl10_guarda.py::test_ga18_sod_prevalece |
| G19 | politica de otra accion | KILLED | tests/test_gov_ctl10_guarda.py::test_ga22_politica_de_estructura_no_toca_programa |
| P01 | sin If-Match pasa | KILLED | tests/test_gov_ctl10_politicas.py::test_pp08_if_match_obligatorio |
| P02 | version obsoleta pasa | KILLED | tests/test_gov_ctl10_politicas.py::test_pp08_if_match_obligatorio |
| P03 | estado no exigido | KILLED | tests/test_gov_ctl10_politicas.py::test_pp10_vigente_inmutable_por_api |
| P04 | segunda vigente | KILLED | tests/test_gov_ctl10_politicas.py::test_pp09_segunda_vigente_por_accion |
| P05 | SoD activar | KILLED | tests/test_gov_ctl10_politicas.py::test_pp13_guarda_sod_activar |
| P06 | SoD retirar | KILLED | tests/test_gov_ctl10_retiro.py::test_rt08_guarda_sod_en_retirar |
| P07 | retirar retirada | KILLED | tests/test_gov_ctl10_retiro.py::test_rt04_retirada_no_vuelve |
| P08 | vigencia invertida en edicion | KILLED | tests/test_gov_ctl10_edicion.py::test_ed07_vigencia_invertida_422 |
| P09 | historia de retiro | KILLED | tests/test_gov_ctl10_retiro.py::test_rt01_retirar_vigente_con_motivo |
| P10 | historia de activacion | KILLED | tests/test_gov_ctl10_politicas.py::test_pp07_activar_politica |
| S01 | politica de otra empresa | KILLED | tests/test_gov_ctl10_seguridad.py::test_sg03_empresa_ajena |
| S02 | lista de otra empresa | KILLED | tests/test_gov_ctl10_seguridad.py::test_sg03_empresa_ajena |
| S03 | bloqueos de otra empresa | KILLED | tests/test_gov_ctl10_bloqueos.py::test_bl04_otra_empresa_no_lo_ve |
| S04 | usuario como uuid | KILLED | tests/test_gov_ctl10_bloqueos.py::test_bl07_item_trae_politica_id_y_nombre_de_usuario |
| S05 | sin politica_id | KILLED | tests/test_gov_ctl10_bloqueos.py::test_bl07_item_trae_politica_id_y_nombre_de_usuario |
| S06 | activar con permiso manage | KILLED | tests/test_gov_ctl10_politicas.py::test_pp11_permisos |
| S07 | activar sin MFA | KILLED | tests/test_mfa_policy.py::test_mfa_g00_todo_permiso_esta_clasificado |
| S08 | bloqueos sin filtro accion | KILLED | tests/test_gov_ctl10_bloqueos.py::test_bl02_filtro_accion_y_fechas |
| F01 | otro code | KILLED | detalleDeBloqueoDeCierre > BDC-01 · devuelve null para Error común, ApiError 409 con otro  |
| F02 | sin enlace a la lista | KILLED | BloqueoDeCierre > BDC-03 · muestra política, proceso con etiqueta, objeto, total, dueño, m |
| F03 | sin duenio | KILLED | BloqueoDeCierre > BDC-03 · muestra política, proceso con etiqueta, objeto, total, dueño, m |
| F04 | If-Match ausente | KILLED | PoliticaPage > PC-01 · BORRADOR con gobierno_cierre:manage y :activate muestra «Editar», « |
| F05 | aviso obsoleto | KILLED | PoliticaPage > PC-11 · activar con 409 GOV_CLOSURE_POLICY_STALE muestra un alert con el me |
| F06 | SoD sin panel | KILLED | PoliticaPage > PC-12 · activar con 409 GOV_SOD_CONFLICT muestra un alert con el mensaje 10 |
| F07 | activar sin controles | KILLED | PoliticaPage > PC-13 · sin controles, Activar está deshabilitado 29ms |
| F08 | politica sin enlace id | KILLED | BloqueosPage > BLQ-05 · con :view muestra la fila con enlaces y celdas 84ms |
| F09 | nueva sin manage | KILLED | PoliticasPage > CIE-PP-03 · sin manage no aparece «Nueva política»; con manage aparece con |
| F10 | estructura sin panel | KILLED | EstructuraPage > GES-CIE · bloqueo material muestra el panel 1074ms |
| F11 | programa sin panel | KILLED | ProgramaPage > muestra el panel de bloqueo material al cerrar 1198ms |
