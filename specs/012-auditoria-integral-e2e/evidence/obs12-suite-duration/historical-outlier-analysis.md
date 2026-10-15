# El atípico histórico de 2946 s (OBS-10, SQLite #2, 2026-10-15 madrugada)
| Registro | Valor |
|---|---|
| Qué se sabe | misma colección, mismas pruebas, mismo veredicto (1692/1/1046) que la #1 de 587 s; corrida secuencial inmediatamente posterior en la misma cadena; medida con `date +%s.%N` (reloj de pared); observación cualitativa «carga de la máquina» sin ninguna medida |
| Qué no existe | load, memoria, CPU, E/S, swap, perfil por prueba, nº de análisis, hora de pared vs monotónico de esa corrida: **HOST_TELEMETRY = UNAVAILABLE** |
| Qué descartan las corridas de hoy | TEST_ORDER (orden idéntico y reproducible), SQLITE_LOCK_WAIT (ningún `busy_timeout` consumido), THREAD_WAIT (techos no consumidos), SCANNER_COST como variable (6,39 s ± 6 % por análisis; 48 análisis fijos = 307 s; para explicar +2360 s cada análisis tendría que haber tardado ≈ 55 s), TEST/PRODUCT defect (suite idéntica hoy en 581,6 s) |
| Qué podría explicarlo | solo factores del anfitrión: CPU robada por otro proceso (load ≫ 12), **paginación por presión de memoria** (hoy 2–3 GB libres y 5 GB de swap en uso: una ventana de navegador o compilación más la dejaría sin margen), o E/S bloqueada. Un salto de reloj de pared (memoria «reloj y red del equipo») también inflaría una medida tomada con `date`, pero la línea `passed in` de pytest de aquella corrida no se conservó para contrastarlo |
| Clasificación | **`HISTORICAL_OUTLIER_WITH_INSUFFICIENT_HOST_TELEMETRY`** = `NOT_REPRODUCED` + `MACHINE_LOAD / MEMORY_PRESSURE / MEASUREMENT_ERROR` sospechadas y no demostrables |
| `EXACT_CAUSE_PROVEN` | NO · `FABRICATED` = NO |
| Qué cambia | a partir de este ciclo cada certificación backend registra duración monotónica, desvío de reloj, perfil por prueba, carga, memoria, swap, E/S y nº de análisis: la próxima corrida atípica será diagnosticable con evidencia (`qa-measurement-contract.md`) |
