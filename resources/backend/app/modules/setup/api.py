"""Módulo de inicialización segura (FR-001-010): instalación, tenant,
empresa inicial y administrador, sin credenciales fijas."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import security
from app.core.database import get_db
from app.core.errors import ConflictError, KontrolError
from app.modules.identity_access import service as identity_service
from app.modules.identity_access.models import Permission, Role, RolePermission, UserRole
from app.modules.licensing import service as licensing_service
from app.modules.organization.models import Company, Installation, Tenant

router = APIRouter(prefix="/setup", tags=["setup"])


class SetupRequest(BaseModel):
    tenant_code: str = Field(min_length=2, max_length=64)
    tenant_name: str = Field(min_length=2, max_length=200)
    company_code: str = Field(min_length=1, max_length=64)
    company_legal_name: str = Field(min_length=1, max_length=255)
    company_rif: str = Field(min_length=5, max_length=20)
    admin_username: str = Field(min_length=3, max_length=64)
    admin_password: str = Field(min_length=10)


class SetupStatus(BaseModel):
    installation: str | None = None
    tenant: str | None = None
    company: str | None = None
    initialized: bool = False


def setup_status(db: Session) -> SetupStatus:
    installation = db.execute(select(Installation).limit(1)).scalars().first()
    tenant = db.execute(select(Tenant).limit(1)).scalars().first()
    company = db.execute(select(Company).limit(1)).scalars().first()
    return SetupStatus(
        installation=installation.installation_uuid if installation else None,
        tenant=str(tenant.id) if tenant else None,
        company=str(company.id) if company else None,
        initialized=bool(installation and tenant and company),
    )


def _bootstrap_roles(db: Session, tenant_id: str, actor_user_id: str) -> Role:
    """Crea o recupera el rol administrador con permisos base (segregación básica)."""
    existing = db.execute(select(Role).where(Role.code == "ADMIN", Role.company_id.is_(None))).scalars().first()
    if existing:
        return existing
    admin_role = Role(code="ADMIN", name="Administrador", protected=True, status="ACTIVE", created_by=actor_user_id)
    db.add(admin_role)
    db.flush()

    resources_actions = {
        "dashboard": ["view"],
        "organization": ["view", "create", "edit", "deactivate", "activate"],
        "users": ["view", "create", "edit", "deactivate", "activate"],
        "roles": ["view", "create", "edit"],
        "audit": ["view"],
        "license": ["view", "create", "edit", "approve"],
        "homologacion": ["view", "create", "edit", "approve"],
    }
    for resource, actions in resources_actions.items():
        for action in actions:
            perm = db.execute(select(Permission).where(Permission.resource == resource, Permission.action == action)).scalars().first()
            if not perm:
                perm = Permission(resource=resource, action=action, scope_type="COMPANY")
                db.add(perm)
                db.flush()
            db.add(RolePermission(role_id=str(admin_role.id), permission_id=str(perm.id)))
    db.flush()
    return admin_role


def initialize(db: Session, body: SetupRequest) -> dict:
    """Ejecuta el asistente seguro de inicialización (idempotente)."""
    status = setup_status(db)
    if status.initialized:
        raise ConflictError(code="SETUP_ALREADY_DONE", message="La instalación ya fue inicializada")

    # 1) Identidad de instalación
    installation = licensing_service.get_or_create_installation(db)

    # 2) Tenant (1:1 con instalación en la fundación, CL-02)
    tenant = Tenant(
        installation_id=str(installation.id),
        code=body.tenant_code,
        name=body.tenant_name,
        plan="MONO_COMPANY",
        status="ACTIVE",
    )
    db.add(tenant)
    db.flush()

    # 3) Empresa inicial
    company = Company(
        tenant_id=str(tenant.id),
        code=body.company_code,
        legal_name=body.company_legal_name,
        rif=body.company_rif,
        legal_type="JURIDICA",
        status="ACTIVE",
        created_by="setup",
    )
    db.add(company)
    db.flush()

    # 4) Administrador (cambio de contraseña obligatorio)
    errors = security.validate_password_policy(body.admin_password)
    if errors:
        raise KontrolError(
            code="PASSWORD_POLICY",
            message="La contraseña del administrador no cumple la política",
            field_errors={"admin_password": errors},
            status_code=422,
        )
    admin = identity_service.create_user(
        db,
        tenant_id=str(tenant.id),
        username=body.admin_username,
        email=None,
        password=body.admin_password,
        must_change_password=True,
        created_by="setup",
    )
    admin_role = _bootstrap_roles(db, str(tenant.id), str(admin.id))
    db.add(UserRole(user_id=str(admin.id), role_id=str(admin_role.id), company_id=str(company.id)))

    db.commit()
    return {
        "ok": True,
        "installation_id": installation.installation_uuid,
        "tenant_id": str(tenant.id),
        "company_id": str(company.id),
        "admin_user_id": str(admin.id),
        "must_change_password": True,
    }


@router.get("/status")
def status(db: Session = Depends(get_db)):
    return setup_status(db).model_dump()


@router.post("/initialize")
def initialize_endpoint(body: SetupRequest, db: Session = Depends(get_db)):
    # El bootstrap inicial no depende de la licencia (aún no existe Installation).
    # initialize() es idempotente: si la instalación ya está inicializada,
    # responde ConflictError (423/409) sin volver a crear datos.
    return initialize(db, body)
