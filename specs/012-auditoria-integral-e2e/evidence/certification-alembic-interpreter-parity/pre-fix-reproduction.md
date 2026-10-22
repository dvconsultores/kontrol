# Reproducción previa y gate de capacidad (HEAD `d20da5b`, 2026-10-21)

Método de medida: sonda `sitecustomize` desechable (scratchpad, no versionada) en `PYTHONPATH` que cada proceso Python
anota al arrancar y al salir: pid, ppid, `sys.executable`, versión, `realpath(/proc/self/exe)`, y las versiones y
ficheros de `alembic` y `sqlalchemy` cargados. Ninguna línea versionada se tocó para medir.

V5 = IMAGE_ROOTFS reconstruido **por digest** `70729b46…` (4 capas verificadas por sha256; `InRelease` de trixie y
trixie-security con firma correcta; `Packages.xz` y `.deb` verificados; `ca-certificates 20250419+deb13u1`, 148 CA;
`pip check` PASS; freeze = lock).

## Gate de capacidad de `python -m alembic` (§7)

| Medida | V0 | V5 |
|---|---|---|
| CPython | 3.11.16 (`.venv` histórico) | 3.13.16 (rootfs de la imagen) |
| alembic · SQLAlchemy | 1.14.0 · 2.0.36 | 1.14.0 · 2.0.36 |
| `alembic/__main__.py` | `from .config import main` · `main(prog="alembic")` | idéntico |
| `python -m alembic --help` | rc 0 | rc 0 |
| `python -m alembic heads` (tenant) | `0057_spec047_notifications (head)` | idéntico |
| `python -m alembic -c central_authority/alembic.ini heads` | `0002_cla_sync_auth (head)` | idéntico |
| error (`upgrade` a revisión inexistente) | rc 1 (`-m`) · rc 1 (script `.venv/bin/alembic`) | rc 1 |

- **V0_PYTHON_M_ALEMBIC_SUPPORTED = 1 · V5_PYTHON_M_ALEMBIC_SUPPORTED = 1.**
- El script de consola es `sys.exit(main())` sobre la misma `alembic.config.main`: mismos argumentos, mismo código de
  salida, misma salida; solo cambia `prog` en el texto de ayuda.
- `sys.path[0]`: con `-m` es el cwd; con el script, su directorio. Es neutral: los dos `alembic.ini` declaran
  `prepend_sys_path = .` y todas las llamadas usan `cwd=BACKEND`.
- Contrato elegido (OD-CERT-11): `[sys.executable, "-m", "alembic", *argumentos]`. Ya es el patrón del repositorio en
  `qa/e2e_base.py:251` (migración del tenant en E2E) y `tests/test_migraciones_url_porcentaje.py:147`.

## Pruebas de migración (15 ficheros, PostgreSQL de QA)

| Entorno | Resultado | Padre (pytest) | Hijos alembic | Intérprete de los hijos | alembic / SQLAlchemy de los hijos |
|---|---|---|---|---|---|
| V0 | 98 passed | `.venv/bin/python` 3.11.16 | 72 | `.venv/bin/python` 3.11.16 | 1.14.0 / 2.0.36 de `.venv/lib/python3.11` |
| V5 | 98 passed | `v5/bin/python` **3.13.16** | 72 | `.venv/bin/python` **3.11.16** | 1.14.0 / 2.0.36 de `.venv/lib/python3.11` |

- MIGRATION_INTERPRETER_PRE_V0 = `.venv` 3.11.16 = padre → paridad 1 (por coincidencia histórica).
- **MIGRATION_INTERPRETER_PRE_V5 = `.venv` 3.11.16 ≠ padre 3.13.16 → MIGRATION_INTERPRETER_PARITY_PRE = 0.**
- Verde en V5 sin paridad: las 72 migraciones de la «certificación V5» las ejecutó V0.

## Migración de la autoridad central en E2E (V5)

Corrida de sonda: `v5/bin/python qa/e2e-run.py --sin-frontend --orden /usr/bin/true` (base efímera; limpieza LIMPIA;
salida 0).

| Proceso | Intérprete |
|---|---|
| arnés `qa/e2e-run.py` | V5 3.13.16 |
| migración del tenant (`e2e_base.migrar`, `sys.executable -m alembic`) | V5 3.13.16 |
| backend `uvicorn app.main:app` | V5 3.13.16 |
| **migración de la autoridad (`e2e_corrida.py:393`, `.venv/bin/alembic -c central_authority/alembic.ini upgrade head`)** | **V0 3.11.16** (alembic de `.venv/lib/python3.11`) |
| API de la autoridad `uvicorn central_authority.main:app` | V5 3.13.16 |

- E2E_HARNESS_INTERPRETER_PRE = V5 3.13.16 · E2E_AUTHORITY_MIGRATION_INTERPRETER_PRE = V0 3.11.16.
- **E2E_INTERPRETER_PARITY_PRE = 0.** La misma corrida migra el tenant con V5 y la autoridad con V0.

## Árbol aislado sin `.venv` (V5, `git archive d20da5b`)

- `resources/backend/.venv` ausente en el árbol aislado; el `.venv` real no se tocó.
- Resultado: **17 failed, 71 errors, 7 passed, 3 skipped** (rc 1).
- Los 88 fallos y errores: `FileNotFoundError: … resources/backend/.venv/bin/alembic`. Ninguna otra causa.
- Las 3 omisiones son **silenciosas**: `test_migrations_offline.py:54/75/164` hace `pytest.skip("alembic no está
  disponible en el entorno")` cuando falta el binario, aunque alembic esté instalado en el intérprete que certifica.
- **NO_VENV_PRE_RESULT = FAIL.**

## Causa raíz

- TEST_MIGRATION_ROOT_CAUSE: 19 construcciones de ruta `BACKEND/.venv/bin/alembic` en 15 ficheros de prueba.
- E2E_HARNESS_ROOT_CAUSE: 1 construcción `base.BACKEND / ".venv/bin/alembic"` en `qa/e2e_corrida.py:393`.
- Mecanismo común: el script de consola `.venv/bin/alembic` lleva el shebang del intérprete del `.venv` histórico; la
  ruta fija decide el intérprete de la migración, no el proceso que certifica.
- **SHARED_ROOT_CAUSE = 1 · SHARED_MECHANISM = 1** (`CERTIFICATION_TOOL_USES_HARDCODED_HISTORICAL_VENV`).
