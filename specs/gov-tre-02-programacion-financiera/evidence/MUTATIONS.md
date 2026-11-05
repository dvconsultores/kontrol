# GOV-TRE-02 · mutaciones de negocio (T029, herramienta de Claude `mutar2.py`)

**Método:** un SEARCH único por mutante; purga de `__pycache__` y `PYTHONDONTWRITEBYTECODE=1`; restauración verificada por sha256 tras cada uno.

## Resultado final: 36 mutantes · 36 muertos · 0 equivalentes · 0 supervivientes

| ID | Mutación | Resultado | Prueba que falla |
|---|---|---|---|
| CJ-M01 | ámbito: programa sin filtro de empresa | KILLED | tests/test_gov_tre02_seguridad.py::test_sg04_empresa_ajena_no_accede |
| CJ-M02 | ámbito: rubro de otra empresa utilizable | KILLED | tests/test_gov_tre02_programa.py::test_pg08_linea - assert 201 == 422 |
| CJ-M03 | cuenta: declarable en cualquier estado | KILLED | tests/test_gov_tre02_programa.py::test_pg06_cuenta_no_valida - Asserti... |
| CJ-M04 | cuenta: de otra empresa | KILLED | tests/test_gov_tre02_seguridad.py::test_sg14_cuenta_vigente_de_otra_empresa |
| CJ-M05 | moneda: cuenta de otra moneda declarable | KILLED | tests/test_gov_tre02_programa.py::test_pg06_cuenta_no_valida - Asserti... |
| CJ-M06 | fórmula: suma los desembolsos | KILLED | tests/test_gov_tre02_programa.py::test_pg09_formula - AssertionError: ... |
| CJ-M07 | fórmula: sin arrastre al mes siguiente | KILLED | tests/test_gov_tre02_programa.py::test_pg09_formula - AssertionError: ... |
| CJ-M08 | fórmula: el déficit no se marca | KILLED | tests/test_gov_tre02_programa.py::test_pg11_deficit - assert False |
| CJ-M09 | período: el mes pasado se admite | KILLED | tests/test_gov_tre02_versiones.py::test_rv03_mes_pasado_en_reprogramacion |
| CJ-M10 | período: la versión 1 también bloquea mes pasado | KILLED | tests/test_gov_tre02_versiones.py::test_rv01_reprogramar_con_motivo - ... |
| CJ-M11 | período cerrado: ejercicio terminado reprogramable | KILLED | tests/test_gov_tre02_versiones.py::test_rv09_ejercicio_terminado - ass... |
| CJ-M12 | período: mes anterior al inicial admitido | KILLED | tests/test_gov_tre02_programa.py::test_pg08_linea - assert 201 == 422 |
| CJ-M13 | historia: activar no deja rastro | KILLED | tests/test_gov_tre02_programa.py::test_pg13_activar - assert False |
| CJ-M14 | estado: la versión anterior no queda superada | KILLED | tests/test_gov_tre02_versiones.py::test_rv05_activar_reprogramacion - ... |
| CJ-M15 | estado: cerrar no cierra la versión | KILLED | tests/test_gov_tre02_cierre.py::test_ci01_cierre_motivo_completo - ass... |
| CJ-M16 | estado: activar sin faltantes | KILLED | tests/test_gov_tre02_programa.py::test_pg14_sin_preparar - assert 200 ... |
| CJ-M17 | reprogramar: no copia las líneas | KILLED | tests/test_gov_tre02_versiones.py::test_rv01_reprogramar_con_motivo - ... |
| CJ-M18 | permiso: activar con manage | KILLED | tests/test_gov_tre02_seguridad.py::test_sg02_gestor_sin_activar_ni_cerrar |
| CJ-M19 | permiso: activar sin MFA | KILLED | tests/test_mfa_policy.py::test_mfa_g00_todo_permiso_esta_clasificado |
| CJ-M20 | auditoría: activar registrada como actualizar | KILLED | tests/test_gov_tre02_programa.py::test_pg13_activar - assert 0 == 1 |
| CJ-M21 | SoD: activar sin guarda | KILLED | tests/test_gov_tre02_seguridad.py::test_sg12_guarda_sod_activar - asse... |
| CJ-M22 | concurrencia: sin versión en programa | KILLED | tests/test_gov_tre02_seguridad.py::test_sg08_version_vieja_y_sin_if_match |
| CJ-M23 | fecha de corte futura admitida | KILLED | tests/test_gov_tre02_programa.py::test_pg07_declaracion_validaciones |
| CJ-M24 | rubro inactivo utilizable | KILLED | tests/test_gov_tre02_programa.py::test_pg08_linea - assert 201 == 422 |
| CJ-M25 | ejercicio anterior admitido | KILLED | tests/test_gov_tre02_programa.py::test_pg04_validaciones - assert 201 ... |
| CJ-M26 | descartar la versión 1 no descarta el programa | KILLED | tests/test_gov_tre02_programa.py::test_pg03_duplicado - AssertionError... |
| CJ-M27 | SoD: reprogramar sin guarda | KILLED | tests/test_gov_tre02_seguridad.py::test_sg15_guarda_sod_reprogramar |
| CJ-M28 | SoD: cerrar sin guarda | KILLED | tests/test_gov_tre02_seguridad.py::test_sg16_guarda_sod_cerrar |
| CJ-F01 | interfaz: mes mal indexado | KILLED | ProgramaPage > muestra la tabla de disponibilidad mensual y el aviso de déficit  |
| CJ-F02 | interfaz: activar sin capacidad | KILLED | ProgramaPage > oculta acciones de activar y cerrar cuando no hay permiso de acti |
| CJ-F03 | interfaz: aviso de semántica fuera | KILLED | ProgramaPage > muestra detalle: encabezado, aviso de semántica y datos del progr |
| CJ-F04 | interfaz: consulta sin versión | KILLED | ProgramaPage > reprograma enviando el motivo y pide versión del borrador 1339ms |
| CJ-F05 | interfaz: líneas desde enero siempre | KILLED | LineasPrograma > LP-06: meses desde el mes inicial 36ms |
| CJ-F06 | interfaz: escribir líneas sin capacidad | KILLED | LineasPrograma > LP-02: solo lectura no muestra acciones 52ms |
| CJ-F07 | interfaz: «Nuevo programa» sin capacidad | KILLED | ProgramasPage > PP-02 · con view: tabla con código enlazado, ejercicio, moneda,  |
| CJ-F08 | interfaz: alta de rubro sin capacidad | KILLED | RubrosPage > RP-02 · con view muestra la tabla sin formulario ni acciones 73ms |

## Incidencias
- **CJ-M04** sobrevivió la primera tanda: las cuentas de otra empresa usadas estaban en borrador y el filtro de estado ocultaba la falta del filtro de empresa. Hueco real de prueba: se añadió SG-14 con una cuenta VIGENTE de otra empresa; el mutante muere.
- **CJ-M19** sobrevivió con la orden de las suites de TRE-02: `classify` falla cerrado. Muere en `test_mfa_policy.py`, que comprueba que todo permiso está clasificado.
- **CJ-F08** no llegó a correr en la primera tanda: SEARCH repetido en el fichero. Se repitió con contexto único y muere.

- **CJ-M27 y CJ-M28** se añadieron tras `/speckit-converge`, que detectó que la guarda de reprogramar y cerrar no tenía prueba (hallazgo F1).

**Estado final:** árbol verificado sin restos de mutantes.
