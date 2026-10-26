"""Recifrado de los factores MFA tras rotar la clave del anillo.

Operación local del servidor. Uso:

    python -m app.modules.identity_access.mfa_rekey

Recifra con la primera clave de ``KONTROL_MFA_KEYS`` los factores que estén
cifrados con otra clave del anillo. Tras ejecutarlo, la clave vieja puede
retirarse del anillo cuando el recuento de factores que la usan sea 0.

No es una ruta HTTP. No imprime secretos, códigos ni identificadores internos.
"""

from __future__ import annotations

import argparse
import sys

from app.core.database import get_session_factory
from app.modules.identity_access.mfa_crypto import MfaUnavailable
from app.modules.identity_access.mfa_service import rekey_factors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.modules.identity_access.mfa_rekey",
        description=(
            "Recifra los factores MFA con la primera clave de KONTROL_MFA_KEYS. "
            "Operación local del servidor; no es una ruta HTTP."
        ),
    )
    parser.parse_args(argv)

    factory = get_session_factory()
    db = factory()
    try:
        rekeyed = rekey_factors(db)
    except MfaUnavailable:
        print(
            "KONTROL_MFA_KEYS no configurada o sin la clave antigua; no se cambió nada.",
            file=sys.stderr,
        )
        return 1
    finally:
        db.close()

    print(f"recifrados={rekeyed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
