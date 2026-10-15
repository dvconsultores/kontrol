# Plan de medición (etapa 1; sin cambio de fuentes del repositorio)
| Elemento | Diseño |
|---|---|
| Corridas | A: SQLite completa canónica con analizador; B: PostgreSQL completa canónica con analizador. Una de cada; una corrida adicional solo con hipótesis nombrada |
| Orden pytest | `-o addopts= -q --durations=0 -p no:cacheprovider` (misma colección y orden que la canónica; `--durations` requiere resumen visible) + `PYTHONDONTWRITEBYTECODE=1` |
| Duración total | `time.monotonic()` en un lanzador Python externo (`<scratch>/o12/lanzar.py`) que ejecuta la orden canónica y registra además `getrusage(RUSAGE_CHILDREN)`; la hora de pared se registra solo para `desvio_de_reloj` |
| Muestreador de anfitrión | `<scratch>/o12/muestrear.py`, cada 30 s: `ELAPSED_MONOTONIC_SECONDS`, `LOAD_1/5/15`, `MEM_AVAILABLE`, utilización de CPU por delta de `/proc/stat`, `procs_running`, deltas de `ctxt`, sectores leídos/escritos de `nvme0n1`, nº de procesos `clamscan`/`alembic`/`python` del árbol (por `/proc/*/comm`, sin argumentos) |
| Coste del analizador | `KONTROL_CLAMSCAN_PATH` apunta a un envoltorio Python externo que registra por invocación: elapsed monotónico, código de salida y tamaño del fichero, y transfiere stdout/stderr/rc intactos al `clamscan` real; la semántica del análisis no cambia (mismo binario, misma base) |
| Perfil por prueba | `--durations=0` → top 30 por motor con setup/call/teardown; cuotas acumuladas top 10 / top 30 / resto |
| Esperas | correlación de las esperas inventariadas con el perfil: una espera «disparada» exige una duración de prueba ≥ su valor |
| Saneado | sin IP, interfaces, VPN, equipo, usuario; rutas como `<repo>`, `<tmp>`, `<qa-cache>` |
| Clases | MACHINE_LOAD · CPU_CONTENTION · MEMORY_PRESSURE · DISK_IO · SCANNER_COST · HARNESS_WAIT · SQLITE_LOCK_WAIT · THREAD_WAIT · PROCESS_STARTUP · NETWORK_EXTERNAL_WAIT · TEST_ORDER · MEASUREMENT_ERROR · MULTIFACTOR · NOT_REPRODUCED · OTHER; UNKNOWN = 0 al converger |
