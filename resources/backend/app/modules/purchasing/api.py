"""API de compras y cuentas por pagar (004).

Endpoints REST `/purchasing/*` con convenciones heredadas de 001 (DOC-03 §14):
errores uniformes, `allowed_actions` en backend, transiciones explícitas,
idempotencia en POST críticos.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission, require_write_allowed
from app.core.errors import NotFoundError
from app.modules.identity_access.models import User
from app.modules.purchasing import service as ap_service
from app.modules.purchasing.models import (
    GoodsReceipt,
    OpenItem,
    Payment,
    PurchaseOrder,
    PurchaseRequisition,
    PurchaseReturn,
    SupplierCreditNote,
    SupplierInvoice,
    SupplierQuote,
    TripleMatch,
    Withholding,
)

router = APIRouter(prefix="/purchasing", tags=["compras"])


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #
class RequisitionCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    requester_id: str | None = None
    cost_center_id: str | None = None
    need_date: date | None = None


class RequisitionLineCreate(BaseModel):
    product_id: str
    quantity: float = Field(gt=0)
    unit_id: str | None = None
    notes: str | None = None


class QuoteCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    supplier_id: str
    validity_until: date | None = None
    currency: str = "VED"
    terms: str | None = None


class QuoteLineCreate(BaseModel):
    product_id: str
    quantity: float = Field(gt=0)
    unit_price: float = Field(ge=0)
    discount: float = 0.0
    delivery_days: int | None = None
    tax_ref: str | None = None


class OrderCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    supplier_id: str
    terms: str | None = None
    expected_date: date | None = None
    currency: str = "VED"


class OrderLineCreate(BaseModel):
    product_id: str
    quantity_ordered: float = Field(gt=0)
    unit_price: float = Field(ge=0)
    discount: float = 0.0
    tax_ref: str | None = None
    needs_inventory: bool = True
    snapshot: str | None = None


class ReceiptCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    order_id: str
    warehouse_id: str


class ReceiptLineCreate(BaseModel):
    order_line_id: str
    product_id: str
    quantity_received: float = Field(gt=0)
    quantity_accepted: float
    quantity_rejected: float
    lot_number: str | None = None
    expiry_date: date | None = None
    serials: list[str] | None = None


class QualityBody(BaseModel):
    quality_status: str = Field(pattern="^(APPROVED|REJECTED)$")


class InvoiceCreate(BaseModel):
    supplier_id: str
    invoice_number: str = Field(min_length=1, max_length=120)
    control_number: str | None = None
    issue_date: date | None = None
    currency: str = "VED"
    idempotency_key: str | None = None


class InvoiceLineCreate(BaseModel):
    product_id: str
    quantity: float = Field(gt=0)
    unit_price: float = Field(ge=0)
    tax_amount: float = 0.0
    order_line_id: str | None = None
    receipt_line_id: str | None = None
    snapshot: str | None = None


class TransitionBody(BaseModel):
    target: str
    approval_ref: str | None = None


class ReturnCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    source_document: str | None = None
    reason: str = Field(min_length=3, max_length=2000)
    condition: str = "DEFECTUOSO"
    inventory_destination: str = "CUARENTENA"


class ReturnLineCreate(BaseModel):
    product_id: str
    quantity: float = Field(gt=0)
    condition: str = "DEFECTUOSO"


class CreditNoteCreate(BaseModel):
    supplier_id: str
    number: str = Field(min_length=1, max_length=120)
    amount: float = Field(gt=0)
    invoice_ref: str | None = None
    currency: str = "VED"


class PaymentCreate(BaseModel):
    party_id: str
    amount: float = Field(gt=0)
    currency: str = "VED"
    instruments: list[dict] | None = None
    idempotency_key: str | None = None


class ApplicationCreate(BaseModel):
    source_type: str = Field(pattern="^(PAYMENT|ADVANCE|CREDIT|WITHHOLDING)$")
    source_id: str
    target_open_item_id: str
    amount: float = Field(gt=0)
    currency: str = "VED"
    rate: float | None = None


class AdvanceCreate(BaseModel):
    party_id: str
    amount: float = Field(gt=0)
    currency: str = "VED"


class WithholdingCreate(BaseModel):
    party_id: str
    tax_type: str = Field(pattern="^(IVA|ISLR)$")
    rule_ref: str | None = None
    base: float = 0.0
    rate_ref: str | None = None
    amount: float
    period: str | None = None
    source_event: str | None = None


class ScheduleCreate(BaseModel):
    party_id: str
    due_date: date | None = None
    amount: float = Field(gt=0)


# --------------------------------------------------------------------------- #
# Requisiciones
# --------------------------------------------------------------------------- #
@router.get("/requisitions")
def list_requisitions(status: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                      db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = select(PurchaseRequisition).where(PurchaseRequisition.company_id == user.tenant_id)
    if status:
        query = query.where(PurchaseRequisition.status == status)
    total = db.execute(select(func.count()).select_from(query.subquery())).scalar() or 0
    items = db.execute(query.order_by(PurchaseRequisition.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return {"items": [{"id": r.id, "code": r.code, "requester_id": r.requester_id, "cost_center_id": r.cost_center_id,
                       "need_date": r.need_date.isoformat() if r.need_date else None, "status": r.status} for r in items],
            "total": total, "page": page, "page_size": page_size}


@router.post("/requisitions", dependencies=[Depends(require_write_allowed)])
def create_requisition(body: RequisitionCreate, db: Session = Depends(get_db),
                       actor: User = Depends(require_permission("compras", "create"))):
    req = ap_service.create_requisition(db, company_id=actor.tenant_id, code=body.code, requester_id=body.requester_id,
                                        cost_center_id=body.cost_center_id, need_date=body.need_date, actor=str(actor.id))
    db.commit()
    db.refresh(req)
    return {"id": req.id, "code": req.code, "status": req.status}


@router.post("/requisitions/{req_id}/lines", dependencies=[Depends(require_write_allowed)])
def add_requisition_line(req_id: str, body: RequisitionLineCreate, db: Session = Depends(get_db),
                         actor: User = Depends(require_permission("compras", "create"))):
    req = _owned(db, PurchaseRequisition, req_id, actor.tenant_id, "REQUISITION_NOT_FOUND", "Requisición no encontrada")
    line = ap_service.add_requisition_line(db, requisition_id=str(req.id), product_id=body.product_id,
                                           quantity=body.quantity, unit_id=body.unit_id, notes=body.notes)
    db.commit()
    db.refresh(line)
    return {"id": line.id, "product_id": line.product_id, "quantity": line.quantity}


@router.post("/requisitions/{req_id}/transition", dependencies=[Depends(require_write_allowed)])
def transition_requisition(req_id: str, body: TransitionBody, db: Session = Depends(get_db),
                           actor: User = Depends(require_permission("compras", "approve"))):
    req = _owned(db, PurchaseRequisition, req_id, actor.tenant_id, "REQUISITION_NOT_FOUND", "Requisición no encontrada")
    ap_service.transition_requisition(db, requisition=req, target=body.target, actor=str(actor.id))
    db.commit()
    db.refresh(req)
    return {"id": req.id, "status": req.status}


# --------------------------------------------------------------------------- #
# Cotizaciones
# --------------------------------------------------------------------------- #
@router.get("/quotes")
def list_quotes(supplier_id: str | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = select(SupplierQuote).where(SupplierQuote.company_id == user.tenant_id)
    if supplier_id:
        query = query.where(SupplierQuote.supplier_id == supplier_id)
    items = db.execute(query.order_by(SupplierQuote.created_at.desc())).scalars().all()
    return {"items": [{"id": q.id, "code": q.code, "supplier_id": q.supplier_id, "currency": q.currency,
                       "validity_until": q.validity_until.isoformat() if q.validity_until else None, "status": q.status} for q in items],
            "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/quotes", dependencies=[Depends(require_write_allowed)])
def create_quote(body: QuoteCreate, db: Session = Depends(get_db),
                 actor: User = Depends(require_permission("compras", "create"))):
    quote = ap_service.create_quote(db, company_id=actor.tenant_id, code=body.code, supplier_id=body.supplier_id,
                                    validity_until=body.validity_until, currency=body.currency, terms=body.terms,
                                    actor=str(actor.id))
    db.commit()
    db.refresh(quote)
    return {"id": quote.id, "code": quote.code, "status": quote.status}


@router.post("/quotes/{quote_id}/lines", dependencies=[Depends(require_write_allowed)])
def add_quote_line(quote_id: str, body: QuoteLineCreate, db: Session = Depends(get_db),
                   actor: User = Depends(require_permission("compras", "create"))):
    line = ap_service.add_quote_line(db, quote_id=quote_id, product_id=body.product_id, quantity=body.quantity,
                                     unit_price=body.unit_price, discount=body.discount,
                                     delivery_days=body.delivery_days, tax_ref=body.tax_ref)
    db.commit()
    db.refresh(line)
    return {"id": line.id, "product_id": line.product_id, "unit_price": line.unit_price}


# --------------------------------------------------------------------------- #
# Órdenes de compra
# --------------------------------------------------------------------------- #
@router.get("/orders")
def list_orders(status: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = select(PurchaseOrder).where(PurchaseOrder.company_id == user.tenant_id)
    if status:
        query = query.where(PurchaseOrder.status == status)
    total = db.execute(select(func.count()).select_from(query.subquery())).scalar() or 0
    items = db.execute(query.order_by(PurchaseOrder.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return {"items": [ap_service.order_dict(db, o) for o in items], "total": total, "page": page, "page_size": page_size}


@router.post("/orders", dependencies=[Depends(require_write_allowed)])
def create_order(body: OrderCreate, db: Session = Depends(get_db),
                 actor: User = Depends(require_permission("compras", "create"))):
    order = ap_service.create_order(db, company_id=actor.tenant_id, code=body.code, supplier_id=body.supplier_id,
                                    terms=body.terms, expected_date=body.expected_date, currency=body.currency,
                                    actor=str(actor.id))
    db.commit()
    db.refresh(order)
    return ap_service.order_dict(db, order)


@router.get("/orders/{order_id}")
def get_order(order_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    order = _owned(db, PurchaseOrder, order_id, user.tenant_id, "ORDER_NOT_FOUND", "Orden no encontrada")
    return ap_service.order_dict(db, order)


@router.post("/orders/{order_id}/lines", dependencies=[Depends(require_write_allowed)])
def add_order_line(order_id: str, body: OrderLineCreate, db: Session = Depends(get_db),
                   actor: User = Depends(require_permission("compras", "create"))):
    order = _owned(db, PurchaseOrder, order_id, actor.tenant_id, "ORDER_NOT_FOUND", "Orden no encontrada")
    line = ap_service.add_order_line(db, order_id=str(order.id), product_id=body.product_id,
                                     quantity_ordered=body.quantity_ordered, unit_price=body.unit_price,
                                     discount=body.discount, tax_ref=body.tax_ref, needs_inventory=body.needs_inventory,
                                     snapshot=body.snapshot)
    db.commit()
    db.refresh(line)
    return {"id": line.id, "product_id": line.product_id, "quantity_ordered": line.quantity_ordered}


@router.post("/orders/{order_id}/transition", dependencies=[Depends(require_write_allowed)])
def transition_order(order_id: str, body: TransitionBody, db: Session = Depends(get_db),
                     actor: User = Depends(require_permission("compras", "approve"))):
    order = _owned(db, PurchaseOrder, order_id, actor.tenant_id, "ORDER_NOT_FOUND", "Orden no encontrada")
    ap_service.transition_order(db, order=order, target=body.target, actor=str(actor.id), approval_ref=body.approval_ref)
    db.commit()
    db.refresh(order)
    return ap_service.order_dict(db, order)


# --------------------------------------------------------------------------- #
# Recepciones
# --------------------------------------------------------------------------- #
@router.get("/receipts")
def list_receipts(status: str | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = select(GoodsReceipt).where(GoodsReceipt.company_id == user.tenant_id)
    if status:
        query = query.where(GoodsReceipt.status == status)
    items = db.execute(query.order_by(GoodsReceipt.created_at.desc())).scalars().all()
    return {"items": [{"id": r.id, "code": r.code, "order_id": r.order_id, "warehouse_id": r.warehouse_id,
                       "status": r.status, "quality_status": r.quality_status} for r in items],
            "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/receipts", dependencies=[Depends(require_write_allowed)])
def create_receipt(body: ReceiptCreate, db: Session = Depends(get_db),
                   actor: User = Depends(require_permission("compras", "create"))):
    receipt = ap_service.create_receipt(db, company_id=actor.tenant_id, code=body.code, order_id=body.order_id,
                                        warehouse_id=body.warehouse_id, actor=str(actor.id))
    db.commit()
    db.refresh(receipt)
    return {"id": receipt.id, "code": receipt.code, "status": receipt.status}


@router.post("/receipts/{receipt_id}/lines", dependencies=[Depends(require_write_allowed)])
def add_receipt_line(receipt_id: str, body: ReceiptLineCreate, db: Session = Depends(get_db),
                     actor: User = Depends(require_permission("compras", "create"))):
    line = ap_service.add_receipt_line(db, receipt_id=receipt_id, order_line_id=body.order_line_id,
                                       product_id=body.product_id, quantity_received=body.quantity_received,
                                       quantity_accepted=body.quantity_accepted, quantity_rejected=body.quantity_rejected,
                                       lot_number=body.lot_number, expiry_date=body.expiry_date, serials=body.serials)
    db.commit()
    db.refresh(line)
    return {"id": line.id, "product_id": line.product_id, "quantity_accepted": line.quantity_accepted}


@router.post("/receipts/{receipt_id}/confirm", dependencies=[Depends(require_write_allowed)])
def confirm_receipt(receipt_id: str, db: Session = Depends(get_db),
                    actor: User = Depends(require_permission("compras", "create"))):
    receipt = _owned(db, GoodsReceipt, receipt_id, actor.tenant_id, "RECEIPT_NOT_FOUND", "Recepción no encontrada")
    ap_service.confirm_receipt(db, receipt=receipt, actor=str(actor.id))
    db.commit()
    db.refresh(receipt)
    return {"id": receipt.id, "status": receipt.status}


@router.post("/receipts/{receipt_id}/quality", dependencies=[Depends(require_write_allowed)])
def set_receipt_quality(receipt_id: str, body: QualityBody, db: Session = Depends(get_db),
                        actor: User = Depends(require_permission("compras", "quality"))):
    receipt = _owned(db, GoodsReceipt, receipt_id, actor.tenant_id, "RECEIPT_NOT_FOUND", "Recepción no encontrada")
    if body.quality_status == "REJECTED":
        ap_service.reject_receipt(db, receipt=receipt, actor=str(actor.id))
    else:
        receipt.quality_status = "APPROVED"
        db.flush()
    db.commit()
    db.refresh(receipt)
    return {"id": receipt.id, "status": receipt.status, "quality_status": receipt.quality_status}


@router.post("/receipts/{receipt_id}/accept", dependencies=[Depends(require_write_allowed)])
def accept_receipt(receipt_id: str, db: Session = Depends(get_db),
                   actor: User = Depends(require_permission("compras", "quality"))):
    receipt = _owned(db, GoodsReceipt, receipt_id, actor.tenant_id, "RECEIPT_NOT_FOUND", "Recepción no encontrada")
    ap_service.accept_receipt(db, receipt=receipt, actor=str(actor.id))
    db.commit()
    db.refresh(receipt)
    return {"id": receipt.id, "status": receipt.status}


# --------------------------------------------------------------------------- #
# Facturas del proveedor y conciliación triple
# --------------------------------------------------------------------------- #
@router.get("/supplier-invoices")
def list_invoices(status: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                  db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = select(SupplierInvoice).where(SupplierInvoice.company_id == user.tenant_id)
    if status:
        query = query.where(SupplierInvoice.status == status)
    total = db.execute(select(func.count()).select_from(query.subquery())).scalar() or 0
    items = db.execute(query.order_by(SupplierInvoice.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return {"items": [ap_service.invoice_dict(i) for i in items], "total": total, "page": page, "page_size": page_size}


@router.post("/supplier-invoices", dependencies=[Depends(require_write_allowed)])
def create_invoice(body: InvoiceCreate, db: Session = Depends(get_db),
                   actor: User = Depends(require_permission("compras", "create"))):
    invoice = ap_service.create_invoice(db, company_id=actor.tenant_id, supplier_id=body.supplier_id,
                                        invoice_number=body.invoice_number, control_number=body.control_number,
                                        issue_date=body.issue_date, currency=body.currency, actor=str(actor.id),
                                        idempotency_key=body.idempotency_key)
    db.commit()
    db.refresh(invoice)
    return ap_service.invoice_dict(invoice)


@router.get("/supplier-invoices/{invoice_id}")
def get_invoice(invoice_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    invoice = _owned(db, SupplierInvoice, invoice_id, user.tenant_id, "INVOICE_NOT_FOUND", "Factura no encontrada")
    return ap_service.invoice_dict(invoice)


@router.post("/supplier-invoices/{invoice_id}/lines", dependencies=[Depends(require_write_allowed)])
def add_invoice_line(invoice_id: str, body: InvoiceLineCreate, db: Session = Depends(get_db),
                     actor: User = Depends(require_permission("compras", "create"))):
    line = ap_service.add_invoice_line(db, invoice_id=invoice_id, product_id=body.product_id, quantity=body.quantity,
                                       unit_price=body.unit_price, tax_amount=body.tax_amount,
                                       order_line_id=body.order_line_id, receipt_line_id=body.receipt_line_id,
                                       snapshot=body.snapshot)
    invoice = _owned(db, SupplierInvoice, invoice_id, actor.tenant_id, "INVOICE_NOT_FOUND", "Factura no encontrada")
    ap_service.recompute_invoice_total(db, invoice=invoice)
    db.commit()
    db.refresh(line)
    return {"id": line.id, "product_id": line.product_id, "total": line.total}


@router.post("/supplier-invoices/{invoice_id}/transition", dependencies=[Depends(require_write_allowed)])
def transition_invoice(invoice_id: str, body: TransitionBody, db: Session = Depends(get_db),
                       actor: User = Depends(require_permission("compras", "approve"))):
    invoice = _owned(db, SupplierInvoice, invoice_id, actor.tenant_id, "INVOICE_NOT_FOUND", "Factura no encontrada")
    if body.target == "MATCHED":
        ap_service.match_invoice(db, invoice=invoice, actor=str(actor.id))
    elif body.target == "POSTED":
        ap_service.post_invoice(db, invoice=invoice, actor=str(actor.id))
    elif body.target == "REVERSED":
        ap_service.reverse_invoice(db, invoice=invoice, actor=str(actor.id))
    else:
        ap_service.transition_invoice(db, invoice=invoice, target=body.target, actor=str(actor.id))
    db.commit()
    db.refresh(invoice)
    return ap_service.invoice_dict(invoice)


@router.get("/triple-match")
def list_triple_match(invoice_id: str | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = select(TripleMatch).where(TripleMatch.company_id == user.tenant_id)
    if invoice_id:
        query = query.where(TripleMatch.invoice_id == invoice_id)
    items = db.execute(query.order_by(TripleMatch.created_at)).scalars().all()
    return {"items": [{"id": t.id, "invoice_id": t.invoice_id, "order_line_id": t.order_line_id,
                       "receipt_line_id": t.receipt_line_id, "variance_qty": t.variance_qty,
                       "variance_price": t.variance_price, "variance_tax": t.variance_tax,
                       "resolution": t.resolution} for t in items],
            "total": len(items), "page": 1, "page_size": len(items) or 1}


# --------------------------------------------------------------------------- #
# Devoluciones y notas de crédito
# --------------------------------------------------------------------------- #
@router.get("/returns")
def list_returns(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    items = db.execute(select(PurchaseReturn).where(PurchaseReturn.company_id == user.tenant_id)
                       .order_by(PurchaseReturn.created_at.desc())).scalars().all()
    return {"items": [{"id": r.id, "code": r.code, "source_document": r.source_document,
                        "reason": r.reason, "condition": r.condition,
                        "inventory_destination": r.inventory_destination, "status": r.status} for r in items],
            "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/returns", dependencies=[Depends(require_write_allowed)])
def create_return(body: ReturnCreate, db: Session = Depends(get_db),
                  actor: User = Depends(require_permission("compras", "create"))):
    ret = ap_service.create_return(db, company_id=actor.tenant_id, code=body.code, source_document=body.source_document,
                                   reason=body.reason, condition=body.condition,
                                   inventory_destination=body.inventory_destination, actor=str(actor.id))
    db.commit()
    db.refresh(ret)
    return {"id": ret.id, "code": ret.code, "status": ret.status}


@router.post("/returns/{return_id}/lines", dependencies=[Depends(require_write_allowed)])
def add_return_line(return_id: str, body: ReturnLineCreate, db: Session = Depends(get_db),
                    actor: User = Depends(require_permission("compras", "create"))):
    line = ap_service.add_return_line(db, return_id=return_id, product_id=body.product_id,
                                      quantity=body.quantity, condition=body.condition)
    db.commit()
    db.refresh(line)
    return {"id": line.id, "product_id": line.product_id, "quantity": line.quantity}


@router.get("/credit-notes")
def list_credit_notes(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    items = db.execute(select(SupplierCreditNote).where(SupplierCreditNote.company_id == user.tenant_id)
                       .order_by(SupplierCreditNote.created_at.desc())).scalars().all()
    return {"items": [{"id": n.id, "number": n.number, "party_id": n.supplier_id,
                        "invoice_ref": n.invoice_ref, "amount": float(n.amount), "applied": float(n.applied),
                        "currency": n.currency, "status": n.status} for n in items],
            "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/credit-notes", dependencies=[Depends(require_write_allowed)])
def create_credit_note(body: CreditNoteCreate, db: Session = Depends(get_db),
                       actor: User = Depends(require_permission("compras", "create"))):
    note = ap_service.create_credit_note(db, company_id=actor.tenant_id, supplier_id=body.supplier_id,
                                         number=body.number, amount=body.amount, invoice_ref=body.invoice_ref,
                                         currency=body.currency, actor=str(actor.id))
    db.commit()
    db.refresh(note)
    return {"id": note.id, "number": note.number, "amount": note.amount, "status": note.status}


@router.post("/credit-notes/{note_id}/post", dependencies=[Depends(require_write_allowed)])
def post_credit_note(note_id: str, db: Session = Depends(get_db),
                     actor: User = Depends(require_permission("compras", "approve"))):
    note = _owned(db, SupplierCreditNote, note_id, actor.tenant_id, "CREDIT_NOTE_NOT_FOUND", "Nota de crédito no encontrada")
    ap_service.post_credit_note(db, note=note)
    db.commit()
    db.refresh(note)
    return {"id": note.id, "status": note.status}


# --------------------------------------------------------------------------- #
# CxP — open items, pagos, aplicaciones, anticipos, retenciones, aging
# --------------------------------------------------------------------------- #
@router.get("/open-items")
def list_open_items(party_id: str | None = None, status: str | None = None,
                    db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = select(OpenItem).where(OpenItem.company_id == user.tenant_id)
    if party_id:
        query = query.where(OpenItem.party_id == party_id)
    if status:
        query = query.where(OpenItem.status == status)
    items = db.execute(query.order_by(OpenItem.due_date.asc().nulls_last())).scalars().all()
    return {"items": [ap_service.open_item_dict(i) for i in items], "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.get("/payments")
def list_payments(status: str | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = select(Payment).where(Payment.company_id == user.tenant_id)
    if status:
        query = query.where(Payment.status == status)
    items = db.execute(query.order_by(Payment.created_at.desc())).scalars().all()
    return {"items": [ap_service.payment_dict(p) for p in items], "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/payments", dependencies=[Depends(require_write_allowed)])
def create_payment(body: PaymentCreate, db: Session = Depends(get_db),
                   actor: User = Depends(require_permission("compras", "create"))):
    payment = ap_service.register_payment(db, company_id=actor.tenant_id, party_id=body.party_id, amount=body.amount,
                                          currency=body.currency, instruments=body.instruments, actor=str(actor.id),
                                          idempotency_key=body.idempotency_key)
    db.commit()
    db.refresh(payment)
    return ap_service.payment_dict(payment)


@router.post("/payments/{payment_id}/transition", dependencies=[Depends(require_write_allowed)])
def transition_payment(payment_id: str, body: TransitionBody, db: Session = Depends(get_db),
                       actor: User = Depends(require_permission("compras", "approve"))):
    payment = _owned(db, Payment, payment_id, actor.tenant_id, "PAYMENT_NOT_FOUND", "Pago no encontrado")
    ap_service.transition_payment(db, payment=payment, target=body.target, actor=str(actor.id))
    db.commit()
    db.refresh(payment)
    return ap_service.payment_dict(payment)


@router.post("/applications", dependencies=[Depends(require_write_allowed)])
def create_application(body: ApplicationCreate, db: Session = Depends(get_db),
                       actor: User = Depends(require_permission("compras", "apply"))):
    app = ap_service.apply_source(db, company_id=actor.tenant_id, source_type=body.source_type, source_id=body.source_id,
                                  target_open_item_id=body.target_open_item_id, amount=body.amount,
                                  currency=body.currency, rate=body.rate, actor=str(actor.id))
    db.commit()
    db.refresh(app)
    return {"id": app.id, "source_type": app.source_type, "source_id": app.source_id,
            "target_open_item_id": app.target_open_item_id, "amount": app.amount, "status": app.status}


@router.post("/advances", dependencies=[Depends(require_write_allowed)])
def create_advance(body: AdvanceCreate, db: Session = Depends(get_db),
                   actor: User = Depends(require_permission("compras", "create"))):
    adv = ap_service.register_advance(db, company_id=actor.tenant_id, party_id=body.party_id, amount=body.amount,
                                      currency=body.currency, actor=str(actor.id))
    db.commit()
    db.refresh(adv)
    return {"id": adv.id, "party_id": adv.party_id, "amount": adv.amount, "available": adv.available, "status": adv.status}


@router.post("/withholdings", dependencies=[Depends(require_write_allowed)])
def create_withholding(body: WithholdingCreate, db: Session = Depends(get_db),
                       actor: User = Depends(require_permission("compras", "create"))):
    w = ap_service.create_withholding(db, company_id=actor.tenant_id, party_id=body.party_id, tax_type=body.tax_type,
                                      rule_ref=body.rule_ref, base=body.base, rate_ref=body.rate_ref,
                                      amount=body.amount, period=body.period, source_event=body.source_event,
                                      actor=str(actor.id))
    db.commit()
    db.refresh(w)
    return {"id": w.id, "party_id": w.party_id, "tax_type": w.tax_type, "amount": w.amount, "status": w.status}


@router.post("/withholdings/{withholding_id}/transition", dependencies=[Depends(require_write_allowed)])
def transition_withholding(withholding_id: str, body: TransitionBody, db: Session = Depends(get_db),
                           actor: User = Depends(require_permission("compras", "approve"))):
    w = _owned(db, Withholding, withholding_id, actor.tenant_id, "WITHHOLDING_NOT_FOUND", "Retención no encontrada")
    ap_service.transition_withholding(db, withholding=w, target=body.target)
    db.commit()
    db.refresh(w)
    return {"id": w.id, "status": w.status}


@router.get("/aging")
def get_aging(party_id: str | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return ap_service.aging(db, company_id=user.tenant_id, party_id=party_id)


@router.post("/payment-schedules", dependencies=[Depends(require_write_allowed)])
def create_schedule(body: ScheduleCreate, db: Session = Depends(get_db),
                    actor: User = Depends(require_permission("compras", "create"))):
    schedule = ap_service.create_schedule(db, company_id=actor.tenant_id, party_id=body.party_id,
                                          due_date=body.due_date, amount=body.amount, actor=str(actor.id))
    db.commit()
    db.refresh(schedule)
    return {"id": schedule.id, "party_id": schedule.party_id, "due_date": schedule.due_date.isoformat() if schedule.due_date else None,
            "amount": schedule.amount, "status": schedule.status}


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _owned(db: Session, model, obj_id: str, tenant: str, code: str, message: str):
    obj = db.get(model, obj_id)
    if not obj or getattr(obj, "company_id", tenant) != tenant:
        raise NotFoundError(code=code, message=message)
    return obj
