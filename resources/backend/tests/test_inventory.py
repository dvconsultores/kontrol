"""Pruebas de inventario y logística (003-inventario-logistica).

Cubre: movimiento balanceado/inmutabilidad/reverso, unicidad de lote y serial,
FEFO, reservas ≤ disponible y liberación, reconstrucción de balance,
máquina de estados de transferencia, conteo/ajuste aprobado, valoración
promedio/FIFO y aislamiento multiempresa.
"""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base, init_models
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.inventory import service as inv_service
from app.modules.inventory.models import (
    InventoryBalance,
    InventoryMovement,
    MovementType,
    StockCount,
    Transfer,
    TransferLine,
)
from app.modules.master_data.models import CatalogItem
from app.modules.organization.models import Warehouse


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    init_models()
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


COMPANY = "tenant-1"
OTHER = "tenant-2"


def _make_warehouse(db: Session, company: str = COMPANY, code: str = "W-01", name: str = "Principal") -> Warehouse:
    wh = Warehouse(company_id=company, code=code, name=name, status="ACTIVE")
    db.add(wh)
    db.flush()
    return wh


def _make_product(db: Session, company: str = COMPANY, code: str = "P-001", name: str = "Arroz") -> CatalogItem:
    item = CatalogItem(company_id=company, code=code, name=name, item_type="PRODUCT", status="ACTIVE")
    db.add(item)
    db.flush()
    return item


def _make_mtype(db: Session, code: str, direction: str) -> MovementType:
    mt = MovementType(company_id=None, code=code, name=code, direction=direction, affects_balance=True, status="ACTIVE")
    db.add(mt)
    db.flush()
    return mt


class TestMovimientos:
    def test_movement_balanced_and_updates_balance(self, db_session) -> None:
        wh = _make_warehouse(db_session)
        product = _make_product(db_session)
        mtype = _make_mtype(db_session, "ENTRADA", "IN")
        movement = inv_service.record_movement(
            db_session, company_id=COMPANY, warehouse_id=str(wh.id), product_id=str(product.id),
            movement_type_id=str(mtype.id), quantity=100.0, unit_cost=10.0, document_ref="R-001",
        )
        assert movement.quantity == 100.0
        assert inv_service.get_available(db_session, company_id=COMPANY, product_id=str(product.id), warehouse_id=str(wh.id)) == 100.0
        # Salida
        out_type = _make_mtype(db_session, "SALIDA", "OUT")
        inv_service.record_movement(db_session, company_id=COMPANY, warehouse_id=str(wh.id), product_id=str(product.id),
                                    movement_type_id=str(out_type.id), quantity=-30.0)
        assert inv_service.get_available(db_session, company_id=COMPANY, product_id=str(product.id), warehouse_id=str(wh.id)) == 70.0

    def test_zero_quantity_rejected(self, db_session) -> None:
        wh = _make_warehouse(db_session)
        product = _make_product(db_session)
        mtype = _make_mtype(db_session, "ENTRADA", "IN")
        with pytest.raises(KontrolError):
            inv_service.record_movement(db_session, company_id=COMPANY, warehouse_id=str(wh.id), product_id=str(product.id),
                                        movement_type_id=str(mtype.id), quantity=0.0)

    def test_insufficient_stock_rejected(self, db_session) -> None:
        wh = _make_warehouse(db_session)
        product = _make_product(db_session)
        out_type = _make_mtype(db_session, "SALIDA", "OUT")
        with pytest.raises(ConflictError):
            inv_service.record_movement(db_session, company_id=COMPANY, warehouse_id=str(wh.id), product_id=str(product.id),
                                        movement_type_id=str(out_type.id), quantity=-10.0)

    def test_reverse_is_linked_and_does_not_delete(self, db_session) -> None:
        wh = _make_warehouse(db_session)
        product = _make_product(db_session)
        mtype = _make_mtype(db_session, "ENTRADA", "IN")
        movement = inv_service.record_movement(db_session, company_id=COMPANY, warehouse_id=str(wh.id),
                                               product_id=str(product.id), movement_type_id=str(mtype.id),
                                               quantity=50.0, unit_cost=8.0)
        reverse = inv_service.reverse_movement(db_session, movement=movement)
        assert reverse.reversed_by_id == str(movement.id)
        assert movement.reversed_by_id == str(reverse.id)
        # El movimiento original sigue existiendo (inmutabilidad, P5)
        assert db_session.get(InventoryMovement, movement.id) is not None
        assert inv_service.get_available(db_session, company_id=COMPANY, product_id=str(product.id), warehouse_id=str(wh.id)) == 0.0
        # No se puede revertir dos veces
        with pytest.raises(ConflictError):
            inv_service.reverse_movement(db_session, movement=movement)

    def test_idempotency_does_not_duplicate(self, db_session) -> None:
        wh = _make_warehouse(db_session)
        product = _make_product(db_session)
        mtype = _make_mtype(db_session, "ENTRADA", "IN")
        m1 = inv_service.record_movement(db_session, company_id=COMPANY, warehouse_id=str(wh.id), product_id=str(product.id),
                                         movement_type_id=str(mtype.id), quantity=10.0, idempotency_key="k-1")
        m2 = inv_service.record_movement(db_session, company_id=COMPANY, warehouse_id=str(wh.id), product_id=str(product.id),
                                         movement_type_id=str(mtype.id), quantity=10.0, idempotency_key="k-1")
        assert m1.id == m2.id
        assert inv_service.get_available(db_session, company_id=COMPANY, product_id=str(product.id), warehouse_id=str(wh.id)) == 10.0


class TestLotesYSeriales:
    def test_lot_unique_and_expiry(self, db_session) -> None:
        product = _make_product(db_session)
        lot = inv_service.create_lot(db_session, company_id=COMPANY, product_id=str(product.id), lot_number="L-1",
                                     manufacture_date=date(2026, 1, 1), expiry_date=date(2027, 1, 1))
        assert lot.status == "DISPONIBLE"
        with pytest.raises(ConflictError):
            inv_service.create_lot(db_session, company_id=COMPANY, product_id=str(product.id), lot_number="L-1")
        with pytest.raises(KontrolError):
            inv_service.create_lot(db_session, company_id=COMPANY, product_id=str(product.id), lot_number="L-2",
                                   manufacture_date=date(2027, 1, 1), expiry_date=date(2026, 1, 1))

    def test_serial_unique(self, db_session) -> None:
        product = _make_product(db_session)
        inv_service.create_serial(db_session, company_id=COMPANY, product_id=str(product.id), serial="IMEI-1", imei1="354000000000001")
        with pytest.raises(ConflictError):
            inv_service.create_serial(db_session, company_id=COMPANY, product_id=str(product.id), serial="IMEI-1")

    def test_fefo_selects_earliest_expiry(self, db_session) -> None:
        product = _make_product(db_session)
        inv_service.create_lot(db_session, company_id=COMPANY, product_id=str(product.id), lot_number="L-LEJOS",
                               expiry_date=date(2028, 1, 1))
        inv_service.create_lot(db_session, company_id=COMPANY, product_id=str(product.id), lot_number="L-CERCA",
                               expiry_date=date(2026, 12, 31))
        lots = inv_service.fefo_pick_lots(db_session, company_id=COMPANY, product_id=str(product.id), quantity=1.0)
        assert [lot.lot_number for lot in lots] == ["L-CERCA", "L-LEJOS"]

    def test_lot_transition(self, db_session) -> None:
        product = _make_product(db_session)
        lot = inv_service.create_lot(db_session, company_id=COMPANY, product_id=str(product.id), lot_number="L-1")
        inv_service.transition_lot(db_session, lot=lot, target="CUARENTENA")
        assert lot.status == "CUARENTENA"
        # Transición no permitida desde DISPONIBLE directo a VENDIDO (requiere pasar por RESERVADO)
        lot2 = inv_service.create_lot(db_session, company_id=COMPANY, product_id=str(product.id), lot_number="L-2")
        with pytest.raises(ConflictError):
            inv_service.transition_lot(db_session, lot=lot2, target="VENDIDO")


class TestReservas:
    def test_reserve_reduces_available_without_physical_change(self, db_session) -> None:
        wh = _make_warehouse(db_session)
        product = _make_product(db_session)
        mtype = _make_mtype(db_session, "ENTRADA", "IN")
        inv_service.record_movement(db_session, company_id=COMPANY, warehouse_id=str(wh.id), product_id=str(product.id),
                                    movement_type_id=str(mtype.id), quantity=100.0)
        reservation = inv_service.reserve(db_session, company_id=COMPANY, source_document="SO-1", product_id=str(product.id),
                                          warehouse_id=str(wh.id), quantity=40.0)
        balance = db_session.execute(
            __import__("sqlalchemy").select(InventoryBalance)
            .where(InventoryBalance.company_id == COMPANY, InventoryBalance.product_id == str(product.id))
        ).scalars().first()
        assert balance.qty_on_hand == 100.0  # la existencia física NO cambia
        assert balance.qty_reserved == 40.0
        assert balance.qty_available == 60.0
        assert reservation.status == "ACTIVE"

    def test_over_reservation_rejected(self, db_session) -> None:
        wh = _make_warehouse(db_session)
        product = _make_product(db_session)
        mtype = _make_mtype(db_session, "ENTRADA", "IN")
        inv_service.record_movement(db_session, company_id=COMPANY, warehouse_id=str(wh.id), product_id=str(product.id),
                                    movement_type_id=str(mtype.id), quantity=10.0)
        with pytest.raises(ConflictError):
            inv_service.reserve(db_session, company_id=COMPANY, source_document="SO-1", product_id=str(product.id),
                                warehouse_id=str(wh.id), quantity=20.0)

    def test_release_restores_available(self, db_session) -> None:
        wh = _make_warehouse(db_session)
        product = _make_product(db_session)
        mtype = _make_mtype(db_session, "ENTRADA", "IN")
        inv_service.record_movement(db_session, company_id=COMPANY, warehouse_id=str(wh.id), product_id=str(product.id),
                                    movement_type_id=str(mtype.id), quantity=50.0)
        reservation = inv_service.reserve(db_session, company_id=COMPANY, source_document="SO-1", product_id=str(product.id),
                                          warehouse_id=str(wh.id), quantity=20.0)
        inv_service.release_reservation(db_session, reservation=reservation)
        assert reservation.status == "RELEASED"
        assert inv_service.get_available(db_session, company_id=COMPANY, product_id=str(product.id), warehouse_id=str(wh.id)) == 50.0


class TestBalanceReconstruible:
    def test_recompute_rebuilds_from_movements(self, db_session) -> None:
        wh = _make_warehouse(db_session)
        product = _make_product(db_session)
        in_type = _make_mtype(db_session, "ENTRADA", "IN")
        out_type = _make_mtype(db_session, "SALIDA", "OUT")
        inv_service.record_movement(db_session, company_id=COMPANY, warehouse_id=str(wh.id), product_id=str(product.id),
                                    movement_type_id=str(in_type.id), quantity=80.0)
        inv_service.record_movement(db_session, company_id=COMPANY, warehouse_id=str(wh.id), product_id=str(product.id),
                                    movement_type_id=str(out_type.id), quantity=-20.0)
        inv_service.reserve(db_session, company_id=COMPANY, source_document="SO-1", product_id=str(product.id),
                            warehouse_id=str(wh.id), quantity=10.0)
        rebuilt = inv_service.recompute_balances(db_session, company_id=COMPANY)
        assert rebuilt >= 1
        balance = db_session.execute(
            __import__("sqlalchemy").select(InventoryBalance)
            .where(InventoryBalance.company_id == COMPANY, InventoryBalance.product_id == str(product.id))
        ).scalars().first()
        assert balance.qty_on_hand == 60.0
        assert balance.qty_reserved == 10.0
        assert balance.qty_available == 50.0


class TestTransferencia:
    def test_full_transfer_state_machine(self, db_session) -> None:
        wh_a = _make_warehouse(db_session, code="W-A", name="A")
        wh_b = _make_warehouse(db_session, code="W-B", name="B")
        product = _make_product(db_session)
        _make_mtype(db_session, "ENTRADA_RECEPCION", "IN")
        _make_mtype(db_session, "TRANSFERENCIA_SALIDA", "OUT")
        _make_mtype(db_session, "TRANSFERENCIA_ENTRADA", "IN")
        in_type = db_session.execute(__import__("sqlalchemy").select(MovementType).where(MovementType.code == "ENTRADA_RECEPCION")).scalars().first()
        inv_service.record_movement(db_session, company_id=COMPANY, warehouse_id=str(wh_a.id), product_id=str(product.id),
                                    movement_type_id=str(in_type.id), quantity=50.0)

        transfer = Transfer(company_id=COMPANY, code="T-1", origin_warehouse_id=str(wh_a.id),
                            destination_warehouse_id=str(wh_b.id), status="DRAFT")
        db_session.add(transfer)
        db_session.flush()
        db_session.add(TransferLine(transfer_id=str(transfer.id), product_id=str(product.id), quantity_sent=30.0))
        inv_service.transition_transfer(db_session, transfer=transfer, target="SUBMITTED")
        inv_service.transition_transfer(db_session, transfer=transfer, target="APPROVED")
        inv_service.confirm_transfer_ship(db_session, transfer=transfer, shipment_ref="SH-1")
        assert transfer.status == "IN_TRANSIT"
        inv_service.confirm_transfer_receipt(db_session, transfer=transfer, receipt_ref="RC-1")
        assert transfer.status == "RECEIVED"
        inv_service.transition_transfer(db_session, transfer=transfer, target="CLOSED")
        assert transfer.status == "CLOSED"
        # Saldo: origen 50-30=20; destino +30
        assert inv_service.get_available(db_session, company_id=COMPANY, product_id=str(product.id), warehouse_id=str(wh_a.id)) == 20.0
        assert inv_service.get_available(db_session, company_id=COMPANY, product_id=str(product.id), warehouse_id=str(wh_b.id)) == 30.0

    def test_transfer_invalid_transition(self, db_session) -> None:
        transfer = Transfer(company_id=COMPANY, code="T-1", origin_warehouse_id="a", destination_warehouse_id="b", status="DRAFT")
        db_session.add(transfer)
        db_session.flush()
        with pytest.raises(ConflictError):
            inv_service.transition_transfer(db_session, transfer=transfer, target="IN_TRANSIT")  # salta pasos


class TestConteoYAjuste:
    def test_count_to_adjustment_generates_movement(self, db_session) -> None:
        wh = _make_warehouse(db_session)
        product = _make_product(db_session)
        _make_mtype(db_session, "CONTEO", "INTERNAL")
        in_type = db_session.execute(__import__("sqlalchemy").select(MovementType).where(MovementType.code == "ENTRADA_RECEPCION")).scalars().first()
        if in_type is None:
            _make_mtype(db_session, "ENTRADA_RECEPCION", "IN")
            in_type = db_session.execute(__import__("sqlalchemy").select(MovementType).where(MovementType.code == "ENTRADA_RECEPCION")).scalars().first()
        inv_service.record_movement(db_session, company_id=COMPANY, warehouse_id=str(wh.id), product_id=str(product.id),
                                    movement_type_id=str(in_type.id), quantity=100.0)

        count = StockCount(company_id=COMPANY, code="C-1", warehouse_id=str(wh.id), scope=[], freeze_policy="PER_PRODUCT", status="DRAFT")
        db_session.add(count)
        db_session.flush()
        inv_service.record_count_line(db_session, count_id=str(count.id), product_id=str(product.id), expected_qty=100.0, counted_qty=95.0)
        inv_service.transition_count(db_session, count=count, target="FROZEN")
        inv_service.transition_count(db_session, count=count, target="COUNTING")
        inv_service.transition_count(db_session, count=count, target="SUBMITTED")
        inv_service.approve_count(db_session, count=count)
        assert count.status == "APPROVED"
        # Diferencia -5 generó movimiento: existencias 95
        assert inv_service.get_available(db_session, company_id=COMPANY, product_id=str(product.id), warehouse_id=str(wh.id)) == 95.0

    def test_adjustment_requires_approval_and_applies_movement(self, db_session) -> None:
        wh = _make_warehouse(db_session)
        product = _make_product(db_session)
        _make_mtype(db_session, "AJUSTE_POSITIVO", "IN")
        adjustment = inv_service.create_adjustment(db_session, company_id=COMPANY, warehouse_id=str(wh.id),
                                                   product_id=str(product.id), quantity=5.0, reason="Merma recuperada",
                                                   evidence_ref="EV-1", unit_cost=2.0)
        assert adjustment.status == "DRAFT"
        inv_service.transition_adjustment(db_session, adjustment=adjustment, target="SUBMITTED")
        inv_service.transition_adjustment(db_session, adjustment=adjustment, target="APPROVED", actor="approver-1")
        assert adjustment.approver_id == "approver-1"
        inv_service.apply_adjustment(db_session, adjustment=adjustment)
        assert adjustment.status == "APPLIED"
        assert inv_service.get_available(db_session, company_id=COMPANY, product_id=str(product.id), warehouse_id=str(wh.id)) == 5.0
        # No se puede saltar a APPLIED desde DRAFT
        adjustment2 = inv_service.create_adjustment(db_session, company_id=COMPANY, warehouse_id=str(wh.id),
                                                    product_id=str(product.id), quantity=1.0, reason="Otra")
        with pytest.raises(ConflictError):
            inv_service.apply_adjustment(db_session, adjustment=adjustment2)


class TestCostos:
    def test_average_valuation_and_cost_of_sale(self, db_session) -> None:
        wh = _make_warehouse(db_session)
        product = _make_product(db_session)
        in_type = _make_mtype(db_session, "ENTRADA", "IN")
        out_type = _make_mtype(db_session, "SALIDA", "OUT")
        inv_service.record_movement(db_session, company_id=COMPANY, warehouse_id=str(wh.id), product_id=str(product.id),
                                    movement_type_id=str(in_type.id), quantity=100.0, unit_cost=10.0, document_ref="R1")
        inv_service.record_movement(db_session, company_id=COMPANY, warehouse_id=str(wh.id), product_id=str(product.id),
                                    movement_type_id=str(in_type.id), quantity=100.0, unit_cost=12.0, document_ref="R2")
        # Promedio = (100*10 + 100*12)/200 = 11
        assert inv_service.valuation(db_session, company_id=COMPANY, product_id=str(product.id), warehouse_id=str(wh.id)) == 2200.0
        movement = inv_service.record_movement(db_session, company_id=COMPANY, warehouse_id=str(wh.id), product_id=str(product.id),
                                               movement_type_id=str(out_type.id), quantity=-100.0, document_ref="S1")
        assert movement.unit_cost == 11.0  # costo de salida promedio
        assert inv_service.valuation(db_session, company_id=COMPANY, product_id=str(product.id), warehouse_id=str(wh.id)) == 1100.0

    def test_fifo_valuation(self, db_session) -> None:
        wh = _make_warehouse(db_session)
        product = _make_product(db_session)
        profile = __import__("app.modules.inventory.models", fromlist=["CostingProfile"]).CostingProfile(
            company_id=COMPANY, code="FIFO-1", method="FIFO", status="ACTIVE")
        db_session.add(profile)
        db_session.flush()
        in_type = _make_mtype(db_session, "ENTRADA", "IN")
        out_type = _make_mtype(db_session, "SALIDA", "OUT")
        inv_service.record_movement(db_session, company_id=COMPANY, warehouse_id=str(wh.id), product_id=str(product.id),
                                    movement_type_id=str(in_type.id), quantity=100.0, unit_cost=10.0, document_ref="R1")
        inv_service.record_movement(db_session, company_id=COMPANY, warehouse_id=str(wh.id), product_id=str(product.id),
                                    movement_type_id=str(in_type.id), quantity=100.0, unit_cost=12.0, document_ref="R2")
        movement = inv_service.record_movement(db_session, company_id=COMPANY, warehouse_id=str(wh.id), product_id=str(product.id),
                                               movement_type_id=str(out_type.id), quantity=-100.0, document_ref="S1")
        assert movement.unit_cost == 10.0  # FIFO: consume la capa más antigua
        assert inv_service.valuation(db_session, company_id=COMPANY, product_id=str(product.id), warehouse_id=str(wh.id)) == 1200.0


class TestMultiempresa:
    def test_tenant_isolation_negative(self, db_session) -> None:
        wh_a = _make_warehouse(db_session, company=COMPANY, code="W-A")
        product_a = _make_product(db_session, company=COMPANY, code="P-A")
        wh_b = _make_warehouse(db_session, company=OTHER, code="W-B")
        product_b = _make_product(db_session, company=OTHER, code="P-B")
        in_type = _make_mtype(db_session, "ENTRADA", "IN")

        inv_service.record_movement(db_session, company_id=COMPANY, warehouse_id=str(wh_a.id), product_id=str(product_a.id),
                                    movement_type_id=str(in_type.id), quantity=100.0)
        # La empresa B no ve el balance de A
        assert inv_service.get_available(db_session, company_id=OTHER, product_id=str(product_a.id), warehouse_id=str(wh_a.id)) == 0.0
        # A no puede operar en el almacén de B
        with pytest.raises(NotFoundError):
            inv_service.record_movement(db_session, company_id=COMPANY, warehouse_id=str(wh_b.id), product_id=str(product_b.id),
                                        movement_type_id=str(in_type.id), quantity=1.0)
