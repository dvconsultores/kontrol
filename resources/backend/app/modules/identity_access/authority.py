"""Autoridad efectiva y techo de delegación (Spec 003, delta spec003-delegation-ceiling)."""

from __future__ import annotations

from typing import NoReturn

from sqlalchemy import exists, or_, select, text
from sqlalchemy.orm import Session

from app.core.company_context import accessible_company_ids
from app.core.errors import ConflictError, NotFoundError, PermissionDeniedError
from app.modules.identity_access.models import Permission, Role, RolePermission, User, UserRole
from app.modules.organization.models import Company
from app.shared import audit as audit_service

# Las constantes fijan la división de ADMIN (OD-DEL-10): ADMIN conserva solo la autoridad
# técnica y de seguridad; la de negocio vive en el rol protegido FUNCIONAL_COMPLETO.
#: Código del rol protegido ADMIN.
ADMIN_ROLE_CODE = "ADMIN"
#: Código del rol protegido FUNCIONAL_COMPLETO.
FUNCTIONAL_ROLE_CODE = "FUNCIONAL_COMPLETO"
#: Capacidades técnicas y de seguridad conservadas por ADMIN.
TECHNICAL_CAPABILITIES: frozenset[str] = frozenset({
    "dashboard:view", "organization:view", "organization:create", "organization:edit", "organization:deactivate",
    "organization:activate", "organization:delete", "organization:manage_structure", "users:view", "users:create", "users:edit",
    "users:deactivate", "users:activate", "users:mfa_reset", "roles:view", "roles:create", "roles:edit", "audit:view", "license:view",
    "license:create", "license:edit", "license:approve", "notificaciones:configure", "tareas:configure", "documentos:manage_types",
})
#: Capacidades exclusivas del rol de seguridad ADMIN.
SECURITY_ADMIN_CAPABILITIES: frozenset[str] = frozenset({"users:create", "roles:edit", "users:mfa_reset"})

#: Clave de bloqueo de autoridad por tenant (INV-DEL-12).
_BLOQUEO_AUTORIDAD = 7_003_041

_MENSAJES: dict[str, str] = {
    "AUTHORITY_CEILING_EXCEEDED": "No puede conceder ni gestionar una autoridad que usted no tiene.",
    "SELF_ESCALATION_FORBIDDEN": "No puede ampliar su propia autoridad.",
    "CROSS_SCOPE_DELEGATION_FORBIDDEN": "No puede conceder autoridad fuera de las empresas en las que la tiene.",
    "TARGET_OUT_OF_SCOPE": "Esa asignación está fuera de las empresas en las que usted tiene autoridad.",
    "LAST_SECURITY_ADMIN_REQUIRED": "La operación dejaría a la empresa sin ningún administrador de seguridad.",
}


def lock_tenant_authority(db: Session, tenant_id: str) -> None:
    """Serializa las mutaciones de autoridad de un tenant (INV-DEL-12)."""
    if db.get_bind().dialect.name == "postgresql":
        db.execute(
            text("SELECT pg_advisory_xact_lock(:clase, hashtext(:tenant))"),
            {"clase": _BLOQUEO_AUTORIDAD, "tenant": tenant_id},
        )


def role_capabilities(db: Session, role_id: str) -> set[str]:
    """Devuelve el conjunto de capacidades «recurso:acción» asociadas a un rol."""
    resultado = db.execute(
        select(Permission.resource, Permission.action)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == role_id)
    ).all()
    return {f"{recurso}:{accion}" for recurso, accion in resultado}


def _asignaciones(db: Session, user_id: str) -> list[tuple[str, str | None, bool]]:
    """Lista las asignaciones activas del usuario: (role_id, company_id, protected)."""
    filas = db.execute(
        select(UserRole.role_id, UserRole.company_id, Role.protected)
        .join(Role, Role.id == UserRole.role_id)
        .where(UserRole.user_id == user_id, Role.status == "ACTIVE")
    ).all()
    return [(str(role_id), company_id, bool(protected)) for role_id, company_id, protected in filas]


def effective_capabilities(
    db: Session, user: User, *, sin: tuple[str, str] | None = None
) -> set[str]:
    """Capacidades efectivas del usuario, excluyendo opcionalmente una asignación."""
    if user.status != "ACTIVE":
        return set()
    capacidades: set[str] = set()
    for role_id, _company_id, _protected in _asignaciones(db, str(user.id)):
        if sin is not None and sin[0] == str(user.id) and sin[1] == role_id:
            continue
        capacidades.update(role_capabilities(db, role_id))
    return capacidades


def effective_scope(db: Session, user: User, capability: str) -> set[str]:
    """Empresas accesibles en las que el usuario dispone de una capacidad concreta."""
    if user.status != "ACTIVE":
        return set()
    accesibles = set(accessible_company_ids(db, user))
    alcance: set[str] = set()
    for role_id, company_id, _protected in _asignaciones(db, str(user.id)):
        if capability not in role_capabilities(db, role_id):
            continue
        if company_id is None:
            alcance.update(accesibles)
        elif company_id in accesibles:
            alcance.add(company_id)
    return alcance


def _alcance_de_rol(db: Session, user: User, role_id: str) -> set[str]:
    """Empresas accesibles cubiertas por las asignaciones del rol indicado."""
    if user.status != "ACTIVE":
        return set()
    accesibles = set(accessible_company_ids(db, user))
    alcance: set[str] = set()
    for asignacion_role_id, company_id, _protected in _asignaciones(db, str(user.id)):
        if asignacion_role_id != role_id:
            continue
        if company_id is None:
            alcance.update(accesibles)
        elif company_id in accesibles:
            alcance.add(company_id)
    return alcance


def granted_scope(db: Session, target: User, company_id: str | None) -> set[str]:
    """Alcance de empresas que se concederán: la empresa indicada o todas las accesibles."""
    if company_id is not None:
        return {company_id}
    return set(accessible_company_ids(db, target))


def _denegar(
    db: Session,
    *,
    actor: User,
    code: str,
    status: int,
    entity_type: str,
    entity_id: str | None,
    role_code: str,
    excedidas: list[str],
    company_id: str | None,
    accion: str = "AUTHORITY_DELEGATION_DENIED",
) -> NoReturn:
    """Registra la denegación y lanza el error correspondiente."""
    db.rollback()
    audit_service.record_audit(
        db,
        action=accion,
        entity_type=entity_type,
        entity_id=entity_id,
        tenant_id=str(actor.tenant_id),
        user_id=str(actor.id),
        reason=code,
        evidence={
            "role_code": role_code,
            "capabilities_excedidas": excedidas,
            "company_id": company_id,
        },
    )
    db.commit()
    mensaje = _MENSAJES[code]
    if status == 403:
        raise PermissionDeniedError(code, mensaje)
    raise ConflictError(code=code, message=mensaje)


def check_can_assign(
    db: Session, *, actor: User, target: User, role: Role, company_id: str | None
) -> None:
    """Comprueba que el actor puede conceder el rol al destinatario en el alcance dado."""
    if role.company_id is not None:
        empresa_tenant = db.execute(
            select(Company.tenant_id).where(Company.id == role.company_id)
        ).scalar_one_or_none()
        if empresa_tenant is None or str(empresa_tenant) != str(actor.tenant_id):
            raise NotFoundError(code="ROLE_NOT_FOUND", message="Rol no encontrado")

    if role.status != "ACTIVE":
        raise ConflictError(code="ROLE_INACTIVE", message="El rol no está activo")

    propio = str(target.id) == str(actor.id)
    caps = role_capabilities(db, str(role.id))
    excedidas = sorted(caps - effective_capabilities(db, actor))
    if excedidas:
        _denegar(
            db,
            actor=actor,
            code="SELF_ESCALATION_FORBIDDEN" if propio else "AUTHORITY_CEILING_EXCEEDED",
            status=403,
            entity_type="UserRole",
            entity_id=None,
            role_code=role.code,
            excedidas=excedidas,
            company_id=company_id,
        )

    concedido = granted_scope(db, target, company_id)
    if role.protected and not concedido.issubset(_alcance_de_rol(db, actor, str(role.id))):
        _denegar(
            db,
            actor=actor,
            code="SELF_ESCALATION_FORBIDDEN" if propio else "AUTHORITY_CEILING_EXCEEDED",
            status=403,
            entity_type="UserRole",
            entity_id=None,
            role_code=role.code,
            excedidas=[],
            company_id=company_id,
        )

    for capacidad in sorted(caps):
        if not concedido.issubset(effective_scope(db, actor, capacidad)):
            _denegar(
                db,
                actor=actor,
                code="SELF_ESCALATION_FORBIDDEN" if propio else "CROSS_SCOPE_DELEGATION_FORBIDDEN",
                status=403,
                entity_type="UserRole",
                entity_id=None,
                role_code=role.code,
                excedidas=[],
                company_id=company_id,
            )


def check_can_manage_assignment(
    db: Session, *, actor: User, target: User, role: Role, company_id: str | None
) -> None:
    """Comprueba que el actor puede retirar la asignación indicada."""
    caps = role_capabilities(db, str(role.id))
    excedidas = sorted(caps - effective_capabilities(db, actor))
    if excedidas:
        _denegar(
            db,
            actor=actor,
            code="AUTHORITY_CEILING_EXCEEDED",
            status=403,
            entity_type="UserRole",
            entity_id=None,
            role_code=role.code,
            excedidas=excedidas,
            company_id=company_id,
        )

    alcance = granted_scope(db, target, company_id)
    if role.protected and not alcance.issubset(_alcance_de_rol(db, actor, str(role.id))):
        _denegar(
            db,
            actor=actor,
            code="AUTHORITY_CEILING_EXCEEDED",
            status=403,
            entity_type="UserRole",
            entity_id=None,
            role_code=role.code,
            excedidas=[],
            company_id=company_id,
        )

    for capacidad in sorted(caps):
        if not alcance.issubset(effective_scope(db, actor, capacidad)):
            _denegar(
                db,
                actor=actor,
                code="TARGET_OUT_OF_SCOPE",
                status=403,
                entity_type="UserRole",
                entity_id=None,
                role_code=role.code,
                excedidas=[],
                company_id=company_id,
            )


def check_can_create_role(
    db: Session,
    *,
    actor: User,
    code: str,
    permissions: list[str],
    company_id: str | None,
) -> None:
    """Comprueba que el actor puede crear un rol con las capacidades y alcance dados."""
    excedidas = sorted(set(permissions) - effective_capabilities(db, actor))
    if excedidas:
        _denegar(
            db,
            actor=actor,
            code="AUTHORITY_CEILING_EXCEEDED",
            status=403,
            entity_type="Role",
            entity_id=None,
            role_code=code,
            excedidas=excedidas,
            company_id=company_id,
        )

    if company_id is not None:
        requerido = {company_id}
    else:
        requerido = {
            str(c)
            for c in db.execute(
                select(Company.id).where(Company.tenant_id == actor.tenant_id)
            ).scalars()
        }

    for capacidad in sorted(set(permissions)):
        if not requerido.issubset(effective_scope(db, actor, capacidad)):
            _denegar(
                db,
                actor=actor,
                code="CROSS_SCOPE_DELEGATION_FORBIDDEN",
                status=403,
                entity_type="Role",
                entity_id=None,
                role_code=code,
                excedidas=[],
                company_id=company_id,
            )


def is_security_admin(
    db: Session, user: User, *, sin: tuple[str, str] | None = None
) -> bool:
    """Indica si el usuario posee las capacidades de administrador de seguridad."""
    return user.status == "ACTIVE" and SECURITY_ADMIN_CAPABILITIES.issubset(
        effective_capabilities(db, user, sin=sin)
    )


def would_remove_last_security_admin(
    db: Session, tenant_id: str, *, user_id: str, role_id: str
) -> bool:
    """Indica si retirar la asignación dejaría sin administrador de seguridad al tenant."""
    usuario = db.get(User, user_id)
    if usuario is None or not is_security_admin(db, usuario):
        return False
    if is_security_admin(db, usuario, sin=(user_id, role_id)):
        return False
    otros = db.execute(
        select(User).where(User.tenant_id == tenant_id, User.id != user_id)
    ).scalars()
    return not any(is_security_admin(db, otro) for otro in otros)


def check_last_security_admin(
    db: Session,
    *,
    actor: User,
    tenant_id: str,
    user_id: str,
    role: Role,
    company_id: str | None,
) -> None:
    """Deniega la operación si elimina al último administrador de seguridad."""
    if would_remove_last_security_admin(db, tenant_id, user_id=user_id, role_id=str(role.id)):
        _denegar(
            db,
            actor=actor,
            code="LAST_SECURITY_ADMIN_REQUIRED",
            status=409,
            entity_type="UserRole",
            entity_id=None,
            role_code=role.code,
            excedidas=[],
            company_id=company_id,
            accion="LAST_ADMIN_OPERATION_DENIED",
        )


def delegability(db: Session, actor: User, role: Role) -> str | None:
    """Devuelve el código de denegación si el actor no puede delegar el rol, o None."""
    caps = role_capabilities(db, str(role.id))
    if not caps.issubset(effective_capabilities(db, actor)):
        return "AUTHORITY_CEILING_EXCEEDED"
    if role.protected:
        asignaciones_rol = {
            role_id
            for role_id, _company_id, _protected in _asignaciones(db, str(actor.id))
        }
        if str(role.id) not in asignaciones_rol:
            return "AUTHORITY_CEILING_EXCEEDED"
    return None


def has_capability_in_company(db: Session, user: User, capability: str, company_id: str) -> bool:
    """La capacidad vale en esa empresa: está en un rol activo asignado con company_id nulo
    (todas las empresas a las que accede) o igual a ella (Spec 003, capacidad × empresa)."""
    return str(company_id) in effective_scope(db, user, capability)


def capabilities_in_company(db: Session, user: User, company_id: str) -> set[str]:
    """Capacidades que valen en esa empresa: las de los roles activos asignados con company_id nulo o igual a
    ella; vacío si el usuario no está activo o no accede a la empresa (Spec 003). Una sola consulta: el acceso va en la misma
    sentencia que `accessible_company_ids` (presupuesto de consultas de los listados)."""
    if user.status != "ACTIVE":
        return set()
    from app.modules.identity_access.models import UserScope

    company_access_exists = exists(
        select(Company.id).where(
            Company.id == str(company_id),
            Company.tenant_id == user.tenant_id,
        )
    )
    tiene_ambitos = exists(
        select(UserScope.id).where(
            UserScope.user_id == str(user.id),
            UserScope.company_id.is_not(None),
        )
    )
    company_in_scope = exists(
        select(UserScope.id).where(
            UserScope.user_id == str(user.id),
            UserScope.company_id == str(company_id),
        )
    )

    filas = db.execute(
        select(Permission.resource, Permission.action)
        .distinct()
        .select_from(UserRole)
        .join(Role, Role.id == UserRole.role_id)
        .join(RolePermission, RolePermission.role_id == Role.id)
        .join(Permission, Permission.id == RolePermission.permission_id)
        .where(
            UserRole.user_id == str(user.id),
            Role.status == "ACTIVE",
            or_(
                UserRole.company_id.is_(None),
                UserRole.company_id == str(company_id),
            ),
            company_access_exists,
            or_(~tiene_ambitos, company_in_scope),
        )
    ).all()
    return {f"{recurso}:{accion}" for recurso, accion in filas}


def tenant_wide_capabilities(db: Session, user: User) -> set[str]:
    """Capacidades que valen en TODAS las empresas del tenant (catálogos de todo el tenant, C4); vacío si el tenant no tiene empresas."""
    ids = db.execute(select(Company.id).where(Company.tenant_id == user.tenant_id)).scalars().all()
    if not ids:
        return set()
    return set.intersection(*(capabilities_in_company(db, user, str(cid)) for cid in ids))


def companies_with_capability(db: Session, user: User, capability: str) -> set[str]:
    """Empresas donde la capacidad vale; para acotar consultas (listas, bitácora)."""
    return effective_scope(db, user, capability)


def has_tenant_wide_capability(db: Session, user: User, capability: str) -> bool:
    """Autoridad de todo el tenant, la que exigen los catálogos que afectan a todas las empresas."""
    tenant_company_ids = {str(c) for c in db.execute(select(Company.id).where(Company.tenant_id == user.tenant_id)).scalars()}
    return bool(tenant_company_ids) and tenant_company_ids.issubset(effective_scope(db, user, capability))


def require_capability_in_company(db: Session, *, user: User, capability: str, company_id: str) -> None:
    """Exige la capacidad en una empresa concreta o lanza PermissionDeniedError."""
    if has_capability_in_company(db, user, capability, company_id):
        return
    db.rollback()
    audit_service.record_audit(db, action="COMPANY_SCOPE_DENIED", entity_type="Company", entity_id=str(company_id), tenant_id=str(user.tenant_id), company_id=str(company_id), user_id=str(user.id), reason="COMPANY_SCOPE_FORBIDDEN", evidence={"capability": capability, "company_id": str(company_id)})
    db.commit()
    raise PermissionDeniedError("COMPANY_SCOPE_FORBIDDEN", "No tiene esa autoridad en esta empresa.")


def require_capability(db: Session, *, user: User, capability: str, company_id: str) -> None:
    """Exige la capacidad en cualquier empresa y, después, en la empresa dada."""
    from app.modules.identity_access import service as identity_service

    permisos = identity_service.get_user_permissions(db, user)
    if capability not in permisos:
        raise PermissionDeniedError()
    require_capability_in_company(db, user=user, capability=capability, company_id=company_id)


def require_tenant_wide_capability(db: Session, *, user: User, capability: str) -> None:
    """Exige la capacidad en todas las empresas del tenant o lanza PermissionDeniedError."""
    if has_tenant_wide_capability(db, user, capability):
        return
    db.rollback()
    audit_service.record_audit(db, action="COMPANY_SCOPE_DENIED", entity_type="Tenant", entity_id=str(user.tenant_id), tenant_id=str(user.tenant_id), company_id=None, user_id=str(user.id), reason="COMPANY_SCOPE_FORBIDDEN", evidence={"capability": capability, "company_id": None})
    db.commit()
    raise PermissionDeniedError("COMPANY_SCOPE_FORBIDDEN", "No tiene esa autoridad en todas las empresas del tenant.")
