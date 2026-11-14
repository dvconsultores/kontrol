"""Spec 021 · confirmación completa: decidir el 100 % de lo aceptado o no mutar nada."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

pytest_plugins = ("tests.conftest_multicompany",)


def _sql(mundo, consulta: str, **params):
    from sqlalchemy import text

    db = mundo.factory()
    try:
        return db.execute(text(consulta), params).fetchall()
    finally:
        db.close()


def _saldos(mundo, empresa, producto) -> dict[str, Decimal]:
    filas = _sql(mundo, "SELECT state, qty_on_hand FROM inventory_balances "
                        "WHERE company_id = :c AND product_id = :p", c=empresa, p=producto)
    return {f[0]: Decimal(str(f[1])) for f in filas}


def _producto(mundo, usuario, empresa, code, base_unit_id=None):
    cuerpo = {"code": code, "name": f"Producto {code}", "item_type": "PRODUCT", "status": "ACTIVE"}
    if base_unit_id:
        cuerpo["base_unit_id"] = base_unit_id
    return mundo.crear("/maestros/catalogos/items", usuario, empresa, cuerpo)


def _recepcion(mundo, marca, lineas, *, presentacion=None, producto=None, aceptar=True):
    """Deja una recepción ACCEPTED con sus líneas en RECIBIDO.

    `lineas` es una lista de tuplas (recibido, aceptado, rechazado); crea
    producto y línea de orden por cada tupla.
    """
    usuario = "ua"
    empresa = mundo.company_a
    almacen = mundo.warehouse_a
    prov = mundo.crear("/maestros/terceros", usuario, empresa,
                       {"code": f"PROV-{marca}", "name": "Proveedor", "person_type": "JURIDICA",
                        "roles": ["PROVEEDOR"], "status": "ACTIVE"})
    if producto is not None and len(lineas) == 1:
        productos = [producto]
    else:
        productos = [_producto(mundo, usuario, empresa, f"P-{marca}-{i}") for i in range(len(lineas))]
    orden = mundo.crear("/purchasing/orders", usuario, empresa,
                        {"code": f"OC-{marca}", "supplier_id": prov, "currency": "VED"})
    lineas_orden = []
    for prod in productos:
        lineas_orden.append(
            mundo.crear(f"/purchasing/orders/{orden}/lines", usuario, empresa,
                        {"product_id": prod, "quantity_ordered": 1000, "unit_price": 1}))
    for destino in ("SUBMITTED", "APPROVED"):
        r = mundo.post(f"/purchasing/orders/{orden}/transition", usuario, empresa, {"target": destino})
        assert r.status_code == 200, r.text
    rec = mundo.crear("/purchasing/receipts", usuario, empresa,
                      {"code": f"RC-{marca}", "order_id": orden, "warehouse_id": almacen})
    lineas_recepcion = []
    recibidos = []
    for (recibido, aceptado, rechazado), prod, linea_orden in zip(lineas, productos, lineas_orden, strict=True):
        cuerpo = {"order_line_id": linea_orden, "product_id": prod,
                  "quantity_received": recibido, "quantity_accepted": aceptado,
                  "quantity_rejected": rechazado}
        if presentacion:
            cuerpo["presentation_id"] = presentacion
        lineas_recepcion.append(
            mundo.crear(f"/purchasing/receipts/{rec}/lines", usuario, empresa, cuerpo))
        recibidos.append(recibido)
    if not aceptar:
        return {"receipt": rec, "lines": lineas_recepcion, "products": productos,
                "order": orden, "recibidos": recibidos}
    for accion, cuerpo in (("confirm", {}), ("quality", {}), ("quality", {"quality_status": "APPROVED"}), ("accept", {})):
        r = mundo.post(f"/purchasing/receipts/{rec}/{accion}", usuario, empresa, cuerpo)
        assert r.status_code == 200, f"{accion}: {r.text}"
    return {"receipt": rec, "lines": lineas_recepcion, "products": productos,
            "order": orden, "recibidos": recibidos}


def _contar(mundo, m):
    for line, recibido in zip(m["lines"], m["recibidos"], strict=True):
        r = mundo.post(f"/purchasing/receipts/{m['receipt']}/lines/{line}/conteo",
                       "uab", mundo.company_a, {"counted_base_quantity": str(recibido)})
        assert r.status_code == 200, r.text


def _confirmar(mundo, m, decisiones, usuario="ua", empresa=None):
    return mundo.post(f"/purchasing/receipts/{m['receipt']}/confirmacion-inventario",
                      usuario, empresa or mundo.company_a, {"decisions": decisiones})


def _sin_confirmar(mundo, almacen, producto):
    from app.modules.purchasing import open_supply

    db = mundo.factory()
    try:
        return open_supply.recibido_sin_confirmar(
            db, company_id=mundo.company_a, warehouse_id=almacen, product_ids=[producto])[producto]
    finally:
        db.close()


def _huella(mundo, m):
    saldos = tuple(sorted((p, sorted(_saldos(mundo, mundo.company_a, p).items()))
                          for p in m["products"]))
    confirmaciones = _sql(mundo, "SELECT count(*) FROM receipt_confirmations WHERE receipt_id = :r",
                          r=m["receipt"])[0][0]
    movimientos = tuple(
        _sql(mundo, "SELECT count(*) FROM inventory_movements WHERE product_id = :p", p=p)[0][0]
        for p in m["products"])
    estado = _sql(mundo, "SELECT status, confirmation_status FROM goods_receipts WHERE id = :r",
                  r=m["receipt"])[0]
    auditorias = _sql(mundo,
                      "SELECT count(*) FROM audit_events WHERE action = 'RECEIPT_INVENTORY_CONFIRMED' "
                      "AND entity_id = :r", r=m["receipt"])[0][0]
    return saldos, confirmaciones, movimientos, estado, auditorias


def _disp(line, n, *, rechazo=False):
    decision = {"receipt_line_id": line, "target_state": "DISPONIBLE", "base_quantity": str(n)}
    if rechazo:
        decision["target_state"] = "RECHAZADO"
        decision["reason"] = "No apto en la prueba"
    return decision


# ------------------------------------------------------------- caso fundamental
def test_confirma_solo_el_total_aceptado(mundo):
    m = _recepcion(mundo, "FUND", [(100, 80, 20)])
    _contar(mundo, m)
    antes = _huella(mundo, m)

    r = _confirmar(mundo, m, [_disp(m["lines"][0], 50), _disp(m["lines"][0], 10, rechazo=True)])
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "RECEIPT_CONFIRMATION_INCOMPLETE"
    det = r.json()["details"]["lines"]
    assert len(det) == 1
    assert det[0]["base_accepted"] == "80.000000"
    assert det[0]["base_decided"] == "60.000000"
    assert det[0]["base_pending"] == "20.000000"
    assert det[0]["product_code"] == "P-FUND-0"
    assert _huella(mundo, m) == antes
    assert _saldos(mundo, mundo.company_a, m["products"][0]) == {"RECIBIDO": Decimal("80")}
    assert _sin_confirmar(mundo, mundo.warehouse_a, m["products"][0]) == Decimal("80")

    r = _confirmar(mundo, m, [_disp(m["lines"][0], 60), _disp(m["lines"][0], 20, rechazo=True)])
    assert r.status_code == 200, r.text
    assert _saldos(mundo, mundo.company_a, m["products"][0]) == {
        "RECIBIDO": Decimal("0"), "DISPONIBLE": Decimal("60"), "RECHAZADO": Decimal("20")}
    assert _sin_confirmar(mundo, mundo.warehouse_a, m["products"][0]) == Decimal("0")
    assert _huella(mundo, m)[4] == 1


def test_rechaza_exceso_sobre_lo_aceptado(mundo):
    m = _recepcion(mundo, "EXC", [(100, 80, 20)])
    _contar(mundo, m)
    antes = _huella(mundo, m)

    r = _confirmar(mundo, m, [_disp(m["lines"][0], 70), _disp(m["lines"][0], 20, rechazo=True)])
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "CONFIRMED_EXCEEDS_RECEIVED"
    assert r.json()["details"]["base_accepted"] == "80.000000"
    assert r.json()["details"]["base_decided"] == "90.000000"
    assert _huella(mundo, m) == antes


def test_rechaza_cantidad_negativa_y_cero(mundo):
    m = _recepcion(mundo, "CERO", [(100, 80, 20)])
    _contar(mundo, m)
    antes = _huella(mundo, m)

    for cantidad in ("-5", "0"):
        r = _confirmar(mundo, m, [_disp(m["lines"][0], cantidad)])
        assert r.status_code == 422, r.text
        assert r.json()["code"] == "INVALID_QUANTITY"
        assert _huella(mundo, m) == antes


def test_linea_omitida_deja_incompleta(mundo):
    m = _recepcion(mundo, "OMIT", [(10, 10, 0), (5, 5, 0)])
    _contar(mundo, m)
    antes = _huella(mundo, m)

    r = _confirmar(mundo, m, [_disp(m["lines"][0], 10)])
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "RECEIPT_CONFIRMATION_INCOMPLETE"
    det = r.json()["details"]["lines"]
    assert len(det) == 1
    assert det[0]["receipt_line_id"] == m["lines"][1]
    assert det[0]["base_pending"] == "5.000000"
    assert _huella(mundo, m) == antes

    r = _confirmar(mundo, m, [_disp(m["lines"][0], 10), _disp(m["lines"][1], 5)])
    assert r.status_code == 200, r.text


def test_linea_con_aceptado_cero_no_exige_decision(mundo):
    m = _recepcion(mundo, "ACEP0", [(10, 10, 0), (10, 0, 10)])
    _contar(mundo, m)

    r = _confirmar(mundo, m, [_disp(m["lines"][0], 10), _disp(m["lines"][1], 1)])
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "CONFIRMED_EXCEEDS_RECEIVED"

    r = _confirmar(mundo, m, [_disp(m["lines"][0], 10)])
    assert r.status_code == 200, r.text


def test_presentacion_se_confirma_en_unidad_base(mundo):
    unidad = mundo.crear("/maestros/unidades", "ua", mundo.company_a,
                         {"code": "UND-021-COMP", "name": "Unidad", "symbol": "u", "decimals": 0})
    prod = _producto(mundo, "ua", mundo.company_a, "P021-COMP", base_unit_id=unidad)
    caja = mundo.crear(f"/maestros/productos/{prod}/presentaciones", "ua", mundo.company_a,
                       {"code": "CAJA12-COMP", "name": "Caja de 12", "factor_to_base": "12",
                        "valid_from": (datetime.now(UTC) - timedelta(days=1)).isoformat()})
    m = _recepcion(mundo, "PRES", [(2, 2, 0)], presentacion=caja, producto=prod)

    mundo.post(f"/purchasing/receipts/{m['receipt']}/lines/{m['lines'][0]}/conteo",
               "uab", mundo.company_a, {"counted_base_quantity": "24"})
    r = _confirmar(mundo, m, [_disp(m["lines"][0], 2)])
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "RECEIPT_CONFIRMATION_INCOMPLETE"
    det = r.json()["details"]["lines"][0]
    assert det["base_accepted"] == "24.000000"
    assert det["base_pending"] == "22.000000"

    r = _confirmar(mundo, m, [_disp(m["lines"][0], 24)])
    assert r.status_code == 200, r.text


def test_linea_de_otra_recepcion_no_es_valida(mundo):
    m1 = _recepcion(mundo, "AJENA1", [(10, 10, 0)])
    m2 = _recepcion(mundo, "AJENA2", [(5, 5, 0)])
    _contar(mundo, m1)
    _contar(mundo, m2)
    antes1 = _huella(mundo, m1)
    antes2 = _huella(mundo, m2)

    r = _confirmar(mundo, m1, [_disp(m2["lines"][0], 5)])
    assert r.status_code == 404, r.text
    assert _huella(mundo, m1) == antes1
    assert _huella(mundo, m2) == antes2


def test_recepcion_de_otra_empresa_no_es_visible(mundo):
    m = _recepcion(mundo, "OTRA", [(10, 10, 0)])
    _contar(mundo, m)
    antes = _huella(mundo, m)

    r = _confirmar(mundo, m, [_disp(m["lines"][0], 10)], usuario="ub", empresa=mundo.company_b)
    assert r.status_code == 404, r.text
    assert _huella(mundo, m) == antes


def test_segunda_confirmacion_rechazada(mundo):
    m = _recepcion(mundo, "DUP", [(10, 10, 0)])
    _contar(mundo, m)
    assert _confirmar(mundo, m, [_disp(m["lines"][0], 10)]).status_code == 200
    confirmaciones = _huella(mundo, m)[1]

    r = _confirmar(mundo, m, [_disp(m["lines"][0], 10)])
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "ALREADY_CONFIRMED"
    assert _huella(mundo, m)[1] == confirmaciones


def test_recepcion_no_aceptada_no_confirma(mundo):
    m = _recepcion(mundo, "NOACEP", [(10, 10, 0)], aceptar=False)
    # No se cuenta ni se acepta; la confirmación debe fallar antes.
    r = _confirmar(mundo, m, [_disp(m["lines"][0], 10)])
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "RECEIPT_NOT_ACCEPTED"


def test_conciliacion_expone_aceptado_y_pendiente_por_decidir(mundo):
    m = _recepcion(mundo, "CONC", [(100, 80, 20)])
    _contar(mundo, m)

    r = mundo.get(f"/purchasing/receipts/{m['receipt']}/conciliacion", "ua", mundo.company_a)
    assert r.status_code == 200, r.text
    item = next(i for i in r.json()["items"] if i["receipt_line_id"] == m["lines"][0])
    assert item["base_quantity_accepted"] == "80.000000"
    assert item["pending_decision_base"] == "80.000000"
    assert item["product_code"] == "P-CONC-0"
    assert item["product_name"]


def test_confirmacion_concurrente_solo_una(mundo):
    from app.core.errors import ConflictError
    from app.modules.purchasing import service as ap_service
    from app.modules.purchasing.models import GoodsReceipt
    from tests.concurrency import carrera

    m = _recepcion(mundo, "RACE", [(100, 100, 0)])
    _contar(mundo, m)
    decisiones_ok = [_disp(m["lines"][0], 100)]

    def confirmar(s):
        return ap_service.confirmar_inventario(
            s, receipt=s.get(GoodsReceipt, m["receipt"]), decisiones=decisiones_ok)

    primero, segundo = carrera(mundo.factory, confirmar, confirmar)
    assert primero["confirmation_status"] == "CONFIRMADA"
    assert isinstance(segundo, ConflictError)
    assert segundo.code == "ALREADY_CONFIRMED"
    assert _huella(mundo, m)[1] == 1
    assert _saldos(mundo, mundo.company_a, m["products"][0]) == {
        "DISPONIBLE": Decimal("100"), "RECIBIDO": Decimal("0")}
