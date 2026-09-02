"""Pruebas de compras y cuentas por pagar (004).

Cubre: máquina de estados de orden, recepción → 003 (movimientos/saldos),
duplicidad de factura, conciliación triple, posteo → open item, pagos con
aplicaciones atómicas (no exceden saldo), anticipos, notas de crédito, aging,
retenciones y aislamiento multiempresa.
"""

from __future__ import annotations

from datetime import date

import pytest
from conftest import make_engine, seed_org_chain
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base, init_models
from app.core.errors import ConflictError, NotFoundError
from app.modules.inventory import service as inv_service
from app.modules.inventory.models import InventoryMovement, MovementType
from app.modules.master_data.models import CatalogItem, Party
from app.modules.organization.models import Warehouse
from app.modules.purchasing import service as ap_service
from app.modules.purchasing.models import OpenItem, SupplierInvoice
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


def _make_party(db: Session, company: str = COMPANY, code: str = "SUP-1", name: str = "Proveedor SA") -> Party:
    party = Party(company_id=company, code=code, name=name, person_type="JURIDICA", tax_id=f"J-1234567-{abs(hash(code)) % 10}", roles=["PROVEEDOR"], status="ACTIVE")
    db.add(party)
    db.flush()
    return party


def _make_product(db: Session, company: str = COMPANY, code: str = "P-001") -> CatalogItem:
    item = CatalogItem(company_id=company, code=code, name="Arroz", item_type="PRODUCT", status="ACTIVE")
    db.add(item)
    db.flush()
    return item


def _make_warehouse(db: Session, company: str = COMPANY, code: str = "W-1") -> Warehouse:
    wh = Warehouse(company_id=company, code=code, name="Principal", status="ACTIVE")
    db.add(wh)
    db.flush()
    return wh


def _make_in_type(db: Session) -> MovementType:
    # Tipo de la empresa, no global: es configuración suya.
    mt = MovementType(company_id=COMPANY, code="ENTRADA_RECEPCION", name="Entrada recepción", direction="IN",
                      affects_balance=True, status="ACTIVE")
    db.add(mt)
    db.flush()
    return mt


class TestOrdenDeCompra:
    def test_order_state_machine(self, db_session) -> None:
        supplier = _make_party(db_session)
        order = ap_service.create_order(db_session, company_id=COMPANY, code="OC-1", supplier_id=str(supplier.id))
        ap_service.transition_order(db_session, order=order, target="SUBMITTED")
        ap_service.transition_order(db_session, order=order, target="APPROVED", approval_ref="APR-1")
        assert order.status == "APPROVED"
        assert order.approval_ref == "APR-1"
        ap_service.transition_order(db_session, order=order, target="RECEIVED")
        ap_service.transition_order(db_session, order=order, target="CLOSED")
        assert order.status == "CLOSED"

    def test_order_invalid_transition(self, db_session) -> None:
        supplier = _make_party(db_session)
        order = ap_service.create_order(db_session, company_id=COMPANY, code="OC-2", supplier_id=str(supplier.id))
        with pytest.raises(ConflictError):
            ap_service.transition_order(db_session, order=order, target="APPROVED")  # salta SUBMITTED


class TestRecepcionIntegra003:
    def test_receipt_accept_updates_inventory_via_003(self, db_session) -> None:
        supplier = _make_party(db_session)
        product = _make_product(db_session)
        wh = _make_warehouse(db_session)
        _make_in_type(db_session)
        order = ap_service.create_order(db_session, company_id=COMPANY, code="OC-3", supplier_id=str(supplier.id))
        order_line = ap_service.add_order_line(db_session, order_id=str(order.id), product_id=str(product.id),
                                               quantity_ordered=50.0, unit_price=10.0)
        ap_service.transition_order(db_session, order=order, target="SUBMITTED")
        ap_service.transition_order(db_session, order=order, target="APPROVED")

        receipt = ap_service.create_receipt(db_session, company_id=COMPANY, code="RC-1", order_id=str(order.id),
                                            warehouse_id=str(wh.id))
        ap_service.add_receipt_line(db_session, company_id=receipt.company_id, receipt_id=str(receipt.id), order_line_id=str(order_line.id),
                                    product_id=str(product.id), quantity_received=30.0, quantity_accepted=30.0,
                                    quantity_rejected=0.0, lot_number="L-1")
        ap_service.confirm_receipt(db_session, receipt=receipt)
        receipt.quality_status = "APPROVED"
        db_session.flush()
        ap_service.accept_receipt(db_session, receipt=receipt)
        assert receipt.status == "ACCEPTED"
        # El motor de 003 registró el movimiento y el saldo
        assert inv_service.get_available(db_session, company_id=COMPANY, product_id=str(product.id), warehouse_id=str(wh.id)) == 30.0
        movements = db_session.query(InventoryMovement).all()
        assert len(movements) == 1
        assert order_line.quantity_received == 30.0
        # La orden pasa a PARTIALLY_RECEIVED (50 ordenados, 30 recibidos)
        assert order.status == "PARTIALLY_RECEIVED"

    def test_receipt_requires_approved_order(self, db_session) -> None:
        supplier = _make_party(db_session)
        product = _make_product(db_session)
        wh = _make_warehouse(db_session)
        order = ap_service.create_order(db_session, company_id=COMPANY, code="OC-4", supplier_id=str(supplier.id))
        ap_service.add_order_line(db_session, order_id=str(order.id), product_id=str(product.id), quantity_ordered=10.0, unit_price=5.0)
        # Sin aprobar, no se puede recibir
        with pytest.raises(ConflictError):
            ap_service.create_receipt(db_session, company_id=COMPANY, code="RC-2", order_id=str(order.id), warehouse_id=str(wh.id))


class TestFacturaProveedor:
    def test_invoice_duplicate_rejected(self, db_session) -> None:
        supplier = _make_party(db_session)
        product = _make_product(db_session)
        inv1 = ap_service.create_invoice(db_session, company_id=COMPANY, supplier_id=str(supplier.id),
                                         invoice_number="F-001", control_number="C-001")
        ap_service.add_invoice_line(db_session, invoice_id=str(inv1.id), product_id=str(product.id), quantity=10.0, unit_price=5.0)
        ap_service.recompute_invoice_total(db_session, invoice=inv1)
        with pytest.raises(ConflictError):
            ap_service.create_invoice(db_session, company_id=COMPANY, supplier_id=str(supplier.id),
                                      invoice_number="F-001", control_number="C-001")

    def test_invoice_flow_to_posted_and_open_item(self, db_session) -> None:
        supplier = _make_party(db_session)
        product = _make_product(db_session)
        invoice = ap_service.create_invoice(db_session, company_id=COMPANY, supplier_id=str(supplier.id),
                                            invoice_number="F-002", control_number="C-002")
        ap_service.add_invoice_line(db_session, invoice_id=str(invoice.id), product_id=str(product.id),
                                    quantity=10.0, unit_price=100.0, tax_amount=16.0)
        ap_service.recompute_invoice_total(db_session, invoice=invoice)
        assert invoice.total == 1016.0
        ap_service.transition_invoice(db_session, invoice=invoice, target="VALIDATED")
        ap_service.transition_invoice(db_session, invoice=invoice, target="MATCHED")
        ap_service.transition_invoice(db_session, invoice=invoice, target="APPROVED")
        ap_service.post_invoice(db_session, invoice=invoice)
        assert invoice.status == "POSTED"
        items = db_session.query(OpenItem).all()
        assert len(items) == 1
        assert items[0].original == 1016.0
        assert ap_service.open_item_balance(items[0]) == 1016.0

    def test_triple_match_with_variance(self, db_session) -> None:
        supplier = _make_party(db_session)
        product = _make_product(db_session)
        wh = _make_warehouse(db_session)
        _make_in_type(db_session)
        order = ap_service.create_order(db_session, company_id=COMPANY, code="OC-5", supplier_id=str(supplier.id))
        order_line = ap_service.add_order_line(db_session, order_id=str(order.id), product_id=str(product.id),
                                               quantity_ordered=10.0, unit_price=10.0)
        ap_service.transition_order(db_session, order=order, target="SUBMITTED")
        ap_service.transition_order(db_session, order=order, target="APPROVED")
        receipt = ap_service.create_receipt(db_session, company_id=COMPANY, code="RC-3", order_id=str(order.id), warehouse_id=str(wh.id))
        receipt_line = ap_service.add_receipt_line(db_session, company_id=receipt.company_id, receipt_id=str(receipt.id), order_line_id=str(order_line.id),
                                                   product_id=str(product.id), quantity_received=10.0, quantity_accepted=10.0,
                                                   quantity_rejected=0.0)
        ap_service.confirm_receipt(db_session, receipt=receipt)
        receipt.quality_status = "APPROVED"
        db_session.flush()
        ap_service.accept_receipt(db_session, receipt=receipt)

        invoice = ap_service.create_invoice(db_session, company_id=COMPANY, supplier_id=str(supplier.id),
                                            invoice_number="F-003", control_number="C-003")
        ap_service.add_invoice_line(db_session, invoice_id=str(invoice.id), product_id=str(product.id),
                                    quantity=10.0, unit_price=12.0,  # precio distinto → variación
                                    order_line_id=str(order_line.id), receipt_line_id=str(receipt_line.id))
        ap_service.recompute_invoice_total(db_session, invoice=invoice)
        ap_service.transition_invoice(db_session, invoice=invoice, target="VALIDATED")
        invoice, matches = ap_service.match_invoice(db_session, invoice=invoice)
        assert invoice.status == "EXCEPTION"  # variación de precio
        assert len(matches) == 1
        assert matches[0].variance_price == 20.0  # (12-10)*10

    def test_invoice_reverse_linked(self, db_session) -> None:
        supplier = _make_party(db_session)
        product = _make_product(db_session)
        invoice = ap_service.create_invoice(db_session, company_id=COMPANY, supplier_id=str(supplier.id),
                                            invoice_number="F-004", control_number="C-004")
        ap_service.add_invoice_line(db_session, invoice_id=str(invoice.id), product_id=str(product.id), quantity=1.0, unit_price=10.0)
        ap_service.recompute_invoice_total(db_session, invoice=invoice)
        ap_service.transition_invoice(db_session, invoice=invoice, target="VALIDATED")
        ap_service.transition_invoice(db_session, invoice=invoice, target="MATCHED")
        ap_service.transition_invoice(db_session, invoice=invoice, target="APPROVED")
        ap_service.post_invoice(db_session, invoice=invoice)
        # No se puede revertir con saldo pendiente
        with pytest.raises(ConflictError):
            ap_service.reverse_invoice(db_session, invoice=invoice)


class TestCxP:
    def _post_invoice(self, db_session, amount: float = 500.0) -> SupplierInvoice:
        supplier = _make_party(db_session)
        product = _make_product(db_session)
        invoice = ap_service.create_invoice(db_session, company_id=COMPANY, supplier_id=str(supplier.id),
                                            invoice_number=f"F-{abs(hash(amount)) % 10000}", control_number="C")
        ap_service.add_invoice_line(db_session, invoice_id=str(invoice.id), product_id=str(product.id),
                                    quantity=1.0, unit_price=amount)
        ap_service.recompute_invoice_total(db_session, invoice=invoice)
        ap_service.transition_invoice(db_session, invoice=invoice, target="VALIDATED")
        ap_service.transition_invoice(db_session, invoice=invoice, target="MATCHED")
        ap_service.transition_invoice(db_session, invoice=invoice, target="APPROVED")
        ap_service.post_invoice(db_session, invoice=invoice)
        return invoice

    def test_payment_apply_reduces_balance(self, db_session) -> None:
        invoice = self._post_invoice(db_session, 500.0)
        open_item = db_session.query(OpenItem).first()
        payment = ap_service.register_payment(db_session, company_id=COMPANY, party_id=invoice.supplier_id, amount=200.0)
        ap_service.transition_payment(db_session, payment=payment, target="SUBMITTED")
        ap_service.transition_payment(db_session, payment=payment, target="APPROVED", actor="approver-1")
        assert payment.approver_id == "approver-1"
        ap_service.apply_source(db_session, company_id=COMPANY, source_type="PAYMENT", source_id=str(payment.id),
                                target_open_item_id=str(open_item.id), amount=200.0)
        db_session.flush()
        assert ap_service.open_item_balance(open_item) == 300.0
        assert payment.applied == 200.0
        assert open_item.status == "OPEN"

    def test_application_cannot_exceed_balance(self, db_session) -> None:
        invoice = self._post_invoice(db_session, 100.0)
        open_item = db_session.query(OpenItem).first()
        payment = ap_service.register_payment(db_session, company_id=COMPANY, party_id=invoice.supplier_id, amount=500.0)
        with pytest.raises(ConflictError):
            ap_service.apply_source(db_session, company_id=COMPANY, source_type="PAYMENT", source_id=str(payment.id),
                                    target_open_item_id=str(open_item.id), amount=150.0)

    def test_application_cannot_exceed_source(self, db_session) -> None:
        invoice = self._post_invoice(db_session, 1000.0)
        open_item = db_session.query(OpenItem).first()
        payment = ap_service.register_payment(db_session, company_id=COMPANY, party_id=invoice.supplier_id, amount=100.0)
        with pytest.raises(ConflictError):
            ap_service.apply_source(db_session, company_id=COMPANY, source_type="PAYMENT", source_id=str(payment.id),
                                    target_open_item_id=str(open_item.id), amount=200.0)

    def test_full_settle_closes_open_item(self, db_session) -> None:
        invoice = self._post_invoice(db_session, 100.0)
        open_item = db_session.query(OpenItem).first()
        payment = ap_service.register_payment(db_session, company_id=COMPANY, party_id=invoice.supplier_id, amount=100.0)
        ap_service.apply_source(db_session, company_id=COMPANY, source_type="PAYMENT", source_id=str(payment.id),
                                target_open_item_id=str(open_item.id), amount=100.0)
        db_session.flush()
        assert open_item.status == "CLOSED"
        assert invoice.status == "PAID"

    def test_credit_note_reduces_balance(self, db_session) -> None:
        invoice = self._post_invoice(db_session, 500.0)
        open_item = db_session.query(OpenItem).first()
        note = ap_service.create_credit_note(db_session, company_id=COMPANY, supplier_id=invoice.supplier_id,
                                             number="NC-1", amount=80.0, invoice_ref=str(invoice.id))
        ap_service.post_credit_note(db_session, note=note)
        ap_service.apply_source(db_session, company_id=COMPANY, source_type="CREDIT", source_id=str(note.id),
                                target_open_item_id=str(open_item.id), amount=80.0)
        db_session.flush()
        assert ap_service.open_item_balance(open_item) == 420.0
        assert note.applied == 80.0

    def test_advance_apply(self, db_session) -> None:
        invoice = self._post_invoice(db_session, 300.0)
        open_item = db_session.query(OpenItem).first()
        advance = ap_service.register_advance(db_session, company_id=COMPANY, party_id=invoice.supplier_id, amount=100.0)
        assert advance.available == 100.0
        ap_service.apply_source(db_session, company_id=COMPANY, source_type="ADVANCE", source_id=str(advance.id),
                                target_open_item_id=str(open_item.id), amount=100.0)
        db_session.flush()
        assert advance.available == 0.0
        assert ap_service.open_item_balance(open_item) == 200.0

    def test_aging_buckets(self, db_session) -> None:
        self._post_invoice(db_session, 1000.0)
        item = db_session.query(OpenItem).first()
        from datetime import timedelta

        item.due_date = date.today() - timedelta(days=45)
        db_session.flush()
        result = ap_service.aging(db_session, company_id=COMPANY)
        assert result["total"] == 1000.0
        assert result["buckets"]["31-60"] == 1000.0


class TestRetencion:
    def test_withholding_states_and_apply(self, db_session) -> None:
        invoice = TestCxP()._post_invoice(db_session, 1000.0)
        open_item = db_session.query(OpenItem).first()
        withholding = ap_service.create_withholding(db_session, company_id=COMPANY, party_id=invoice.supplier_id,
                                                    tax_type="ISLR", rule_ref="ISLR-RET-15", base=1000.0,
                                                    rate_ref="RATE-15", amount=150.0, source_event=f"INVOICE:{invoice.id}")
        assert withholding.status == "CALCULADA"
        ap_service.transition_withholding(db_session, withholding=withholding, target="PRACTICADA")
        ap_service.apply_source(db_session, company_id=COMPANY, source_type="WITHHOLDING", source_id=str(withholding.id),
                                target_open_item_id=str(open_item.id), amount=150.0)
        db_session.flush()
        assert ap_service.open_item_balance(open_item) == 850.0
        assert withholding.status == "EMITIDA"


class TestMultiempresa:
    def test_tenant_isolation(self, db_session) -> None:
        supplier_a = _make_party(db_session, company=COMPANY, code="SUP-A")
        product_a = _make_product(db_session, company=COMPANY, code="P-A")
        supplier_b = _make_party(db_session, company=OTHER, code="SUP-B")
        # A no puede operar con el proveedor de B
        with pytest.raises(NotFoundError):
            ap_service.create_order(db_session, company_id=COMPANY, code="OC-X", supplier_id=str(supplier_b.id))
        # A no ve los open items de B
        invoice = ap_service.create_invoice(db_session, company_id=COMPANY, supplier_id=str(supplier_a.id),
                                            invoice_number="F-A", control_number="C")
        ap_service.add_invoice_line(db_session, invoice_id=str(invoice.id), product_id=str(product_a.id), quantity=1.0, unit_price=10.0)
        ap_service.recompute_invoice_total(db_session, invoice=invoice)
        db_session.flush()
        assert len(db_session.query(OpenItem).all()) == 0  # aún no postada
