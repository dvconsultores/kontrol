"""MFA · política por capacidades: PRIVILEGED / SENSITIVE / STANDARD (Spec 002/003 · OQ-MFA-1)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

import app
from app.modules.identity_access import service as identity_service
from app.modules.identity_access.mfa_policy import (
    PRIVILEGED_PERMISSIONS,
    SENSITIVE_PERMISSIONS,
    STANDARD_PERMISSIONS,
    classify,
    requires_mfa,
    user_policy_class,
)
from app.modules.identity_access.models import Permission, User, UserRole
from app.modules.setup.api import SetupRequest, initialize


def _initialize(session: Session) -> dict:
    return initialize(
        session,
        SetupRequest(
            tenant_code="DEMO",
            tenant_name="Empresa Demo",
            company_code="D1",
            company_legal_name="Demo C.A.",
            company_rif="J-12345678-9",
            admin_username="admin",
            admin_password="Kontrol2026Segura!",
        ),
    )


def _permission_universe(session: Session) -> set[str]:
    universe: set[str] = set()

    regex = r"require_permission\s*\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*\)"
    for path in Path(app.__file__).parent.rglob("*.py"):
        for match in re.finditer(regex, path.read_text(encoding="utf-8")):
            universe.add(f"{match.group(1)}:{match.group(2)}")

    for permission in session.query(Permission).all():
        universe.add(f"{permission.resource}:{permission.action}")

    universe.add("users:mfa_reset")
    return universe


def test_mfa_g00_todo_permiso_esta_clasificado(sesion_de_prueba):
    """MFA-G00: cada permiso está exactamente en una lista; sin sobrantes ni ausentes."""
    _initialize(sesion_de_prueba)
    universe = _permission_universe(sesion_de_prueba)
    classified = PRIVILEGED_PERMISSIONS | SENSITIVE_PERMISSIONS | STANDARD_PERMISSIONS

    assert not (PRIVILEGED_PERMISSIONS & SENSITIVE_PERMISSIONS)
    assert not (PRIVILEGED_PERMISSIONS & STANDARD_PERMISSIONS)
    assert not (SENSITIVE_PERMISSIONS & STANDARD_PERMISSIONS)

    unclassified = universe - classified
    leftovers = classified - universe
    assert not unclassified, f"Permisos no clasificados: {sorted(unclassified)}"
    assert not leftovers, f"Permisos sobrantes: {sorted(leftovers)}"


def test_mfa_g00b_recuentos():
    """MFA-G00b: contadores exactos de las listas de clasificación."""
    assert len(PRIVILEGED_PERMISSIONS) == 18
    assert len(SENSITIVE_PERMISSIONS) == 60
    assert len(STANDARD_PERMISSIONS) == 61


@pytest.mark.parametrize(
    "permission",
    [
        "users:create",
        "users:edit",
        "users:deactivate",
        "users:activate",
        "users:mfa_reset",
        "roles:create",
        "roles:edit",
        "license:create",
        "license:edit",
        "license:approve",
        "organization:create",
        "organization:activate",
        "organization:deactivate",
        "organization:delete",
        "organization:manage_structure",
        "aprobaciones:configure",
        "aprobaciones:delegate",
        "aprobaciones:edit",
    ],
)
def test_mfa_g01_cada_privilegiado(permission):
    """MFA-G01: cada permiso privilegiado esperado clasifica como PRIVILEGED."""
    assert classify({permission}) == "PRIVILEGED"
    assert permission in PRIVILEGED_PERMISSIONS


@pytest.mark.parametrize(
    "permission",
    [
        "fiscal:create",
        "fiscal:approve",
        "tesoreria:create",
        "tesoreria:approve",
        "compras:approve",
        "compras:apply",
        "compras:create",
        "compras:quality",
        "ventas:approve",
        "ventas:apply",
        "ventas:create",
        "ventas:quality",
        "ventas:submit",
        "inventario:approve",
        "inventario:transition",
        "inventario:create",
        "inventario:confirm",
        "inventario:reserve",
        "aprobaciones:approve",
        "aprobaciones:create",
        "regulatorio:approve",
        "regulatorio:create",
        "homologacion:approve",
        "audit:view",
        "reportes:export",
        "documentos:delete",
        "documentos:manage_types",
        "maestros:delete",
        "maestros:create",
        "comercial:manage_policies",
        "comercial:publish",
        "notificaciones:configure",
        "tareas:configure",
        "organization:edit",
    ],
)
def test_mfa_g02_cada_sensible(permission):
    """MFA-G02: cada permiso sensible esperado clasifica como SENSITIVE."""
    assert classify({permission}) == "SENSITIVE"


@pytest.mark.parametrize(
    "permission",
    [
        "dashboard:view",
        "organization:view",
        "users:view",
        "roles:view",
        "license:view",
        "homologacion:view",
        "homologacion:create",
        "homologacion:edit",
        "maestros:view",
        "maestros:edit",
        "maestros:deactivate",
        "compras:view",
        "ventas:view",
        "inventario:view",
        "tesoreria:view",
        "fiscal:view",
        "regulatorio:view",
        "reportes:view",
        "aprobaciones:view",
        "documentos:view",
        "documentos:create",
        "documentos:edit",
        "documentos:upload",
        "documentos:download",
        "documentos:link",
        "documentos:deactivate",
        "comercial:view",
        "comercial:create",
        "comercial:edit",
        "comercial:archive",
        "tareas:view",
        "tareas:assign",
        "tareas:complete",
        "alertas:view",
    ],
)
def test_mfa_g03_cada_estandar(permission):
    """MFA-G03: cada permiso estándar esperado clasifica como STANDARD."""
    assert classify({permission}) == "STANDARD"


def test_mfa_g04_gana_la_clase_mas_alta():
    """MFA-G04: gana la clase más alta entre PRIVILEGED, SENSITIVE y STANDARD."""
    assert classify({"inventario:view", "users:create"}) == "PRIVILEGED"
    assert classify({"inventario:view", "inventario:transition"}) == "SENSITIVE"
    assert classify({"inventario:view", "ventas:view"}) == "STANDARD"


def test_mfa_g05_permiso_desconocido_nunca_es_estandar():
    """MFA-G05: un permiso desconocido nunca cae en STANDARD en silencio."""
    assert classify({"nuevo:accion"}) == "SENSITIVE"
    assert classify({"inventario:view", "nuevo:x"}) == "SENSITIVE"


def test_mfa_g06_sin_permisos_es_estandar():
    """MFA-G06: sin permisos la clase es STANDARD."""
    assert classify(set()) == "STANDARD"


def test_mfa_g07_admin_protegido_siempre_privilegiado():
    """MFA-G07: el rol protegido ADMIN siempre es PRIVILEGED."""
    assert classify(set(), protected_role_codes={"ADMIN"}) == "PRIVILEGED"
    assert classify({"dashboard:view"}, protected_role_codes={"OTRO"}) == "STANDARD"


def test_mfa_g08_requires_mfa():
    """MFA-G08: requiere MFA para PRIVILEGED y SENSITIVE, no para STANDARD."""
    assert requires_mfa("PRIVILEGED") is True
    assert requires_mfa("SENSITIVE") is True
    assert requires_mfa("STANDARD") is False


def test_mfa_g09_clase_del_usuario_por_capacidad(sesion_de_prueba):
    """MFA-G09: la clase del usuario deriva de capacidades, no del nombre del rol."""
    setup = _initialize(sesion_de_prueba)

    admin = sesion_de_prueba.get(User, setup["admin_user_id"])
    assert user_policy_class(sesion_de_prueba, admin) == "PRIVILEGED"

    no_roles = identity_service.create_user(
        sesion_de_prueba,
        tenant_id=setup["tenant_id"],
        username="sin_roles",
        email="sin_roles@example.com",
        password="Kontrol2026Segura!",
    )
    assert user_policy_class(sesion_de_prueba, no_roles) == "STANDARD"

    rol_admin_empresa = identity_service.create_role(
        sesion_de_prueba,
        tenant_id=setup["tenant_id"],
        code="ADMIN",
        name="Admin de Empresa",
        company_id=setup["company_id"],
        permissions=["dashboard:view", "inventario:view"],
        actor=setup["admin_user_id"],
    )
    usuario_admin_empresa = identity_service.create_user(
        sesion_de_prueba,
        tenant_id=setup["tenant_id"],
        username="admin_empresa",
        email="admin_empresa@example.com",
        password="Kontrol2026Segura!",
    )
    sesion_de_prueba.add(
        UserRole(
            user_id=usuario_admin_empresa.id,
            role_id=rol_admin_empresa["id"],
            company_id=setup["company_id"],
        )
    )
    sesion_de_prueba.commit()
    sesion_de_prueba.refresh(usuario_admin_empresa)
    assert user_policy_class(sesion_de_prueba, usuario_admin_empresa) == "STANDARD"

    rol_sensible_empresa = identity_service.create_role(
        sesion_de_prueba,
        tenant_id=setup["tenant_id"],
        code="INVENTARIO_SENSIBLE",
        name="Inventario Empresa",
        company_id=setup["company_id"],
        permissions=["inventario:view", "inventario:transition"],
        actor=setup["admin_user_id"],
    )
    usuario_sensible_empresa = identity_service.create_user(
        sesion_de_prueba,
        tenant_id=setup["tenant_id"],
        username="sensible_empresa",
        email="sensible_empresa@example.com",
        password="Kontrol2026Segura!",
    )
    sesion_de_prueba.add(
        UserRole(
            user_id=usuario_sensible_empresa.id,
            role_id=rol_sensible_empresa["id"],
            company_id=setup["company_id"],
        )
    )
    sesion_de_prueba.commit()
    sesion_de_prueba.refresh(usuario_sensible_empresa)
    assert user_policy_class(sesion_de_prueba, usuario_sensible_empresa) == "SENSITIVE"

    rol_privilegiado_empresa = identity_service.create_role(
        sesion_de_prueba,
        tenant_id=setup["tenant_id"],
        code="USUARIOS_PRIVILEGIADO",
        name="Usuarios Empresa",
        company_id=setup["company_id"],
        permissions=["users:create"],
        actor=setup["admin_user_id"],
    )
    usuario_privilegiado_empresa = identity_service.create_user(
        sesion_de_prueba,
        tenant_id=setup["tenant_id"],
        username="privilegiado_empresa",
        email="privilegiado_empresa@example.com",
        password="Kontrol2026Segura!",
    )
    sesion_de_prueba.add(
        UserRole(
            user_id=usuario_privilegiado_empresa.id,
            role_id=rol_privilegiado_empresa["id"],
            company_id=setup["company_id"],
        )
    )
    sesion_de_prueba.commit()
    sesion_de_prueba.refresh(usuario_privilegiado_empresa)
    assert user_policy_class(sesion_de_prueba, usuario_privilegiado_empresa) == "PRIVILEGED"


def test_mfa_g10_inventario_transition_es_sensible():
    """MFA-G10: inventario:transition es sensible de forma definitiva."""
    assert "inventario:transition" in SENSITIVE_PERMISSIONS
