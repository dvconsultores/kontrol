# Pruebas dirigidas O12-01…20 (`resources/backend/tests/test_suite_tiempos_qa.py`; dobles: orden falsa, `/proc` en texto, relojes inyectados)
| Id | Qué fija | Resultado |
|---|---|---|
| O12-01 | la duración es monotónica; un salto de +1 h del reloj de pared solo aparece como desvío y `salto` | PASS |
| O12-02 | el manifiesto registra duración total, identidad de la corrida, orden saneada y las secciones completas | PASS |
| O12-03 | telemetría de carga con columnas fijas, sin identidad, numérica (CPU 69,2 % por delta) | PASS |
| O12-04 | memoria y swap saneadas; sin nombre del equipo, `/home/`, IPv4, túneles ni usuario | PASS |
| O12-05 | disco por dispositivo entero, sin rutas absolutas ni raíz del repositorio | PASS |
| O12-06 | `parsear_duraciones`/`top_n`/`perfil` deterministas, empates por nodo | PASS |
| O12-07 | fuente ausente → `disponible` falso, columnas `None`, duración y veredicto intactos | PASS |
| O12-08 | metadatos del analizador presentes; `KONTROL_DOCUMENT_SCAN=off` heredado no llega a pytest; entorno postgres | PASS |
| O12-09 | `kontrol-test-storage` no es residuo | PASS |
| O12-10 | efímeros `sqlite-*`/`license-*` detectados; carpeta ausente → vacío | PASS |
| O12-11 | 1000 s frente a mediana 105 s → `ANOMALIA` (9,52×) y **rc 0 se conserva**; otro motor y manifiestos incompletos no son referencia | PASS |
| O12-12 | anomalía sin cambiar el veredicto; `SIN_REFERENCIA` < 3; NORMAL 1,04×; 2946/587 = 5,02×; motor desconocido → `ValueError` | PASS |
| O12-13 | `scanning.py` conserva `timeout: int = 120`; la herramienta no impone techos | PASS |
| O12-14 | sin `busy_timeout`/`PRAGMA`/`isolation_level` en `conftest.py` ni en la herramienta | PASS |
| O12-15 | falso seguro `scanner_unavailable` intacto; único uso de `KONTROL_DOCUMENT_SCAN` es retirarlo | PASS |
| O12-16 | la herramienta no importa `app`/`sqlalchemy`/`tests` y solo escribe en su carpeta de corrida | PASS |
| O12-17 | `ORDEN_PYTEST` exacta; sin `random/--reverse/-k/--lf/--ff/-x` | PASS |
| O12-18 | sin `-n/xdist/--dist/--forked/multiprocessing` | PASS |
| O12-19 | recuentos del resumen tal cual (con y sin failed, con warnings; sin resumen → incompleto) | PASS |
| O12-20 | `e2e_corrida`/`e2e-run`/`e2e_base`/`clamav_qa` no importan la telemetría; sin sleep/retry/skip/xfail; `.gitignore` y `CLAUDE.md` actualizados; `time.monotonic` y no `time.time()` | PASS |
20/20 en 0,22 s (`-o addopts= -p no:cacheprovider`); `ruff check` limpio; `mypy qa/suite_tiempos.py` limpio.
