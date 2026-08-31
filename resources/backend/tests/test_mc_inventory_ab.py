"""Inventario con dos empresas del mismo tenant (ARCH-MC-001, N5).

El almacén de la Spec 008 siempre tuvo `company_id` con clave foránea real, así
que aquí no se espera encontrar el defecto de origen. Lo que se prueba es lo que
cuelga del almacén: existencias, movimientos, lotes, conteos y transferencias,
donde la empresa se deriva y una derivación equivocada es indistinguible de un
dato correcto.
"""

from __future__ import annotations

from sqlalchemy import text

pytest_plugins = ("tests.conftest_multicompany",)


def _producto(mundo, usuario, empresa, code):
    return mundo.crear("/maestros/catalogos/items", usuario, empresa,
                       {"code": code, "name": f"Producto {code}", "item_type": "PRODUCT"})


def _tipo_entrada(mundo, usuario, empresa, code):
    return mundo.crear("/inventory/movement-types", usuario, empresa,
                       {"code": code, "name": f"Entrada {code}", "direction": "IN"})


def _entrada(mundo, usuario, empresa, almacen, producto, tipo, cantidad, clave=None):
    cuerpo = {"warehouse_id": almacen, "product_id": producto, "movement_type_id": tipo,
              "quantity": cantidad, "unit_cost": 10.0, "currency": "VED"}
    if clave:
        cuerpo["idempotency_key"] = clave
    return mundo.crear("/inventory/movements", usuario, empresa, cuerpo)


# --------------------------------------------------------------- almacenes
def test_los_almacenes_ya_separaban_bien(mundo):
    """La referencia positiva: aquí la empresa nunca se perdió.

    Sirve de control. Si esta prueba fallara, el problema no estaría en la
    derivación sino en el fixture.
    """
    assert mundo.dueño("warehouses", mundo.warehouse_a) == mundo.company_a
    assert mundo.dueño("warehouses", mundo.warehouse_b) == mundo.company_b
    de_a = {w["id"] for w in mundo.get("/organization/warehouses", "ua", mundo.company_a).json()["items"]}
    assert mundo.warehouse_a in de_a and mundo.warehouse_b not in de_a


# --------------------------------------------------------------- existencias
def test_el_mismo_producto_tiene_existencias_distintas_en_cada_empresa(mundo):
    """§58: dos empresas, el mismo artículo de catálogo, dos saldos.

    Es el caso que más se parece a un error de programa y no lo es: el producto
    puede repetirse, pero las unidades son de quien las compró.
    """
    tipo_a = _tipo_entrada(mundo, "ua", mundo.company_a, "IN-A")
    tipo_b = _tipo_entrada(mundo, "ub", mundo.company_b, "IN-B")
    pa = _producto(mundo, "ua", mundo.company_a, "SKU-STOCK-A")
    pb = _producto(mundo, "ub", mundo.company_b, "SKU-STOCK-B")

    _entrada(mundo, "ua", mundo.company_a, mundo.warehouse_a, pa, tipo_a, 7)
    _entrada(mundo, "ub", mundo.company_b, mundo.warehouse_b, pb, tipo_b, 3)

    saldos_a = mundo.get("/inventory/balances", "ua", mundo.company_a).json()["items"]
    saldos_b = mundo.get("/inventory/balances", "ub", mundo.company_b).json()["items"]
    assert {s["id"] for s in saldos_a} and {s["id"] for s in saldos_b}
    assert not ({s["id"] for s in saldos_a} & {s["id"] for s in saldos_b})
    for s in saldos_a:
        assert mundo.dueño("inventory_balances", s["id"]) == mundo.company_a


def test_no_se_mueve_stock_en_el_almacen_de_otra_empresa(mundo):
    tipo_a = _tipo_entrada(mundo, "ua", mundo.company_a, "IN-CRZ")
    pa = _producto(mundo, "ua", mundo.company_a, "SKU-CRZ-A")
    r = mundo.post("/inventory/movements", "ua", mundo.company_a, {
        "warehouse_id": mundo.warehouse_b, "product_id": pa,
        "movement_type_id": tipo_a, "quantity": 5, "unit_cost": 1.0, "currency": "VED"})
    assert r.status_code == 404, f"A movió existencias en el almacén de B: {r.text}"


def test_el_movimiento_guarda_su_empresa_y_su_almacen(mundo):
    tipo_a = _tipo_entrada(mundo, "ua", mundo.company_a, "IN-OWN")
    pa = _producto(mundo, "ua", mundo.company_a, "SKU-OWN-A")
    mov = _entrada(mundo, "ua", mundo.company_a, mundo.warehouse_a, pa, tipo_a, 2)

    assert mundo.dueño("inventory_movements", mov) == mundo.company_a
    assert mundo.dueño("inventory_movements", mov) != mundo.t1
    db = mundo.factory()
    try:
        alm = db.execute(text("SELECT warehouse_id FROM inventory_movements WHERE id = :i"),
                         {"i": mov}).scalar_one()
    finally:
        db.close()
    assert alm == mundo.warehouse_a


def test_el_movimiento_de_b_no_se_lee_ni_se_revierte_desde_a(mundo):
    tipo_b = _tipo_entrada(mundo, "ub", mundo.company_b, "IN-REV")
    pb = _producto(mundo, "ub", mundo.company_b, "SKU-REV-B")
    mov_b = _entrada(mundo, "ub", mundo.company_b, mundo.warehouse_b, pb, tipo_b, 4)

    assert mundo.get(f"/inventory/movements/{mov_b}", "ua", mundo.company_a).status_code == 404
    r = mundo.post("/inventory/movements/reverse", "ua", mundo.company_a, {"movement_id": mov_b})
    assert r.status_code == 404, f"A revirtió un movimiento de B: {r.text}"


def test_la_idempotencia_de_movimientos_no_cruza_empresas(mundo):
    tipo_a = _tipo_entrada(mundo, "ua", mundo.company_a, "IN-IDEM-A")
    tipo_b = _tipo_entrada(mundo, "ub", mundo.company_b, "IN-IDEM-B")
    pa = _producto(mundo, "ua", mundo.company_a, "SKU-IDEM-A")
    pb = _producto(mundo, "ub", mundo.company_b, "SKU-IDEM-B")
    clave = "idem-movimiento-mc"

    mov_b = _entrada(mundo, "ub", mundo.company_b, mundo.warehouse_b, pb, tipo_b, 9, clave)
    mov_a = _entrada(mundo, "ua", mundo.company_a, mundo.warehouse_a, pa, tipo_a, 1, clave)

    assert mov_a != mov_b, "A recibió el movimiento de B por reutilizar la clave"
    assert mundo.dueño("inventory_movements", mov_a) == mundo.company_a


# --------------------------------------------------------------- transferencias
def test_no_hay_transferencia_de_existencias_entre_empresas(mundo):
    """§62: bloquear, no implementar.

    Mover mercancía de una persona jurídica a otra es una venta o una cesión,
    con su documento y su efecto fiscal. Un traslado interno la haría desaparecer
    de un balance y aparecer en otro sin que nada la explique.
    """
    tipo_a = _tipo_entrada(mundo, "ua", mundo.company_a, "IN-TRF")
    pa = _producto(mundo, "ua", mundo.company_a, "SKU-TRF-A")
    _entrada(mundo, "ua", mundo.company_a, mundo.warehouse_a, pa, tipo_a, 10)

    r = mundo.post("/inventory/transfers", "ua", mundo.company_a, {
        "code": "TR-CRUZADA", "origin_warehouse_id": mundo.warehouse_a,
        "destination_warehouse_id": mundo.warehouse_b,
        "lines": [{"product_id": pa, "quantity_sent": 5}]})
    assert r.status_code == 404, f"salió mercancía de A hacia el almacén de B: {r.text}"

    db = mundo.factory()
    try:
        assert db.execute(text(
            "SELECT count(*) FROM transfers WHERE destination_warehouse_id = :w"),
            {"w": mundo.warehouse_b}).scalar_one() == 0
    finally:
        db.close()


def test_la_transferencia_dentro_de_la_misma_empresa_sigue_siendo_posible(mundo):
    """Sin esto, el bloqueo anterior podría deberse a que nada funciona."""
    segundo = mundo.crear("/organization/warehouses", "ua", mundo.company_a, {
        "company_id": mundo.company_a, "branch_id": None,
        "code": "ALM-A2", "name": "Segundo almacén de A"})
    tipo_a = _tipo_entrada(mundo, "ua", mundo.company_a, "IN-TRF2")
    pa = _producto(mundo, "ua", mundo.company_a, "SKU-TRF2-A")
    _entrada(mundo, "ua", mundo.company_a, mundo.warehouse_a, pa, tipo_a, 10)

    r = mundo.post("/inventory/transfers", "ua", mundo.company_a, {
        "code": "TR-INTERNA", "origin_warehouse_id": mundo.warehouse_a,
        "destination_warehouse_id": segundo,
        "lines": [{"product_id": pa, "quantity_sent": 2}]})
    assert r.status_code == 200, r.text
    assert mundo.dueño("transfers", r.json()["id"]) == mundo.company_a


# --------------------------------------------------------------- conteos y lotes
def test_no_se_cuenta_el_almacen_de_otra_empresa(mundo):
    r = mundo.post("/inventory/counts", "ua", mundo.company_a,
                   {"code": "CONT-CRZ", "warehouse_id": mundo.warehouse_b})
    assert r.status_code == 404, f"A inventarió el almacén de B: {r.text}"


def test_el_conteo_de_b_no_se_toca_desde_a(mundo):
    conteo_b = mundo.crear("/inventory/counts", "ub", mundo.company_b,
                           {"code": "CONT-B", "warehouse_id": mundo.warehouse_b})
    assert mundo.dueño("stock_counts", conteo_b) == mundo.company_b
    pa = _producto(mundo, "ua", mundo.company_a, "SKU-CONT-A")
    r = mundo.post(f"/inventory/counts/{conteo_b}/lines", "ua", mundo.company_a,
                   {"product_id": pa, "expected_qty": 1, "counted_qty": 1})
    assert r.status_code == 404, f"A anotó una línea en el conteo de B: {r.text}"
    r = mundo.post(f"/inventory/counts/{conteo_b}/transition", "ua", mundo.company_a,
                   {"target": "IN_PROGRESS"})
    assert r.status_code == 404, f"A movió el conteo de B: {r.text}"


def test_los_lotes_no_se_mezclan(mundo):
    pa = _producto(mundo, "ua", mundo.company_a, "SKU-LOT-A")
    pb = _producto(mundo, "ub", mundo.company_b, "SKU-LOT-B")
    lote_a = mundo.crear("/inventory/lots", "ua", mundo.company_a,
                         {"product_id": pa, "lot_number": "L-A-1"})
    lote_b = mundo.crear("/inventory/lots", "ub", mundo.company_b,
                         {"product_id": pb, "lot_number": "L-B-1"})
    assert mundo.dueño("inventory_lots", lote_a) == mundo.company_a
    assert mundo.dueño("inventory_lots", lote_b) == mundo.company_b

    de_a = {x["id"] for x in mundo.get("/inventory/lots", "ua", mundo.company_a).json()["items"]}
    assert lote_a in de_a and lote_b not in de_a
    r = mundo.post(f"/inventory/lots/{lote_b}/transition", "ua", mundo.company_a,
                   {"target": "QUARANTINE"})
    assert r.status_code == 404, f"A puso en cuarentena un lote de B: {r.text}"


def test_las_capas_de_costo_no_se_mezclan(mundo):
    """§66: el costo es de quien compró. Mezclarlo falsea dos márgenes."""
    tipo_a = _tipo_entrada(mundo, "ua", mundo.company_a, "IN-COST-A")
    tipo_b = _tipo_entrada(mundo, "ub", mundo.company_b, "IN-COST-B")
    pa = _producto(mundo, "ua", mundo.company_a, "SKU-COST-A")
    pb = _producto(mundo, "ub", mundo.company_b, "SKU-COST-B")
    _entrada(mundo, "ua", mundo.company_a, mundo.warehouse_a, pa, tipo_a, 5)
    _entrada(mundo, "ub", mundo.company_b, mundo.warehouse_b, pb, tipo_b, 5)

    capas_a = mundo.get("/inventory/cost-layers", "ua", mundo.company_a).json()["items"]
    capas_b = mundo.get("/inventory/cost-layers", "ub", mundo.company_b).json()["items"]
    assert capas_a and capas_b
    assert not ({c["id"] for c in capas_a} & {c["id"] for c in capas_b})
    for c in capas_a:
        assert mundo.dueño("cost_layers", c["id"]) == mundo.company_a


# --------------------------------------------------------------- la base
def test_ninguna_fila_de_inventario_guarda_el_tenant_como_empresa(mundo):
    """La mezcla, medida directamente sobre PostgreSQL.

    No basta con que A no vea lo de B: si `company_id` guardara el tenant o una
    empresa inexistente, el filtro sería correcto sobre un dato indistinguible.
    """
    tablas = ["inventory_movements", "inventory_balances", "inventory_lots",
              "product_serials", "reservations", "transfers", "stock_counts",
              "inventory_adjustments", "cost_layers"]
    db = mundo.factory()
    try:
        for tabla in tablas:
            malas = db.execute(text(
                f"SELECT count(*) FROM {tabla} t WHERE t.company_id IS NOT NULL "
                "AND NOT EXISTS (SELECT 1 FROM companies c WHERE c.id = t.company_id)"
            )).scalar_one()
            assert malas == 0, f"{tabla}: {malas} filas no pertenecen a ninguna empresa"
    finally:
        db.close()
