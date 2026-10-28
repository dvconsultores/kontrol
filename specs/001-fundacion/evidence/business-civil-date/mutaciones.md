# Mutaciones · BUSINESS CIVIL DATE (03) · 2026-10-28

Herramienta de Claude fuera del árbol (`scratchpad/tools/mutaciones_tiempo.py`):
- reemplazo exacto con una sola coincidencia (35/35 anclas validadas antes);
- backend: pytest en PostgreSQL de QA y en SQLite (muere si cae en cualquiera), `PYTHONDONTWRITEBYTECODE=1` y purga de `__pycache__` antes y después de cada mutante;
- frontend: vitest sobre `src/lib`, `src/i18n`, AuditoriaPage.fecha, `src/tests`, `src/modules/reportes` y `src/modules/fiscal`;
- restauración byte a byte con aserción; 0 `.bak`.

**Validez:** sin mutación, las familias estaban verdes: PG 179/0, SQLite 93/0 (86 omitidas solo-PG) y vitest 378/378.

| TOTAL | KILLED | EQUIVALENT | BEHAVIORALLY_SURVIVING | INVALID |
|---|---|---|---|---|
| 35 | 35 | 0 | **0** | 0 |

| Mutante | Resultado | Prueba que lo mata |
|---|---|---|
| B01 la zona de negocio pasa a UTC | MUERTO | PG: 1 failed in 1.80s · test_vector_01_dia_de_negocio_antes_de_medianoche_caracas |
| B02 el día de negocio es .date() del instante | MUERTO | PG: 1 failed in 1.72s · test_vector_01_dia_de_negocio_antes_de_medianoche_caracas |
| B03 desfase fijo -04:00 en vez de ZoneInfo | MUERTO | PG: 1 failed, 8 passed in 1.76s · test_transicion_historica_decreto_2301 |
| B04 límite superior del período inclusivo | MUERTO | PG: 1 failed, 41 passed in 10.17s · test_el_periodo_es_el_mes_de_caracas |
| B05 límite inferior del período exclusivo | MUERTO | PG: 1 failed, 41 passed in 10.51s · test_el_periodo_es_el_mes_de_caracas |
| B06 rate_date con la fecha UTC | MUERTO | PG: 1 failed, 24 passed in 6.13s · test_la_rate_date_de_las_2330_de_caracas_es_la_del_dia_de_caracas |
| B07 política de la consulta con la fecha UTC | MUERTO | PG: 1 failed, 25 passed in 6.12s · test_la_politica_de_una_consulta_a_las_2330_es_la_del_dia_de_caracas |
| B08 SQLite: la fecha registrada no se normaliza a UTC | MUERTO | PG: 179 passed in 21.50s / SQLite: 1 failed, 24 passed, 7 skipped in 2.24s · test_en_ambos_motores_una_fecha_rige_desde_las_cero_de_caracas |
| B09 CSV: hora sin zona leída como UTC | MUERTO | PG: 1 failed, 29 passed in 6.24s · test_el_csv_con_hora_sin_zona_es_hora_de_caracas |
| B10 CSV: fecha suelta a las 00:00 UTC | MUERTO | PG: 1 failed, 28 passed in 6.21s · test_el_csv_con_fecha_rige_desde_las_cero_de_caracas |
| B11 vencimiento documental con la fecha UTC | MUERTO | PG: 1 failed, 34 passed in 6.72s · test_un_documento_que_vence_hoy_no_esta_vencido_a_las_2330_de_caracas |
| B12 estado de cuenta corta el ISO (día UTC o de la sesión) | MUERTO | PG: 1 failed, 38 passed in 9.28s · test_la_fecha_del_estado_de_cuenta_es_la_de_caracas |
| B13 sin reloj inyectado | MUERTO | PG: 1 failed, 35 passed in 6.99s · test_a_las_0030_de_caracas_del_dia_siguiente_ya_esta_vencido |
| B14 la configuración vuelve a admitir otra zona | MUERTO | PG: 1 failed, 23 passed in 1.84s · test_config_business_timezone_puede_ser_solo_caracas |
| B15 período laxo AAAA-NN | MUERTO | PG: 1 failed, 16 passed in 1.81s · test_periodo_invalido_lanza_kontrol_error[2026-13] |
| B16 la sesión de PostgreSQL deja de fijarse en UTC | MUERTO | PG: 1 failed, 46 passed in 10.08s · test_el_motor_de_la_aplicacion_fija_la_sesion_en_utc |
| B17 los libros fiscales dicen que filtran | MUERTO | PG: 1 failed, 44 passed in 10.02s · test_los_libros_fiscales_declaran_que_no_filtran |
| B18 el período vuelve a ignorarse | MUERTO | PG: 1 failed, 41 passed in 10.14s · test_el_periodo_es_el_mes_de_caracas |
| B19 el estado de cuenta ordena solo por fecha | MUERTO | PG: 1 failed, 39 passed in 9.29s · test_dentro_del_mismo_dia_manda_el_instante |
| Q01 el resumen calla el salto de reloj | MUERTO | PG: 1 failed, 115 passed in 16.15s · test_o12_21_el_resumen_dice_si_hubo_salto_de_reloj |
| F01 formatearInstante sin zona explícita | MUERTO | Tests  4 failed / 374 passed (378) · DATE-03/04/05/06/07 · texto exacto de Caracas bajo la zona del proceso (Europe/A; formatea y convierte en la zona Asia/Tokyo; formatea y convierte en la zona Pacific/Kiritimati |
| F02 hoyDeNegocio con toISOString().slice(0, 10) | MUERTO | Tests  7 failed / 371 passed (378) · devuelve el día de Caracas, no el de UTC; formatea y convierte en la zona America/Caracas; formatea y convierte en la zona Asia/Tokyo |
| F03 hora del input con componentes locales | MUERTO | Tests  3 failed / 375 passed (378) · formatea y convierte en la zona Asia/Tokyo; formatea y convierte en la zona Pacific/Kiritimati; formatea y convierte en la zona UTC |
| F04 desfase fijo de 4 h al convertir hora de Caracas | MUERTO | Tests  1 failed / 377 passed (378) · respeta la transición de hora legal de 2016 |
| F05 hoyDeNegocio con el día del navegador | MUERTO | Tests  6 failed / 372 passed (378) · devuelve el día de Caracas, no el de UTC; formatea y convierte en la zona Asia/Tokyo; formatea y convierte en la zona Pacific/Kiritimati |
| F06 formatearFechaDeInstante sin zona | MUERTO | Tests  3 failed / 375 passed (378) · formatea y convierte en la zona Asia/Tokyo; formatea y convierte en la zona Pacific/Kiritimati; formatea y convierte en la zona UTC |
| F07 el Centro no valida el período | MUERTO | Tests  1 failed / 377 passed (378) · CR-08 un período inválido muestra el error y no pide el reporte |
| F08 el Centro no avisa del bloqueo normativo | MUERTO | Tests  1 failed / 377 passed (378) · CR-10 avisa cuando el libro fiscal no filtra por período |
| F09 Libros no avisa del bloqueo normativo | MUERTO | Tests  1 failed / 377 passed (378) · LIB-01 avisa que el libro no filtra por período |
| F10 formatearFecha vuelve a la zona del navegador | MUERTO | Tests  2 failed / 376 passed (378) · DATE-03/04/05/06/07 · texto exacto de Caracas bajo la zona del proceso (Europe/A; las fechas se formatean y convierten solo en el módulo central |
| F11 una pantalla vuelve a toLocaleString | MUERTO | Tests  1 failed / 377 passed (378) · las fechas se formatean y convierten solo en el módulo central |
| F12 Delegaciones envía 00:00 UTC | MUERTO | Tests  1 failed / 377 passed (378) · las fechas se formatean y convierten solo en el módulo central |
| F13 Tasas envía la hora del navegador | MUERTO | Tests  1 failed / 377 passed (378) · las fechas se formatean y convierten solo en el módulo central |
| F14 una pantalla vuelve a cortar el ISO | MUERTO | Tests  1 failed / 377 passed (378) · las fechas se formatean y convierten solo en el módulo central |
| F15 un instante inválido se disfraza de «—» (DATE-13) | MUERTO | Tests  4 failed / 374 passed (378) · DATE-13 · un valor que no es un instante no se disfraza de «ahora» ni de «—»; devuelve FECHA_INVALIDA para un valor no vacío que no es un instante |

## Líneas base (sin mezclar)

| Campaña | TOTAL | KILLED | EQUIVALENT | BEHAVIORAL |
|---|---|---|---|---|
| 02D (línea base total) | 91 | 89 | 2 | 0 |
| 02E | 12 | 11 | 1 | 0 |
| **03** | **35** | **35** | **0** | **0** |
