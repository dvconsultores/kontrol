"""Ventas y CxC con dos empresas del mismo tenant (ARCH-MC-001, N5).

Del lado del cobro el error es simétrico al de compras: si un cobro de A cancela
una factura de B, dos empresas declaran el mismo ingreso y ninguna cuadra mal.
Del lado del despacho el error es físico: mercancía que sale de un almacén que
no es de la empresa que vendió.
"""

from __future__ import annotations

from sqlalchemy import text

pytest_plugins = ("tests.conftest_multicompany",)


def _cliente(mundo, usuario, empresa, code):
    return mundo.crear("/maestros/terceros", usuario, empresa,
                       {"code": code, "name": f"Cliente {code}", "roles": ["CLIENTE"]})


def _producto(mundo, usuario, empresa, code):
    return mundo.crear("/maestros/catalogos/items", usuario, empresa,
                       {"code": code, "name": f"Producto {code}", "item_type": "PRODUCT"})


def _orden(mundo, usuario, empresa, code, almacen=None):
    return mundo.crear("/sales/orders", usuario, empresa, {
        "code": code, "customer_id": _cliente(mundo, usuario, empresa, f"CLI-{code}"),
        "warehouse_id": almacen, "currency": "VED"})


def _receivable(mundo, usuario, empresa, marca):
    """Lleva una factura de venta hasta EMITTED, que es lo que crea la cuenta por cobrar."""
    cli = _cliente(mundo, usuario, empresa, f"CL-{marca}")
    prod = _producto(mundo, usuario, empresa, f"PS-{marca}")
    inv = mundo.crear("/sales/invoices", usuario, empresa,
                      {"customer_id": cli, "base_fiscal_currency": "VED"})
    r = mundo.post(f"/sales/invoices/{inv}/lines", usuario, empresa,
                   {"product_id": prod, "quantity": 1, "unit_price": 200.0})
    assert r.status_code == 200, r.text
    for destino in ("VALIDATED", "APPROVED", "EMITTED"):
        r = mundo.post(f"/sales/invoices/{inv}/transition", usuario, empresa, {"target": destino})
        assert r.status_code == 200, f"{destino}: {r.text}"
    db = mundo.factory()
    try:
        item = db.execute(text(
            "SELECT id FROM ap_open_items WHERE source_document = :d AND company_id = :c"),
            {"d": f"SALES_INVOICE:{inv}", "c": empresa}).scalar_one()
    finally:
        db.close()
    return cli, inv, item


# --------------------------------------------------------------- órdenes
def test_las_ordenes_de_venta_guardan_su_empresa(mundo):
    oa = _orden(mundo, "ua", mundo.company_a, "OV-A1", mundo.warehouse_a)
    ob = _orden(mundo, "ub", mundo.company_b, "OV-B1", mundo.warehouse_b)
    assert mundo.dueño("sales_orders", oa) == mundo.company_a
    assert mundo.dueño("sales_orders", ob) == mundo.company_b
    assert mundo.dueño("sales_orders", oa) != mundo.t1


def test_cada_empresa_lista_solo_sus_ordenes_de_venta(mundo):
    _orden(mundo, "ua", mundo.company_a, "OV-A2", mundo.warehouse_a)
    _orden(mundo, "ub", mundo.company_b, "OV-B2", mundo.warehouse_b)
    de_a = {o["id"] for o in mundo.get("/sales/orders", "ua", mundo.company_a).json()["items"]}
    de_b = {o["id"] for o in mundo.get("/sales/orders", "ub", mundo.company_b).json()["items"]}
    assert de_a and de_b and not (de_a & de_b)


def test_la_orden_de_venta_de_b_no_se_lee_ni_se_modifica_desde_a(mundo):
    ob = _orden(mundo, "ub", mundo.company_b, "OV-B3", mundo.warehouse_b)
    prod = _producto(mundo, "ua", mundo.company_a, "PS-A3")

    assert mundo.get(f"/sales/orders/{ob}", "ua", mundo.company_a).status_code == 404
    r = mundo.post(f"/sales/orders/{ob}/lines", "ua", mundo.company_a,
                   {"product_id": prod, "quantity": 1, "unit_price": 10})
    assert r.status_code == 404, f"A añadió una línea a la orden de B: {r.text}"
    r = mundo.post(f"/sales/orders/{ob}/transition", "ua", mundo.company_a, {"target": "CONFIRMED"})
    assert r.status_code == 404, f"A movió el estado de la orden de B: {r.text}"


def test_no_se_vende_a_un_cliente_de_otra_empresa(mundo):
    cli_b = _cliente(mundo, "ub", mundo.company_b, "CLI-AJENO")
    r = mundo.post("/sales/orders", "ua", mundo.company_a,
                   {"code": "OV-CRUZADA", "customer_id": cli_b,
                    "warehouse_id": mundo.warehouse_a, "currency": "VED"})
    assert r.status_code == 404, f"A vendió a un cliente de B: {r.text}"


# --------------------------------------------------------------- almacén
def test_no_se_vende_desde_el_almacen_de_otra_empresa(mundo):
    """§42: el almacén de la venta tiene que ser de quien vende.

    Que exista y sea alcanzable no lo hace válido: la mercancía es de otra
    persona jurídica.
    """
    cli = _cliente(mundo, "ua", mundo.company_a, "CLI-ALM")
    r = mundo.post("/sales/orders", "ua", mundo.company_a,
                   {"code": "OV-ALM-B", "customer_id": cli,
                    "warehouse_id": mundo.warehouse_b, "currency": "VED"})
    assert r.status_code == 404, f"A vendió desde el almacén de B: {r.text}"


def test_no_se_prepara_ni_despacha_desde_el_almacen_ajeno(mundo):
    """§44 y §45: picking y despacho, no solo la cabecera de la orden.

    La orden se lleva hasta RESERVED a propósito. Con la orden en borrador el
    rechazo llegaría por el estado y no por la empresa, y la prueba estaría
    dándose por buena sin haber tocado nunca la comprobación que interroga.
    """
    cli = _cliente(mundo, "ua", mundo.company_a, "CLI-DESP")
    prod = _producto(mundo, "ua", mundo.company_a, "PS-DESP")
    oa = mundo.crear("/sales/orders", "ua", mundo.company_a, {
        "code": "OV-DESP", "customer_id": cli,
        "warehouse_id": mundo.warehouse_a, "currency": "VED"})
    r = mundo.post(f"/sales/orders/{oa}/lines", "ua", mundo.company_a,
                   {"product_id": prod, "quantity": 1, "unit_price": 10, "needs_inventory": False})
    assert r.status_code == 200, r.text
    for destino in ("SUBMITTED", "CREDIT_PENDING", "APPROVED", "RESERVED"):
        estado = mundo.get(f"/sales/orders/{oa}", "ua", mundo.company_a).json()["status"]
        if estado == destino:
            continue  # aprobar reserva sola; el paso ya está dado
        r = mundo.post(f"/sales/orders/{oa}/transition", "ua", mundo.company_a,
                       {"target": destino, "credit_decision": "APPROVED"})
        assert r.status_code == 200, f"{destino}: {r.text}"
    assert mundo.get(f"/sales/orders/{oa}", "ua", mundo.company_a).json()["status"] == "RESERVED"

    r = mundo.post("/sales/pick-lists", "ua", mundo.company_a,
                   {"code": "PL-CRUZADA", "order_id": oa, "warehouse_id": mundo.warehouse_b})
    assert r.status_code == 404, f"A preparó el pedido en el almacén de B: {r.text}"
    r = mundo.post("/sales/shipments", "ua", mundo.company_a,
                   {"code": "SH-CRUZADA", "order_id": oa, "origin_warehouse_id": mundo.warehouse_b})
    assert r.status_code == 404, f"A despachó desde el almacén de B: {r.text}"


def test_no_se_despacha_una_orden_ajena(mundo):
    ob = _orden(mundo, "ub", mundo.company_b, "OV-AJENA", mundo.warehouse_b)
    r = mundo.post("/sales/shipments", "ua", mundo.company_a,
                   {"code": "SH-AJENA", "order_id": ob, "origin_warehouse_id": mundo.warehouse_a})
    assert r.status_code == 404, f"A despachó la orden de B: {r.text}"


# --------------------------------------------------------------- facturas
def test_las_facturas_de_venta_guardan_su_empresa(mundo):
    _, inv_a, _ = _receivable(mundo, "ua", mundo.company_a, "FA")
    _, inv_b, _ = _receivable(mundo, "ub", mundo.company_b, "FB")
    assert mundo.dueño("sales_invoices", inv_a) == mundo.company_a
    assert mundo.dueño("sales_invoices", inv_b) == mundo.company_b


def test_la_factura_de_venta_de_b_no_se_toca_desde_a(mundo):
    cli_b = _cliente(mundo, "ub", mundo.company_b, "CLI-FV")
    inv_b = mundo.crear("/sales/invoices", "ub", mundo.company_b,
                        {"customer_id": cli_b, "base_fiscal_currency": "VED"})
    prod_a = _producto(mundo, "ua", mundo.company_a, "PS-FV")
    r = mundo.post(f"/sales/invoices/{inv_b}/lines", "ua", mundo.company_a,
                   {"product_id": prod_a, "quantity": 1, "unit_price": 5})
    assert r.status_code == 404, f"A facturó sobre el documento de B: {r.text}"
    r = mundo.post(f"/sales/invoices/{inv_b}/transition", "ua", mundo.company_a,
                   {"target": "VALIDATED"})
    assert r.status_code == 404, f"A validó la factura de B: {r.text}"


def test_la_idempotencia_de_facturas_no_cruza_empresas(mundo):
    """Una clave repetida no puede devolver la factura de otra empresa.

    El daño aquí es peor que en un listado: A recibiría como propia una factura
    fiscal emitida por B, con su número y su total.
    """
    cli_a = _cliente(mundo, "ua", mundo.company_a, "CLI-IDEM-A")
    cli_b = _cliente(mundo, "ub", mundo.company_b, "CLI-IDEM-B")
    clave = "idem-factura-mc"

    inv_b = mundo.crear("/sales/invoices", "ub", mundo.company_b,
                        {"customer_id": cli_b, "base_fiscal_currency": "VED",
                         "idempotency_key": clave})
    inv_a = mundo.crear("/sales/invoices", "ua", mundo.company_a,
                        {"customer_id": cli_a, "base_fiscal_currency": "VED",
                         "idempotency_key": clave})

    assert inv_a != inv_b, "A recibió la factura fiscal de B por reutilizar la clave"
    assert mundo.dueño("sales_invoices", inv_a) == mundo.company_a


# --------------------------------------------------------------- cobros
def test_el_cobro_guarda_su_empresa(mundo):
    cli = _cliente(mundo, "ua", mundo.company_a, "CLI-COB")
    cob = mundo.crear("/sales/collections", "ua", mundo.company_a,
                      {"party_id": cli, "amount": 30.0, "currency": "VED"})
    assert mundo.dueño("ap_payments", cob) == mundo.company_a


def test_no_se_cobra_a_un_cliente_de_otra_empresa(mundo):
    cli_b = _cliente(mundo, "ub", mundo.company_b, "CLI-COB-B")
    r = mundo.post("/sales/collections", "ua", mundo.company_a,
                   {"party_id": cli_b, "amount": 10.0, "currency": "VED"})
    assert r.status_code == 404, f"A cobró a un cliente de B: {r.text}"


def test_el_cobro_de_b_no_cancela_la_factura_de_a(mundo):
    """§49: el reflejo exacto del caso de compras, en el lado del ingreso.

    Si el cobro de B salda una cuenta por cobrar de A, dos empresas se reparten
    el mismo dinero y ninguna cuadra mal.
    """
    _, _, item_a = _receivable(mundo, "ua", mundo.company_a, "COB-A")
    cli_b = _cliente(mundo, "ub", mundo.company_b, "CLI-CRZ-B")
    cob_b = mundo.crear("/sales/collections", "ub", mundo.company_b,
                        {"party_id": cli_b, "amount": 200.0, "currency": "VED"})

    r = mundo.post("/sales/applications", "ua", mundo.company_a, {
        "source_type": "PAYMENT", "source_id": cob_b,
        "target_open_item_id": item_a, "amount": 100.0, "currency": "VED"})
    assert r.status_code == 404, f"el cobro de B canceló la factura de A: {r.text}"

    db = mundo.factory()
    try:
        aplicado = db.execute(text("SELECT applied FROM ap_payments WHERE id = :i"),
                              {"i": cob_b}).scalar_one()
    finally:
        db.close()
    assert float(aplicado) == 0.0


def test_la_cuenta_por_cobrar_de_b_no_se_salda_desde_a(mundo):
    _, _, item_b = _receivable(mundo, "ub", mundo.company_b, "COB-B")
    cli_a = _cliente(mundo, "ua", mundo.company_a, "CLI-CRZ-A")
    cob_a = mundo.crear("/sales/collections", "ua", mundo.company_a,
                        {"party_id": cli_a, "amount": 200.0, "currency": "VED"})
    r = mundo.post("/sales/applications", "ua", mundo.company_a, {
        "source_type": "PAYMENT", "source_id": cob_a,
        "target_open_item_id": item_b, "amount": 100.0, "currency": "VED"})
    assert r.status_code == 404, f"A saldó la cuenta por cobrar de B: {r.text}"


def test_el_cobro_legitimo_sigue_funcionando(mundo):
    _, _, item_a = _receivable(mundo, "ua", mundo.company_a, "COB-OK")
    cli_a = _cliente(mundo, "ua", mundo.company_a, "CLI-OK-A")
    cob_a = mundo.crear("/sales/collections", "ua", mundo.company_a,
                        {"party_id": cli_a, "amount": 200.0, "currency": "VED"})
    r = mundo.post("/sales/applications", "ua", mundo.company_a, {
        "source_type": "PAYMENT", "source_id": cob_a,
        "target_open_item_id": item_a, "amount": 100.0, "currency": "VED"})
    assert r.status_code == 200, r.text
    assert mundo.dueño("ap_applications", r.json()["id"]) == mundo.company_a


def test_las_cuentas_por_cobrar_no_se_mezclan(mundo):
    _receivable(mundo, "ua", mundo.company_a, "MIX-A")
    _receivable(mundo, "ub", mundo.company_b, "MIX-B")
    de_a = {i["id"] for i in mundo.get("/sales/open-items", "ua", mundo.company_a).json()["items"]}
    de_b = {i["id"] for i in mundo.get("/sales/open-items", "ub", mundo.company_b).json()["items"]}
    assert de_a and de_b and not (de_a & de_b)


# --------------------------------------------------------------- rastro
def test_la_auditoria_de_cxc_lleva_la_empresa_correcta(mundo):
    _, _, item_a = _receivable(mundo, "ua", mundo.company_a, "AUD-A")
    cli_a = _cliente(mundo, "ua", mundo.company_a, "CLI-AUD-A")
    cob_a = mundo.crear("/sales/collections", "ua", mundo.company_a,
                        {"party_id": cli_a, "amount": 50.0, "currency": "VED"})
    r = mundo.post("/sales/applications", "ua", mundo.company_a, {
        "source_type": "PAYMENT", "source_id": cob_a,
        "target_open_item_id": item_a, "amount": 50.0, "currency": "VED"})
    assert r.status_code == 200, r.text

    db = mundo.factory()
    try:
        fila = db.execute(text(
            "SELECT company_id FROM audit_events WHERE action = 'CXC_APPLICATION' "
            "AND entity_id = :i ORDER BY event_time DESC LIMIT 1"), {"i": item_a}).first()
    finally:
        db.close()
    assert fila is not None, "aplicar un cobro no dejó rastro"
    assert fila.company_id == mundo.company_a
    assert fila.company_id != mundo.t1
