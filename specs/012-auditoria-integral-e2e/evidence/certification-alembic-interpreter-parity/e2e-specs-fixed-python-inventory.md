# Rutas `.venv/bin/python` fijas en `resources/frontend/e2e/` (hallazgo del cierre, 2026-10-22)

Fuera del alcance declarado de este ciclo (`tests/**` y `qa/e2e_corrida.py`) y fuera de OD-CERT-11, que trata de alembic. Estas rutas ejecutan **ayudantes QA** y `app.modules.scheduler tick`, no alembic. Siempre corren en **V0**, aunque la corrida E2E certifique V5. El arnés ya exporta `KONTROL_E2E_PYTHON = sys.executable` (lo usa `qa/e2e-seed.sh`), pero las specs no lo leen.

| Sitio |
|---|
| `e2e/inicio-version.spec.ts:27` |
| `e2e/licencia-sync.spec.ts:23` |
| `e2e/licencia-periodo.spec.ts:49` |
| `e2e/licencia-revision.spec.ts:24` |
| `e2e/licencia-import.spec.ts:41` |
| `e2e/licencia-import.spec.ts:54` |
| `e2e/diagnostico.spec.ts:31` |
| `e2e/licencia-rotacion.spec.ts:20` |
| `e2e/roles-alta.spec.ts:24` |
| `e2e/licencia.spec.ts:44` |
| `e2e/helpers/usuario.ts:62` |
| `e2e/helpers/planificador.ts:19` |

Total: 12 sitios en 11 ficheros. Deuda nueva, **no absorbida**: **E2E-SPECS-PYTHON-HELPERS-VENV-FIXED** (dueña 054). Consecuencia para este cierre: en V5, el arnés, el backend, la migración del tenant, la siembra, la migración de la autoridad y la autoridad corren en 3.13.16 (medido), y los ayudantes que las specs lanzan con `execFileSync` corren en V0.
