"""Servicios de compras y cuentas por pagar (004).

Requisición → cotización → orden → recepción (invoca el motor de 003) →
factura del proveedor (duplicidad) → conciliación triple → devolución/nota →
CxP (open items, pagos, aplicaciones atómicas, anticipos, retenciones, aging).

Invariantes (Constitución P4/P5/P8, DOC-01 §5, DOC-03 §12):
- Facturas postadas y pagos aprobados son inmutables; corrección por reverso.
- Los saldos de CxP se calculan desde documentos y aplicaciones; nunca se editan.
- Las aplicaciones no exceden el saldo de origen ni destino; operación atómica.
- Las retenciones se refieren a reglas versionadas (motor fiscal en 007).
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.inventory import service as inv_service
from app.modules.organization.models import Warehouse
from app.modules.organization.service import warehouse_in_tenant_scope
from app.modules.purchasing.models import (
    Advance,
    Application,
    GoodsReceipt,
    GoodsReceiptLine,
    OpenItem,
    Payment,
    PaymentInstrument,
    PaymentSchedule,
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseRequisition,
    PurchaseReturn,
    PurchaseReturnLine,
    QuoteLine,
    RequisitionLine,
    SupplierCreditNote,
    SupplierInvoice,
    SupplierInvoiceLine,
    SupplierQuote,
    TripleMatch,
    Withholding,
)
from app.shared import audit as audit_service


def _audit(db: Session, *, action: str, entity_type: str, entity_id: str,
           company_id: str, actor: str | None = None, **kw: Any) -> None:
    """Registra un evento de auditoría de negocio (KAUD-001 → FR-009-022)."""
    audit_service.record_audit(
        db, action=action, entity_type=entity_type, entity_id=entity_id,
        company_id=company_id, user_id=actor, source="API", **kw,
    )

# --------------------------------------------------------------------------- #
# Máquinas de estado (DOC-03 §13)
# --------------------------------------------------------------------------- #
REQUISITION_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"SUBMITTED", "CANCELLED"},
    "SUBMITTED": {"APPROVED", "REJECTED"},
    "APPROVED": {"CLOSED"},
    "REJECTED": set(),
    "CANCELLED": set(),
    "CLOSED": set(),
}

ORDER_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"SUBMITTED", "CANCELLED"},
    "SUBMITTED": {"APPROVED", "REJECTED"},
    "APPROVED": {"PARTIALLY_RECEIVED", "RECEIVED", "CANCELLED"},
    "PARTIALLY_RECEIVED": {"RECEIVED", "CLOSED"},
    "RECEIVED": {"CLOSED"},
    "CLOSED": set(),
    "CANCELLED": set(),
    "REJECTED": set(),
}

RECEIPT_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"CONFIRMED", "CANCELLED"},
    "CONFIRMED": {"QUALITY_PENDING", "ACCEPTED", "PARTIALLY_ACCEPTED", "REJECTED"},
    "QUALITY_PENDING": {"ACCEPTED", "PARTIALLY_ACCEPTED", "REJECTED"},
    "ACCEPTED": {"CLOSED"},
    "PARTIALLY_ACCEPTED": {"CLOSED"},
    "REJECTED": {"CLOSED"},
    "CLOSED": set(),
    "CANCELLED": set(),
}

INVOICE_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"VALIDATED", "CANCELLED"},
    "VALIDATED": {"MATCHED", "EXCEPTION"},
    "MATCHED": {"APPROVED"},
    "EXCEPTION": {"APPROVED", "REJECTED"},
    "APPROVED": {"POSTED"},
    "POSTED": {"PARTIALLY_PAID", "PAID", "REVERSED"},
    "PARTIALLY_PAID": {"PAID", "REVERSED"},
    "PAID": {"REVERSED"},
    "REVERSED": set(),
    "REJECTED": set(),
    "CANCELLED": set(),
}

PAYMENT_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"SUBMITTED", "CANCELLED"},
    "SUBMITTED": {"APPROVED", "REJECTED"},
    "APPROVED": {"POSTED"},
    "POSTED": set(),
    "REJECTED": set(),
    "CANCELLED": set(),
}

WITHHOLDING_TRANSITIONS: dict[str, set[str]] = {
    "CALCULADA": {"PRACTICADA"},
    "PRACTICADA": {"EMITIDA"},
    "EMITIDA": {"DECLARADA"},
    "DECLARADA": {"PAGADA"},
    "PAGADA": {"CONCILIADA"},
    "CONCILIADA": set(),
    "REVERSADA": set(),
}


def _assert_transition(current: str, target: str, transitions: dict[str, set[str]], what: str) -> None:
    if target not in transitions.get(current, set()):
        raise ConflictError(code="INVALID_STATE_TRANSITION", message=f"No se permite pasar {what} de {current} a {target}.")


def _company(company_id: str | None, *, obj: str) -> str:
    if not company_id:
        raise KontrolError(code="COMPANY_REQUIRED", message="Se requiere la empresa para esta operación", status_code=422)
    return company_id


# --------------------------------------------------------------------------- #
# Helpers de dominio
# --------------------------------------------------------------------------- #
def _require_party(db: Session, company_id: str, party_id: str) -> None:
    from app.modules.master_data.models import Party

    party = db.get(Party, party_id)
    if not party or party.company_id != company_id:
        raise NotFoundError(code="PARTY_NOT_FOUND", message="Tercero no encontrado")


def _require_product(db: Session, company_id: str, product_id: str) -> None:
    from app.modules.master_data.models import CatalogItem

    item = db.get(CatalogItem, product_id)
    if not item or item.company_id != company_id:
        raise NotFoundError(code="PRODUCT_NOT_FOUND", message="Producto no encontrado")


def _require_order(db: Session, company_id: str, order_id: str) -> PurchaseOrder:
    order = db.get(PurchaseOrder, order_id)
    if not order or order.company_id != company_id:
        raise NotFoundError(code="ORDER_NOT_FOUND", message="Orden de compra no encontrada")
    return order


def order_allowed_actions(order: PurchaseOrder) -> dict[str, bool]:
    s = order.status
    return {"view": True, "submit": s == "DRAFT", "approve": s == "SUBMITTED", "reject": s == "SUBMITTED",
            "cancel": s in ("DRAFT", "APPROVED"), "receive": s in ("APPROVED", "PARTIALLY_RECEIVED"), "close": s == "RECEIVED"}


def invoice_allowed_actions(invoice: SupplierInvoice) -> dict[str, bool]:
    s = invoice.status
    return {"view": True, "validate": s == "DRAFT", "match": s in ("VALIDATED",), "approve": s in ("MATCHED", "EXCEPTION"),
            "post": s == "APPROVED", "reverse": s in ("POSTED", "PARTIALLY_PAID", "PAID"), "cancel": s == "DRAFT"}


def payment_allowed_actions(payment: Payment) -> dict[str, bool]:
    s = payment.status
    return {"view": True, "submit": s == "DRAFT", "approve": s == "SUBMITTED", "reject": s == "SUBMITTED",
            "post": s == "APPROVED", "cancel": s == "DRAFT"}


# --------------------------------------------------------------------------- #
# Requisición
# --------------------------------------------------------------------------- #
def create_requisition(db: Session, *, company_id: str, code: str, requester_id: str | None = None,
                       cost_center_id: str | None = None, need_date=None, actor: str | None = None) -> PurchaseRequisition:
    company_id = _company(company_id, obj="requisición")
    req = PurchaseRequisition(company_id=company_id, code=code, requester_id=requester_id,
                              cost_center_id=cost_center_id, need_date=need_date, status="DRAFT", created_by=actor)
    db.add(req)
    db.flush()
    return req


def add_requisition_line(db: Session, *, requisition_id: str, product_id: str, quantity: float,
                         unit_id: str | None = None, notes: str | None = None) -> RequisitionLine:
    line = RequisitionLine(requisition_id=requisition_id, product_id=product_id, quantity=quantity,
                           unit_id=unit_id, notes=notes)
    db.add(line)
    db.flush()
    return line


def transition_requisition(db: Session, *, requisition: PurchaseRequisition, target: str,
                           actor: str | None = None) -> PurchaseRequisition:
    _assert_transition(requisition.status, target, REQUISITION_TRANSITIONS, "la requisición")
    requisition.status = target
    requisition.updated_at = datetime.now(UTC)
    db.flush()
    return requisition


# --------------------------------------------------------------------------- #
# Cotización
# --------------------------------------------------------------------------- #
def create_quote(db: Session, *, company_id: str, code: str, supplier_id: str, validity_until=None,
                 currency: str = "VED", terms: str | None = None, actor: str | None = None) -> SupplierQuote:
    company_id = _company(company_id, obj="cotización")
    _require_party(db, company_id, supplier_id)
    quote = SupplierQuote(company_id=company_id, code=code, supplier_id=supplier_id, validity_until=validity_until,
                          currency=currency, terms=terms, status="ACTIVE", created_by=actor)
    db.add(quote)
    db.flush()
    return quote


def add_quote_line(db: Session, *, quote_id: str, product_id: str, quantity: float, unit_price: float,
                   discount: float = 0.0, delivery_days: int | None = None, tax_ref: str | None = None) -> QuoteLine:
    line = QuoteLine(quote_id=quote_id, product_id=product_id, quantity=quantity, unit_price=unit_price,
                     discount=discount, delivery_days=delivery_days, tax_ref=tax_ref)
    db.add(line)
    db.flush()
    return line


# --------------------------------------------------------------------------- #
# Orden de compra
# --------------------------------------------------------------------------- #
def create_order(db: Session, *, company_id: str, code: str, supplier_id: str, terms: str | None = None,
                 expected_date=None, currency: str = "VED", actor: str | None = None) -> PurchaseOrder:
    company_id = _company(company_id, obj="orden")
    _require_party(db, company_id, supplier_id)
    order = PurchaseOrder(company_id=company_id, code=code, supplier_id=supplier_id, terms=terms,
                          expected_date=expected_date, currency=currency, status="DRAFT", created_by=actor)
    db.add(order)
    db.flush()
    return order


def add_order_line(db: Session, *, order_id: str, product_id: str, quantity_ordered: float, unit_price: float,
                   discount: float = 0.0, tax_ref: str | None = None, needs_inventory: bool = True,
                   snapshot: str | None = None) -> PurchaseOrderLine:
    if quantity_ordered <= 0:
        raise KontrolError(code="INVALID_QUANTITY", message="La cantidad ordenada debe ser positiva", status_code=422)
    line = PurchaseOrderLine(order_id=order_id, product_id=product_id, quantity_ordered=quantity_ordered,
                             quantity_received=0.0, unit_price=unit_price, discount=discount, tax_ref=tax_ref,
                             needs_inventory=needs_inventory, snapshot=snapshot)
    db.add(line)
    db.flush()
    return line


def transition_order(db: Session, *, order: PurchaseOrder, target: str, actor: str | None = None,
                     approval_ref: str | None = None) -> PurchaseOrder:
    _assert_transition(order.status, target, ORDER_TRANSITIONS, "la orden")
    order.status = target
    order.updated_at = datetime.now(UTC)
    if target == "APPROVED":
        order.approval_ref = approval_ref or order.approval_ref
    db.flush()
    _audit(db, action="PURCHASE_ORDER_TRANSITIONED", entity_type="PurchaseOrder", entity_id=str(order.id),
           company_id=order.company_id, actor=actor, after={"target": order.status})
    return order


# --------------------------------------------------------------------------- #
# Recepción (invoca el motor de inventario de 003)
# --------------------------------------------------------------------------- #
def create_receipt(db: Session, *, company_id: str, code: str, order_id: str, warehouse_id: str,
                   actor: str | None = None) -> GoodsReceipt:
    company_id = _company(company_id, obj="recepción")
    order = _require_order(db, company_id, order_id)
    if order.status not in ("APPROVED", "PARTIALLY_RECEIVED", "RECEIVED"):
        raise ConflictError(code="ORDER_NOT_RECEIVABLE", message="La orden no está en estado para recibirse.")
    warehouse = db.get(Warehouse, warehouse_id)
    if not warehouse or not warehouse_in_tenant_scope(db, company_id, warehouse):
        raise NotFoundError(code="WAREHOUSE_NOT_FOUND", message="Almacén no encontrado")
    receipt = GoodsReceipt(company_id=company_id, code=code, order_id=order_id, warehouse_id=warehouse_id,
                           status="DRAFT", quality_status="PENDING", created_by=actor)
    db.add(receipt)
    db.flush()
    return receipt


def add_receipt_line(db: Session, *, receipt_id: str, order_line_id: str, product_id: str, quantity_received: float,
                     quantity_accepted: float, quantity_rejected: float, lot_number: str | None = None,
                     expiry_date=None, serials: list[str] | None = None) -> GoodsReceiptLine:
    if quantity_received <= 0:
        raise KontrolError(code="INVALID_QUANTITY", message="La cantidad recibida debe ser positiva", status_code=422)
    line = GoodsReceiptLine(receipt_id=receipt_id, order_line_id=order_line_id, product_id=product_id,
                            quantity_received=quantity_received, quantity_accepted=quantity_accepted,
                            quantity_rejected=quantity_rejected, lot_number=lot_number, expiry_date=expiry_date,
                            serials=serials, quality="PENDING")
    db.add(line)
    db.flush()
    return line


def confirm_receipt(db: Session, *, receipt: GoodsReceipt, actor: str | None = None) -> GoodsReceipt:
    _assert_transition(receipt.status, "CONFIRMED", RECEIPT_TRANSITIONS, "la recepción")
    receipt.status = "CONFIRMED"
    receipt.updated_at = datetime.now(UTC)
    db.flush()
    return receipt


def accept_receipt(db: Session, *, receipt: GoodsReceipt, actor: str | None = None) -> GoodsReceipt:
    """Acepta la recepción y registra entradas en el motor de 003 (FR-004-033).

    Para cada línea aceptada con inventario: crea lote/seriales (si aplica) y
    registra el movimiento de entrada con el costo de la orden. No duplica la
    lógica de saldos de 003.
    """
    _assert_transition(receipt.status, "ACCEPTED", RECEIPT_TRANSITIONS, "la recepción")
    if receipt.quality_status != "APPROVED":
        raise ConflictError(code="QUALITY_NOT_APPROVED", message="La recepción requiere control de calidad aprobado.")
    lines = db.execute(select(GoodsReceiptLine).where(GoodsReceiptLine.receipt_id == receipt.id)).scalars().all()
    for line in lines:
        if line.quantity_accepted > 0:
            order_line = db.get(PurchaseOrderLine, line.order_line_id)
            if order_line and order_line.needs_inventory:
                inv_service._require_product(db, receipt.company_id, line.product_id)
                lot_id = None
                if line.lot_number:
                    lot = inv_service.create_lot(db, company_id=receipt.company_id, product_id=line.product_id,
                                                 lot_number=line.lot_number, expiry_date=line.expiry_date,
                                                 receipt_ref=f"RECEIPT:{receipt.id}", actor=actor)
                    lot_id = str(lot.id)
                for serial in (line.serials or "").split(",") if line.serials else []:
                    serial = serial.strip()
                    if serial:
                        inv_service.create_serial(db, company_id=receipt.company_id, product_id=line.product_id,
                                                  serial=serial, lot_id=lot_id, warehouse_id=receipt.warehouse_id, actor=actor)
                mtype = inv_service._get_movement_type_by_code(db, receipt.company_id, "ENTRADA_RECEPCION")
                inv_service.record_movement(
                    db, company_id=receipt.company_id, warehouse_id=receipt.warehouse_id, product_id=line.product_id,
                    movement_type_id=str(mtype.id), quantity=line.quantity_accepted,
                    unit_cost=order_line.unit_price if order_line else None, currency="VED",
                    document_ref=f"RECEIPT:{receipt.id}", actor=actor,
                )
            # Acumular recibido en la línea de orden
            if order_line:
                order_line.quantity_received = round(order_line.quantity_received + line.quantity_accepted, 6)
    receipt.status = "ACCEPTED"
    receipt.updated_at = datetime.now(UTC)
    db.flush()
    _sync_order_status(db, receipt.order_id)
    _audit(db, action="RECEIPT_ACCEPTED", entity_type="GoodsReceipt", entity_id=str(receipt.id),
           company_id=receipt.company_id, actor=actor, after={"order_id": str(receipt.order_id)})
    return receipt


def reject_receipt(db: Session, *, receipt: GoodsReceipt, actor: str | None = None) -> GoodsReceipt:
    _assert_transition(receipt.status, "REJECTED", RECEIPT_TRANSITIONS, "la recepción")
    receipt.status = "REJECTED"
    receipt.updated_at = datetime.now(UTC)
    db.flush()
    return receipt


def _sync_order_status(db: Session, order_id: str) -> None:
    order = db.get(PurchaseOrder, order_id)
    if not order or order.status in ("CLOSED", "CANCELLED"):
        return
    lines = db.execute(select(PurchaseOrderLine).where(PurchaseOrderLine.order_id == order_id)).scalars().all()
    total = sum(line.quantity_ordered for line in lines)
    received = sum(line.quantity_received for line in lines)
    if total > 0 and received >= total:
        order.status = "RECEIVED"
    elif received > 0:
        order.status = "PARTIALLY_RECEIVED"
    order.updated_at = datetime.now(UTC)


# --------------------------------------------------------------------------- #
# Factura del proveedor (duplicidad + estados)
# --------------------------------------------------------------------------- #
def create_invoice(db: Session, *, company_id: str, supplier_id: str, invoice_number: str,
                   control_number: str | None = None, issue_date=None, currency: str = "VED",
                   actor: str | None = None, idempotency_key: str | None = None) -> SupplierInvoice:
    company_id = _company(company_id, obj="factura")
    _require_party(db, company_id, supplier_id)
    if idempotency_key:
        existing = db.execute(select(SupplierInvoice).where(SupplierInvoice.idempotency_key == idempotency_key)).scalars().first()
        if existing:
            return existing
    dup = (
        db.execute(
            select(SupplierInvoice).where(
                SupplierInvoice.company_id == company_id,
                SupplierInvoice.supplier_id == supplier_id,
                SupplierInvoice.invoice_number == invoice_number,
                SupplierInvoice.control_number.is_(None) if control_number is None else SupplierInvoice.control_number == control_number,
            )
        )
        .scalars()
        .first()
    )
    if dup and dup.status != "REVERSED":
        raise ConflictError(code="INVOICE_DUPLICATE", message="Ya existe una factura del proveedor con ese número y control.")
    invoice = SupplierInvoice(company_id=company_id, supplier_id=supplier_id, invoice_number=invoice_number,
                              control_number=control_number, issue_date=issue_date, currency=currency,
                              status="DRAFT", created_by=actor, idempotency_key=idempotency_key)
    db.add(invoice)
    db.flush()
    return invoice


def add_invoice_line(db: Session, *, invoice_id: str, product_id: str, quantity: float, unit_price: float,
                     tax_amount: float = 0.0, order_line_id: str | None = None, receipt_line_id: str | None = None,
                     snapshot: str | None = None) -> SupplierInvoiceLine:
    line = SupplierInvoiceLine(invoice_id=invoice_id, order_line_id=order_line_id, receipt_line_id=receipt_line_id,
                               product_id=product_id, quantity=quantity, unit_price=unit_price,
                               tax_amount=tax_amount, total=round(quantity * unit_price + tax_amount, 6), snapshot=snapshot)
    db.add(line)
    db.flush()
    return line


def recompute_invoice_total(db: Session, *, invoice: SupplierInvoice) -> SupplierInvoice:
    lines = db.execute(select(SupplierInvoiceLine).where(SupplierInvoiceLine.invoice_id == invoice.id)).scalars().all()
    invoice.total = round(sum(float(line.total) for line in lines), 6)
    invoice.tax_total = round(sum(float(line.tax_amount) for line in lines), 6)
    db.flush()
    return invoice


def transition_invoice(db: Session, *, invoice: SupplierInvoice, target: str, actor: str | None = None) -> SupplierInvoice:
    _assert_transition(invoice.status, target, INVOICE_TRANSITIONS, "la factura")
    invoice.status = target
    invoice.updated_at = datetime.now(UTC)
    db.flush()
    _audit(db, action="SUPPLIER_INVOICE_TRANSITIONED", entity_type="SupplierInvoice", entity_id=str(invoice.id),
           company_id=invoice.company_id, actor=actor, after={"target": invoice.status, "total": float(invoice.total or 0.0)})
    return invoice


def match_invoice(db: Session, *, invoice: SupplierInvoice, actor: str | None = None) -> tuple[SupplierInvoice, list[TripleMatch]]:
    """Calcula la conciliación triple orden/recepción/factura (FR-004-050/051)."""
    _assert_transition(invoice.status, "MATCHED", INVOICE_TRANSITIONS, "la factura")
    lines = db.execute(select(SupplierInvoiceLine).where(SupplierInvoiceLine.invoice_id == invoice.id)).scalars().all()
    matches: list[TripleMatch] = []
    has_variance = False
    for line in lines:
        order_line = db.get(PurchaseOrderLine, line.order_line_id) if line.order_line_id else None
        variance_qty = round(line.quantity - (order_line.quantity_received if order_line else line.quantity), 6)
        variance_price = round((float(line.unit_price) - float(order_line.unit_price)) * float(line.quantity), 6) if order_line else 0.0
        variance_tax = round(float(line.tax_amount) - ((float(order_line.unit_price) * float(line.quantity) * 0.0) if order_line else 0.0), 6)
        match = TripleMatch(company_id=invoice.company_id, invoice_id=str(invoice.id),
                            order_line_id=line.order_line_id, receipt_line_id=line.receipt_line_id,
                            invoice_line_id=str(line.id), variance_qty=variance_qty,
                            variance_price=variance_price, variance_tax=variance_tax,
                            resolution="PENDING", approved_by=actor)
        db.add(match)
        matches.append(match)
        if abs(variance_qty) > 1e-6 or abs(variance_price) > 1e-6 or abs(variance_tax) > 1e-6:
            has_variance = True
    invoice.status = "EXCEPTION" if has_variance else "MATCHED"
    invoice.updated_at = datetime.now(UTC)
    db.flush()
    return invoice, matches


def post_invoice(db: Session, *, invoice: SupplierInvoice, actor: str | None = None,
                 due_days: int | None = None) -> SupplierInvoice:
    """Posta la factura y crea el OpenItem (PAYABLE) (FR-004-042/070)."""
    _assert_transition(invoice.status, "POSTED", INVOICE_TRANSITIONS, "la factura")
    open_item = OpenItem(company_id=invoice.company_id, party_id=invoice.supplier_id,
                         source_document=f"INVOICE:{invoice.id}", item_type="PAYABLE", currency=invoice.currency,
                         original=invoice.total, applied=0.0,
                         due_date=(date.today() + timedelta(days=due_days)) if due_days else None,
                         status="OPEN")
    db.add(open_item)
    db.flush()
    invoice.status = "POSTED"
    invoice.updated_at = datetime.now(UTC)
    db.flush()
    _audit(db, action="SUPPLIER_INVOICE_POSTED", entity_type="SupplierInvoice", entity_id=str(invoice.id),
           company_id=invoice.company_id, actor=actor, after={"total": float(invoice.total or 0.0)})
    return invoice


def reverse_invoice(db: Session, *, invoice: SupplierInvoice, actor: str | None = None) -> SupplierInvoice:
    """Reverso vinculado de una factura postada (P5): crea una factura inversa."""
    _assert_transition(invoice.status, "REVERSED", INVOICE_TRANSITIONS, "la factura")
    open_items = db.execute(
        select(OpenItem).where(OpenItem.company_id == invoice.company_id, OpenItem.source_document == f"INVOICE:{invoice.id}")
    ).scalars().all()
    for item in open_items:
        if item.status == "OPEN":
            raise ConflictError(code="OPEN_ITEM_NOT_SETTLED", message="No se puede revertir la factura con saldo pendiente.")
    invoice.status = "REVERSED"
    invoice.reversed_by_id = actor
    invoice.updated_at = datetime.now(UTC)
    db.flush()
    _audit(db, action="SUPPLIER_INVOICE_REVERSED", entity_type="SupplierInvoice", entity_id=str(invoice.id),
           company_id=invoice.company_id, actor=actor)
    return invoice


# --------------------------------------------------------------------------- #
# Devoluciones y notas de crédito
# --------------------------------------------------------------------------- #
def create_return(db: Session, *, company_id: str, code: str, source_document: str | None, reason: str,
                  condition: str = "DEFECTUOSO", inventory_destination: str = "CUARENTENA",
                  actor: str | None = None) -> PurchaseReturn:
    company_id = _company(company_id, obj="devolución")
    ret = PurchaseReturn(company_id=company_id, code=code, source_document=source_document, reason=reason,
                         condition=condition, inventory_destination=inventory_destination, status="DRAFT", created_by=actor)
    db.add(ret)
    db.flush()
    return ret


def add_return_line(db: Session, *, return_id: str, product_id: str, quantity: float,
                    condition: str = "DEFECTUOSO") -> PurchaseReturnLine:
    line = PurchaseReturnLine(return_id=return_id, product_id=product_id, quantity=quantity, condition=condition)
    db.add(line)
    db.flush()
    return line


def create_credit_note(db: Session, *, company_id: str, supplier_id: str, number: str, amount: float,
                       invoice_ref: str | None = None, currency: str = "VED",
                       actor: str | None = None) -> SupplierCreditNote:
    company_id = _company(company_id, obj="nota de crédito")
    _require_party(db, company_id, supplier_id)
    if amount <= 0:
        raise KontrolError(code="INVALID_AMOUNT", message="El monto de la nota debe ser positivo", status_code=422)
    note = SupplierCreditNote(company_id=company_id, supplier_id=supplier_id, invoice_ref=invoice_ref,
                              number=number, amount=amount, applied=0.0, currency=currency, status="DRAFT", created_by=actor)
    db.add(note)
    db.flush()
    return note


def post_credit_note(db: Session, *, note: SupplierCreditNote) -> SupplierCreditNote:
    if note.status != "DRAFT":
        raise ConflictError(code="CREDIT_NOTE_STATE", message="La nota de crédito ya fue postada.")
    note.status = "POSTED"
    note.updated_at = datetime.now(UTC)
    db.flush()
    _audit(db, action="SUPPLIER_CREDIT_NOTE_POSTED", entity_type="SupplierCreditNote", entity_id=str(note.id),
           company_id=note.company_id, actor=None, after={"amount": float(note.amount)})
    return note


# --------------------------------------------------------------------------- #
# CxP — open items, pagos, aplicaciones, anticipos, retenciones, aging
# --------------------------------------------------------------------------- #
def open_item_balance(item: OpenItem) -> float:
    return round(float(item.original) - float(item.applied), 6)


def register_payment(db: Session, *, company_id: str, party_id: str, amount: float, currency: str = "VED",
                     instruments: list[dict] | None = None, actor: str | None = None,
                     idempotency_key: str | None = None, direction: str = "OUT") -> Payment:
    company_id = _company(company_id, obj="pago")
    _require_party(db, company_id, party_id)
    if amount <= 0:
        raise KontrolError(code="INVALID_AMOUNT", message="El monto del pago debe ser positivo", status_code=422)
    if idempotency_key:
        existing = db.execute(select(Payment).where(Payment.idempotency_key == idempotency_key)).scalars().first()
        if existing:
            return existing
    payment = Payment(company_id=company_id, party_id=party_id, direction=direction, currency=currency,
                      amount=amount, applied=0.0, status="DRAFT", created_by=actor, idempotency_key=idempotency_key)
    db.add(payment)
    db.flush()
    for inst in instruments or []:
        db.add(PaymentInstrument(payment_id=str(payment.id), method=inst.get("method", "TRANSFERENCIA"),
                                 account=inst.get("account"), currency=inst.get("currency", currency),
                                 amount=inst.get("amount", amount), rate=inst.get("rate"),
                                 reference=inst.get("reference"), value_date=inst.get("value_date")))
    db.flush()
    return payment


def transition_payment(db: Session, *, payment: Payment, target: str, actor: str | None = None) -> Payment:
    _assert_transition(payment.status, target, PAYMENT_TRANSITIONS, "el pago")
    payment.status = target
    payment.updated_at = datetime.now(UTC)
    if target in ("APPROVED", "REJECTED"):
        payment.approver_id = actor
    db.flush()
    _audit(db, action="PAYMENT_TRANSITIONED", entity_type="Payment", entity_id=str(payment.id),
           company_id=payment.company_id, actor=actor, after={"target": payment.status, "amount": float(payment.amount)})
    return payment


def _source_available(db: Session, *, source_type: str, source_id: str) -> float:
    if source_type == "PAYMENT":
        p = db.get(Payment, source_id)
        return round(float(p.amount) - float(p.applied), 6) if p else 0.0
    if source_type == "ADVANCE":
        a = db.get(Advance, source_id)
        return round(float(a.available), 6) if a else 0.0
    if source_type == "CREDIT":
        c = db.get(SupplierCreditNote, source_id)
        return round(float(c.amount) - float(c.applied), 6) if c else 0.0
    if source_type == "WITHHOLDING":
        w = db.get(Withholding, source_id)
        return w.amount if w and w.status not in ("REVERSADA",) else 0.0
    raise KontrolError(code="INVALID_SOURCE_TYPE", message="Tipo de fuente de aplicación no válido", status_code=422)


def _reduce_source(db: Session, *, source_type: str, source_id: str, amount: float) -> None:
    if source_type == "PAYMENT":
        p = db.get(Payment, source_id)
        if p:
            p.applied = round(float(p.applied) + amount, 6)
    elif source_type == "ADVANCE":
        a = db.get(Advance, source_id)
        if a:
            a.available = round(max(float(a.available) - amount, 0.0), 6)
    elif source_type == "CREDIT":
        c = db.get(SupplierCreditNote, source_id)
        if c:
            c.applied = round(float(c.applied) + amount, 6)
    elif source_type == "WITHHOLDING":
        w = db.get(Withholding, source_id)
        if w and w.status == "PRACTICADA":
            w.status = "EMITIDA"


def apply_source(db: Session, *, company_id: str, source_type: str, source_id: str, target_open_item_id: str,
                 amount: float, currency: str = "VED", rate: float | None = None, actor: str | None = None) -> Application:
    """Aplica una fuente (pago/anticipo/nota/retención) a un open item (FR-004-073).

    Atómica: no excede el saldo de origen ni de destino. Reduce ambos saldos.
    """
    company_id = _company(company_id, obj="aplicación")
    if amount <= 0:
        raise KontrolError(code="INVALID_AMOUNT", message="El monto a aplicar debe ser positivo", status_code=422)
    target = db.get(OpenItem, target_open_item_id)
    if not target or target.company_id != company_id:
        raise NotFoundError(code="OPEN_ITEM_NOT_FOUND", message="Documento de CxP no encontrado")
    if target.status != "OPEN":
        raise ConflictError(code="OPEN_ITEM_CLOSED", message="El documento de CxP está cerrado.")
    balance = open_item_balance(target)
    if amount > balance:
        raise ConflictError(code="APPLICATION_EXCEEDS_BALANCE", message=f"La aplicación excede el saldo disponible ({balance}).")
    available = _source_available(db, source_type=source_type, source_id=source_id)
    if amount > available:
        raise ConflictError(code="APPLICATION_EXCEEDS_SOURCE", message=f"La fuente no tiene saldo disponible ({available}).")

    target.applied = round(float(target.applied) + amount, 6)
    if open_item_balance(target) <= 1e-6:
        target.status = "CLOSED"
    _reduce_source(db, source_type=source_type, source_id=source_id, amount=amount)
    app = Application(company_id=company_id, source_type=source_type, source_id=source_id,
                      target_open_item_id=target_open_item_id, amount=amount, currency=currency,
                      rate=rate, date=date.today(), status="APPLIED")
    db.add(app)
    db.flush()
    _sync_invoice_paid(db, target_open_item_id=str(target.id))
    _audit(db, action="CXP_APPLICATION", entity_type="OpenItem", entity_id=str(target_open_item_id),
           company_id=company_id, actor=actor, after={"source_type": source_type, "amount": float(amount)})
    return app


def _sync_invoice_paid(db: Session, *, target_open_item_id: str) -> None:
    item = db.get(OpenItem, target_open_item_id)
    if not item:
        return
    if item.source_document and item.source_document.startswith("INVOICE:"):
        invoice_id = item.source_document.split(":", 1)[1]
        invoice = db.get(SupplierInvoice, invoice_id)
        if invoice and invoice.status in ("POSTED", "PARTIALLY_PAID"):
            invoice.status = "PAID" if open_item_balance(item) <= 1e-6 else "PARTIALLY_PAID"
            invoice.updated_at = datetime.now(UTC)


def register_advance(db: Session, *, company_id: str, party_id: str, amount: float, currency: str = "VED",
                     actor: str | None = None, direction: str = "OUT") -> Advance:
    company_id = _company(company_id, obj="anticipo")
    _require_party(db, company_id, party_id)
    if amount <= 0:
        raise KontrolError(code="INVALID_AMOUNT", message="El monto del anticipo debe ser positivo", status_code=422)
    adv = Advance(company_id=company_id, party_id=party_id, direction=direction, currency=currency,
                  amount=amount, available=amount, status="ACTIVE", created_by=actor)
    db.add(adv)
    db.flush()
    return adv


def create_withholding(db: Session, *, company_id: str, party_id: str, tax_type: str, rule_ref: str | None,
                       base: float, rate_ref: str | None, amount: float, period: str | None = None,
                       source_event: str | None = None, actor: str | None = None) -> Withholding:
    company_id = _company(company_id, obj="retención")
    _require_party(db, company_id, party_id)
    withholding = Withholding(company_id=company_id, party_id=party_id, source_event=source_event, tax_type=tax_type,
                              rule_ref=rule_ref, base=base, rate_ref=rate_ref, amount=amount, period=period,
                              status="CALCULADA", created_by=actor)
    db.add(withholding)
    db.flush()
    return withholding


def transition_withholding(db: Session, *, withholding: Withholding, target: str) -> Withholding:
    _assert_transition(withholding.status, target, WITHHOLDING_TRANSITIONS, "la retención")
    withholding.status = target
    withholding.updated_at = datetime.now(UTC)
    db.flush()
    _audit(db, action="WITHHOLDING_TRANSITIONED", entity_type="Withholding", entity_id=str(withholding.id),
           company_id=withholding.company_id, actor=None, after={"target": withholding.status})
    return withholding


def aging(db: Session, *, company_id: str, party_id: str | None = None, item_type: str = "PAYABLE") -> dict:
    """Aging por buckets de vencimiento (FR-004-075). `item_type` permite PAYABLE (CxP) o RECEIVABLE (CxC)."""
    query = select(OpenItem).where(OpenItem.company_id == company_id, OpenItem.item_type == item_type, OpenItem.status == "OPEN")
    if party_id:
        query = query.where(OpenItem.party_id == party_id)
    items = db.execute(query).scalars().all()
    today = date.today()
    buckets = {"0-30": 0.0, "31-60": 0.0, "61-90": 0.0, "90+": 0.0}
    total = 0.0
    for item in items:
        balance = open_item_balance(item)
        total += balance
        if balance <= 0:
            continue
        if not item.due_date:
            buckets["90+"] += balance
        else:
            days = (today - item.due_date).days
            if days <= 30:
                buckets["0-30"] += balance
            elif days <= 60:
                buckets["31-60"] += balance
            elif days <= 90:
                buckets["61-90"] += balance
            else:
                buckets["90+"] += balance
    return {"total": round(total, 6), "buckets": {k: round(v, 6) for k, v in buckets.items()}}


def create_schedule(db: Session, *, company_id: str, party_id: str, due_date, amount: float,
                    actor: str | None = None) -> PaymentSchedule:
    company_id = _company(company_id, obj="programación")
    _require_party(db, company_id, party_id)
    schedule = PaymentSchedule(company_id=company_id, party_id=party_id, due_date=due_date,
                               amount=amount, status="PENDING", created_by=actor)
    db.add(schedule)
    db.flush()
    return schedule


# --------------------------------------------------------------------------- #
# Helpers de serialización
# --------------------------------------------------------------------------- #
def invoice_dict(invoice: SupplierInvoice) -> dict:
    return {"id": invoice.id, "supplier_id": invoice.supplier_id, "invoice_number": invoice.invoice_number,
            "control_number": invoice.control_number,
            "issue_date": invoice.issue_date.isoformat() if invoice.issue_date else None,
            "currency": invoice.currency, "tax_total": invoice.tax_total, "total": invoice.total,
            "status": invoice.status, "reversed_by_id": invoice.reversed_by_id,
            "allowed_actions": invoice_allowed_actions(invoice)}


def order_dict(db: Session, order: PurchaseOrder) -> dict:
    lines = db.execute(select(PurchaseOrderLine).where(PurchaseOrderLine.order_id == order.id)).scalars().all()
    return {"id": order.id, "code": order.code, "supplier_id": order.supplier_id, "terms": order.terms,
            "expected_date": order.expected_date.isoformat() if order.expected_date else None,
            "currency": order.currency, "status": order.status, "approval_ref": order.approval_ref,
            "allowed_actions": order_allowed_actions(order),
            "lines": [{"id": line.id, "product_id": line.product_id, "quantity_ordered": line.quantity_ordered,
                       "quantity_received": line.quantity_received, "unit_price": line.unit_price,
                       "needs_inventory": line.needs_inventory} for line in lines]}


def payment_dict(payment: Payment) -> dict:
    return {"id": payment.id, "party_id": payment.party_id, "direction": payment.direction,
            "date": payment.date.isoformat() if payment.date else None, "currency": payment.currency,
            "amount": payment.amount, "applied": payment.applied, "status": payment.status,
            "approver_id": payment.approver_id, "allowed_actions": payment_allowed_actions(payment)}


def open_item_dict(item: OpenItem) -> dict:
    return {"id": item.id, "party_id": item.party_id, "source_document": item.source_document,
            "item_type": item.item_type, "currency": item.currency, "original": item.original,
            "applied": item.applied, "balance": open_item_balance(item),
            "due_date": item.due_date.isoformat() if item.due_date else None, "status": item.status}
