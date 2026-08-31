"""Compras y CxP con dos empresas del mismo tenant (ARCH-MC-001, N5).

El caso que importa no es el listado: es que un pago de una empresa cancele la
deuda de otra. Eso no se ve mirando pantallas —el saldo cuadra en las dos— y
solo aparece si alguien lo intenta a propósito.
"""

from __future__ import annotations

from sqlalchemy import text

pytest_plugins = ("tests.conftest_multicompany",)


# --------------------------------------------------------------- utilidades
def _tercero(mundo, usuario, empresa, code):
    return mundo.crear("/maestros/terceros", usuario, empresa,
                       {"code": code, "name": f"Proveedor {code}", "roles": ["PROVEEDOR"]})


def _producto(mundo, usuario, empresa, code):
    return mundo.crear("/maestros/catalogos/items", usuario, empresa,
                       {"code": code, "name": f"Producto {code}", "item_type": "PRODUCT"})


def _orden(mundo, usuario, empresa, code, proveedor=None):
    prov = proveedor or _tercero(mundo, usuario, empresa, f"PRV-{code}")
    return mundo.crear("/purchasing/orders", usuario, empresa,
                       {"code": code, "supplier_id": prov, "currency": "VED"})


def _open_item(mundo, usuario, empresa, numero):
    """Lleva una factura de proveedor hasta POSTED, que es lo que crea la deuda."""
    prov = _tercero(mundo, usuario, empresa, f"PV-{numero}")
    prod = _producto(mundo, usuario, empresa, f"PD-{numero}")
    inv = mundo.crear("/purchasing/supplier-invoices", usuario, empresa, {
        "supplier_id": prov, "invoice_number": numero, "control_number": f"C-{numero}"})
    r = mundo.post(f"/purchasing/supplier-invoices/{inv}/lines", usuario, empresa,
                   {"product_id": prod, "quantity": 1, "unit_price": 100.0})
    assert r.status_code == 200, r.text
    for destino in ("VALIDATED", "MATCHED", "APPROVED", "POSTED"):
        r = mundo.post(f"/purchasing/supplier-invoices/{inv}/transition", usuario, empresa,
                       {"target": destino})
        assert r.status_code == 200, f"{destino}: {r.text}"
    db = mundo.factory()
    try:
        item = db.execute(text(
            "SELECT id FROM ap_open_items WHERE source_document = :n AND company_id = :c"),
            {"n": f"INVOICE:{inv}", "c": empresa}).scalar_one()
    finally:
        db.close()
    return prov, inv, item


# --------------------------------------------------------------- órdenes
def test_las_ordenes_de_a_y_b_guardan_su_propia_empresa(mundo):
    oa = _orden(mundo, "ua", mundo.company_a, "OC-A1")
    ob = _orden(mundo, "ub", mundo.company_b, "OC-B1")
    assert mundo.dueño("purchase_orders", oa) == mundo.company_a
    assert mundo.dueño("purchase_orders", ob) == mundo.company_b
    assert mundo.dueño("purchase_orders", oa) != mundo.t1


def test_cada_empresa_lista_solo_sus_ordenes(mundo):
    _orden(mundo, "ua", mundo.company_a, "OC-A2")
    _orden(mundo, "ub", mundo.company_b, "OC-B2")
    de_a = {o["id"] for o in mundo.get("/purchasing/orders", "ua", mundo.company_a).json()["items"]}
    de_b = {o["id"] for o in mundo.get("/purchasing/orders", "ub", mundo.company_b).json()["items"]}
    assert de_a and de_b and not (de_a & de_b)


def test_la_orden_de_b_no_se_lee_ni_se_modifica_desde_a(mundo):
    ob = _orden(mundo, "ub", mundo.company_b, "OC-B3")
    prod = _producto(mundo, "ua", mundo.company_a, "PR-A3")

    assert mundo.get(f"/purchasing/orders/{ob}", "ua", mundo.company_a).status_code == 404
    r = mundo.post(f"/purchasing/orders/{ob}/lines", "ua", mundo.company_a,
                   {"product_id": prod, "quantity_ordered": 1, "unit_price": 10})
    assert r.status_code == 404, f"A añadió una línea a la orden de B: {r.text}"
    r = mundo.post(f"/purchasing/orders/{ob}/transition", "ua", mundo.company_a,
                   {"target": "SUBMITTED"})
    assert r.status_code == 404, f"A movió el estado de la orden de B: {r.text}"


def test_no_se_compra_a_un_proveedor_de_otra_empresa(mundo):
    prov_b = _tercero(mundo, "ub", mundo.company_b, "PRV-AJENO")
    r = mundo.post("/purchasing/orders", "ua", mundo.company_a,
                   {"code": "OC-CRUZADA", "supplier_id": prov_b, "currency": "VED"})
    assert r.status_code == 404, f"A creó una orden a un proveedor de B: {r.text}"


# --------------------------------------------------------------- recepción
def test_no_se_recibe_mercancia_de_a_en_un_almacen_de_b(mundo):
    """§28 y §29: el almacén tiene que ser de la misma empresa que la orden.

    Dos empresas del mismo tenant no comparten inventario. Que el almacén exista
    y sea alcanzable no lo hace válido para esta orden.
    """
    prov = _tercero(mundo, "ua", mundo.company_a, "PRV-REC")
    prod = _producto(mundo, "ua", mundo.company_a, "PRD-REC")
    oa = mundo.crear("/purchasing/orders", "ua", mundo.company_a,
                     {"code": "OC-REC", "supplier_id": prov, "currency": "VED"})
    r = mundo.post(f"/purchasing/orders/{oa}/lines", "ua", mundo.company_a,
                   {"product_id": prod, "quantity_ordered": 5, "unit_price": 10})
    assert r.status_code == 200, r.text
    for destino in ("SUBMITTED", "APPROVED"):
        r = mundo.post(f"/purchasing/orders/{oa}/transition", "ua", mundo.company_a, {"target": destino})
        assert r.status_code == 200, f"{destino}: {r.text}"

    r = mundo.post("/purchasing/receipts", "ua", mundo.company_a,
                   {"code": "RC-CRUZADA", "order_id": oa, "warehouse_id": mundo.warehouse_b})
    assert r.status_code == 404, f"la mercancía de A entró en el almacén de B: {r.text}"

    # Y con el almacén correcto sí funciona: la prueba anterior no vale nada si
    # resulta que la ruta rechaza cualquier recepción.
    r = mundo.post("/purchasing/receipts", "ua", mundo.company_a,
                   {"code": "RC-BUENA", "order_id": oa, "warehouse_id": mundo.warehouse_a})
    assert r.status_code == 200, r.text
    assert mundo.dueño("goods_receipts", r.json()["id"]) == mundo.company_a


# --------------------------------------------------------------- facturas
def test_la_factura_de_proveedor_de_b_no_se_toca_desde_a(mundo):
    prov_b = _tercero(mundo, "ub", mundo.company_b, "PRV-FAC")
    inv_b = mundo.crear("/purchasing/supplier-invoices", "ub", mundo.company_b,
                        {"supplier_id": prov_b, "invoice_number": "F-B-1", "control_number": "C-B-1"})
    assert mundo.dueño("supplier_invoices", inv_b) == mundo.company_b

    assert mundo.get(f"/purchasing/supplier-invoices/{inv_b}", "ua", mundo.company_a).status_code == 404
    prod_a = _producto(mundo, "ua", mundo.company_a, "PRD-FAC")
    r = mundo.post(f"/purchasing/supplier-invoices/{inv_b}/lines", "ua", mundo.company_a,
                   {"product_id": prod_a, "quantity": 1, "unit_price": 1})
    assert r.status_code == 404, f"A facturó sobre el documento de B: {r.text}"
    r = mundo.post(f"/purchasing/supplier-invoices/{inv_b}/transition", "ua", mundo.company_a,
                   {"target": "VALIDATED"})
    assert r.status_code == 404, f"A validó la factura de B: {r.text}"


# --------------------------------------------------------------- pagos
def test_el_pago_guarda_su_empresa(mundo):
    prov = _tercero(mundo, "ua", mundo.company_a, "PRV-PAG")
    pago = mundo.crear("/purchasing/payments", "ua", mundo.company_a,
                       {"party_id": prov, "amount": 50.0, "currency": "VED"})
    assert mundo.dueño("ap_payments", pago) == mundo.company_a


def test_no_se_paga_a_un_proveedor_de_otra_empresa(mundo):
    prov_b = _tercero(mundo, "ub", mundo.company_b, "PRV-PAGO-B")
    r = mundo.post("/purchasing/payments", "ua", mundo.company_a,
                   {"party_id": prov_b, "amount": 10.0, "currency": "VED"})
    assert r.status_code == 404, f"A pagó a un proveedor de B: {r.text}"


def test_el_pago_de_b_no_cancela_la_deuda_de_a(mundo):
    """§35, la prueba que da sentido a todo el bloque.

    Aplicar un pago de B a una obligación de A significa que una empresa liquidó
    la deuda de otra sin que exista el préstamo entre ellas. Los saldos cuadran
    a ambos lados, así que nadie lo nota: la única forma de descubrirlo es
    intentarlo.
    """
    _, _, item_a = _open_item(mundo, "ua", mundo.company_a, "F-APL-A")
    prov_b = _tercero(mundo, "ub", mundo.company_b, "PRV-APL-B")
    pago_b = mundo.crear("/purchasing/payments", "ub", mundo.company_b,
                         {"party_id": prov_b, "amount": 100.0, "currency": "VED"})

    r = mundo.post("/purchasing/applications", "ua", mundo.company_a, {
        "source_type": "PAYMENT", "source_id": pago_b,
        "target_open_item_id": item_a, "amount": 50.0, "currency": "VED"})
    assert r.status_code == 404, f"el pago de B canceló deuda de A: {r.status_code} {r.text}"

    db = mundo.factory()
    try:
        aplicado = db.execute(text("SELECT applied FROM ap_payments WHERE id = :i"),
                              {"i": pago_b}).scalar_one()
    finally:
        db.close()
    assert float(aplicado) == 0.0, "el pago de B quedó parcialmente consumido"


def test_la_deuda_de_b_no_se_cancela_desde_a(mundo):
    """El mismo cruce por el otro lado: destino ajeno, fuente propia."""
    _, _, item_b = _open_item(mundo, "ub", mundo.company_b, "F-APL-B")
    prov_a = _tercero(mundo, "ua", mundo.company_a, "PRV-APL-A")
    pago_a = mundo.crear("/purchasing/payments", "ua", mundo.company_a,
                         {"party_id": prov_a, "amount": 100.0, "currency": "VED"})

    r = mundo.post("/purchasing/applications", "ua", mundo.company_a, {
        "source_type": "PAYMENT", "source_id": pago_a,
        "target_open_item_id": item_b, "amount": 50.0, "currency": "VED"})
    assert r.status_code == 404, f"A canceló la deuda de B: {r.text}"


def test_la_aplicacion_legitima_sigue_funcionando(mundo):
    """Sin esto, las dos anteriores podrían estar pasando por estar todo roto."""
    _, _, item_a = _open_item(mundo, "ua", mundo.company_a, "F-OK-A")
    prov_a = _tercero(mundo, "ua", mundo.company_a, "PRV-OK-A")
    pago_a = mundo.crear("/purchasing/payments", "ua", mundo.company_a,
                         {"party_id": prov_a, "amount": 100.0, "currency": "VED"})

    r = mundo.post("/purchasing/applications", "ua", mundo.company_a, {
        "source_type": "PAYMENT", "source_id": pago_a,
        "target_open_item_id": item_a, "amount": 50.0, "currency": "VED"})
    assert r.status_code == 200, r.text
    assert mundo.dueño("ap_applications", r.json()["id"]) == mundo.company_a


def test_la_idempotencia_no_devuelve_el_pago_de_otra_empresa(mundo):
    """Una clave repetida no puede cruzar la frontera entre empresas.

    Si la búsqueda por clave de idempotencia no acota la empresa, A pidiendo un
    pago con una clave que B ya usó recibiría el pago de B: un identificador de
    otra empresa entregado como si fuera propio.
    """
    prov_a = _tercero(mundo, "ua", mundo.company_a, "PRV-IDEM-A")
    prov_b = _tercero(mundo, "ub", mundo.company_b, "PRV-IDEM-B")
    clave = "idem-compartida-mc"

    pago_b = mundo.crear("/purchasing/payments", "ub", mundo.company_b,
                         {"party_id": prov_b, "amount": 77.0, "currency": "VED",
                          "idempotency_key": clave})
    pago_a = mundo.crear("/purchasing/payments", "ua", mundo.company_a,
                         {"party_id": prov_a, "amount": 33.0, "currency": "VED",
                          "idempotency_key": clave})

    assert pago_a != pago_b, "A recibió el pago de B por reutilizar la clave"
    assert mundo.dueño("ap_payments", pago_a) == mundo.company_a


# --------------------------------------------------------------- otro tenant
def test_el_otro_tenant_no_ve_ordenes_de_t1(mundo):
    _orden(mundo, "ua", mundo.company_a, "OC-T1")
    assert mundo.get("/purchasing/orders", "uc", mundo.company_a, tenant="T2").status_code == 404
    de_c = mundo.get("/purchasing/orders", "uc", mundo.company_c, tenant="T2").json()["items"]
    assert de_c == []


# --------------------------------------------------------------- rastro
def test_la_auditoria_de_cxp_lleva_la_empresa_correcta(mundo):
    _, _, item_a = _open_item(mundo, "ua", mundo.company_a, "F-AUD-A")
    prov_a = _tercero(mundo, "ua", mundo.company_a, "PRV-AUD-A")
    pago_a = mundo.crear("/purchasing/payments", "ua", mundo.company_a,
                         {"party_id": prov_a, "amount": 20.0, "currency": "VED"})
    r = mundo.post("/purchasing/applications", "ua", mundo.company_a, {
        "source_type": "PAYMENT", "source_id": pago_a,
        "target_open_item_id": item_a, "amount": 20.0, "currency": "VED"})
    assert r.status_code == 200, r.text

    db = mundo.factory()
    try:
        fila = db.execute(text(
            "SELECT company_id, tenant_id FROM audit_events WHERE action = 'CXP_APPLICATION' "
            "AND entity_id = :i ORDER BY event_time DESC LIMIT 1"), {"i": item_a}).first()
    finally:
        db.close()
    assert fila is not None, "aplicar un pago no dejó rastro"
    assert fila.company_id == mundo.company_a
    assert fila.company_id != mundo.t1
