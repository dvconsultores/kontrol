"""Incidencias de recepción — Spec 020.

La etapa 8 del proceso manda **registrar** las diferencias, la 9 generar su
evidencia y la 10 escalarlas a Compras. Hasta ahora una recepción con diez
unidades dañadas solo sabía decir `quantity_rejected = 10`: sin tipo, sin
responsable, sin evidencia y sin tratamiento.

Estas pruebas protegen tres cosas. Que la incidencia **no repita** el hecho
físico que la Spec 019 ya capturó. Que no se pueda comprometer más mercancía de
la que llegó. Y que registrar el tratamiento no sea ejecutarlo: confirmar el
inventario sigue siendo de la Spec 021.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import text

pytest_plugins = ("tests.conftest_multicompany",)


# --------------------------------------------------------------------------- #
# Mundo: orden aprobada, recepción y línea recibida
# --------------------------------------------------------------------------- #
def _producto(mundo, usuario, empresa, code, base_unit_id=None):
    cuerpo = {"code": code, "name": f"Producto {code}", "item_type": "PRODUCT"}
    if base_unit_id:
        cuerpo["base_unit_id"] = base_unit_id
    return mundo.crear("/maestros/catalogos/items", usuario, empresa, cuerpo)


def _orden(mundo, usuario, empresa, marca, producto, cantidad=100):
    prov = mundo.crear("/maestros/terceros", usuario, empresa,
                       {"code": f"PRV-{marca}", "name": "Proveedor", "roles": ["PROVEEDOR"]})
    oc = mundo.crear("/purchasing/orders", usuario, empresa,
                     {"code": f"OC-{marca}", "supplier_id": prov, "currency": "VED"})
    r = mundo.post(f"/purchasing/orders/{oc}/lines", usuario, empresa,
                   {"product_id": producto, "quantity_ordered": cantidad, "unit_price": 5})
    assert r.status_code == 200, r.text
    linea_oc = r.json()["id"]
    for destino in ("SUBMITTED", "APPROVED"):
        assert mundo.post(f"/purchasing/orders/{oc}/transition", usuario, empresa,
                          {"target": destino}).status_code == 200
    return {"orden": oc, "linea_oc": linea_oc}


def _recepcion_con_linea(mundo, usuario, empresa, almacen, marca, producto=None,
                         recibido=20, presentation_id=None, cantidad_orden=100, **linea_extra):
    prod = producto or _producto(mundo, usuario, empresa, f"P020-{marca}")
    oc = _orden(mundo, usuario, empresa, marca, prod, cantidad=cantidad_orden)
    rec = mundo.post("/purchasing/receipts", usuario, empresa,
                     {"code": f"REC-{marca}", "order_id": oc["orden"], "warehouse_id": almacen})
    assert rec.status_code == 200, rec.text
    rec = rec.json()
    cuerpo = {"order_line_id": oc["linea_oc"], "product_id": prod,
              "quantity_received": recibido, "quantity_accepted": recibido, "quantity_rejected": 0}
    if presentation_id:
        cuerpo["presentation_id"] = presentation_id
    cuerpo.update(linea_extra)
    r = mundo.post(f"/purchasing/receipts/{rec['id']}/lines", usuario, empresa, cuerpo)
    assert r.status_code == 200, r.text
    return {"recepcion": rec["id"], "linea": r.json()["id"], "producto": prod, **oc}


def _incidencia(mundo, usuario, empresa, recepcion, **cuerpo):
    return mundo.post(f"/purchasing/receipts/{recepcion}/incidencias", usuario, empresa, cuerpo)


def _sql(mundo, sentencia, **params):
    db = mundo.factory()
    try:
        out = db.execute(text(sentencia), params).fetchall()
        db.commit()
        return out
    finally:
        db.close()


def _politica_de_ajuste(mundo, usuario, empresa, umbral=0.0):
    """Política 045 para `RECEIPT_INCIDENT`, resuelta por ADMIN."""
    pid = mundo.crear("/approvals/policies", usuario, empresa, {
        "process_type": "RECEIPT_INCIDENT", "code": "AJ-020", "name": "Ajuste de incidencia",
        "requires_segregation": False, "allow_self_approval": True})
    regla = mundo.crear(f"/approvals/policies/{pid}/rules", usuario, empresa, {
        "name": "Todo ajuste",
        "conditions": [{"field": "amount_base", "operator": "gt", "value": umbral}],
        "condition_fields": ["amount_base", "amount", "currency"]})
    assert mundo.post(f"/approvals/policies/{pid}/rules/{regla}/levels", usuario, empresa,
                      {"level_order": 1, "resolver_type": "ROLE", "resolver_ref": "ADMIN",
                       "quorum_type": "ANY"}).status_code == 201
    assert mundo.post(f"/approvals/policies/{pid}/activate", usuario, empresa, {}).status_code == 200
    return pid


# --------------------------------------------------------------------------- #
# Etapa 8: registrar la diferencia
# --------------------------------------------------------------------------- #
def test_registrar_un_dano_apunta_a_la_linea_y_no_repite_el_hecho(mundo):
    """La incidencia clasifica; el hecho físico sigue viviendo en la Spec 019."""
    m = _recepcion_con_linea(mundo, "ua", mundo.company_a, mundo.warehouse_a, "DANO",
                             recibido=20, physical_condition="DAÑADO", damaged_quantity=3,
                             damage_notes="Tres cajas aplastadas")
    r = _incidencia(mundo, "ua", mundo.company_a, m["recepcion"],
                    code="INC-DANO-1", incident_type="DANO", receipt_line_id=m["linea"],
                    affected_base_quantity=3, description="Se reclama al transportista")
    assert r.status_code == 200, r.text
    inc = r.json()
    assert inc["incident_type"] == "DANO" and inc["status"] == "REGISTRADA"
    assert inc["receipt_line_id"] == m["linea"]
    assert float(inc["affected_base_quantity"]) == 3.0
    assert inc["resolution"] is None

    # El hecho físico no se ha copiado a la incidencia: sigue en la línea
    detalle = mundo.get(f"/purchasing/receipts/{m['recepcion']}", "ua", mundo.company_a).json()
    linea = detalle["lines"][0]
    assert linea["physical_condition"] == "DAÑADO" and float(linea["damaged_quantity"]) == 3.0
    assert "physical_condition" not in inc, "la incidencia duplicó el hecho de la Spec 019"


def test_los_cinco_tipos_del_contrato_y_solo_esos(mundo):
    """Los cinco subelementos literales de la etapa 8. Ni uno más."""
    m = _recepcion_con_linea(mundo, "ua", mundo.company_a, mundo.warehouse_a, "TIPOS", recibido=50)
    for i, tipo in enumerate(("FALTANTE", "SOBRANTE", "DANO", "REFERENCIA_INCORRECTA")):
        r = _incidencia(mundo, "ua", mundo.company_a, m["recepcion"],
                        code=f"INC-T{i}", incident_type=tipo,
                        receipt_line_id=m["linea"], affected_base_quantity=2)
        assert r.status_code == 200, f"{tipo}: {r.text}"
    r = _incidencia(mundo, "ua", mundo.company_a, m["recepcion"],
                    code="INC-T4", incident_type="DIFERENCIA_DOCUMENTAL",
                    description="Falta el certificado de origen")
    assert r.status_code == 200, r.text
    assert r.json()["receipt_line_id"] is None

    for inventado in ("CALIDAD", "CUARENTENA", "LOTE", "VENCIMIENTO", "EMPAQUE"):
        r = _incidencia(mundo, "ua", mundo.company_a, m["recepcion"],
                        code=f"INC-X-{inventado}", incident_type=inventado,
                        receipt_line_id=m["linea"], affected_base_quantity=1)
        assert r.status_code == 422, f"aceptó un tipo inventado: {inventado}"
        assert r.json()["code"] == "INVALID_INCIDENT_TYPE"


def test_la_diferencia_documental_no_lleva_linea_ni_cantidad(mundo):
    """Es del documento, no de la mercancía."""
    m = _recepcion_con_linea(mundo, "ua", mundo.company_a, mundo.warehouse_a, "DOC")
    r = _incidencia(mundo, "ua", mundo.company_a, m["recepcion"],
                    code="INC-DOC-MAL", incident_type="DIFERENCIA_DOCUMENTAL",
                    receipt_line_id=m["linea"], affected_base_quantity=1)
    assert r.status_code == 422 and r.json()["code"] == "INCIDENT_DOCUMENTAL_HAS_NO_LINE", r.text


def test_una_diferencia_de_mercancia_exige_linea_y_cantidad(mundo):
    m = _recepcion_con_linea(mundo, "ua", mundo.company_a, mundo.warehouse_a, "MERC")
    r = _incidencia(mundo, "ua", mundo.company_a, m["recepcion"],
                    code="INC-SIN-LINEA", incident_type="DANO")
    assert r.status_code == 422 and r.json()["code"] == "INCIDENT_REQUIRES_LINE_AND_QUANTITY", r.text


# --------------------------------------------------------------------------- #
# Invariantes de cantidad
# --------------------------------------------------------------------------- #
def test_no_se_puede_danar_mas_de_lo_que_llego(mundo):
    m = _recepcion_con_linea(mundo, "ua", mundo.company_a, mundo.warehouse_a, "TOPE", recibido=10)
    r = _incidencia(mundo, "ua", mundo.company_a, m["recepcion"],
                    code="INC-TOPE", incident_type="DANO",
                    receipt_line_id=m["linea"], affected_base_quantity=11)
    assert r.status_code == 409 and r.json()["code"] == "INCIDENT_QUANTITY_EXCEEDED", r.text
    assert r.json()["details"]["cap_base"] == "10.000000"


def test_dos_incidencias_del_mismo_tipo_no_suman_mas_de_lo_recibido(mundo):
    """§42: si compiten sobre la misma clasificación física, no pueden pasarse."""
    m = _recepcion_con_linea(mundo, "ua", mundo.company_a, mundo.warehouse_a, "ACUM", recibido=24)
    assert _incidencia(mundo, "ua", mundo.company_a, m["recepcion"], code="INC-A1",
                       incident_type="DANO", receipt_line_id=m["linea"],
                       affected_base_quantity=10).status_code == 200
    r = _incidencia(mundo, "ua", mundo.company_a, m["recepcion"], code="INC-A2",
                    incident_type="DANO", receipt_line_id=m["linea"], affected_base_quantity=20)
    assert r.status_code == 409 and r.json()["code"] == "INCIDENT_QUANTITY_EXCEEDED", r.text
    assert r.json()["details"]["already_affected_base"] == "10.000000"
    # Otro tipo es otra dimensión: no compite con el daño
    assert _incidencia(mundo, "ua", mundo.company_a, m["recepcion"], code="INC-A3",
                       incident_type="REFERENCIA_INCORRECTA", receipt_line_id=m["linea"],
                       affected_base_quantity=20).status_code == 200


def test_el_faltante_se_mide_contra_lo_pedido_no_contra_lo_recibido(mundo):
    """Un faltante habla de mercancía que no llegó: su techo es lo que se pidió."""
    m = _recepcion_con_linea(mundo, "ua", mundo.company_a, mundo.warehouse_a, "FALTA",
                             recibido=5, cantidad_orden=100)
    r = _incidencia(mundo, "ua", mundo.company_a, m["recepcion"], code="INC-FALTA",
                    incident_type="FALTANTE", receipt_line_id=m["linea"], affected_base_quantity=95)
    assert r.status_code == 200, f"midió el faltante contra lo recibido: {r.text}"
    r = _incidencia(mundo, "ua", mundo.company_a, m["recepcion"], code="INC-FALTA-2",
                    incident_type="FALTANTE", receipt_line_id=m["linea"], affected_base_quantity=10)
    assert r.status_code == 409, "permitió faltar más de lo pedido"


def test_anular_libera_la_cantidad_comprometida(mundo):
    m = _recepcion_con_linea(mundo, "ua", mundo.company_a, mundo.warehouse_a, "ANUL", recibido=10)
    inc = _incidencia(mundo, "ua", mundo.company_a, m["recepcion"], code="INC-ANUL",
                      incident_type="DANO", receipt_line_id=m["linea"],
                      affected_base_quantity=10).json()
    r = _incidencia(mundo, "ua", mundo.company_a, m["recepcion"], code="INC-ANUL-2",
                    incident_type="DANO", receipt_line_id=m["linea"], affected_base_quantity=10)
    assert r.status_code == 409
    r = mundo.post(f"/purchasing/receipts/{m['recepcion']}/incidencias/{inc['id']}/cancel",
                   "ua", mundo.company_a, {"reason": "Se registró en la línea equivocada"})
    assert r.status_code == 200 and r.json()["status"] == "ANULADA", r.text
    r = _incidencia(mundo, "ua", mundo.company_a, m["recepcion"], code="INC-ANUL-3",
                    incident_type="DANO", receipt_line_id=m["linea"], affected_base_quantity=10)
    assert r.status_code == 200, "anular no liberó la cantidad"


# --------------------------------------------------------------------------- #
# Etapas 9 y 10: evidencia y escalamiento
# --------------------------------------------------------------------------- #
def test_escalar_deja_constancia_de_cuando_y_de_quien(mundo):
    m = _recepcion_con_linea(mundo, "ua", mundo.company_a, mundo.warehouse_a, "ESC")
    inc = _incidencia(mundo, "ua", mundo.company_a, m["recepcion"], code="INC-ESC",
                      incident_type="SOBRANTE", receipt_line_id=m["linea"],
                      affected_base_quantity=2).json()
    r = mundo.post(f"/purchasing/receipts/{m['recepcion']}/incidencias/{inc['id']}/escalate",
                   "ua", mundo.company_a, {"notes": "Se avisa a Compras para que reclame"})
    assert r.status_code == 200, r.text
    esc = r.json()
    assert esc["status"] == "ESCALADA" and esc["escalated_at"] and esc["escalated_by"]
    assert esc["escalation_notes"] == "Se avisa a Compras para que reclame"
    r = mundo.post(f"/purchasing/receipts/{m['recepcion']}/incidencias/{inc['id']}/escalate",
                   "ua", mundo.company_a, {})
    assert r.status_code == 409, "escaló dos veces"


def test_la_evidencia_se_adjunta_por_la_spec_046(mundo):
    """Etapa 9. Sin almacenamiento paralelo: la incidencia es un recurso enlazable."""
    m = _recepcion_con_linea(mundo, "ua", mundo.company_a, mundo.warehouse_a, "EVID")
    inc = _incidencia(mundo, "ua", mundo.company_a, m["recepcion"], code="INC-EVID",
                      incident_type="DANO", receipt_line_id=m["linea"],
                      affected_base_quantity=1).json()
    tipo = mundo.crear("/documentos/tipos", "ua", mundo.company_a,
                       {"company_id": mundo.company_a, "code": "EVID020", "name": "Evidencia",
                        "allowed_mime_types": ["image/png"], "scan_required": False})
    doc = mundo.crear("/documentos", "ua", mundo.company_a,
                      {"company_id": mundo.company_a, "document_type_id": tipo,
                       "title": "Foto de la caja rota"})
    r = mundo.post(f"/documentos/{doc}/vinculos", "ua", mundo.company_a,
                   {"resource_type": "ReceiptIncident", "resource_id": inc["id"]})
    assert r.status_code in (200, 201), r.text
    enlazados = mundo.get(f"/documentos/por-recurso/ReceiptIncident/{inc['id']}", "ua", mundo.company_a)
    assert enlazados.status_code == 200, enlazados.text
    cuerpo = enlazados.json()
    items = cuerpo["items"] if isinstance(cuerpo, dict) else cuerpo
    assert any(d["id"] == doc for d in items), enlazados.text


# --------------------------------------------------------------------------- #
# Tratamiento (§3): se registra, no se ejecuta
# --------------------------------------------------------------------------- #
def test_resolver_exige_un_tratamiento_del_contrato_y_un_motivo(mundo):
    m = _recepcion_con_linea(mundo, "ua", mundo.company_a, mundo.warehouse_a, "TRAT")
    inc = _incidencia(mundo, "ua", mundo.company_a, m["recepcion"], code="INC-TRAT",
                      incident_type="DANO", receipt_line_id=m["linea"],
                      affected_base_quantity=2).json()
    ruta = f"/purchasing/receipts/{m['recepcion']}/incidencias/{inc['id']}/resolve"
    r = mundo.post(ruta, "ua", mundo.company_a, {"resolution": "RECLAMO_PROVEEDOR", "reason": ""})
    assert r.status_code == 422, "resolvió sin motivo"
    r = mundo.post(ruta, "ua", mundo.company_a, {"resolution": "DEVOLVER", "reason": "x"})
    assert r.status_code == 422 and r.json()["code"] == "INVALID_INCIDENT_RESOLUTION", r.text
    r = mundo.post(ruta, "ua", mundo.company_a,
                   {"resolution": "RECLAMO_PROVEEDOR", "reason": "Se reclama al proveedor"})
    assert r.status_code == 200, r.text
    res = r.json()
    assert res["status"] == "RESUELTA" and res["resolution"] == "RECLAMO_PROVEEDOR"
    assert res["resolved_at"] and res["resolved_by"]
    assert res["resolution_reason"] == "Se reclama al proveedor"


def test_resolver_dos_veces_no_toma_dos_decisiones(mundo):
    m = _recepcion_con_linea(mundo, "ua", mundo.company_a, mundo.warehouse_a, "DOBLE")
    inc = _incidencia(mundo, "ua", mundo.company_a, m["recepcion"], code="INC-DOBLE",
                      incident_type="DANO", receipt_line_id=m["linea"],
                      affected_base_quantity=2).json()
    ruta = f"/purchasing/receipts/{m['recepcion']}/incidencias/{inc['id']}/resolve"
    assert mundo.post(ruta, "ua", mundo.company_a,
                      {"resolution": "CUARENTENA", "reason": "A cuarentena"}).status_code == 200
    r = mundo.post(ruta, "ua", mundo.company_a,
                   {"resolution": "RECLAMO_PROVEEDOR", "reason": "Ahora reclamo"})
    assert r.status_code == 409, "una incidencia resuelta cambió de tratamiento"
    final = mundo.get(f"/purchasing/receipts/{m['recepcion']}/incidencias/{inc['id']}",
                      "ua", mundo.company_a).json()
    assert final["resolution"] == "CUARENTENA"


def test_el_ajuste_autorizado_pasa_por_el_motor_de_aprobaciones(mundo):
    """Control crítico 115 del proceso: «Autorización de ajustes»."""
    pid = _politica_de_ajuste(mundo, "ua", mundo.company_a)
    try:
        m = _recepcion_con_linea(mundo, "ua", mundo.company_a, mundo.warehouse_a, "AJUS")
        inc = _incidencia(mundo, "ua", mundo.company_a, m["recepcion"], code="INC-AJUS",
                          incident_type="FALTANTE", receipt_line_id=m["linea"],
                          affected_base_quantity=4).json()
        ruta = f"/purchasing/receipts/{m['recepcion']}/incidencias/{inc['id']}/resolve"
        r = mundo.post(ruta, "ua", mundo.company_a,
                       {"resolution": "AJUSTE_AUTORIZADO", "reason": "Se ajusta el faltante"})
        assert r.status_code == 200, r.text
        pendiente = r.json()
        assert pendiente["status"] == "PENDIENTE_AUTORIZACION", "resolvió sin autorización"
        assert pendiente["approval_request_id"], "no abrió solicitud en el motor único"
        assert pendiente["resolution"] is None, "dio por decidido lo que aún no está autorizado"

        r = mundo.post(ruta, "ua", mundo.company_a,
                       {"resolution": "AJUSTE_AUTORIZADO", "reason": "insisto"})
        assert r.status_code == 409 and r.json()["code"] == "APPROVAL_PENDING", r.text

        bandeja = mundo.get("/approvals/inbox", "uab", mundo.company_a).json()["items"]
        paso = next(i for i in bandeja if i["document_id"] == inc["id"])["step_id"]
        assert mundo.post(f"/approvals/steps/{paso}/approve", "uab", mundo.company_a,
                          {"reason": None}).status_code == 200

        r = mundo.post(ruta, "ua", mundo.company_a,
                       {"resolution": "AJUSTE_AUTORIZADO", "reason": "Se ajusta el faltante"})
        assert r.status_code == 200 and r.json()["status"] == "RESUELTA", r.text
        assert r.json()["resolution"] == "AJUSTE_AUTORIZADO"
    finally:
        mundo.post(f"/approvals/policies/{pid}/close", "ua", mundo.company_a, {})


def test_sin_politica_de_aprobacion_el_ajuste_se_resuelve_directo(mundo):
    """`P8`: la política es del cliente. Sin ella, el motor no exige nada."""
    m = _recepcion_con_linea(mundo, "ua", mundo.company_a, mundo.warehouse_a, "AJSIN")
    inc = _incidencia(mundo, "ua", mundo.company_a, m["recepcion"], code="INC-AJSIN",
                      incident_type="FALTANTE", receipt_line_id=m["linea"],
                      affected_base_quantity=3).json()
    r = mundo.post(f"/purchasing/receipts/{m['recepcion']}/incidencias/{inc['id']}/resolve",
                   "ua", mundo.company_a, {"resolution": "AJUSTE_AUTORIZADO", "reason": "Ajuste"})
    assert r.status_code == 200 and r.json()["status"] == "RESUELTA", r.text


def test_resolver_no_toca_el_inventario(mundo):
    """Registrar el tratamiento no es ejecutarlo: eso es de la Spec 021."""
    m = _recepcion_con_linea(mundo, "ua", mundo.company_a, mundo.warehouse_a, "NOINV", recibido=10)
    saldos_antes = mundo.get("/inventory/balances", "ua", mundo.company_a).json()["items"]
    movimientos_antes = len(mundo.filas("inventory_movements", "id"))
    inc = _incidencia(mundo, "ua", mundo.company_a, m["recepcion"], code="INC-NOINV",
                      incident_type="DANO", receipt_line_id=m["linea"],
                      affected_base_quantity=4).json()
    mundo.post(f"/purchasing/receipts/{m['recepcion']}/incidencias/{inc['id']}/resolve",
               "ua", mundo.company_a, {"resolution": "CUARENTENA", "reason": "Se separa"})
    saldos_despues = mundo.get("/inventory/balances", "ua", mundo.company_a).json()["items"]
    assert saldos_antes == saldos_despues, "la incidencia movió inventario"
    assert len(mundo.filas("inventory_movements", "id")) == movimientos_antes
    estados = {e[0] for e in _sql(mundo, "SELECT DISTINCT state FROM inventory_balances WHERE company_id = :c",
                                  c=mundo.company_a)}
    assert estados <= {"RECIBIDO"}, "020 escribió estados de mercancía, que son de 021/023"


# --------------------------------------------------------------------------- #
# Contrato de salida para la Spec 021
# --------------------------------------------------------------------------- #
def test_el_resultado_para_la_021_es_estructurado_y_no_texto_libre(mundo):
    m = _recepcion_con_linea(mundo, "ua", mundo.company_a, mundo.warehouse_a, "RES", recibido=30)
    a = _incidencia(mundo, "ua", mundo.company_a, m["recepcion"], code="INC-R1",
                    incident_type="DANO", receipt_line_id=m["linea"],
                    affected_base_quantity=5).json()
    b = _incidencia(mundo, "ua", mundo.company_a, m["recepcion"], code="INC-R2",
                    incident_type="DIFERENCIA_DOCUMENTAL", description="Falta guía").json()

    ruta = f"/purchasing/receipts/{m['recepcion']}/incidencias/resultado"
    parcial = mundo.get(ruta, "ua", mundo.company_a).json()
    assert parcial["total"] == 2 and parcial["unresolved"] == 2
    assert parcial["ready_for_confirmation"] is False, "dio por lista una recepción con incidencias abiertas"

    for inc, tratamiento in ((a, "CUARENTENA"), (b, "INVESTIGACION_INTERNA")):
        assert mundo.post(f"/purchasing/receipts/{m['recepcion']}/incidencias/{inc['id']}/resolve",
                          "ua", mundo.company_a,
                          {"resolution": tratamiento, "reason": "Resuelto"}).status_code == 200

    final = mundo.get(ruta, "ua", mundo.company_a).json()
    assert final["ready_for_confirmation"] is True and final["unresolved"] == 0
    porcodigo = {x["code"]: x for x in final["items"]}
    assert porcodigo["INC-R1"]["resolution"] == "CUARENTENA"
    assert float(porcodigo["INC-R1"]["affected_base_quantity"]) == 5.0
    assert porcodigo["INC-R1"]["receipt_line_id"] == m["linea"]
    assert porcodigo["INC-R2"]["resolution"] == "INVESTIGACION_INTERNA"
    assert porcodigo["INC-R2"]["receipt_line_id"] is None


def test_una_recepcion_sin_diferencias_no_crea_ninguna_incidencia(mundo):
    """§16: el camino feliz no pasa por la Spec 020."""
    antes = len(mundo.filas("receipt_incidents", "id"))
    m = _recepcion_con_linea(mundo, "ua", mundo.company_a, mundo.warehouse_a, "FELIZ", recibido=8)
    for accion, cuerpo in (("confirm", {}), ("quality", {}), ("quality", {"quality_status": "APPROVED"}), ("accept", {})):
        assert mundo.post(f"/purchasing/receipts/{m['recepcion']}/{accion}", "ua", mundo.company_a,
                          cuerpo).status_code == 200
    assert len(mundo.filas("receipt_incidents", "id")) == antes, "se creó una incidencia vacía"
    resultado = mundo.get(f"/purchasing/receipts/{m['recepcion']}/incidencias/resultado",
                          "ua", mundo.company_a).json()
    assert resultado["total"] == 0 and resultado["ready_for_confirmation"] is True


# --------------------------------------------------------------------------- #
# P23: la incidencia no reinterpreta el hecho
# --------------------------------------------------------------------------- #
def test_la_incidencia_historica_no_cambia_si_cambia_el_maestro(mundo):
    unidad = mundo.crear("/maestros/unidades", "ua", mundo.company_a,
                         {"code": "U020", "name": "Unidad", "symbol": "u", "decimals": 0})
    prod = _producto(mundo, "ua", mundo.company_a, "P020-P23", base_unit_id=unidad)
    caja = mundo.crear(f"/maestros/productos/{prod}/presentaciones", "ua", mundo.company_a,
                       {"code": "CAJA12-020", "name": "Caja de 12", "factor_to_base": "12",
                        "valid_from": (datetime.now(UTC) - timedelta(days=1)).isoformat()})
    m = _recepcion_con_linea(mundo, "ua", mundo.company_a, mundo.warehouse_a, "P23",
                             producto=prod, recibido=2, presentation_id=caja)
    inc = _incidencia(mundo, "ua", mundo.company_a, m["recepcion"], code="INC-P23",
                      incident_type="DANO", receipt_line_id=m["linea"],
                      affected_base_quantity=12).json()
    assert float(inc["affected_base_quantity"]) == 12.0

    r = mundo.post(f"/maestros/presentaciones/{caja}/versiones", "ua", mundo.company_a,
                   {"factor_to_base": "6", "valid_from": (datetime.now(UTC) + timedelta(seconds=1)).isoformat()})
    assert r.status_code in (200, 201), r.text
    despues = mundo.get(f"/purchasing/receipts/{m['recepcion']}/incidencias/{inc['id']}",
                        "ua", mundo.company_a).json()
    assert float(despues["affected_base_quantity"]) == 12.0, "reinterpretó una incidencia histórica"
    linea = mundo.get(f"/purchasing/receipts/{m['recepcion']}", "ua", mundo.company_a).json()["lines"][0]
    assert float(linea["conversion_factor_snapshot"]) == 12.0


# --------------------------------------------------------------------------- #
# Multiempresa y cadena de padres
# --------------------------------------------------------------------------- #
def test_usuario_ab_bajo_contexto_a_no_opera_la_incidencia_de_b(mundo):
    m = _recepcion_con_linea(mundo, "ub", mundo.company_b, mundo.warehouse_b, "AB")
    inc = _incidencia(mundo, "ub", mundo.company_b, m["recepcion"], code="INC-AB",
                      incident_type="DANO", receipt_line_id=m["linea"],
                      affected_base_quantity=1).json()
    base = f"/purchasing/receipts/{m['recepcion']}/incidencias/{inc['id']}"
    assert mundo.get(base, "uab", mundo.company_a).status_code == 404
    for accion, cuerpo in (("escalate", {}), ("resolve", {"resolution": "CUARENTENA", "reason": "x"}),
                           ("cancel", {"reason": "x"})):
        r = mundo.post(f"{base}/{accion}", "uab", mundo.company_a, cuerpo)
        assert r.status_code == 404, f"{accion}: {r.status_code} {r.text}"
    assert mundo.get(base, "uab", mundo.company_b).status_code == 200


def test_cross_tenant_bloqueado(mundo):
    m = _recepcion_con_linea(mundo, "ua", mundo.company_a, mundo.warehouse_a, "XT")
    inc = _incidencia(mundo, "ua", mundo.company_a, m["recepcion"], code="INC-XT",
                      incident_type="DANO", receipt_line_id=m["linea"],
                      affected_base_quantity=1).json()
    r = mundo.get(f"/purchasing/receipts/{m['recepcion']}/incidencias/{inc['id']}",
                  "uc", mundo.company_c, tenant="T2")
    assert r.status_code == 404, r.text


def test_una_incidencia_no_se_alcanza_desde_otra_recepcion(mundo):
    """§31: que el identificador exista no la hace de esta recepción."""
    a = _recepcion_con_linea(mundo, "ua", mundo.company_a, mundo.warehouse_a, "CAD1")
    b = _recepcion_con_linea(mundo, "ua", mundo.company_a, mundo.warehouse_a, "CAD2")
    inc = _incidencia(mundo, "ua", mundo.company_a, a["recepcion"], code="INC-CAD",
                      incident_type="DANO", receipt_line_id=a["linea"],
                      affected_base_quantity=1).json()
    r = mundo.get(f"/purchasing/receipts/{b['recepcion']}/incidencias/{inc['id']}", "ua", mundo.company_a)
    assert r.status_code == 404, "alcanzó la incidencia desde otra recepción"


def test_no_se_registra_contra_la_linea_de_otra_recepcion(mundo):
    a = _recepcion_con_linea(mundo, "ua", mundo.company_a, mundo.warehouse_a, "LIN1")
    b = _recepcion_con_linea(mundo, "ua", mundo.company_a, mundo.warehouse_a, "LIN2")
    r = _incidencia(mundo, "ua", mundo.company_a, a["recepcion"], code="INC-LIN",
                    incident_type="DANO", receipt_line_id=b["linea"], affected_base_quantity=1)
    assert r.status_code == 404 and r.json()["code"] == "RECEIPT_LINE_NOT_FOUND", r.text


def test_el_cuerpo_no_elige_la_empresa(mundo):
    m = _recepcion_con_linea(mundo, "ua", mundo.company_a, mundo.warehouse_a, "BODY")
    r = _incidencia(mundo, "ua", mundo.company_a, m["recepcion"], code="INC-BODY",
                    incident_type="DANO", receipt_line_id=m["linea"], affected_base_quantity=1,
                    company_id=mundo.company_b)
    assert r.status_code == 422, r.text


# --------------------------------------------------------------------------- #
# Auditoría
# --------------------------------------------------------------------------- #
def test_la_auditoria_cuenta_el_ciclo_entero(mundo):
    m = _recepcion_con_linea(mundo, "ua", mundo.company_a, mundo.warehouse_a, "AUD", recibido=12)
    inc = _incidencia(mundo, "ua", mundo.company_a, m["recepcion"], code="INC-AUD",
                      incident_type="DANO", receipt_line_id=m["linea"],
                      affected_base_quantity=6).json()
    base = f"/purchasing/receipts/{m['recepcion']}/incidencias/{inc['id']}"
    mundo.post(f"{base}/escalate", "ua", mundo.company_a, {"notes": "A Compras"})
    mundo.post(f"{base}/resolve", "ua", mundo.company_a,
               {"resolution": "RECLAMO_PROVEEDOR", "reason": "Se reclama"})

    filas = _sql(mundo, "SELECT action, user_id, company_id, tenant_id, after, reason FROM audit_events "
                        "WHERE entity_type = 'ReceiptIncident' AND entity_id = :i ORDER BY created_at",
                 i=inc["id"])
    acciones = [f[0] for f in filas]
    assert acciones == ["RECEIPT_INCIDENT_REGISTERED", "RECEIPT_INCIDENT_ESCALATED",
                        "RECEIPT_INCIDENT_RESOLVED"], acciones
    registrada = filas[0]
    assert registrada[1] and registrada[2] == mundo.company_a and registrada[3] == mundo.t1
    for campo in ("receipt_id", "receipt_line_id", "product_id", "incident_type",
                  "affected_base_quantity"):
        assert campo in registrada[4], f"la auditoría no conserva {campo}"
    resuelta = filas[2]
    assert resuelta[4]["resolution"] == "RECLAMO_PROVEEDOR" and resuelta[5] == "Se reclama"
