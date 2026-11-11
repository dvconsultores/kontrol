from __future__ import annotations

import threading
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.errors import ConflictError
from app.modules.imports.landed_cost import _is_layer_consumed
from app.modules.inventory import service as inv
from app.modules.inventory.models import CostingProfile, CostLayer, DispatchCostRelief, InventoryMovement
from app.modules.organization.models import Warehouse
from app.modules.sales import service as sales
from app.modules.sales.models import Shipment
from tests.test_spec035_dispatch import _despacho, _emitir, _hasta_facturado, _saldos
from tests.test_spec036_returns import _despachado, _solicitar

pytest_plugins = ("tests.conftest_multicompany",)


def _capas(db, *, company_id, product_id, warehouse_id):
    return db.execute(
        select(CostLayer)
        .where(CostLayer.company_id == company_id,
               CostLayer.product_id == product_id,
               CostLayer.warehouse_id == warehouse_id)
        .order_by(CostLayer.created_at.asc())
    ).scalars().all()


def _snapshot(db, *, shipment_id):
    return db.execute(
        select(DispatchCostRelief).where(DispatchCostRelief.shipment_id == shipment_id)
    ).scalars().all()


def _activo_fifo(db, *, company_id, product_id):
    perfil = CostingProfile(
        company_id=company_id,
        product_id=product_id,
        code=f"FIFO-{uuid4().hex[:8]}",
        method="FIFO",
        status="ACTIVE",
        currency="VED",
    )
    db.add(perfil)
    db.flush()
    return perfil


def _preparar_y_confirmar(db, mundo, e, *, fifo=False):
    _emitir(db, mundo, e)
    sh = _despacho(db, mundo, e)
    sales.validate_shipment(db, shipment=sh, actor="despachador")
    if fifo:
        _activo_fifo(db, company_id=mundo.company_a, product_id=e["prod"])
        db.commit()
    sales.confirm_shipment(db, shipment=sh, actor="despachador")
    db.commit()
    return sh


def _valoracion(db, mundo, product_id, warehouse_id=None):
    wh = warehouse_id or mundo.warehouse_a
    return Decimal(str(inv.valuation(db, company_id=mundo.company_a,
                                     product_id=product_id, warehouse_id=wh))).quantize(Decimal("0.01"))


def test_v1_promedio_simple_consume_una_capa(mundo):
    db = mundo.factory()
    try:
        e = _hasta_facturado(db, mundo, cantidad=4, entradas=[(10, "5.00")])
        sh = _preparar_y_confirmar(db, mundo, e)

        layers = _capas(db, company_id=mundo.company_a, product_id=e["prod"],
                        warehouse_id=mundo.warehouse_a)
        assert len(layers) == 1
        assert layers[0].quantity_remaining == Decimal("6.000000")
        assert _valoracion(db, mundo, e["prod"]) == Decimal("30.00")

        snap = _snapshot(db, shipment_id=str(sh.id))
        assert len(snap) == 1
        assert snap[0].quantity == Decimal("4.000000")
        assert snap[0].total_cost == Decimal("20.000000")
        assert snap[0].method == "AVERAGE"
        assert snap[0].currency == "VED"

        mov = db.get(InventoryMovement, snap[0].movement_id)
        assert mov.unit_cost == Decimal("5.00")

        saldos = _saldos(db, mundo.company_a, e["prod"])
        assert saldos.get((e["area"], "DESPACHADO")) == Decimal("4")

        reservas = inv.order_reservations(db, company_id=mundo.company_a,
                                          order_id=str(e["pedido"].id), only_active=False)
        assert all(r.status == "FULFILLED" for r in reservas)
    finally:
        db.close()


def test_v2_promedio_dos_capas(mundo):
    db = mundo.factory()
    try:
        e = _hasta_facturado(db, mundo, cantidad=4, entradas=[(10, "5.00"), (10, "7.00")])
        sh = _preparar_y_confirmar(db, mundo, e)

        layers = _capas(db, company_id=mundo.company_a, product_id=e["prod"],
                        warehouse_id=mundo.warehouse_a)
        assert [float(capa.quantity_remaining) for capa in layers] == [8.0, 8.0]
        assert _valoracion(db, mundo, e["prod"]) == Decimal("96.00")

        snap = _snapshot(db, shipment_id=str(sh.id))
        assert len(snap) == 2
        assert sum(s.quantity for s in snap) == Decimal("4")
        assert sum(s.total_cost for s in snap) == Decimal("24")
        assert all(s.effective_unit_cost == Decimal("6.000000") for s in snap)
    finally:
        db.close()


def test_v3_fifo_dos_capas(mundo):
    db = mundo.factory()
    try:
        e = _hasta_facturado(db, mundo, cantidad=5, entradas=[(3, "5.00"), (10, "8.00")])
        sh = _preparar_y_confirmar(db, mundo, e, fifo=True)

        layers = _capas(db, company_id=mundo.company_a, product_id=e["prod"],
                        warehouse_id=mundo.warehouse_a)
        assert [float(capa.quantity_remaining) for capa in layers] == [0.0, 8.0]
        assert layers[0].status == "CLOSED"
        assert layers[1].status == "OPEN"
        assert _valoracion(db, mundo, e["prod"]) == Decimal("64.00")

        snap = _snapshot(db, shipment_id=str(sh.id))
        assert len(snap) == 2
        ordenados = sorted(snap, key=lambda s: s.quantity, reverse=True)
        assert [(float(s.quantity), float(s.total_cost)) for s in ordenados] == [(3.0, 15.0), (2.0, 16.0)]
        assert all(s.method == "FIFO" for s in snap)

        mov = db.get(InventoryMovement, ordenados[0].movement_id)
        assert Decimal(str(mov.unit_cost)).quantize(Decimal("0.01")) == Decimal("6.20")
    finally:
        db.close()


def test_v4_fifo_una_capa(mundo):
    db = mundo.factory()
    try:
        e = _hasta_facturado(db, mundo, cantidad=4, entradas=[(10, "5.00")])
        sh = _preparar_y_confirmar(db, mundo, e, fifo=True)

        layers = _capas(db, company_id=mundo.company_a, product_id=e["prod"],
                        warehouse_id=mundo.warehouse_a)
        assert len(layers) == 1
        assert layers[0].quantity_remaining == Decimal("6.000000")
        assert _valoracion(db, mundo, e["prod"]) == Decimal("30.00")

        snap = _snapshot(db, shipment_id=str(sh.id))
        assert len(snap) == 1
        assert snap[0].method == "FIFO"
    finally:
        db.close()


def test_v5_landed_cost_con_promedio(mundo):
    db = mundo.factory()
    try:
        e = _hasta_facturado(db, mundo, cantidad=4, entradas=[(10, "5.00")])
        _emitir(db, mundo, e)
        sh = _despacho(db, mundo, e)
        sales.validate_shipment(db, shipment=sh, actor="despachador")

        layer = _capas(db, company_id=mundo.company_a, product_id=e["prod"],
                       warehouse_id=mundo.warehouse_a)[0]
        layer.landed_cost = Decimal("10.00")
        db.commit()

        sales.confirm_shipment(db, shipment=sh, actor="despachador")
        db.commit()

        layers = _capas(db, company_id=mundo.company_a, product_id=e["prod"],
                        warehouse_id=mundo.warehouse_a)
        assert float(layers[0].quantity_remaining) == 6.0
        assert _is_layer_consumed(layers[0]) is True
        assert _valoracion(db, mundo, e["prod"]) == Decimal("36.00")

        snap = _snapshot(db, shipment_id=str(sh.id))
        assert snap[0].total_cost == Decimal("24.000000")
    finally:
        db.close()


def test_v6_fifo_unidades_sin_costo(mundo):
    db = mundo.factory()
    try:
        e = _hasta_facturado(db, mundo, cantidad=5, entradas=[(3, "5.00"), (2, None)])
        _emitir(db, mundo, e)
        sh = _despacho(db, mundo, e)
        sales.validate_shipment(db, shipment=sh, actor="despachador")
        _activo_fifo(db, company_id=mundo.company_a, product_id=e["prod"])
        db.commit()
        sh_id = str(sh.id)

        with pytest.raises(ConflictError) as exc:
            sales.confirm_shipment(db, shipment=sh, actor="despachador")
        assert exc.value.code == "NO_COST_LAYER"
        db.rollback()

        sh2 = db.get(Shipment, sh_id)
        assert sh2.status == "READY"
        assert sh2.dispatched_at is None

        layers = _capas(db, company_id=mundo.company_a, product_id=e["prod"],
                        warehouse_id=mundo.warehouse_a)
        assert layers[0].quantity_remaining == Decimal("3.000000")
        assert layers[0].status == "OPEN"

        assert len(_snapshot(db, shipment_id=sh_id)) == 0

        reservas = inv.order_reservations(db, company_id=mundo.company_a,
                                          order_id=str(e["pedido"].id), only_active=False)
        assert all(r.status == "ACTIVE" for r in reservas)

        saldos = _saldos(db, mundo.company_a, e["prod"])
        assert saldos.get((e["area"], "PREPARADO")) == Decimal("5")
    finally:
        db.close()


def test_v7_promedio_unidades_sin_costo(mundo):
    db = mundo.factory()
    try:
        e = _hasta_facturado(db, mundo, cantidad=5, entradas=[(3, "5.00"), (2, None)])
        _emitir(db, mundo, e)
        sh = _despacho(db, mundo, e)
        sales.validate_shipment(db, shipment=sh, actor="despachador")
        db.commit()
        sh_id = str(sh.id)

        with pytest.raises(ConflictError) as exc:
            sales.confirm_shipment(db, shipment=sh, actor="despachador")
        assert exc.value.code == "NO_COST_LAYER"
        db.rollback()

        sh2 = db.get(Shipment, sh_id)
        assert sh2.status == "READY"
        assert sh2.dispatched_at is None

        layers = _capas(db, company_id=mundo.company_a, product_id=e["prod"],
                        warehouse_id=mundo.warehouse_a)
        assert layers[0].quantity_remaining == Decimal("3.000000")
        assert layers[0].status == "OPEN"

        assert len(_snapshot(db, shipment_id=sh_id)) == 0

        reservas = inv.order_reservations(db, company_id=mundo.company_a,
                                          order_id=str(e["pedido"].id), only_active=False)
        assert all(r.status == "ACTIVE" for r in reservas)

        saldos = _saldos(db, mundo.company_a, e["prod"])
        assert saldos.get((e["area"], "PREPARADO")) == Decimal("5")
    finally:
        db.close()


def test_v8_confirmacion_doble_y_concurrente(mundo):
    db = mundo.factory()
    try:
        e = _hasta_facturado(db, mundo, cantidad=4, entradas=[(10, "5.00")])
        sh = _preparar_y_confirmar(db, mundo, e)

        sales.confirm_shipment(db, shipment=sh, actor="despachador")
        db.commit()

        snap = _snapshot(db, shipment_id=str(sh.id))
        assert len(snap) == 1
        assert _valoracion(db, mundo, e["prod"]) == Decimal("30.00")

        e2 = _hasta_facturado(db, mundo, cantidad=4, entradas=[(10, "5.00")])
        _emitir(db, mundo, e2)
        sh2 = _despacho(db, mundo, e2)
        sales.validate_shipment(db, shipment=sh2, actor="despachador")
        db.commit()
        sh2_id = str(sh2.id)
    finally:
        db.close()

    exitos: list[int] = []
    choques: list[str] = []

    def _worker() -> None:
        s = mundo.factory()
        try:
            envio = s.get(Shipment, sh2_id)
            sales.confirm_shipment(s, shipment=envio, actor="despachador")
            s.commit()
            exitos.append(1)
        except Exception as exc:                                   # noqa: BLE001
            s.rollback()
            choques.append(type(exc).__name__)
        finally:
            s.close()

    hilos = [threading.Thread(target=_worker) for _ in range(2)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()

    db = mundo.factory()
    try:
        snap2 = _snapshot(db, shipment_id=sh2_id)
        assert len(snap2) == 1
        assert _valoracion(db, mundo, e2["prod"]) == Decimal("30.00")
        saldos = _saldos(db, mundo.company_a, e2["prod"])
        assert saldos.get((e2["area"], "DESPACHADO")) == Decimal("4")
    finally:
        db.close()


def test_v9_devolucion_dispone_costo(mundo):
    db = mundo.factory()
    try:
        e = _despachado(db, mundo, cantidad=4, entradas=[(10, "5.00")])
        assert _valoracion(db, mundo, e["prod"]) == Decimal("30.00")

        dev = _solicitar(db, mundo, e, base=2)
        sales.receive_return(db, company_id=mundo.company_a, return_id=str(dev.id),
                             location_id=e["devoluciones"], actor="almacenista")
        linea = sales._lineas_de_devolucion(db, str(dev.id))[0]
        sales.inspect_return(db, company_id=mundo.company_a, return_id=str(dev.id),
                             lines=[{"return_line_id": str(linea.id), "disposition": "DISPONIBLE",
                                     "accepted_base_quantity": 2}], actor="verificador")
        sales.decide_return(db, company_id=mundo.company_a, return_id=str(dev.id),
                            approved=True, actor="jefe")
        sales.reenter_return(db, company_id=mundo.company_a, return_id=str(dev.id), actor="almacenista")
        db.commit()

        layers = _capas(db, company_id=mundo.company_a, product_id=e["prod"],
                        warehouse_id=mundo.warehouse_a)
        capa = [x for x in layers if x.receipt_ref == f"SALES_RETURN:{dev.id}"]
        assert len(capa) == 1
        capa = capa[0]
        assert capa.quantity_remaining == Decimal("2.000000")
        assert Decimal(str(capa.unit_cost)).quantize(Decimal("0.01")) == Decimal("5.00")
        assert capa.currency == "VED"
        assert _valoracion(db, mundo, e["prod"]) == Decimal("40.00")
    finally:
        db.close()


def test_v9b_devolucion_rechazada_no_crea_capa(mundo):
    db = mundo.factory()
    try:
        e = _despachado(db, mundo, cantidad=4, entradas=[(10, "5.00")])
        assert _valoracion(db, mundo, e["prod"]) == Decimal("30.00")

        dev = _solicitar(db, mundo, e, base=2)
        sales.receive_return(db, company_id=mundo.company_a, return_id=str(dev.id),
                             location_id=e["devoluciones"], actor="almacenista")
        linea = sales._lineas_de_devolucion(db, str(dev.id))[0]
        sales.inspect_return(db, company_id=mundo.company_a, return_id=str(dev.id),
                             lines=[{"return_line_id": str(linea.id), "disposition": "RECHAZADO",
                                     "accepted_base_quantity": 0}], actor="verificador")
        sales.decide_return(db, company_id=mundo.company_a, return_id=str(dev.id),
                            approved=True, actor="jefe")
        sales.reenter_return(db, company_id=mundo.company_a, return_id=str(dev.id), actor="almacenista")
        db.commit()

        layers = _capas(db, company_id=mundo.company_a, product_id=e["prod"],
                        warehouse_id=mundo.warehouse_a)
        capa = [x for x in layers if x.receipt_ref == f"SALES_RETURN:{dev.id}"]
        assert len(capa) == 0
        assert _valoracion(db, mundo, e["prod"]) == Decimal("30.00")
    finally:
        db.close()


def test_aislamiento_almacen_y_compania(mundo):
    db = mundo.factory()
    try:
        e = _hasta_facturado(db, mundo, cantidad=4, entradas=[(10, "5.00")])
        w2 = Warehouse(company_id=mundo.company_a, code=f"W2-{uuid4().hex[:6]}",
                       name="Segundo", status="ACTIVE")
        db.add(w2)
        db.flush()
        inv.record_movement(db, company_id=mundo.company_a, warehouse_id=str(w2.id),
                            product_id=e["prod"],
                            movement_type_id=str(inv._get_movement_type_by_code(
                                db, mundo.company_a, "ENTRADA_RECEPCION").id),
                            quantity=5, unit_cost=Decimal("9.00"), currency="VED", actor="qa")
        db.commit()

        sh = _preparar_y_confirmar(db, mundo, e)

        layers_w2 = _capas(db, company_id=mundo.company_a, product_id=e["prod"],
                           warehouse_id=str(w2.id))
        assert [float(capa.quantity_remaining) for capa in layers_w2] == [5.0]

        snap = _snapshot(db, shipment_id=str(sh.id))
        assert all(s.warehouse_id == mundo.warehouse_a for s in snap)
        assert all(s.company_id == mundo.company_a for s in snap)

        assert _valoracion(db, mundo, e["prod"]) == Decimal("30.00")
        assert Decimal(str(inv.valuation(db, company_id=mundo.company_b, product_id=e["prod"]))) == Decimal("0")
    finally:
        db.close()
