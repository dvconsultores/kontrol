import uuid

import pytest
from mfa_mundo import API, alta_por_desafio, crear_usuario, login, mundo_mfa
from sqlalchemy import select

from app.modules.identity_access import service as identity_service
from app.modules.identity_access.models import UserRole
from app.modules.organization.models import Company

pytest_plugins = ("mfa_apoyo",)


def _nombre():
    return uuid.uuid4().hex[:10]


def _dar(mundo, user_id, role_id, company_id):
    db = mundo.factory()
    try:
        db.add(UserRole(user_id=user_id, role_id=role_id, company_id=company_id))
        db.commit()
    finally:
        db.close()


def _quitar(mundo, user_id, role_id):
    db = mundo.factory()
    try:
        for row in db.execute(
            select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
        ).scalars():
            db.delete(row)
        db.commit()
    finally:
        db.close()


def _entrar(mundo, reloj, nombre):
    r = login(mundo.client, nombre)
    assert r.status_code == 200, r.text
    if r.json().get("status") == "AUTHENTICATED":
        return {"Authorization": f"Bearer {r.json()['access_token']}"}
    return alta_por_desafio(mundo.client, reloj, nombre).cabeceras


def _actor(mundo, reloj, asignaciones):
    nombre = _nombre()
    user_id = crear_usuario(mundo, nombre)
    for role_id, company_id in asignaciones:
        _dar(mundo, user_id, role_id, company_id)
    return user_id, _entrar(mundo, reloj, nombre)


def _h(cab, empresa):
    return {**cab, "X-Kontrol-Company": empresa}


@pytest.fixture(scope="module")
def mundo():
    with mundo_mfa() as m:
        yield m


@pytest.fixture(scope="module")
def escenario(mundo):
    db = mundo.factory()
    try:
        d1 = mundo.company_id
        d2_obj = Company(
            tenant_id=mundo.tenant_id,
            code="D2",
            legal_name="Demo Dos CA",
            rif="J-44444444-4",
            legal_type="JURIDICA",
            functional_currency="VED",
            status="ACTIVE",
        )
        db.add(d2_obj)
        db.commit()
        db.refresh(d2_obj)
        d2 = d2_obj.id

        rol = identity_service.create_role(
            db,
            tenant_id=mundo.tenant_id,
            code="R_UIA",
            name="Rol UIA",
            company_id=None,
            permissions=["maestros:view", "maestros:create"],
            actor=mundo.admin_id,
        )
        roles = identity_service.list_roles(db)
        fc = next(r["id"] for r in roles if r["code"] == "FUNCIONAL_COMPLETO")
        return {"d1": d1, "d2": d2, "rol": rol["id"], "fc": fc}
    finally:
        db.close()


def test_uia_b01_tenant_permissions_solo_rol_nulo(mundo, reloj_mfa, escenario):
    """UIA-B01: /auth/me diferencia tenant_permissions según company_id NULO o D1."""
    _, cab_nulo = _actor(mundo, reloj_mfa, [(escenario["rol"], None)])
    r = mundo.client.get(f"{API}/auth/me", headers=cab_nulo)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "maestros:view" in body["permissions"], r.text
    assert "maestros:view" in body["tenant_permissions"], r.text

    _, cab_d1 = _actor(mundo, reloj_mfa, [(escenario["rol"], escenario["d1"])])
    r = mundo.client.get(f"{API}/auth/me", headers=cab_d1)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "maestros:view" in body["permissions"], r.text
    assert "maestros:view" not in body["tenant_permissions"], r.text


def test_uia_b02_authority_company_por_empresa(mundo, reloj_mfa, escenario):
    """UIA-B02: /authority/company devuelve permisos de la empresa indicada."""
    _, cab = _actor(mundo, reloj_mfa, [(escenario["rol"], escenario["d1"])])
    r = mundo.client.get(f"{API}/authority/company", headers=_h(cab, escenario["d1"]))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["company_id"] == escenario["d1"], r.text
    assert "maestros:view" in body["permissions"], r.text

    r = mundo.client.get(f"{API}/authority/company", headers=_h(cab, escenario["d2"]))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["company_id"] == escenario["d2"], r.text
    assert "maestros:view" not in body["permissions"], r.text


def test_uia_b03_authority_company_empresa_otro_tenant(mundo, reloj_mfa, escenario):
    """UIA-B03: empresa de otro tenant en /authority/company devuelve 404 COMPANY_NOT_FOUND."""
    _, cab = _actor(mundo, reloj_mfa, [(escenario["rol"], escenario["d1"])])
    db = mundo.factory()
    try:
        empresa_b = db.execute(
            select(Company.id).where(Company.tenant_id == mundo.tenant_b_id)
        ).scalar_one()
    finally:
        db.close()
    r = mundo.client.get(f"{API}/authority/company", headers=_h(cab, empresa_b))
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "COMPANY_NOT_FOUND", r.text


def test_uia_b04_admin_sin_permisos_funcionales(mundo, reloj_mfa, escenario):
    """UIA-B04: ADMIN no aporta permisos funcionales en /authority/company ni /auth/me."""
    nombre = _nombre()
    crear_usuario(mundo, nombre, admin=True)
    cab = _entrar(mundo, reloj_mfa, nombre)

    r = mundo.client.get(f"{API}/authority/company", headers=_h(cab, escenario["d1"]))
    assert r.status_code == 200, r.text
    assert "maestros:view" not in r.json()["permissions"], r.text

    r = mundo.client.get(f"{API}/auth/me", headers=cab)
    assert r.status_code == 200, r.text
    assert "maestros:view" not in r.json()["permissions"], r.text


def test_uia_b05_funcional_completo_solo_en_empresa_asignada(mundo, reloj_mfa, escenario):
    """UIA-B05: FUNCIONAL_COMPLETO en D1 se limita a D1 en /authority/company y no es tenant permission."""
    nombre = _nombre()
    user_id = crear_usuario(mundo, nombre)
    _dar(mundo, user_id, escenario["fc"], escenario["d1"])
    cab = _entrar(mundo, reloj_mfa, nombre)

    r = mundo.client.get(f"{API}/authority/company", headers=_h(cab, escenario["d1"]))
    assert r.status_code == 200, r.text
    permisos = r.json()["permissions"]
    assert "maestros:view" in permisos, r.text
    assert "ventas:view" in permisos, r.text

    r = mundo.client.get(f"{API}/authority/company", headers=_h(cab, escenario["d2"]))
    assert r.status_code == 200, r.text
    permisos = r.json()["permissions"]
    assert "maestros:view" not in permisos, r.text
    assert "ventas:view" not in permisos, r.text

    r = mundo.client.get(f"{API}/auth/me", headers=cab)
    assert r.status_code == 200, r.text
    tenant_permissions = r.json()["tenant_permissions"]
    assert "maestros:view" not in tenant_permissions, r.text
    assert "ventas:view" not in tenant_permissions, r.text


def test_uia_b06_operations_contrato_exacto(mundo, reloj_mfa, escenario):
    """UIA-B06: /auth/operations devuelve las operaciones exactas del contrato y exige sesión."""
    _, cab = _actor(mundo, reloj_mfa, [(escenario["rol"], None)])
    r = mundo.client.get(f"{API}/auth/operations", headers=cab)
    assert r.status_code == 200, r.text
    operaciones = r.json()["operations"]

    esperadas = [
        {
            "method": "GET",
            "path": "/api/v1/maestros/unidades",
            "capabilities": ["maestros:view"],
            "scope": "COMPANY",
        },
        {
            "method": "POST",
            "path": "/api/v1/fiscal/legal-sources",
            "capabilities": ["fiscal:create"],
            "scope": "TENANT",
        },
        {
            "method": "GET",
            "path": "/api/v1/users",
            "capabilities": ["users:view"],
            "scope": "GLOBAL",
        },
        {
            "method": "GET",
            "path": "/api/v1/authority/company",
            "capabilities": [],
            "scope": "COMPANY",
        },
    ]
    for esperada in esperadas:
        assert esperada in operaciones, r.text
    assert len({(op["method"], op["path"]) for op in operaciones}) == len(operaciones), r.text

    for op in operaciones:
        assert op["method"] not in ("HEAD", "OPTIONS"), r.text
        assert op["scope"] in ("COMPANY", "TENANT", "GLOBAL"), r.text
        assert op["capabilities"] == sorted(op["capabilities"]), r.text

    r = mundo.client.get(f"{API}/auth/operations")
    assert r.status_code == 401, r.text


def test_uia_b07_authority_company_relee_asignaciones(mundo, reloj_mfa, escenario):
    """UIA-B07: /authority/company relee la asignación con el mismo token."""
    user_id, cab = _actor(mundo, reloj_mfa, [(escenario["rol"], None)])

    r = mundo.client.get(f"{API}/authority/company", headers=_h(cab, escenario["d2"]))
    assert r.status_code == 200, r.text
    assert "maestros:view" in r.json()["permissions"], r.text

    _quitar(mundo, user_id, escenario["rol"])
    _dar(mundo, user_id, escenario["rol"], escenario["d1"])

    r = mundo.client.get(f"{API}/authority/company", headers=_h(cab, escenario["d2"]))
    assert r.status_code == 200, r.text
    assert "maestros:view" not in r.json()["permissions"], r.text
