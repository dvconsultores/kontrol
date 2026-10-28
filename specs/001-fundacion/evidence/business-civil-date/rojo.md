# Rojo primero · BUSINESS CIVIL DATE (03) · 2026-10-28

Cada bloque es la salida medida al aplicar SOLO la prueba (producto sin aplicar), salvo donde se indica.

## C03-T01

```
ERROR tests/test_business_civil_date.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.39s
ImportError while importing test module '<home>/Projectos/Kontrol/resources/backend/tests/test_business_civil_date.py'.
E   ImportError: cannot import name 'ZONA_DE_NEGOCIO' from 'app.shared.clock' (<home>/Projectos/Kontrol/resources/backend/app/shared/clock.py)
```

## C03-T02

```
== rojo sqlite
== rojo pg
FAILED tests/test_business_civil_date_rates.py::test_la_rate_date_de_las_2330_de_caracas_es_la_del_dia_de_caracas
FAILED tests/test_business_civil_date_rates.py::test_la_politica_de_una_consulta_a_las_2330_es_la_del_dia_de_caracas
FAILED tests/test_business_civil_date_rates.py::test_el_csv_con_fecha_rige_desde_las_cero_de_caracas
FAILED tests/test_business_civil_date_rates.py::test_el_csv_con_hora_sin_zona_es_hora_de_caracas
4 failed, 3 passed in 5.20s
FAILED tests/test_business_civil_date_rates.py::test_en_ambos_motores_una_fecha_rige_desde_las_cero_de_caracas
FAILED tests/test_business_civil_date_rates.py::test_en_ambos_motores_un_instante_de_caracas_es_el_mismo_instante
2 failed, 1 skipped, 6 deselected in 1.42s
```

## C03-T03

```
=========================== short test summary info ============================
FAILED tests/test_business_civil_date_documents.py::test_hoy_de_negocio_sale_de_la_costura
FAILED tests/test_business_civil_date_documents.py::test_un_documento_que_vence_hoy_no_esta_vencido_a_las_2330_de_caracas
FAILED tests/test_business_civil_date_documents.py::test_a_las_0030_de_caracas_del_dia_siguiente_ya_esta_vencido
3 failed, 2 passed in 0.44s
```

## C03-T04_T06

```
== rojo PG
FAILED tests/test_business_civil_date_statement.py::test_la_fecha_del_estado_de_cuenta_es_la_de_caracas
FAILED tests/test_business_civil_date_statement.py::test_ninguna_fecha_del_estado_lleva_hora
FAILED tests/test_business_civil_date_reports.py::test_el_periodo_es_el_mes_de_caracas
FAILED tests/test_business_civil_date_reports.py::test_sin_periodo_no_se_filtra
FAILED tests/test_business_civil_date_reports.py::test_un_periodo_invalido_es_422
FAILED tests/test_business_civil_date_reports.py::test_los_libros_fiscales_declaran_que_no_filtran
FAILED tests/test_business_civil_date_reports.py::test_los_reportes_sin_periodo_declaran_period_applied
7 failed, 1 passed in 5.73s
== rojo SQLite
FAILED tests/test_business_civil_date_reports.py::test_el_periodo_es_el_mes_de_caracas
FAILED tests/test_business_civil_date_reports.py::test_sin_periodo_no_se_filtra
FAILED tests/test_business_civil_date_reports.py::test_un_periodo_invalido_es_422
FAILED tests/test_business_civil_date_reports.py::test_los_libros_fiscales_declaran_que_no_filtran
FAILED tests/test_business_civil_date_reports.py::test_los_reportes_sin_periodo_declaran_period_applied
5 failed in 1.71s
```

## C03-T05

```
== rojo PG
FAILED tests/test_business_civil_date_pg.py::test_el_motor_de_la_aplicacion_fija_la_sesion_en_utc
1 failed, 7 passed in 5.28s
```

## C03-T07

```
FAILED tests/test_suite_tiempos_qa.py::test_o12_21_el_resumen_dice_si_hubo_salto_de_reloj
FAILED tests/test_suite_tiempos_qa.py::test_o12_22_sin_salto_el_resumen_lo_dice_tambien
2 failed, 20 passed in 0.27s
```

## C03-T08

```
⎯⎯⎯⎯⎯⎯ Failed Tests 10 ⎯⎯⎯⎯⎯⎯⎯
 FAIL  src/lib/fecha-de-negocio.test.ts > presentación en Caracas sin depender de la zona del navegador > formatea y convierte en la zona UTC
 FAIL  src/lib/fecha-de-negocio.test.ts > presentación en Caracas sin depender de la zona del navegador > formatea y convierte en la zona America/Caracas
 FAIL  src/lib/fecha-de-negocio.test.ts > presentación en Caracas sin depender de la zona del navegador > formatea y convierte en la zona Asia/Tokyo
```

## C03-T14

```
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 2 ⎯⎯⎯⎯⎯⎯⎯
 FAIL  src/modules/reportes/centro/CentroReportesPage.test.tsx > CentroReportesPage > CR-08 un período inválido muestra el error y no pide el reporte
 FAIL  src/modules/reportes/centro/CentroReportesPage.test.tsx > CentroReportesPage > CR-10 avisa cuando el libro fiscal no filtra por período
      Tests  2 failed | 10 passed (12)
nota: rojo de LIB-01 no medido (bloque de producto 11 aplicado junto a las pruebas por error de numeración de Claude)
```

Notas:
- T01: el rojo es de colección (los nombres nuevos del núcleo no existían).
- T02: con el `rates.py` original, las 2 pruebas sobre `sesion_de_prueba` fallan en SQLite (la fecha registrada quedaba en hora de pared de Caracas leída como UTC); 4/7 fallan en PostgreSQL.
- T03: el rojo de las 3 pruebas es por la costura ausente; el defecto de fecha UTC lo prueba además el mutante B11 (muere).
- T05: las pruebas de zona de sesión ya pasaban con T04 aplicado (la fecha se deriva en la aplicación); el rojo atribuible es el del motor que no fijaba la sesión.
- T14: el rojo de LIB-01 no se midió (Claude aplicó por error un bloque de producto junto a las pruebas); CR-08 y CR-10 sí fueron rojos.
