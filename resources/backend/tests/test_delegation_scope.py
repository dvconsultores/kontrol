"""Pruebas de límite de alcance de empresa en delegación de roles (DSC)."""
from uuid import uuid4

import pytest
from mfa_mundo import API, alta_por_desafio, crear_usuario, eventos, mundo_mfa
from sqlalchemy import func, select

from app.core.errors import PermissionDeniedError
from app.modules.identity_access import service as identity_service
from app.modules.identity_access.models import UserRole, UserScope
from app.modules.organization.models import Company

pytest_plugins = ("mfa_apoyo",)


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
            code="D2",
            legal_name="Demo Dos CA",
            rif="J-11111111-1",
            legal_type="JURIDICA",
            functional_currency="VED",
            status="ACTIVE",
        )
        db.add(d2)
        db.commit()

        r_gestor = identity_service.create_role(
            db,
            tenant_id=mundo.tenant_id,
            code="R_DSC_GESTOR",
            name="Gestor DSC",
            company_id=None,
            permissions=["roles:view", "roles:edit", "users:view", "inventario:view"],
            actor=mundo.admin_id,
        )
        r_sub = identity_service.create_role(
            db,
            tenant_id=mundo.tenant_id,
            code="R_DSC_SUB",
            name="Sub DSC",
            company_id=None,
            permissions=["inventario:view"],
            actor=mundo.admin_id,
        )
        return {"d1": mundo.company_id, "d2": d2.id, "r_gestor": r_gestor["id"], "r_sub": r_sub["id"]}
    finally:
        db.close()


def _nombre():
    return uuid4().hex[:10]


def _dar(mundo, user_id, role_id, company_id):
    db = mundo.factory()
    try:
        db.add(UserRole(user_id=user_id, role_id=role_id, company_id=company_id))
        db.commit()
    finally:
        db.close()


def _alcance(mundo, user_id, company_id):
    db = mundo.factory()
    try:
        db.add(UserScope(user_id=user_id, company_id=company_id))
        db.commit()
    finally:
        db.close()


def _filas(mundo, user_id, role_id):
    db = mundo.factory()
    try:
        return db.scalar(select(func.count()).select_from(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id))
    finally:
        db.close()


def _gestor_d1(mundo, reloj, esc):
    nombre = f"gestor_{_nombre()}"
    user_id = crear_usuario(mundo, nombre, tenant="DEMO")
    _dar(mundo, user_id, esc["r_gestor"], esc["d1"])
    cabeceras = alta_por_desafio(mundo.client, reloj, nombre).cabeceras
    return user_id, cabeceras


def _asignar(mundo, cab, user_id, role_id, company_id=None):
    payload = {"role_id": role_id}
    if company_id is not None:
        payload["company_id"] = company_id
    return mundo.client.post(f"{API}/users/{user_id}/roles", json=payload, headers=cab)


def _negaciones(mundo, actor_id):
    return [e for e in eventos(mundo, "AUTHORITY_DELEGATION_DENIED") if e.user_id == actor_id]


def test_dsc_e01_cross_scope_company_id_d2(mundo, reloj_mfa, escenario):
    """DSC-E01: gestor D1 asigna con company_id=d2 fuera de su alcance."""
    actor, cab = _gestor_d1(mundo, reloj_mfa, escenario)
    destino = crear_usuario(mundo, f"destino_{_nombre()}", tenant="DEMO")
    antes = len(_negaciones(mundo, actor))

    r = _asignar(mundo, cab, destino, escenario["r_sub"], escenario["d2"])

    assert r.status_code == 403, r.text
    assert r.json().get("code") == "CROSS_SCOPE_DELEGATION_FORBIDDEN", r.text
    assert _filas(mundo, destino, escenario["r_sub"]) == 0, r.text
    nuevas = _negaciones(mundo, actor)[antes:]
    assert len(nuevas) == 1, r.text
    assert nuevas[0].reason == "CROSS_SCOPE_DELEGATION_FORBIDDEN", r.text


def test_dsc_e02_ok_company_id_d1(mundo, reloj_mfa, escenario):
    """DSC-E02: gestor D1 asigna con company_id=d1 dentro de su alcance."""
    actor, cab = _gestor_d1(mundo, reloj_mfa, escenario)
    destino = crear_usuario(mundo, f"destino_{_nombre()}", tenant="DEMO")

    r = _asignar(mundo, cab, destino, escenario["r_sub"], escenario["d1"])

    assert r.status_code == 200, r.text
    assert _filas(mundo, destino, escenario["r_sub"]) == 1, r.text
    db = mundo.factory()
    try:
        fila = db.scalar(select(UserRole).where(UserRole.user_id == destino, UserRole.role_id == escenario["r_sub"]))
        assert fila.company_id == escenario["d1"], r.text
    finally:
        db.close()


def test_dsc_e03_sin_company_scope_mixto(mundo, reloj_mfa, escenario):
    """DSC-E03: gestor D1 asigna sin company_id y el destino sin alcances accede a D1 y D2."""
    actor, cab = _gestor_d1(mundo, reloj_mfa, escenario)
    destino = crear_usuario(mundo, f"destino_{_nombre()}", tenant="DEMO")
    antes = len(_negaciones(mundo, actor))

    r = _asignar(mundo, cab, destino, escenario["r_sub"])

    assert r.status_code == 403, r.text
    assert r.json().get("code") == "CROSS_SCOPE_DELEGATION_FORBIDDEN", r.text
    assert _filas(mundo, destino, escenario["r_sub"]) == 0, r.text
    nuevas = _negaciones(mundo, actor)[antes:]
    assert len(nuevas) == 1, r.text
    assert nuevas[0].reason == "CROSS_SCOPE_DELEGATION_FORBIDDEN", r.text


def test_dsc_e04_sin_company_scope_destino_d1(mundo, reloj_mfa, escenario):
    """DSC-E04: gestor D1 asigna sin company_id y el destino con UserScope solo en D1."""
    actor, cab = _gestor_d1(mundo, reloj_mfa, escenario)
    destino = crear_usuario(mundo, f"destino_{_nombre()}", tenant="DEMO")
    _alcance(mundo, destino, escenario["d1"])

    r = _asignar(mundo, cab, destino, escenario["r_sub"])

    assert r.status_code == 200, r.text
    assert _filas(mundo, destino, escenario["r_sub"]) == 1, r.text


def test_dsc_e05_autoescalamiento(mundo, reloj_mfa, escenario):
    """DSC-E05: gestor D1 se asigna a sí mismo con company_id=d2 fuera de su alcance."""
    actor, cab = _gestor_d1(mundo, reloj_mfa, escenario)
    antes = len(_negaciones(mundo, actor))

    r = _asignar(mundo, cab, actor, escenario["r_sub"], escenario["d2"])

    assert r.status_code == 403, r.text
    assert r.json().get("code") == "SELF_ESCALATION_FORBIDDEN", r.text
    assert _filas(mundo, actor, escenario["r_sub"]) == 0, r.text
    nuevas = _negaciones(mundo, actor)[antes:]
    assert len(nuevas) == 1, r.text
    assert nuevas[0].reason == "SELF_ESCALATION_FORBIDDEN", r.text


def test_dsc_e06_gestor_tenant_scope(mundo, reloj_mfa, escenario):
    """DSC-E06: gestor con company_id=None (todo el tenant) asigna con company_id=d2."""
    nombre = f"gestor_{_nombre()}"
    actor = crear_usuario(mundo, nombre, tenant="DEMO")
    _dar(mundo, actor, escenario["r_gestor"], None)
    cab = alta_por_desafio(mundo.client, reloj_mfa, nombre).cabeceras
    destino = crear_usuario(mundo, f"destino_{_nombre()}", tenant="DEMO")

    r = _asignar(mundo, cab, destino, escenario["r_sub"], escenario["d2"])

    assert r.status_code == 200, r.text
    assert _filas(mundo, destino, escenario["r_sub"]) == 1, r.text


def test_dsc_m01_quitar_fuera_de_alcance(mundo, reloj_mfa, escenario):
    """DSC-M01: gestor D1 quita asignación en D2 fuera de su alcance."""
    actor, cab = _gestor_d1(mundo, reloj_mfa, escenario)
    destino = crear_usuario(mundo, f"destino_{_nombre()}", tenant="DEMO")
    _dar(mundo, destino, escenario["r_sub"], escenario["d2"])

    r = mundo.client.delete(f"{API}/users/{destino}/roles/{escenario['r_sub']}", headers=cab)

    assert r.status_code == 403, r.text
    assert r.json().get("code") == "TARGET_OUT_OF_SCOPE", r.text
    assert _filas(mundo, destino, escenario["r_sub"]) == 1, r.text


def test_dsc_m02_quitar_dentro_de_alcance(mundo, reloj_mfa, escenario):
    """DSC-M02: gestor D1 quita asignación en D1 dentro de su alcance."""
    actor, cab = _gestor_d1(mundo, reloj_mfa, escenario)
    destino = crear_usuario(mundo, f"destino_{_nombre()}", tenant="DEMO")
    _dar(mundo, destino, escenario["r_sub"], escenario["d1"])

    r = mundo.client.delete(f"{API}/users/{destino}/roles/{escenario['r_sub']}", headers=cab)

    assert r.status_code == 200, r.text
    assert _filas(mundo, destino, escenario["r_sub"]) == 0, r.text


def test_dsc_c01_crear_rol_fuera_del_alcance_se_deniega(mundo, escenario):
    """DSC-C01: quien tiene la autoridad solo en D1 no crea roles de D2 ni de todo el tenant; sí de D1."""
    gestor_id = crear_usuario(mundo, f"gestor_{_nombre()}")
    _dar(mundo, gestor_id, escenario["r_gestor"], escenario["d1"])
    db_apoyo = mundo.factory()
    try:
        rol_id = identity_service.create_role(
            db_apoyo,
            tenant_id=mundo.tenant_id,
            code=f"rol_{_nombre()}",
            name="Rol delegado",
            company_id=None,
            permissions=["roles:create"],
            actor=mundo.admin_id,
        )["id"]
    finally:
        db_apoyo.close()
    _dar(mundo, gestor_id, rol_id, escenario["d1"])
    db = mundo.factory()
    try:
        with pytest.raises(PermissionDeniedError) as exc_info:
            identity_service.create_role(
                db,
                tenant_id=mundo.tenant_id,
                code=f"r_{_nombre()}",
                name="Rol D2",
                company_id=escenario["d2"],
                permissions=["inventario:view"],
                actor=gestor_id,
            )
        assert exc_info.value.code == "CROSS_SCOPE_DELEGATION_FORBIDDEN"
        with pytest.raises(PermissionDeniedError) as exc_info:
            identity_service.create_role(
                db,
                tenant_id=mundo.tenant_id,
                code=f"r_{_nombre()}",
                name="Rol tenant",
                company_id=None,
                permissions=["inventario:view"],
                actor=gestor_id,
            )
        assert exc_info.value.code == "CROSS_SCOPE_DELEGATION_FORBIDDEN"
        creado = identity_service.create_role(
            db,
            tenant_id=mundo.tenant_id,
            code=f"r_{_nombre()}",
            name="Rol D1",
            company_id=escenario["d1"],
            permissions=["inventario:view"],
            actor=gestor_id,
        )
        assert "id" in creado
    finally:
        db.close()
