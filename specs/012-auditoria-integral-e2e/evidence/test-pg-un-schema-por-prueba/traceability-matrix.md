# Matriz de trazabilidad · TEST-PG-UN-SCHEMA-POR-PRUEBA

| Eslabón | Artefacto | Prueba / evidencia |
|---|---|---|
| 12 suites `db_session` de función | `suite-inventory.md` | PGS-27 (estático) |
| `make_engine` / `create_all` por prueba | `harness-map.md` | contador PGLIFE (`benchmark-before.md`) |
| relaciones por schema | `relations-per-schema.md` | 841 + 811 · 0 secuencias (PGS-08) |
| benchmark ANTES | `benchmark-before.md` | 384 schemas · 929,8 s · catálogo |
| commits / sesiones / hilos / secuencias | `suite-inventory.md` | PGS-04 (commit de producto), PGS-06 (segunda sesión) |
| POC A/B/C | `poc-candidate-a.md` | 15 → 2 schemas; SQLite descartado |
| mecanismo elegido (HYBRID) | delta §4 | T01 `tests/conftest.py` |
| aislamiento adversarial | `isolation-proof.md` | PGS-02…06b; sondas; M-02…M-05 |
| PGLIFE | `harness-map.md`, `isolation-proof.md` | PGS-07/10/11/26; M-06, M-09b |
| implementación | T01 conftest · T03 12 suites (DeepSeek) · T02 PGS + sondas | `directed-suites.md` |
| mutaciones | `mutation-campaign.md` | 12/12 |
| SQLite completa | `sqlite-full.md` | 43 / 1582 / 1040 |
| PostgreSQL completa + benchmark DESPUÉS + catálogo | `postgres-full-and-benchmark-after.md` | 37 / 2600 / 28 · 188 schemas · 810,0 s |
| E2E global | `global-e2e.txt` | runner sin cambio |
| convergencia | `convergence.md`, delta §13 | — |

FR-PGS-001…029 → T01–T04 y PGS-02…28 (delta §5, §9, §12). Cobertura: **100 %**.
