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


@pytest.fixture(scope="module")
def rol_sin_aprobacion(mundo):
    from app.modules.identity_access import service as identity_service

    db = mundo.factory()
    try:
        rol = identity_service.create_role(
            db,
            tenant_id=mundo.tenant_id,
            code=f"rev{uuid.uuid4().hex[:12]}",
            name="Import Revisor",
            company_id=None,
            permissions=["compras:view", "compras:create"],
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


def _aprobar_proveedor(mundo, supplier_id):
    from app.modules.master_data.models import Supplier

    db = mundo.factory()
    try:
        stmt = select(Supplier).where(
            Supplier.party_id == supplier_id,
        )
        supplier = db.scalar(stmt)
        assert supplier is not None
        supplier.approval_status = "APPROVED"
        db.commit()
    finally:
        db.close()


def _almacen(mundo, company_id, code=None):
    from app.modules.organization.models import Warehouse

    db = mundo.factory()
    try:
        warehouse = Warehouse(
            company_id=company_id,
            code=code or f"W-{uuid.uuid4().hex[:12]}",
            name=f"Almacén {code or uuid.uuid4().hex[:12]}",
            warehouse_type="PHYSICAL",
            status="ACTIVE",
        )
        db.add(warehouse)
        db.commit()
        db.refresh(warehouse)
        return warehouse.id
    finally:
        db.close()


def _hasta_despachado(mundo, reloj_mfa, rol_completo):
    cabeceras = _operador(mundo, reloj_mfa, rol_completo)
    supplier_id = _proveedor(mundo, cabeceras)
    _aprobar_proveedor(mundo, supplier_id)
    file_payload = _crear_expediente(mundo, cabeceras, supplier_id)
    file_id = file_payload["id"]

    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/order",
        json={"order_id": _crear_orden(mundo, mundo.company_id, supplier_id, status="APPROVED")},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text

    for doc in r.json()["documents"]:
        _adjuntar_documento(mundo, mundo.company_id, doc["id"])
        r = mundo.client.post(
            f"{API}/importaciones/{file_id}/documents/{doc['id']}/receive",
            json={"reference": "REF"},
            headers=cabeceras,
        )
        assert r.status_code == 200, r.text
        r = mundo.client.post(
            f"{API}/importaciones/{file_id}/documents/{doc['id']}/validate",
            headers=cabeceras,
        )
        assert r.status_code == 200, r.text

    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/confirm-documents",
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text

    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/tracking",
        json={"milestone": "DEPARTED", "occurred_on": "2026-11-01"},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text

    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/confirm-dispatch",
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text
    return cabeceras, file_id, supplier_id



def test_recepcion_despachado_flujo(mundo, reloj_mfa, rol_completo):
    cabeceras, file_id, _ = _hasta_despachado(mundo, reloj_mfa, rol_completo)
    warehouse_id = _almacen(mundo, mundo.company_id)

    r = mundo.client.get(f"{API}/importaciones/{file_id}", headers=cabeceras)
    assert r.status_code == 200, r.text
    payload = r.json()
    assert payload["logistics"]["stage"] == "NO_RECEIPT"
    assert payload["allowed_actions"]["create_receipt"] is True

    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/receipts",
        json={"code": "REC-001", "warehouse_id": warehouse_id, "packages_declared": 10},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text
    payload = r.json()
    assert payload["logistics"]["stage"] == "AWAITING_ARRIVAL"
    receipt_id = payload["logistics"]["receipts"][0]["id"]

    r = mundo.client.post(
        f"{API}/purchasing/receipts/{receipt_id}/arrival",
        json={},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text

    r = mundo.client.get(f"{API}/importaciones/{file_id}", headers=cabeceras)
    assert r.status_code == 200, r.text
    assert r.json()["logistics"]["stage"] == "RECEIVING"

    r = mundo.client.get(f"{API}/importaciones/{file_id}/audit", headers=cabeceras)
    assert r.status_code == 200, r.text
    assert any(
        event.get("action") == "IMPORT_RECEIPT_CREATED"
        for event in r.json().get("items", [])
    )


def test_negativo_recepcion_expediente_inexistente(mundo, reloj_mfa, rol_completo):
    cabeceras, file_id, _ = _hasta_despachado(mundo, reloj_mfa, rol_completo)
    otras_cabeceras = cabeceras.copy()
    otras_cabeceras["X-Kontrol-Company"] = str(uuid.uuid4())
    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/receipts",
        json={"code": "REC-ERR", "warehouse_id": str(uuid.uuid4()), "packages_declared": 10},
        headers=otras_cabeceras,
    )
    assert r.status_code == 404, r.text


def test_negativo_warehouse_not_found(mundo, reloj_mfa, rol_completo):
    cabeceras, file_id, _ = _hasta_despachado(mundo, reloj_mfa, rol_completo)
    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/receipts",
        json={"code": "REC-ERR", "warehouse_id": str(uuid.uuid4()), "packages_declared": 10},
        headers=cabeceras,
    )
    assert r.status_code == 404, r.text
    assert "WAREHOUSE_NOT_FOUND" in r.text


def test_negativo_crear_recepcion_ordered(mundo, reloj_mfa, rol_completo):
    cabeceras = _operador(mundo, reloj_mfa, rol_completo)
    supplier_id = _proveedor(mundo, cabeceras)
    _aprobar_proveedor(mundo, supplier_id)
    file_payload = _crear_expediente(mundo, cabeceras, supplier_id)
    file_id = file_payload["id"]
    warehouse_id = _almacen(mundo, mundo.company_id)
    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/receipts",
        json={"code": "REC-ERR", "warehouse_id": warehouse_id, "packages_declared": 10},
        headers=cabeceras,
    )
    assert r.status_code == 409, r.text
    assert "IMPORT_INVALID_STATE" in r.text


def test_negativo_sin_permiso(mundo, reloj_mfa, rol_completo, rol_solo_lectura):
    cabeceras, file_id, _ = _hasta_despachado(mundo, reloj_mfa, rol_completo)
    warehouse_id = _almacen(mundo, mundo.company_id)
    solo_lectura = _operador(mundo, reloj_mfa, rol_solo_lectura)
    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/receipts",
        json={"code": "REC-ERR", "warehouse_id": warehouse_id, "packages_declared": 10},
        headers=solo_lectura,
    )
    assert r.status_code == 403, r.text
    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/payments",
        json={"kind": "PAYMENT", "amount": "1.00"},
        headers=solo_lectura,
    )
    assert r.status_code == 403, r.text


def test_negativo_payment_draft_permission_contract(mundo, reloj_mfa, rol_completo, rol_sin_aprobacion):
    from app.modules.imports.models import ImportFinancialLink

    cabeceras, file_id, _ = _hasta_despachado(mundo, reloj_mfa, rol_completo)
    revisor = _operador(mundo, reloj_mfa, rol_sin_aprobacion)
    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/payments",
        json={"kind": "PAYMENT", "amount": "1.00"},
        headers=revisor,
    )
    assert r.status_code == 200, r.text
    db = mundo.factory()
    try:
        link = db.scalar(select(ImportFinancialLink).where(ImportFinancialLink.file_id == file_id))
        assert link is not None
        payment_id = str(link.target_id)
    finally:
        db.close()
    r = mundo.client.post(
        f"{API}/purchasing/payments/{payment_id}/transition",
        json={"target": "SUBMITTED"},
        headers=revisor,
    )
    assert r.status_code == 403, r.text


def test_negativo_dispatch_no_cancela(mundo, reloj_mfa, rol_completo):
    cabeceras, file_id, _ = _hasta_despachado(mundo, reloj_mfa, rol_completo)
    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/cancel",
        json={"reason": "Intento de cancelación posterior al despacho"},
        headers=cabeceras,
    )
    assert r.status_code == 409, r.text
    r = mundo.client.get(f"{API}/importaciones/{file_id}", headers=cabeceras)
    assert r.status_code == 200, r.text
    assert r.json()["allowed_actions"]["cancel"] is False


def test_negativo_correccion_abierta_vuelve_ordered(mundo, reloj_mfa, rol_completo):
    cabeceras = _operador(mundo, reloj_mfa, rol_completo)
    supplier_id = _proveedor(mundo, cabeceras)
    _aprobar_proveedor(mundo, supplier_id)
    file_payload = _crear_expediente(mundo, cabeceras, supplier_id)
    file_id = file_payload["id"]

    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/order",
        json={"order_id": _crear_orden(mundo, mundo.company_id, supplier_id, status="APPROVED")},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text
    documentos = r.json().get("documents", [])

    for doc in documentos:
        doc_id = doc["id"]
        _adjuntar_documento(mundo, mundo.company_id, doc_id)
        r = mundo.client.post(
            f"{API}/importaciones/{file_id}/documents/{doc_id}/receive",
            json={"reference": "REF"},
            headers=cabeceras,
        )
        assert r.status_code == 200, r.text
        r = mundo.client.post(
            f"{API}/importaciones/{file_id}/documents/{doc_id}/validate",
            headers=cabeceras,
        )
        assert r.status_code == 200, r.text

    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/confirm-documents",
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text

    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/corrections",
        json={
            "kind": "FALTANTE",
            "description": "Falta documentación",
            "action_required": "Adjuntar documento faltante",
            "responsible": "PROVEEDOR",
        },
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text

    r = mundo.client.get(f"{API}/importaciones/{file_id}", headers=cabeceras)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "ORDERED"


def test_eligible_orders(mundo, reloj_mfa, rol_completo):
    cabeceras = _operador(mundo, reloj_mfa, rol_completo)
    supplier_id = _proveedor(mundo, cabeceras)
    _aprobar_proveedor(mundo, supplier_id)
    file_id = _crear_expediente(mundo, cabeceras, supplier_id)["id"]
    for _ in range(3):
        _crear_orden(mundo, mundo.company_id, supplier_id, status="APPROVED")
    r = mundo.client.get(
        f"{API}/importaciones/eligible-orders?file_id={file_id}&page=1&page_size=2",
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text
    payload = r.json()
    assert len(payload["items"]) == 2
    assert payload["total"] == 3


def test_negativo_proveedor_no_aprobado(mundo, reloj_mfa, rol_completo):
    cabeceras = _operador(mundo, reloj_mfa, rol_completo)
    supplier_id = _proveedor(mundo, cabeceras)
    file_payload = _crear_expediente(mundo, cabeceras, supplier_id)
    file_id = file_payload["id"]
    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/order",
        json={"order_id": _crear_orden(mundo, mundo.company_id, supplier_id, status="APPROVED")},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text
    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/payments",
        json={"kind": "ADVANCE", "amount": "100.00"},
        headers=cabeceras,
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "SUPPLIER_NOT_APPROVED"
    r = mundo.client.get(
        f"{API}/importaciones/{file_id}",
        headers=cabeceras,
    )
    assert r.json()["financial"] == []


def test_negativo_pago_otro_proveedor(mundo, reloj_mfa, rol_completo):
    cabeceras = _operador(mundo, reloj_mfa, rol_completo)
    supplier_id = _proveedor(mundo, cabeceras)
    _aprobar_proveedor(mundo, supplier_id)
    file_payload = _crear_expediente(mundo, cabeceras, supplier_id)
    file_id = file_payload["id"]
    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/order",
        json={"order_id": _crear_orden(mundo, mundo.company_id, supplier_id, status="APPROVED")},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text

    other_supplier = _proveedor(mundo, cabeceras)

    from app.modules.purchasing.models import Payment

    db = mundo.factory()
    try:
        payment = Payment(
            company_id=mundo.company_id,
            party_id=other_supplier,
            direction="OUT",
            currency="VED",
            amount=500,
            applied=0,
            status="DRAFT",
        )
        db.add(payment)
        db.commit()
        payment_id = payment.id
    finally:
        db.close()

    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/financial-links",
        json={"kind": "PAYMENT", "target_id": payment_id},
        headers=cabeceras,
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "IMPORT_FINANCIAL_SUPPLIER_MISMATCH"


def test_negativo_vincular_dos_veces(mundo, reloj_mfa, rol_completo):
    cabeceras = _operador(mundo, reloj_mfa, rol_completo)
    supplier_id = _proveedor(mundo, cabeceras)
    _aprobar_proveedor(mundo, supplier_id)
    file_payload = _crear_expediente(mundo, cabeceras, supplier_id)
    file_id = file_payload["id"]
    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/order",
        json={"order_id": _crear_orden(mundo, mundo.company_id, supplier_id, status="APPROVED")},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text

    from app.modules.purchasing.models import Payment

    db = mundo.factory()
    try:
        payment = Payment(
            company_id=mundo.company_id,
            party_id=supplier_id,
            direction="OUT",
            currency="VED",
            amount=500,
            applied=0,
            status="DRAFT",
        )
        db.add(payment)
        db.commit()
        payment_id = payment.id
    finally:
        db.close()

    payload = {"kind": "PAYMENT", "target_id": payment_id}
    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/financial-links",
        json=payload,
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text
    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/financial-links",
        json=payload,
        headers=cabeceras,
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "IMPORT_FINANCIAL_IN_USE"


def test_negativo_vincular_in(mundo, reloj_mfa, rol_completo):
    cabeceras = _operador(mundo, reloj_mfa, rol_completo)
    supplier_id = _proveedor(mundo, cabeceras)
    _aprobar_proveedor(mundo, supplier_id)
    file_payload = _crear_expediente(mundo, cabeceras, supplier_id)
    file_id = file_payload["id"]
    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/order",
        json={"order_id": _crear_orden(mundo, mundo.company_id, supplier_id, status="APPROVED")},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text

    from app.modules.purchasing.models import Payment

    db = mundo.factory()
    try:
        payment = Payment(
            company_id=mundo.company_id,
            party_id=supplier_id,
            direction="IN",
            currency="VED",
            amount=500,
            applied=0,
            status="DRAFT",
        )
        db.add(payment)
        db.commit()
        payment_id = payment.id
    finally:
        db.close()

    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/financial-links",
        json={"kind": "PAYMENT", "target_id": payment_id},
        headers=cabeceras,
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "IMPORT_FINANCIAL_DIRECTION_INVALID"


def test_negativo_company_isolation(mundo, reloj_mfa, rol_completo):
    from app.modules.imports.models import ImportFile
    from app.modules.organization.models import Company

    db = mundo.factory()
    try:
        other_company_id = db.scalar(
            select(Company.id).where(Company.tenant_id == mundo.tenant_b_id)
        )
        file = ImportFile(
            company_id=other_company_id,
            code=f"IMP-{uuid.uuid4().hex[:12]}",
            supplier_id=str(uuid.uuid4()),
            currency="VED",
            status="NEGOTIATING",
        )
        db.add(file)
        db.commit()
        file_id = file.id
    finally:
        db.close()

    cabeceras = _operador(mundo, reloj_mfa, rol_completo)
    r = mundo.client.get(
        f"{API}/importaciones/{file_id}",
        headers=cabeceras,
    )
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "IMPORT_NOT_FOUND"


def test_negativo_despacho_sin_salida(mundo, reloj_mfa, rol_completo):
    cabeceras = _operador(mundo, reloj_mfa, rol_completo)
    supplier_id = _proveedor(mundo, cabeceras)
    _aprobar_proveedor(mundo, supplier_id)
    file_payload = _crear_expediente(mundo, cabeceras, supplier_id)
    file_id = file_payload["id"]
    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/order",
        json={"order_id": _crear_orden(mundo, mundo.company_id, supplier_id, status="APPROVED")},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text

    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/confirm-dispatch",
        headers=cabeceras,
    )
    assert r.status_code == 409, r.text
