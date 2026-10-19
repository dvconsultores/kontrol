# E2E con V2 (backend en CPython 3.13.15 con las dependencias de despliegue + python-magic)

- **Orden:** `<V2>/bin/python qa/e2e-run.py --con-analizador`, corrida `r20261019t212411p848650n4029fd`.
- **Resultado:** rc 0 · **284/0/0** · suite 270,8 s · limpieza LIMPIA · `protegidas_sin_cambios` True.
- **`backend.log`:** 0 `QueuePool limit`, 0 «Error no controlado», 0 respuestas 500.
- **Equipo:**
  - Precheck: 6,2 GB disponibles, swap 1,9 GB, carga 0,65, puertos libres, 0 clamscan.
  - Muestreo: 281 muestras; memoria mínima 1118 MB, swap máxima 5024 MB, carga máxima 9,87, hasta 5 clamscan.

**Intérprete, verificado por construcción** (el registro de la corrida no lo anota):
- Con `sys.executable`, es decir V2: el backend (`qa/e2e_corrida.py:383`), la autoridad central (`:400`), la migración
  de la base de la corrida (`qa/e2e_base.py:251`) y la siembra (`KONTROL_E2E_PYTHON = sys.executable`, `:311`).
- **Excepción, E2E_HARNESS_INTERPRETER_FIXED parcial:** la migración de la autoridad central usa `.venv/bin/alembic`
  (`qa/e2e_corrida.py:393`), es decir V0. Alembic 1.14.0 y SQLAlchemy 2.0.36 son los mismos en los dos entornos.
