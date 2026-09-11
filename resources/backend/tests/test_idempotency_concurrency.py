"""T-214 · Idempotencia y concurrencia (KAUD-Ola 2, P13/§59).

Verifica que la repetición accidental de una request no genere duplicados:
- Pagos con idempotency_key → 1 pago.
- Factura de venta con idempotency_key → 1 factura.
- Movimiento de inventario con idempotency_key → 1 movimiento (saldo una vez).
- Emisión fiscal idempotente por business_document.
- Transiciones dobles rechazadas (máquina de estados → Conflict).
- Aplicación doble de pago a CxP → no excede saldo / segundo falla.
"""
from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta

import pytest
from conftest import make_engine
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.database import Base, get_db, init_models
from app.modules.licensing import service as licensing_service
from app.modules.organization.models import Installation
from app.modules.setup.api import SetupRequest, initialize

_ENGINE = _FACTORY = _CLIENT = None


@pytest.fixture(scope="module", autouse=True)
def _app_client():
    global _ENGINE, _FACTORY, _CLIENT
    engine = make_engine()
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
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    key = Ed25519PrivateKey.generate()
    pub = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    inst = db.execute(select(Installation).limit(1)).scalars().first()
    now = datetime.now(UTC)
    payload = {
        "issuer": "K", "license_id": "LIC-IDEM", "installation_id": inst.installation_uuid,
        "customer_id": "C1", "contract_id": "C1", "company_tax_id": "J-12345678-9",
        "period_start": (now - timedelta(days=30)).isoformat(),
        "period_end": (now + timedelta(days=120)).isoformat(),
        "critical_warning_start": (now + timedelta(days=180)).isoformat(),
        "read_only_start": (now + timedelta(days=200)).isoformat(),
        "entitlements": {"companies": 1, "users": 25, "modules": ["*"]},
        "minimum_version": "1.0.0", "kid": "k",
    }
    sig = key.sign(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hex()
    os.environ["KONTROL_LICENSE_PUBLIC_KEY_PEM"] = pub
    get_settings.cache_clear()
    try:
        licensing_service.import_license(db, payload=payload, signature_hex=sig, source="MANUAL")
    finally:
        os.environ.pop("KONTROL_LICENSE_PUBLIC_KEY_PEM", None)
        get_settings.cache_clear()
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
    _ENGINE, _FACTORY = engine, factory
    _CLIENT = TestClient(app)
    yield _CLIENT


def _auth() -> dict:
    r = _CLIENT.post("/api/v1/auth/login", json={
        "tenant_code": "DEMO", "username": "admin", "password": "Kontrol2026Segura!",
    })
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _make_party(h: dict, code: str) -> str:
    r = _CLIENT.post("/api/v1/maestros/terceros", headers=h,
                     json={"code": code, "name": f"Party {code}", "roles": ["PROVEEDOR", "CLIENTE"]})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _make_product(h: dict, code: str) -> str:
    """Producto real: PostgreSQL exige la FK de `product_id` y SQLite no (P21)."""
    r = _CLIENT.post("/api/v1/maestros/catalogos/items", headers=h,
                     json={"code": code, "name": f"Producto {code}", "item_type": "PRODUCT"})
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


def _count(model) -> int:
    db = _FACTORY()
    try:
        return db.execute(select(func.count()).select_from(model)).scalar() or 0
    finally:
        db.close()


# --------------------------------------------------------------------------- #
def test_payment_idempotency_key_no_duplicates():
    """Dos POST /purchasing/payments con el mismo idempotency_key → 1 pago."""
    from app.modules.purchasing.models import Payment

    h = _auth()
    party = _make_party(h, "P-IDEM-1")
    body = {"party_id": party, "amount": 500.0, "currency": "VED",
            "idempotency_key": "idem-pay-001", "instruments": [{"method": "TRANSFERENCIA", "amount": 500.0}]}
    r1 = _CLIENT.post("/api/v1/purchasing/payments", headers=h, json=body)
    assert r1.status_code == 200, r1.text
    r2 = _CLIENT.post("/api/v1/purchasing/payments", headers=h, json=body)
    assert r2.status_code == 200, r2.text
    assert r1.json()["id"] == r2.json()["id"], "la repetición no debe crear un pago duplicado"
    assert _count(Payment) == 1


def test_sales_invoice_idempotency_key_no_duplicates():
    """Dos POST /sales/invoices con el mismo idempotency_key → 1 factura."""
    from app.modules.sales.models import SalesInvoice

    h = _auth()
    party = _make_party(h, "P-IDEM-2")
    body = {"customer_id": party, "base_fiscal_currency": "VED", "idempotency_key": "idem-inv-001"}
    r1 = _CLIENT.post("/api/v1/sales/invoices", headers=h, json=body)
    assert r1.status_code == 200, r1.text
    r2 = _CLIENT.post("/api/v1/sales/invoices", headers=h, json=body)
    assert r2.status_code == 200, r2.text
    assert r1.json()["id"] == r2.json()["id"]
    assert _count(SalesInvoice) == 1


def test_inventory_movement_idempotency_no_duplicate_balance():
    """Movimiento con idempotency_key → no duplica ni altera el saldo dos veces."""
    from app.modules.inventory.models import InventoryMovement

    h = _auth()
    # producto + almacén
    comp = _CLIENT.get("/api/v1/organization/companies", headers=h).json()[0]
    prod = _CLIENT.post("/api/v1/maestros/catalogos/items", headers=h,
                        json={"code": "PR-IDEM", "name": "Prod Idem", "item_type": "PRODUCT",
                              "tracking": "SIMPLE", "status": "ACTIVE"}).json()
    wh = _CLIENT.post("/api/v1/organization/warehouses", headers=h,
                      json={"company_id": comp["id"], "branch_id": None, "code": "ALM-IDEM",
                            "name": "Almacén Idem"}).json()
    # crear un tipo de movimiento IN (la BD fresca no tiene tipos configurados)
    mtype = _CLIENT.post("/api/v1/inventory/movement-types", headers=h,
                         json={"code": "ENTRADA_TEST", "name": "Entrada test", "direction": "IN"}).json()
    mtype_id = mtype["id"]
    body = {"company_id": comp["id"], "warehouse_id": wh["id"], "product_id": prod["id"],
            "movement_type_id": mtype_id, "quantity": 10.0, "unit_cost": 5.0,
            "currency": "VED", "idempotency_key": "idem-mov-001"}
    r1 = _CLIENT.post("/api/v1/inventory/movements", headers=h, json=body)
    assert r1.status_code == 200, r1.text
    r2 = _CLIENT.post("/api/v1/inventory/movements", headers=h, json=body)
    assert r2.status_code == 200, r2.text
    assert r1.json()["id"] == r2.json()["id"]
    assert _count(InventoryMovement) == 1
    # saldo 10, no 20
    balances = _CLIENT.get(f"/api/v1/inventory/balances?warehouse_id={wh['id']}", headers=h).json()
    rows = balances.get("items") or balances
    total = sum(float(b["qty_on_hand"]) for b in rows if b["product_id"] == prod["id"])
    assert total == 10.0, f"saldo debe ser 10 (no duplicado), got {total}"


def test_double_transition_rejected():
    """Doble transición al mismo estado → Conflict (máquina de estados)."""
    h = _auth()
    party = _make_party(h, "P-IDEM-3")
    order = _CLIENT.post("/api/v1/sales/orders", headers=h,
                         json={"code": "OV-IDEM", "customer_id": party, "margin": None, "currency": "VED"}).json()
    oid = order["id"]
    # Spec 030: confirmar exige al menos una línea (un pedido vacío no se emite).
    prod = _CLIENT.post("/api/v1/maestros/catalogos/items", headers=h,
                        json={"code": "P-IDEM-3", "name": "Servicio", "item_type": "PRODUCT"}).json()
    r0 = _CLIENT.post(f"/api/v1/sales/orders/{oid}/lines", headers=h,
                      json={"product_id": prod["id"], "quantity": 1, "unit_price": 10, "needs_inventory": False})
    assert r0.status_code == 200, r0.text
    r1 = _CLIENT.post(f"/api/v1/sales/orders/{oid}/transition", headers=h, json={"target": "SUBMITTED"})
    assert r1.status_code == 200, r1.text
    r2 = _CLIENT.post(f"/api/v1/sales/orders/{oid}/transition", headers=h, json={"target": "SUBMITTED"})
    assert r2.status_code == 409, f"la segunda transición debe rechazarse: {r2.status_code} {r2.text[:120]}"


def test_double_payment_application_not_duplicated():
    """Aplicar dos veces el mismo pago a la CxP → no duplica; el saldo no se excede."""
    from app.modules.purchasing.models import Application

    h = _auth()
    supplier = _make_party(h, "P-IDEM-4")
    # factura proveedor postada (crea open item PAYABLE)
    inv = _CLIENT.post("/api/v1/purchasing/supplier-invoices", headers=h,
                       json={"supplier_id": supplier, "invoice_number": "F-IDEM", "currency": "VED"}).json()
    iid = inv["id"]
    _CLIENT.post(f"/api/v1/purchasing/supplier-invoices/{iid}/lines", headers=h,
                 json={"product_id": _make_product(h, f"PR-{iid[:8]}"), "quantity": 1,
                       "unit_price": 200.0, "discount": 0})
    for target in ("VALIDATED", "MATCHED", "APPROVED", "POSTED"):
        r = _CLIENT.post(f"/api/v1/purchasing/supplier-invoices/{iid}/transition", headers=h, json={"target": target})
        assert r.status_code == 200, r.text
    open_items = _CLIENT.get("/api/v1/purchasing/open-items", headers=h).json()["items"]
    target = open_items[0]["id"]
    # pago 200
    pay = _CLIENT.post("/api/v1/purchasing/payments", headers=h,
                       json={"party_id": supplier, "amount": 200.0, "currency": "VED",
                             "instruments": [{"method": "TRANSFERENCIA", "amount": 200.0}]}).json()
    pid = pay["id"]
    for target_state in ("SUBMITTED", "APPROVED", "POSTED"):
        r = _CLIENT.post(f"/api/v1/purchasing/payments/{pid}/transition", headers=h, json={"target": target_state})
        assert r.status_code == 200, r.text
    # aplicar 200 → ok
    r1 = _CLIENT.post("/api/v1/purchasing/applications", headers=h,
                      json={"source_type": "PAYMENT", "source_id": pid, "target_open_item_id": target, "amount": 200.0})
    assert r1.status_code == 200, r1.text
    # aplicar de nuevo el mismo pago (ya sin saldo) → Conflict
    r2 = _CLIENT.post("/api/v1/purchasing/applications", headers=h,
                      json={"source_type": "PAYMENT", "source_id": pid, "target_open_item_id": target, "amount": 200.0})
    assert r2.status_code == 409, f"la segunda aplicación debe rechazarse: {r2.status_code} {r2.text[:120]}"
    assert _count(Application) == 1


def test_fiscal_emit_idempotent():
    """Emisión fiscal idempotente por business_document."""
    h = _auth()
    party = _make_party(h, "P-IDEM-5")
    inv = _CLIENT.post("/api/v1/sales/invoices", headers=h,
                       json={"customer_id": party, "base_fiscal_currency": "VED"}).json()
    iid = inv["id"]
    _CLIENT.post(f"/api/v1/sales/invoices/{iid}/lines", headers=h,
                 json={"product_id": _make_product(h, f"PR-{iid[:8]}"), "quantity": 1,
                       "unit_price": 100.0, "tax_amount": 16.0})
    for target in ("VALIDATED", "APPROVED", "EMITTED"):
        r = _CLIENT.post(f"/api/v1/sales/invoices/{iid}/transition", headers=h, json={"target": target})
        assert r.status_code == 200, r.text
    # serie + lote de control (configurar en BD fresca)
    series = _CLIENT.post("/api/v1/fiscal/number-series", headers=h,
                          json={"document_type": "INVOICE", "prefix": "IDEM"}).json()
    batch = _CLIENT.post("/api/v1/fiscal/control-batches", headers=h,
                         json={"range_from": "00000001", "range_to": "00001000"}).json()
    body = {"business_document": f"INVOICE:{iid}", "series_id": series["id"], "batch_id": batch["id"]}
    r1 = _CLIENT.post("/api/v1/fiscal/documents/emit", headers=h, json=body)
    assert r1.status_code == 200, r1.text
    r2 = _CLIENT.post("/api/v1/fiscal/documents/emit", headers=h, json=body)
    assert r2.status_code == 200, r2.text
    assert r1.json()["id"] == r2.json()["id"]
    assert r2.json().get("idempotent") is True
