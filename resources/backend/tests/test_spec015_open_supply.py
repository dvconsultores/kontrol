# ruff: noqa: E402, F811, F401, I001

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.modules.audit.models import AuditEvent
from app.modules.inventory.models import InventoryBalance, InventoryMovement
from app.modules.master_data.models import Party, Supplier
from app.modules.organization.models import Company, Warehouse
from app.modules.planning.engine import compute_plan
from app.modules.planning.models import ReplenishmentNeed
from app.modules.planning.replenishment import evaluate_replenishment_needs
from app.modules.purchasing import open_supply
from app.modules.purchasing import service as ap_service
from app.modules.purchasing.models import GoodsReceipt, PurchaseOrder, PurchaseOrderLine
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

pytest_plugins = ["mfa_apoyo"]

API = "/api/v1"


def _hex():
    return uuid.uuid4().hex[:8]


def _proveedor(mundo):
    db: Session = mundo.factory()
    try:
        party = Party(
            company_id=mundo.company_id,
            code=f"SUP-{_hex()}",
            name="Proveedor OSW",
            person_type="JURIDICA",
            tax_id=f"J-{uuid.uuid4().hex[:8]}-1",
            roles=["PROVEEDOR"],
            status="ACTIVE",
        )
        db.add(party)
        db.flush()
        supplier = Supplier(party_id=str(party.id), approval_status="APPROVED")
        db.add(supplier)
        db.commit()
        return str(party.id)
    finally:
        db.close()


def _orden(mundo, supplier_id, lines, status="APPROVED"):
    db: Session = mundo.factory()
    try:
        order = ap_service.create_order(
            db,
            company_id=mundo.company_id,
            code=f"OC-{_hex()}",
            supplier_id=supplier_id,
        )
        line_ids = []
        for product_id, qty, destination, needs_inventory in lines:
            line = ap_service.add_order_line(
                db,
                order_id=str(order.id),
                product_id=product_id,
                quantity_ordered=qty,
                unit_price=1.0,
                needs_inventory=needs_inventory,
                destination_warehouse_id=destination,
            )
            line_ids.append(str(line.id))

        order = db.get(PurchaseOrder, order.id)
        if status in ("SUBMITTED", "APPROVED"):
            ap_service.transition_order(db, order=order, target="SUBMITTED")
        if status == "APPROVED":
            order = db.get(PurchaseOrder, order.id)
            ap_service.transition_order(db, order=order, target="APPROVED")

        db.commit()
        return str(order.id), line_ids
    finally:
        db.close()


def _recibir(mundo, order_id, line_id, product_id, warehouse_id, accepted):
    db: Session = mundo.factory()
    try:
        receipt = ap_service.create_receipt(
            db,
            company_id=mundo.company_id,
            code=f"RC-{_hex()}",
            order_id=order_id,
            warehouse_id=warehouse_id,
        )
        ap_service.add_receipt_line(
            db,
            company_id=mundo.company_id,
            receipt_id=str(receipt.id),
            order_line_id=line_id,
            product_id=product_id,
            quantity_received=accepted,
            quantity_accepted=accepted,
            quantity_rejected=0.0,
        )
        ap_service.confirm_receipt(db, receipt=receipt)
        ap_service.enviar_a_calidad(db, receipt=receipt)
        receipt.quality_status = "APPROVED"
        db.flush()
        ap_service.accept_receipt(db, receipt=receipt)
        db.commit()
    finally:
        db.close()


def _abierto(mundo, warehouse_id, product_id):
    db: Session = mundo.factory()
    try:
        return open_supply.suministro_abierto(
            db,
            company_id=mundo.company_id,
            warehouse_id=warehouse_id,
            product_ids=[product_id],
        )[product_id]
    finally:
        db.close()


def test_parcial_100_40_30_cierre(mundo, reloj_mfa):
    db: Session = mundo.factory()
    try:
        wh = _almacen(mundo)
        prod = _producto(mundo)
        supplier_id = _proveedor(mundo)
        order_id, [line_id] = _orden(mundo, supplier_id, [(prod, 100, wh, True)])

        line = db.get(PurchaseOrderLine, line_id)
        order = db.get(PurchaseOrder, order_id)
        assert _abierto(mundo, wh, prod) == Decimal("100")
        assert open_supply.cantidad_abierta(line, order.status) == Decimal("100")

        headers = _operador(mundo, reloj_mfa, _crear_rol(mundo, ["compras:view", "compras:create"]))
        resp = mundo.client.get(f"{API}/purchasing/orders/{order_id}", headers=headers)
        assert resp.status_code == 200
        assert Decimal(resp.json()["lines"][0]["open_quantity"]) == Decimal("100")
        assert resp.json()["lines"][0]["destination_warehouse"]["code"] == db.get(Warehouse, wh).code

        _recibir(mundo, order_id, line_id, prod, wh, 40)
        db.expire_all()
        line = db.get(PurchaseOrderLine, line_id)
        order = db.get(PurchaseOrder, order_id)
        assert _abierto(mundo, wh, prod) == Decimal("60")
        assert open_supply.cantidad_abierta(line, order.status) == Decimal("60")

        _recibir(mundo, order_id, line_id, prod, wh, 30)
        db.expire_all()
        line = db.get(PurchaseOrderLine, line_id)
        order = db.get(PurchaseOrder, order_id)
        assert _abierto(mundo, wh, prod) == Decimal("30")
        assert open_supply.cantidad_abierta(line, order.status) == Decimal("30")

        order = db.get(PurchaseOrder, order_id)
        ap_service.transition_order(db, order=order, target="CLOSED")
        db.commit()
        db.expire_all()
        line = db.get(PurchaseOrderLine, line_id)
        order = db.get(PurchaseOrder, order_id)
        assert _abierto(mundo, wh, prod) == Decimal("0")
        assert open_supply.cantidad_abierta(line, order.status) == Decimal("0")
    finally:
        db.close()


def test_estados_y_lineas_que_no_cuentan(mundo):
    wh = _almacen(mundo)
    prod = _producto(mundo)
    supplier_id = _proveedor(mundo)

    _orden(mundo, supplier_id, [(prod, 10, wh, True)], status="DRAFT")
    assert _abierto(mundo, wh, prod) == Decimal("0")

    _orden(mundo, supplier_id, [(prod, 10, wh, True)], status="SUBMITTED")
    assert _abierto(mundo, wh, prod) == Decimal("0")

    order_id, _ = _orden(mundo, supplier_id, [(prod, 10, wh, True)])
    db: Session = mundo.factory()
    try:
        order = db.get(PurchaseOrder, order_id)
        ap_service.transition_order(db, order=order, target="CANCELLED")
        db.commit()
    finally:
        db.close()
    assert _abierto(mundo, wh, prod) == Decimal("0")

    _orden(mundo, supplier_id, [(prod, 10, wh, False)])
    assert _abierto(mundo, wh, prod) == Decimal("0")

    _orden(mundo, supplier_id, [(prod, 10, None, True)])
    assert _abierto(mundo, wh, prod) == Decimal("0")


def test_varios_almacenes(mundo):
    wh_a = _almacen(mundo)
    wh_b = _almacen(mundo)
    prod = _producto(mundo)
    supplier_id = _proveedor(mundo)
    _orden(mundo, supplier_id, [(prod, 50, wh_a, True), (prod, 80, wh_b, True)])

    assert _abierto(mundo, wh_a, prod) == Decimal("50")
    assert _abierto(mundo, wh_b, prod) == Decimal("80")

    db: Session = mundo.factory()
    try:
        plan_a = compute_plan(db, company_id=mundo.company_id, warehouse_id=wh_a, product_id=prod)
        plan_b = compute_plan(db, company_id=mundo.company_id, warehouse_id=wh_b, product_id=prod)
        assert plan_a["open_supply"] == "50.000000"
        assert plan_b["open_supply"] == "80.000000"
    finally:
        db.close()


def test_planificacion_descuenta_y_no_duplica(mundo):
    wh = _almacen(mundo)
    prod = _producto(mundo)
    _politica(mundo, wh, {"auto_replenishment_enabled": True, "safety_mode": "NONE", "safety_value": "0", "demand_source": "INVENTORY_ISSUES"})
    _entrada(mundo, wh, prod, 12, 8)
    _salida(mundo, wh, prod, 10, 2)

    db: Session = mundo.factory()
    try:
        evaluate_replenishment_needs(mundo.factory, now=datetime.now(UTC))
        needs = _necesidades_activas(mundo, wh, prod)
        assert len(needs) == 1
        assert needs[0].trigger_open_supply == Decimal("0")
        assert needs[0].trigger_projected_available == Decimal("2")

        supplier_id = _proveedor(mundo)
        _orden(mundo, supplier_id, [(prod, 5, wh, True)])

        evaluate_replenishment_needs(mundo.factory, now=datetime.now(UTC))
        all_needs = db.execute(
            select(ReplenishmentNeed)
            .where(
                ReplenishmentNeed.warehouse_id == wh,
                ReplenishmentNeed.product_id == prod,
            )
        ).scalars().all()
        assert len(all_needs) == 1
        assert all_needs[0].status == "RESOLVED"
        assert all_needs[0].resolution_reason == "CONDITION_CLEARED"
        assert all_needs[0].current_open_supply == Decimal("5")
        assert all_needs[0].current_projected_available == Decimal("7")

        evaluate_replenishment_needs(mundo.factory, now=datetime.now(UTC))
        assert len(_necesidades_activas(mundo, wh, prod)) == 0

        plan = compute_plan(db, company_id=mundo.company_id, warehouse_id=wh, product_id=prod)
        assert plan["open_supply"] == "5.000000"
        assert plan["projected_available"] == "7.000000"
        assert plan["recommended_quantity"] == "0.000000"
    finally:
        db.close()


def test_sin_efecto_en_inventario(mundo):
    db: Session = mundo.factory()
    try:
        movements_before = db.scalar(select(func.count()).select_from(InventoryMovement).where(InventoryMovement.company_id == mundo.company_id))
        balances_before = db.scalar(select(func.count()).select_from(InventoryBalance).where(InventoryBalance.company_id == mundo.company_id))
        receipts_before = db.scalar(select(func.count()).select_from(GoodsReceipt).where(GoodsReceipt.company_id == mundo.company_id))

        wh = _almacen(mundo)
        prod = _producto(mundo)
        supplier_id = _proveedor(mundo)
        _orden(mundo, supplier_id, [(prod, 5, wh, True)])
        db.expire_all()
        compute_plan(db, company_id=mundo.company_id, warehouse_id=wh, product_id=prod)
        evaluate_replenishment_needs(mundo.factory, now=datetime.now(UTC))

        draft_order_id, [draft_line_id] = _orden(mundo, supplier_id, [(prod, 5, None, True)], status="DRAFT")
        ap_service.fijar_destino_de_linea(
            db,
            company_id=mundo.company_id,
            order_id=draft_order_id,
            line_id=draft_line_id,
            warehouse_id=wh,
        )
        db.commit()

        movements_after = db.scalar(select(func.count()).select_from(InventoryMovement).where(InventoryMovement.company_id == mundo.company_id))
        balances_after = db.scalar(select(func.count()).select_from(InventoryBalance).where(InventoryBalance.company_id == mundo.company_id))
        receipts_after = db.scalar(select(func.count()).select_from(GoodsReceipt).where(GoodsReceipt.company_id == mundo.company_id))

        assert movements_after == movements_before
        assert balances_after == balances_before
        assert receipts_after == receipts_before
    finally:
        db.close()


def test_recepcion_en_otro_almacen_bloqueada(mundo):
    wh_a = _almacen(mundo)
    wh_b = _almacen(mundo)
    prod = _producto(mundo)
    supplier_id = _proveedor(mundo)
    order_id, [line_id] = _orden(mundo, supplier_id, [(prod, 5, wh_a, True)])

    db: Session = mundo.factory()
    try:
        receipt = ap_service.create_receipt(db, company_id=mundo.company_id, code=f"RC-{_hex()}", order_id=order_id, warehouse_id=wh_b)
        with pytest.raises(ConflictError) as exc_info:
            ap_service.add_receipt_line(
                db,
                company_id=mundo.company_id,
                receipt_id=str(receipt.id),
                order_line_id=line_id,
                product_id=prod,
                quantity_received=1,
                quantity_accepted=1,
                quantity_rejected=0,
            )
        assert exc_info.value.code == "RECEIPT_LINE_OTHER_WAREHOUSE"
        db.rollback()

        receipt_ok = ap_service.create_receipt(db, company_id=mundo.company_id, code=f"RC-{_hex()}", order_id=order_id, warehouse_id=wh_a)
        ap_service.add_receipt_line(
            db,
            company_id=mundo.company_id,
            receipt_id=str(receipt_ok.id),
            order_line_id=line_id,
            product_id=prod,
            quantity_received=1,
            quantity_accepted=1,
            quantity_rejected=0,
        )
        db.flush()
        db.commit()

        order_id, [line_id_sin_destino] = _orden(mundo, supplier_id, [(prod, 3, None, True)])
        receipt_b = ap_service.create_receipt(db, company_id=mundo.company_id, code=f"RC-{_hex()}", order_id=order_id, warehouse_id=wh_b)
        ap_service.add_receipt_line(
            db,
            company_id=mundo.company_id,
            receipt_id=str(receipt_b.id),
            order_line_id=line_id_sin_destino,
            product_id=prod,
            quantity_received=1,
            quantity_accepted=1,
            quantity_rejected=0,
        )
        db.flush()
        db.commit()
    finally:
        db.close()


def test_api_fijar_destino(mundo, reloj_mfa):
    db: Session = mundo.factory()
    try:
        wh_a = _almacen(mundo)
        wh_b = _almacen(mundo)
        prod = _producto(mundo)
        supplier_id = _proveedor(mundo)
        order_id, [line_id] = _orden(mundo, supplier_id, [(prod, 5, None, True)], status="DRAFT")

        headers = _operador(mundo, reloj_mfa, _crear_rol(mundo, ["compras:view", "compras:create"]))
        resp = mundo.client.post(
            f"{API}/purchasing/orders/{order_id}/lines/{line_id}/destination",
            json={"warehouse_id": wh_a},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["lines"][0]["destination_warehouse"]["code"] == db.get(Warehouse, wh_a).code
        assert resp.json()["lines"][0]["can_set_destination"] is True

        resp = mundo.client.post(
            f"{API}/purchasing/orders/{order_id}/lines/{line_id}/destination",
            json={"warehouse_id": wh_b},
            headers=headers,
        )
        assert resp.status_code == 200

        audit = db.execute(
            select(AuditEvent)
            .where(
                AuditEvent.action == "PURCHASE_ORDER_LINE_DESTINATION_SET",
                AuditEvent.entity_id == line_id,
            )
            .order_by(AuditEvent.created_at.desc())
        ).scalars().first()
        assert audit.before["destination_warehouse_code"] == db.get(Warehouse, wh_a).code
        assert audit.after["destination_warehouse_code"] == db.get(Warehouse, wh_b).code

        audit_count_before = db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.action == "PURCHASE_ORDER_LINE_DESTINATION_SET", AuditEvent.entity_id == line_id))
        resp = mundo.client.post(
            f"{API}/purchasing/orders/{order_id}/lines/{line_id}/destination",
            json={"warehouse_id": wh_b},
            headers=headers,
        )
        assert resp.status_code == 200
        audit_count_after = db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.action == "PURCHASE_ORDER_LINE_DESTINATION_SET", AuditEvent.entity_id == line_id))
        assert audit_count_after == audit_count_before

        other_company_id = db.scalar(select(Company.id).where(Company.tenant_id == mundo.tenant_b_id))
        wh_other = _almacen(mundo, company_id=other_company_id)
        with pytest.raises(NotFoundError) as exc_info:
            ap_service.fijar_destino_de_linea(
                db,
                company_id=mundo.company_id,
                order_id=order_id,
                line_id=line_id,
                warehouse_id=wh_other,
            )
        assert exc_info.value.code == "WAREHOUSE_NOT_FOUND"
        db.rollback()

        wh_inactive = _almacen(mundo)
        db.get(Warehouse, wh_inactive).status = "INACTIVE"
        db.commit()
        with pytest.raises(ConflictError) as exc_info:
            ap_service.fijar_destino_de_linea(
                db,
                company_id=mundo.company_id,
                order_id=order_id,
                line_id=line_id,
                warehouse_id=wh_inactive,
            )
        assert exc_info.value.code == "WAREHOUSE_NOT_ELIGIBLE"
        db.rollback()

        order = db.get(PurchaseOrder, order_id)
        ap_service.transition_order(db, order=order, target="SUBMITTED")
        ap_service.transition_order(db, order=db.get(PurchaseOrder, order_id), target="APPROVED")
        db.commit()
        receipt = ap_service.create_receipt(db, company_id=mundo.company_id, code=f"RC-{_hex()}", order_id=order_id, warehouse_id=wh_b)
        ap_service.add_receipt_line(
            db,
            company_id=mundo.company_id,
            receipt_id=str(receipt.id),
            order_line_id=line_id,
            product_id=prod,
            quantity_received=1,
            quantity_accepted=1,
            quantity_rejected=0,
        )
        db.flush()
        db.commit()
        with pytest.raises(ConflictError) as exc_info:
            ap_service.fijar_destino_de_linea(
                db,
                company_id=mundo.company_id,
                order_id=order_id,
                line_id=line_id,
                warehouse_id=wh_a,
            )
        assert exc_info.value.code == "ORDER_LINE_DESTINATION_LOCKED"
        db.rollback()

        order2, [line2] = _orden(mundo, supplier_id, [(prod, 7, None, True)], status="DRAFT")
        resp = mundo.client.post(
            f"{API}/purchasing/orders/{order2}/lines",
            json={
                "product_id": prod,
                "quantity_ordered": 7,
                "unit_price": 1.0,
                "needs_inventory": True,
                "destination_warehouse_id": wh_a,
            },
            headers=headers,
        )
        assert resp.status_code == 200
        resp = mundo.client.get(f"{API}/purchasing/orders/{order2}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["lines"][-1]["destination_warehouse"]["code"] == db.get(Warehouse, wh_a).code

        view_headers = _operador(mundo, reloj_mfa, _crear_rol(mundo, ["compras:view"]))
        resp = mundo.client.post(
            f"{API}/purchasing/orders/{order2}/lines/{line2}/destination",
            json={"warehouse_id": wh_b},
            headers=view_headers,
        )
        assert resp.status_code == 403

        # Casos HTTP 404/409 del contrato T7.
        resp = mundo.client.post(
            f"{API}/purchasing/orders/{order2}/lines/{line2}/destination",
            json={"warehouse_id": wh_other},
            headers=headers,
        )
        assert resp.status_code == 404
        assert resp.json()["code"] == "WAREHOUSE_NOT_FOUND"

        resp = mundo.client.post(
            f"{API}/purchasing/orders/{order2}/lines/{line2}/destination",
            json={"warehouse_id": wh_inactive},
            headers=headers,
        )
        assert resp.status_code == 409
        assert resp.json()["code"] == "WAREHOUSE_NOT_ELIGIBLE"

        resp = mundo.client.post(
            f"{API}/purchasing/orders/{order_id}/lines/{line_id}/destination",
            json={"warehouse_id": wh_a},
            headers=headers,
        )
        assert resp.status_code == 409
        assert resp.json()["code"] == "ORDER_LINE_DESTINATION_LOCKED"
    finally:
        db.rollback()
        db.close()


def test_aislamiento(mundo, reloj_mfa):
    db: Session = mundo.factory()
    try:
        wh = _almacen(mundo)
        prod = _producto(mundo)
        other_company_id = db.scalar(select(Company.id).where(Company.tenant_id == mundo.tenant_b_id))

        party = Party(
            company_id=other_company_id,
            code=f"SUP-{_hex()}",
            name="Proveedor externo",
            person_type="JURIDICA",
            tax_id=f"J-{uuid.uuid4().hex[:8]}-1",
            roles=["PROVEEDOR"],
            status="ACTIVE",
        )
        db.add(party)
        db.flush()
        db.add(Supplier(party_id=str(party.id), approval_status="APPROVED"))
        db.flush()

        other_order = PurchaseOrder(
            company_id=other_company_id,
            code=f"OC-{_hex()}",
            supplier_id=str(party.id),
            status="APPROVED",
            currency="VED",
        )
        db.add(other_order)
        db.flush()
        other_line = PurchaseOrderLine(
            order_id=str(other_order.id),
            product_id=prod,
            quantity_ordered=9,
            quantity_received=0,
            unit_price=1.0,
            needs_inventory=True,
            destination_warehouse_id=wh,
        )
        db.add(other_line)
        db.commit()

        assert _abierto(mundo, wh, prod) == Decimal("0")

        headers = _operador(mundo, reloj_mfa, _crear_rol(mundo, ["compras:view", "compras:create"]))
        resp = mundo.client.post(
            f"{API}/purchasing/orders/{other_order.id}/lines/{other_line.id}/destination",
            json={"warehouse_id": wh},
            headers=headers,
        )
        assert resp.status_code == 404
    finally:
        db.close()


def test_detalle_de_necesidad_expone_suministro(mundo, reloj_mfa):
    wh = _almacen(mundo)
    prod = _producto(mundo)
    _politica(mundo, wh, {"auto_replenishment_enabled": True, "safety_mode": "NONE", "safety_value": "0", "demand_source": "INVENTORY_ISSUES"})
    _entrada(mundo, wh, prod, 12, 8)
    _salida(mundo, wh, prod, 10, 2)

    evaluate_replenishment_needs(mundo.factory, now=datetime.now(UTC))
    needs = _necesidades_activas(mundo, wh, prod)
    need_id = str(needs[0].id)

    headers = _operador(mundo, reloj_mfa, _crear_rol(mundo, ["compras:view"]))
    resp = mundo.client.get(f"{API}/planning/replenishment-needs/{need_id}", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["trigger"]["open_supply"] == "0.000000"
    assert body["trigger"]["projected_available"] == "2.000000"
    assert "open_supply" in body["current"]
