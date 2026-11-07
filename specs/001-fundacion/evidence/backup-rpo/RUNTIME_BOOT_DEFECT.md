# RUNTIME-LOCK-API-BOOT-FAILURE

Medido el 2026-11-07 en `.venv` con Python 3.13.5 y `requirements-test.lock` (runtime exacto de `requirements.lock`).

- `fastapi 0.141.1`, `starlette 1.9.0`.
- `python -c "import app.main"`: RC 1, `ImportError: cannot import name 'get_flat_dependant' from 'fastapi.dependencies.utils'`.
- Origen: `app/core/query_contract.py:18`, introducido por `f24e74e` (2026-10-28), posterior a la última certificación contra el lock (2026-10-24).
- `Dockerfile.backend` instala `requirements.lock`, por lo que la imagen de producción resultante fallaría al arrancar (DERIVED: sin Docker en este puesto).
- Suite SQLite con el lock: 9 ficheros sin recolectar más `test_read_catalog_completeness.py`; se detuvo al alcanzar `--maxfail=400`.
- No se detectó antes porque las corridas de P1 usan otro entorno y SPEC054 sigue sin corrida oficial.
