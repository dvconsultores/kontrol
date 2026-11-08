import uuid

import pytest
from sqlalchemy import select

pytest_plugins = ("mfa_apoyo",)


API = "/api/v1"


@pytest.fixture(scope="module")
def mundo():
    from mfa_mundo import mundo_mfa

    with mundo_mfa() as m:
        yield m


@pytest.fixture(scope="module")
def rol_operador(mundo):
    from app.modules.identity_access import service as identity_service

    db = mundo.factory()
    try:
        rol = identity_service.create_role(
            db,
            tenant_id=mundo.tenant_id,
            code=f"terc{uuid.uuid4().hex[:12]}",
            name="Terceros Auditoría",
            company_id=None,
            permissions=[
                "maestros:view",
                "maestros:create",
                "maestros:edit",
                "compras:approve",
                "audit:view",
            ],
            actor=mundo.admin_id,
        )
        db.commit()
        return rol["id"]
    finally:
        db.close()


@pytest.fixture(scope="module")
def rol_solo_lectura(mundo):
    from app.modules.identity_access import service as identity_service

    db = mundo.factory()
    try:
        rol = identity_service.create_role(
            db,
            tenant_id=mundo.tenant_id,
            code=f"lect{uuid.uuid4().hex[:12]}",
            name="Terceros Solo Lectura",
            company_id=None,
            permissions=["maestros:view"],
            actor=mundo.admin_id,
        )
        db.commit()
        return rol["id"]
    finally:
        db.close()


def _dar(mundo, user_id, role_id, company_id):
    from app.modules.identity_access.models import UserRole

    db = mundo.factory()
    try:
        db.add(UserRole(user_id=user_id, role_id=role_id, company_id=company_id))
        db.commit()
    finally:
        db.close()


def _entrar(mundo, reloj_mfa, nombre):
    from mfa_mundo import alta_por_desafio, login

    r = login(mundo.client, nombre)
    assert r.status_code == 200, r.text
    if r.json().get("status") == "AUTHENTICATED":
        return {"Authorization": f"Bearer {r.json()['access_token']}"}
    return alta_por_desafio(mundo.client, reloj_mfa, nombre).cabeceras


def _operador(mundo, reloj_mfa, rol):
    from mfa_mundo import crear_usuario

    nombre = f"terc{uuid.uuid4().hex[:12]}"
    user_id = crear_usuario(mundo, nombre)
    _dar(mundo, user_id, rol, mundo.company_id)
    cabeceras = _entrar(mundo, reloj_mfa, nombre)
    cabeceras["X-Kontrol-Company"] = str(mundo.company_id)
    return cabeceras


def _tercero(mundo, cabeceras, roles, tax_id=None):
    code = f"T-{uuid.uuid4().hex[:12]}"
    payload = {"code": code, "name": f"Tercero {code}", "roles": roles}
    if tax_id:
        payload["tax_id"] = tax_id
    r = mundo.client.post(
        f"{API}/maestros/terceros",
        json=payload,
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _crear_cuenta(mundo, cabeceras, party_id, **overrides):
    payload = {"bank": "Banco", "account_number": "01020000000000000001", **overrides}
    r = mundo.client.post(
        f"{API}/maestros/terceros/{party_id}/bank-accounts",
        json=payload,
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_historial_del_tercero(mundo, reloj_mfa, rol_operador):
    cabeceras = _operador(mundo, reloj_mfa, rol_operador)
    party_id = _tercero(mundo, cabeceras, ["PROVEEDOR"])

    _crear_cuenta(mundo, cabeceras, party_id)

    r = mundo.client.patch(
        f"{API}/maestros/terceros/{party_id}",
        json={"name": "Renombrado"},
        headers={**cabeceras, "If-Match": "1"},
    )
    assert r.status_code == 200, r.text

    r = mundo.client.post(
        f"{API}/maestros/terceros/{party_id}/roles/PROVEEDOR/reject",
        json={"reason": "revisión"},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text

    r = mundo.client.get(
        f"{API}/maestros/terceros/{party_id}/audit",
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert items[0]["action"] == "SUPPLIER_APPROVAL_CHANGED"
    assert items[0]["reason"] == "revisión"
    acciones = {e["action"] for e in items}
    assert "PARTY_BANK_ACCOUNT_CREATED" in acciones
    assert "PARTY_UPDATED" in acciones
    assert "PARTY_CREATED" in acciones
    assert all(e["username"] is not None for e in items)
    assert "01020000000000000001" not in r.text


def test_historial_sin_permiso_403(mundo, reloj_mfa, rol_operador, rol_solo_lectura):
    cabeceras_operador = _operador(mundo, reloj_mfa, rol_operador)
    party_id = _tercero(mundo, cabeceras_operador, ["CLIENTE"])
    cabeceras = _operador(mundo, reloj_mfa, rol_solo_lectura)

    r = mundo.client.get(
        f"{API}/maestros/terceros/{party_id}/audit",
        headers=cabeceras,
    )
    assert r.status_code == 403, r.text


def test_historial_empresa_ajena_404(mundo, reloj_mfa, rol_operador):
    from app.modules.master_data.models import Party
    from app.modules.organization.models import Company

    cabeceras = _operador(mundo, reloj_mfa, rol_operador)
    db = mundo.factory()
    party_externo_id = None
    try:
        empresa_b = db.scalar(select(Company).where(Company.tenant_id == mundo.tenant_b_id))
        assert empresa_b is not None
        party_externo = Party(
            company_id=empresa_b.id,
            code=f"AJ-{uuid.uuid4().hex[:8]}",
            name="Ajeno",
            roles=["CLIENTE"],
            status="ACTIVE",
        )
        db.add(party_externo)
        db.commit()
        party_externo_id = str(party_externo.id)
    finally:
        db.close()

    assert party_externo_id is not None
    r = mundo.client.get(
        f"{API}/maestros/terceros/{party_externo_id}/audit",
        headers=cabeceras,
    )
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "PARTY_NOT_FOUND"
