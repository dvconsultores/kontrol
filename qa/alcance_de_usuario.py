"""Declara en qué empresas opera un usuario. Autoridad única.

`UserScope` es la autoridad de acceso del producto —lo dice
`app/core/company_context.py:62`— y no tiene ni API ni interfaz: solo se escribe
desde aquí, desde `qa/`. Antes lo escribían dos guiones por su cuenta; ahora
pasan por esta función, porque dos maneras de conceder acceso son dos maneras de
concederlo mal.

Existe además el caso legítimo de **no** declarar alcance: sin ninguna fila, el
servidor admite todas las empresas del tenant, y eso está especificado —«es el
caso del administrador que crea la instalación»—. Este módulo no lo prohíbe: lo
deja fuera. Quien quiera un usuario sin restricción simplemente no lo llama, y
así la ausencia de alcance es una decisión escrita en el sitio donde se toma, no
un olvido.

Como orden de línea de comandos, es lo que el E2E invoca para que el usuario que
acaba de crear por API sea el usuario que su escenario declara:

    python qa/alcance_de_usuario.py DEMO check-abc <empresa-id> [<empresa-id>...]
"""

from __future__ import annotations

import sys
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session


def declarar(db: Session, *, tenant_code: str, username: str,
             empresas: Sequence[str]) -> list[str]:
    """Deja a `username` operando exactamente en `empresas`. Devuelve su alcance.

    Es aditivo e idempotente: completa lo que falte y no toca lo que esté,
    porque una base de QA acumula el trabajo de muchas ejecuciones y reescribir
    lo que ya está sería inventar un estado que nadie pidió.

    Y se niega a lo contradictorio: si el usuario ya opera en una empresa que
    esta llamada no pide, no escribe nada y falla. Un fixture que pide una
    empresa y obtiene dos no debe descubrirlo sesenta segundos después, en una
    pantalla equivocada.
    """
    from app.modules.identity_access.models import User, UserScope
    from app.modules.organization.models import Company, Tenant

    if not empresas:
        raise ValueError(
            "declarar() exige al menos una empresa: un usuario sin alcance alcanza todas "
            "las del tenant, y eso se decide no llamando a esta función")

    tenant = db.execute(select(Tenant).where(Tenant.code == tenant_code)).scalars().first()
    if tenant is None:
        raise RuntimeError(f"no existe el tenant {tenant_code!r}")
    u = db.execute(select(User).where(
        User.tenant_id == str(tenant.id), User.username == username)).scalars().first()
    if u is None:
        raise RuntimeError(f"no existe el usuario {username!r} en el tenant {tenant_code!r}")

    del_tenant = {str(c) for c in db.execute(
        select(Company.id).where(Company.tenant_id == str(tenant.id))).scalars().all()}
    ajenas = [c for c in empresas if c not in del_tenant]
    if ajenas:
        raise RuntimeError(
            f"{ajenas} no son empresas del tenant {tenant_code!r}: declarar alcance sobre una "
            "empresa ajena no concede nada y dejaría la prueba pasando por el motivo equivocado")

    ya = {s.company_id for s in db.execute(select(UserScope).where(
        UserScope.user_id == str(u.id))).scalars().all() if s.company_id}
    pedido = set(empresas)

    # Se comprueba **antes** de escribir. Validar después dejaba hecho el daño:
    # una petición contradictoria añadía su fila, fallaba a continuación y el
    # usuario quedaba operando en más empresas que las de cualquiera de las dos
    # peticiones. Lo encontró la propia prueba de contrato.
    sobra = ya - pedido
    if sobra:
        raise RuntimeError(
            f"{username!r} ya opera en {sorted(ya)} y se pide {sorted(pedido)}: "
            f"{sorted(sobra)} quedaría de más. No se escribe nada")

    for c in sorted(pedido - ya):
        db.add(UserScope(user_id=str(u.id), company_id=c))
    if pedido - ya:
        db.commit()
    return sorted(pedido)


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__, file=sys.stderr)
        return 2
    import os

    os.environ.setdefault("KONTROL_SECRET_KEY", "qa-secret-key-0123456789abcdef0123456789abcdef")
    os.environ.setdefault("KONTROL_ENVIRONMENT", "local")
    os.environ.setdefault("KONTROL_LOG_JSON", "false")

    from app.core.database import get_session_factory, init_models

    init_models()
    db = get_session_factory()()
    try:
        final = declarar(db, tenant_code=argv[0], username=argv[1], empresas=argv[2:])
    finally:
        db.close()
    print(" ".join(final))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
