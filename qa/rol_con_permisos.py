"""Un usuario de QA con exactamente los permisos indicados (Spec 003, E2E del techo de delegación).

Lo usa el E2E para probar la autorización desde el lado de quien tiene el techo de delegación: no existe una API
de alta de roles con permisos, así que el rol se escribe en la base de la corrida, igual que
`qa/alcance_de_usuario.py` escribe el alcance. Idempotente: si el usuario ya existe con ese rol,
no toca nada.

Uso (contra la base del E2E, nunca contra producción):
    KONTROL_DB_URL=... PYTHONPATH=resources/backend \
        resources/backend/.venv/bin/python qa/rol_con_permisos.py <tenant> <usuario> <empresa> <permiso>...
Escribe en la salida el id del usuario.
"""
from __future__ import annotations

import os
import sys

os.environ.setdefault("KONTROL_SECRET_KEY", "qa-secret-key-0123456789abcdef0123456789abcdef")
os.environ.setdefault("KONTROL_ENVIRONMENT", "local")
os.environ.setdefault("KONTROL_LOG_JSON", "false")

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.database import get_session_factory, init_models  # noqa: E402
from app.modules.identity_access import service as identity_service  # noqa: E402
from app.modules.identity_access.models import Permission, Role, RolePermission, User, UserRole, UserScope  # noqa: E402
from app.modules.organization.models import Company, Tenant  # noqa: E402

CLAVE = os.environ.get("KONTROL_E2E_PASSWORD")


def crear(db: Session, *, tenant_code: str, username: str, empresa_code: str, con: set[str]) -> str:
    """Deja a `username` con un rol que lleva exactamente `con`, operando en `empresa_code`."""
    if os.environ.get("KONTROL_ENVIRONMENT", "local") not in ("local", "dev", "qa"):
        raise RuntimeError("este guion solo escribe en entornos de QA")
    if not CLAVE:
        raise RuntimeError("KONTROL_E2E_PASSWORD es obligatoria")
    tenant = db.execute(select(Tenant).where(Tenant.code == tenant_code)).scalars().one()
    empresa = db.execute(select(Company).where(Company.tenant_id == tenant.id, Company.code == empresa_code)).scalars().one()
    existente = db.execute(select(User).where(User.tenant_id == str(tenant.id), User.username == username)).scalars().first()
    if existente is not None:
        return str(existente.id)
    usuario = identity_service.create_user(db, tenant_id=str(tenant.id), username=username,
                                           email=f"{username}@kontrol-qa.com", password=CLAVE,
                                           must_change_password=False, created_by=None)
    rol = Role(code=f"QA-CON-{username}".upper()[:64], name=f"QA con permisos ({username})", protected=False,
               status="ACTIVE")
    db.add(rol)
    db.flush()
    otorgados: set[str] = set()
    for p in db.query(Permission).all():
        clave = f"{p.resource}:{p.action}"
        if clave not in con:
            continue
        otorgados.add(clave)
        db.add(RolePermission(role_id=str(rol.id), permission_id=str(p.id)))
    if otorgados != con:
        raise RuntimeError(f"el catálogo no trae {sorted(con - otorgados)}")
    db.add(UserRole(user_id=str(usuario.id), role_id=str(rol.id), company_id=None))
    db.add(UserScope(user_id=str(usuario.id), company_id=str(empresa.id)))
    db.commit()
    return str(usuario.id)


def main(argv: list[str]) -> int:
    if len(argv) < 4:
        print("uso: rol_con_permisos.py <tenant> <usuario> <empresa> <permiso>...", file=sys.stderr)
        return 2
    init_models()
    db = get_session_factory()()
    try:
        print(crear(db, tenant_code=argv[0], username=argv[1], empresa_code=argv[2], con=set(argv[3:])))
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
