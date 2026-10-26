"""Siembra adicional de la Spec 047 para el E2E sobre PostgreSQL.

Se ejecuta **después** de `qa/pg-e2e-seed.py`. Añade una segunda empresa (D2) al
tenant DEMO para que el E2E de la 047 pueda demostrar que lo de una empresa no se
ve ni se cuenta en otra.

El administrador de la siembra canónica queda con alcance explícito solo en D1:
así sigue operando en una única empresa y el resto de la cadena E2E no cambia de
comportamiento. El usuario que crea cada ejecución de la 047 no tiene alcance
declarado y alcanza las dos.

Uso:
    KONTROL_DB_URL=postgresql+psycopg2://... PYTHONPATH=resources/backend \
        resources/backend/.venv/bin/python qa/spec047-e2e-seed.py
"""

from __future__ import annotations

import os

os.environ.setdefault("KONTROL_SECRET_KEY", "qa-secret-key-0123456789abcdef0123456789abcdef")
os.environ.setdefault("KONTROL_ENVIRONMENT", "local")
os.environ.setdefault("KONTROL_LOG_JSON", "false")

import alcance_de_usuario  # noqa: E402  (mismo directorio que este guion)
import n6_world  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.core.database import get_session_factory, init_models  # noqa: E402
from app.modules.identity_access import service as identity_service  # noqa: E402
from app.modules.identity_access.models import Role, User, UserRole, UserScope  # noqa: E402
from app.modules.organization.models import Company, Tenant  # noqa: E402


def main() -> None:
    init_models()
    db = get_session_factory()()
    try:
        tenant = db.execute(select(Tenant).where(Tenant.code == "DEMO")).scalars().one()
        d1 = db.execute(select(Company).where(Company.tenant_id == tenant.id, Company.code == "D1")).scalars().one()
        # La segunda empresa la describe `qa/n6_world.py`, no este guion. Antes
        # la definían dos guiones por su cuenta —este y el arranque de N6— con
        # distinto nombre y distinto RIF para el mismo `(tenant, code)`, y cuál
        # quedaba dependía de cuál corriera último.
        d2 = n6_world.empresa(db, tenant, **n6_world.EMPRESA_B)
        admin = db.execute(select(User).where(User.tenant_id == tenant.id, User.username == "admin")).scalars().one()
        ambitos = db.execute(select(UserScope).where(UserScope.user_id == str(admin.id))).scalars().all()
        if not ambitos:
            # El acceso a una empresa lo concede `qa/alcance_de_usuario.py`, aquí
            # y en cualquier otro sitio: dos maneras de concederlo son dos
            # maneras de concederlo mal.
            alcance_de_usuario.declarar(db, tenant_code="DEMO", username="admin",
                                        empresas=[str(d1.id)])
        # Un administrador de QA de todo el tenant para preparar autoridad que abarca D1 y D2: con el techo de delegación, `admin` (solo D1) ya no
        # puede concederla (Spec 003).
        clave = n6_world.PASS  # La misma fuente que el resto de la siembra N6 (deuda TEST-FIXTURE-PASSWORD-LITERAL aparte).
        admintenant = db.execute(
            select(User).where(User.tenant_id == tenant.id, User.username == "admintenant")
        ).scalar_one_or_none()
        if admintenant is None:
            admintenant = identity_service.create_user(
                db, tenant_id=str(tenant.id), username="admintenant",
                email="admintenant@kontrol-qa.com", password=clave,
                must_change_password=False, created_by=None)
            db.flush()
        for code in ("ADMIN", "FUNCIONAL_COMPLETO"):
            rol = db.execute(
                select(Role).where(Role.code == code, Role.company_id.is_(None), Role.protected.is_(True))
            ).scalars().one()
            tiene = db.execute(
                select(UserRole).where(UserRole.user_id == str(admintenant.id), UserRole.role_id == str(rol.id))
            ).scalar_one_or_none()
            if tiene is None:
                db.add(UserRole(user_id=str(admintenant.id), role_id=str(rol.id), company_id=None))
        db.commit()
        print({"tenant": str(tenant.id), "d1": str(d1.id), "d2": str(d2.id), "admin_scoped_to": "D1"})
    finally:
        db.close()


if __name__ == "__main__":
    main()
