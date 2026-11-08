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
def rol_completo(mundo):
    from app.modules.identity_access import service as identity_service

    db = mundo.factory()
    try:
        rol = identity_service.create_role(
            db,
            tenant_id=mundo.tenant_id,
            code=f"imp{uuid.uuid4().hex[:12]}",
            name="Importaciones Completo",
            company_id=None,
            permissions=[
                "maestros:view",
                "maestros:create",
                "maestros:edit",
                "compras:view",
                "compras:create",
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
            code=f"lec{uuid.uuid4().hex[:12]}",
            name="Import Solo Lectura",
            company_id=None,
            permissions=["compras:view"],
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

    nombre = f"imp{uuid.uuid4().hex[:12]}"
    user_id = crear_usuario(mundo, nombre)
    _dar(mundo, user_id, rol, mundo.company_id)
    cabeceras = _entrar(mundo, reloj_mfa, nombre)
    cabeceras["X-Kontrol-Company"] = str(mundo.company_id)
    return cabeceras


def _proveedor(mundo, cabeceras):
    code = f"P-{uuid.uuid4().hex[:12]}"
    payload = {
        "code": code,
        "name": f"Proveedor {code}",
        "roles": ["PROVEEDOR"],
        "status": "ACTIVE",
    }
    r = mundo.client.post(
        f"{API}/maestros/terceros", json=payload, headers=cabeceras
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _cliente(mundo, cabeceras):
    code = f"C-{uuid.uuid4().hex[:12]}"
    payload = {
        "code": code,
        "name": f"Cliente {code}",
        "roles": ["CLIENTE"],
        "status": "ACTIVE",
    }
    r = mundo.client.post(
        f"{API}/maestros/terceros", json=payload, headers=cabeceras
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _crear_expediente(mundo, cabeceras, supplier_id, code=None, negociacion=True):
    code = code or f"IMP-{uuid.uuid4().hex[:12]}"
    payload = {"code": code, "supplier_id": supplier_id, "currency": "VED"}
    if negociacion:
        payload.update(
            {
                "incoterm": "CIF",
                "payment_conditions": "Pago a 30 días",
                "delivery_conditions": "Entrega en puerto",
                "expected_arrival_date": "2025-01-15",
            }
        )
    r = mundo.client.post(
        f"{API}/importaciones", json=payload, headers=cabeceras
    )
    assert r.status_code == 200, r.text
    return r.json()


def _crear_orden(
    mundo,
    company_id,
    supplier_id,
    currency="VED",
    status="APPROVED",
):
    from app.modules.purchasing.models import PurchaseOrder

    db = mundo.factory()
    try:
        order = PurchaseOrder(
            company_id=company_id,
            code=f"OC-{uuid.uuid4().hex[:12]}",
            supplier_id=supplier_id,
            currency=currency,
            status=status,
        )
        db.add(order)
        db.commit()
        return order.id
    finally:
        db.close()


def _adjuntar_documento(mundo, company_id, document_id):
    from app.modules.documents.models import DocumentLink

    db = mundo.factory()
    try:
        link = DocumentLink(
            document_id=str(uuid.uuid4()),
            company_id=company_id,
            resource_type="ImportDocument",
            resource_id=document_id,
            role="ATTACHMENT",
        )
        db.add(link)
        db.commit()
    finally:
        db.close()


def test_flujo_de_importacion(mundo, reloj_mfa, rol_completo):
    cabeceras = _operador(mundo, reloj_mfa, rol_completo)
    supplier_id = _proveedor(mundo, cabeceras)

    file_resp = _crear_expediente(mundo, cabeceras, supplier_id, negociacion=False)
    file_id = file_resp["id"]
    assert file_resp["status"] == "NEGOTIATING"
    r = mundo.client.get(f"{API}/importaciones", params={"q": file_resp["code"]}, headers=cabeceras)
    assert r.status_code == 200, r.text
    assert [item["id"] for item in r.json()["items"]] == [file_id]
    assert r.json()["items"][0]["supplier_name"]
    assert len(file_resp["documents"]) == 3
    assert {doc["kind"] for doc in file_resp["documents"]} == {
        "PROFORMA_INVOICE",
        "PACKING_LIST",
        "SHIPPING_DOCUMENT",
    }
    version = file_resp["version"]

    # Intentar vincular sin negociación completa
    order_id = _crear_orden(mundo, mundo.company_id, supplier_id)
    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/order",
        json={"order_id": str(order_id)},
        headers=cabeceras,
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "IMPORT_NEGOTIATION_INCOMPLETE"
    assert "missing" in r.json()["details"]

    # Completar negociación
    r = mundo.client.patch(
        f"{API}/importaciones/{file_id}",
        json={
            "incoterm": "CIF",
            "payment_conditions": "Pago a 30 días",
            "delivery_conditions": "Entrega en puerto",
        },
        headers={**cabeceras, "If-Match": str(version)},
    )
    assert r.status_code == 200, r.text
    version = r.json()["version"]

    # Vincular orden
    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/order",
        json={"order_id": str(order_id)},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "ORDERED"
    version = r.json()["version"]

    # Confirmar sin validar documentos
    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/confirm-documents",
        headers=cabeceras,
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "IMPORT_DOCUMENTS_INCOMPLETE"
    assert len(r.json()["details"]["missing"]) == 3

    # Recibir, adjuntar y validar cada obligatorio
    r = mundo.client.get(f"{API}/importaciones/{file_id}", headers=cabeceras)
    assert r.status_code == 200, r.text
    detail = r.json()

    for doc in detail["documents"]:
        doc_id = doc["id"]
        receive_body = {"reference": f"REF-{uuid.uuid4().hex[:8]}"}
        r = mundo.client.post(
            f"{API}/importaciones/{file_id}/documents/{doc_id}/receive",
            json=receive_body,
            headers=cabeceras,
        )
        assert r.status_code == 200, r.text

        _adjuntar_documento(mundo, mundo.company_id, doc_id)

        r = mundo.client.post(
            f"{API}/importaciones/{file_id}/documents/{doc_id}/validate",
            headers=cabeceras,
        )
        assert r.status_code == 200, r.text

    # Confirmar documentación
    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/confirm-documents",
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "DOCUMENTS_COMPLETE"

    # Auditoría
    r = mundo.client.get(f"{API}/importaciones/{file_id}/audit", headers=cabeceras)
    assert r.status_code == 200, r.text
    acciones = [item["action"] for item in r.json()["items"]]
    assert "IMPORT_DOCUMENTS_CONFIRMED" in acciones


def test_empresa_ajena_404(mundo, reloj_mfa, rol_completo):
    from app.modules.imports.models import ImportFile
    from app.modules.organization.models import Company

    cabeceras = _operador(mundo, reloj_mfa, rol_completo)
    db = mundo.factory()
    file_externo_id = None
    try:
        empresa_b = db.scalar(
            select(Company).where(Company.tenant_id == mundo.tenant_b_id)
        )
        assert empresa_b is not None
        file_externo = ImportFile(
            company_id=empresa_b.id,
            code=f"EXT-{uuid.uuid4().hex[:8]}",
            supplier_id=str(uuid.uuid4()),
            currency="VED",
            status="NEGOTIATING",
        )
        db.add(file_externo)
        db.commit()
        file_externo_id = str(file_externo.id)
    finally:
        db.close()

    r = mundo.client.get(
        f"{API}/importaciones/{file_externo_id}", headers=cabeceras
    )
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "IMPORT_NOT_FOUND"


def test_orden_otro_proveedor_409(mundo, reloj_mfa, rol_completo):
    cabeceras = _operador(mundo, reloj_mfa, rol_completo)
    supplier_a = _proveedor(mundo, cabeceras)
    supplier_b = _proveedor(mundo, cabeceras)

    file_resp = _crear_expediente(mundo, cabeceras, supplier_a)
    file_id = file_resp["id"]

    order_other = _crear_orden(mundo, mundo.company_id, supplier_b)

    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/order",
        json={"order_id": str(order_other)},
        headers=cabeceras,
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "IMPORT_ORDER_SUPPLIER_MISMATCH"


def test_orden_no_aprobada_409(mundo, reloj_mfa, rol_completo):
    cabeceras = _operador(mundo, reloj_mfa, rol_completo)
    supplier = _proveedor(mundo, cabeceras)

    file_resp = _crear_expediente(mundo, cabeceras, supplier)
    file_id = file_resp["id"]

    order_draft = _crear_orden(
        mundo, mundo.company_id, supplier, status="DRAFT"
    )

    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/order",
        json={"order_id": str(order_draft)},
        headers=cabeceras,
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "IMPORT_ORDER_NOT_APPROVED"


def test_orden_en_uso_409_y_cancelar_libera(mundo, reloj_mfa, rol_completo):
    cabeceras = _operador(mundo, reloj_mfa, rol_completo)
    supplier = _proveedor(mundo, cabeceras)

    file_1 = _crear_expediente(mundo, cabeceras, supplier)
    file_2 = _crear_expediente(mundo, cabeceras, supplier)

    order_id = _crear_orden(mundo, mundo.company_id, supplier)

    r = mundo.client.post(
        f"{API}/importaciones/{file_1['id']}/order",
        json={"order_id": str(order_id)},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text

    r = mundo.client.post(
        f"{API}/importaciones/{file_2['id']}/order",
        json={"order_id": str(order_id)},
        headers=cabeceras,
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "IMPORT_ORDER_IN_USE"

    # Cancelar file_1 libera la orden
    r = mundo.client.post(
        f"{API}/importaciones/{file_1['id']}/cancel",
        json={"reason": "Cancelación para liberar orden"},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "CANCELLED"

    r = mundo.client.post(
        f"{API}/importaciones/{file_2['id']}/order",
        json={"order_id": str(order_id)},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text


def test_validar_sin_adjunto_409(mundo, reloj_mfa, rol_completo):
    cabeceras = _operador(mundo, reloj_mfa, rol_completo)
    supplier = _proveedor(mundo, cabeceras)

    file_resp = _crear_expediente(mundo, cabeceras, supplier)
    file_id = file_resp["id"]

    # Obtener documento obligatorio
    r = mundo.client.get(f"{API}/importaciones/{file_id}", headers=cabeceras)
    assert r.status_code == 200, r.text
    doc = r.json()["documents"][0]

    # Recibir documento
    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/documents/{doc['id']}/receive",
        json={"reference": "REF-001"},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text

    # Validar sin adjunto
    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/documents/{doc['id']}/validate",
        headers=cabeceras,
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "IMPORT_DOCUMENT_WITHOUT_FILE"


def test_version_desfasada_409(mundo, reloj_mfa, rol_completo):
    cabeceras = _operador(mundo, reloj_mfa, rol_completo)
    supplier = _proveedor(mundo, cabeceras)

    file_resp = _crear_expediente(mundo, cabeceras, supplier)
    file_id = file_resp["id"]
    version = file_resp["version"]

    # Primera actualización válida
    r = mundo.client.patch(
        f"{API}/importaciones/{file_id}",
        json={"notes": "Primera actualización"},
        headers={**cabeceras, "If-Match": str(version)},
    )
    assert r.status_code == 200, r.text

    # Segunda con versión antigua
    r = mundo.client.patch(
        f"{API}/importaciones/{file_id}",
        json={"notes": "Segunda actualización"},
        headers={**cabeceras, "If-Match": str(version)},
    )
    assert r.status_code == 409, r.text


def test_sin_permiso_403(mundo, reloj_mfa, rol_completo, rol_solo_lectura):
    cabeceras_completo = _operador(mundo, reloj_mfa, rol_completo)
    cabeceras_lectura = _operador(mundo, reloj_mfa, rol_solo_lectura)
    supplier = _proveedor(mundo, cabeceras_completo)

    file_resp = _crear_expediente(mundo, cabeceras_completo, supplier)
    file_id = file_resp["id"]

    # Solo lectura no puede crear
    r = mundo.client.post(
        f"{API}/importaciones",
        json={
            "code": f"IMP-{uuid.uuid4().hex[:12]}",
            "supplier_id": supplier,
            "currency": "VED",
        },
        headers=cabeceras_lectura,
    )
    assert r.status_code == 403, r.text

    # compras:create no puede confirmar la documentación
    db = mundo.factory()
    try:
        from app.modules.identity_access import service as identity_service

        rol = identity_service.create_role(
            db,
            tenant_id=mundo.tenant_id,
            code=f"cre{uuid.uuid4().hex[:12]}",
            name="Import Alta",
            company_id=None,
            permissions=["compras:view", "compras:create"],
            actor=mundo.admin_id,
        )
        db.commit()
    finally:
        db.close()
    cabeceras_alta = _operador(mundo, reloj_mfa, rol["id"])
    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/confirm-documents",
        headers=cabeceras_alta,
    )
    assert r.status_code == 403, r.text


def test_proveedor_cliente_409(mundo, reloj_mfa, rol_completo):
    cabeceras = _operador(mundo, reloj_mfa, rol_completo)
    cliente = _cliente(mundo, cabeceras)

    r = mundo.client.post(
        f"{API}/importaciones",
        json={
            "code": f"IMP-{uuid.uuid4().hex[:12]}",
            "supplier_id": cliente,
            "currency": "VED",
        },
        headers=cabeceras,
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "PARTY_ROLE_REQUIRED"
