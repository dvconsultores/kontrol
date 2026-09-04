"""Recepción física — Spec 019.

El DOCX de procesos §2 describe doce etapas; ocho son de esta Spec. Existía la
recepción **contable** —qué orden, qué producto, cuánto— y faltaba la **física**:
cuándo llegó, cuántos bultos, contra qué se comparó, qué se vio al inspeccionar
y con qué unidad se recibió.

Lo que estas pruebas protegen es `P23`: nada de eso se reconstruye cuando el
camión se ha ido. Y protegen el defecto que lo hacía peligroso: el asiento de
inventario tomaba la cantidad tecleada como si fuera la base.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import text

pytest_plugins = ("tests.conftest_multicompany",)


# --------------------------------------------------------------------------- #
# Mundo mínimo: proveedor, producto, orden aprobada y recepción
# --------------------------------------------------------------------------- #
def _proveedor(mundo, usuario, empresa, code):
    return mundo.crear("/maestros/terceros", usuario, empresa,
                       {"code": code, "name": f"Proveedor {code}", "roles": ["PROVEEDOR"]})


def _producto(mundo, usuario, empresa, code, base_unit_id=None):
    cuerpo = {"code": code, "name": f"Producto {code}", "item_type": "PRODUCT"}
    if base_unit_id:
        cuerpo["base_unit_id"] = base_unit_id
    return mundo.crear("/maestros/catalogos/items", usuario, empresa, cuerpo)


def _orden_aprobada(mundo, usuario, empresa, marca, producto, cantidad=100, precio=5):
    """Orden de compra aprobada con una línea, lista para recibirse."""
    prov = _proveedor(mundo, usuario, empresa, f"PRV-{marca}")
    oc = mundo.crear("/purchasing/orders", usuario, empresa,
                     {"code": f"OC-{marca}", "supplier_id": prov, "currency": "VED"})
    r = mundo.post(f"/purchasing/orders/{oc}/lines", usuario, empresa,
                   {"product_id": producto, "quantity_ordered": cantidad, "unit_price": precio})
    assert r.status_code == 200, r.text
    linea = r.json()["id"]
    for destino in ("SUBMITTED", "APPROVED"):
        r = mundo.post(f"/purchasing/orders/{oc}/transition", usuario, empresa, {"target": destino})
        assert r.status_code == 200, f"{destino}: {r.text}"
    return {"orden": oc, "linea": linea, "proveedor": prov}


def _recepcion(mundo, usuario, empresa, marca, orden, almacen, **extra):
    cuerpo = {"code": f"REC-{marca}", "order_id": orden, "warehouse_id": almacen}
    cuerpo.update(extra)
    r = mundo.post("/purchasing/receipts", usuario, empresa, cuerpo)
    assert r.status_code == 200, r.text
    return r.json()


def _linea(mundo, usuario, empresa, recepcion, orden_linea, producto, recibido, aceptado=None, **extra):
    cuerpo = {"order_line_id": orden_linea, "product_id": producto,
              "quantity_received": recibido,
              "quantity_accepted": recibido if aceptado is None else aceptado,
              "quantity_rejected": 0 if aceptado is None else recibido - aceptado}
    cuerpo.update(extra)
    r = mundo.post(f"/purchasing/receipts/{recepcion}/lines", usuario, empresa, cuerpo)
    return r


def _ver(mundo, usuario, empresa, recepcion):
    r = mundo.get(f"/purchasing/receipts/{recepcion}", usuario, empresa)
    assert r.status_code == 200, r.text
    return r.json()


def _saldo(mundo, usuario, empresa, almacen, producto):
    r = mundo.get("/inventory/balances", usuario, empresa)
    assert r.status_code == 200, r.text
    for s in r.json()["items"]:
        if s["product_id"] == producto and s["warehouse_id"] == almacen:
            return float(s["qty_on_hand"]), s.get("location_id")
    return 0.0, None


def _sql(mundo, sentencia, **params):
    db = mundo.factory()
    try:
        out = db.execute(text(sentencia), params).fetchall()
        db.commit()
        return out
    finally:
        db.close()


def _aceptar(mundo, usuario, empresa, recepcion):
    for accion, cuerpo in (("confirm", {}), ("quality", {"quality_status": "APPROVED"}), ("accept", {})):
        r = mundo.post(f"/purchasing/receipts/{recepcion}/{accion}", usuario, empresa, cuerpo)
        assert r.status_code == 200, f"{accion}: {r.text}"
    return r.json()


# --------------------------------------------------------------------------- #
# El defecto P0: la cantidad base
# --------------------------------------------------------------------------- #
def test_recibir_dos_cajas_de_doce_ingresa_veinticuatro_unidades(mundo):
    """El caso que esta Spec existe para cerrar (§31 de la autorización).

    Antes, la línea no guardaba presentación ni cantidad base y el asiento
    tomaba la cantidad tecleada: dos cajas entraban como dos unidades.
    """
    unidad = mundo.crear("/maestros/unidades", "ua", mundo.company_a,
                         {"code": "UND-019", "name": "Unidad", "symbol": "u", "decimals": 0})
    prod = _producto(mundo, "ua", mundo.company_a, "P019-CAJA", base_unit_id=unidad)
    caja = mundo.crear(f"/maestros/productos/{prod}/presentaciones", "ua", mundo.company_a,
                       {"code": "CAJA12-019", "name": "Caja de 12", "factor_to_base": "12",
                        "valid_from": (datetime.now(UTC) - timedelta(days=1)).isoformat()})
    oc = _orden_aprobada(mundo, "ua", mundo.company_a, "CAJA", prod, cantidad=100)
    rec = _recepcion(mundo, "ua", mundo.company_a, "CAJA", oc["orden"], mundo.warehouse_a)

    r = _linea(mundo, "ua", mundo.company_a, rec["id"], oc["linea"], prod, 2, presentation_id=caja)
    assert r.status_code == 200, r.text
    linea = r.json()
    assert float(linea["quantity_received"]) == 2.0, "la cantidad tecleada se conserva"
    assert float(linea["base_quantity_received"]) == 24.0, "no capturó la cantidad base"
    assert float(linea["base_quantity_accepted"]) == 24.0
    assert float(linea["conversion_factor_snapshot"]) == 12.0, "no congeló el factor"
    assert linea["presentation_id"] == caja
    assert linea["uom_source"] == "CAPTURED"

    _aceptar(mundo, "ua", mundo.company_a, rec["id"])
    on_hand, location = _saldo(mundo, "ua", mundo.company_a, mundo.warehouse_a, prod)
    assert on_hand == 24.0, f"el inventario registró {on_hand} en vez de 24"
    assert location is None, "recibir no es ubicar: la ubicación es de la Spec 022"


def test_la_recepcion_historica_no_cambia_si_cambia_el_factor(mundo):
    """§32: el maestro puede cambiar mañana; lo recibido ayer no."""
    unidad = mundo.crear("/maestros/unidades", "ua", mundo.company_a,
                         {"code": "UND-INV", "name": "Unidad", "symbol": "u", "decimals": 0})
    prod = _producto(mundo, "ua", mundo.company_a, "P019-INV", base_unit_id=unidad)
    caja = mundo.crear(f"/maestros/productos/{prod}/presentaciones", "ua", mundo.company_a,
                       {"code": "CAJA6-019", "name": "Caja de 6", "factor_to_base": "6",
                        "valid_from": (datetime.now(UTC) - timedelta(days=1)).isoformat()})
    oc = _orden_aprobada(mundo, "ua", mundo.company_a, "INV", prod)
    rec = _recepcion(mundo, "ua", mundo.company_a, "INV", oc["orden"], mundo.warehouse_a)
    _linea(mundo, "ua", mundo.company_a, rec["id"], oc["linea"], prod, 3, presentation_id=caja)
    _aceptar(mundo, "ua", mundo.company_a, rec["id"])
    on_hand, _ = _saldo(mundo, "ua", mundo.company_a, mundo.warehouse_a, prod)
    assert on_hand == 18.0

    r = mundo.post(f"/maestros/presentaciones/{caja}/versiones", "ua", mundo.company_a,
                   {"factor_to_base": "10", "valid_from": (datetime.now(UTC) + timedelta(seconds=1)).isoformat()})
    assert r.status_code in (200, 201), r.text

    despues = _ver(mundo, "ua", mundo.company_a, rec["id"])["lines"][0]
    assert float(despues["conversion_factor_snapshot"]) == 6.0, "reinterpretó una recepción histórica"
    assert float(despues["base_quantity_received"]) == 18.0
    on_hand_2, _ = _saldo(mundo, "ua", mundo.company_a, mundo.warehouse_a, prod)
    assert on_hand_2 == 18.0, "el movimiento histórico cambió"


def test_sin_presentacion_la_cantidad_ya_esta_en_base(mundo):
    """El caso demostrable de R-011-4: sin presentación, factor 1."""
    prod = _producto(mundo, "ua", mundo.company_a, "P019-SIMPLE")
    oc = _orden_aprobada(mundo, "ua", mundo.company_a, "SIMPLE", prod)
    rec = _recepcion(mundo, "ua", mundo.company_a, "SIMPLE", oc["orden"], mundo.warehouse_a)
    linea = _linea(mundo, "ua", mundo.company_a, rec["id"], oc["linea"], prod, 7).json()
    assert float(linea["base_quantity_received"]) == 7.0
    assert float(linea["conversion_factor_snapshot"]) == 1.0


# --------------------------------------------------------------------------- #
# Etapas 1 y 2: arribo y programación
# --------------------------------------------------------------------------- #
def test_la_recepcion_registra_el_arribo_y_la_descarga_programada(mundo):
    """Etapas 1 y 2. El instante del arribo no se reconstruye después."""
    prod = _producto(mundo, "ua", mundo.company_a, "P019-ARR")
    oc = _orden_aprobada(mundo, "ua", mundo.company_a, "ARR", prod)
    programada = (datetime.now(UTC) + timedelta(hours=6)).replace(microsecond=0)
    rec = _recepcion(mundo, "ua", mundo.company_a, "ARR", oc["orden"], mundo.warehouse_a,
                     unloading_scheduled_at=programada.isoformat(),
                     packing_list_ref="PL-778", supplier_invoice_ref="FAC-991", packages_declared=12)
    assert rec["unloading_scheduled_at"] is not None
    assert rec["packing_list_ref"] == "PL-778" and rec["supplier_invoice_ref"] == "FAC-991"
    assert rec["packages_declared"] == 12
    assert rec["arrival_at"] is None, "el arribo aún no se ha confirmado"

    r = mundo.post(f"/purchasing/receipts/{rec['id']}/arrival", "ua", mundo.company_a,
                   {"packages_received": 11})
    assert r.status_code == 200, r.text
    confirmada = r.json()
    assert confirmada["arrival_at"] is not None
    assert confirmada["arrival_confirmed_by"], "no registró quién confirmó el arribo"
    assert confirmada["packages_received"] == 11, "no registró los bultos contados"
    assert confirmada["packages_declared"] == 12, "la diferencia con lo declarado queda a la vista"


def test_los_bultos_no_pueden_ser_negativos(mundo):
    prod = _producto(mundo, "ua", mundo.company_a, "P019-NEG")
    oc = _orden_aprobada(mundo, "ua", mundo.company_a, "NEG", prod)
    r = mundo.post("/purchasing/receipts", "ua", mundo.company_a,
                   {"code": "REC-NEG", "order_id": oc["orden"], "warehouse_id": mundo.warehouse_a,
                    "packages_declared": -1})
    assert r.status_code == 422, r.text
    rec = _recepcion(mundo, "ua", mundo.company_a, "NEG2", oc["orden"], mundo.warehouse_a)
    r = mundo.post(f"/purchasing/receipts/{rec['id']}/arrival", "ua", mundo.company_a,
                   {"packages_received": -3})
    assert r.status_code == 422, r.text


# --------------------------------------------------------------------------- #
# Etapas 4, 5 y 6: comparación, inspección y observación física
# --------------------------------------------------------------------------- #
def test_la_inspeccion_guarda_contra_que_se_comparo_y_con_que_resultado(mundo):
    """Etapa 4. Saber que alguien comparó, sin saber contra qué ni con qué
    resultado, deja la etapa sin valor probatorio."""
    prod = _producto(mundo, "ua", mundo.company_a, "P019-INSP")
    oc = _orden_aprobada(mundo, "ua", mundo.company_a, "INSP", prod)
    rec = _recepcion(mundo, "ua", mundo.company_a, "INSP", oc["orden"], mundo.warehouse_a,
                     packing_list_ref="PL-1", supplier_invoice_ref="FAC-1", packages_declared=5)
    r = mundo.post(f"/purchasing/receipts/{rec['id']}/inspection", "ua", mundo.company_a,
                   {"packing_list_match": True, "supplier_invoice_match": False, "order_match": True,
                    "documentation_match": True, "packages_received": 5,
                    "notes": "Una caja con el precinto forzado"})
    assert r.status_code == 200, r.text
    insp = r.json()
    assert insp["packing_list_match"] is True and insp["supplier_invoice_match"] is False
    assert insp["order_match"] is True and insp["documentation_match"] is True
    assert insp["inspected_at"] is not None and insp["inspected_by"]
    assert insp["inspection_notes"] == "Una caja con el precinto forzado"
    assert insp["packages_received"] == 5


def test_la_linea_conserva_lo_que_se_observo_en_el_muelle(mundo):
    """Etapa 6. El hecho observado es de 019; la incidencia que derive, de 020."""
    prod = _producto(mundo, "ua", mundo.company_a, "P019-DANO")
    oc = _orden_aprobada(mundo, "ua", mundo.company_a, "DANO", prod)
    rec = _recepcion(mundo, "ua", mundo.company_a, "DANO", oc["orden"], mundo.warehouse_a)
    r = _linea(mundo, "ua", mundo.company_a, rec["id"], oc["linea"], prod, 20, aceptado=18,
               physical_condition="DAÑADO", damaged_quantity=2,
               damage_notes="Dos unidades con la caja aplastada", identification_ok=True, reference_ok=False)
    assert r.status_code == 200, r.text
    linea = r.json()
    assert linea["physical_condition"] == "DAÑADO"
    assert float(linea["damaged_quantity"]) == 2.0
    assert linea["damage_notes"] == "Dos unidades con la caja aplastada"
    assert linea["identification_ok"] is True and linea["reference_ok"] is False
    assert float(linea["quantity_rejected"]) == 2.0

    # La observación sobrevive a la aceptación: no se consume al aceptar
    _aceptar(mundo, "ua", mundo.company_a, rec["id"])
    despues = _ver(mundo, "ua", mundo.company_a, rec["id"])["lines"][0]
    assert despues["physical_condition"] == "DAÑADO" and float(despues["damaged_quantity"]) == 2.0


def test_no_se_puede_observar_mas_dano_que_lo_recibido(mundo):
    prod = _producto(mundo, "ua", mundo.company_a, "P019-DMAX")
    oc = _orden_aprobada(mundo, "ua", mundo.company_a, "DMAX", prod)
    rec = _recepcion(mundo, "ua", mundo.company_a, "DMAX", oc["orden"], mundo.warehouse_a)
    r = _linea(mundo, "ua", mundo.company_a, rec["id"], oc["linea"], prod, 5, damaged_quantity=9)
    assert r.status_code == 422 and r.json()["code"] == "RECEIPT_DAMAGE_EXCEEDS_RECEIVED", r.text


def test_aceptado_mas_rechazado_no_puede_superar_lo_recibido(mundo):
    prod = _producto(mundo, "ua", mundo.company_a, "P019-SUMA")
    oc = _orden_aprobada(mundo, "ua", mundo.company_a, "SUMA", prod)
    rec = _recepcion(mundo, "ua", mundo.company_a, "SUMA", oc["orden"], mundo.warehouse_a)
    r = mundo.post(f"/purchasing/receipts/{rec['id']}/lines", "ua", mundo.company_a,
                   {"order_line_id": oc["linea"], "product_id": prod, "quantity_received": 10,
                    "quantity_accepted": 8, "quantity_rejected": 5})
    assert r.status_code == 422 and r.json()["code"] == "RECEIPT_QUANTITY_MISMATCH", r.text


# --------------------------------------------------------------------------- #
# Sobrante observado (etapa 8 es de 020; el hecho es de 019)
# --------------------------------------------------------------------------- #
def test_el_sobrante_se_registra_como_hecho_observado(mundo):
    """El DOCX manda registrar el sobrante; tratarlo es de la Spec 020.

    019 no lo impide —la mercancía llegó— pero tampoco lo deja pasar en
    silencio: lo congela en la línea.
    """
    prod = _producto(mundo, "ua", mundo.company_a, "P019-SOBRA")
    oc = _orden_aprobada(mundo, "ua", mundo.company_a, "SOBRA", prod, cantidad=10)
    rec = _recepcion(mundo, "ua", mundo.company_a, "SOBRA", oc["orden"], mundo.warehouse_a)
    linea = _linea(mundo, "ua", mundo.company_a, rec["id"], oc["linea"], prod, 13).json()
    assert float(linea["overage_base_quantity"]) == 3.0, "no registró el sobrante observado"

    normal = _producto(mundo, "ua", mundo.company_a, "P019-JUSTO")
    oc2 = _orden_aprobada(mundo, "ua", mundo.company_a, "JUSTO", normal, cantidad=10)
    rec2 = _recepcion(mundo, "ua", mundo.company_a, "JUSTO", oc2["orden"], mundo.warehouse_a)
    linea2 = _linea(mundo, "ua", mundo.company_a, rec2["id"], oc2["linea"], normal, 10).json()
    assert linea2["overage_base_quantity"] is None, "inventó un sobrante donde no lo hay"


# --------------------------------------------------------------------------- #
# Lote, serial y vencimiento: ya eran de 019 y se preservan
# --------------------------------------------------------------------------- #
def test_lote_serial_y_vencimiento_se_capturan_al_recibir(mundo):
    """`P23`: separada la mercancía del documento, ya nadie sabe qué serial vino en qué recepción."""
    prod = _producto(mundo, "ua", mundo.company_a, "P019-LOTE")
    oc = _orden_aprobada(mundo, "ua", mundo.company_a, "LOTE", prod)
    rec = _recepcion(mundo, "ua", mundo.company_a, "LOTE", oc["orden"], mundo.warehouse_a)
    vence = date.today() + timedelta(days=180)
    r = _linea(mundo, "ua", mundo.company_a, rec["id"], oc["linea"], prod, 3,
               lot_number="L-4491", expiry_date=vence.isoformat(), serials=["S-1", "S-2", "S-3"])
    assert r.status_code == 200, r.text
    linea = r.json()
    assert linea["lot_number"] == "L-4491" and linea["expiry_date"] == vence.isoformat()
    assert linea["serials"] == "S-1,S-2,S-3", f"los seriales no se normalizaron: {linea['serials']!r}"

    _aceptar(mundo, "ua", mundo.company_a, rec["id"])
    lotes = _sql(mundo, "SELECT lot_number, expiry_date FROM inventory_lots WHERE company_id = :c "
                        "AND lot_number = 'L-4491'", c=mundo.company_a)
    assert len(lotes) == 1 and str(lotes[0][1]) == vence.isoformat()
    seriales = _sql(mundo, "SELECT serial FROM product_serials WHERE company_id = :c AND product_id = :p "
                           "ORDER BY serial", c=mundo.company_a, p=prod)
    assert [s[0] for s in seriales] == ["S-1", "S-2", "S-3"], "no materializó los tres seriales"


# --------------------------------------------------------------------------- #
# Etapa 11 y fronteras
# --------------------------------------------------------------------------- #
def test_aceptar_emite_el_acta_y_no_invade_las_specs_vecinas(mundo):
    """Etapa 11, más las fronteras con 020, 021 y 022."""
    prod = _producto(mundo, "ua", mundo.company_a, "P019-ACTA")
    oc = _orden_aprobada(mundo, "ua", mundo.company_a, "ACTA", prod)
    rec = _recepcion(mundo, "ua", mundo.company_a, "ACTA", oc["orden"], mundo.warehouse_a)
    _linea(mundo, "ua", mundo.company_a, rec["id"], oc["linea"], prod, 6)
    antes_pick = len(mundo.filas("pick_lists", "id"))
    _aceptar(mundo, "ua", mundo.company_a, rec["id"])

    final = _ver(mundo, "ua", mundo.company_a, rec["id"])
    assert final["status"] == "ACCEPTED"
    assert final["record_issued_at"] is not None and final["record_issued_by"], "no emitió el acta"
    # Frontera con 022: ni ubicación ni tarea de colocación
    on_hand, location = _saldo(mundo, "ua", mundo.company_a, mundo.warehouse_a, prod)
    assert on_hand == 6.0 and location is None
    assert len(mundo.filas("pick_lists", "id")) == antes_pick, "creó preparación, que es de 031"
    # Frontera con 021: el estado del saldo sigue siendo el que el motor sabe escribir
    estados = _sql(mundo, "SELECT DISTINCT state FROM inventory_balances WHERE company_id = :c",
                   c=mundo.company_a)
    assert {e[0] for e in estados} <= {"RECIBIDO"}, \
        "la aceptación debe dejar la mercancía en RECIBIDO: liberar es de la Spec 021 (R-D0-10-4)"


def test_aceptar_dos_veces_no_duplica_el_movimiento(mundo):
    prod = _producto(mundo, "ua", mundo.company_a, "P019-DOBLE")
    oc = _orden_aprobada(mundo, "ua", mundo.company_a, "DOBLE", prod)
    rec = _recepcion(mundo, "ua", mundo.company_a, "DOBLE", oc["orden"], mundo.warehouse_a)
    _linea(mundo, "ua", mundo.company_a, rec["id"], oc["linea"], prod, 9)
    _aceptar(mundo, "ua", mundo.company_a, rec["id"])
    r = mundo.post(f"/purchasing/receipts/{rec['id']}/accept", "ua", mundo.company_a, {})
    assert r.status_code == 409, r.text
    movimientos = _sql(mundo, "SELECT count(*) FROM inventory_movements WHERE document_ref = :d",
                       d=f"RECEIPT:{rec['id']}")
    assert movimientos[0][0] == 1, "el segundo intento duplicó el asiento"
    on_hand, _ = _saldo(mundo, "ua", mundo.company_a, mundo.warehouse_a, prod)
    assert on_hand == 9.0


def test_una_recepcion_sin_lineas_no_se_acepta(mundo):
    prod = _producto(mundo, "ua", mundo.company_a, "P019-VACIA")
    oc = _orden_aprobada(mundo, "ua", mundo.company_a, "VACIA", prod)
    rec = _recepcion(mundo, "ua", mundo.company_a, "VACIA", oc["orden"], mundo.warehouse_a)
    for accion, cuerpo in (("confirm", {}), ("quality", {"quality_status": "APPROVED"})):
        assert mundo.post(f"/purchasing/receipts/{rec['id']}/{accion}", "ua", mundo.company_a,
                          cuerpo).status_code == 200
    r = mundo.post(f"/purchasing/receipts/{rec['id']}/accept", "ua", mundo.company_a, {})
    assert r.status_code == 409 and r.json()["code"] == "RECEIPT_EMPTY", r.text


def test_una_recepcion_aceptada_no_admite_lineas_nuevas(mundo):
    prod = _producto(mundo, "ua", mundo.company_a, "P019-CERR")
    oc = _orden_aprobada(mundo, "ua", mundo.company_a, "CERR", prod)
    rec = _recepcion(mundo, "ua", mundo.company_a, "CERR", oc["orden"], mundo.warehouse_a)
    _linea(mundo, "ua", mundo.company_a, rec["id"], oc["linea"], prod, 4)
    _aceptar(mundo, "ua", mundo.company_a, rec["id"])
    r = _linea(mundo, "ua", mundo.company_a, rec["id"], oc["linea"], prod, 1)
    assert r.status_code == 409 and r.json()["code"] == "RECEIPT_NOT_OPEN", r.text


# --------------------------------------------------------------------------- #
# Multiempresa (ARCH-MC-001)
# --------------------------------------------------------------------------- #
def test_usuario_ab_bajo_contexto_a_no_opera_la_recepcion_de_b(mundo):
    prod = _producto(mundo, "ub", mundo.company_b, "P019-AB")
    oc = _orden_aprobada(mundo, "ub", mundo.company_b, "AB", prod)
    rec = _recepcion(mundo, "ub", mundo.company_b, "AB", oc["orden"], mundo.warehouse_b)
    for accion, cuerpo in (("arrival", {}), ("inspection", {"order_match": True}),
                           ("confirm", {}), ("quality", {"quality_status": "APPROVED"}), ("accept", {})):
        r = mundo.post(f"/purchasing/receipts/{rec['id']}/{accion}", "uab", mundo.company_a, cuerpo)
        assert r.status_code == 404, f"{accion}: {r.status_code} {r.text}"
    assert mundo.get(f"/purchasing/receipts/{rec['id']}", "uab", mundo.company_a).status_code == 404
    assert mundo.get(f"/purchasing/receipts/{rec['id']}", "uab", mundo.company_b).status_code == 200


def test_cross_tenant_bloqueado(mundo):
    prod = _producto(mundo, "ua", mundo.company_a, "P019-XT")
    oc = _orden_aprobada(mundo, "ua", mundo.company_a, "XT", prod)
    rec = _recepcion(mundo, "ua", mundo.company_a, "XT", oc["orden"], mundo.warehouse_a)
    r = mundo.get(f"/purchasing/receipts/{rec['id']}", "uc", mundo.company_c, tenant="T2")
    assert r.status_code == 404, r.text


def test_no_se_recibe_contra_la_linea_de_orden_de_otra_recepcion(mundo):
    """La línea de la que se recibe tiene que ser de la orden de esta recepción."""
    prod_a = _producto(mundo, "ua", mundo.company_a, "P019-CRUCE-A")
    oc1 = _orden_aprobada(mundo, "ua", mundo.company_a, "CRUCE1", prod_a)
    oc2 = _orden_aprobada(mundo, "ua", mundo.company_a, "CRUCE2", prod_a)
    rec = _recepcion(mundo, "ua", mundo.company_a, "CRUCE", oc1["orden"], mundo.warehouse_a)
    r = _linea(mundo, "ua", mundo.company_a, rec["id"], oc2["linea"], prod_a, 1)
    assert r.status_code == 404 and r.json()["code"] == "PURCHASE_ORDER_LINE_NOT_FOUND", r.text


def test_el_almacen_de_otra_empresa_no_sirve(mundo):
    prod = _producto(mundo, "ua", mundo.company_a, "P019-WB")
    oc = _orden_aprobada(mundo, "ua", mundo.company_a, "WB", prod)
    r = mundo.post("/purchasing/receipts", "ua", mundo.company_a,
                   {"code": "REC-WB", "order_id": oc["orden"], "warehouse_id": mundo.warehouse_b})
    assert r.status_code == 404 and r.json()["code"] == "WAREHOUSE_NOT_FOUND", r.text


def test_el_cuerpo_no_elige_la_empresa(mundo):
    prod = _producto(mundo, "ua", mundo.company_a, "P019-BODY")
    oc = _orden_aprobada(mundo, "ua", mundo.company_a, "BODY", prod)
    rec = _recepcion(mundo, "ua", mundo.company_a, "BODY", oc["orden"], mundo.warehouse_a)
    r = mundo.post(f"/purchasing/receipts/{rec['id']}/arrival", "ua", mundo.company_a,
                   {"company_id": mundo.company_b})
    assert r.status_code == 422, r.text


# --------------------------------------------------------------------------- #
# Auditoría
# --------------------------------------------------------------------------- #
def test_la_auditoria_conserva_la_unidad_y_lo_observado(mundo):
    unidad = mundo.crear("/maestros/unidades", "ua", mundo.company_a,
                         {"code": "UND-AUD19", "name": "Unidad", "symbol": "u", "decimals": 0})
    prod = _producto(mundo, "ua", mundo.company_a, "P019-AUD", base_unit_id=unidad)
    caja = mundo.crear(f"/maestros/productos/{prod}/presentaciones", "ua", mundo.company_a,
                       {"code": "CAJA4-019", "name": "Caja de 4", "factor_to_base": "4",
                        "valid_from": (datetime.now(UTC) - timedelta(days=1)).isoformat()})
    oc = _orden_aprobada(mundo, "ua", mundo.company_a, "AUD", prod)
    rec = _recepcion(mundo, "ua", mundo.company_a, "AUD", oc["orden"], mundo.warehouse_a,
                     packages_declared=3)
    mundo.post(f"/purchasing/receipts/{rec['id']}/arrival", "ua", mundo.company_a, {"packages_received": 3})
    _linea(mundo, "ua", mundo.company_a, rec["id"], oc["linea"], prod, 5, presentation_id=caja,
           physical_condition="BUENO", identification_ok=True, reference_ok=True)
    _aceptar(mundo, "ua", mundo.company_a, rec["id"])

    acciones = [a[0] for a in _sql(
        mundo, "SELECT action FROM audit_events WHERE company_id = :c AND action LIKE 'RECEIPT%' "
               "ORDER BY created_at", c=mundo.company_a)]
    for esperada in ("RECEIPT_CREATED", "RECEIPT_ARRIVAL_CONFIRMED", "RECEIPT_LINE_ADDED", "RECEIPT_ACCEPTED"):
        assert esperada in acciones, f"falta {esperada} en la auditoría: {acciones}"

    linea_ev = _sql(mundo, "SELECT after FROM audit_events WHERE action = 'RECEIPT_LINE_ADDED' "
                           "AND company_id = :c ORDER BY created_at DESC LIMIT 1", c=mundo.company_a)
    after = linea_ev[0][0]
    for campo in ("quantity_received", "base_quantity_received", "presentation_id",
                  "conversion_factor_snapshot", "physical_condition", "identification_ok"):
        assert campo in after, f"la auditoría no conserva {campo}"
    # Se comparan como números: `to_base` cuantiza según los decimales que
    # declara la unidad, y la forma del texto no es lo que la prueba interroga.
    assert float(after["base_quantity_received"]) == 20.0
    assert float(after["conversion_factor_snapshot"]) == 4.0
