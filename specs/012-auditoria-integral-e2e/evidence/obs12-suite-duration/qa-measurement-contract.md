# Contrato de medición del QA (`qa/suite_tiempos.py`, Spec 054)
Orden canónica instrumentada (en `.claude/CLAUDE.md`): `python qa/suite_tiempos.py --motor sqlite|postgres --con-analizador`.
| Elemento | Contrato |
|---|---|
| Orden envuelta | `<venv python> -m pytest tests -o addopts= -q --durations=0 -p no:cacheprovider` desde `resources/backend`: misma colección y mismo orden que la canónica; `-o addopts=` deja visible el resumen que `--durations` necesita |
| Entorno | `PYTHONDONTWRITEBYTECODE=1`; `KONTROL_TEST_DB_URL` fijada (postgres) o retirada (sqlite); `KONTROL_DOCUMENT_SCAN` **retirado siempre** (nunca se apaga el analizador); con `--con-analizador`, `clamav_qa.asegurar()` antes de empezar y sus rutas exportadas como las lee el producto |
| Duración | `time.monotonic()`; el reloj de pared solo para `desvio_de_reloj` (reutiliza `e2e_corrida.desvio_de_reloj`: `salto` si |desvío| > 5 s) |
| Veredicto | el código de salida de la orden **es el de pytest**; recuentos del resumen (`failed/passed/skipped/errors/segundos`, `completo`) |
| Perfil | `--durations=0` → `top_n` (30) por prueba con setup/call/teardown, suma listada, por fase; empates por nodo (determinista) |
| Anfitrión | muestreador en hilo cada 30 s desde `/proc`: load1/5/15, `MemAvailable`, swap usada, paginación entrante/saliente (`pswpin/pswpout`), utilización de CPU por delta, E/S de disco por delta sobre dispositivos enteros; resumen (medias, máximos, mínimos, sumas) y `disponible` por fuente; una fuente ausente deja `None`, nunca inventa ni falsea la duración |
| Recursos | `getrusage(RUSAGE_CHILDREN)` delta: CPU usuario/sistema, RSS máximo, cambios de contexto, bloques de E/S |
| Residuos | `kontrol-test-sqlite-*` y `kontrol-test-license-*` en el directorio temporal; `kontrol-test-storage` se anota como almacén fijo, no como residuo |
| Anomalía | **no bloqueante**: razón duración/mediana de las corridas previas del mismo motor con resumen completo en `qa/backend-runs/`; `SIN_REFERENCIA` con menos de 3; `ANOMALIA` desde 2,0× (evidencia: corridas normales ≤ 1,2× entre sí; la atípica 5×); `umbral_duro: null`; **`HARD_THRESHOLD = NONE`** |
| Saneado | `<repo>`, `<qa-cache>`, `<tmp>`, `<home>` sustituyen las rutas en el manifiesto, la orden y la salida de pytest; nunca se recogen IP, interfaces, túneles, nombre del equipo ni usuario |
| Evidencia | `qa/backend-runs/<run_id>/manifest.json`, `pytest.txt`, `host.csv` (ignorado por Git, como `qa/e2e-runs/`) |
| Manifiesto | `suite, motor, run_id, inicio_utc, orden, duracion{monotonica_s, pared_s, desvio_s, salto}, pytest{completo, passed, failed, skipped, errors, segundos, rc}, analizador{exigido, habilitado, motor, bases}, perfil{top_n, n, pruebas_listadas, suma_listada_s, por_fase_s, top_n_s}, anfitrion{intervalo_s, muestras, disponible, carga, memoria, cpu, disco}, recursos, residuos, anomalia` |
Fuera del contrato (prohibido): cambiar `pytest`/`conftest`/pruebas de producto, timeouts, `busy_timeout`, orden, paralelismo,
analizador; medir con el analizador apagado; umbral duro de duración. `ruff check` y `mypy` limpios.
