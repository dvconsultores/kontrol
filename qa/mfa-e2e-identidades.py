"""Siembra identidades MFA por worker para la corrida E2E canónica.

La siembra base (`qa/pg-e2e-seed.py`) crea un único usuario por identidad
(`admin`, `ua`, `ub`, `uab`, `uc`). Con MFA obligatorio, la antirrepetición
TOTP admite un único login por usuario y paso de 30 s: seis workers
ejecutándose en paralelo compartirían el mismo usuario y colisionarían.
Por eso la corrida fija `--workers=6` y este guion siembra, por cada usuario
base, seis clones `usuario_w{k}` con los mismos roles y el mismo alcance.

No crea factores MFA: el arnés da de alta cada factor por la API real. Es
idempotente (no borra nada y completa lo que falte).

Uso:
    KONTROL_DB_URL=postgresql+psycopg2://... PYTHONPATH=resources/backend \
        resources/backend/.venv/bin/python qa/mfa-e2e-identidades.py
"""

from __future__ import annotations

import json
import os

os.environ.setdefault("KONTROL_SECRET_KEY", "qa-secret-key-0123456789abcdef0123456789abcdef")
os.environ.setdefault("KONTROL_ENVIRONMENT", "local")
os.environ.setdefault("KONTROL_LOG_JSON", "false")

from sqlalchemy import select  # noqa: E402

from app.core.database import get_session_factory, init_models  # noqa: E402
from app.modules.identity_access import service as identity_service  # noqa: E402
from app.modules.identity_access.models import User, UserRole, UserScope  # noqa: E402
from app.modules.organization.models import Tenant  # noqa: E402

import alcance_de_usuario  # noqa: E402

#: La corrida canónica fija `--workers=6`.
WORKERS = 6

#: Usuarios base de los que clonar identidades por worker.
BASES = (("DEMO", "admin"), ("DEMO", "admintenant"), ("DEMO", "ua"), ("DEMO", "ub"),
         ("DEMO", "uab"), ("DEMO2", "uc"))

PASSWORD = os.environ.get("KONTROL_E2E_PASSWORD", "Kontrol2026Segura!")


def main() -> None:
    init_models()
    db = get_session_factory()()
    try:
        for codigo, usuario in BASES:
            tenant = db.execute(select(Tenant).where(
                Tenant.code == codigo)).scalars().first()
            if tenant is None:
                raise SystemExit(
                    f"la siembra base no ha creado el tenant {codigo}")

            tenant_id = str(tenant.id)

            base = db.execute(select(User).where(
                User.tenant_id == tenant_id, User.username == usuario)).scalars().first()
            if base is None:
                raise SystemExit(
                    f"la siembra base no ha creado {codigo}/{usuario}")

            roles = db.execute(select(UserRole).where(
                UserRole.user_id == str(base.id))).scalars().all()
            alcance = db.execute(select(UserScope).where(
                UserScope.user_id == str(base.id))).scalars().all()

            for k in range(WORKERS):
                clon = f"{usuario}_w{k}"
                usuario_clon = db.execute(select(User).where(
                    User.tenant_id == tenant_id, User.username == clon)).scalars().first()
                if usuario_clon is None:
                    usuario_clon = identity_service.create_user(
                        db, tenant_id=tenant_id, username=clon, email=f"{clon}@qa.test",
                        password=PASSWORD, must_change_password=False, created_by=None)
                    db.flush()

                for rol in roles:
                    tiene_rol = db.execute(select(UserRole).where(
                        UserRole.user_id == str(usuario_clon.id),
                        UserRole.role_id == str(rol.role_id),
                        UserRole.company_id == rol.company_id)).scalars().first()
                    if tiene_rol is None:
                        db.add(UserRole(
                            user_id=str(usuario_clon.id),
                            role_id=str(rol.role_id),
                            company_id=rol.company_id))

                if alcance:
                    companies = [str(f.company_id) for f in alcance]
                    alcance_de_usuario.declarar(
                        db, tenant_code=codigo, username=clon, empresas=companies)

        db.commit()
        print(json.dumps({"identidades": WORKERS * len(BASES)}))
    finally:
        db.close()


if __name__ == "__main__":
    main()
