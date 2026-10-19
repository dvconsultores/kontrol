# Resultados de las suites (orden canónica `qa/suite_tiempos.py --con-analizador`, ejecutada con el intérprete de cada entorno)

| Entorno | Ejecución | Resultado | Referencia |
|---|---|---|---|
| V0 (histórico, `.venv`) | SQLite ×2 · PostgreSQL ×1 · E2E ×1 (2026-10-19, ciclo anterior) | 1885/0/1056 ×2 · 2915/0/26 · 284/0/0 | `HISTORICAL_QA_BASELINE` |
| V1 (lo que construye la imagen) | `tests/test_documents*.py`, SQLite | 79 pasan · **31 fallan** · 28 omitidas (V0: 111/0/27) | todas `PRODUCTION_IMAGE_WITHOUT_LIBMAGIC` |
| V2 (V1 + python-magic) | SQLite completa `r20261019t204738p508804n505eed` | rc 1 · **1881/4/1056** · 594,6 s · NORMAL | 4 = OAS-14, ACS-08, U03, U04 |
| V2 | PostgreSQL completa `r20261019t205747p587585n2bd98c` | rc 1 · **2913/2/26** · 1329,7 s · NORMAL | 2 = OAS-14, ACS-08 |
| V0 control | `tests/test_license_middleware_event_loop.py`, SQLite | 17/0/0 | U03/U04 pasan en V0 |
| V2 control | el mismo módulo, SQLite | 15/2/0; U03 sola también falla | determinista |

**Totales:** los mismos casos que V0 (SQLite 1885 + 1056 = 2941; PostgreSQL 2915 + 26 = 2941). Ningún caso se perdió ni
cambió de omitido a ejecutado.

**Pruebas TEST-MIGRACIONES-VENV-FIJO:** pasaron en V2, pero invocan `.venv/bin/alembic` por ruta fija, así que **se
ejecutaron con el alembic de V0**. No fallan; son un hueco de paridad (VENV_PATH_FAILURES 0 · VENV_PATH_TESTS_ON_V0 10
ficheros).
