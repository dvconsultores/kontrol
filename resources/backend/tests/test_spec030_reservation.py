"""Crédito, aprobación y reserva — Spec 030.

`RESERVATION TRIGGER = ORDER_CONFIRMATION` (ADR-D0-003 v2). La reserva nace al
confirmar el pedido, en cantidad base, todo o nada, y vive lo que vive el
pedido: cancelar, rechazar, revertir o expirar la devuelven; despachar la
consume. Estas pruebas corren sobre PostgreSQL con dos tenants y tres
empresas, porque la mitad de lo que afirman es «quién puede tocar qué».
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import text

pytest_plugins = ("tests.conftest_multicompany",)


# --------------------------------------------------------------------------- #
# Mundo mínimo: cliente, producto, entrada de stock y pedido
# --------------------------------------------------------------------------- #
def _cliente(mundo, usuario, empresa, code):
    return mundo.crear("/maestros/terceros", usuario, empresa,
                       {"code": code, "name": f"Cliente {code}", "roles": ["CLIENTE"]})


def _producto(mundo, usuario, empresa, code, base_unit_id=None):
    cuerpo = {"code": code, "name": f"Producto {code}", "item_type": "PRODUCT"}
    if base_unit_id:
        cuerpo["base_unit_id"] = base_unit_id
    return mundo.crear("/maestros/catalogos/items", usuario, empresa, cuerpo)


_tipos: dict[tuple[str, str], str] = {}


def _tipo_entrada(mundo, usuario, empresa):
    clave = (usuario, empresa)
    if clave not in _tipos:
        _tipos[clave] = mundo.crear("/inventory/movement-types", usuario, empresa,
                                    {"code": f"ENT-030-{len(_tipos)}", "name": "Entrada 030", "direction": "IN"})
    return _tipos[clave]


def _stock(mundo, usuario, empresa, almacen, producto, cantidad):
    return mundo.crear("/inventory/movements", usuario, empresa, {
        "warehouse_id": almacen, "product_id": producto, "movement_type_id": _tipo_entrada(mundo, usuario, empresa),
        "quantity": cantidad, "unit_cost": 10.0, "currency": "VED"})


def _pedido(mundo, usuario, empresa, code, cliente, almacen=None):
    cuerpo = {"code": code, "customer_id": cliente, "currency": "VED"}
    if almacen:
        cuerpo["warehouse_id"] = almacen
    return mundo.crear("/sales/orders", usuario, empresa, cuerpo)


def _linea(mundo, usuario, empresa, pedido, producto, cantidad, precio=10, **extra):
    r = mundo.post(f"/sales/orders/{pedido}/lines", usuario, empresa,
                   {"product_id": producto, "quantity": cantidad, "unit_price": precio, **extra})
    assert r.status_code == 200, r.text
    return r.json()


def _pedido_listo(mundo, usuario, empresa, almacen, marca, stock=10, cantidad=8):
    """Pedido en borrador con una línea y stock disponible en su almacén."""
    cli = _cliente(mundo, usuario, empresa, f"CLI-{marca}")
    prod = _producto(mundo, usuario, empresa, f"PRD-{marca}")
    _stock(mundo, usuario, empresa, almacen, prod, stock)
    ped = _pedido(mundo, usuario, empresa, f"OV-{marca}", cli, almacen)
    linea = _linea(mundo, usuario, empresa, ped, prod, cantidad)
    return {"cliente": cli, "producto": prod, "pedido": ped, "linea": linea["id"]}


def _orden(mundo, usuario, empresa, pedido):
    r = mundo.get(f"/sales/orders/{pedido}", usuario, empresa)
    assert r.status_code == 200, r.text
    return r.json()


def _disponible(mundo, usuario, empresa, almacen, producto):
    r = mundo.get("/inventory/balances", usuario, empresa)
    assert r.status_code == 200, r.text
    for saldo in r.json()["items"]:
        if saldo["product_id"] == producto and saldo["warehouse_id"] == almacen:
            return float(saldo["qty_on_hand"]), float(saldo["qty_reserved"]), float(saldo["qty_available"])
    return 0.0, 0.0, 0.0


def _reservas(mundo, usuario, empresa, pedido=None):
    r = mundo.get("/inventory/reservations", usuario, empresa)
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    return [x for x in items if pedido is None or x["source_order_id"] == pedido]


def _sql(mundo, sentencia, **params):
    db = mundo.factory()
    try:
        out = db.execute(text(sentencia), params)
        db.commit()
        return out
    finally:
        db.close()


def _contar(mundo, tabla):
    return len(mundo.filas(tabla, "id"))


def _politica_de_credito(mundo, usuario, empresa, umbral=50.0):
    """Política 045 de `SALES_CREDIT` sobre `amount_base > umbral`, resuelta por ADMIN."""
    pid = mundo.crear("/approvals/policies", usuario, empresa, {
        "process_type": "SALES_CREDIT", "code": f"CR-{umbral:.0f}", "name": "Crédito",
        "requires_segregation": False, "allow_self_approval": True})
    regla = mundo.crear(f"/approvals/policies/{pid}/rules", usuario, empresa, {
        "name": "Sobre umbral",
        "conditions": [{"field": "amount_base", "operator": "gt", "value": umbral}],
        "condition_fields": ["amount_base", "amount", "currency"]})
    r = mundo.post(f"/approvals/policies/{pid}/rules/{regla}/levels", usuario, empresa,
                   {"level_order": 1, "resolver_type": "ROLE", "resolver_ref": "ADMIN", "quorum_type": "ANY"})
    assert r.status_code == 201, r.text
    r = mundo.post(f"/approvals/policies/{pid}/activate", usuario, empresa, {})
    assert r.status_code == 200, r.text
    return pid


def _cerrar_politica(mundo, usuario, empresa, pid):
    r = mundo.post(f"/approvals/policies/{pid}/close", usuario, empresa, {})
    assert r.status_code == 200, r.text


def _paso_pendiente(mundo, usuario, empresa, pedido):
    r = mundo.get("/approvals/inbox", usuario, empresa)
    assert r.status_code == 200, r.text
    item = next(i for i in r.json()["items"] if i["document_id"] == pedido)
    return item["step_id"]


def _estado_aprobacion(mundo, usuario, empresa, pedido):
    r = mundo.get(f"/approvals/requests/by-document?document_type=SalesOrder&document_id={pedido}",
                  usuario, empresa)
    assert r.status_code == 200, r.text
    return r.json()


# --------------------------------------------------------------------------- #
# Contado: DRAFT → SUBMITTED [reserva] → RELEASED en una transacción
# --------------------------------------------------------------------------- #
def test_confirmar_un_pedido_de_contado_reserva_y_lo_libera_a_preparacion(mundo):
    """IMP-030-003/004/024: sin política de crédito, confirmar reserva y libera."""
    m = _pedido_listo(mundo, "ua", mundo.company_a, mundo.warehouse_a, "CONT")
    assert _orden(mundo, "ua", mundo.company_a, m["pedido"])["status"] == "DRAFT"
    assert _reservas(mundo, "ua", mundo.company_a, m["pedido"]) == [], "el borrador no reserva (IMP-030-001)"

    r = mundo.post(f"/sales/orders/{m['pedido']}/submit", "ua", mundo.company_a, {})
    assert r.status_code == 200, r.text
    pedido = r.json()
    assert pedido["status"] == "RELEASED"
    assert pedido["eligible_for_picking"] is True
    assert pedido["submitted_at"] and pedido["released_at"]
    assert pedido["reservation_trigger"] == "ORDER_CONFIRMATION"

    reservas = _reservas(mundo, "ua", mundo.company_a, m["pedido"])
    assert len(reservas) == 1
    reserva = reservas[0]
    assert reserva["status"] == "ACTIVE"
    assert reserva["source_type"] == "SALES_ORDER"
    assert reserva["source_order_id"] == m["pedido"], "la reserva no identifica el pedido (IMP-030-016)"
    assert reserva["source_line_id"] == m["linea"], "la reserva no identifica la línea (IMP-030-017)"
    assert reserva["trigger"] == "ORDER_CONFIRMATION"
    assert reserva["oversell"] is False
    assert reserva["expires_at"] is None
    assert float(reserva["base_quantity"]) == 8.0

    on_hand, reservado, disponible = _disponible(mundo, "ua", mundo.company_a, mundo.warehouse_a, m["producto"])
    assert (on_hand, reservado, disponible) == (10.0, 8.0, 2.0), "la reserva no movió físico y sí disponible"

    # Lo que 031 recibe: la reserva viaja con la línea (IMP-030-053)
    detalle = _orden(mundo, "ua", mundo.company_a, m["pedido"])
    assert detalle["lines"][0]["reservations"][0]["status"] == "ACTIVE"
    assert detalle["lines"][0]["base_quantity"] == "8.000000"


def test_confirmar_dos_veces_no_duplica_la_reserva(mundo):
    """IMP-030-019: el reintento choca con la máquina de estados y con el índice."""
    m = _pedido_listo(mundo, "ua", mundo.company_a, mundo.warehouse_a, "DOBLE")
    assert mundo.post(f"/sales/orders/{m['pedido']}/submit", "ua", mundo.company_a, {}).status_code == 200
    r = mundo.post(f"/sales/orders/{m['pedido']}/submit", "ua", mundo.company_a, {})
    assert r.status_code == 409, r.text
    assert len(_reservas(mundo, "ua", mundo.company_a, m["pedido"])) == 1
    assert _disponible(mundo, "ua", mundo.company_a, mundo.warehouse_a, m["producto"])[1] == 8.0


def test_las_lineas_de_servicio_no_reservan_y_no_exigen_almacen(mundo):
    cli = _cliente(mundo, "ua", mundo.company_a, "CLI-SERV")
    prod = _producto(mundo, "ua", mundo.company_a, "PRD-SERV")
    ped = _pedido(mundo, "ua", mundo.company_a, "OV-SERV", cli)  # sin almacén
    _linea(mundo, "ua", mundo.company_a, ped, prod, 3, needs_inventory=False)
    r = mundo.post(f"/sales/orders/{ped}/submit", "ua", mundo.company_a, {})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "RELEASED"
    assert _reservas(mundo, "ua", mundo.company_a, ped) == []


def test_un_pedido_vacio_no_se_confirma(mundo):
    cli = _cliente(mundo, "ua", mundo.company_a, "CLI-VACIO")
    ped = _pedido(mundo, "ua", mundo.company_a, "OV-VACIO", cli, mundo.warehouse_a)
    r = mundo.post(f"/sales/orders/{ped}/submit", "ua", mundo.company_a, {})
    assert r.status_code == 422 and r.json()["code"] == "ORDER_EMPTY", r.text


def test_el_listado_devuelve_las_mismas_reservas_que_el_detalle(mundo):
    """El listado las trae por lotes; traerlas por lotes no puede cambiar lo que dicen.

    Sin esta prueba, la consulta agrupada del listado sería el único camino del
    servicio que nadie recorre.
    """
    a = _pedido_listo(mundo, "ua", mundo.company_a, mundo.warehouse_a, "LIST1", stock=10, cantidad=3)
    b = _pedido_listo(mundo, "ua", mundo.company_a, mundo.warehouse_a, "LIST2", stock=10, cantidad=5)
    assert mundo.post(f"/sales/orders/{a['pedido']}/submit", "ua", mundo.company_a, {}).status_code == 200
    # `b` se queda en borrador: el listado tiene que servir los dos casos
    r = mundo.get("/sales/orders", "ua", mundo.company_a)
    assert r.status_code == 200, r.text
    listado = {o["id"]: o for o in r.json()["items"]}
    assert {a["pedido"], b["pedido"]} <= set(listado)

    for pedido_id in (a["pedido"], b["pedido"]):
        del_listado = listado[pedido_id]
        del_detalle = _orden(mundo, "ua", mundo.company_a, pedido_id)
        assert del_listado["status"] == del_detalle["status"]
        assert del_listado["eligible_for_picking"] == del_detalle["eligible_for_picking"]
        assert ([linea["id"] for linea in del_listado["lines"]]
                == [linea["id"] for linea in del_detalle["lines"]])
        assert ([linea["reservations"] for linea in del_listado["lines"]]
                == [linea["reservations"] for linea in del_detalle["lines"]])

    confirmado = listado[a["pedido"]]["lines"][0]["reservations"]
    assert len(confirmado) == 1 and confirmado[0]["status"] == "ACTIVE"
    assert listado[b["pedido"]]["lines"][0]["reservations"] == [], "el borrador no reserva"


def test_el_listado_no_mezcla_las_reservas_de_otra_empresa(mundo):
    """La consulta agrupada acota por empresa, no solo por identificador de pedido."""
    propio = _pedido_listo(mundo, "ua", mundo.company_a, mundo.warehouse_a, "LISTA", stock=10, cantidad=2)
    ajeno = _pedido_listo(mundo, "ub", mundo.company_b, mundo.warehouse_b, "LISTB", stock=10, cantidad=2)
    assert mundo.post(f"/sales/orders/{propio['pedido']}/submit", "ua", mundo.company_a, {}).status_code == 200
    assert mundo.post(f"/sales/orders/{ajeno['pedido']}/submit", "ub", mundo.company_b, {}).status_code == 200

    r = mundo.get("/sales/orders", "ua", mundo.company_a)
    ids = {o["id"] for o in r.json()["items"]}
    assert propio["pedido"] in ids and ajeno["pedido"] not in ids


# --------------------------------------------------------------------------- #
# Almacén y cantidad base
# --------------------------------------------------------------------------- #
def test_confirmar_con_inventario_exige_almacen(mundo):
    """IMP-030-005: el silencio de `_reserve_order` desaparece."""
    cli = _cliente(mundo, "ua", mundo.company_a, "CLI-SINALM")
    prod = _producto(mundo, "ua", mundo.company_a, "PRD-SINALM")
    ped = _pedido(mundo, "ua", mundo.company_a, "OV-SINALM", cli)
    _linea(mundo, "ua", mundo.company_a, ped, prod, 1)
    r = mundo.post(f"/sales/orders/{ped}/submit", "ua", mundo.company_a, {})
    assert r.status_code == 422 and r.json()["code"] == "WAREHOUSE_REQUIRED", r.text
    assert _orden(mundo, "ua", mundo.company_a, ped)["status"] == "DRAFT"


def test_la_reserva_se_hace_en_cantidad_base_y_no_cambia_si_cambia_el_factor(mundo):
    """IMP-030-007/008: caja ×12, 2 cajas → 24 en base; el factor de mañana no toca la reserva."""
    unidad = mundo.crear("/maestros/unidades", "ua", mundo.company_a,
                         {"code": "UND-030", "name": "Unidad", "symbol": "u", "decimals": 0})
    prod = _producto(mundo, "ua", mundo.company_a, "PRD-CAJA", base_unit_id=unidad)
    caja = mundo.crear(f"/maestros/productos/{prod}/presentaciones", "ua", mundo.company_a,
                       {"code": "CAJA12", "name": "Caja de 12", "factor_to_base": "12",
                        "valid_from": (datetime.now(UTC) - timedelta(days=1)).isoformat()})
    _stock(mundo, "ua", mundo.company_a, mundo.warehouse_a, prod, 30)
    cli = _cliente(mundo, "ua", mundo.company_a, "CLI-CAJA")
    ped = _pedido(mundo, "ua", mundo.company_a, "OV-CAJA", cli, mundo.warehouse_a)
    linea = _linea(mundo, "ua", mundo.company_a, ped, prod, 2, presentation_id=caja)
    assert float(linea["base_quantity"]) == 24.0, f"la línea no capturó la base: {linea}"
    assert float(linea["conversion_factor_snapshot"]) == 12.0

    r = mundo.post(f"/sales/orders/{ped}/submit", "ua", mundo.company_a, {})
    assert r.status_code == 200, r.text
    reserva = _reservas(mundo, "ua", mundo.company_a, ped)[0]
    assert float(reserva["quantity"]) == 2.0, "la cantidad tecleada se conserva"
    assert reserva["base_quantity"] == "24.000000", "reservó lo tecleado en vez de la base (IMP-030-007)"
    assert reserva["presentation_id"] == caja
    assert _disponible(mundo, "ua", mundo.company_a, mundo.warehouse_a, prod) == (30.0, 24.0, 6.0)

    # Mañana la caja trae 10: la reserva histórica sigue diciendo 24
    r = mundo.post(f"/maestros/presentaciones/{caja}/versiones", "ua", mundo.company_a,
                   {"factor_to_base": "10", "valid_from": (datetime.now(UTC) + timedelta(seconds=1)).isoformat()})
    assert r.status_code in (200, 201), r.text
    assert _reservas(mundo, "ua", mundo.company_a, ped)[0]["base_quantity"] == "24.000000"


# --------------------------------------------------------------------------- #
# Insuficiencia: todo o nada
# --------------------------------------------------------------------------- #
def test_sin_disponible_el_pedido_sigue_en_borrador_y_nada_se_reserva(mundo):
    """IMP-030-009..012: 409 con detalle por línea; ni reserva ni transición."""
    m = _pedido_listo(mundo, "ua", mundo.company_a, mundo.warehouse_a, "FALTA", stock=6, cantidad=8)
    r = mundo.post(f"/sales/orders/{m['pedido']}/submit", "ua", mundo.company_a, {})
    assert r.status_code == 409, r.text
    cuerpo = r.json()
    assert cuerpo["code"] == "INSUFFICIENT_AVAILABLE"
    detalle = cuerpo["details"]["lines"]
    assert detalle == [{"line_id": m["linea"], "product_id": m["producto"],
                        "requested_base": "8.000000", "available_base": "6.000000"}], detalle
    assert _orden(mundo, "ua", mundo.company_a, m["pedido"])["status"] == "DRAFT"
    assert _reservas(mundo, "ua", mundo.company_a, m["pedido"]) == []
    assert _disponible(mundo, "ua", mundo.company_a, mundo.warehouse_a, m["producto"]) == (6.0, 0.0, 6.0)


def test_multilinea_una_linea_sin_stock_impide_reservar_las_demas(mundo):
    """§42: A alcanza, B no → nada reservado, ambos saldos intactos, pedido DRAFT."""
    cli = _cliente(mundo, "ua", mundo.company_a, "CLI-MULTI")
    pa = _producto(mundo, "ua", mundo.company_a, "PRD-MULTI-A")
    pb = _producto(mundo, "ua", mundo.company_a, "PRD-MULTI-B")
    _stock(mundo, "ua", mundo.company_a, mundo.warehouse_a, pa, 10)
    _stock(mundo, "ua", mundo.company_a, mundo.warehouse_a, pb, 3)
    ped = _pedido(mundo, "ua", mundo.company_a, "OV-MULTI", cli, mundo.warehouse_a)
    _linea(mundo, "ua", mundo.company_a, ped, pa, 8)
    lb = _linea(mundo, "ua", mundo.company_a, ped, pb, 5)
    r = mundo.post(f"/sales/orders/{ped}/submit", "ua", mundo.company_a, {})
    assert r.status_code == 409, r.text
    assert [x["line_id"] for x in r.json()["details"]["lines"]] == [lb["id"]]
    assert _reservas(mundo, "ua", mundo.company_a, ped) == []
    assert _disponible(mundo, "ua", mundo.company_a, mundo.warehouse_a, pa)[1] == 0.0
    assert _disponible(mundo, "ua", mundo.company_a, mundo.warehouse_a, pb)[1] == 0.0
    assert _orden(mundo, "ua", mundo.company_a, ped)["status"] == "DRAFT"

    # El vendedor arregla el borrador: revierte nada (está en DRAFT), no puede
    # tocar líneas emitidas, pero sí añadir stock o dividir. Aquí llega stock.
    _stock(mundo, "ua", mundo.company_a, mundo.warehouse_a, pb, 2)
    r = mundo.post(f"/sales/orders/{ped}/submit", "ua", mundo.company_a, {})
    assert r.status_code == 200, r.text
    assert len(_reservas(mundo, "ua", mundo.company_a, ped)) == 2


def test_la_sobreventa_solo_existe_con_allow_negative_y_queda_marcada(mundo):
    """IMP-030-014/015: política explícita del almacén, reserva íntegra, `oversell` auditado."""
    alm = mundo.crear("/organization/warehouses", "ua", mundo.company_a,
                      {"code": "W-NEG-030", "name": "Negativo", "branch_id": mundo.branch_a,
                       "company_id": mundo.company_a})
    _sql(mundo, "UPDATE warehouses SET policies = CAST(:p AS JSON) WHERE id = :w",
         p='{"allow_negative": true}', w=alm)
    m = _pedido_listo(mundo, "ua", mundo.company_a, alm, "NEG", stock=6, cantidad=8)
    r = mundo.post(f"/sales/orders/{m['pedido']}/submit", "ua", mundo.company_a, {})
    assert r.status_code == 200, r.text
    reserva = _reservas(mundo, "ua", mundo.company_a, m["pedido"])[0]
    assert reserva["oversell"] is True
    assert reserva["base_quantity"] == "8.000000", "la sobreventa autorizada reserva entero, no parcial"
    assert _disponible(mundo, "ua", mundo.company_a, alm, m["producto"]) == (6.0, 8.0, -2.0)
    evento = _sql(mundo, "SELECT after FROM audit_events WHERE action = 'RESERVATION_CREATED' "
                         "AND entity_id = :r", r=reserva["id"]).fetchone()
    assert evento is not None and evento[0]["oversell"] is True
    assert evento[0]["available_before"] == "6.000000"


# --------------------------------------------------------------------------- #
# Crédito: SUBMITTED mientras 045 decide; aprobar libera; rechazar devuelve
# --------------------------------------------------------------------------- #
def test_con_credito_el_pedido_espera_en_submitted_con_la_reserva_hecha(mundo):
    """IMP-030-025/026/028/029/030: la reserva precede al crédito y sobrevive a la aprobación."""
    pid = _politica_de_credito(mundo, "ua", mundo.company_a)
    try:
        m = _pedido_listo(mundo, "ua", mundo.company_a, mundo.warehouse_a, "CRED", stock=10, cantidad=8)
        r = mundo.post(f"/sales/orders/{m['pedido']}/submit", "ua", mundo.company_a, {})
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "SUBMITTED", "con política debía esperar en SUBMITTED"
        assert r.json()["approval_ref"], "sin solicitud de 045 enlazada"
        assert _disponible(mundo, "ua", mundo.company_a, mundo.warehouse_a, m["producto"])[1] == 8.0
        estado = _estado_aprobacion(mundo, "ua", mundo.company_a, m["pedido"])
        assert estado["blocks_advance"] is True

        # Liberar antes de la decisión: bloqueado por 045, no por ventas
        r = mundo.post(f"/sales/orders/{m['pedido']}/release", "ua", mundo.company_a, {})
        assert r.status_code == 409 and r.json()["code"] == "APPROVAL_PENDING", r.text

        paso = _paso_pendiente(mundo, "uab", mundo.company_a, m["pedido"])
        r = mundo.post(f"/approvals/steps/{paso}/approve", "uab", mundo.company_a, {"reason": None})
        assert r.status_code == 200, r.text

        r = mundo.post(f"/sales/orders/{m['pedido']}/release", "ua", mundo.company_a, {})
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "RELEASED"
        reservas = _reservas(mundo, "ua", mundo.company_a, m["pedido"])
        assert len(reservas) == 1 and reservas[0]["status"] == "ACTIVE", "aprobar no crea ni cierra reservas"
        assert _disponible(mundo, "ua", mundo.company_a, mundo.warehouse_a, m["producto"])[1] == 8.0
    finally:
        _cerrar_politica(mundo, "ua", mundo.company_a, pid)


def test_rechazar_el_credito_libera_toda_la_reserva_en_la_misma_transaccion(mundo):
    """IMP-030-031/032/033."""
    pid = _politica_de_credito(mundo, "ua", mundo.company_a)
    try:
        m = _pedido_listo(mundo, "ua", mundo.company_a, mundo.warehouse_a, "RECH", stock=10, cantidad=8)
        assert mundo.post(f"/sales/orders/{m['pedido']}/submit", "ua", mundo.company_a, {}).json()["status"] == "SUBMITTED"
        # 045 rechaza; el pedido no puede liberarse, y rechazarlo devuelve el stock
        paso = _paso_pendiente(mundo, "uab", mundo.company_a, m["pedido"])
        r = mundo.post(f"/approvals/steps/{paso}/reject", "uab", mundo.company_a, {"reason": "Sin cupo"})
        assert r.status_code == 200, r.text
        r = mundo.post(f"/sales/orders/{m['pedido']}/release", "ua", mundo.company_a, {})
        assert r.status_code == 409 and r.json()["code"] == "APPROVAL_NOT_GRANTED", r.text

        r = mundo.post(f"/sales/orders/{m['pedido']}/reject", "ua", mundo.company_a, {})
        assert r.status_code == 422, "rechazar sin motivo debía fallar (IMP-030-035)"
        r = mundo.post(f"/sales/orders/{m['pedido']}/reject", "ua", mundo.company_a, {"reason": "Sin cupo"})
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "REJECTED" and r.json()["status_reason"] == "Sin cupo"
        reserva = _reservas(mundo, "ua", mundo.company_a, m["pedido"])[0]
        assert reserva["status"] == "RELEASED" and reserva["release_reason"] == "CREDIT_REJECTED"
        assert _disponible(mundo, "ua", mundo.company_a, mundo.warehouse_a, m["producto"]) == (10.0, 0.0, 10.0)
    finally:
        _cerrar_politica(mundo, "ua", mundo.company_a, pid)


def test_rechazar_desde_ventas_cierra_la_solicitud_viva_de_045(mundo):
    """Una solicitud no queda huérfana cuando el pedido se rechaza por ventas."""
    pid = _politica_de_credito(mundo, "ua", mundo.company_a)
    try:
        m = _pedido_listo(mundo, "ua", mundo.company_a, mundo.warehouse_a, "RECH2", stock=10, cantidad=8)
        mundo.post(f"/sales/orders/{m['pedido']}/submit", "ua", mundo.company_a, {})
        r = mundo.post(f"/sales/orders/{m['pedido']}/reject", "ua", mundo.company_a, {"reason": "Cliente moroso"})
        assert r.status_code == 200, r.text
        estado = _estado_aprobacion(mundo, "ua", mundo.company_a, m["pedido"])
        assert estado["current"]["status"] == "CANCELLED", estado["current"]["status"]
        assert estado["blocks_advance"] is False
    finally:
        _cerrar_politica(mundo, "ua", mundo.company_a, pid)


# --------------------------------------------------------------------------- #
# Modificar = revertir a borrador; cancelar libera
# --------------------------------------------------------------------------- #
def test_un_pedido_emitido_no_admite_lineas(mundo):
    m = _pedido_listo(mundo, "ua", mundo.company_a, mundo.warehouse_a, "NOEDIT")
    mundo.post(f"/sales/orders/{m['pedido']}/submit", "ua", mundo.company_a, {})
    r = mundo.post(f"/sales/orders/{m['pedido']}/lines", "ua", mundo.company_a,
                   {"product_id": m["producto"], "quantity": 1, "unit_price": 10})
    assert r.status_code == 409 and r.json()["code"] == "ORDER_NOT_EDITABLE", r.text


def test_revertir_libera_todo_y_reemitir_reserva_desde_cero(mundo):
    """IMP-030-036..039 y IMP-030-047: la aprobación previa no sobrevive."""
    pid = _politica_de_credito(mundo, "ua", mundo.company_a)
    try:
        m = _pedido_listo(mundo, "ua", mundo.company_a, mundo.warehouse_a, "REV", stock=20, cantidad=8)
        mundo.post(f"/sales/orders/{m['pedido']}/submit", "ua", mundo.company_a, {})
        paso = _paso_pendiente(mundo, "uab", mundo.company_a, m["pedido"])
        mundo.post(f"/approvals/steps/{paso}/approve", "uab", mundo.company_a, {"reason": None})
        assert mundo.post(f"/sales/orders/{m['pedido']}/release", "ua", mundo.company_a, {}).json()["status"] == "RELEASED"

        r = mundo.post(f"/sales/orders/{m['pedido']}/revert", "ua", mundo.company_a, {"reason": "El cliente quiere 12"})
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "DRAFT" and r.json()["approval_ref"] is None
        assert _disponible(mundo, "ua", mundo.company_a, mundo.warehouse_a, m["producto"]) == (20.0, 0.0, 20.0)
        assert [x["release_reason"] for x in _reservas(mundo, "ua", mundo.company_a, m["pedido"])] == ["ORDER_REVERTED"]

        # Modificar: ahora sí admite líneas. Reemitir reserva desde cero y vuelve a pedir crédito
        _linea(mundo, "ua", mundo.company_a, m["pedido"], m["producto"], 4)
        r = mundo.post(f"/sales/orders/{m['pedido']}/submit", "ua", mundo.company_a, {})
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "SUBMITTED", "la aprobación anterior no debía reutilizarse"
        activas = [x for x in _reservas(mundo, "ua", mundo.company_a, m["pedido"]) if x["status"] == "ACTIVE"]
        assert sorted(float(x["base_quantity"]) for x in activas) == [4.0, 8.0]
        assert _disponible(mundo, "ua", mundo.company_a, mundo.warehouse_a, m["producto"])[1] == 12.0
    finally:
        _cerrar_politica(mundo, "ua", mundo.company_a, pid)


def test_cancelar_libera_y_el_segundo_intento_choca_sin_restar_dos_veces(mundo):
    """IMP-030-034/035, §56/§57."""
    m = _pedido_listo(mundo, "ua", mundo.company_a, mundo.warehouse_a, "CANC")
    mundo.post(f"/sales/orders/{m['pedido']}/submit", "ua", mundo.company_a, {})
    r = mundo.post(f"/sales/orders/{m['pedido']}/cancel", "ua", mundo.company_a, {})
    assert r.status_code == 422, "cancelar sin motivo debía fallar"
    r = mundo.post(f"/sales/orders/{m['pedido']}/cancel", "ua", mundo.company_a, {"reason": "Cliente desistió"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "CANCELLED"
    assert _disponible(mundo, "ua", mundo.company_a, mundo.warehouse_a, m["producto"]) == (10.0, 0.0, 10.0)
    r = mundo.post(f"/sales/orders/{m['pedido']}/cancel", "ua", mundo.company_a, {"reason": "otra vez"})
    assert r.status_code == 409, r.text
    assert _disponible(mundo, "ua", mundo.company_a, mundo.warehouse_a, m["producto"])[1] == 0.0
    reserva = _reservas(mundo, "ua", mundo.company_a, m["pedido"])[0]
    assert reserva["status"] == "RELEASED" and reserva["release_reason"] == "ORDER_CANCELLED"


def test_la_reserva_de_un_pedido_no_se_libera_a_mano(mundo):
    """§62/§63: liberar manualmente es para reservas manuales y con motivo."""
    m = _pedido_listo(mundo, "ua", mundo.company_a, mundo.warehouse_a, "MANUAL")
    mundo.post(f"/sales/orders/{m['pedido']}/submit", "ua", mundo.company_a, {})
    reserva = _reservas(mundo, "ua", mundo.company_a, m["pedido"])[0]
    r = mundo.post(f"/inventory/reservations/{reserva['id']}/release", "ua", mundo.company_a, {"reason": "quiero"})
    assert r.status_code == 409 and r.json()["code"] == "RESERVATION_ORDER_BOUND", r.text

    manual = mundo.crear("/inventory/reservations", "ua", mundo.company_a,
                         {"product_id": m["producto"], "warehouse_id": mundo.warehouse_a, "quantity": 1})
    r = mundo.post(f"/inventory/reservations/{manual}/release", "ua", mundo.company_a, {})
    assert r.status_code == 422, "liberar a mano sin motivo debía fallar"
    r = mundo.post(f"/inventory/reservations/{manual}/release", "ua", mundo.company_a, {"reason": "Se vendió aparte"})
    assert r.status_code == 200, r.text
    assert r.json()["release_reason"] == "MANUAL:Se vendió aparte" and r.json()["trigger"] == "MANUAL"
    r = mundo.post(f"/inventory/reservations/{manual}/release", "ua", mundo.company_a, {"reason": "de nuevo"})
    assert r.status_code == 409 and r.json()["code"] == "RESERVATION_NOT_ACTIVE"


# --------------------------------------------------------------------------- #
# TTL y expiración: sin worker, idempotente, expira también el pedido
# --------------------------------------------------------------------------- #
def test_ttl_opcional_solo_mientras_espera_credito_y_expirar_cierra_el_pedido(mundo):
    """IMP-030-040..044."""
    r = mundo.get("/sales/settings/reservation", "ua", mundo.company_a)
    assert r.status_code == 200 and r.json() == {"reservation_trigger": "ORDER_CONFIRMATION",
                                                 "trigger_configurable": False, "reservation_ttl_days": None}
    r = mundo.put_json("/sales/settings/reservation", "ua", mundo.company_a, {"reservation_ttl_days": 2})
    assert r.status_code == 200, r.text
    pid = _politica_de_credito(mundo, "ua", mundo.company_a)
    try:
        m = _pedido_listo(mundo, "ua", mundo.company_a, mundo.warehouse_a, "TTL", stock=10, cantidad=8)
        mundo.post(f"/sales/orders/{m['pedido']}/submit", "ua", mundo.company_a, {})
        reserva = _reservas(mundo, "ua", mundo.company_a, m["pedido"])[0]
        assert reserva["expires_at"] is not None, "con TTL la reserva a la espera de crédito debía vencer"

        # Sin TTL cumplido no pasa nada (idempotente y seguro)
        r = mundo.post("/sales/orders/expire-reservations", "ua", mundo.company_a, {})
        assert r.status_code == 200 and r.json() == {"expired_reservations": 0, "expired_orders": 0}

        # El reloj avanza: se fuerza el vencimiento en la base
        _sql(mundo, "UPDATE reservations SET expires_at = :t WHERE id = :i",
             t=datetime.now(UTC) - timedelta(minutes=1), i=reserva["id"])
        r = mundo.post("/sales/orders/expire-reservations", "ua", mundo.company_a, {})
        assert r.status_code == 200 and r.json() == {"expired_reservations": 1, "expired_orders": 1}, r.text
        assert _orden(mundo, "ua", mundo.company_a, m["pedido"])["status"] == "EXPIRED"
        assert _reservas(mundo, "ua", mundo.company_a, m["pedido"])[0]["status"] == "EXPIRED"
        assert _disponible(mundo, "ua", mundo.company_a, mundo.warehouse_a, m["producto"]) == (10.0, 0.0, 10.0)
        assert _estado_aprobacion(mundo, "ua", mundo.company_a, m["pedido"])["blocks_advance"] is False
        r = mundo.post("/sales/orders/expire-reservations", "ua", mundo.company_a, {})
        assert r.json() == {"expired_reservations": 0, "expired_orders": 0}, "la segunda pasada no debía restar nada"

        # Un pedido de contado (RELEASED) no lleva vencimiento aunque haya TTL
        _cerrar_politica(mundo, "ua", mundo.company_a, pid)
        pid = None
        m2 = _pedido_listo(mundo, "ua", mundo.company_a, mundo.warehouse_a, "TTL2", stock=10, cantidad=1)
        assert mundo.post(f"/sales/orders/{m2['pedido']}/submit", "ua", mundo.company_a, {}).json()["status"] == "RELEASED"
        assert _reservas(mundo, "ua", mundo.company_a, m2["pedido"])[0]["expires_at"] is None
    finally:
        if pid:
            _cerrar_politica(mundo, "ua", mundo.company_a, pid)
        mundo.put_json("/sales/settings/reservation", "ua", mundo.company_a, {"reservation_ttl_days": None})


# --------------------------------------------------------------------------- #
# Despacho consume; sin efectos en picking, factura ni CxC
# --------------------------------------------------------------------------- #
def test_liberar_a_preparacion_no_crea_picking_factura_ni_cxc_y_despachar_consume(mundo):
    """IMP-030-054..057 y R-D0-03-7."""
    antes = {t: _contar(mundo, t) for t in ("pick_lists", "sales_invoices", "ap_open_items")}
    m = _pedido_listo(mundo, "ua", mundo.company_a, mundo.warehouse_a, "DESP", stock=10, cantidad=4)
    assert mundo.post(f"/sales/orders/{m['pedido']}/submit", "ua", mundo.company_a, {}).json()["status"] == "RELEASED"
    despues = {t: _contar(mundo, t) for t in ("pick_lists", "sales_invoices", "ap_open_items")}
    assert antes == despues, f"RELEASED produjo efectos ajenos: {antes} → {despues}"

    # Despachar desde `RELEASED` ya no es posible: el ¶103 exige «Pedido
    # preparado + Pedido confirmado + Factura emitida» antes de la salida
    # física, y la Spec 035 lo hace cumplir. Esta prueba afirmaba lo contrario
    # porque se escribió cuando la cadena no existía.
    r = mundo.post("/sales/shipments", "ua", mundo.company_a, {
        "code": f"SH-{m['pedido'][:6]}", "order_id": m["pedido"],
        "origin_warehouse_id": mundo.warehouse_a,
        "lines": [{"product_id": m["producto"], "quantity": 4}]})
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "ORDER_NOT_SHIPPABLE"
    reserva = _reservas(mundo, "ua", mundo.company_a, m["pedido"])[0]
    assert reserva["status"] == "ACTIVE", "la reserva se consumió sin despachar"
    # Que el despacho **consume** la reserva (`R-D0-03-7`) lo prueba la cadena
    # completa en `test_spec035_dispatch.py`, que es su dueña.


# --------------------------------------------------------------------------- #
# Multiempresa (ARCH-MC-001)
# --------------------------------------------------------------------------- #
def test_usuario_ab_bajo_contexto_a_no_confirma_ni_cancela_el_pedido_de_b(mundo):
    """IMP-030-045/047/049: tener acceso a B no permite operar B bajo A."""
    m = _pedido_listo(mundo, "ub", mundo.company_b, mundo.warehouse_b, "AB")
    for accion, cuerpo in (("submit", {}), ("cancel", {"reason": "x"}), ("revert", {"reason": "x"}),
                           ("reject", {"reason": "x"}), ("release", {})):
        r = mundo.post(f"/sales/orders/{m['pedido']}/{accion}", "uab", mundo.company_a, cuerpo)
        assert r.status_code == 404, f"{accion}: {r.status_code} {r.text}"
    assert _orden(mundo, "ub", mundo.company_b, m["pedido"])["status"] == "DRAFT"
    assert _reservas(mundo, "ub", mundo.company_b, m["pedido"]) == []
    # Bajo B, el mismo usuario sí puede
    r = mundo.post(f"/sales/orders/{m['pedido']}/submit", "uab", mundo.company_b, {})
    assert r.status_code == 200, r.text


def test_cross_tenant_bloqueado(mundo):
    """IMP-030-046."""
    m = _pedido_listo(mundo, "ua", mundo.company_a, mundo.warehouse_a, "XT")
    r = mundo.post(f"/sales/orders/{m['pedido']}/submit", "uc", mundo.company_c, {}, tenant="T2")
    assert r.status_code == 404, r.text
    assert _orden(mundo, "ua", mundo.company_a, m["pedido"])["status"] == "DRAFT"


def test_el_almacen_de_otra_empresa_no_sirve_ni_por_debajo(mundo):
    """§13: aunque el almacén de B se cuele en el pedido de A, confirmar responde 404."""
    m = _pedido_listo(mundo, "ua", mundo.company_a, mundo.warehouse_a, "WB")
    _sql(mundo, "UPDATE sales_orders SET warehouse_id = :w WHERE id = :o", w=mundo.warehouse_b, o=m["pedido"])
    r = mundo.post(f"/sales/orders/{m['pedido']}/submit", "ua", mundo.company_a, {})
    assert r.status_code == 404 and r.json()["code"] == "WAREHOUSE_NOT_FOUND", r.text
    assert _reservas(mundo, "ub", mundo.company_b) == [x for x in _reservas(mundo, "ub", mundo.company_b)
                                                       if x["source_order_id"] != m["pedido"]]


def test_el_cuerpo_no_elige_la_empresa(mundo):
    """IMP-030-048: un campo ajeno responde 422; nunca se lee."""
    m = _pedido_listo(mundo, "ua", mundo.company_a, mundo.warehouse_a, "BODY")
    r = mundo.post(f"/sales/orders/{m['pedido']}/cancel", "ua", mundo.company_a,
                   {"reason": "x", "company_id": mundo.company_b})
    assert r.status_code == 422, r.text
    r = mundo.put_json("/sales/settings/reservation", "ua", mundo.company_a,
                       {"reservation_ttl_days": 3, "company_id": mundo.company_b})
    assert r.status_code == 422, r.text
    assert mundo.get("/sales/settings/reservation", "ub", mundo.company_b).json()["reservation_ttl_days"] is None


# --------------------------------------------------------------------------- #
# Auditoría
# --------------------------------------------------------------------------- #
def test_la_auditoria_de_la_reserva_dice_quien_que_cuanto_y_por_que(mundo):
    """IMP-030-050..052."""
    m = _pedido_listo(mundo, "ua", mundo.company_a, mundo.warehouse_a, "AUD")
    mundo.post(f"/sales/orders/{m['pedido']}/submit", "ua", mundo.company_a, {})
    mundo.post(f"/sales/orders/{m['pedido']}/cancel", "ua", mundo.company_a, {"reason": "Auditoría"})
    reserva = _reservas(mundo, "ua", mundo.company_a, m["pedido"])[0]
    filas = _sql(mundo, "SELECT action, user_id, company_id, tenant_id, after, reason FROM audit_events "
                        "WHERE entity_type = 'Reservation' AND entity_id = :r ORDER BY created_at", r=reserva["id"]).fetchall()
    acciones = [f[0] for f in filas]
    assert acciones == ["RESERVATION_CREATED", "RESERVATION_RELEASED"], acciones
    creada = filas[0]
    assert creada[1] and creada[2] == mundo.company_a and creada[3] == mundo.t1
    after = creada[4]
    for campo in ("source_order_id", "source_line_id", "warehouse_id", "product_id", "quantity",
                  "base_quantity", "uom_id", "presentation_id", "trigger", "oversell", "available_before"):
        assert campo in after, f"falta {campo} en la auditoría"
    assert after["source_order_id"] == m["pedido"] and after["source_line_id"] == m["linea"]
    assert after["trigger"] == "ORDER_CONFIRMATION" and after["base_quantity"] == "8.000000"
    liberada = filas[1]
    assert liberada[4]["release_reason"] == "ORDER_CANCELLED" and liberada[5] == "ORDER_CANCELLED"
    pedido = _sql(mundo, "SELECT reason FROM audit_events WHERE entity_type = 'SalesOrder' AND entity_id = :o "
                         "AND action = 'SALES_ORDER_TRANSITIONED' ORDER BY created_at DESC", o=m["pedido"]).fetchone()
    assert pedido[0] == "Auditoría"


# --------------------------------------------------------------------------- #
# Compatibilidad: la ruta genérica delega
# --------------------------------------------------------------------------- #
def test_la_transicion_generica_delega_y_los_estados_viejos_no_existen(mundo):
    m = _pedido_listo(mundo, "ua", mundo.company_a, mundo.warehouse_a, "COMPAT")
    for viejo in ("CREDIT_PENDING", "APPROVED", "RESERVED"):
        r = mundo.post(f"/sales/orders/{m['pedido']}/transition", "ua", mundo.company_a, {"target": viejo})
        assert r.status_code == 409, f"{viejo}: {r.text}"
    r = mundo.post(f"/sales/orders/{m['pedido']}/transition", "ua", mundo.company_a, {"target": "SUBMITTED"})
    assert r.status_code == 200 and r.json()["status"] == "RELEASED", r.text
    assert len(_reservas(mundo, "ua", mundo.company_a, m["pedido"])) == 1
    r = mundo.post(f"/sales/orders/{m['pedido']}/transition", "ua", mundo.company_a, {"target": "CANCELLED"})
    assert r.status_code == 422 and r.json()["code"] == "REASON_REQUIRED"
    r = mundo.post(f"/sales/orders/{m['pedido']}/transition", "ua", mundo.company_a,
                   {"target": "CANCELLED", "reason": "compat"})
    assert r.status_code == 200 and r.json()["status"] == "CANCELLED"
