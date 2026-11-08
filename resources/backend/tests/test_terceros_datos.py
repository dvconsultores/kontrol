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
            name="Terceros Datos",
            company_id=None,
            permissions=[
                "maestros:view",
                "maestros:create",
                "maestros:edit",
                "compras:approve",
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


@pytest.fixture(scope="module")
def rol_aprobador(mundo):
    from app.modules.identity_access import service as identity_service

    db = mundo.factory()
    try:
        rol = identity_service.create_role(
            db,
            tenant_id=mundo.tenant_id,
            code=f"aprob{uuid.uuid4().hex[:12]}",
            name="Terceros Aprobador",
            company_id=None,
            permissions=["maestros:view", "compras:approve"],
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


def _tercero(mundo, cabeceras, roles):
    code = f"T-{uuid.uuid4().hex[:12]}"
    r = mundo.client.post(
        f"{API}/maestros/terceros",
        json={"code": code, "name": f"Tercero {code}", "roles": roles},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _crear_direccion(mundo, cabeceras, party_id, **overrides):
    payload = {"address": "Av. Principal", **overrides}
    r = mundo.client.post(
        f"{API}/maestros/terceros/{party_id}/addresses",
        json=payload,
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text
    return r.json()


def _crear_contacto(mundo, cabeceras, party_id, **overrides):
    payload = {"phone": "04121234567", **overrides}
    r = mundo.client.post(
        f"{API}/maestros/terceros/{party_id}/contacts",
        json=payload,
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text
    return r.json()


def _crear_cuenta(mundo, cabeceras, party_id, **overrides):
    payload = {"bank": "Banco", "account_number": "01020000000000000001", **overrides}
    r = mundo.client.post(
        f"{API}/maestros/terceros/{party_id}/bank-accounts",
        json=payload,
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_datos_tercero_flujo_completo(mundo, reloj_mfa, rol_operador):
    cabeceras = _operador(mundo, reloj_mfa, rol_operador)
    party_id = _tercero(mundo, cabeceras, ["PROVEEDOR"])

    direccion = _crear_direccion(
        mundo,
        cabeceras,
        party_id,
        is_fiscal=True,
        city="Caracas",
    )
    contacto = _crear_contacto(mundo, cabeceras, party_id, phone="04121234567")
    cuenta = _crear_cuenta(
        mundo,
        cabeceras,
        party_id,
        account_number="01020000000000000001",
    )

    r = mundo.client.get(
        f"{API}/maestros/terceros/{party_id}/addresses",
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text
    direccion_leida = next(
        item for item in r.json()["items"] if item["id"] == direccion["id"]
    )
    assert direccion_leida["city"] == "Caracas"

    r = mundo.client.get(
        f"{API}/maestros/terceros/{party_id}/contacts",
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text
    contacto_leido = next(
        item for item in r.json()["items"] if item["id"] == contacto["id"]
    )
    assert contacto_leido["phone"] == "04121234567"

    r = mundo.client.get(
        f"{API}/maestros/terceros/{party_id}/bank-accounts",
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text
    cuenta_leida = next(
        item for item in r.json()["items"] if item["id"] == cuenta["id"]
    )
    assert cuenta_leida["account_number"] == "01020000000000000001"

    r = mundo.client.patch(
        f"{API}/maestros/terceros/{party_id}/addresses/{direccion['id']}",
        json={"city": "Valencia"},
        headers={**cabeceras, "If-Match": "1"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["city"] == "Valencia"
    assert r.json()["version"] == 2


def test_marca_fiscal_desplazada_sube_version(mundo, reloj_mfa, rol_operador):
    cabeceras = _operador(mundo, reloj_mfa, rol_operador)
    party_id = _tercero(mundo, cabeceras, ["PROVEEDOR"])

    primera = _crear_direccion(mundo, cabeceras, party_id, is_fiscal=True)
    segunda = _crear_direccion(mundo, cabeceras, party_id, is_fiscal=True)

    r = mundo.client.get(
        f"{API}/maestros/terceros/{party_id}/addresses",
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text
    items = {item["id"]: item for item in r.json()["items"]}
    assert items[primera["id"]]["is_fiscal"] is False
    assert items[primera["id"]]["version"] == 2
    assert items[segunda["id"]]["is_fiscal"] is True
    assert items[segunda["id"]]["version"] == 1


def test_otro_tercero_404(mundo, reloj_mfa, rol_operador):
    cabeceras = _operador(mundo, reloj_mfa, rol_operador)
    party_uno = _tercero(mundo, cabeceras, ["CLIENTE"])
    party_dos = _tercero(mundo, cabeceras, ["CLIENTE"])

    direccion = _crear_direccion(mundo, cabeceras, party_uno)

    r = mundo.client.patch(
        f"{API}/maestros/terceros/{party_dos}/addresses/{direccion['id']}",
        json={"city": "Maracay"},
        headers={**cabeceras, "If-Match": "1"},
    )
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "PARTY_CHILD_NOT_FOUND"


def test_empresa_ajena_404(mundo, reloj_mfa, rol_operador):
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
    r = mundo.client.post(
        f"{API}/maestros/terceros/{party_externo_id}/addresses",
        json={"address": "Av. Ajena"},
        headers=cabeceras,
    )
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "PARTY_NOT_FOUND"


def test_version_desfasada_409(mundo, reloj_mfa, rol_operador):
    cabeceras = _operador(mundo, reloj_mfa, rol_operador)
    party_id = _tercero(mundo, cabeceras, ["CLIENTE"])
    direccion = _crear_direccion(mundo, cabeceras, party_id)

    r = mundo.client.patch(
        f"{API}/maestros/terceros/{party_id}/addresses/{direccion['id']}",
        json={"city": "Maracay"},
        headers={**cabeceras, "If-Match": "99"},
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "VERSION_CONFLICT"


def test_nulo_explicito_422(mundo, reloj_mfa, rol_operador):
    cabeceras = _operador(mundo, reloj_mfa, rol_operador)
    party_id = _tercero(mundo, cabeceras, ["CLIENTE"])
    direccion = _crear_direccion(mundo, cabeceras, party_id)

    r = mundo.client.patch(
        f"{API}/maestros/terceros/{party_id}/addresses/{direccion['id']}",
        json={"address": None},
        headers={**cabeceras, "If-Match": "1"},
    )
    assert r.status_code == 422, r.text


def test_contacto_vacio_422(mundo, reloj_mfa, rol_operador):
    cabeceras = _operador(mundo, reloj_mfa, rol_operador)
    party_id = _tercero(mundo, cabeceras, ["CLIENTE"])

    r = mundo.client.post(
        f"{API}/maestros/terceros/{party_id}/contacts",
        json={"role": "VENTAS"},
        headers=cabeceras,
    )
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "PARTY_CONTACT_EMPTY"


def test_verify_sin_permiso_403(mundo, reloj_mfa, rol_operador, rol_solo_lectura):
    cabeceras = _operador(mundo, reloj_mfa, rol_operador)
    party_id = _tercero(mundo, cabeceras, ["CLIENTE"])
    cuenta = _crear_cuenta(mundo, cabeceras, party_id)

    cabeceras_lectura = _operador(mundo, reloj_mfa, rol_solo_lectura)
    r = mundo.client.post(
        f"{API}/maestros/terceros/{party_id}/bank-accounts/{cuenta['id']}/verify",
        json={"evidence": "evidencia"},
        headers=cabeceras_lectura,
    )
    assert r.status_code == 403, r.text


def test_verify_enmascara_sin_edicion(mundo, reloj_mfa, rol_operador, rol_aprobador):
    cabeceras_operador = _operador(mundo, reloj_mfa, rol_operador)
    party_id = _tercero(mundo, cabeceras_operador, ["CLIENTE"])
    cuenta = _crear_cuenta(mundo, cabeceras_operador, party_id)

    cabeceras_aprobador = _operador(mundo, reloj_mfa, rol_aprobador)
    r = mundo.client.post(
        f"{API}/maestros/terceros/{party_id}/bank-accounts/{cuenta['id']}/verify",
        json={"evidence": "evidencia"},
        headers=cabeceras_aprobador,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["verified"] is True
    assert body["account_number"] == "****0001"


def test_cuenta_nueva_devuelve_supplier_a_pendiente(mundo, reloj_mfa, rol_operador):
    from app.modules.master_data.models import Supplier

    cabeceras = _operador(mundo, reloj_mfa, rol_operador)
    party_id = _tercero(mundo, cabeceras, ["PROVEEDOR"])

    db = mundo.factory()
    try:
        supplier = db.scalar(select(Supplier).where(Supplier.party_id == party_id))
        assert supplier is not None
        supplier.approval_status = "APPROVED"
        db.commit()
    finally:
        db.close()

    _crear_cuenta(mundo, cabeceras, party_id)

    db = mundo.factory()
    try:
        supplier = db.scalar(select(Supplier).where(Supplier.party_id == party_id))
        assert supplier is not None
        assert supplier.approval_status == "PENDING_APPROVAL"
    finally:
        db.close()


def test_lectura_enmascarada(mundo, reloj_mfa, rol_operador, rol_solo_lectura):
    cabeceras_operador = _operador(mundo, reloj_mfa, rol_operador)
    party_id = _tercero(mundo, cabeceras_operador, ["CLIENTE"])
    _crear_cuenta(mundo, cabeceras_operador, party_id)

    cabeceras_lectura = _operador(mundo, reloj_mfa, rol_solo_lectura)
    r = mundo.client.get(
        f"{API}/maestros/terceros/{party_id}/bank-accounts",
        headers=cabeceras_lectura,
    )
    assert r.status_code == 200, r.text
    assert r.json()["items"][0]["account_number"] == "****0001"
    assert r.json()["items"][0]["account_last4"] == "0001"
