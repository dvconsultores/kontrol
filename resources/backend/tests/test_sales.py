"""Pruebas de ventas y cuentas por cobrar (005).

Cubre: máquina de estados de orden + reserva vía 003, despacho (validación +
salida), factura de venta → CxC (RECEIVABLE), cobros y aplicaciones, nota de
crédito, aging y aislamiento multiempresa.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from conftest import make_engine, seed_org_chain
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base, init_models
from app.core.errors import ConflictError, NotFoundError
from app.modules.inventory import service as inv_service
from app.modules.inventory.models import MovementType
from app.modules.master_data.models import CatalogItem, Party
from app.modules.organization.models import Warehouse
from app.modules.purchasing.models import OpenItem, Payment
from app.modules.sales import service as sales_service
from app.modules.sales.models import SalesInvoice
from tests.company_seed import EMPRESA_DOS, EMPRESA_UNO


@pytest.fixture()
def db_session():
    engine = make_engine()
    init_models()
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    session = session_factory()
    seed_org_chain(session, COMPANY, OTHER)
    try:
        yield session
    finally:
        session.close()


#: Empresas **reales**, sembradas por `db_session`. Antes eran la cadena
#: «tenant-1», que no era ni empresa ni tenant y solo se aceptaba porque la
#: base no comprobaba nada.
COMPANY = EMPRESA_UNO
OTHER = EMPRESA_DOS


def _make_customer(db: Session, company: str = COMPANY, code: str = "CLI-1") -> Party:
    party = Party(company_id=company, code=code, name="Cliente SA", person_type="JURIDICA",
                  tax_id=f"J-9876543-{abs(hash(code)) % 10}", roles=["CLIENTE"], status="ACTIVE")
    db.add(party)
    db.flush()
    return party


def _make_product(db: Session, company: str = COMPANY, code: str = "P-001") -> CatalogItem:
    item = CatalogItem(company_id=company, code=code, name="Producto", item_type="PRODUCT", status="ACTIVE")
    db.add(item)
    db.flush()
    return item


def _make_warehouse(db: Session, company: str = COMPANY) -> Warehouse:
    wh = Warehouse(company_id=company, code="W-1", name="Principal", status="ACTIVE")
    db.add(wh)
    db.flush()
    return wh


def _make_types(db: Session) -> None:
    for code, direction in (("ENTRADA_RECEPCION", "IN"), ("SALIDA_DESPACHO", "OUT")):
        db.add(MovementType(company_id=COMPANY, code=code, name=code, direction=direction,
                            affects_balance=True, status="ACTIVE"))
    db.flush()


def _stock(db: Session, product: CatalogItem, warehouse: Warehouse, qty: float = 100.0) -> None:
    mtype = db.execute(__import__("sqlalchemy").select(MovementType).where(MovementType.code == "ENTRADA_RECEPCION")).scalars().first()
    inv_service.record_movement(db, company_id=COMPANY, warehouse_id=str(warehouse.id), product_id=str(product.id),
                                movement_type_id=str(mtype.id), quantity=qty, unit_cost=5.0)


class TestOrdenDeVenta:
    def test_order_state_machine_and_reserve(self, db_session) -> None:
        customer = _make_customer(db_session)
        product = _make_product(db_session)
        wh = _make_warehouse(db_session)
        _make_types(db_session)
        _stock(db_session, product, wh)
        order = sales_service.create_order(db_session, company_id=COMPANY, code="OV-1", customer_id=str(customer.id),
                                           warehouse_id=str(wh.id), margin=0.3)
        sales_service.add_order_line(db_session, order_id=str(order.id), product_id=str(product.id),
                                     quantity=30.0, unit_price=10.0)
        # Spec 030: la reserva nace al confirmar (`DRAFT → SUBMITTED`); sin
        # política de crédito el pedido queda RELEASED en la misma llamada.
        sales_service.confirmar_pedido(db_session, company_id=COMPANY, order_id=str(order.id))
        # La reserva vía 003 redujo el disponible, sin cambio físico
        assert inv_service.get_available(db_session, company_id=COMPANY, product_id=str(product.id), warehouse_id=str(wh.id)) == 70.0
        assert order.status == "RELEASED"
        assert order.submitted_at is not None and order.released_at is not None

    def test_order_invalid_transition(self, db_session) -> None:
        customer = _make_customer(db_session)
        order = sales_service.create_order(db_session, company_id=COMPANY, code="OV-2", customer_id=str(customer.id))
        with pytest.raises(ConflictError):
            sales_service.transition_order(db_session, order=order, target="RELEASED")  # salta la confirmación


class TestDespacho:
    def test_shipment_validate_and_confirm(self, db_session) -> None:
        customer = _make_customer(db_session)
        product = _make_product(db_session)
        wh = _make_warehouse(db_session)
        _make_types(db_session)
        _stock(db_session, product, wh, 50.0)
        order = sales_service.create_order(db_session, company_id=COMPANY, code="OV-3", customer_id=str(customer.id),
                                           warehouse_id=str(wh.id))
        sales_service.add_order_line(db_session, order_id=str(order.id), product_id=str(product.id),
                                     quantity=20.0, unit_price=10.0)
        sales_service.confirmar_pedido(db_session, company_id=COMPANY, order_id=str(order.id))
        assert order.status == "RELEASED"
        shipment = sales_service.create_shipment(db_session, company_id=COMPANY, code="SH-1", order_id=str(order.id),
                                                 origin_warehouse_id=str(wh.id), lines=[{"product_id": str(product.id), "quantity": 20.0}])
        sales_service.validate_shipment(db_session, shipment=shipment)
        assert shipment.validation_status == "APPROVED"
        sales_service.confirm_shipment(db_session, shipment=shipment)
        assert shipment.status == "SHIPPED"
        assert order.status == "SHIPPED"
        # Salida registrada: disponible 30
        assert inv_service.get_available(db_session, company_id=COMPANY, product_id=str(product.id), warehouse_id=str(wh.id)) == 30.0

    def test_shipment_requires_validation(self, db_session) -> None:
        customer = _make_customer(db_session)
        product = _make_product(db_session)
        wh = _make_warehouse(db_session)
        _make_types(db_session)
        _stock(db_session, product, wh)
        order = sales_service.create_order(db_session, company_id=COMPANY, code="OV-4", customer_id=str(customer.id),
                                           warehouse_id=str(wh.id))
        sales_service.add_order_line(db_session, order_id=str(order.id), product_id=str(product.id), quantity=10.0, unit_price=5.0)
        sales_service.confirmar_pedido(db_session, company_id=COMPANY, order_id=str(order.id))
        shipment = sales_service.create_shipment(db_session, company_id=COMPANY, code="SH-2", order_id=str(order.id),
                                                 origin_warehouse_id=str(wh.id), lines=[{"product_id": str(product.id), "quantity": 10.0}])
        with pytest.raises(ConflictError):
            sales_service.confirm_shipment(db_session, shipment=shipment)  # sin validación


class TestFacturaVenta:
    def test_invoice_emit_creates_receivable(self, db_session) -> None:
        customer = _make_customer(db_session)
        product = _make_product(db_session)
        invoice = sales_service.create_invoice(db_session, company_id=COMPANY, customer_id=str(customer.id))
        sales_service.add_invoice_line(db_session, invoice_id=str(invoice.id), product_id=str(product.id),
                                       quantity=10.0, unit_price=100.0, tax_amount=16.0)
        sales_service.recompute_invoice_total(db_session, invoice=invoice)
        assert invoice.total == 1016.0
        sales_service.transition_invoice(db_session, invoice=invoice, target="VALIDATED")
        sales_service.transition_invoice(db_session, invoice=invoice, target="APPROVED")
        sales_service.transition_invoice(db_session, invoice=invoice, target="EMITTED")
        assert invoice.status == "EMITTED"
        items = db_session.query(OpenItem).all()
        assert len(items) == 1
        assert items[0].item_type == "RECEIVABLE"
        assert items[0].original == 1016.0

    def test_invoice_void_blocked_with_application(self, db_session) -> None:
        customer = _make_customer(db_session)
        product = _make_product(db_session)
        invoice = sales_service.create_invoice(db_session, company_id=COMPANY, customer_id=str(customer.id))
        sales_service.add_invoice_line(db_session, invoice_id=str(invoice.id), product_id=str(product.id), quantity=1.0, unit_price=100.0)
        sales_service.recompute_invoice_total(db_session, invoice=invoice)
        sales_service.transition_invoice(db_session, invoice=invoice, target="VALIDATED")
        sales_service.transition_invoice(db_session, invoice=invoice, target="APPROVED")
        sales_service.transition_invoice(db_session, invoice=invoice, target="EMITTED")
        item = db_session.query(OpenItem).first()
        # Aplicar un cobro
        collection = _collection(db_session, invoice.customer_id, 100.0)
        from app.modules.purchasing import service as ap_service

        ap_service.apply_source(db_session, company_id=COMPANY, source_type="PAYMENT", source_id=str(collection.id),
                                target_open_item_id=str(item.id), amount=100.0)
        with pytest.raises(ConflictError):
            sales_service.void_invoice(db_session, invoice=invoice)  # con cobro aplicado


def _collection(db_session, party_id: str, amount: float = 200.0) -> Payment:
    from app.modules.purchasing import service as ap_service

    payment = ap_service.register_payment(db_session, company_id=COMPANY, party_id=party_id, amount=amount,
                                          direction="IN")
    ap_service.transition_payment(db_session, payment=payment, target="SUBMITTED")
    ap_service.transition_payment(db_session, payment=payment, target="APPROVED", actor="approver-1")
    return payment


class TestCxC:
    def _emit(self, db_session, amount: float = 500.0) -> SalesInvoice:
        customer = _make_customer(db_session)
        product = _make_product(db_session)
        invoice = sales_service.create_invoice(db_session, company_id=COMPANY, customer_id=str(customer.id))
        sales_service.add_invoice_line(db_session, invoice_id=str(invoice.id), product_id=str(product.id),
                                       quantity=1.0, unit_price=amount)
        sales_service.recompute_invoice_total(db_session, invoice=invoice)
        sales_service.transition_invoice(db_session, invoice=invoice, target="VALIDATED")
        sales_service.transition_invoice(db_session, invoice=invoice, target="APPROVED")
        sales_service.transition_invoice(db_session, invoice=invoice, target="EMITTED")
        return invoice

    def test_collection_apply_reduces_balance(self, db_session) -> None:
        invoice = self._emit(db_session, 500.0)
        open_item = db_session.query(OpenItem).first()
        collection = _collection(db_session, invoice.customer_id, 200.0)
        from app.modules.purchasing import service as ap_service

        ap_service.apply_source(db_session, company_id=COMPANY, source_type="PAYMENT", source_id=str(collection.id),
                                target_open_item_id=str(open_item.id), amount=200.0)
        db_session.flush()
        assert ap_service.open_item_balance(open_item) == 300.0
        assert open_item.status == "OPEN"

    def test_full_settle_marks_invoice_paid(self, db_session) -> None:
        invoice = self._emit(db_session, 100.0)
        open_item = db_session.query(OpenItem).first()
        collection = _collection(db_session, invoice.customer_id, 100.0)
        sales_service.apply_to_cxc(db_session, company_id=COMPANY, source_type="PAYMENT", source_id=str(collection.id),
                                   target_open_item_id=str(open_item.id), amount=100.0)
        db_session.flush()
        assert open_item.status == "CLOSED"
        assert invoice.status == "PAID"

    def test_credit_note_reduces_balance(self, db_session) -> None:
        invoice = self._emit(db_session, 400.0)
        open_item = db_session.query(OpenItem).first()
        note = sales_service.create_credit_note(db_session, company_id=COMPANY, customer_id=invoice.customer_id,
                                                number="NC-1", amount=100.0, invoice_ref=str(invoice.id))
        sales_service.post_credit_note(db_session, note=note)
        sales_service.apply_credit_note(db_session, note=note, target_open_item_id=str(open_item.id), amount=100.0)
        db_session.flush()
        assert open_item.status == "OPEN"
        # coerción a float: original/applied son Decimal (Numeric) tras T-201
        assert round(float(open_item.original) - float(open_item.applied), 6) == 300.0
        assert note.applied == 100.0

    def test_aging_receivable(self, db_session) -> None:
        self._emit(db_session, 1000.0)
        item = db_session.query(OpenItem).first()
        item.due_date = date.today() - timedelta(days=75)
        db_session.flush()
        from app.modules.purchasing import service as ap_service

        result = ap_service.aging(db_session, company_id=COMPANY, item_type="RECEIVABLE")
        assert result["total"] == 1000.0
        assert result["buckets"]["61-90"] == 1000.0


class TestMultiempresa:
    def test_tenant_isolation(self, db_session) -> None:
        customer_b = _make_customer(db_session, company=OTHER, code="CLI-B")
        with pytest.raises(NotFoundError):
            sales_service.create_order(db_session, company_id=COMPANY, code="OV-X", customer_id=str(customer_b.id))
