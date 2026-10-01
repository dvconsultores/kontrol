"""Regresión QA: bugs encontrados por la prueba funcional integral (re-ejecución).

- Bug A (CRITICAL): Decimal+float en recompute/aplicaciones rompía factura proveedor,
  pago, cobro y notas (regresión de la migración Numeric).
- Bug B (HIGH): recepción no podía completarse porque faltaba el tipo de movimiento
  `ENTRADA_RECEPCION` en instalaciones frescas → el inventario nunca se actualizaba.

Estas pruebas garantizan que ambos flujos completan sin error y con efectos reales.
"""
from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.database import Base, get_db, init_models
from app.modules.licensing import service as licensing_service
from app.modules.organization.models import Installation
from app.modules.setup.api import SetupRequest, initialize

_ENGINE = _FACTORY = _APP = _CLIENT = None


def _setup_license(db: Session) -> None:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    key = Ed25519PrivateKey.generate()
    pub = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    inst = db.execute(select(Installation).limit(1)).scalars().first()
    now = datetime.now(UTC)
    payload = {
        "issuer": "K", "license_id": "LIC-FIX", "installation_id": inst.installation_uuid,
        "customer_id": "C1", "contract_id": "C1", "company_tax_id": "J-12345678-9",
        "period_start": (now - timedelta(days=30)).isoformat(),
        "period_end": (now + timedelta(days=120)).isoformat(),
        "critical_warning_start": (now + timedelta(days=180)).isoformat(),
        "read_only_start": (now + timedelta(days=200)).isoformat(),
        "entitlements": {"companies": 1, "users": 25, "modules": ["*"]},
        "minimum_version": "1.0.0", "kid": "kontrol-lic-2026-01",
    }
    sig = key.sign(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hex()
    os.environ["KONTROL_LICENSE_PUBLIC_KEY_PEM"] = pub
    get_settings.cache_clear()
    try:
        licensing_service.import_license(db, payload=payload, signature_hex=sig, source="MANUAL")
    finally:
        os.environ.pop("KONTROL_LICENSE_PUBLIC_KEY_PEM", None)
        get_settings.cache_clear()


@pytest.fixture(scope="module", autouse=True)
def _app_client():
    global _ENGINE, _FACTORY, _APP, _CLIENT
    engine = create_engine(
        "sqlite+pysqlite:///:memory:", future=True,
        connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    init_models()
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    import app.core.database as dm

    dm._engine = engine  # type: ignore[attr-defined]
    dm._SessionLocal = factory  # type: ignore[attr-defined]

    db = factory()
    initialize(db, SetupRequest(
        tenant_code="DEMO", tenant_name="Empresa Demo", company_code="D1",
        company_legal_name="Demo C.A.", company_rif="J-12345678-9",
        admin_username="admin", admin_password="Kontrol2026Segura!",
    ))
    _setup_license(db)
    db.close()

    from app.main import create_app

    app = create_app()

    def _override_get_db():
        d = factory()
        try:
            yield d
        finally:
            d.close()

    app.dependency_overrides[get_db] = _override_get_db
    _ENGINE, _FACTORY, _APP = engine, factory, app
    _CLIENT = TestClient(app)
    yield _CLIENT


def _auth():
    r = _CLIENT.post("/api/v1/auth/login", json={
        "tenant_code": "DEMO", "username": "admin", "password": "Kontrol2026Segura!",
    })
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _party(h, code, name, role):
    r = _CLIENT.post("/api/v1/maestros/terceros", headers=h,
                     json={"code": code, "name": name, "roles": [role]})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _item(h, code, name, itype="PRODUCT"):
    r = _CLIENT.post("/api/v1/maestros/catalogos/items", headers=h,
                     json={"code": code, "name": name, "item_type": itype})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_supplier_invoice_payment_no_decimal_error():
    """Bug A: factura proveedor POSTED + CxP + pago + aplicación sin TypeError Decimal+float."""
    h = _auth()
    sup = _party(h, "P-FIX-01", "PROVEEDOR FIX", "PROVEEDOR")
    item = _item(h, "ART-FIX-01", "ARTICULO FIX")

    inv = _CLIENT.post("/api/v1/purchasing/supplier-invoices", headers=h,
                       json={"supplier_id": sup, "invoice_number": "FAC-FIX-1",
                             "control_number": None, "issue_date": None, "currency": "VED"})
    assert inv.status_code == 200, inv.text
    iid = inv.json()["id"]
    for q, p in [(5, 40.0), (2, 10.5)]:
        r = _CLIENT.post(f"/api/v1/purchasing/supplier-invoices/{iid}/lines", headers=h,
                         json={"product_id": item, "quantity": q, "unit_price": p, "tax_amount": 0})
        assert r.status_code == 200, r.text
    for t in ("VALIDATED", "MATCHED", "APPROVED", "POSTED"):
        r = _CLIENT.post(f"/api/v1/purchasing/supplier-invoices/{iid}/transition", headers=h, json={"target": t})
        assert r.status_code == 200, r.text

    oi = _CLIENT.get("/api/v1/purchasing/open-items", headers=h)
    assert oi.status_code == 200, oi.text
    items = [o for o in oi.json()["items"] if o["party_id"] == sup]
    assert items
    total = sum(o["balance"] for o in items)
    assert total == 221.0, total  # 5*40 + 2*10.5

    pay = _CLIENT.post("/api/v1/purchasing/payments", headers=h,
                       json={"party_id": sup, "amount": total, "currency": "VED", "instruments": None})
    assert pay.status_code == 200, pay.text
    pay_id = pay.json()["id"]
    for t in ("SUBMITTED", "APPROVED"):
        r = _CLIENT.post(f"/api/v1/purchasing/payments/{pay_id}/transition", headers=h, json={"target": t})
        assert r.status_code == 200, r.text
    for o in items:
        r = _CLIENT.post("/api/v1/purchasing/applications", headers=h, json={
            "source_type": "PAYMENT", "source_id": pay_id, "target_open_item_id": o["id"],
            "amount": o["balance"], "currency": "VED", "rate": None})
        assert r.status_code == 200, r.text

    oi2 = _CLIENT.get("/api/v1/purchasing/open-items", headers=h)
    bal = sum(o["balance"] for o in oi2.json()["items"] if o["party_id"] == sup)
    assert bal == 0, f"CxP no saldada: {bal}"


def test_sales_invoice_collection_no_decimal_error():
    """Bug A (ventas): factura de venta EMITTED + CxC + cobro + aplicación sin TypeError."""
    h = _auth()
    cli = _party(h, "C-FIX-01", "CLIENTE FIX", "CLIENTE")
    item = _item(h, "ART-FIX-02", "ARTICULO FIX 2")

    inv = _CLIENT.post("/api/v1/sales/invoices", headers=h,
                       json={"customer_id": cli, "base_fiscal_currency": "VED"})
    assert inv.status_code == 200, inv.text
    iid = inv.json()["id"]
    for q, p in [(2, 180.0), (2, 40.0)]:
        r = _CLIENT.post(f"/api/v1/sales/invoices/{iid}/lines", headers=h,
                         json={"product_id": item, "quantity": q, "unit_price": p, "tax_amount": 0})
        assert r.status_code == 200, r.text
    for t in ("VALIDATED", "APPROVED", "EMITTED"):
        r = _CLIENT.post(f"/api/v1/sales/invoices/{iid}/transition", headers=h, json={"target": t})
        assert r.status_code == 200, r.text

    oi = _CLIENT.get("/api/v1/sales/open-items", headers=h)
    assert oi.status_code == 200, oi.text
    items = [o for o in oi.json()["items"] if o["party_id"] == cli]
    assert items
    total = sum(o["balance"] for o in items)
    assert total == 440.0, total  # 2*180 + 2*40

    col = _CLIENT.post("/api/v1/sales/collections", headers=h,
                       json={"party_id": cli, "amount": total, "currency": "VED", "instruments": None})
    assert col.status_code == 200, col.text
    col_id = col.json()["id"]
    for o in items:
        r = _CLIENT.post("/api/v1/sales/applications", headers=h, json={
            "source_type": "PAYMENT", "source_id": col_id, "target_open_item_id": o["id"],
            "amount": o["balance"], "currency": "VED", "rate": None})
        assert r.status_code == 200, r.text

    oi2 = _CLIENT.get("/api/v1/sales/open-items", headers=h)
    bal = sum(o["balance"] for o in oi2.json()["items"] if o["party_id"] == cli)
    assert bal == 0, f"CxC no saldada: {bal}"


def test_receipt_accept_autoseeds_movement_type_and_updates_stock():
    """Bug B: recepción se completa (auto-configura ENTRADA_RECEPCION) y actualiza inventario."""
    h = _auth()
    companies = _CLIENT.get("/api/v1/organization/companies", headers=h).json()["items"]
    cid = companies[0]["id"]
    wh = _CLIENT.post("/api/v1/organization/warehouses", headers=h,
                      json={"company_id": cid, "branch_id": None, "code": "ALM-FIX", "name": "Almacén Fix"})
    assert wh.status_code == 200, wh.text
    wh_id = wh.json()["id"]
    sup = _party(h, "P-FIX-02", "PROVEEDOR FIX 2", "PROVEEDOR")
    item = _item(h, "ART-FIX-03", "ARTICULO FIX 3")

    po = _CLIENT.post("/api/v1/purchasing/orders", headers=h,
                      json={"code": "OC-FIX-1", "supplier_id": sup, "terms": None, "currency": "VED"})
    assert po.status_code == 200, po.text
    po_id = po.json()["id"]
    r = _CLIENT.post(f"/api/v1/purchasing/orders/{po_id}/lines", headers=h,
                     json={"product_id": item, "quantity_ordered": 10, "unit_price": 15.0, "discount": 0})
    assert r.status_code == 200, r.text
    for t in ("SUBMITTED", "APPROVED"):
        r = _CLIENT.post(f"/api/v1/purchasing/orders/{po_id}/transition", headers=h, json={"target": t})
        assert r.status_code == 200, r.text
    det = _CLIENT.get(f"/api/v1/purchasing/orders/{po_id}", headers=h).json()
    order_line_id = det["lines"][0]["id"]

    rc = _CLIENT.post("/api/v1/purchasing/receipts", headers=h,
                      json={"code": "RC-FIX-1", "order_id": po_id, "warehouse_id": wh_id})
    assert rc.status_code == 200, rc.text
    rc_id = rc.json()["id"]
    r = _CLIENT.post(f"/api/v1/purchasing/receipts/{rc_id}/lines", headers=h, json={
        "order_line_id": order_line_id, "product_id": item, "quantity_received": 10,
        "quantity_accepted": 10, "quantity_rejected": 0, "lot_number": None,
        "expiry_date": None, "serials": None})
    assert r.status_code == 200, r.text
    for action, body in [("confirm", {}), ("quality", {"quality_status": "APPROVED"}), ("accept", {})]:
        r = _CLIENT.post(f"/api/v1/purchasing/receipts/{rc_id}/{action}", headers=h, json=body)
        assert r.status_code == 200, f"{action}: {r.text}"

    # Inventario debe reflejar 10 unidades (Bug B corregido)
    bal = _CLIENT.get("/api/v1/inventory/balances", headers=h)
    assert bal.status_code == 200, bal.text
    qty = sum(b["qty_on_hand"] for b in bal.json()["items"] if b["product_id"] == item)
    assert qty == 10, f"stock={qty}"
