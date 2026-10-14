# `/speckit.analyze` final

| Métrica | Valor | Dónde |
|---|---|---|
| DOUBLE_WINNER | 0 (SA-01 10/10, SA-02 5/5, naturales 20/20 + 20/20) | `controlled-i1-*.md`, `directed-series-after.txt` |
| CONDITIONAL_UPDATE_MISSING · ROWCOUNT_IGNORED | 0 · 0 (SA-16; M-01/M-02 muertas) | `mutation-campaign.md` |
| LOSER_SESSION_CREATED · LOSER_WRONG_STATUS · LOSER_WRONG_DOMAIN_CODE | 0 · 0 · 0 (SA-01, SA-06/10; M-03/04/06/07) | ídem |
| REPLAY · EXPIRY · TOKEN_HASH · INACTIVE_USER regresiones | 0 (SA-06/07/08/09) | `security-directed-tests.md` |
| ORM_STALE_OVERWRITE | 0 (SA-13) | ídem |
| WITH_FOR_UPDATE_REMOVED | 0 (SA-16; M-05) | ídem |
| SQLITE_LOCK_MISCLASSIFIED | 0 (SA-14; M-12) | ídem |
| SHARED_SQLITE_AUTH_CONNECTION | 0 (`motor_para_hilos` en los dos módulos; M-08) | `implementation.md` |
| WORKER_EXCEPTION_HIDDEN | 0 (SA-15; M-11) | ídem |
| AUTH_TARGET_INTERMITTENT | 0 (20/20 sola, 10/10 módulo, 2 suites completas) | `sqlite-full-*.md` |
| NEW_SKIP · XFAIL · ASSERTION_WEAKENING · RETRY · SLEEP · BEGIN_IMMEDIATE_PRODUCT · BUSY_TIMEOUT_INFLATION | 0 (SA-16; M-09/10/13) | ídem |
| MIGRATION_ADDED · SCHEMA_CHANGE · TOKEN_MODEL_CHANGE · SESSION_MODEL_CHANGE | 0 (`git diff -- alembic/ models.py` vacío) | SA-20 |
| POSTGRESQL_AUTH_REGRESSION · MOTOR_PARA_HILOS · WAREHOUSE · PGLIFE · PG_SCHEMA · INSTALLATION_VOLUME · LISTADOS · E2E_HELPER · OPENAPI · LICENSING · CENTRAL_SYNC · PICKLIST_409 · CLAMSCAN_SKIP · KEEPALIVE_75 · VERSION_PANEL regresiones | 0 (suites completas sin fallo nuevo; OpenAPI 544/533/11; E2E 280/0/4) | `postgres-full.md`, `openapi.md`, `global-e2e.md` |
| PRODUCTION_502_SCOPE_EXPANSION · SPEC057_STARTED · NEXT_MASTER_SPEC_SELECTED · SECRET_EXPOSURE | 0 · 0 · 0 · 0 (barrido) | roadmap |
| BLOCKER · CRITICAL · CONTRADICTIONS · OWNER CONFLICT · ORPHAN REQ · ORPHAN TASKS · MATERIAL OQ · UNKNOWN | 0 ×8 | delta §11–§16 |
| TRACEABILITY | 100 % | `traceability-matrix.md` |
