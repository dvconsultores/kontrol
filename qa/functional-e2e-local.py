"""E2E funcional integral contra el backend LOCAL (127.0.0.1:8000) usando urllib (sin proxy).

Recorre: empresa → sucursales → almacenes → proveedores → clientes → productos →
compra(PO) → recepción → factura proveedor → CxP → pago → inventario → cotización →
orden → despacho → factura venta → CxC → cobro → devolución → NC → transferencia → auditoría.
Uso: PYTHONPATH=resources/backend resources/backend/.venv/bin/python qa/functional-e2e-local.py
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000/api/v1"
results: list[dict] = []


def _request(method: str, path: str, headers: dict, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    for k, v in headers.items():
        req.add_header(k, v)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=30) as resp:
            raw = resp.read().decode()
            code = resp.status
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        code = e.code
    if code >= 400:
        raise RuntimeError(f"{method} {path} -> {code}: {raw[:200]}")
    return json.loads(raw) if raw else None


def step(name: str, fn):
    try:
        fn()
        results.append({"caso": name, "resultado": "PASS"})
        print(f"  [PASS] {name}")
    except Exception as e:  # noqa: BLE001
        results.append({"caso": name, "resultado": f"FAIL: {e}"})
        print(f"  [FAIL] {name}: {e}")


def main() -> None:
    h: dict = {}
    ids: dict = {}
    company_id = None

    r = _request("POST", "/auth/login", {}, {
        "tenant_code": "DEMO", "username": "admin", "password": "Kontrol2026Segura!",
    })
    h = {"Authorization": f"Bearer {r['access_token']}"}
    print("[PASS] login")

    def _empresa():
        nonlocal company_id
        companies = _request("GET", "/organization/companies", h)
        assert companies["items"] and companies["items"][0]["rif"] == "J-50662172-0"
        company_id = companies[0]["id"]
    step("empresa GLOBAL DV", _empresa)

    def _sucursales():
        b1 = _request("POST", "/organization/branches", h, {
            "company_id": company_id, "code": "VAL-QA", "name": "SUCURSAL VALENCIA"})
        b2 = _request("POST", "/organization/branches", h, {
            "company_id": company_id, "code": "CCS-QA", "name": "SUCURSAL CARACAS"})
        ids["branch_val"] = b1["id"]
        ids["branch_ccs"] = b2["id"]
        bs = _request("GET", "/organization/branches", h)
        assert len(bs) == 2
    step("sucursales VAL-QA / CCS-QA", _sucursales)

    def _almacenes():
        w1 = _request("POST", "/organization/warehouses", h, {
            "company_id": company_id, "branch_id": ids["branch_val"],
            "code": "ALM-VAL-QA", "name": "ALMACÉN PRINCIPAL VALENCIA QA"})
        w2 = _request("POST", "/organization/warehouses", h, {
            "company_id": company_id, "branch_id": ids["branch_ccs"],
            "code": "ALM-CCS-QA", "name": "ALMACÉN PRINCIPAL CARACAS QA"})
        ids["wh_val"] = w1["id"]
        ids["wh_ccs"] = w2["id"]
        ws = _request("GET", f"/organization/warehouses?company_id={company_id}", h)
        assert len(ws) == 2
    step("almacenes ALM-VAL-QA / ALM-CCS-QA", _almacenes)

    def _terceros():
        prov = _request("POST", "/maestros/terceros", h, {
            "code": "PROV-QA-ALFA", "name": "PROVEEDOR QA ALFA, C.A.", "roles": ["PROVEEDOR"]})
        _request("POST", "/maestros/terceros", h, {
            "code": "PROV-QA-BETA", "name": "PROVEEDOR QA BETA, C.A.", "roles": ["PROVEEDOR"]})
        cli = _request("POST", "/maestros/terceros", h, {
            "code": "CLI-QA-ORION", "name": "CLIENTE QA ORION, C.A.", "roles": ["CLIENTE"]})
        _request("POST", "/maestros/terceros", h, {
            "code": "CLI-QA-NOVA", "name": "CLIENTE QA NOVA, C.A.", "roles": ["CLIENTE"]})
        ids["supplier_alfa"] = prov["id"]
        ids["customer_orion"] = cli["id"]
        ts = _request("GET", "/maestros/terceros", h)
        assert len(ts["items"]) == 4
    step("proveedores ALFA/BETA + clientes ORION/NOVA", _terceros)

    def _items():
        for code, name, itype in [
            ("QA-MONITOR-24", "MONITOR 24 PULGADAS QA", "PRODUCT"),
            ("QA-TECLADO-USB", "TECLADO USB QA", "PRODUCT"),
            ("QA-LAPTOP", "LAPTOP EMPRESARIAL QA", "PRODUCT"),
            ("QA-TONER", "TONER QA", "PRODUCT"),
            ("QA-SOPORTE", "SERVICIO DE SOPORTE TÉCNICO QA", "SERVICE"),
        ]:
            it = _request("POST", "/maestros/catalogos/items", h, {
                "code": code, "name": name, "item_type": itype})
            ids[code] = it["id"]
        items = _request("GET", "/maestros/catalogos/items", h)
        assert len(items["items"]) == 5
    step("productos QA + servicio soporte", _items)

    def _compra():
        po = _request("POST", "/purchasing/orders", h, {
            "code": "OC-QA-0001", "supplier_id": ids["supplier_alfa"],
            "terms": "30 días", "currency": "VED"})
        po_id = po["id"]
        for prod, qty, price in [("QA-MONITOR-24", 10, 120.0), ("QA-TECLADO-USB", 20, 25.0)]:
            _request("POST", f"/purchasing/orders/{po_id}/lines", h, {
                "product_id": ids[prod], "quantity_ordered": qty, "unit_price": price, "discount": 0})
        for t in ("SUBMITTED", "APPROVED"):
            _request("POST", f"/purchasing/orders/{po_id}/transition", h, {"target": t})
        ids["po_id"] = po_id
        det = _request("GET", f"/purchasing/orders/{po_id}", h)
        assert det["status"] == "APPROVED"
    step("orden de compra OC-QA-0001 (aprobada)", _compra)

    def _recepcion():
        det = _request("GET", f"/purchasing/orders/{ids['po_id']}", h)
        line_map = {ln["product_id"]: ln["id"] for ln in det["lines"]}
        rc = _request("POST", "/purchasing/receipts", h, {
            "code": "RC-QA-0001", "order_id": ids["po_id"], "warehouse_id": ids["wh_val"]})
        rc_id = rc["id"]
        for prod, qty in [("QA-MONITOR-24", 10), ("QA-TECLADO-USB", 20)]:
            _request("POST", f"/purchasing/receipts/{rc_id}/lines", h, {
                "order_line_id": line_map[ids[prod]], "product_id": ids[prod],
                "quantity_received": qty, "quantity_accepted": qty, "quantity_rejected": 0,
                "lot_number": None, "expiry_date": None, "serials": None})
        _request("POST", f"/purchasing/receipts/{rc_id}/confirm", h, {})
        _request("POST", f"/purchasing/receipts/{rc_id}/quality", h, {"quality_status": "APPROVED"})
        _request("POST", f"/purchasing/receipts/{rc_id}/accept", h, {})
        ids["receipt_id"] = rc_id
    step("recepción RC-QA-0001 (confirm+quality+accept)", _recepcion)

    def _factura_prov():
        inv = _request("POST", "/purchasing/supplier-invoices", h, {
            "supplier_id": ids["supplier_alfa"], "invoice_number": "FAC-QA-ALFA-0001",
            "control_number": None, "issue_date": None, "currency": "VED"})
        inv_id = inv["id"]
        _request("POST", f"/purchasing/supplier-invoices/{inv_id}/lines", h, {
            "product_id": ids["QA-MONITOR-24"], "quantity": 10, "unit_price": 120.0, "tax_amount": 0})
        _request("POST", f"/purchasing/supplier-invoices/{inv_id}/lines", h, {
            "product_id": ids["QA-TECLADO-USB"], "quantity": 20, "unit_price": 25.0, "tax_amount": 0})
        for t in ("VALIDATED", "APPROVED", "POSTED"):
            _request("POST", f"/purchasing/supplier-invoices/{inv_id}/transition", h, {"target": t})
        ids["inv_prov"] = inv_id
    step("factura proveedor FAC-QA-ALFA-0001 (POSTED)", _factura_prov)

    def _conciliacion():
        tm = _request("GET", f"/purchasing/triple-match?invoice_id={ids['inv_prov']}", h)
        assert isinstance(tm, list)
    step("conciliación triple-match consultable", _conciliacion)

    def _pago():
        oi = _request("GET", "/purchasing/open-items", h)
        items = [o for o in oi["items"] if o["party_id"] == ids["supplier_alfa"]]
        assert items, "sin open items CxP"
        total = sum(o["balance"] for o in items)
        pay = _request("POST", "/purchasing/payments", h, {
            "party_id": ids["supplier_alfa"], "amount": total, "currency": "VED", "instruments": None})
        pay_id = pay["id"]
        _request("POST", f"/purchasing/payments/{pay_id}/transition", h, {"target": "APPROVED"})
        for o in items:
            if o["balance"] > 0:
                _request("POST", "/purchasing/applications", h, {
                    "source_type": "PAYMENT", "source_id": pay_id,
                    "target_open_item_id": o["id"], "amount": o["balance"], "currency": "VED", "rate": None})
        oi2 = _request("GET", "/purchasing/open-items", h)
        bal = sum(o["balance"] for o in oi2["items"] if o["party_id"] == ids["supplier_alfa"])
        assert bal == 0, f"CxP no saldada: {bal}"
    step("pago y aplicación CxP (saldo 0)", _pago)

    def _inventario():
        bal = _request("GET", "/inventory/balances", h)
        mon = sum(b["qty_on_hand"] for b in bal["items"] if b["product_id"] == ids["QA-MONITOR-24"])
        tec = sum(b["qty_on_hand"] for b in bal["items"] if b["product_id"] == ids["QA-TECLADO-USB"])
        assert mon == 10, f"MONITOR={mon}"
        assert tec == 20, f"TECLADO={tec}"
    step("inventario MONITOR=10 / TECLADO=20", _inventario)

    def _cotizacion():
        q = _request("POST", "/sales/quotes", h, {
            "code": "COT-QA-0001", "customer_id": ids["customer_orion"],
            "price_list": None, "validity_until": None, "currency": "VED"})
        q_id = q["id"]
        for prod, qty, price in [("QA-MONITOR-24", 2, 180.0), ("QA-TECLADO-USB", 2, 40.0), ("QA-SOPORTE", 1, 100.0)]:
            _request("POST", f"/sales/quotes/{q_id}/lines", h, {
                "product_id": ids[prod], "quantity": qty, "unit_price": price, "discount": 0, "tax_ref": None})
        ids["quote_id"] = q_id
    step("cotización COT-QA-0001", _cotizacion)

    def _orden_venta():
        o = _request("POST", "/sales/orders", h, {
            "code": "OV-QA-0001", "customer_id": ids["customer_orion"],
            "warehouse_id": ids["wh_val"], "margin": None, "currency": "VED"})
        o_id = o["id"]
        for prod, qty, price in [("QA-MONITOR-24", 2, 180.0), ("QA-TECLADO-USB", 2, 40.0)]:
            _request("POST", f"/sales/orders/{o_id}/lines", h, {
                "product_id": ids[prod], "quantity": qty, "unit_price": price,
                "discount": 0, "needs_inventory": True})
        for t in ("SUBMITTED", "CREDIT_PENDING", "APPROVED"):
            _request("POST", f"/sales/orders/{o_id}/transition", h, {"target": t})
        det = _request("GET", f"/sales/orders/{o_id}", h)
        assert det["status"] in ("RESERVED", "PREPARING"), det["status"]
        ids["order_id"] = o_id
    step("orden de venta OV-QA-0001 (RESERVED)", _orden_venta)

    def _despacho():
        pl = _request("POST", "/sales/pick-lists", h, {
            "code": "PK-QA-0001", "order_id": ids["order_id"], "warehouse_id": ids["wh_val"], "lines": None})
        sh = _request("POST", "/sales/shipments", h, {
            "code": "DESP-QA-0001", "order_id": ids["order_id"],
            "origin_warehouse_id": ids["wh_val"], "destination": "DIRECCIÓN OPERATIVA QA — NO FISCAL",
            "transport": None, "lines": None})
        _request("POST", f"/sales/shipments/{sh['id']}/validate", h, {})
        assert pl["status"] in ("DRAFT", "PREPARING")
    step("despacho PK-QA-0001 / DESP-QA-0001 (validate)", _despacho)

    def _factura_venta():
        inv = _request("POST", "/sales/invoices", h, {
            "customer_id": ids["customer_orion"], "base_fiscal_currency": "VED"})
        inv_id = inv["id"]
        _request("POST", f"/sales/invoices/{inv_id}/lines", h, {
            "product_id": ids["QA-MONITOR-24"], "quantity": 2, "unit_price": 180.0, "tax_amount": 0})
        _request("POST", f"/sales/invoices/{inv_id}/lines", h, {
            "product_id": ids["QA-TECLADO-USB"], "quantity": 2, "unit_price": 40.0, "tax_amount": 0})
        ids["inv_venta"] = inv_id
    step("factura de venta (creada con líneas)", _factura_venta)

    def _cobro():
        oi = _request("GET", "/sales/open-items", h)
        items = [o for o in oi["items"] if o["party_id"] == ids["customer_orion"]]
        assert items, "sin open items CxC"
        total = sum(o["balance"] for o in items)
        col = _request("POST", "/sales/collections", h, {
            "party_id": ids["customer_orion"], "amount": total, "currency": "VED", "instruments": None})
        col_id = col["id"]
        for o in items:
            if o["balance"] > 0:
                _request("POST", "/sales/applications", h, {
                    "source_type": "PAYMENT", "source_id": col_id,
                    "target_open_item_id": o["id"], "amount": o["balance"], "currency": "VED", "rate": None})
        oi2 = _request("GET", "/sales/open-items", h)
        bal = sum(o["balance"] for o in oi2["items"] if o["party_id"] == ids["customer_orion"])
        assert bal == 0, f"CxC no saldada: {bal}"
    step("cobro y aplicación CxC (saldo 0)", _cobro)

    def _devolucion():
        ret = _request("POST", "/sales/returns", h, {
            "code": "DEV-QA-0001", "source_document": "FAC-QA-0001", "reason": "Devolución QA",
            "condition": "DEFECTUOSO", "inventory_destination": "CUARENTENA"})
        _request("POST", f"/sales/returns/{ret['id']}/lines", h, {
            "product_id": ids["QA-TECLADO-USB"], "quantity": 1, "condition": "DEFECTUOSO"})
    step("devolución de venta DEV-QA-0001", _devolucion)

    def _nota_credito():
        nc = _request("POST", "/sales/credit-notes", h, {
            "customer_id": ids["customer_orion"], "number": "NC-QA-0001", "amount": 50.0,
            "invoice_ref": "FAC-QA-0001", "currency": "VED"})
        _request("POST", f"/sales/credit-notes/{nc['id']}/post", h, {})
    step("nota de crédito NC-QA-0001 (post)", _nota_credito)

    def _transferencia():
        tr = _request("POST", "/inventory/transfers", h, {
            "code": "TR-QA-0001", "origin_warehouse_id": ids["wh_val"],
            "destination_warehouse_id": ids["wh_ccs"], "request_ref": None,
            "lines": [{"product_id": ids["QA-TECLADO-USB"], "quantity_sent": 2, "lot_id": None, "serial_id": None}]})
        _request("POST", f"/inventory/transfers/{tr['id']}/transition", h, {"target": "SUBMITTED"})
        _request("POST", f"/inventory/transfers/{tr['id']}/transition", h, {"target": "APPROVED"})
    step("transferencia TR-QA-0001 Valencia→Caracas", _transferencia)

    def _auditoria():
        ev = _request("GET", "/audit/events?page=1&page_size=50", h)
        assert len(ev["items"]) >= 10, "auditoría sin eventos suficientes"
    step("auditoría registra eventos", _auditoria)

    print("\n===== RESUMEN E2E LOCAL =====")
    total = len(results)
    passed = sum(1 for r in results if r["resultado"] == "PASS")
    print(f"PASS {passed}/{total}")
    for r in results:
        if r["resultado"] != "PASS":
            print(f"  FAIL: {r['caso']} -> {r['resultado']}")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
