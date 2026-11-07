"""Spec 021 · confirmación y conciliación del inventario recibido.

La regla que da sentido a la Spec: **recibir no es tener disponible**. Hasta
ahora aceptar una recepción ponía la mercancía a la venta sin que nadie la
hubiera contado; `R-D0-10-4` lo prohíbe y aquí se cierra.

Multiempresa sobre PostgreSQL real, por la API, con el arnés `mundo`.
"""

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


def _recepcion_aceptada(mundo, usuario, empresa, almacen, marca, *, cantidad=100,
                        producto=None, presentacion=None, tecleado=None):
    """Deja una recepción `ACCEPTED` con su mercancía en `RECIBIDO`."""
    prov = mundo.crear("/maestros/terceros", usuario, empresa,
                       {"code": f"PROV-{marca}", "name": "Proveedor", "person_type": "JURIDICA",
                        "roles": ["PROVEEDOR"], "status": "ACTIVE"})
    prod = producto or _producto(mundo, usuario, empresa, f"P-{marca}")
    orden = mundo.crear("/purchasing/orders", usuario, empresa,
                        {"code": f"OC-{marca}", "supplier_id": prov, "currency": "VED"})
    linea = mundo.crear(f"/purchasing/orders/{orden}/lines", usuario, empresa,
                        {"product_id": prod, "quantity_ordered": 1000, "unit_price": 1})
    for destino in ("SUBMITTED", "APPROVED"):
        r = mundo.post(f"/purchasing/orders/{orden}/transition", usuario, empresa, {"target": destino})
        assert r.status_code == 200, r.text
    rec = mundo.crear("/purchasing/receipts", usuario, empresa,
                      {"code": f"RC-{marca}", "order_id": orden, "warehouse_id": almacen})
    cuerpo = {"order_line_id": linea, "product_id": prod,
              "quantity_received": tecleado if tecleado is not None else cantidad,
              "quantity_accepted": tecleado if tecleado is not None else cantidad,
              "quantity_rejected": 0}
    if presentacion:
        cuerpo["presentation_id"] = presentacion
    rl = mundo.crear(f"/purchasing/receipts/{rec}/lines", usuario, empresa, cuerpo)
    for accion, cuerpo in (("confirm", {}), ("quality", {}), ("quality", {"quality_status": "APPROVED"}), ("accept", {})):
        r = mundo.post(f"/purchasing/receipts/{rec}/{accion}", usuario, empresa, cuerpo)
        assert r.status_code == 200, f"{accion}: {r.text}"
    return {"receipt": rec, "line": rl, "product": prod, "order": orden, "order_line": linea}


# ------------------------------------------------------- recibir ≠ disponible
def test_aceptar_una_recepcion_no_pone_la_mercancia_a_la_venta(mundo):
    """El corazón de la Spec: `R-D0-10-4` en su forma más literal."""
    m = _recepcion_aceptada(mundo, "ua", mundo.company_a, mundo.warehouse_a, "NOSALE")
    saldos = _saldos(mundo, mundo.company_a, m["product"])
    assert saldos == {"RECIBIDO": Decimal("100")}, saldos

    r = mundo.get(f"/inventory/balances?product_id={m['product']}&state=DISPONIBLE",
                  "ua", mundo.company_a)
    assert r.status_code == 200
    assert r.json()["items"] == [], "la mercancía recién recibida no puede ofrecerse"


def test_el_movimiento_de_aceptacion_declara_su_destino(mundo):
    m = _recepcion_aceptada(mundo, "ua", mundo.company_a, mundo.warehouse_a, "PROV")
    filas = _sql(mundo, "SELECT source_state, target_state FROM inventory_movements "
                        "WHERE product_id = :p", p=m["product"])
    assert [(f[0], f[1]) for f in filas] == [(None, "RECIBIDO")]


# ------------------------------------------------------------------ el conteo
def test_el_conteo_se_registra_en_unidad_base_y_con_sus_diferencias(mundo):
    m = _recepcion_aceptada(mundo, "ua", mundo.company_a, mundo.warehouse_a, "CONT")
    r = mundo.post(f"/purchasing/receipts/{m['receipt']}/lines/{m['line']}/conteo",
                   "ua", mundo.company_a,
                   {"counted_base_quantity": "97", "difference_kinds": ["CANTIDAD", "REFERENCIA"]})
    assert r.status_code == 200, r.text

    concilia = mundo.get(f"/purchasing/receipts/{m['receipt']}/conciliacion",
                         "ua", mundo.company_a).json()
    item = concilia["items"][0]
    assert item["counted_base_quantity"] == "97.000000"
    assert item["matches_physical"] is False
    assert sorted(item["difference_kinds"]) == ["CANTIDAD", "REFERENCIA"]


def test_una_diferencia_inventada_no_entra(mundo):
    m = _recepcion_aceptada(mundo, "ua", mundo.company_a, mundo.warehouse_a, "DIFX")
    r = mundo.post(f"/purchasing/receipts/{m['receipt']}/lines/{m['line']}/conteo",
                   "ua", mundo.company_a,
                   {"counted_base_quantity": "100", "difference_kinds": ["COLOR"]})
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "COUNT_DIFFERENCE_KIND_UNKNOWN"


def test_sin_conteo_la_conciliacion_no_declara_listo(mundo):
    m = _recepcion_aceptada(mundo, "ua", mundo.company_a, mundo.warehouse_a, "SINCONT")
    concilia = mundo.get(f"/purchasing/receipts/{m['receipt']}/conciliacion",
                         "ua", mundo.company_a).json()
    assert concilia["ready_for_confirmation"] is False
    assert concilia["lines_pending_count"] == [m["line"]]


def test_el_conteo_de_una_linea_ajena_no_se_acepta(mundo):
    a = _recepcion_aceptada(mundo, "ua", mundo.company_a, mundo.warehouse_a, "OWNA")
    b = _recepcion_aceptada(mundo, "ua", mundo.company_a, mundo.warehouse_a, "OWNB")
    r = mundo.post(f"/purchasing/receipts/{a['receipt']}/lines/{b['line']}/conteo",
                   "ua", mundo.company_a, {"counted_base_quantity": "10"})
    assert r.status_code == 404, r.text


# ------------------------------------------------- las cuatro transiciones
def test_recibido_a_disponible_libera_la_mercancia(mundo):
    m = _recepcion_aceptada(mundo, "ua", mundo.company_a, mundo.warehouse_a, "REL")
    mundo.post(f"/purchasing/receipts/{m['receipt']}/lines/{m['line']}/conteo",
               "ua", mundo.company_a, {"counted_base_quantity": "100"})
    r = mundo.post(f"/purchasing/receipts/{m['receipt']}/confirmacion-inventario", "ua", mundo.company_a,
                   {"decisions": [{"receipt_line_id": m["line"], "target_state": "DISPONIBLE",
                                   "base_quantity": "100"}]})
    assert r.status_code == 200, r.text
    assert r.json()["confirmation_status"] == "CONFIRMADA"
    assert _saldos(mundo, mundo.company_a, m["product"]) == {
        "RECIBIDO": Decimal("0"), "DISPONIBLE": Decimal("100")}


def test_recibido_a_rechazado_no_deja_nada_disponible(mundo):
    m = _recepcion_aceptada(mundo, "ua", mundo.company_a, mundo.warehouse_a, "REJ")
    mundo.post(f"/purchasing/receipts/{m['receipt']}/lines/{m['line']}/conteo",
               "ua", mundo.company_a, {"counted_base_quantity": "100"})
    r = mundo.post(f"/purchasing/receipts/{m['receipt']}/confirmacion-inventario", "ua", mundo.company_a,
                   {"decisions": [{"receipt_line_id": m["line"], "target_state": "RECHAZADO",
                                   "base_quantity": "100", "reason": "No apto tras el conteo"}]})
    assert r.status_code == 200, r.text
    saldos = _saldos(mundo, mundo.company_a, m["product"])
    assert saldos["RECHAZADO"] == Decimal("100")
    assert saldos.get("DISPONIBLE", Decimal(0)) == Decimal(0)


def test_el_resultado_mixto_reparte_y_conserva_el_fisico(mundo):
    """Etapa 9: «diferenciar inventario». Noventa liberadas y diez rechazadas."""
    m = _recepcion_aceptada(mundo, "ua", mundo.company_a, mundo.warehouse_a, "MIX")
    mundo.post(f"/purchasing/receipts/{m['receipt']}/lines/{m['line']}/conteo",
               "ua", mundo.company_a, {"counted_base_quantity": "100"})
    r = mundo.post(f"/purchasing/receipts/{m['receipt']}/confirmacion-inventario", "ua", mundo.company_a,
                   {"decisions": [
                       {"receipt_line_id": m["line"], "target_state": "DISPONIBLE",
                        "base_quantity": "90"},
                       {"receipt_line_id": m["line"], "target_state": "RECHAZADO",
                        "base_quantity": "10", "reason": "Diez unidades no aptas"}]})
    assert r.status_code == 200, r.text
    saldos = _saldos(mundo, mundo.company_a, m["product"])
    assert saldos["DISPONIBLE"] == Decimal("90")
    assert saldos["RECHAZADO"] == Decimal("10")
    assert sum(saldos.values()) == Decimal("100"), "la confirmación creó o destruyó existencia"


def test_no_se_puede_confirmar_mas_de_lo_recibido(mundo):
    m = _recepcion_aceptada(mundo, "ua", mundo.company_a, mundo.warehouse_a, "EXC")
    mundo.post(f"/purchasing/receipts/{m['receipt']}/lines/{m['line']}/conteo",
               "ua", mundo.company_a, {"counted_base_quantity": "100"})
    r = mundo.post(f"/purchasing/receipts/{m['receipt']}/confirmacion-inventario", "ua", mundo.company_a,
                   {"decisions": [{"receipt_line_id": m["line"], "target_state": "DISPONIBLE",
                                   "base_quantity": "101"}]})
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "CONFIRMED_EXCEEDS_RECEIVED"
    assert _saldos(mundo, mundo.company_a, m["product"]) == {"RECIBIDO": Decimal("100")}


def test_un_destino_fuera_de_las_cuatro_transiciones_se_rechaza(mundo):
    """`R-D0-10-7` por partida doble: la 021 lo filtra y la 023 lo volvería a filtrar."""
    m = _recepcion_aceptada(mundo, "ua", mundo.company_a, mundo.warehouse_a, "DENY")
    mundo.post(f"/purchasing/receipts/{m['receipt']}/lines/{m['line']}/conteo",
               "ua", mundo.company_a, {"counted_base_quantity": "100"})
    r = mundo.post(f"/purchasing/receipts/{m['receipt']}/confirmacion-inventario", "ua", mundo.company_a,
                   {"decisions": [{"receipt_line_id": m["line"], "target_state": "DESECHO",
                                   "base_quantity": "10", "reason": "x"}]})
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "CONFIRMATION_TARGET_UNKNOWN"
    assert _saldos(mundo, mundo.company_a, m["product"]) == {"RECIBIDO": Decimal("100")}


# ----------------------------------------------------------- la caja por doce
def test_la_caja_por_doce_se_confirma_en_base(mundo):
    unidad = mundo.crear("/maestros/unidades", "ua", mundo.company_a,
                         {"code": "UND-021", "name": "Unidad", "symbol": "u", "decimals": 0})
    prod = _producto(mundo, "ua", mundo.company_a, "P021-CAJA", base_unit_id=unidad)
    caja = mundo.crear(f"/maestros/productos/{prod}/presentaciones", "ua", mundo.company_a,
                       {"code": "CAJA12-021", "name": "Caja de 12", "factor_to_base": "12",
                        "valid_from": (datetime.now(UTC) - timedelta(days=1)).isoformat()})
    m = _recepcion_aceptada(mundo, "ua", mundo.company_a, mundo.warehouse_a, "CAJA",
                            producto=prod, presentacion=caja, tecleado=2)

    assert _saldos(mundo, mundo.company_a, prod) == {"RECIBIDO": Decimal("24")}, "dos cajas son 24"
    mundo.post(f"/purchasing/receipts/{m['receipt']}/lines/{m['line']}/conteo",
               "ua", mundo.company_a, {"counted_base_quantity": "24"})
    r = mundo.post(f"/purchasing/receipts/{m['receipt']}/confirmacion-inventario", "ua", mundo.company_a,
                   {"decisions": [{"receipt_line_id": m["line"], "target_state": "DISPONIBLE",
                                   "base_quantity": "24"}]})
    assert r.status_code == 200, r.text
    assert _saldos(mundo, mundo.company_a, prod)["DISPONIBLE"] == Decimal("24")


# ------------------------------------------------------------- las incidencias
def test_una_incidencia_abierta_impide_confirmar(mundo):
    m = _recepcion_aceptada(mundo, "ua", mundo.company_a, mundo.warehouse_a, "INCOPEN")
    mundo.post(f"/purchasing/receipts/{m['receipt']}/lines/{m['line']}/conteo",
               "ua", mundo.company_a, {"counted_base_quantity": "95"})
    inc = mundo.post(f"/purchasing/receipts/{m['receipt']}/incidencias", "ua", mundo.company_a,
                     {"code": f"INC-{m['receipt'][:8]}", "incident_type": "FALTANTE",
                      "receipt_line_id": m["line"], "affected_base_quantity": "5",
                      "description": "Faltan cinco"})
    assert inc.status_code in (200, 201), inc.text

    r = mundo.post(f"/purchasing/receipts/{m['receipt']}/confirmacion-inventario", "ua", mundo.company_a,
                   {"decisions": [{"receipt_line_id": m["line"], "target_state": "DISPONIBLE",
                                   "base_quantity": "95"}]})
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "INCIDENTS_UNRESOLVED"
    assert _saldos(mundo, mundo.company_a, m["product"]) == {"RECIBIDO": Decimal("100")}


def test_el_camino_feliz_no_necesita_ninguna_incidencia(mundo):
    m = _recepcion_aceptada(mundo, "ua", mundo.company_a, mundo.warehouse_a, "FELIZ")
    mundo.post(f"/purchasing/receipts/{m['receipt']}/lines/{m['line']}/conteo",
               "ua", mundo.company_a, {"counted_base_quantity": "100"})
    r = mundo.post(f"/purchasing/receipts/{m['receipt']}/confirmacion-inventario", "ua", mundo.company_a,
                   {"decisions": [{"receipt_line_id": m["line"], "target_state": "DISPONIBLE",
                                   "base_quantity": "100"}]})
    assert r.status_code == 200, r.text
    incidencias = mundo.get(f"/purchasing/receipts/{m['receipt']}/incidencias",
                            "ua", mundo.company_a).json()
    assert incidencias["total"] == 0, "el camino feliz no fabrica excepciones"


# ---------------------------------------------------------------- idempotencia
def test_confirmar_dos_veces_no_duplica_nada(mundo):
    m = _recepcion_aceptada(mundo, "ua", mundo.company_a, mundo.warehouse_a, "IDEM")
    mundo.post(f"/purchasing/receipts/{m['receipt']}/lines/{m['line']}/conteo",
               "ua", mundo.company_a, {"counted_base_quantity": "100"})
    cuerpo = {"decisions": [{"receipt_line_id": m["line"], "target_state": "DISPONIBLE",
                             "base_quantity": "100"}]}
    assert mundo.post(f"/purchasing/receipts/{m['receipt']}/confirmacion-inventario",
                      "ua", mundo.company_a, cuerpo).status_code == 200
    segunda = mundo.post(f"/purchasing/receipts/{m['receipt']}/confirmacion-inventario",
                         "ua", mundo.company_a, cuerpo)
    assert segunda.status_code == 409, segunda.text
    assert segunda.json()["code"] == "ALREADY_CONFIRMED"

    assert _saldos(mundo, mundo.company_a, m["product"])["DISPONIBLE"] == Decimal("100")
    filas = mundo.get(f"/purchasing/receipts/{m['receipt']}/confirmacion-inventario",
                      "ua", mundo.company_a).json()
    assert filas["total"] == 1, "la segunda llamada creó otro registro"


# --------------------------------------------------------------- la frontera
def test_confirmar_no_ubica_nada(mundo):
    """Frontera con la Spec 022: confirmar no es colocar."""
    m = _recepcion_aceptada(mundo, "ua", mundo.company_a, mundo.warehouse_a, "NOLOC")
    mundo.post(f"/purchasing/receipts/{m['receipt']}/lines/{m['line']}/conteo",
               "ua", mundo.company_a, {"counted_base_quantity": "100"})
    mundo.post(f"/purchasing/receipts/{m['receipt']}/confirmacion-inventario", "ua", mundo.company_a,
               {"decisions": [{"receipt_line_id": m["line"], "target_state": "DISPONIBLE",
                               "base_quantity": "100"}]})
    ubicaciones = _sql(mundo, "SELECT DISTINCT location_id FROM inventory_balances "
                              "WHERE company_id = :c AND product_id = :p",
                       c=mundo.company_a, p=m["product"])
    assert [u[0] for u in ubicaciones] == [None], "la confirmación asignó ubicación"


def test_una_recepcion_sin_aceptar_no_se_confirma(mundo):
    prov = mundo.crear("/maestros/terceros", "ua", mundo.company_a,
                       {"code": "PROV-NOACC", "name": "P", "person_type": "JURIDICA",
                        "roles": ["PROVEEDOR"], "status": "ACTIVE"})
    prod = _producto(mundo, "ua", mundo.company_a, "P-NOACC")
    orden = mundo.crear("/purchasing/orders", "ua", mundo.company_a,
                        {"code": "OC-NOACC", "supplier_id": prov, "currency": "VED"})
    linea = mundo.crear(f"/purchasing/orders/{orden}/lines", "ua", mundo.company_a,
                        {"product_id": prod, "quantity_ordered": 10, "unit_price": 1})
    for destino in ("SUBMITTED", "APPROVED"):
        assert mundo.post(f"/purchasing/orders/{orden}/transition", "ua", mundo.company_a,
                          {"target": destino}).status_code == 200
    rec = mundo.crear("/purchasing/receipts", "ua", mundo.company_a,
                      {"code": "RC-NOACC", "order_id": orden, "warehouse_id": mundo.warehouse_a})
    rl = mundo.crear(f"/purchasing/receipts/{rec}/lines", "ua", mundo.company_a,
                     {"order_line_id": linea, "product_id": prod, "quantity_received": 10,
                      "quantity_accepted": 10, "quantity_rejected": 0})
    r = mundo.post(f"/purchasing/receipts/{rec}/confirmacion-inventario", "ua", mundo.company_a,
                   {"decisions": [{"receipt_line_id": rl, "target_state": "DISPONIBLE",
                                   "base_quantity": "10"}]})
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "RECEIPT_NOT_ACCEPTED"


# ---------------------------------------------------------------- multiempresa
def test_la_empresa_ajena_no_ve_ni_confirma_la_recepcion(mundo):
    m = _recepcion_aceptada(mundo, "ua", mundo.company_a, mundo.warehouse_a, "MCA")
    for ruta, metodo in ((f"/purchasing/receipts/{m['receipt']}/conciliacion", "get"),
                         (f"/purchasing/receipts/{m['receipt']}/confirmacion-inventario", "get")):
        r = getattr(mundo, metodo)(ruta, "ub", mundo.company_b)
        assert r.status_code == 404, f"{ruta}: {r.status_code}"

    r = mundo.post(f"/purchasing/receipts/{m['receipt']}/confirmacion-inventario", "ub", mundo.company_b,
                   {"decisions": [{"receipt_line_id": m["line"], "target_state": "DISPONIBLE",
                                   "base_quantity": "100"}]})
    assert r.status_code == 404, r.text
    assert _saldos(mundo, mundo.company_a, m["product"]) == {"RECIBIDO": Decimal("100")}


def test_el_usuario_ab_fuera_de_contexto_no_confirma(mundo):
    """Tiene acceso a A y a B; en contexto A, la recepción de A sí, la de B no."""
    a = _recepcion_aceptada(mundo, "ua", mundo.company_a, mundo.warehouse_a, "ABA")
    b = _recepcion_aceptada(mundo, "ub", mundo.company_b, mundo.warehouse_b, "ABB")

    r = mundo.get(f"/purchasing/receipts/{b['receipt']}/conciliacion", "uab", mundo.company_a)
    assert r.status_code == 404, "en contexto A vio una recepción de B"
    r = mundo.get(f"/purchasing/receipts/{b['receipt']}/conciliacion", "uab", mundo.company_b)
    assert r.status_code == 200, r.text
    r = mundo.get(f"/purchasing/receipts/{a['receipt']}/conciliacion", "uab", mundo.company_a)
    assert r.status_code == 200, r.text


def test_el_otro_tenant_no_alcanza_la_recepcion(mundo):
    m = _recepcion_aceptada(mundo, "ua", mundo.company_a, mundo.warehouse_a, "TEN")
    r = mundo.get(f"/purchasing/receipts/{m['receipt']}/conciliacion", "uc", mundo.company_c,
                  tenant="T2")
    assert r.status_code == 404, r.text


def test_iso_com_05_la_incidencia_ajena_no_se_enlaza(mundo):
    """ISO-COM-05: La incidencia de otra recepción/empresa no puede enlazarse."""
    import uuid

    m = _recepcion_aceptada(mundo, "ua", mundo.company_a, mundo.warehouse_a, "ISOCOM5")
    mundo.post(f"/purchasing/receipts/{m['receipt']}/lines/{m['line']}/conteo", "ua",
               mundo.company_a, {"counted_base_quantity": "100"})

    mb = _recepcion_aceptada(mundo, "ub", mundo.company_b, mundo.warehouse_b, "ISOCOM5B")
    ib = mundo.post(f"/purchasing/receipts/{mb['receipt']}/incidencias", "ub", mundo.company_b,
                    {"code": "INC-ISO-B", "incident_type": "DIFERENCIA_DOCUMENTAL",
                     "description": "Ajena"})
    assert ib.status_code in (200, 201), ib.text
    incidente_b = ib.json()["id"]

    m2 = _recepcion_aceptada(mundo, "ua", mundo.company_a, mundo.warehouse_a, "ISOCOM5X")
    ia = mundo.post(f"/purchasing/receipts/{m2['receipt']}/incidencias", "ua", mundo.company_a,
                    {"code": "INC-ISO-A2", "incident_type": "DIFERENCIA_DOCUMENTAL",
                     "description": "Ajena"})
    assert ia.status_code in (200, 201), ia.text
    incidente_a2 = ia.json()["id"]

    for incident_id in (incidente_b, incidente_a2, str(uuid.uuid4())):
        r = mundo.post(f"/purchasing/receipts/{m['receipt']}/confirmacion-inventario", "ua",
                       mundo.company_a, {
                           "decisions": [{"receipt_line_id": m["line"], "target_state": "DISPONIBLE",
                                          "base_quantity": "100", "incident_id": incident_id}]
                       })
        assert r.status_code == 404, r.text
        assert r.json()["code"] == "RECEIPT_INCIDENT_NOT_FOUND"
        assert _saldos(mundo, mundo.company_a, m["product"]) == {"RECIBIDO": Decimal("100")}
