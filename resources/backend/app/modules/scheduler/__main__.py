"""Orden canónica del planificador: `python -m app.modules.scheduler tick`.

# Spec 047 · Orden del planificador (ADR-D0-015)

La invoca el temporizador del sistema a través de `kontrol.py scheduler-tick`.
No acepta argumentos que elijan trabajo: el trabajo lo decide el registro.

Salida: una línea JSON. Códigos: `0` completado u omitido por solapamiento ·
`2` completado con errores de manejador · `1` fallo operacional.
"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.modules.scheduler")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("tick")
    parser.parse_args(argv)
    try:
        from app.core.database import get_session_factory, init_models
        from app.modules.scheduler.service import tick

        init_models()
        resultado = tick(get_session_factory())
    except Exception as error:  # sin base, sin registro: fallo operacional real
        print(json.dumps({"status": "FAILED", "error_code": type(error).__name__}))
        return 1
    print(json.dumps(resultado.as_dict()))
    return resultado.exit_code


if __name__ == "__main__":
    sys.exit(main())
