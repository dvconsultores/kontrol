# Certificación (por `qa/suite_tiempos.py --con-analizador` y `qa/e2e-run.py --con-analizador`; 2026-10-18)
| Suite | Resultado | Duración monotónica | Anomalía | Delta frente a la línea base de entrada |
|---|---|---|---|---|
| SQLite #1 | **1800 / 0 / 1046** | 651,8 s | NORMAL (1,07×) | +17 = +14 de `test_compose_qa.py` (ddc46a8, ya en `HEAD`) + 3 de la regresión de aislamiento |
| SQLite #2 | **1800 / 0 / 1046** | 648,2 s | NORMAL (1,04×) | ídem |
| PostgreSQL | **2820 / 0 / 26** | 1458,1 s | NORMAL (1,02×) | +17 (mismo origen) |
| E2E | **284 / 0 / 0** | — | — | sin cambio; limpieza LIMPIA |
| OpenAPI | **544 / 533 / 11** | — | — | sin cambio |
Residuos: bases de corrida 0 · esquemas `t_` 0 · raíces efímeras 0 · puertos libres. Producto, `qa/`, composición y OBS-09: 0 cambios.
