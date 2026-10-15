# `/speckit.converge` · OBS-06 · HARNESS-SHARED-STORAGE-PATHS
| Gate | Resultado |
|---|---|
| Causa raíz | PROVEN: SHARED_PATH_LEAK + STALE_STATE_ACROSS_RUNS + CROSS_PROCESS_COLLISION + HARNESS_CLEANUP_DEFECT (D1–D5); SETTINGS/PRODUCT descartadas (D8) |
| Rutas | almacén y respaldos únicos por proceso (`kontrol-test-almacen-<aleatorio>/{storage,backups}`); consistentes dentro del proceso; visibilidad entre procesos 0; estado entre corridas 0; limpieza propia y segura; inyección antes de la captura |
| Producto / migración / esquema / timeouts / retry / sleep / skip / xfail / paralelismo / analizador | 0 / 0 / 0 / 0 / 0 / 0 / 0 / 0 / 0 / intacto |
| OBS-12 | preservada y ampliada (`modo_almacen`, `almacen_por_proceso`, `almacen_fijo_legado_presente`); duración monotónica, perfil, anfitrión y anomalía intactos; **dos suspensiones del equipo registradas como `salto` sin alterar veredictos** |
| Dirigidas / mutaciones | O06 20/20 + regresiones 281/0/44 y 351/0/8 · 14/14 |
| SQLite ×2 | 1739/0/1046 · 1739/0/1046 (642,6 s con suspensión; 600,0 s NORMAL 1,03×) |
| PostgreSQL | 2759/0/26 (1631,9 s; suspensión de 26 min registrada) |
| E2E | 284/0/0 con analizador; LIMPIA |
| OpenAPI | 544/533/11, sin cambio |
| Residuos | bases 0 · esquemas `t_` 0 · raíces efímeras 0 · almacén legado `<tmp>/kontrol-test-storage` conservado (121 ficheros históricos; los marcadores sintéticos de las mutaciones retirados) · puertos libres · ClamAV rastreado 0 |
| BLOCKER · MATERIAL OQ · UNKNOWN · trazabilidad | 0 · 0 · 0 · 100 % |
**CLOSED / CONVERGED**. Tareas 9 · CLAUDE_ONLY 9 · DEEPSEEK_ELIGIBLE 0 · DeepSeek 0 llamadas · reintentos 0 · parches 0/0 ·
implementadas por Claude 9 (Claude hizo la delta entera) · coste $0.
