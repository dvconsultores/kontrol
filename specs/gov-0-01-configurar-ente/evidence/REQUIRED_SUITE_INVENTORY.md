# GOV-0-01 · inventario de suites exigidas (2026-10-30)

| Suite | Orden canónica | Resultado | Evidencia |
|---|---|---|---|
| Proceso, backend (PostgreSQL) | `pytest tests/test_gov0_ente.py` (`KONTROL_TEST_DB_URL` de QA) | 18/18 | primero en rojo 18/18 (sin módulo), después verde |
| Backend completo, PostgreSQL | `qa/suite_tiempos.py --motor postgres --con-analizador` | **4075 / 0 / 18** (rc 0, anomalía NORMAL) | `qa/backend-runs/r20261030t014144p3892734n27b70c` |
| Backend completo, SQLite | `qa/suite_tiempos.py --motor sqlite --con-analizador` | **2777 / 0 / 1316** (rc 0, anomalía NORMAL) | `qa/backend-runs/r20261030t022545p133436ncff461` |
| Primera corrida PG completa (antes de las correcciones) | ídem | 4066 / 9 / 18: nueve guardas que exigían declarar lo nuevo y un defecto real de orden de guardas | `qa/backend-runs/r20261030t003648p3319602n805575` → T013/T014 |
| Migración 0063 | `alembic upgrade head` → `downgrade 0062` → `upgrade head` sobre PostgreSQL nueva | rc 0; 15 restricciones con sus nombres; 4 permisos `gobierno_ente` | base de QA `gov0mig` |
| Frontend: tipos | `tsc -b --noEmit` (src, herramientas y e2e) | limpio | — |
| Frontend: lint | `eslint . --max-warnings 0` | limpio | — |
| Frontend: unitarias | `vitest run` | 707 antes del corte + 20 nuevas (GEP-01..10, GEF-01..07, GSB-01..03); 27/27 del módulo y del menú | — |
| Instantáneas del frontend | `qa/fixtures_de_frontend.py` + `test_frontend_fixtures.py` | regeneradas: 6 operaciones nuevas, 4 capacidades nuevas | — |
| Mutaciones de negocio | herramienta de Claude `mutar07b` | **24 / 24 KILLED**, 0 sobrevivientes | `MUTATIONS.md` |
| E2E del proceso ×3 (chromium, firefox, webkit) | `qa/e2e-run.py --con-analizador -- e2e/gobierno-ente.spec.ts --project=firefox --project=webkit` (puertos 18000/15173/18010) | 15/15 en la 1.ª; 2.ª y 3.ª: ver certificación | `qa/e2e-runs/r20261030t025055p274070nfa6bd6` |
| E2E canónica | `qa/e2e-run.py --con-analizador` | ver certificación | — |

Puertos: otro proyecto de la estación ocupa 8000; las corridas usan `KONTROL_E2E_PUERTO_BACKEND=18000`, `_FRONTEND=15173`, `_CENTRAL=18010`. No se detuvo ningún proceso ajeno.
