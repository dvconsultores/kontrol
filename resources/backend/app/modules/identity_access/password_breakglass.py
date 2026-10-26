"""Rotura de cristal local de la contraseña: código de un solo uso para /reset-password.

Operación local del servidor, nunca expuesta por HTTP ni por el frontend. Uso:

    python -m app.modules.identity_access.password_breakglass --tenant CODE --username USER --confirm USER --salida RUTA

Sirve para el caso en que una persona no puede recuperar su contraseña por los
canales habituales: el operador del servidor emite un código de un solo uso
(caduca en 15 minutos) que entrega por un canal de confianza; la persona elige
su nueva contraseña en /reset-password. El operador nunca conoce la contraseña.

No es una ruta HTTP. Nunca imprime ni registra el token ni identificadores
internos.
"""

from __future__ import annotations

import argparse
import os
import sys

from sqlalchemy import select

from app.core.database import get_session_factory
from app.modules.identity_access import service as identity_service
from app.modules.organization.models import Tenant


def _descartar(fd: int, ruta: str) -> None:
    """Cierra el descriptor y borra el fichero de salida, ignorando errores."""
    os.close(fd)
    try:
        os.unlink(ruta)
    except OSError:
        pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.modules.identity_access.password_breakglass",
        description=(
            "Emite localmente un código de un solo uso para restablecer la "
            "contraseña de un usuario. Operación de rotura de cristal ejecutada "
            "en el servidor; no es una ruta HTTP."
        ),
    )
    parser.add_argument("--tenant", required=True, help="Código del tenant.")
    parser.add_argument("--username", required=True, help="Nombre de usuario afectado.")
    parser.add_argument(
        "--confirm",
        required=True,
        help="Debe repetir exactamente el nombre de usuario para confirmar.",
    )
    parser.add_argument(
        "--salida",
        required=True,
        help="Ruta del fichero donde se escribe el código (permisos 0600).",
    )
    args = parser.parse_args(argv)

    if args.confirm != args.username:
        print(
            "La confirmación no coincide con el usuario; no se cambió nada.",
            file=sys.stderr,
        )
        return 2

    try:
        fd = os.open(args.salida, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except OSError:
        print(
            "No se puede crear el fichero de salida (¿ya existe?); no se cambió nada.",
            file=sys.stderr,
        )
        return 2

    db = get_session_factory()()
    try:
        tenant = db.execute(
            select(Tenant).where(Tenant.code == args.tenant)
        ).scalar_one_or_none()
        if tenant is None:
            _descartar(fd, args.salida)
            print(
                "No se puede emitir un código para ese usuario; no se cambió nada.",
                file=sys.stderr,
            )
            return 1
        user = identity_service.get_user_by_username(
            db, str(tenant.id), args.username
        )
        if user is None or user.status != "ACTIVE":
            _descartar(fd, args.salida)
            print(
                "No se puede emitir un código para ese usuario; no se cambió nada.",
                file=sys.stderr,
            )
            return 1

        token = identity_service.issue_password_reset_token(
            db, user=user, source="CLI", request_id=None
        )
    except BaseException:
        _descartar(fd, args.salida)
        raise
    finally:
        db.close()

    try:
        os.write(fd, token.encode())
    except OSError:
        _descartar(fd, args.salida)
        print(
            "No se pudo escribir el código; el código emitido caducará sin usarse "
            "en 15 minutos. Vuelva a ejecutar la orden.",
            file=sys.stderr,
        )
        return 1
    os.close(fd)

    print(
        f"Código escrito en {args.salida}: caduca en 15 minutos y sirve una sola vez. "
        "Entréguelo por un canal de confianza."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
