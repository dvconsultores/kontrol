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
from app.modules.identity_access.authority import ADMIN_ROLE_CODE, FUNCTIONAL_ROLE_CODE, TECHNICAL_CAPABILITIES
from app.modules.identity_access.models import Permission, Role, RolePermission, UserRole
from app.modules.licensing import service as licensing_service
from app.modules.organization.models import Company, Installation, Tenant
from app.shared.audit import record_audit

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
    installation = db.execute(
        select(Installation).order_by(Installation.created_at, Installation.id).limit(1)
    ).scalars().first()
    tenant = db.execute(select(Tenant).limit(1)).scalars().first()
    company = db.execute(select(Company).limit(1)).scalars().first()
    return SetupStatus(
        installation=installation.installation_uuid if installation else None,
        tenant=str(tenant.id) if tenant else None,
        company=str(company.id) if company else None,
        initialized=bool(installation and tenant and company),
    )


# Catálogo de capacidades del arranque (recurso → acciones). Fuente única también para la
# instantánea de la UI (Spec 003, ADR-018).
CATALOGO_DE_PERMISOS: dict[str, list[str]] = {
    "dashboard": ["view"],
    # `delete` y `manage_structure` los añade la Spec 008 al recurso
    # existente: se extiende el modelo de la Spec 003, no se crea otro.
    "organization": ["view", "create", "edit", "deactivate", "activate", "delete", "manage_structure"],
    "users": ["view", "create", "edit", "deactivate", "activate", "mfa_reset"],
    "roles": ["view", "create", "edit"],
    "audit": ["view"],
    "license": ["view", "create", "edit", "approve"],
    "homologacion": ["view", "create", "edit", "approve"],
    "maestros": ["view", "create", "edit", "deactivate"],
    "compras": ["view", "create", "approve", "quality", "apply"],
    # `submit` lo añade la Spec 030: emitir un pedido no es aprobarlo.
    "ventas": ["view", "create", "submit", "approve", "quality", "apply"],
    # `confirm` lo añade la Spec 021: confirmar el inventario recibido no es
    # aprobarlo ni moverlo; es la liberación formal que `R-D0-10-4` exige.
    "inventario": ["view", "create", "approve", "transition", "reserve", "confirm"],
    "tesoreria": ["view", "create", "approve"],
    "fiscal": ["view", "create", "approve"],
    "regulatorio": ["view", "create", "approve"],
    "reportes": ["view", "export"],
    "aprobaciones": ["view", "create", "edit", "approve", "delegate", "configure"],
    # Recurso nuevo de la Spec 046. Extiende el modelo de la Spec 003.
    "documentos": ["view", "create", "edit", "upload", "download", "link",
                   "deactivate", "delete", "manage_types"],
    # Recurso nuevo de la Spec 012. Tener el permiso **no** es tener acceso
    # a una empresa: `comercial:create` dice que el usuario puede crear
    # maestros comerciales, no en cuál. Eso lo decide `CompanyContext`.
    "comercial": ["view", "create", "edit", "manage_policies", "publish", "archive"],
    # Recursos nuevos de la Spec 047. Ver lo propio —notificaciones recibidas,
    # tareas donde se es candidato— no pide permiso de recurso: lo autoriza la
    # fila de destinatario y el contexto de empresa (CL-047-05).
    "notificaciones": ["configure"],
    "tareas": ["view", "assign", "complete", "configure"],
    "alertas": ["view"],
    # Línea de Gobierno (GOV-0-01): capacidades funcionales del ente (PDD-GOV0-01).
    "gobierno_ente": ["view", "create", "edit", "activate"],
    # GOV-0-02: estructura organizativa por ejercicio (PDD-ORG02-01).
    "gobierno_estructura": ["view", "edit", "publish", "close"],
    # GOV-0-03: cargos con competencias y límites de firma/aprobación (PDD-ORG03-01).
    "gobierno_cargos": ["view", "edit", "publish"],
    # DOC-02: actos administrativos con autoridad, motivación y eficacia (PDD-DOC02-01).
    "gobierno_actos": ["view", "edit", "issue", "annul"],
    # DOC-04: notificaciones administrativas con constancia de recepción (PDD-DOC04-04).
    "gobierno_notificaciones": ["view", "edit", "record"],
    # ORG-07: matriz auditable de autoridad, solo lectura (OD-ORG07-03).
    "gobierno_autoridad": ["view"],
    # CTL-04: consulta y muestreo read-only del auditor (OD-CTL04-03).
    "gobierno_auditoria": ["view", "sample"],
    # CTL-06: hallazgos, recomendaciones y planes de acción correctiva (OD-CTL06-02).
    "gobierno_hallazgos": ["view", "manage", "verify"],
    # DOC-08: paquetes de auditoría exportables con índice, huellas y referencias cruzadas (OD-DOC08-04).
    "gobierno_paquetes": ["view", "generate"],
    # CTL-01: matriz de segregación de funciones con detección previa (OD-CTL01-04).
    "gobierno_sod": ["view", "manage", "activate"],
    # TRE-01: cuentas bancarias públicas (OD-TRE01-07).
    "gobierno_cuentas": ["view", "manage", "activate"],
    # TRE-02: programación financiera (OD-TRE02-04).
    "gobierno_caja": ["view", "manage", "activate"],
    # CTL-10: controles materiales de cierre (OD-CTL10-04).
    "gobierno_cierre": ["view", "manage", "activate"],
    # ORG-04: ocupación de cargos (OD-ORG04-08).
    "gobierno_ocupacion": ["view", "manage", "activate", "revoke"],
    "gobierno_identidad": ["view", "manage", "activate", "revoke"],
    "gobierno_comisiones": ["view", "manage", "activate", "close"],
    "gobierno_expedientes": ["view", "manage", "close"],
    "gobierno_ofertas": ["view", "receive"],
    "gobierno_evaluacion": ["view", "criteria", "open", "evaluate"],
    "gobierno_decision": ["view", "recommend", "decide"],
    "gobierno_garantias": ["view", "manage", "release", "execute"],
}


def _bootstrap_roles(db: Session, tenant_id: str, actor_user_id: str) -> Role:
    """Crea o completa los dos roles protegidos de toda la instalación.

    ADMIN recibe EXACTAMENTE las capacidades técnicas y FUNCIONAL_COMPLETO recibe
    exactamente el resto del catálogo (OD-DEL-10). Es idempotente: los permisos
    faltantes se añaden y, si ADMIN ya existía con capacidades funcionales, se le
    quitan. Devuelve ADMIN.
    """
    resources_actions = CATALOGO_DE_PERMISOS
    def _rol_protegido(db: Session, code: str, name: str, actor_user_id: str) -> Role:
        existing = db.execute(select(Role).where(Role.code == code, Role.company_id.is_(None), Role.protected.is_(True))).scalars().first()
        if existing:
            return existing
        role = Role(code=code, name=name, protected=True, status="ACTIVE", created_by=actor_user_id)
        db.add(role)
        db.flush()
        return role

    admin_role = _rol_protegido(db, ADMIN_ROLE_CODE, "Administrador", actor_user_id)
    funcional_role = _rol_protegido(db, FUNCTIONAL_ROLE_CODE, "Funcional completo", actor_user_id)

    for resource, actions in resources_actions.items():
        for action in actions:
            perm = db.execute(select(Permission).where(Permission.resource == resource, Permission.action == action)).scalars().first()
            if not perm:
                perm = Permission(resource=resource, action=action, scope_type="COMPANY")
                db.add(perm)
                db.flush()
            clave = f"{resource}:{action}"
            destino = admin_role if clave in TECHNICAL_CAPABILITIES else funcional_role
            otro = funcional_role if destino is admin_role else admin_role
            already = db.execute(select(RolePermission).where(
                RolePermission.role_id == str(destino.id),
                RolePermission.permission_id == str(perm.id),
            )).scalars().first()
            if not already:
                db.add(RolePermission(role_id=str(destino.id), permission_id=str(perm.id)))
            duplicado = db.execute(select(RolePermission).where(
                RolePermission.role_id == str(otro.id),
                RolePermission.permission_id == str(perm.id),
            )).scalars().first()
            if duplicado:
                db.delete(duplicado)
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
    # OD-DEL-10/12: la autoridad funcional se concede de forma explícita y con alcance de tenant.
    funcional_role = db.execute(select(Role).where(Role.code == FUNCTIONAL_ROLE_CODE, Role.company_id.is_(None), Role.protected.is_(True))).scalars().one()
    asignacion_admin = UserRole(user_id=str(admin.id), role_id=str(admin_role.id), company_id=None)
    asignacion_funcional = UserRole(user_id=str(admin.id), role_id=str(funcional_role.id), company_id=None)
    db.add(asignacion_admin)
    db.add(asignacion_funcional)
    db.flush()
    record_audit(db, action="ROLE_ASSIGNED", entity_type="UserRole", entity_id=str(asignacion_admin.id), tenant_id=str(tenant.id), user_id=None, after={"role_id": str(admin_role.id), "user_id": str(admin.id), "company_id": None}, source="SETUP", reason="OD-DEL-10")
    record_audit(db, action="ROLE_ASSIGNED", entity_type="UserRole", entity_id=str(asignacion_funcional.id), tenant_id=str(tenant.id), user_id=None, after={"role_id": str(funcional_role.id), "user_id": str(admin.id), "company_id": None}, source="SETUP", reason="OD-DEL-10")

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
