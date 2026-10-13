# Matriz de trazabilidad · TEST-VOLUMEN-DE-INSTALACION-COMPARTIDO

| Eslabón | Artefacto | Prueba / evidencia |
|---|---|---|
| ruta compartida | `tests/conftest.py:26` (HEAD 1f28c83) | `fixture-inventory.md` |
| alcance de fixtures | `--setup-show`; sin class/session | `fixture-inventory.md`, `isolation-scope-decision.md` |
| caché de settings | `get_settings` lru_cache; `_fijar_volumen` | `settings-cache-analysis.md`; TV-05/06/07; M-03 |
| consumidores de clave/estado | 81 ficheros clasificados, UNKNOWN 0 | `consumer-matrix.md` |
| sesiones consecutivas | sonda `tv_probe` | `consecutive-sessions.md` |
| procesos concurrentes | 03a concurrente, 03b determinista | `parallel-processes.md` |
| interferencia | gate material | `interference-proof.md` |
| alcance del aislamiento | HYBRID | `isolation-scope-decision.md` |
| volumen temporal | `pytest_configure` + `mkdtemp` + `config.stash` | T01; TV-01; M-01/M-07 |
| reinicio de caché | `_fijar_volumen` | TV-05/06; M-03 |
| limpieza | `finally` del gestor + `pytest_unconfigure` | `cleanup-proof.md`; TV-03/08/09; M-05/M-08 |
| corrección de pruebas dependientes | 0 necesarias (T02 quita un setdefault inerte) | `consumer-matrix.md` |
| pruebas del arnés | TV-01…TV-23 (`test_volumen_de_instalacion*.py`, `sondas_volumen/`) | `suites-dirigidas.md` |
| mutaciones | M-01…M-12 | `mutation-campaign.md` |
| SQLite completa | 43/1567/1040 | `sqlite-full.md` |
| PostgreSQL completa | 38/2584/28 | `postgres-full.md` |
| E2E global | 273/0/4 | `global-e2e.txt` |
| convergencia | delta §13 | `convergence.md` |

FR-TV-001…026 → cubiertos por T01–T05 y TV-01…TV-23 (delta §5, §9, §12). Cobertura: **100 %**.
