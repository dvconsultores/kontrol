# Órdenes canónicas (sin cambio durante clarify)
| Registro | Valor |
|---|---|
| `SQLITE_COMMAND` | desde `resources/backend/`: `.venv/bin/python -m pytest tests -q -p no:cacheprovider` (con `PYTHONDONTWRITEBYTECODE=1` en los ciclos recientes) |
| `POSTGRES_COMMAND` | ídem con `KONTROL_TEST_DB_URL=postgresql+psycopg2://postgres@localhost:55432/ktest` |
| `E2E_COMMAND` | desde la raíz: `resources/backend/.venv/bin/python qa/e2e-run.py --con-analizador` |
| `PYTEST_ADDOPTS` | `pyproject.toml` `[tool.pytest.ini_options] addopts = "-q"` (la orden canónica corre en `-qq`: sin línea de resumen; se cuenta la barra de progreso) |
| `CACHEPROVIDER` | desactivado (`-p no:cacheprovider`) |
| `SCANNER_PRECONDITION` | `eval "$(python qa/clamav_qa.py entorno)"` exporta `KONTROL_CLAMSCAN_PATH` y `KONTROL_CLAMAV_DB` (motor 1.4.3 en `<qa-cache>`; preflight ≈ 14,5 s con caché; aprovisionamiento ≈ 3 min 54 s una vez) |
| `DB_LIFECYCLE` | SQLite: `:memory:` + `StaticPool` por sesión de prueba, o fichero temporal por `motor_para_hilos` (eliminado en `finally`); PostgreSQL: un esquema `t_…` por prueba sobre `ktest` (PGLIFE), eliminado al terminar; E2E: base efímera por corrida |
| Versión | pytest 9.0.3 · Python 3.11 · SQLAlchemy 2.0.36 |
Equivalente compatible para el perfil por prueba: `-o addopts= -q --durations=0 -p no:cacheprovider` (misma colección y
mismo orden; `--durations` necesita que la sección de resumen no esté suprimida por `-qq`).
