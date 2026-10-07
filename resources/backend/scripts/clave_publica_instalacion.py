"""Clave PÚBLICA de identidad de esta instalación, para el enrolamiento fuera de banda en la Autoridad Central.

Uso (en el servidor de la instalación, con su configuración):
    python scripts/clave_publica_instalacion.py            # PEM de la clave pública
    python scripts/clave_publica_instalacion.py --huella   # además, la huella SHA-256 del DER

La deriva de la clave privada del volumen protegido (`KONTROL_INSTALLATION_VOLUME_PATH`), que no se
imprime ni se transmite: el operador entrega el PEM al vendor por un canal controlado y el vendor lo
vincula con `register-installation --public-key-file`. No hay ruta web para esto, a propósito.
"""

from __future__ import annotations

import os
import sys

from app.core.config import get_settings
from app.core.license_contract import load_private_key
from app.core.sync_auth_contract import public_key_fingerprint, public_key_pem_from_private


def main(argv: list[str]) -> int:
    ruta = os.path.join(get_settings().installation_volume_path, "installation_private_key.pem")
    try:
        with open(ruta, encoding="utf-8") as fh:
            clave = load_private_key(fh.read())
    except (OSError, ValueError, TypeError):
        print("no hay clave privada de instalación legible en el volumen protegido", file=sys.stderr)
        return 2
    publica = public_key_pem_from_private(clave)
    sys.stdout.write(publica)
    if "--huella" in argv:
        print(f"huella sha256: {public_key_fingerprint(publica)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
