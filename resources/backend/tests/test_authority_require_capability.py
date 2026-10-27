"""Fija el orden de errores de require_capability: PERMISSION_DENIED si no tiene la capacidad en ninguna empresa, COMPANY_SCOPE_FORBIDDEN si solo en otra."""

import uuid
from types import SimpleNamespace

import pytest
from mfa_mundo import crear_usuario, mundo_mfa

from app.core.errors import PermissionDeniedError
from app.modules.identity_access import authority
from app.modules.identity_access import service as identity_service
from app.modules.identity_access.models import User, UserRole
from app.modules.organization.models import Company

pytest_plugins = ("mfa_apoyo",)


def _nombre():
    return f"rca{uuid.uuid4().hex[:12]}"


@pytest.fixture(scope="module")
def mundo():
    with mundo_mfa() as m:
        yield m


@pytest.fixture(scope="module")
def escenario(mundo):
    db = mundo.factory()
    try:
        d2 = Company(
            tenant_id=mundo.tenant_id,
            code="RCA-D2",
            legal_name="Require Capability D2",
            rif="J-55555555-5",
            legal_type="JURIDICA",
            functional_currency="VED",
            status="ACTIVE",
        )
        db.add(d2)
        db.flush()

        rol_id = identity_service.create_role(
            db,
            tenant_id=mundo.tenant_id,
            code=f"R_RCA_VEN-{uuid.uuid4().hex[:8]}",
            name=f"R_RCA_VEN-{uuid.uuid4().hex[:8]}",
            company_id=None,
            permissions=["ventas:view"],
            actor=mundo.admin_id,
        )["id"]

        db.commit()
        return SimpleNamespace(rol_id=rol_id, d1=mundo.company_id, d2=d2.id)
    finally:
        db.close()


def _crear_usuario_con_rol(mundo, escenario, nombre, company_id=None):
    user_id = crear_usuario(mundo, nombre)
    db = mundo.factory()
    try:
        db.add(
            UserRole(
                user_id=user_id,
                role_id=escenario.rol_id,
                company_id=company_id,
            )
        )
        db.commit()
    finally:
        db.close()
    return user_id


def test_rca_01_usuario_sin_roles_permiso_denegado(mundo, escenario):
    user_id = crear_usuario(mundo, _nombre())
    db = mundo.factory()
    try:
        user = db.get(User, user_id)
        with pytest.raises(PermissionDeniedError) as exc:
            authority.require_capability(
                db, user=user, capability="ventas:view", company_id=escenario.d1
            )
        assert exc.value.code == "PERMISSION_DENIED"
    finally:
        db.close()


def test_rca_02_usuario_con_rol_en_d2_solicita_d1_company_scope_forbidden(mundo, escenario):
    user_id = _crear_usuario_con_rol(mundo, escenario, _nombre(), company_id=escenario.d2)
    db = mundo.factory()
    try:
        user = db.get(User, user_id)
        with pytest.raises(PermissionDeniedError) as exc:
            authority.require_capability(
                db, user=user, capability="ventas:view", company_id=escenario.d1
            )
        assert exc.value.code == "COMPANY_SCOPE_FORBIDDEN"
    finally:
        db.close()


def test_rca_03_usuario_con_rol_en_d2_solicita_d2_no_lanza(mundo, escenario):
    user_id = _crear_usuario_con_rol(mundo, escenario, _nombre(), company_id=escenario.d2)
    db = mundo.factory()
    try:
        user = db.get(User, user_id)
        authority.require_capability(
            db, user=user, capability="ventas:view", company_id=escenario.d2
        )
    finally:
        db.close()


def test_rca_04_usuario_con_rol_global_solicita_d1_no_lanza(mundo, escenario):
    user_id = _crear_usuario_con_rol(mundo, escenario, _nombre(), company_id=None)
    db = mundo.factory()
    try:
        user = db.get(User, user_id)
        authority.require_capability(
            db, user=user, capability="ventas:view", company_id=escenario.d1
        )
    finally:
        db.close()
