# Inventario de esperas y timeouts en `tests/` y `qa/` (solo inventario; nada se cambia)
| Fichero · patrón | Tipo | Valor | Explícito | Propósito | Dueño | Tasa esperada de disparo | En alcance de medición |
|---|---|---|---|---|---|---|---|
| `tests/concurrency.py:38,98` `time.sleep(0.05)` | sondeo PostgreSQL (`pg_stat_activity` hasta `Lock`) | 50 ms por vuelta, plazo acotado | sí | esperar a que el segundo participante quede bloqueado | 054 | se sale en cuanto hay `Lock` (decenas de ms) | sí (PG) |
| `tests/test_spec004_installation_race.py:129` `sleep(0.05)` | sondeo de subproceso | 50 ms | sí | esperar al proceso hermano | 004 | corto | sí |
| `tests/test_backend_keepalive.py:85` `sleep(0.2)` + `urlopen(timeout=2)` + `wait(15)` | sondeo de salud de un backend real | 0,2 s · 2 s · 15 s | sí | arranque de uvicorn | 054 | hasta que responde (segundos) | sí (PROCESS_STARTUP) |
| `tests/test_e2e_corrida.py:293`, `test_e2e_base_ciclo.py:350-362` `sleep(120)` | **dentro de subprocesos sacrificables** (no se espera a que terminen; se matan) | 120 s nominal | sí | simular un proceso ajeno/de la corrida | 054 | 0 (se detienen con señal) | no |
| `threading.Barrier(timeout=15/20/PLAZO)` (import_race, spec030, auth_rotacion, uom_hilos) | barrera | 15–60 s **techo** | sí | entrelazado forzado | 001/008/010/030 | 0 en verde (todas llegan) | sí |
| `h.join(timeout=60)` / `Event.wait(timeout=30)` (license races, spec022, spec030) | techo de hilo | 30–60 s | sí | no colgar la suite | varias | 0 en verde | sí |
| `subprocess.run(..., timeout=600/900)` (migraciones 0018/0024/0033/0043/0047/0048, backfill UoM, spec047 schema) | techo de subproceso **alembic** | 600–900 s | sí | migración real en subproceso | varias | 0 (techo); el coste real es el arranque + migración | sí (PROCESS_STARTUP) |
| `test_pg_sesion_aislada.py`, `test_volumen_de_instalacion.py` `communicate(timeout=300/600)` | techo de subproceso pytest anidado | 300–600 s | sí | sondas de aislamiento | 054 | 0 | sí |
| `test_migrations_offline.py` `timeout=180/240` | techo alembic offline | 180–240 s | sí | — | 054 | 0 | sí |
| `busy_timeout` | **ninguna fijación en tests** (solo un comentario en `test_motor_para_hilos.py:188`); pysqlite por defecto 5 s; `motor_para_hilos` no fija `timeout` ni `PRAGMA` | 5 s por defecto | no | — | 054 | solo bajo contención real entre conexiones (OBS-02/OBS-10 ya eliminaron las contenciones conocidas) | sí (SQLITE_LOCK_WAIT) |
| `app/modules/documents/scanning.py:68` `timeout=120` | techo del subproceso `clamscan` | 120 s | sí (producto) | falso seguro ante cuelgue | 046 | 0 | sí (SCANNER_COST, solo medir) |
| `retry` | 15 coincidencias en tests: **todas** son contratos estáticos que prohíben la palabra, o comentarios de reglas de tasa (`rate_limit`); ningún reintento real | — | — | — | — | — | no |
| `poll` | `proceso.poll()` (estado de subproceso, no espera) | — | — | — | — | — | no |
| `backoff` | 0 | — | — | — | — | — | — |
Conclusión del inventario: no existe ninguna espera incondicional larga en el camino verde; las esperas largas son techos
(timeouts de hilos/subprocesos) que no se consumen cuando la prueba pasa. Candidatos reales de coste: subprocesos alembic
(PROCESS_STARTUP), `clamscan` por subida (SCANNER_COST), sondeos de 50–200 ms y el `busy_timeout` de 5 s solo si hay
contención (se verifica en la etapa 1 por el perfil por prueba).
