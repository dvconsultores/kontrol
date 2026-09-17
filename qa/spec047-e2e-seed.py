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

import n6_world  # noqa: E402  (mismo directorio que este guion)
from sqlalchemy import select  # noqa: E402

from app.core.database import get_session_factory, init_models  # noqa: E402
from app.modules.identity_access.models import User, UserScope  # noqa: E402
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
            db.add(UserScope(user_id=str(admin.id), company_id=str(d1.id)))
        db.commit()
        print({"tenant": str(tenant.id), "d1": str(d1.id), "d2": str(d2.id), "admin_scoped_to": "D1"})
    finally:
        db.close()


if __name__ == "__main__":
    main()
