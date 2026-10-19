# Certificación (2026-10-19)
| Suite | Resultado | Duración | Anomalía | Delta frente a la entrada |
|---|---|---|---|---|
| Sonda X3 tras la corrección (uvicorn real, pool de producción, PostgreSQL) | retenedoras **3,06 s** (antes 30,26 s) · escritura **404 en 3,0 s** (antes 500 en 30,03 s) · C1 3,05 s · C2 3,05 s · X2 hasta 20 sin error · balance 145 = 145 | — | — | converge con el contrafactual X4 (`post-fix-reproduction.json`) |
| SQLite #1 | **1876 / 0 / 1046** | 649,6 s | NORMAL | +17 = `test_license_middleware_event_loop.py` |
| SQLite #2 | **1876 / 0 / 1046** | 646,0 s | NORMAL | +17 |
| PostgreSQL | **2896 / 0 / 26** | 1433,4 s | NORMAL | +17 |
| E2E (una corrida, `r20261019t052611p1246833nc3e106`) | **284 / 0 / 0** · limpieza LIMPIA | 4,6 min | — | sin cambio |
| OpenAPI | **544 / 533 / 11** | — | — | sin cambio |

**Durante la E2E** (precheck apto: MemAvailable 5 975 MB, swap 4 094 MB):
- La memoria disponible bajó hasta 572 MB, la swap llegó a 7 912 MB y la carga a 14,77.
- Hubo 5 clamscan simultáneos, con una vida máxima de 21 s.
- El backend registró 0 `QueuePool` y 0 errores no controlados. La presión fue **mayor** que en la corrida roja de `f93232b`.

Residuos: bases de corrida 0 · `t_` 0 · efímeros 0 · puertos libres · procesos del ciclo 0 · sondas 0 · hooks de telemetría 0.
