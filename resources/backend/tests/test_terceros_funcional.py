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
            code=f"tercf{uuid.uuid4().hex[:12]}",
            name="Terceros Funcional",
            company_id=None,
            permissions=[
                "maestros:view",
                "maestros:create",
                "maestros:edit",
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


@pytest.fixture(scope="module")
def rol_solo_lectura(mundo):
    from app.modules.identity_access import service as identity_service

    db = mundo.factory()
    try:
        rol = identity_service.create_role(
            db,
            tenant_id=mundo.tenant_id,
            code=f"tercr{uuid.uuid4().hex[:12]}",
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


def _entrar(mundo, reloj, nombre):
    from mfa_mundo import alta_por_desafio, login

    r = login(mundo.client, nombre)
    assert r.status_code == 200, r.text
    if r.json().get("status") == "AUTHENTICATED":
        return {"Authorization": f"Bearer {r.json()['access_token']}"}
    return alta_por_desafio(mundo.client, reloj, nombre).cabeceras


def _operador(mundo, reloj, rol, company_id=None):
    from mfa_mundo import crear_usuario

    nombre = f"tercf{uuid.uuid4().hex[:12]}"
    user_id = crear_usuario(mundo, nombre)
    company_id = company_id or mundo.company_id
    _dar(mundo, user_id, rol, company_id)
    cabeceras = _entrar(mundo, reloj, nombre)
    cabeceras["X-Kontrol-Company"] = str(company_id)
    return cabeceras


def _crear_tercero(mundo, cabeceras, *, roles=None, name=None, tax_id=None, person_type="JURIDICA"):
    payload = {
        "code": f"TF-{uuid.uuid4().hex[:12]}",
        "name": name or f"Funcional {uuid.uuid4().hex[:8]}",
        "person_type": person_type,
        "nationality": "VE",
        "residence": "VE",
        "tax_id": tax_id or f"J-{uuid.uuid4().int % 100000000:08d}-1",
        "roles": roles or ["CLIENTE"],
    }
    r = mundo.client.post(f"{API}/maestros/terceros", json=payload, headers=cabeceras)
    assert r.status_code == 200, r.text
    return r.json()


def _tercero_id(mundo, cabeceras, **kwargs):
    return _crear_tercero(mundo, cabeceras, **kwargs)["id"]


def test_tf01_flujo_principal_party(mundo, reloj_mfa, rol_operador):
    cabeceras = _operador(mundo, reloj_mfa, rol_operador)
    payload = {
        "code": f"TF-{uuid.uuid4().hex[:12]}",
        "name": "Tercero Funcional Principal",
        "person_type": "JURIDICA",
        "nationality": "VE",
        "residence": "VE",
        "tax_id": f"J-{uuid.uuid4().int % 100000000:08d}-1",
        "roles": ["cliente"],
    }

    r = mundo.client.post(f"{API}/maestros/terceros", json=payload, headers=cabeceras)
    assert r.status_code == 200, r.text
    party = r.json()
    assert party["roles"] == ["CLIENTE"]
    assert party["nationality"] == "VE"
    assert party["version"] == 1
    party_id = party["id"]

    r = mundo.client.get(f"{API}/maestros/terceros/{party_id}", headers=cabeceras)
    assert r.status_code == 200, r.text
    assert r.json()["blocking_documents"] == []
    assert r.json()["allowed_actions"]["delete"] is True

    r = mundo.client.patch(
        f"{API}/maestros/terceros/{party_id}",
        json={"name": "Nuevo"},
        headers={**cabeceras, "If-Match": "1"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["version"] == 2

    r = mundo.client.post(f"{API}/maestros/terceros/{party_id}/deactivate", headers=cabeceras)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "INACTIVE"

    r = mundo.client.post(f"{API}/maestros/terceros/{party_id}/activate", headers=cabeceras)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "ACTIVE"

    r = mundo.client.get(
        f"{API}/maestros/terceros",
        params={"status": "ACTIVE", "page": 1, "page_size": 10},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text
    assert any(item["id"] == party_id for item in r.json()["items"])


def test_tf02_roles_de_party(mundo, reloj_mfa, rol_operador):
    cabeceras = _operador(mundo, reloj_mfa, rol_operador)
    party = _crear_tercero(mundo, cabeceras, roles=["CLIENTE"], tax_id=f"J-{uuid.uuid4().int % 100000000:08d}-1")
    party_id = party["id"]

    r = mundo.client.post(f"{API}/maestros/terceros/{party_id}/roles/PROVEEDOR", headers=cabeceras)
    assert r.status_code == 200, r.text
    assert r.json()["roles"] == ["CLIENTE", "PROVEEDOR"]
    assert r.json()["id"] == party_id

    r = mundo.client.get(
        f"{API}/maestros/terceros",
        params={"role": "PROVEEDOR", "page": 1, "page_size": 10},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text
    assert any(item["id"] == party_id for item in r.json()["items"])

    db = mundo.factory()
    try:
        from app.modules.master_data.models import Customer, Supplier

        customer = db.scalar(select(Customer).where(Customer.party_id == party_id))
        supplier = db.scalar(select(Supplier).where(Supplier.party_id == party_id))
        assert customer is not None
        assert supplier is not None
        assert supplier.approval_status == "PENDING_APPROVAL"
    finally:
        db.close()

    r = mundo.client.delete(f"{API}/maestros/terceros/{party_id}/roles/PROVEEDOR", headers=cabeceras)
    assert r.status_code == 200, r.text
    assert r.json()["roles"] == ["CLIENTE"]

    db = mundo.factory()
    try:
        from app.modules.master_data.models import Supplier

        supplier = db.scalar(select(Supplier).where(Supplier.party_id == party_id))
        assert supplier is not None
    finally:
        db.close()

    r = mundo.client.delete(f"{API}/maestros/terceros/{party_id}/roles/CLIENTE", headers=cabeceras)
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "PARTY_LAST_ROLE"


def test_tf03_negativa_otra_empresa(mundo, reloj_mfa, rol_operador):
    from app.modules.master_data.models import Party
    from app.modules.organization.models import Company

    cabeceras = _operador(mundo, reloj_mfa, rol_operador)

    db = mundo.factory()
    try:
        empresa_b = db.scalar(select(Company).where(Company.tenant_id == mundo.tenant_b_id))
        assert empresa_b is not None
        ajeno = Party(
            company_id=empresa_b.id,
            code=f"AJ-{uuid.uuid4().hex[:8]}",
            name="Ajeno",
            roles=["CLIENTE"],
            status="ACTIVE",
        )
        db.add(ajeno)
        db.commit()
        ajeno_id = ajeno.id
    finally:
        db.close()

    r = mundo.client.get(f"{API}/maestros/terceros/{ajeno_id}", headers=cabeceras)
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "PARTY_NOT_FOUND"

    r = mundo.client.patch(
        f"{API}/maestros/terceros/{ajeno_id}",
        json={"name": "Intruso"},
        headers={**cabeceras, "If-Match": "1"},
    )
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "PARTY_NOT_FOUND"

    r = mundo.client.post(f"{API}/maestros/terceros/{ajeno_id}/deactivate", headers=cabeceras)
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "PARTY_NOT_FOUND"

    r = mundo.client.delete(f"{API}/maestros/terceros/{ajeno_id}", headers=cabeceras)
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "PARTY_NOT_FOUND"

    db = mundo.factory()
    try:
        ajeno_tras = db.get(Party, ajeno_id)
        assert ajeno_tras is not None
        assert ajeno_tras.name == "Ajeno"
        assert ajeno_tras.status == "ACTIVE"
    finally:
        db.close()


def test_tf04_negativa_rif_duplicado_y_rol_invalido(mundo, reloj_mfa, rol_operador):
    cabeceras = _operador(mundo, reloj_mfa, rol_operador)
    tax_id = f"J-{uuid.uuid4().int % 100000000:08d}-1"
    primer = _crear_tercero(mundo, cabeceras, roles=["CLIENTE"], tax_id=tax_id)
    party_id = primer["id"]

    r = mundo.client.post(
        f"{API}/maestros/terceros",
        json={
            "code": f"TF-{uuid.uuid4().hex[:12]}",
            "name": "Cliente Duplicado",
            "person_type": "JURIDICA",
            "nationality": "VE",
            "residence": "VE",
            "tax_id": tax_id,
            "roles": ["CLIENTE"],
        },
        headers=cabeceras,
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "PARTY_DUPLICATE_TAX_ID"

    r = mundo.client.post(
        f"{API}/maestros/terceros",
        json={
            "code": f"TF-{uuid.uuid4().hex[:12]}",
            "name": "Proveedor Duplicado",
            "person_type": "JURIDICA",
            "nationality": "VE",
            "residence": "VE",
            "tax_id": tax_id,
            "roles": ["PROVEEDOR"],
        },
        headers=cabeceras,
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "PARTY_TAX_ID_EXISTS"
    assert r.json()["details"]["party_id"] == party_id

    r = mundo.client.post(f"{API}/maestros/terceros/{party_id}/roles/XX", headers=cabeceras)
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "PARTY_ROLE_INVALID"


def test_tf05_negativa_documento_activo(mundo, reloj_mfa, rol_operador):
    cabeceras = _operador(mundo, reloj_mfa, rol_operador)
    party = _crear_tercero(mundo, cabeceras, roles=["CLIENTE", "PROVEEDOR"], tax_id=f"J-{uuid.uuid4().int % 100000000:08d}-1")
    party_id = party["id"]

    r = mundo.client.post(
        f"{API}/sales/quotes",
        json={"code": f"Q-{uuid.uuid4().hex[:12]}", "customer_id": party_id, "currency": "VED"},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text

    r = mundo.client.post(f"{API}/maestros/terceros/{party_id}/deactivate", headers=cabeceras)
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "PARTY_HAS_ACTIVE_DOCUMENTS"
    assert r.json()["details"]["documents"]

    r = mundo.client.get(f"{API}/maestros/terceros/{party_id}", headers=cabeceras)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "ACTIVE"

    r = mundo.client.delete(f"{API}/maestros/terceros/{party_id}", headers=cabeceras)
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "PARTY_HAS_RELATIONS"

    r = mundo.client.delete(f"{API}/maestros/terceros/{party_id}/roles/CLIENTE", headers=cabeceras)
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "PARTY_ROLE_IN_USE"


def test_tf06_negativa_control_de_version(mundo, reloj_mfa, rol_operador):
    cabeceras = _operador(mundo, reloj_mfa, rol_operador)
    party = _crear_tercero(mundo, cabeceras, roles=["CLIENTE"], tax_id=f"J-{uuid.uuid4().int % 100000000:08d}-1")
    party_id = party["id"]

    r = mundo.client.patch(
        f"{API}/maestros/terceros/{party_id}",
        json={"name": "Primer Cambio"},
        headers={**cabeceras, "If-Match": "1"},
    )
    assert r.status_code == 200, r.text

    r = mundo.client.patch(
        f"{API}/maestros/terceros/{party_id}",
        json={"name": "Segundo Cambio"},
        headers={**cabeceras, "If-Match": "1"},
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "VERSION_CONFLICT"

    r = mundo.client.patch(f"{API}/maestros/terceros/{party_id}", json={"name": "Sin Versión"}, headers=cabeceras)
    assert r.status_code == 428, r.text
    assert r.json()["code"] == "VERSION_REQUIRED"


def test_tf07_negativa_permisos(mundo, reloj_mfa, rol_operador, rol_solo_lectura):
    cabeceras_operador = _operador(mundo, reloj_mfa, rol_operador)
    party = _crear_tercero(mundo, cabeceras_operador, roles=["CLIENTE"], tax_id=f"J-{uuid.uuid4().int % 100000000:08d}-1")
    party_id = party["id"]

    cabeceras_lectura = _operador(mundo, reloj_mfa, rol_solo_lectura)

    r = mundo.client.get(f"{API}/maestros/terceros/{party_id}", headers=cabeceras_lectura)
    assert r.status_code == 200, r.text

    r = mundo.client.patch(
        f"{API}/maestros/terceros/{party_id}",
        json={"name": "Sin Permiso"},
        headers={**cabeceras_lectura, "If-Match": "1"},
    )
    assert r.status_code == 403, r.text

    r = mundo.client.post(
        f"{API}/maestros/terceros",
        json={
            "code": f"TF-{uuid.uuid4().hex[:12]}",
            "name": "Sin Permiso",
            "person_type": "JURIDICA",
            "nationality": "VE",
            "residence": "VE",
            "tax_id": f"J-{uuid.uuid4().int % 100000000:08d}-1",
            "roles": ["CLIENTE"],
        },
        headers=cabeceras_lectura,
    )
    assert r.status_code == 403, r.text


def test_tf08_evento_de_auditoria_creacion(mundo, reloj_mfa, rol_operador):
    cabeceras = _operador(mundo, reloj_mfa, rol_operador)
    party = _crear_tercero(mundo, cabeceras, roles=["CLIENTE"], tax_id=f"J-{uuid.uuid4().int % 100000000:08d}-1")
    party_id = party["id"]

    db = mundo.factory()
    try:
        from app.modules.audit.models import AuditEvent

        eventos = db.scalars(
            select(AuditEvent).where(
                AuditEvent.entity_type == "Party",
                AuditEvent.entity_id == party_id,
                AuditEvent.action == "PARTY_CREATED",
            )
        ).all()
        assert len(eventos) >= 1
    finally:
        db.close()
