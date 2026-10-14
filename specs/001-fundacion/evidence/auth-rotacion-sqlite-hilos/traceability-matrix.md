# Trazabilidad

| Eslabón | Evidencia |
|---|---|
| Decisión A de la dueña | `owner-decision-a.md` |
| Causa raíz previa (dos capas) | `root-cause.md`, `controlled-interleaving.md` |
| Limitación de `with_for_update` en SQLite | `contract.md`, `sqlite-i1-poc.md` |
| Contrato de la escritura condicional | `conditional-update-contract.md`, `operation-order.md`, `clock-contract.md` |
| rowcount 1→0 | `rowcount-sqlite.md`, `rowcount-postgres.md`, `cas-poc-output.txt` |
| POC I1 SQLite con el UPDATE exacto | `sqlite-i1-poc.md` |
| Compuerta material | delta §14 |
| Implementación (producto, arnés, pruebas, REM-AUTH) | `implementation.md`; diff en el commit |
| Un ganador · perdedor 401 · sin reemplazo del perdedor · ORM · OperationalError · hilos visibles | `security-directed-tests.md` (SA-01…16) |
| `motor_para_hilos` en auth | `implementation.md`; M-08 |
| Carreras controladas SQLite / PostgreSQL | `controlled-i1-sqlite.md`, `controlled-i1-postgres.md` |
| Mutaciones | `mutation-campaign.md`, `mutation-run.txt`, `mutation-script.sh` |
| Suites completas · OpenAPI · E2E | `sqlite-full-1.md`, `sqlite-full-2.md`, `postgres-full.md`, `openapi.md`, `global-e2e.md`, `full-suites-failed.txt` |
| Convergencia | `convergence.md`, delta §16, roadmap, `next-spec-decision.md` |

FR-AR-A-001…033 ↔ T01–T08 ↔ SA-01…20 / M-01…14: sin huérfanos. Cobertura 100 %.
