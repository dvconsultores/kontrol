"""Corre la suite E2E contra una base PostgreSQL nueva, que se elimina al terminar.

Es la manera de certificar: cada corrida crea su base (`kontrol_e2e_test_<run>`), la migra a
la cabeza, la siembra, levanta contra ella el backend y Vite, ejecuta Playwright y lo
elimina todo, pase o falle. `kaud` no participa. El detalle está en `qa/e2e_corrida.py`.

Uso (PostgreSQL de QA en marcha: `bash qa/pg-provision.sh start`):
    resources/backend/.venv/bin/python qa/e2e-run.py
    resources/backend/.venv/bin/python qa/e2e-run.py -- e2e/notifications.spec.ts --trace retain-on-failure
    resources/backend/.venv/bin/python qa/e2e-run.py --sin-frontend --orden qa/repro-almacenes-listado.py

El código de salida es el de la suite; 70 si la preparación falló; 75 si la suite pasó y la
limpieza no. La evidencia queda en `qa/e2e-runs/<run>/`.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import e2e_corrida  # noqa: E402

if __name__ == "__main__":
    sys.exit(e2e_corrida.main())
