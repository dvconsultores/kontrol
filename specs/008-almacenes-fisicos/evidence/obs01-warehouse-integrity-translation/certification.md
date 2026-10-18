# Certificación (`qa/suite_tiempos.py --con-analizador` y `qa/e2e-run.py --con-analizador`; 2026-10-18)
| Suite | Resultado | Duración monotónica | Anomalía | Delta frente a la entrada |
|---|---|---|---|---|
| SQLite #1 | **1814 / 0 / 1046** | 639,2 s | NORMAL (1,01× la mediana de 8) | +14 = O01-01…14 |
| SQLite #2 | **1814 / 0 / 1046** | 638,7 s | NORMAL (1,00×) | +14 |
| PostgreSQL | **2834 / 0 / 26** | 1413,8 s | NORMAL (0,98×) | +14 |
| E2E | **284 / 0 / 0** | 4,5 min | — | sin cambio; limpieza LIMPIA |
| OpenAPI | **544 / 533 / 11** | — | — | sin cambio |
Residuos: bases de corrida 0 · esquemas `t_` 0 · raíces efímeras 0 (cuatro directorios vacíos de mi guion de recuento OpenAPI,
eliminados por nombre) · puertos 8000/8010/5173 libres. Migraciones, esquema, `qa/`, composición y OBS-09: 0 cambios.
