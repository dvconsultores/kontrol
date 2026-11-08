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
            name="Terceros HTTP",
            company_id=None,
            permissions=[
                "maestros:view",
                "maestros:create",
                "maestros:deactivate",
                "ventas:view",
                "ventas:create",
                "compras:view",
                "compras:create",
                "regulatorio:view",
                "regulatorio:create",
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


def _entrar(mundo, reloj, nombre):
    from mfa_mundo import alta_por_desafio, login

    r = login(mundo.client, nombre)
    assert r.status_code == 200, r.text
    if r.json().get("status") == "AUTHENTICATED":
        return {"Authorization": f"Bearer {r.json()['access_token']}"}
    return alta_por_desafio(mundo.client, reloj, nombre).cabeceras


def _operador(mundo, reloj, rol):
    from mfa_mundo import crear_usuario

    nombre = f"terc{uuid.uuid4().hex[:12]}"
    user_id = crear_usuario(mundo, nombre)
    _dar(mundo, user_id, rol, mundo.company_id)
    cabeceras = _entrar(mundo, reloj, nombre)
    cabeceras["X-Kontrol-Company"] = str(mundo.company_id)
    return cabeceras


def _tercero(mundo, cabeceras, roles):
    code = f"T-{uuid.uuid4().hex[:12]}"
    r = mundo.client.post(
        f"{API}/maestros/terceros",
        json={
            "code": code,
            "name": f"Tercero {code}",
            "roles": roles,
        },
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_ht01_sales_quotes_party_role_required(mundo, reloj_mfa, rol_operador):
    cabeceras = _operador(mundo, reloj_mfa, rol_operador)
    proveedor = _tercero(mundo, cabeceras, ["PROVEEDOR"])
    cliente = _tercero(mundo, cabeceras, ["CLIENTE"])

    r = mundo.client.post(
        f"{API}/sales/quotes",
        json={"code": f"Q-{uuid.uuid4().hex[:12]}", "customer_id": proveedor, "currency": "VED"},
        headers=cabeceras,
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "PARTY_ROLE_REQUIRED"

    r = mundo.client.post(
        f"{API}/sales/quotes",
        json={"code": f"Q-{uuid.uuid4().hex[:12]}", "customer_id": cliente, "currency": "VED"},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text


def test_ht02_purchasing_orders_party_role_required(mundo, reloj_mfa, rol_operador):
    cabeceras = _operador(mundo, reloj_mfa, rol_operador)
    cliente = _tercero(mundo, cabeceras, ["CLIENTE"])
    proveedor = _tercero(mundo, cabeceras, ["PROVEEDOR"])

    r = mundo.client.post(
        f"{API}/purchasing/orders",
        json={"code": f"O-{uuid.uuid4().hex[:12]}", "supplier_id": cliente, "currency": "VED"},
        headers=cabeceras,
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "PARTY_ROLE_REQUIRED"

    r = mundo.client.post(
        f"{API}/purchasing/orders",
        json={"code": f"O-{uuid.uuid4().hex[:12]}", "supplier_id": proveedor, "currency": "VED"},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text


def test_ht03_deactivated_customer_sales_quotes_party_inactive(mundo, reloj_mfa, rol_operador):
    cabeceras = _operador(mundo, reloj_mfa, rol_operador)
    cliente = _tercero(mundo, cabeceras, ["CLIENTE"])

    r = mundo.client.post(f"{API}/maestros/terceros/{cliente}/deactivate", headers=cabeceras)
    assert r.status_code == 200, r.text

    r = mundo.client.post(
        f"{API}/sales/quotes",
        json={"code": f"Q-{uuid.uuid4().hex[:12]}", "customer_id": cliente, "currency": "VED"},
        headers=cabeceras,
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "PARTY_INACTIVE"


def test_ht04_sales_withholdings_suffered_role(mundo, reloj_mfa, rol_operador):
    cabeceras = _operador(mundo, reloj_mfa, rol_operador)
    cliente = _tercero(mundo, cabeceras, ["CLIENTE"])
    proveedor = _tercero(mundo, cabeceras, ["PROVEEDOR"])

    r = mundo.client.post(
        f"{API}/sales/withholdings-suffered",
        json={"party_id": cliente, "tax_type": "IVA", "amount": 5.0},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text

    r = mundo.client.post(
        f"{API}/sales/withholdings-suffered",
        json={"party_id": proveedor, "tax_type": "IVA", "amount": 5.0},
        headers=cabeceras,
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "PARTY_ROLE_REQUIRED"


def test_ht05_purchasing_withholdings_role(mundo, reloj_mfa, rol_operador):
    cabeceras = _operador(mundo, reloj_mfa, rol_operador)
    proveedor = _tercero(mundo, cabeceras, ["PROVEEDOR"])
    cliente = _tercero(mundo, cabeceras, ["CLIENTE"])

    r = mundo.client.post(
        f"{API}/purchasing/withholdings",
        json={"party_id": proveedor, "tax_type": "IVA", "amount": 5.0},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text

    r = mundo.client.post(
        f"{API}/purchasing/withholdings",
        json={"party_id": cliente, "tax_type": "IVA", "amount": 5.0},
        headers=cabeceras,
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "PARTY_ROLE_REQUIRED"


def test_ht06_collections_and_payments_party_role_required(mundo, reloj_mfa, rol_operador):
    cabeceras = _operador(mundo, reloj_mfa, rol_operador)
    proveedor = _tercero(mundo, cabeceras, ["PROVEEDOR"])
    cliente = _tercero(mundo, cabeceras, ["CLIENTE"])

    r = mundo.client.post(
        f"{API}/sales/collections",
        json={"party_id": proveedor, "amount": 10.0, "currency": "VED"},
        headers=cabeceras,
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "PARTY_ROLE_REQUIRED"

    r = mundo.client.post(
        f"{API}/purchasing/payments",
        json={"party_id": cliente, "amount": 10.0, "currency": "VED"},
        headers=cabeceras,
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "PARTY_ROLE_REQUIRED"


def test_ht07_regulatory_drivers_party_not_found(mundo, reloj_mfa, rol_operador):
    cabeceras = _operador(mundo, reloj_mfa, rol_operador)

    r = mundo.client.post(
        f"{API}/regulatory/drivers",
        json={"party_id": "00000000-0000-4000-8000-000000000999"},
        headers=cabeceras,
    )
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "PARTY_NOT_FOUND"
