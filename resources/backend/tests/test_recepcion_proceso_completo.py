"""Recepción como proceso completo: orden recibible, almacén operable e integridad al aceptar."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.core.errors import ConflictError, NotFoundError
from app.modules.audit.models import AuditEvent
from app.modules.inventory.models import InventoryLot, InventoryMovement, ProductSerial
from app.modules.purchasing import api as purchasing_api
from app.modules.purchasing import service as ap_service
from app.modules.purchasing.models import GoodsReceipt, GoodsReceiptLine
from tests.test_recepcion_linea_integridad import (
    COMPANY,
    OTHER,
    _almacen,
    _party,
    db_session,  # noqa: F401
    mundo,  # noqa: F401
)


def _ctx(company=COMPANY):
    return SimpleNamespace(company_id=company)


def _historica(db, m, *, order_line, producto):
    line = GoodsReceiptLine(
        receipt_id=str(m.recepcion.id),
        order_line_id=str(order_line.id),
        product_id=str(producto.id),
        quantity_received=5,
        quantity_accepted=5,
        quantity_rejected=0,
        quality="PENDING",
        lot_number="L-H",
        serials="S-H",
    )
    db.add(line)
    db.flush()
    return line


def _preparar_aceptacion(db, recepcion):
    ap_service.confirm_receipt(db, receipt=recepcion)
    recepcion.quality_status = "APPROVED"
    db.flush()


def _crear_ordenes_aprobadas(db, m, cantidad):
    creadas = []
    for i in range(cantidad):
        order = ap_service.create_order(
            db, company_id=COMPANY, code=f"OC-A{i:02d}", supplier_id=str(m.supplier.id)
        )
        order.status = "APPROVED"
        db.flush()
        creadas.append(order)
    return creadas


def test_o01_la_primera_pagina_no_alcanza(db_session, mundo):  # noqa: F811
    _crear_ordenes_aprobadas(db_session, mundo, 25)
    resultado = purchasing_api.list_orders(
        db=db_session,
        user=None,
        ctx=_ctx(),
        q="",
        status=None,
        receivable=False,
        page=1,
        page_size=20,
    )
    assert len(resultado["items"]) == 20
    assert resultado["total"] == 26


def test_o02_orden_fuera_de_la_primera_pagina_se_encuentra(db_session, mundo):  # noqa: F811
    _crear_ordenes_aprobadas(db_session, mundo, 25)
    resultado = purchasing_api.list_orders(
        db=db_session,
        user=None,
        ctx=_ctx(),
        q="OC-A00",
        status=None,
        receivable=True,
        page=1,
        page_size=20,
    )
    assert resultado["total"] == 1
    assert len(resultado["items"]) == 1
    assert resultado["items"][0]["code"] == "OC-A00"


def test_o02b_recorrer_paginas_alcanza_todas(db_session, mundo):  # noqa: F811
    _crear_ordenes_aprobadas(db_session, mundo, 25)
    ids = set()
    for page in (1, 2):
        resultado = purchasing_api.list_orders(
            db=db_session,
            user=None,
            ctx=_ctx(),
            q="",
            status=None,
            receivable=True,
            page=page,
            page_size=20,
        )
        for item in resultado["items"]:
            ids.add(item["id"])
    assert len(ids) == 26


def test_o03_orden_de_otra_empresa_no_aparece(db_session, mundo):  # noqa: F811
    supplier_otro = _party(db_session, OTHER, "SUP-X")
    ap_service.create_order(
        db_session, company_id=OTHER, code="OC-X", supplier_id=str(supplier_otro.id)
    )
    resultado = purchasing_api.list_orders(
        db=db_session,
        user=None,
        ctx=_ctx(),
        q="OC-X",
        status=None,
        receivable=False,
        page=1,
        page_size=20,
    )
    assert resultado["items"] == []
    assert resultado["total"] == 0


def test_o04_orden_no_recibible_no_aparece(db_session, mundo):  # noqa: F811
    order = ap_service.create_order(
        db_session, company_id=COMPANY, code="OC-DR", supplier_id=str(mundo.supplier.id)
    )
    assert order.status == "DRAFT"
    recibible = purchasing_api.list_orders(
        db=db_session,
        user=None,
        ctx=_ctx(),
        q="OC-DR",
        status=None,
        receivable=True,
        page=1,
        page_size=20,
    )
    assert recibible["items"] == []
    no_recibible = purchasing_api.list_orders(
        db=db_session,
        user=None,
        ctx=_ctx(),
        q="OC-DR",
        status=None,
        receivable=False,
        page=1,
        page_size=20,
    )
    assert len(no_recibible["items"]) == 1


def test_estados_recibibles_son_una_sola_autoridad():
    assert ap_service.RECEIVABLE_ORDER_STATUSES == (
        "APPROVED",
        "PARTIALLY_RECEIVED",
        "RECEIVED",
    )


@pytest.mark.parametrize("estado", ("APPROVED", "PARTIALLY_RECEIVED", "RECEIVED"))
def test_orden_recibible_admite_recepcion(db_session, mundo, estado):  # noqa: F811
    mundo.order.status = estado
    db_session.flush()
    acciones = ap_service.order_allowed_actions(mundo.order)
    assert acciones["receive"] is True
    receipt = ap_service.create_receipt(
        db_session,
        company_id=COMPANY,
        code="RC-E",
        order_id=str(mundo.order.id),
        warehouse_id=str(mundo.almacen.id),
    )
    assert receipt is not None


@pytest.mark.parametrize(
    "estado", ("DRAFT", "SUBMITTED", "CLOSED", "CANCELLED", "REJECTED")
)
def test_orden_no_recibible_se_rechaza(db_session, mundo, estado):  # noqa: F811
    mundo.order.status = estado
    db_session.flush()
    acciones = ap_service.order_allowed_actions(mundo.order)
    assert acciones["receive"] is False
    with pytest.raises(ConflictError) as excinfo:
        ap_service.create_receipt(
            db_session,
            company_id=COMPANY,
            code="RC-N",
            order_id=str(mundo.order.id),
            warehouse_id=str(mundo.almacen.id),
        )
    assert excinfo.value.code == "ORDER_NOT_RECEIVABLE"


@pytest.mark.parametrize("estado", ("INACTIVE", "BLOCKED", "MAINTENANCE"))
def test_w_almacen_no_operable_no_recibe(db_session, mundo, estado):  # noqa: F811
    almacen = _almacen(db_session, COMPANY, f"WH-{estado}")
    almacen.status = estado
    db_session.flush()
    audit_antes = (
        db_session.query(AuditEvent).filter(AuditEvent.action == "RECEIPT_CREATED").count()
    )
    with pytest.raises(ConflictError) as excinfo:
        ap_service.create_receipt(
            db_session,
            company_id=COMPANY,
            code="RC-W",
            order_id=str(mundo.order.id),
            warehouse_id=str(almacen.id),
        )
    assert excinfo.value.code == "WAREHOUSE_NOT_ELIGIBLE"
    assert (
        db_session.query(GoodsReceipt).filter(GoodsReceipt.code == "RC-W").count() == 0
    )
    audit_despues = (
        db_session.query(AuditEvent).filter(AuditEvent.action == "RECEIPT_CREATED").count()
    )
    assert audit_despues == audit_antes


def test_w01_almacen_activo_recibe(db_session, mundo):  # noqa: F811
    almacen = _almacen(db_session, COMPANY, "WH-ACT")
    almacen.status = "ACTIVE"
    db_session.flush()
    receipt = ap_service.create_receipt(
        db_session,
        company_id=COMPANY,
        code="RC-ACT",
        order_id=str(mundo.order.id),
        warehouse_id=str(almacen.id),
    )
    assert receipt is not None


def test_w06_almacen_de_otra_empresa_no_existe(db_session, mundo):  # noqa: F811
    almacen = _almacen(db_session, OTHER, "WH-OTRA")
    with pytest.raises(NotFoundError) as excinfo:
        ap_service.create_receipt(
            db_session,
            company_id=COMPANY,
            code="RC-OTRA",
            order_id=str(mundo.order.id),
            warehouse_id=str(almacen.id),
        )
    assert excinfo.value.code == "WAREHOUSE_NOT_FOUND"


def test_w_almacen_desactivado_no_acepta(db_session, mundo):  # noqa: F811
    ap_service.add_receipt_line(
        db_session,
        company_id=COMPANY,
        receipt_id=str(mundo.recepcion.id),
        order_line_id=str(mundo.linea_a.id),
        product_id=str(mundo.producto_a.id),
        quantity_received=10.0,
        quantity_accepted=10.0,
        quantity_rejected=0.0,
        identification_ok=None,
        reference_ok=None,
    )
    _preparar_aceptacion(db_session, mundo.recepcion)
    mundo.almacen.status = "INACTIVE"
    db_session.flush()
    with pytest.raises(ConflictError) as excinfo:
        ap_service.accept_receipt(db_session, receipt=mundo.recepcion)
    assert excinfo.value.code == "WAREHOUSE_NOT_ELIGIBLE"
    assert db_session.query(InventoryMovement).count() == 0
    db_session.refresh(mundo.recepcion)
    assert mundo.recepcion.status == "CONFIRMED"


def test_h01_h08_fila_historica_no_se_acepta(db_session, mundo):  # noqa: F811
    _historica(db_session, mundo, order_line=mundo.linea_a, producto=mundo.producto_b)
    _preparar_aceptacion(db_session, mundo.recepcion)
    with pytest.raises(ConflictError) as excinfo:
        ap_service.accept_receipt(db_session, receipt=mundo.recepcion)
    assert excinfo.value.code == "RECEIPT_LINE_INTEGRITY"
    assert (
        db_session.query(InventoryMovement)
        .filter(InventoryMovement.product_id == str(mundo.producto_b.id))
        .count()
        == 0
    )
    assert (
        db_session.query(InventoryLot)
        .filter(InventoryLot.product_id == str(mundo.producto_b.id))
        .count()
        == 0
    )
    assert (
        db_session.query(ProductSerial)
        .filter(ProductSerial.product_id == str(mundo.producto_b.id))
        .count()
        == 0
    )
    db_session.refresh(mundo.linea_a)
    assert mundo.linea_a.quantity_received == 0
    db_session.refresh(mundo.recepcion)
    assert mundo.recepcion.status == "CONFIRMED"
    assert mundo.recepcion.record_issued_at is None
    assert (
        db_session.query(AuditEvent).filter(AuditEvent.action == "RECEIPT_ACCEPTED").count()
        == 0
    )


def test_h_linea_buena_antes_de_la_mala_no_deja_efectos(db_session, mundo):  # noqa: F811
    ap_service.add_receipt_line(
        db_session,
        company_id=COMPANY,
        receipt_id=str(mundo.recepcion.id),
        order_line_id=str(mundo.linea_a.id),
        product_id=str(mundo.producto_a.id),
        quantity_received=10.0,
        quantity_accepted=10.0,
        quantity_rejected=0.0,
        identification_ok=None,
        reference_ok=None,
    )
    db_session.flush()
    for linea in db_session.query(GoodsReceiptLine).filter(
        GoodsReceiptLine.receipt_id == str(mundo.recepcion.id)
    ):
        linea.lot_number = "L-OK"
    db_session.flush()
    _historica(db_session, mundo, order_line=mundo.linea_b, producto=mundo.producto_a)
    _preparar_aceptacion(db_session, mundo.recepcion)
    with pytest.raises(ConflictError) as excinfo:
        ap_service.accept_receipt(db_session, receipt=mundo.recepcion)
    assert excinfo.value.code == "RECEIPT_LINE_INTEGRITY"
    assert db_session.query(InventoryMovement).count() == 0
    assert (
        db_session.query(InventoryLot)
        .filter(InventoryLot.product_id == str(mundo.producto_a.id))
        .count()
        == 0
    )
    db_session.refresh(mundo.linea_a)
    assert mundo.linea_a.quantity_received == 0


def test_h_linea_de_otra_orden_no_se_acepta(db_session, mundo):  # noqa: F811
    otra_order = ap_service.create_order(
        db_session, company_id=COMPANY, code="OC-OTRA", supplier_id=str(mundo.supplier.id)
    )
    otra_linea = ap_service.add_order_line(
        db_session,
        order_id=str(otra_order.id),
        product_id=str(mundo.producto_a.id),
        quantity_ordered=10.0,
        unit_price=5.0,
    )
    _historica(db_session, mundo, order_line=otra_linea, producto=mundo.producto_a)
    _preparar_aceptacion(db_session, mundo.recepcion)
    with pytest.raises(ConflictError) as excinfo:
        ap_service.accept_receipt(db_session, receipt=mundo.recepcion)
    assert excinfo.value.code == "RECEIPT_LINE_INTEGRITY"


def test_h09_flujo_correcto_sigue_aceptando(db_session, mundo):  # noqa: F811
    ap_service.add_receipt_line(
        db_session,
        company_id=COMPANY,
        receipt_id=str(mundo.recepcion.id),
        order_line_id=str(mundo.linea_a.id),
        product_id=str(mundo.producto_a.id),
        quantity_received=10.0,
        quantity_accepted=10.0,
        quantity_rejected=0.0,
        identification_ok=None,
        reference_ok=None,
    )
    _preparar_aceptacion(db_session, mundo.recepcion)
    ap_service.accept_receipt(db_session, receipt=mundo.recepcion)
    db_session.refresh(mundo.recepcion)
    assert mundo.recepcion.status == "ACCEPTED"
    assert db_session.query(InventoryMovement).count() == 1


@pytest.mark.parametrize("veredicto", ("APPROVED", "REJECTED"))
def test_conformidad_se_registra_y_audita(db_session, mundo, veredicto):  # noqa: F811
    ap_service.confirm_receipt(db_session, receipt=mundo.recepcion)
    ap_service.registrar_conformidad(
        db_session, receipt=mundo.recepcion, quality_status=veredicto, actor=None
    )
    db_session.refresh(mundo.recepcion)
    assert mundo.recepcion.quality_status == veredicto
    eventos = (
        db_session.query(AuditEvent)
        .filter(AuditEvent.action == "RECEIPT_QUALITY_RECORDED")
        .all()
    )
    assert len(eventos) == 1
    assert eventos[0].after["quality_status"] == veredicto


def test_rechazada_cierra_la_recepcion(db_session, mundo):  # noqa: F811
    ap_service.confirm_receipt(db_session, receipt=mundo.recepcion)
    ap_service.registrar_conformidad(
        db_session, receipt=mundo.recepcion, quality_status="REJECTED", actor=None
    )
    db_session.refresh(mundo.recepcion)
    assert mundo.recepcion.status == "REJECTED"
    assert db_session.query(InventoryMovement).count() == 0


@pytest.mark.parametrize("valor", (True, False, None))
def test_observacion_se_guarda_tal_cual(db_session, mundo, valor):  # noqa: F811
    ap_service.add_receipt_line(
        db_session,
        company_id=COMPANY,
        receipt_id=str(mundo.recepcion.id),
        order_line_id=str(mundo.linea_a.id),
        product_id=str(mundo.producto_a.id),
        quantity_received=10.0,
        quantity_accepted=10.0,
        quantity_rejected=0.0,
        identification_ok=valor,
        reference_ok=valor,
    )
    linea = (
        db_session.query(GoodsReceiptLine)
        .filter(GoodsReceiptLine.receipt_id == str(mundo.recepcion.id))
        .one()
    )
    assert linea.identification_ok is valor
    assert linea.reference_ok is valor
    evento = (
        db_session.query(AuditEvent)
        .filter(AuditEvent.action == "RECEIPT_LINE_ADDED")
        .one()
    )
    assert evento.after["identification_ok"] is valor
    assert evento.after["reference_ok"] is valor


def test_listado_de_recepciones_trae_codigo_de_orden(db_session, mundo):  # noqa: F811
    resultado = purchasing_api.list_receipts(
        db=db_session, user=None, ctx=_ctx()
    )
    recibos = [item for item in resultado["items"] if item["id"] == str(mundo.recepcion.id)]
    assert len(recibos) == 1
    assert recibos[0]["order_code"] == "OC-1"
