"""La orden de alembic de las pruebas: el intérprete que ejecuta pytest.

Certificar con un intérprete y migrar con otro no es certificar (Spec 054,
CERTIFICATION-ALEMBIC-INTERPRETER-PARITY): las pruebas no ejecutan alembic por una ruta fija a un
entorno virtual ni buscan `alembic`, `python` o `python3` en el PATH.
"""
from __future__ import annotations

import sys


def orden_alembic(*argumentos: str) -> list[str]:
    """`alembic <argumentos>` ejecutado por `sys.executable`, el intérprete de esta suite."""
    return [sys.executable, "-m", "alembic", *argumentos]
