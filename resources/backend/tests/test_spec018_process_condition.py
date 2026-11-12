"""Spec 018 · §3 — la condición del proceso de recepción.

La fila «Estados recibido, disponible, pendiente, bloqueado» se cierra como
condición **derivada** del proceso: recepción, conteo, confirmación de
inventario (Spec 021) e incidencias vivas (Spec 020). Estas pruebas fijan la
precedencia, la recalculación al resolver una incidencia y que la condición no
toque el stock ni invente estados de inventario.

Multiempresa sobre PostgreSQL real, por la API, con el arnés `mundo`.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import text

pytest_plugins = ("tests.conftest_multicompany",)
PENDIENTE = "PENDIENTE_DE_VALIDACION"
BLOQUEADO = "BLOQUEADO_POR_INCIDENCIA"
RECIBIDO = "RECIBIDO"


# --------------------------------------------------------------------------- #
# Mundo: orden aprobada, recepción con línea y flujo hasta donde haga falta
# --------------------------------------------------------------------------- #
def _sql(mundo, sentencia: str, **params):
    db = mundo.factory()
    try:
        return db.execute(text(sentencia), params).fetchall()
    finally:
        db.close()


def _saldos(mundo, empresa, producto) -> dict[str, Decimal]:
    filas = _sql(mundo, "SELECT state, qty_on_hand FROM inventory_balances "
                        "WHERE company_id = :c AND product_id = :p", c=empresa, p=producto)
    return {f[0]: Decimal(str(f[1])) for f in filas}


def _recepcion(mundo, usuario, empresa, almacen, marca, *, cantidad=100, producto=None):
    """Orden aprobada, recepción y su línea recibida. Aún en `DRAFT`."""
    prov = mundo.crear("/maestros/terceros", usuario, empresa,
                       {"code": f"PROV-{marca}", "name": "Proveedor",
                        "person_type": "JURIDICA", "roles": ["PROVEEDOR"], "status": "ACTIVE"})
    prod = producto or mundo.crear("/maestros/catalogos/items", usuario, empresa,
                                   {"code": f"P-{marca}", "name": f"Producto {marca}",
                                    "item_type": "PRODUCT", "status": "ACTIVE"})
    orden = mundo.crear("/purchasing/orders", usuario, empresa,
                        {"code": f"OC-{marca}", "supplier_id": prov, "currency": "VED"})
    linea = mundo.crear(f"/purchasing/orders/{orden}/lines", usuario, empresa,
                        {"product_id": prod, "quantity_ordered": 1000, "unit_price": 1})
    for destino in ("SUBMITTED", "APPROVED"):
        r = mundo.post(f"/purchasing/orders/{orden}/transition", usuario, empresa,
                       {"target": destino})
        assert r.status_code == 200, r.text
    rec = mundo.crear("/purchasing/receipts", usuario, empresa,
                      {"code": f"RC-{marca}", "order_id": orden, "warehouse_id": almacen})
    rl = mundo.crear(f"/purchasing/receipts/{rec}/lines", usuario, empresa,
                     {"order_line_id": linea, "product_id": prod,
                      "quantity_received": cantidad, "quantity_accepted": cantidad,
                      "quantity_rejected": 0})
    return {"receipt": rec, "line": rl, "product": prod, "order": orden,
            "order_line": linea, "supplier": prov}


def _aceptar(mundo, usuario, empresa, receipt):
    """`DRAFT → CONFIRMED → QUALITY_PENDING → ACCEPTED`, como el proceso."""
    for accion, cuerpo in (("confirm", {}), ("quality", {}),
                           ("quality", {"quality_status": "APPROVED"}), ("accept", {})):
        r = mundo.post(f"/purchasing/receipts/{receipt}/{accion}", usuario, empresa, cuerpo)
        assert r.status_code == 200, f"{accion}: {r.text}"


def _contar(mundo, usuario, empresa, receipt, line, cantidad="100"):
    r = mundo.post(f"/purchasing/receipts/{receipt}/lines/{line}/conteo", usuario, empresa,
                   {"counted_base_quantity": cantidad, "difference_kinds": []})
    assert r.status_code == 200, r.text


def _confirmar(mundo, usuario, empresa, receipt, line, cantidad="100"):
    r = mundo.post(f"/purchasing/receipts/{receipt}/confirmacion-inventario", usuario, empresa,
                   {"decisions": [{"receipt_line_id": line, "target_state": "DISPONIBLE",
                                   "base_quantity": cantidad, "source_state": "RECIBIDO"}]})
    assert r.status_code == 200, r.text


def _condicion(mundo, usuario, empresa, receipt) -> dict:
    r = mundo.get(f"/purchasing/receipts/{receipt}", usuario, empresa)
    assert r.status_code == 200, r.text
    condicion = r.json()["process_condition"]
    assert condicion is not None, "una recepción del proceso normal debe tener condición"
    return condicion


def _incidencia(mundo, usuario, empresa, receipt, line, code, *, tipo="DANO", cantidad=3):
    r = mundo.post(f"/purchasing/receipts/{receipt}/incidencias", usuario, empresa,
                   {"code": code, "incident_type": tipo,
                    "receipt_line_id": line, "affected_base_quantity": cantidad})
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


def _resolver(mundo, usuario, empresa, receipt, incident):
    r = mundo.post(f"/purchasing/receipts/{receipt}/incidencias/{incident}/resolve", usuario,
                   empresa, {"resolution": "RECLAMO_PROVEEDOR",
                             "reason": "Reclamo registrado al proveedor."})
    assert r.status_code == 200, r.text


# --------------------------------------------------------------------------- #
# Caso 1 y caso 2: todavía no está validada
# --------------------------------------------------------------------------- #
def test_una_recepcion_recien_creada_esta_pendiente_de_validacion(mundo):
    m = _recepcion(mundo, "ua", mundo.company_a, mundo.warehouse_a, "PC1")
    condicion = _condicion(mundo, "ua", mundo.company_a, m["receipt"])
    assert condicion["code"] == PENDIENTE
    assert condicion["label"] == "Pendiente de validación"
    assert condicion["blocking_incidents"] == 0


def test_contar_sin_confirmar_sigue_pendiente_de_validacion(mundo):
    """El conteo no valida: la validación la cierra la confirmación de la 021."""
    m = _recepcion(mundo, "ua", mundo.company_a, mundo.warehouse_a, "PC2")
    _aceptar(mundo, "ua", mundo.company_a, m["receipt"])
    _contar(mundo, "uab", mundo.company_a, m["receipt"], m["line"])
    condicion = _condicion(mundo, "ua", mundo.company_a, m["receipt"])
    assert condicion["code"] == PENDIENTE


# --------------------------------------------------------------------------- #
# Caso 3 y caso 4: la incidencia bloquea y, al resolverse, se recalcula
# --------------------------------------------------------------------------- #
def test_una_incidencia_abierta_bloquea_y_la_confirmacion_lo_respeta(mundo):
    m = _recepcion(mundo, "ua", mundo.company_a, mundo.warehouse_a, "PC3")
    _aceptar(mundo, "ua", mundo.company_a, m["receipt"])
    _contar(mundo, "uab", mundo.company_a, m["receipt"], m["line"])
    inc = _incidencia(mundo, "ua", mundo.company_a, m["receipt"], m["line"], "INC-PC3")

    condicion = _condicion(mundo, "ua", mundo.company_a, m["receipt"])
    assert condicion["code"] == BLOQUEADO
    assert condicion["label"] == "Bloqueado por incidencia"
    assert condicion["blocking_incidents"] == 1
    assert [x["code"] for x in condicion["incidents"]] == ["INC-PC3"]
    assert condicion["reason"]

    r = mundo.post(f"/purchasing/receipts/{m['receipt']}/confirmacion-inventario", "ua",
                   mundo.company_a,
                   {"decisions": [{"receipt_line_id": m["line"], "target_state": "DISPONIBLE",
                                   "base_quantity": "100", "source_state": "RECIBIDO"}]})
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "INCIDENTS_UNRESOLVED"

    _resolver(mundo, "ua", mundo.company_a, m["receipt"], inc)
    condicion = _condicion(mundo, "ua", mundo.company_a, m["receipt"])
    assert condicion["code"] == PENDIENTE
    assert condicion["blocking_incidents"] == 0
    assert condicion["incidents"] == []

    _confirmar(mundo, "ua", mundo.company_a, m["receipt"], m["line"])
    assert _condicion(mundo, "ua", mundo.company_a, m["receipt"])["code"] == RECIBIDO


# --------------------------------------------------------------------------- #
# Caso 5: el proceso completo
# --------------------------------------------------------------------------- #
def test_el_proceso_completo_deja_la_recepcion_recibida(mundo):
    m = _recepcion(mundo, "ua", mundo.company_a, mundo.warehouse_a, "PC5")
    _aceptar(mundo, "ua", mundo.company_a, m["receipt"])
    _contar(mundo, "uab", mundo.company_a, m["receipt"], m["line"])
    _confirmar(mundo, "ua", mundo.company_a, m["receipt"], m["line"])
    condicion = _condicion(mundo, "ua", mundo.company_a, m["receipt"])
    assert condicion["code"] == RECIBIDO
    assert condicion["label"] == "Recibido"


# --------------------------------------------------------------------------- #
# Precedencia determinista
# --------------------------------------------------------------------------- #
def test_el_bloqueo_prevalece_sobre_recibido_y_se_recalcula_al_resolver(mundo):
    """Una incidencia viva manda sobre cualquier otro estado del proceso."""
    m = _recepcion(mundo, "ua", mundo.company_a, mundo.warehouse_a, "PC6")
    _aceptar(mundo, "ua", mundo.company_a, m["receipt"])
    _contar(mundo, "uab", mundo.company_a, m["receipt"], m["line"])
    _confirmar(mundo, "ua", mundo.company_a, m["receipt"], m["line"])
    assert _condicion(mundo, "ua", mundo.company_a, m["receipt"])["code"] == RECIBIDO

    inc = _incidencia(mundo, "ua", mundo.company_a, m["receipt"], m["line"], "INC-PC6")
    assert _condicion(mundo, "ua", mundo.company_a, m["receipt"])["code"] == BLOQUEADO

    _resolver(mundo, "ua", mundo.company_a, m["receipt"], inc)
    assert _condicion(mundo, "ua", mundo.company_a, m["receipt"])["code"] == RECIBIDO


def test_una_sola_condicion_principal_por_recepcion(mundo):
    m = _recepcion(mundo, "ua", mundo.company_a, mundo.warehouse_a, "PC7")
    _aceptar(mundo, "ua", mundo.company_a, m["receipt"])
    _incidencia(mundo, "ua", mundo.company_a, m["receipt"], m["line"], "INC-PC7")
    condicion = _condicion(mundo, "ua", mundo.company_a, m["receipt"])
    assert condicion["code"] in {RECIBIDO, PENDIENTE, BLOQUEADO}
    assert condicion["code"] == BLOQUEADO


# --------------------------------------------------------------------------- #
# La condición no es inventario
# --------------------------------------------------------------------------- #
def test_la_condicion_no_mueve_el_stock_ni_inventa_estados(mundo):
    m = _recepcion(mundo, "ua", mundo.company_a, mundo.warehouse_a, "PC8")
    _aceptar(mundo, "ua", mundo.company_a, m["receipt"])
    antes = _saldos(mundo, mundo.company_a, m["product"])
    assert antes == {"RECIBIDO": Decimal("100")}, antes

    inc = _incidencia(mundo, "ua", mundo.company_a, m["receipt"], m["line"], "INC-PC8")
    assert _condicion(mundo, "ua", mundo.company_a, m["receipt"])["code"] == BLOQUEADO
    assert _saldos(mundo, mundo.company_a, m["product"]) == antes

    _resolver(mundo, "ua", mundo.company_a, m["receipt"], inc)
    assert _condicion(mundo, "ua", mundo.company_a, m["receipt"])["code"] == PENDIENTE
    assert _saldos(mundo, mundo.company_a, m["product"]) == antes

    estados = {fila[0] for fila in _sql(
        mundo, "SELECT DISTINCT state FROM inventory_balances WHERE company_id = :c AND product_id = :p",
        c=mundo.company_a, p=m["product"])}
    assert not {"PENDIENTE_DE_VALIDACION", "BLOQUEADO_POR_INCIDENCIA"} & estados, estados


# --------------------------------------------------------------------------- #
# Superficies y aislamiento
# --------------------------------------------------------------------------- #
def test_el_expediente_de_importacion_muestra_la_misma_condicion(mundo):
    from app.modules.imports.models import ImportFile

    m = _recepcion(mundo, "ua", mundo.company_a, mundo.warehouse_a, "PC9")
    _aceptar(mundo, "ua", mundo.company_a, m["receipt"])
    _incidencia(mundo, "ua", mundo.company_a, m["receipt"], m["line"], "INC-PC9")

    db = mundo.factory()
    try:
        file = ImportFile(company_id=mundo.company_a, supplier_id=m["supplier"],
                          order_id=m["order"], currency="VED", status="DISPATCHED",
                          code="IMP-PC9")
        db.add(file)
        db.commit()
        file_id = str(file.id)
    finally:
        db.close()

    detalle = mundo.get(f"/importaciones/{file_id}", "ua", mundo.company_a)
    assert detalle.status_code == 200, detalle.text
    fila = next(r for r in detalle.json()["logistics"]["receipts"] if r["id"] == m["receipt"])

    propia = _condicion(mundo, "ua", mundo.company_a, m["receipt"])
    assert fila["process_condition"] == propia, "el expediente recalculó una versión distinta"
    assert fila["process_condition"]["code"] == BLOQUEADO


def test_el_listado_trae_la_condicion_de_cada_recepcion(mundo):
    m = _recepcion(mundo, "ua", mundo.company_a, mundo.warehouse_a, "PC10")
    r = mundo.get("/purchasing/receipts", "ua", mundo.company_a)
    assert r.status_code == 200, r.text
    fila = next(x for x in r.json()["items"] if x["id"] == m["receipt"])
    assert fila["process_condition"]["code"] == PENDIENTE
    assert fila["process_condition"]["label"] == "Pendiente de validación"


def test_otra_empresa_no_ve_ni_consulta_la_recepcion(mundo):
    m = _recepcion(mundo, "ua", mundo.company_a, mundo.warehouse_a, "PC11")
    r = mundo.get(f"/purchasing/receipts/{m['receipt']}", "ub", mundo.company_b)
    assert r.status_code == 404, r.text
    listado = mundo.get("/purchasing/receipts", "ub", mundo.company_b)
    assert listado.status_code == 200
    assert all(x["id"] != m["receipt"] for x in listado.json()["items"])


def test_una_recepcion_anulada_no_finge_una_condicion_del_proceso(mundo):
    m = _recepcion(mundo, "ua", mundo.company_a, mundo.warehouse_a, "PC12")
    r = mundo.post(f"/purchasing/receipts/{m['receipt']}/cancel", "ua", mundo.company_a,
                   {"reason": "Documento emitido por error."})
    assert r.status_code == 200, r.text
    r = mundo.get(f"/purchasing/receipts/{m['receipt']}", "ua", mundo.company_a)
    assert r.status_code == 200
    assert r.json()["process_condition"] is None
