"""Política MFA por capacidades para el módulo de identidad y acceso.

Clasifica el nivel de riesgo de un usuario en tres clases —
PRIVILEGED / SENSITIVE / STANDARD — a partir del **conjunto efectivo de
permisos** y de los códigos de rol protegidos, nunca del nombre del rol
(Spec 002/003, OQ-MFA-1 = A).

La regla es código versionado y no configuración: un interruptor que
permitiera degradar la clasificación sería un vector de degradación del
control de acceso. Un permiso nuevo sin clasificar se considera SENSITIVE y,
por tanto, hace fallar MFA-G00 hasta que se clasifique explícitamente.

La evidencia de cada clase está en
``specs/001-fundacion/spec002-mfa-privileged-roles-delta.md`` §4.1–§4.2.
"""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.identity_access.models import Permission, Role, RolePermission, User, UserRole

PRIVILEGED = "PRIVILEGED"
SENSITIVE = "SENSITIVE"
STANDARD = "STANDARD"

# --- PRIVILEGIADO -----------------------------------------------------------
# Capacidades que otorgan control directo sobre identidades, roles,
# licencias, estructura organizativa y configuración de aprobaciones.
PRIVILEGED_PERMISSIONS: frozenset[str] = frozenset(
    {
        # users · gestión de identidades y recuperación de MFA
        "users:create",
        "users:edit",
        "users:deactivate",
        "users:activate",
        "users:mfa_reset",
        # roles · administración del modelo de permisos
        "roles:create",
        "roles:edit",
        # license · emisión y aprobación de licencias
        "license:create",
        "license:edit",
        "license:approve",
        # organization · alta, activación, baja y estructura
        "organization:create",
        "organization:activate",
        "organization:deactivate",
        "organization:delete",
        "organization:manage_structure",
        # aprobaciones · configuración del motor de aprobaciones
        "aprobaciones:configure",
        "aprobaciones:delegate",
        "aprobaciones:edit",
    }
)

# --- SENSIBLE ---------------------------------------------------------------
# Capacidades con impacto financiero, operativo o de auditoría relevante,
# pero que no constituyen control absoluto del sistema.
SENSITIVE_PERMISSIONS: frozenset[str] = frozenset(
    {
        # fiscal · operaciones con impacto tributario
        "fiscal:create",
        "fiscal:approve",
        # tesoreria · operaciones con impacto financiero
        "tesoreria:create",
        "tesoreria:approve",
        # compras · decisiones de gasto y calidad de recepción
        "compras:approve",
        "compras:apply",
        "compras:create",
        "compras:quality",
        # ventas · decisiones comerciales y de envío
        "ventas:approve",
        "ventas:apply",
        "ventas:create",
        "ventas:quality",
        "ventas:submit",
        # inventario · transiciones y reservas de stock
        "inventario:approve",
        "inventario:transition",
        "inventario:create",
        "inventario:confirm",
        "inventario:reserve",
        # aprobaciones · decisiones del flujo de aprobación
        "aprobaciones:approve",
        "aprobaciones:create",
        # regulatorio · cumplimiento normativo
        "regulatorio:approve",
        "regulatorio:create",
        # homologacion · validación de terceros
        "homologacion:approve",
        # audit · acceso a evidencia de auditoría
        "audit:view",
        # reportes · extracción de información sensible
        "reportes:export",
        # documentos · borrado y gestión de tipos documentales
        "documentos:delete",
        "documentos:manage_types",
        # maestros · creación y borrado de datos maestros
        "maestros:delete",
        "maestros:create",
        # comercial · políticas y publicación comercial
        "comercial:manage_policies",
        "comercial:publish",
        # notificaciones · configuración del canal de notificaciones
        "notificaciones:configure",
        # tareas · configuración del motor de tareas
        "tareas:configure",
        # organization · edición de la organización
        "organization:edit",
        # gobierno_ente · identidad, naturaleza y acto de creación del ente (GOV-0-01, PDD-GOV0-04)
        "gobierno_ente:create",
        "gobierno_ente:edit",
        "gobierno_ente:activate",
        # gobierno_estructura · unidades, puesta en vigor y cierre de la estructura (GOV-0-02, PDD-ORG02-02)
        "gobierno_estructura:edit",
        "gobierno_estructura:publish",
        "gobierno_estructura:close",
        # gobierno_cargos · cargos, competencias y límites de firma/aprobación (GOV-0-03, PDD-ORG03-02)
        "gobierno_cargos:edit",
        "gobierno_cargos:publish",
        # gobierno_actos · registro, emisión, eficacia, corrección, revocación y nulidad de actos administrativos (DOC-02, PDD-DOC02-02)
        "gobierno_actos:edit",
        "gobierno_actos:issue",
        "gobierno_actos:annul",
        # gobierno_notificaciones · destinatarios, intentos y constancias de notificación (DOC-04, PDD-DOC04-04)
        "gobierno_notificaciones:edit",
        "gobierno_notificaciones:record",
        # gobierno_hallazgos · verificación y cierre de hallazgos por Control Interno (CTL-06, OD-CTL06-02)
        "gobierno_hallazgos:verify",
        # gobierno_paquetes · generación de paquetes de auditoría exportables (DOC-08, OD-DOC08-04)
        "gobierno_paquetes:generate",
        # gobierno_sod · activación y cierre de reglas de segregación de funciones (CTL-01, OD-CTL01-04)
        "gobierno_sod:activate",
        # gobierno_cuentas · activación, inactivación, reactivación y cierre de cuentas bancarias (TRE-01, OD-TRE01-07)
        "gobierno_cuentas:activate",
        # gobierno_caja · activación y cierre de programas de programación financiera (TRE-02)
        "gobierno_caja:activate",
        # gobierno_cierre · activación y retiro de políticas de cierre (CTL-10)
        "gobierno_cierre:activate",
        # gobierno_ocupacion · activación y revocación de asignaciones de cargos (ORG-04)
        "gobierno_ocupacion:activate",
        "gobierno_ocupacion:revoke",
    }
)

# --- ESTÁNDAR ---------------------------------------------------------------
# Capacidades de consulta y operación ordinaria sin impacto crítico.
STANDARD_PERMISSIONS: frozenset[str] = frozenset(
    {
        # dashboard · consulta de indicadores
        "dashboard:view",
        # organization · consulta de la organización
        "organization:view",
        # users · consulta de identidades
        "users:view",
        # roles · consulta del catálogo de permisos
        "roles:view",
        # license · consulta de licencias
        "license:view",
        # homologacion · consulta, creación y edición de proveedores
        "homologacion:view",
        "homologacion:create",
        "homologacion:edit",
        # maestros · consulta, edición y desactivación de datos maestros
        "maestros:view",
        "maestros:edit",
        "maestros:deactivate",
        # compras · consulta de documentos de compra
        "compras:view",
        # ventas · consulta de documentos de venta
        "ventas:view",
        # inventario · consulta de stock
        "inventario:view",
        # tesoreria · consulta de tesorería
        "tesoreria:view",
        # fiscal · consulta fiscal
        "fiscal:view",
        # regulatorio · consulta regulatoria
        "regulatorio:view",
        # reportes · consulta de reportes
        "reportes:view",
        # aprobaciones · consulta de aprobaciones
        "aprobaciones:view",
        # documentos · operación documental ordinaria
        "documentos:view",
        "documentos:create",
        "documentos:edit",
        "documentos:upload",
        "documentos:download",
        "documentos:link",
        "documentos:deactivate",
        # comercial · operación comercial ordinaria
        "comercial:view",
        "comercial:create",
        "comercial:edit",
        "comercial:archive",
        # tareas · operación ordinaria de tareas
        "tareas:view",
        "tareas:assign",
        "tareas:complete",
        # alertas · consulta de alertas
        "alertas:view",
        # gobierno_ente · consulta del ente (GOV-0-01)
        "gobierno_ente:view",
        # gobierno_estructura · consulta y exportación de la estructura (GOV-0-02)
        "gobierno_estructura:view",
        # gobierno_cargos · consulta y exportación de cargos (GOV-0-03)
        "gobierno_cargos:view",
        # gobierno_actos · consulta y exportación de actos (DOC-02)
        "gobierno_actos:view",
        # gobierno_notificaciones · consulta y exportación de notificaciones (DOC-04)
        "gobierno_notificaciones:view",
        # gobierno_autoridad · consulta y exportación de la matriz de autoridad (ORG-07)
        "gobierno_autoridad:view",
        # gobierno_auditoria · consulta y muestreo del auditor de Gobierno
        # (CTL-04); la muestra es papel de trabajo y no toca la evidencia
        "gobierno_auditoria:view",
        "gobierno_auditoria:sample",
        # gobierno_hallazgos · consulta y gestión del plan de acción correctiva (CTL-06)
        "gobierno_hallazgos:view",
        "gobierno_hallazgos:manage",
        # gobierno_paquetes · consulta, descarga y verificación de paquetes de auditoría (DOC-08)
        "gobierno_paquetes:view",
        # gobierno_sod · consulta de reglas y conflictos y gestión de borradores (CTL-01)
        "gobierno_sod:view",
        "gobierno_sod:manage",
        # gobierno_cuentas · consulta y gestión de cuentas bancarias y autorizados (TRE-01)
        "gobierno_cuentas:view",
        "gobierno_cuentas:manage",
        # gobierno_caja · consulta y gestión de rubros y programas de programación financiera (TRE-02)
        "gobierno_caja:view",
        "gobierno_caja:manage",
        # gobierno_cierre · consulta y gestión de políticas de cierre (CTL-10)
        "gobierno_cierre:view",
        "gobierno_cierre:manage",
        # gobierno_ocupacion · consulta y registro de ocupación de cargos (ORG-04)
        "gobierno_ocupacion:view",
        "gobierno_ocupacion:manage",
    }
)

# Roles protegidos que fuerzan clasificación PRIVILEGED.
PRIVILEGED_ROLE_CODES: frozenset[str] = frozenset({"ADMIN"})


def classify(
    permissions: Iterable[str],
    *,
    protected_role_codes: Iterable[str] = (),
) -> str:
    """Devuelve la clase MFA más alta que corresponde a ``permissions``.

    Reglas:

    - PRIVILEGED si algún código protegido está en ``PRIVILEGED_ROLE_CODES``
      o algún permiso está en ``PRIVILEGED_PERMISSIONS``.
    - En caso contrario, SENSITIVE si algún permiso está en
      ``SENSITIVE_PERMISSIONS`` o no está en ninguna lista.
    - En caso contrario, STANDARD.
    """
    permission_set = set(permissions)
    protected_codes = set(protected_role_codes)

    if PRIVILEGED_ROLE_CODES & protected_codes:
        return PRIVILEGED
    if permission_set & PRIVILEGED_PERMISSIONS:
        return PRIVILEGED
    if permission_set & SENSITIVE_PERMISSIONS:
        return SENSITIVE
    if permission_set - PRIVILEGED_PERMISSIONS - SENSITIVE_PERMISSIONS - STANDARD_PERMISSIONS:
        return SENSITIVE
    return STANDARD


def requires_mfa(policy_class: str) -> bool:
    """Devuelve ``True`` si la clase exige autenticación multifactor."""
    return policy_class in (PRIVILEGED, SENSITIVE)


def user_policy_class(db: Session, user: User) -> str:
    """Calcula la clase MFA del usuario a partir de permisos y roles efectivos.

    Usa una única consulta para los permisos efectivos y otra para los códigos
    de roles protegidos, replicando la semántica de ``get_user_permissions``.
    """
    permission_rows = db.execute(
        select(Permission.resource, Permission.action)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .where(UserRole.user_id == user.id)
    ).all()

    protected_role_rows = db.execute(
        select(Role.code)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user.id, Role.protected.is_(True))
    ).all()

    permissions = (f"{resource}:{action}" for resource, action in permission_rows)
    protected_role_codes = (code for (code,) in protected_role_rows)

    return classify(permissions, protected_role_codes=protected_role_codes)


# Registro cerrado de operaciones que exigen reautenticación reciente.
# La prueba MFA-F03 exige que coincida exactamente con las rutas que llevan
# `require_recent_reauth`. Gobierno lo heredará; solo crece por Spec.
REAUTH_PROTECTED_OPERATIONS: frozenset[tuple[str, str]] = frozenset(
    {
        ("POST", "/api/v1/license/activate"),
        ("POST", "/api/v1/license/import"),
        ("PUT", "/api/v1/licensing/central-config"),
        ("PUT", "/api/v1/system/backup-config"),
        ("POST", "/api/v1/licensing/sync"),
        ("POST", "/api/v1/licensing/renewal-requests"),
        ("POST", "/api/v1/licensing/renewal-requests/{request_id}/transition"),
        ("POST", "/api/v1/licensing/mode-transition"),
        ("POST", "/api/v1/users"),
        ("POST", "/api/v1/users/{user_id}/roles"),
        ("DELETE", "/api/v1/users/{user_id}/roles/{role_id}"),
        ("POST", "/api/v1/roles"),
        ("POST", "/api/v1/organization/warehouses/{warehouse_id}/deactivate"),
        ("DELETE", "/api/v1/organization/warehouses/{warehouse_id}"),
        ("POST", "/api/v1/organization/zones/{node_id}/deactivate"),
        ("DELETE", "/api/v1/organization/zones/{node_id}"),
        ("POST", "/api/v1/organization/aisles/{node_id}/deactivate"),
        ("DELETE", "/api/v1/organization/aisles/{node_id}"),
        ("POST", "/api/v1/organization/racks/{node_id}/deactivate"),
        ("DELETE", "/api/v1/organization/racks/{node_id}"),
        ("POST", "/api/v1/organization/levels/{node_id}/deactivate"),
        ("DELETE", "/api/v1/organization/levels/{node_id}"),
        ("POST", "/api/v1/organization/locations/{location_id}/deactivate"),
        ("DELETE", "/api/v1/organization/locations/{location_id}"),
        ("POST", "/api/v1/approvals/policies"),
        ("PATCH", "/api/v1/approvals/policies/{policy_id}"),
        ("POST", "/api/v1/approvals/policies/{policy_id}/activate"),
        ("POST", "/api/v1/approvals/policies/{policy_id}/close"),
        ("POST", "/api/v1/approvals/policies/{policy_id}/rules"),
        ("POST", "/api/v1/approvals/policies/{policy_id}/rules/{rule_id}/levels"),
        ("POST", "/api/v1/auth/mfa/recovery-codes"),
        ("DELETE", "/api/v1/auth/mfa"),
        ("POST", "/api/v1/users/{user_id}/mfa/reset"),
    }
)
