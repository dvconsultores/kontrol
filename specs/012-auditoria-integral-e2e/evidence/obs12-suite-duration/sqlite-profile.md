# Perfil SQLite completa instrumentada (etapa 1; orden canónica + `--durations=0`; analizador real por envoltorio de medición)
| Registro | Valor |
|---|---|
| `TOTAL_DURATION` | **581,6 s monotónicos** (pared 581,6 s; `desvio_reloj_s` −0,0: sin salto) · pytest interno 553,7 s → **≈ 28 s de arranque + colección + importación** (PROCESS_STARTUP del propio pytest) |
| `RESULT_COUNTS` | 1698 passed · 1 failed · 1046 skipped (2745 nodos). El único fallo es `test_clam_04_05_06…`, que exige que `KONTROL_CLAMSCAN_PATH` sea el binario del caché y en la corrida instrumentada era el **envoltorio de medición**: artefacto de la instrumentación (`MEASUREMENT_ERROR` conocido y explicado), no del producto ni del arnés; sin envoltorio esa prueba pasa (OBS-11: 1699/0/1046 ×2) |
| `SCANNER_ENGINE` / `SCANNER_DB` | ClamAV 1.4.3 · main 63 · daily 28153 · bytecode 339 (`<qa-cache>`) |
| CPU del árbol de pytest (`getrusage`) | usuario 628,0 s + sistema 55,2 s = **683 s de CPU en 582 s de pared (≈ 1,17 núcleos)**: la suite es secuencial y está limitada por su propio trabajo de CPU (pytest + `clamscan`), no por esperas |
| `maxrss` · cambios de contexto · E/S | 1666 MB · voluntarios 167 618 · involuntarios 25 407 · bloques leídos 69 864 · escritos 0 (todo en memoria/caché) |
| Suma de duraciones listadas (≥ 0,005 s) | 544 s = setup 63 s + call 481 s + teardown 0 s, en 847 pruebas; el resto (≈ 1900 pruebas) suma < 10 s |
| Distribución | ≥ 5 s: 40 fases · 1–5 s: 26 · < 0,5 s: 996 listadas |
| `TOP30` | 300 s = **52 %** del total; top 10 = 160 s (27 %); resto de la suite 282 s (`top30-sqlite.md`) |
| `WAIT_EVENTS` | ninguna espera de techo consumida: ninguna prueba con hilos/subprocesos supera 10 s salvo las que arrancan procesos reales (keepalive 8,5/8,3/6,1 s: uvicorn real; volumen de instalación y sesión aislada 2–4 s: pytest anidado en subproceso); `busy_timeout` no se consume (ninguna prueba SQLite con hilos supera 3,5 s y esa es su setup) |
| Familias | documentos con analizador real **328 s (56 %)** (`test_documents_security.py` 216 s + `test_documents.py` 112 s); preflight real del analizador 13,8 s; procesos reales (keepalive, volumen, sesión aislada) ≈ 57 s; el resto de los ≈ 2680 nodos ≈ 150 s |
Fuente: `<scratch>/o12/corrida-sqlite.pytest.txt`, `corrida-sqlite.rusage.json`, `host-sqlite.csv`, `clamscan-sqlite.csv`.
