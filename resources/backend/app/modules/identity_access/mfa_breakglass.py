"""Rotura de cristal del MFA: reset local del segundo factor de un usuario.

Operación local del servidor, nunca expuesta por HTTP ni por el frontend ni como
bypass persistente. Uso:

    python -m app.modules.identity_access.mfa_breakglass --tenant CODE --username USER --confirm USER

Sirve para el caso en que un usuario (por ejemplo el último administrador) ha
perdido su factor y sus códigos de recuperación y hay que restablecer su MFA.
Deja auditoría ``MFA_RESET_BREAKGLASS`` con fuente CLI y revoca todas las
sesiones del usuario afectado. Tras ejecutarlo, el usuario deberá darse de alta
de nuevo en su siguiente inicio de sesión.

No es una ruta HTTP. No imprime secretos, códigos ni identificadores internos.
"""

from __future__ import annotations

import argparse
import sys

from app.core.database import get_session_factory
from app.modules.identity_access.mfa_service import breakglass_reset


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.modules.identity_access.mfa_breakglass",
        description=(
            "Restablece localmente el segundo factor de un usuario. Operación de "
            "rotura de cristal ejecutada en el servidor; no es una ruta HTTP."
        ),
    )
    parser.add_argument("--tenant", required=True, help="Código del tenant.")
    parser.add_argument("--username", required=True, help="Nombre de usuario afectado.")
    parser.add_argument(
        "--confirm",
        required=True,
        help="Debe repetir exactamente el nombre de usuario para confirmar.",
    )
    args = parser.parse_args(argv)

    if args.confirm != args.username:
        print(
            "La confirmación no coincide con el usuario; no se cambió nada.",
            file=sys.stderr,
        )
        return 2

    factory = get_session_factory()
    db = factory()
    try:
        breakglass_reset(db, tenant_code=args.tenant, username=args.username)
    except LookupError:
        print(
            "No existe el tenant, el usuario o su segundo factor activo; no se cambió nada.",
            file=sys.stderr,
        )
        return 1
    finally:
        db.close()

    print(
        f"MFA restablecido para {args.username}: debe darse de alta en su próximo inicio de sesión."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
