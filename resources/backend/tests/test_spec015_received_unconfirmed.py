# ruff: noqa: E402, F811, F401, I001

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.inventory.models import InventoryBalance, InventoryMovement
from app.modules.master_data.models import Party, Supplier
from app.modules.organization.models import Company, Warehouse
from app.modules.planning.engine import compute_plan
from app.modules.planning.models import ReplenishmentNeed
from app.modules.planning.replenishment import evaluate_replenishment_needs
from app.modules.purchasing import open_supply
from app.modules.purchasing import service as ap_service
from app.modules.purchasing.models import (
    GoodsReceipt,
    GoodsReceiptLine,
    PurchaseOrder,
    PurchaseOrderLine,
)
from test_importaciones_seguimiento import _operador
from test_planning_replenishment import (
    _almacen,
    _crear_rol,
    _entrada,
    _necesidades_activas,
    _politica,
    _producto,
    _salida,
    mundo,
)
from test_spec015_open_supply import _abierto, _hex, _orden, _proveedor

pytest_plugins = ["mfa_apoyo"]

API = "/api/v1"


def _recibir(mundo, order_id, line_id, product_id, warehouse_id, received, accepted, rejected):
    db: Session = mundo.factory()
    try:
        receipt = ap_service.create_receipt(
            db,
            company_id=mundo.company_id,
            code=f"RC-{_hex()}",
            order_id=order_id,
            warehouse_id=warehouse_id,
        )
        receipt_line = ap_service.add_receipt_line(
            db,
            company_id=mundo.company_id,
            receipt_id=str(receipt.id),
            order_line_id=line_id,
            product_id=product_id,
            quantity_received=received,
            quantity_accepted=accepted,
            quantity_rejected=rejected,
        )
        ap_service.confirm_receipt(db, receipt=receipt)
        ap_service.enviar_a_calidad(db, receipt=receipt)
        receipt.quality_status = "APPROVED"
        db.flush()
        ap_service.accept_receipt(db, receipt=receipt)
        db.commit()
        return str(receipt.id), str(receipt_line.id)
    finally:
        db.close()


def _confirmar(mundo, receipt_id, decisiones):
    db: Session = mundo.factory()
    try:
        receipt = db.get(GoodsReceipt, receipt_id)
        lineas_distintas = {}
        for line_id, _target_state, _cantidad in decisiones:
            lineas_distintas[line_id] = line_id

        for line_id in lineas_distintas:
            line = db.get(GoodsReceiptLine, line_id)
            ap_service.registrar_conteo(
                db,
                receipt=receipt,
                line_id=line_id,
                counted_base_quantity=line.base_quantity_received
                if line.base_quantity_received is not None
                else line.quantity_received,
                difference_kinds=[],
            )

        ap_service.confirmar_inventario(
            db,
            receipt=receipt,
            decisiones=[
                {
                    "receipt_line_id": line_id,
                    "target_state": target_state,
                    "base_quantity": str(cantidad),
                    **(
                        {"reason": "No apto en la prueba"}
                        if target_state == "RECHAZADO"
                        else {}
                    ),
                }
                for line_id, target_state, cantidad in decisiones
            ],
        )
        db.commit()
    finally:
        db.close()


def _sin_confirmar(mundo, wh, prod):
    db: Session = mundo.factory()
    try:
        return open_supply.recibido_sin_confirmar(
            db,
            company_id=mundo.company_id,
            warehouse_id=wh,
            product_ids=[prod],
        )[prod]
    finally:
        db.close()


def _plan(mundo, wh, prod):
    db: Session = mundo.factory()
    try:
        return compute_plan(
            db,
            company_id=mundo.company_id,
            warehouse_id=wh,
            product_id=prod,
        )
    finally:
        db.close()


def _en_camino(mundo, wh, prod):
    db: Session = mundo.factory()
    try:
        return open_supply.en_camino(
            db,
            company_id=mundo.company_id,
            warehouse_id=wh,
            product_ids=[prod],
        )[prod]
    finally:
        db.close()


def test_secuencia_100_40_30_con_confirmaciones(mundo):
    wh = _almacen(mundo)
    prod = _producto(mundo)
    supplier_id = _proveedor(mundo)
    order_id, [line_id] = _orden(mundo, supplier_id, [(prod, 100, wh, True)])

    def _comprobar(available, open_supply, received):
        expected_available = f"{available}.000000"
        expected_open = f"{open_supply}.000000"
        expected_received = f"{received}.000000"

        plan = _plan(mundo, wh, prod)
        assert plan["available"] == expected_available
        assert plan["open_supply"] == expected_open
        assert plan["received_unconfirmed"] == expected_received
        assert Decimal(plan["projected_available"]) == (
            Decimal(plan["available"])
            + Decimal(plan["open_supply"])
            + Decimal(plan["received_unconfirmed"])
        )

        en_camino_value = _en_camino(mundo, wh, prod)
        assert en_camino_value.open_supply == Decimal(plan["open_supply"])
        assert en_camino_value.received_unconfirmed == Decimal(plan["received_unconfirmed"])
        assert _abierto(mundo, wh, prod) == Decimal(plan["open_supply"])
        assert _sin_confirmar(mundo, wh, prod) == Decimal(plan["received_unconfirmed"])

    _comprobar(0, 100, 0)
    r1, l1 = _recibir(mundo, order_id, line_id, prod, wh, 40, 40, 0)
    _comprobar(0, 60, 40)

    _confirmar(mundo, r1, [(l1, "DISPONIBLE", Decimal("40"))])
    _comprobar(40, 60, 0)

    r2, l2 = _recibir(mundo, order_id, line_id, prod, wh, 30, 30, 0)
    _comprobar(40, 30, 30)

    _confirmar(mundo, r2, [(l2, "DISPONIBLE", Decimal("30"))])
    _comprobar(70, 30, 0)


def test_aceptacion_parcial_rechazado_no_cuenta(mundo):
    wh = _almacen(mundo)
    prod = _producto(mundo)
    supplier_id = _proveedor(mundo)
    order_id, [line_id] = _orden(mundo, supplier_id, [(prod, 100, wh, True)])
    _recibir(mundo, order_id, line_id, prod, wh, 100, 80, 20)

    plan = _plan(mundo, wh, prod)
    assert plan["available"] == "0.000000"
    assert plan["open_supply"] == "20.000000"
    assert plan["received_unconfirmed"] == "80.000000"
    assert _sin_confirmar(mundo, wh, prod) == Decimal("80")
    assert _abierto(mundo, wh, prod) == Decimal("20")


def test_confirmacion_con_rechazo(mundo):
    wh = _almacen(mundo)
    prod = _producto(mundo)
    supplier_id = _proveedor(mundo)
    order_id, [line_id] = _orden(mundo, supplier_id, [(prod, 100, wh, True)])
    receipt_id, receipt_line_id = _recibir(mundo, order_id, line_id, prod, wh, 60, 60, 0)
    _confirmar(
        mundo,
        receipt_id,
        [
            (receipt_line_id, "DISPONIBLE", Decimal("40")),
            (receipt_line_id, "RECHAZADO", Decimal("20")),
        ],
    )

    plan = _plan(mundo, wh, prod)
    assert plan["available"] == "40.000000"
    assert plan["open_supply"] == "40.000000"
    assert plan["received_unconfirmed"] == "0.000000"


def test_confirmacion_que_no_decide_todo_no_queda_pendiente(mundo):
    wh = _almacen(mundo)
    prod = _producto(mundo)
    supplier_id = _proveedor(mundo)
    order_id, [line_id] = _orden(mundo, supplier_id, [(prod, 100, wh, True)])
    receipt_id, receipt_line_id = _recibir(mundo, order_id, line_id, prod, wh, 60, 60, 0)
    _confirmar(mundo, receipt_id, [(receipt_line_id, "DISPONIBLE", Decimal("40"))])

    plan = _plan(mundo, wh, prod)
    assert plan["available"] == "40.000000"
    assert plan["open_supply"] == "40.000000"
    assert plan["received_unconfirmed"] == "0.000000"


def test_estados_que_no_cuentan(mundo):
    wh = _almacen(mundo)
    prod = _producto(mundo)
    supplier_id = _proveedor(mundo)

    order_id, [line_id] = _orden(mundo, supplier_id, [(prod, 20, wh, True)])
    db: Session = mundo.factory()
    try:
        receipt = ap_service.create_receipt(
            db,
            company_id=mundo.company_id,
            code=f"RC-{_hex()}",
            order_id=order_id,
            warehouse_id=wh,
        )
        ap_service.add_receipt_line(
            db,
            company_id=mundo.company_id,
            receipt_id=str(receipt.id),
            order_line_id=line_id,
            product_id=prod,
            quantity_received=5,
            quantity_accepted=5,
            quantity_rejected=0.0,
        )
        ap_service.confirm_receipt(db, receipt=receipt)
        ap_service.enviar_a_calidad(db, receipt=receipt)
        db.commit()
    finally:
        db.close()
    assert _sin_confirmar(mundo, wh, prod) == Decimal("0")
    assert _abierto(mundo, wh, prod) == Decimal("20")

    order_id_ni, [line_id_ni] = _orden(mundo, supplier_id, [(prod, 10, wh, False)])
    _recibir(mundo, order_id_ni, line_id_ni, prod, wh, 10, 10, 0)
    assert _sin_confirmar(mundo, wh, prod) == Decimal("0")
    assert _abierto(mundo, wh, prod) == Decimal("20")


def test_varios_almacenes(mundo):
    wh_a = _almacen(mundo)
    wh_b = _almacen(mundo)
    prod = _producto(mundo)
    supplier_id = _proveedor(mundo)
    order_id, [line_a_id, line_b_id] = _orden(
        mundo,
        supplier_id,
        [
            (prod, 50, wh_a, True),
            (prod, 80, wh_b, True),
        ],
    )
    _recibir(mundo, order_id, line_a_id, prod, wh_a, 30, 30, 0)

    assert _sin_confirmar(mundo, wh_a, prod) == Decimal("30")
    assert _sin_confirmar(mundo, wh_b, prod) == Decimal("0")

    plan_b = _plan(mundo, wh_b, prod)
    assert plan_b["open_supply"] == "80.000000"
    assert plan_b["received_unconfirmed"] == "0.000000"


def test_aislamiento(mundo):
    wh = _almacen(mundo)
    prod = _producto(mundo)

    db: Session = mundo.factory()
    try:
        company_otra = db.scalars(
            select(Company).where(Company.tenant_id == mundo.tenant_b_id)
        ).first()
        party = Party(
            company_id=str(company_otra.id),
            code=f"SUP-{_hex()}",
            name="Proveedor Aislado",
            person_type="JURIDICA",
            tax_id=f"J-{uuid.uuid4().hex[:8]}-1",
            roles=["PROVEEDOR"],
            status="ACTIVE",
        )
        db.add(party)
        db.flush()
        supplier = Supplier(party_id=str(party.id), approval_status="APPROVED")
        db.add(supplier)
        db.flush()

        order = PurchaseOrder(
            company_id=str(company_otra.id),
            code=f"OC-{_hex()}",
            supplier_id=str(supplier.party_id),
            status="APPROVED",
            currency="VED",
        )
        db.add(order)
        db.flush()
        order_line = PurchaseOrderLine(
            order_id=str(order.id),
            product_id=prod,
            quantity_ordered=Decimal("9"),
            base_quantity_ordered=Decimal("9"),
            quantity_received=Decimal("0"),
            unit_price=Decimal("1"),
            needs_inventory=True,
            destination_warehouse_id=wh,
        )
        db.add(order_line)
        db.flush()
        receipt = GoodsReceipt(
            company_id=str(company_otra.id),
            order_id=str(order.id),
            warehouse_id=wh,
            status="ACCEPTED",
            code=f"RC-{_hex()}",
        )
        db.add(receipt)
        db.flush()
        goods_receipt_line = GoodsReceiptLine(
            receipt_id=str(receipt.id),
            order_line_id=str(order_line.id),
            product_id=prod,
            quantity_received=Decimal("9"),
            quantity_accepted=Decimal("9"),
            quantity_rejected=Decimal("0"),
            base_quantity_received=Decimal("9"),
            base_quantity_accepted=Decimal("9"),
            base_quantity_rejected=Decimal("0"),
        )
        db.add(goods_receipt_line)
        db.commit()

        assert _sin_confirmar(mundo, wh, prod) == Decimal("0")
    finally:
        db.close()


def test_planificacion_no_repone_lo_recibido(mundo):
    wh = _almacen(mundo)
    prod = _producto(mundo)
    _politica(
        mundo,
        wh,
        {
            "auto_replenishment_enabled": True,
            "safety_mode": "NONE",
            "safety_value": "0",
            "demand_source": "INVENTORY_ISSUES",
        },
    )
    _entrada(mundo, wh, prod, 12, 8)
    _salida(mundo, wh, prod, 10, 2)

    evaluate_replenishment_needs(mundo.factory, now=datetime.now(UTC))
    assert len(_necesidades_activas(mundo, wh, prod)) == 1

    supplier_id = _proveedor(mundo)
    order_id, [line_id] = _orden(mundo, supplier_id, [(prod, 5, wh, True)])
    receipt_id, receipt_line_id = _recibir(mundo, order_id, line_id, prod, wh, 5, 5, 0)

    plan = _plan(mundo, wh, prod)
    assert plan["open_supply"] == "0.000000"
    assert plan["received_unconfirmed"] == "5.000000"
    assert plan["projected_available"] == "7.000000"
    assert plan["recommended_quantity"] == "0.000000"

    evaluate_replenishment_needs(mundo.factory, now=datetime.now(UTC))
    assert len(_necesidades_activas(mundo, wh, prod)) == 0

    _confirmar(mundo, receipt_id, [(receipt_line_id, "DISPONIBLE", Decimal("5"))])

    plan = _plan(mundo, wh, prod)
    assert plan["available"] == "7.000000"
    assert plan["received_unconfirmed"] == "0.000000"
    assert plan["projected_available"] == "7.000000"

    evaluate_replenishment_needs(mundo.factory, now=datetime.now(UTC))
    assert len(_necesidades_activas(mundo, wh, prod)) == 0

    db = mundo.factory()
    try:
        total_necesidades = db.scalar(
            select(func.count(ReplenishmentNeed.id)).where(
                ReplenishmentNeed.company_id == mundo.company_id,
                ReplenishmentNeed.warehouse_id == wh,
                ReplenishmentNeed.product_id == prod,
            )
        )
        assert total_necesidades == 1
    finally:
        db.close()


def test_sin_efecto_en_inventario(mundo):
    wh = _almacen(mundo)
    prod = _producto(mundo)
    supplier_id = _proveedor(mundo)
    order_id, [line_id] = _orden(mundo, supplier_id, [(prod, 10, wh, True)])
    _recibir(mundo, order_id, line_id, prod, wh, 10, 10, 0)

    def _contar():
        db: Session = mundo.factory()
        try:
            movimientos = db.scalar(
                select(func.count(InventoryMovement.id)).where(
                    InventoryMovement.company_id == mundo.company_id
                )
            )
            saldos = db.scalar(
                select(func.count(InventoryBalance.id)).where(
                    InventoryBalance.company_id == mundo.company_id
                )
            )
            return movimientos, saldos
        finally:
            db.close()

    movimientos_antes, saldos_antes = _contar()

    _plan(mundo, wh, prod)
    _sin_confirmar(mundo, wh, prod)
    _en_camino(mundo, wh, prod)
    evaluate_replenishment_needs(mundo.factory, now=datetime.now(UTC))

    movimientos_despues, saldos_despues = _contar()
    assert movimientos_despues == movimientos_antes
    assert saldos_despues == saldos_antes


def test_detalle_de_necesidad_expone_recibido(mundo, reloj_mfa):
    wh = _almacen(mundo)
    prod = _producto(mundo)
    _politica(
        mundo,
        wh,
        {
            "auto_replenishment_enabled": True,
            "safety_mode": "NONE",
            "safety_value": "0",
            "demand_source": "INVENTORY_ISSUES",
        },
    )
    _entrada(mundo, wh, prod, 12, 8)
    _salida(mundo, wh, prod, 10, 2)

    supplier_id = _proveedor(mundo)
    order_id, [line_id] = _orden(mundo, supplier_id, [(prod, 1, wh, True)])
    _recibir(mundo, order_id, line_id, prod, wh, 1, 1, 0)

    evaluate_replenishment_needs(mundo.factory, now=datetime.now(UTC))
    activas = _necesidades_activas(mundo, wh, prod)
    assert len(activas) == 1

    need_id = str(activas[0].id)
    headers = _operador(mundo, reloj_mfa, _crear_rol(mundo, ["compras:view"]))
    resp = mundo.client.get(f"{API}/planning/replenishment-needs/{need_id}", headers=headers)
    assert resp.status_code == 200
    payload = resp.json()

    assert payload["trigger"]["received_unconfirmed"] == "1.000000"
    assert payload["trigger"]["projected_available"] == "3.000000"
    assert payload["trigger"]["available"] == "2.000000"
    assert payload["trigger"]["open_supply"] == "0.000000"
    assert payload["current"]["received_unconfirmed"] == "1.000000"
