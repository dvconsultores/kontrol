"""E2E funcional integral de KONTROL (in-process, TestClient de la app real).

Recorre la historia empresarial completa contra la aplicación real:
empresa → sucursales → almacenes → proveedores → clientes → productos → compra(PO) →
recepción → factura proveedor → CxP → pago → inventario → cotización → orden → despacho →
factura venta → CxC → cobro → devolución → NC → transferencia → auditoría.

Imprime PASS/FAIL por paso. Es la "prueba de nuevo" del backend sin depender de red/sandbox.
Uso: PYTHONPATH=resources/backend resources/backend/.venv/bin/python qa/functional-e2e-inprocess.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import UTC, datetime, timedelta

os.environ.setdefault("KONTROL_SECRET_KEY", "qa-secret-key-0123456789abcdef0123456789abcdef")
os.environ.setdefault("KONTROL_ENVIRONMENT", "local")
os.environ.setdefault("KONTROL_LOG_JSON", "false")
os.environ.setdefault("KONTROL_COOKIE_SECURE", "false")
os.environ.setdefault("KONTROL_DB_URL", "sqlite+pysqlite:///:memory:")
_tmp = tempfile.gettempdir()
os.environ.setdefault("KONTROL_INSTALLATION_VOLUME_PATH", os.path.join(_tmp, "kontrol-qa-license"))
os.environ.setdefault("KONTROL_STORAGE_PATH", os.path.join(_tmp, "kontrol-qa-storage"))
os.environ.setdefault("KONTROL_BACKUP_PATH", os.path.join(_tmp, "kontrol-qa-backups"))

from app.core.config import get_settings  # noqa: E402
get_settings.cache_clear()

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, select  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.database import Base, get_db, init_models  # noqa: E402
from app.modules.licensing import service as licensing_service  # noqa: E402
from app.modules.organization.models import Installation  # noqa: E402
from app.modules.setup.api import SetupRequest, initialize  # noqa: E402

engine = create_engine("sqlite+pysqlite:///:memory:", future=True,
                       connect_args={"check_same_thread": False}, poolclass=StaticPool)
init_models()
Base.metadata.create_all(engine)
factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
import app.core.database as dm
dm._engine = engine  # type: ignore[attr-defined]
dm._SessionLocal = factory  # type: ignore[attr-defined]

db = factory()
initialize(db, SetupRequest(
    tenant_code="DEMO", tenant_name="Empresa Demo QA", company_code="D1",
    company_legal_name="GLOBAL DV ASESORES, C.A.", company_rif="J-50662172-0",
    admin_username="admin", admin_password="Kontrol2026Segura!",
))

from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402
key = Ed25519PrivateKey.generate()
pub = key.public_key().public_bytes(
    encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo,
).decode("utf-8")
inst = db.execute(select(Installation).limit(1)).scalars().first()
now = datetime.now(UTC)
payload = {
    "issuer": "K", "license_id": "LIC-QA-E2E", "installation_id": inst.installation_uuid,
    "customer_id": "C1", "contract_id": "C1", "company_tax_id": "J-50662172-0",
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
db.close()

from app.main import create_app  # noqa: E402
app = create_app()

def _override_get_db():
    d = factory()
    try:
        yield d
    finally:
        d.close()

app.dependency_overrides[get_db] = _override_get_db
client = TestClient(app)

results: list[dict] = []
h: dict = {}
ids: dict = {}
company_id = None


def call(method: str, path: str, json_body=None):
    full = path if path.startswith("/api/v1") else "/api/v1" + path
    r = client.request(method, full, headers=h, json=json_body)
    if r.status_code >= 400:
        raise RuntimeError(f"{method} {full} -> {r.status_code}: {r.text[:200]}")
    return r.json() if r.content else None


def step(name: str, fn):
    try:
        fn()
        results.append({"caso": name, "resultado": "PASS"})
        print(f"  [PASS] {name}")
    except Exception as e:  # noqa: BLE001
        results.append({"caso": name, "resultado": f"FAIL: {e}"})
        print(f"  [FAIL] {name}: {e}")


def main() -> None:
    global h, company_id

    r = client.post("/api/v1/auth/login", json={
        "tenant_code": "DEMO", "username": "admin", "password": "Kontrol2026Segura!",
    })
    assert r.status_code == 200, r.text
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    print("[PASS] login")

    def _empresa():
        global company_id
        companies = call("GET", "/organization/companies")
        assert companies["items"] and companies["items"][0]["rif"] == "J-50662172-0"
        company_id = companies[0]["id"]
    step("empresa GLOBAL DV", _empresa)

    def _sucursales():
        b1 = call("POST", "/organization/branches", {"company_id": company_id, "code": "VAL-QA", "name": "SUCURSAL VALENCIA"})
        b2 = call("POST", "/organization/branches", {"company_id": company_id, "code": "CCS-QA", "name": "SUCURSAL CARACAS"})
        ids["branch_val"] = b1["id"]
        ids["branch_ccs"] = b2["id"]
        bs = call("GET", "/organization/branches")
        assert len(bs) == 2
    step("sucursales VAL-QA / CCS-QA", _sucursales)

    def _almacenes():
        w1 = call("POST", "/organization/warehouses", {
            "company_id": company_id, "branch_id": ids["branch_val"], "code": "ALM-VAL-QA", "name": "ALMACÉN PRINCIPAL VALENCIA QA"})
        w2 = call("POST", "/organization/warehouses", {
            "company_id": company_id, "branch_id": ids["branch_ccs"], "code": "ALM-CCS-QA", "name": "ALMACÉN PRINCIPAL CARACAS QA"})
        ids["wh_val"] = w1["id"]
        ids["wh_ccs"] = w2["id"]
        assert len(call("GET", f"/organization/warehouses?company_id={company_id}")) == 2
    step("almacenes ALM-VAL-QA / ALM-CCS-QA", _almacenes)

    def _terceros():
        prov = call("POST", "/maestros/terceros", {"code": "PROV-QA-ALFA", "name": "PROVEEDOR QA ALFA, C.A.", "roles": ["PROVEEDOR"], "tax_id": "J-40000001-1"})
        cuenta = call("POST", f"/maestros/terceros/{prov['id']}/bank-accounts", {"bank": "Banco QA", "account_number": "01020000000000000001"})
        call("POST", f"/maestros/terceros/{prov['id']}/bank-accounts/{cuenta['id']}/verify", {"evidence": "constancia QA"})
        call("POST", f"/maestros/terceros/{prov['id']}/roles/PROVEEDOR/approve")
        call("POST", "/maestros/terceros", {"code": "PROV-QA-BETA", "name": "PROVEEDOR QA BETA, C.A.", "roles": ["PROVEEDOR"]})
        cli = call("POST", "/maestros/terceros", {"code": "CLI-QA-ORION", "name": "CLIENTE QA ORION, C.A.", "roles": ["CLIENTE"]})
        call("POST", "/maestros/terceros", {"code": "CLI-QA-NOVA", "name": "CLIENTE QA NOVA, C.A.", "roles": ["CLIENTE"]})
        ids["supplier_alfa"] = prov["id"]
        ids["customer_orion"] = cli["id"]
        assert len(call("GET", "/maestros/terceros")["items"]) == 4
    step("proveedores ALFA/BETA + clientes ORION/NOVA", _terceros)

    def _items():
        for code, name, itype in [
            ("QA-MONITOR-24", "MONITOR 24 PULGADAS QA", "PRODUCT"),
            ("QA-TECLADO-USB", "TECLADO USB QA", "PRODUCT"),
            ("QA-LAPTOP", "LAPTOP EMPRESARIAL QA", "PRODUCT"),
            ("QA-TONER", "TONER QA", "PRODUCT"),
            ("QA-SOPORTE", "SERVICIO DE SOPORTE TÉCNICO QA", "SERVICE"),
        ]:
            it = call("POST", "/maestros/catalogos/items", {"code": code, "name": name, "item_type": itype})
            ids[code] = it["id"]
        assert len(call("GET", "/maestros/catalogos/items")["items"]) == 5
    step("productos QA + servicio soporte", _items)

    def _compra():
        po = call("POST", "/purchasing/orders", {
            "code": "OC-QA-0001", "supplier_id": ids["supplier_alfa"], "terms": "30 días", "currency": "VED"})
        po_id = po["id"]
        for prod, qty, price in [("QA-MONITOR-24", 10, 120.0), ("QA-TECLADO-USB", 20, 25.0)]:
            call("POST", f"/purchasing/orders/{po_id}/lines", {
                "product_id": ids[prod], "quantity_ordered": qty, "unit_price": price, "discount": 0})
        for t in ("SUBMITTED", "APPROVED"):
            call("POST", f"/purchasing/orders/{po_id}/transition", {"target": t})
        ids["po_id"] = po_id
        det = call("GET", f"/purchasing/orders/{po_id}")
        assert det["status"] == "APPROVED"
    step("orden de compra OC-QA-0001 (aprobada)", _compra)

    def _recepcion():
        det = call("GET", f"/purchasing/orders/{ids['po_id']}")
        line_map = {ln["product_id"]: ln["id"] for ln in det["lines"]}
        rc = call("POST", "/purchasing/receipts", {"code": "RC-QA-0001", "order_id": ids["po_id"], "warehouse_id": ids["wh_val"]})
        rc_id = rc["id"]
        for prod, qty in [("QA-MONITOR-24", 10), ("QA-TECLADO-USB", 20)]:
            call("POST", f"/purchasing/receipts/{rc_id}/lines", {
                "order_line_id": line_map[ids[prod]], "product_id": ids[prod],
                "quantity_received": qty, "quantity_accepted": qty, "quantity_rejected": 0,
                "lot_number": None, "expiry_date": None, "serials": None})
        call("POST", f"/purchasing/receipts/{rc_id}/confirm", {})
        call("POST", f"/purchasing/receipts/{rc_id}/quality", {})
        call("POST", f"/purchasing/receipts/{rc_id}/quality", {"quality_status": "APPROVED"})
        call("POST", f"/purchasing/receipts/{rc_id}/accept", {})
        ids["receipt_id"] = rc_id
    step("recepción RC-QA-0001 (confirm+quality+accept)", _recepcion)

    def _factura_prov():
        inv = call("POST", "/purchasing/supplier-invoices", {
            "supplier_id": ids["supplier_alfa"], "invoice_number": "FAC-QA-ALFA-0001",
            "control_number": None, "issue_date": None, "currency": "VED"})
        inv_id = inv["id"]
        call("POST", f"/purchasing/supplier-invoices/{inv_id}/lines", {"product_id": ids["QA-MONITOR-24"], "quantity": 10, "unit_price": 120.0, "tax_amount": 0})
        call("POST", f"/purchasing/supplier-invoices/{inv_id}/lines", {"product_id": ids["QA-TECLADO-USB"], "quantity": 20, "unit_price": 25.0, "tax_amount": 0})
        for t in ("VALIDATED", "MATCHED", "APPROVED", "POSTED"):
            call("POST", f"/purchasing/supplier-invoices/{inv_id}/transition", {"target": t})
        ids["inv_prov"] = inv_id
    step("factura proveedor FAC-QA-ALFA-0001 (POSTED)", _factura_prov)

    def _conciliacion():
        tm = call("GET", f"/purchasing/triple-match?invoice_id={ids['inv_prov']}")
        assert isinstance(tm, dict) and "items" in tm, tm
    step("conciliación triple-match consultable", _conciliacion)

    def _pago():
        oi = call("GET", "/purchasing/open-items")
        items = [o for o in oi["items"] if o["party_id"] == ids["supplier_alfa"]]
        assert items, "sin open items CxP"
        total = sum(o["balance"] for o in items)
        pay = call("POST", "/purchasing/payments", {"party_id": ids["supplier_alfa"], "amount": total, "currency": "VED", "instruments": None})
        pay_id = pay["id"]
        for t in ("SUBMITTED", "APPROVED"):
            call("POST", f"/purchasing/payments/{pay_id}/transition", {"target": t})
        for o in items:
            if o["balance"] > 0:
                call("POST", "/purchasing/applications", {
                    "source_type": "PAYMENT", "source_id": pay_id,
                    "target_open_item_id": o["id"], "amount": o["balance"], "currency": "VED", "rate": None})
        oi2 = call("GET", "/purchasing/open-items")
        bal = sum(o["balance"] for o in oi2["items"] if o["party_id"] == ids["supplier_alfa"])
        assert bal == 0, f"CxP no saldada: {bal}"
    step("pago y aplicación CxP (saldo 0)", _pago)

    def _inventario():
        bal = call("GET", "/inventory/balances")
        mon = sum(b["qty_on_hand"] for b in bal["items"] if b["product_id"] == ids["QA-MONITOR-24"])
        tec = sum(b["qty_on_hand"] for b in bal["items"] if b["product_id"] == ids["QA-TECLADO-USB"])
        assert mon == 10, f"MONITOR={mon}"
        assert tec == 20, f"TECLADO={tec}"
    step("inventario MONITOR=10 / TECLADO=20", _inventario)

    def _cotizacion():
        q = call("POST", "/sales/quotes", {
            "code": "COT-QA-0001", "customer_id": ids["customer_orion"],
            "price_list": None, "validity_until": None, "currency": "VED"})
        q_id = q["id"]
        for prod, qty, price in [("QA-MONITOR-24", 2, 180.0), ("QA-TECLADO-USB", 2, 40.0), ("QA-SOPORTE", 1, 100.0)]:
            call("POST", f"/sales/quotes/{q_id}/lines", {"product_id": ids[prod], "quantity": qty, "unit_price": price, "discount": 0, "tax_ref": None})
        ids["quote_id"] = q_id
    step("cotización COT-QA-0001", _cotizacion)

    def _orden_venta():
        o = call("POST", "/sales/orders", {
            "code": "OV-QA-0001", "customer_id": ids["customer_orion"],
            "warehouse_id": ids["wh_val"], "margin": None, "currency": "VED"})
        o_id = o["id"]
        for prod, qty, price in [("QA-MONITOR-24", 2, 180.0), ("QA-TECLADO-USB", 2, 40.0)]:
            call("POST", f"/sales/orders/{o_id}/lines", {"product_id": ids[prod], "quantity": qty, "unit_price": price, "discount": 0, "needs_inventory": True})
        for t in ("SUBMITTED", "CREDIT_PENDING", "APPROVED"):
            call("POST", f"/sales/orders/{o_id}/transition", {"target": t})
        det = call("GET", f"/sales/orders/{o_id}")
        assert det["status"] in ("RESERVED", "PREPARING"), det["status"]
        ids["order_id"] = o_id
    step("orden de venta OV-QA-0001 (RESERVED)", _orden_venta)

    def _despacho():
        pl = call("POST", "/sales/pick-lists", {"code": "PK-QA-0001", "order_id": ids["order_id"], "warehouse_id": ids["wh_val"], "lines": None})
        sh = call("POST", "/sales/shipments", {"code": "DESP-QA-0001", "order_id": ids["order_id"], "origin_warehouse_id": ids["wh_val"], "destination": "DIRECCIÓN OPERATIVA QA — NO FISCAL", "transport": None, "lines": None})
        call("POST", f"/sales/shipments/{sh['id']}/validate", {})
        assert pl["status"] in ("DRAFT", "PREPARING")
    step("despacho PK-QA-0001 / DESP-QA-0001 (validate)", _despacho)

    def _factura_venta():
        inv = call("POST", "/sales/invoices", {"customer_id": ids["customer_orion"], "base_fiscal_currency": "VED"})
        inv_id = inv["id"]
        call("POST", f"/sales/invoices/{inv_id}/lines", {"product_id": ids["QA-MONITOR-24"], "quantity": 2, "unit_price": 180.0, "tax_amount": 0})
        call("POST", f"/sales/invoices/{inv_id}/lines", {"product_id": ids["QA-TECLADO-USB"], "quantity": 2, "unit_price": 40.0, "tax_amount": 0})
        for t in ("VALIDATED", "APPROVED", "EMITTED"):
            call("POST", f"/sales/invoices/{inv_id}/transition", {"target": t})
        ids["inv_venta"] = inv_id
    step("factura de venta (EMITTED + CxC)", _factura_venta)

    def _cobro():
        oi = call("GET", "/sales/open-items")
        items = [o for o in oi["items"] if o["party_id"] == ids["customer_orion"]]
        assert items, "sin open items CxC"
        total = sum(o["balance"] for o in items)
        col = call("POST", "/sales/collections", {"party_id": ids["customer_orion"], "amount": total, "currency": "VED", "instruments": None})
        col_id = col["id"]
        for o in items:
            if o["balance"] > 0:
                call("POST", "/sales/applications", {
                    "source_type": "PAYMENT", "source_id": col_id,
                    "target_open_item_id": o["id"], "amount": o["balance"], "currency": "VED", "rate": None})
        oi2 = call("GET", "/sales/open-items")
        bal = sum(o["balance"] for o in oi2["items"] if o["party_id"] == ids["customer_orion"])
        assert bal == 0, f"CxC no saldada: {bal}"
    step("cobro y aplicación CxC (saldo 0)", _cobro)

    def _devolucion():
        ret = call("POST", "/sales/returns", {
            "code": "DEV-QA-0001", "source_document": "FAC-QA-0001", "reason": "Devolución QA",
            "condition": "DEFECTUOSO", "inventory_destination": "CUARENTENA"})
        call("POST", f"/sales/returns/{ret['id']}/lines", {"product_id": ids["QA-TECLADO-USB"], "quantity": 1, "condition": "DEFECTUOSO"})
    step("devolución de venta DEV-QA-0001", _devolucion)

    def _nota_credito():
        nc = call("POST", "/sales/credit-notes", {
            "customer_id": ids["customer_orion"], "number": "NC-QA-0001", "amount": 50.0,
            "invoice_ref": "FAC-QA-0001", "currency": "VED"})
        call("POST", f"/sales/credit-notes/{nc['id']}/post", {})
    step("nota de crédito NC-QA-0001 (post)", _nota_credito)

    def _transferencia():
        tr = call("POST", "/inventory/transfers", {
            "code": "TR-QA-0001", "origin_warehouse_id": ids["wh_val"],
            "destination_warehouse_id": ids["wh_ccs"], "request_ref": None,
            "lines": [{"product_id": ids["QA-TECLADO-USB"], "quantity_sent": 2, "lot_id": None, "serial_id": None}]})
        call("POST", f"/inventory/transfers/{tr['id']}/transition", {"target": "SUBMITTED"})
        call("POST", f"/inventory/transfers/{tr['id']}/transition", {"target": "APPROVED"})
    step("transferencia TR-QA-0001 Valencia→Caracas", _transferencia)

    def _auditoria():
        ev = call("GET", "/audit/events?page=1&page_size=50")
        assert ev.get("total", 0) >= 5, f"auditoría con pocos eventos: {ev.get('total')}"
        actions = {e["action"] for e in ev.get("items", [])}
        assert "LOGIN_SUCCESS" in actions, "no se registró LOGIN_SUCCESS"
    step("auditoría registra eventos", _auditoria)

    print("\n===== RESUMEN E2E IN-PROCESS =====")
    total = len(results)
    passed = sum(1 for r in results if r["resultado"] == "PASS")
    print(f"PASS {passed}/{total}")
    for r in results:
        if r["resultado"] != "PASS":
            print(f"  FAIL: {r['caso']} -> {r['resultado']}")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
