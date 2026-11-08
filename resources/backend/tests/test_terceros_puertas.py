import uuid

import pytest

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
                "compras:view",
                "compras:create",
                "compras:approve",
                "ventas:view",
                "ventas:create",
                "ventas:apply",
            ],
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


def _rif():
    return f"J-{uuid.uuid4().int % 100000000:08d}-1"


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


def _pago_submitted(mundo, cabeceras, party_id):
    r = mundo.client.post(
        f"{API}/purchasing/payments",
        json={"party_id": party_id, "amount": 100},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text
    payment_id = r.json()["id"]
    r = mundo.client.post(
        f"{API}/purchasing/payments/{payment_id}/transition",
        json={"target": "SUBMITTED"},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text
    return payment_id


def _fetch_payment_status(mundo, cabeceras, payment_id):
    r = mundo.client.get(
        f"{API}/purchasing/payments",
        params={"status": "SUBMITTED"},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    for item in items:
        if item["id"] == payment_id:
            return item["status"]
    return None


def test_pago_solo_a_proveedor_aprobado(mundo, reloj_mfa, rol_operador):
    cabeceras = _operador(mundo, reloj_mfa, rol_operador)
    party_id = _tercero(mundo, cabeceras, ["PROVEEDOR"], tax_id=_rif())

    r = mundo.client.post(
        f"{API}/purchasing/payments",
        json={"party_id": party_id, "amount": 100},
        headers=cabeceras,
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "SUPPLIER_NOT_APPROVED"

    r = mundo.client.post(
        f"{API}/purchasing/advances",
        json={"party_id": party_id, "amount": 100},
        headers=cabeceras,
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "SUPPLIER_NOT_APPROVED"

    cuenta = _crear_cuenta(mundo, cabeceras, party_id)
    r = mundo.client.post(
        f"{API}/maestros/terceros/{party_id}/bank-accounts/{cuenta['id']}/verify",
        json={"evidence": "constancia"},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text
    r = mundo.client.post(
        f"{API}/maestros/terceros/{party_id}/roles/PROVEEDOR/approve",
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text

    r = mundo.client.post(
        f"{API}/purchasing/payments",
        json={"party_id": party_id, "amount": 100},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text
    payment = r.json()
    assert payment["status"] == "DRAFT"
    payment_id = payment["id"]

    r = mundo.client.post(
        f"{API}/purchasing/payments/{payment_id}/transition",
        json={"target": "SUBMITTED"},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text

    r = mundo.client.post(
        f"{API}/maestros/terceros/{party_id}/roles/PROVEEDOR/reject",
        json={"reason": "revisión"},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text

    r = mundo.client.post(
        f"{API}/purchasing/payments/{payment_id}/transition",
        json={"target": "APPROVED"},
        headers=cabeceras,
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "SUPPLIER_NOT_APPROVED"

    assert _fetch_payment_status(mundo, cabeceras, payment_id) == "SUBMITTED"

    r = mundo.client.post(
        f"{API}/maestros/terceros/{party_id}/roles/PROVEEDOR/resubmit",
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text
    r = mundo.client.post(
        f"{API}/maestros/terceros/{party_id}/roles/PROVEEDOR/approve",
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text

    r = mundo.client.post(
        f"{API}/purchasing/payments/{payment_id}/transition",
        json={"target": "APPROVED"},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text


def test_rechazar_pago_de_proveedor_no_aprobado(mundo, reloj_mfa, rol_operador):
    cabeceras = _operador(mundo, reloj_mfa, rol_operador)
    party_id = _tercero(mundo, cabeceras, ["PROVEEDOR"], tax_id=_rif())
    cuenta = _crear_cuenta(mundo, cabeceras, party_id)
    r = mundo.client.post(
        f"{API}/maestros/terceros/{party_id}/bank-accounts/{cuenta['id']}/verify",
        json={"evidence": "constancia"},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text
    r = mundo.client.post(
        f"{API}/maestros/terceros/{party_id}/roles/PROVEEDOR/approve",
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text

    payment_id = _pago_submitted(mundo, cabeceras, party_id)

    r = mundo.client.post(
        f"{API}/maestros/terceros/{party_id}/roles/PROVEEDOR/reject",
        json={"reason": "revisión"},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text

    r = mundo.client.post(
        f"{API}/purchasing/payments/{payment_id}/transition",
        json={"target": "REJECTED"},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text


def test_cobro_no_exige_aprobacion(mundo, reloj_mfa, rol_operador):
    cabeceras = _operador(mundo, reloj_mfa, rol_operador)
    party_id = _tercero(mundo, cabeceras, ["CLIENTE", "PROVEEDOR"], tax_id=_rif())

    r = mundo.client.post(
        f"{API}/sales/collections",
        json={"party_id": party_id, "amount": 100},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text


def test_cliente_bloqueado_sin_documentos_nuevos(mundo, reloj_mfa, rol_operador):
    cabeceras = _operador(mundo, reloj_mfa, rol_operador)
    party_id = _tercero(mundo, cabeceras, ["CLIENTE"])

    r = mundo.client.post(
        f"{API}/sales/quotes",
        json={"code": f"C-{uuid.uuid4().hex[:12]}", "customer_id": party_id},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text

    r = mundo.client.put(
        f"{API}/maestros/terceros/{party_id}/customer",
        json={"blocked": True, "block_reason": "Deuda"},
        headers={**cabeceras, "If-Match": "1"},
    )
    assert r.status_code == 200, r.text

    r = mundo.client.post(
        f"{API}/sales/quotes",
        json={"code": f"C-{uuid.uuid4().hex[:12]}", "customer_id": party_id},
        headers=cabeceras,
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "CUSTOMER_BLOCKED"

    r = mundo.client.put(
        f"{API}/maestros/terceros/{party_id}/customer",
        json={"blocked": False},
        headers={**cabeceras, "If-Match": "2"},
    )
    assert r.status_code == 200, r.text

    r = mundo.client.post(
        f"{API}/sales/quotes",
        json={"code": f"C-{uuid.uuid4().hex[:12]}", "customer_id": party_id},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text
