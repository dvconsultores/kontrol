# `/speckit.converge` · OBS-12 · SUITE-DURATION-VARIABILITY
| Gate | Resultado |
|---|---|
| Histórico | 9 corridas reconciliadas; 2946 s = `HISTORICAL_OUTLIER_WITH_INSUFFICIENT_HOST_TELEMETRY`; nada inventado |
| Medición actual | SQLite 581,6 s · PostgreSQL 1356,5 s (etapa 1, instrumentación externa); perfil por prueba completo |
| Familias lentas | analizador 55 % / 39 % (estable, legítimo) · procesos reales 15 % · esperas legítimas < 2 % · PGLIFE ≈ 330 s · resto repartido |
| Esperas | inventario completo; ningún techo consumido; `busy_timeout` nunca alcanzado |
| Retraso patológico activo | 0 |
| Contrato de medición | `qa/suite_tiempos.py` reproducible: monotónico, perfil, anfitrión saneado (carga, memoria, swap, paginación, CPU, disco), `getrusage`, residuos, anomalía no bloqueante, `HARD_THRESHOLD = NONE` |
| Dirigidas / mutaciones | 20/20 · 13/13 |
| SQLite ×2 (por la herramienta) | 1719/0/1046 · 1719/0/1046 (580,2 s · 576,4 s) |
| PostgreSQL | 2739/0/26 (1349,9 s) |
| E2E | 284/0/0 con analizador; LIMPIA |
| OpenAPI | 544/533/11 `BearerAccessToken`, sin cambio |
| Producto / timeouts / busy_timeout / analizador / paralelismo | 0 / 0 / 0 / sin debilitar / 0 |
| Residuos | bases 0 · esquemas `t_` 0 · efímeros 0 · almacén fijo distinguido · puertos libres · ClamAV rastreado 0 · `qa/backend-runs/` ignorado |
| BLOCKER · MATERIAL OQ · UNKNOWN · trazabilidad | 0 · 0 · 0 · 100 % |
**CLOSED / CONVERGED** (caso A con el atípico histórico clasificado como telemetría insuficiente). Tareas 8 · CLAUDE_ONLY 8 ·
DeepSeek 0 · reintentos 0 · parches 0/0 · implementadas por Claude 8 (Claude hizo la delta entera) · coste $0.
