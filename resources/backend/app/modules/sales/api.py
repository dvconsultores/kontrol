"""API de ventas y cuentas por cobrar (005).

Endpoints REST `/sales/*` con convenciones heredadas de 001 (DOC-03 §14):
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
from app.modules.purchasing.models import OpenItem, Payment, Withholding
from app.modules.sales import service as sales_service
from app.modules.sales.models import (
    SalesCreditNote,
    SalesInvoice,
    SalesOrder,
    SalesQuote,
    Shipment,
)

router = APIRouter(prefix="/sales", tags=["ventas"])


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #
class QuoteCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    customer_id: str
    price_list: str | None = None
    validity_until: date | None = None
    currency: str = "VED"


class QuoteLineCreate(BaseModel):
    product_id: str
    quantity: float = Field(gt=0)
    unit_price: float = Field(ge=0)
    discount: float = 0.0
    tax_ref: str | None = None


class OrderCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    customer_id: str
    warehouse_id: str | None = None
    margin: float | None = None
    currency: str = "VED"


class OrderLineCreate(BaseModel):
    product_id: str
    quantity: float = Field(gt=0)
    unit_price: float = Field(ge=0)
    discount: float = 0.0
    tax_ref: str | None = None
    needs_inventory: bool = True
    snapshot: str | None = None


class TransitionBody(BaseModel):
    target: str
    credit_decision: str | None = None
    approval_ref: str | None = None


class PickListCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    order_id: str
    warehouse_id: str
    lines: list[dict] | None = None


class ShipmentCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    order_id: str
    origin_warehouse_id: str
    destination: str | None = None
    transport: str | None = None
    lines: list[dict] | None = None


class InvoiceCreate(BaseModel):
    customer_id: str
    base_fiscal_currency: str = "VED"
    idempotency_key: str | None = None


class InvoiceLineCreate(BaseModel):
    product_id: str
    quantity: float = Field(gt=0)
    unit_price: float = Field(ge=0)
    tax_amount: float = 0.0
    snapshot: str | None = None


class CreditNoteCreate(BaseModel):
    customer_id: str
    number: str = Field(min_length=1, max_length=120)
    amount: float = Field(gt=0)
    invoice_ref: str | None = None
    currency: str = "VED"


class DebitNoteCreate(BaseModel):
    customer_id: str
    number: str = Field(min_length=1, max_length=120)
    amount: float = Field(gt=0)
    invoice_ref: str | None = None
    currency: str = "VED"


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


class CollectionCreate(BaseModel):
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


# --------------------------------------------------------------------------- #
# Cotizaciones y pedidos
# --------------------------------------------------------------------------- #
@router.get("/quotes")
def list_quotes(customer_id: str | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = select(SalesQuote).where(SalesQuote.company_id == user.tenant_id)
    if customer_id:
        query = query.where(SalesQuote.customer_id == customer_id)
    items = db.execute(query.order_by(SalesQuote.created_at.desc())).scalars().all()
    return {"items": [{"id": q.id, "code": q.code, "customer_id": q.customer_id, "currency": q.currency, "status": q.status} for q in items],
            "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/quotes", dependencies=[Depends(require_write_allowed)])
def create_quote(body: QuoteCreate, db: Session = Depends(get_db),
                 actor: User = Depends(require_permission("ventas", "create"))):
    quote = sales_service.create_quote(db, company_id=actor.tenant_id, code=body.code, customer_id=body.customer_id,
                                       price_list=body.price_list, validity_until=body.validity_until,
                                       currency=body.currency, actor=str(actor.id))
    db.commit()
    db.refresh(quote)
    return {"id": quote.id, "code": quote.code, "status": quote.status}


@router.post("/quotes/{quote_id}/lines", dependencies=[Depends(require_write_allowed)])
def add_quote_line(quote_id: str, body: QuoteLineCreate, db: Session = Depends(get_db),
                   actor: User = Depends(require_permission("ventas", "create"))):
    line = sales_service.add_quote_line(db, quote_id=quote_id, product_id=body.product_id, quantity=body.quantity,
                                        unit_price=body.unit_price, discount=body.discount, tax_ref=body.tax_ref)
    db.commit()
    db.refresh(line)
    return {"id": line.id, "product_id": line.product_id, "unit_price": line.unit_price}


@router.get("/orders")
def list_orders(status: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = select(SalesOrder).where(SalesOrder.company_id == user.tenant_id)
    if status:
        query = query.where(SalesOrder.status == status)
    total = db.execute(select(func.count()).select_from(query.subquery())).scalar() or 0
    items = db.execute(query.order_by(SalesOrder.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return {"items": [sales_service.order_dict(db, o) for o in items], "total": total, "page": page, "page_size": page_size}


@router.post("/orders", dependencies=[Depends(require_write_allowed)])
def create_order(body: OrderCreate, db: Session = Depends(get_db),
                 actor: User = Depends(require_permission("ventas", "create"))):
    order = sales_service.create_order(db, company_id=actor.tenant_id, code=body.code, customer_id=body.customer_id,
                                       warehouse_id=body.warehouse_id, margin=body.margin, currency=body.currency,
                                       actor=str(actor.id))
    db.commit()
    db.refresh(order)
    return sales_service.order_dict(db, order)


@router.get("/orders/{order_id}")
def get_order(order_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    order = _owned(db, SalesOrder, order_id, user.tenant_id, "SALES_ORDER_NOT_FOUND", "Orden no encontrada")
    return sales_service.order_dict(db, order)


@router.post("/orders/{order_id}/lines", dependencies=[Depends(require_write_allowed)])
def add_order_line(order_id: str, body: OrderLineCreate, db: Session = Depends(get_db),
                   actor: User = Depends(require_permission("ventas", "create"))):
    order = _owned(db, SalesOrder, order_id, actor.tenant_id, "SALES_ORDER_NOT_FOUND", "Orden no encontrada")
    line = sales_service.add_order_line(db, order_id=str(order.id), product_id=body.product_id, quantity=body.quantity,
                                        unit_price=body.unit_price, discount=body.discount, tax_ref=body.tax_ref,
                                        needs_inventory=body.needs_inventory, snapshot=body.snapshot)
    db.commit()
    db.refresh(line)
    return {"id": line.id, "product_id": line.product_id, "quantity": line.quantity}


@router.post("/orders/{order_id}/transition", dependencies=[Depends(require_write_allowed)])
def transition_order(order_id: str, body: TransitionBody, db: Session = Depends(get_db),
                     actor: User = Depends(require_permission("ventas", "approve"))):
    order = _owned(db, SalesOrder, order_id, actor.tenant_id, "SALES_ORDER_NOT_FOUND", "Orden no encontrada")
    sales_service.transition_order(db, order=order, target=body.target, actor=str(actor.id),
                                   credit_decision=body.credit_decision, approval_ref=body.approval_ref)
    db.commit()
    db.refresh(order)
    return sales_service.order_dict(db, order)


# --------------------------------------------------------------------------- #
# Picking y despacho
# --------------------------------------------------------------------------- #
@router.post("/pick-lists", dependencies=[Depends(require_write_allowed)])
def create_picklist(body: PickListCreate, db: Session = Depends(get_db),
                    actor: User = Depends(require_permission("ventas", "create"))):
    pl = sales_service.create_picklist(db, company_id=actor.tenant_id, code=body.code, order_id=body.order_id,
                                       warehouse_id=body.warehouse_id, lines=body.lines, actor=str(actor.id))
    db.commit()
    db.refresh(pl)
    return {"id": pl.id, "code": pl.code, "status": pl.status}


@router.post("/shipments", dependencies=[Depends(require_write_allowed)])
def create_shipment(body: ShipmentCreate, db: Session = Depends(get_db),
                    actor: User = Depends(require_permission("ventas", "create"))):
    shipment = sales_service.create_shipment(db, company_id=actor.tenant_id, code=body.code, order_id=body.order_id,
                                             origin_warehouse_id=body.origin_warehouse_id, destination=body.destination,
                                             transport=body.transport, lines=body.lines, actor=str(actor.id))
    db.commit()
    db.refresh(shipment)
    return {"id": shipment.id, "code": shipment.code, "status": shipment.status, "validation_status": shipment.validation_status}


@router.post("/shipments/{shipment_id}/validate", dependencies=[Depends(require_write_allowed)])
def validate_shipment(shipment_id: str, db: Session = Depends(get_db),
                      actor: User = Depends(require_permission("ventas", "quality"))):
    shipment = _owned(db, Shipment, shipment_id, actor.tenant_id, "SHIPMENT_NOT_FOUND", "Despacho no encontrado")
    sales_service.validate_shipment(db, shipment=shipment, actor=str(actor.id))
    db.commit()
    db.refresh(shipment)
    return {"id": shipment.id, "status": shipment.status, "validation_status": shipment.validation_status}


@router.post("/shipments/{shipment_id}/confirm", dependencies=[Depends(require_write_allowed)])
def confirm_shipment(shipment_id: str, db: Session = Depends(get_db),
                     actor: User = Depends(require_permission("ventas", "quality"))):
    shipment = _owned(db, Shipment, shipment_id, actor.tenant_id, "SHIPMENT_NOT_FOUND", "Despacho no encontrado")
    sales_service.confirm_shipment(db, shipment=shipment, actor=str(actor.id))
    db.commit()
    db.refresh(shipment)
    return {"id": shipment.id, "status": shipment.status}


# --------------------------------------------------------------------------- #
# Factura de venta y notas
# --------------------------------------------------------------------------- #
@router.get("/invoices")
def list_invoices(status: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                  db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = select(SalesInvoice).where(SalesInvoice.company_id == user.tenant_id)
    if status:
        query = query.where(SalesInvoice.status == status)
    total = db.execute(select(func.count()).select_from(query.subquery())).scalar() or 0
    items = db.execute(query.order_by(SalesInvoice.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return {"items": [sales_service.invoice_dict(i) for i in items], "total": total, "page": page, "page_size": page_size}


@router.post("/invoices", dependencies=[Depends(require_write_allowed)])
def create_invoice(body: InvoiceCreate, db: Session = Depends(get_db),
                   actor: User = Depends(require_permission("ventas", "create"))):
    invoice = sales_service.create_invoice(db, company_id=actor.tenant_id, customer_id=body.customer_id,
                                           base_fiscal_currency=body.base_fiscal_currency, actor=str(actor.id),
                                           idempotency_key=body.idempotency_key)
    db.commit()
    db.refresh(invoice)
    return sales_service.invoice_dict(invoice)


@router.post("/invoices/{invoice_id}/lines", dependencies=[Depends(require_write_allowed)])
def add_invoice_line(invoice_id: str, body: InvoiceLineCreate, db: Session = Depends(get_db),
                     actor: User = Depends(require_permission("ventas", "create"))):
    invoice = _owned(db, SalesInvoice, invoice_id, actor.tenant_id, "INVOICE_NOT_FOUND", "Factura no encontrada")
    line = sales_service.add_invoice_line(db, invoice_id=str(invoice.id), product_id=body.product_id,
                                          quantity=body.quantity, unit_price=body.unit_price,
                                          tax_amount=body.tax_amount, snapshot=body.snapshot)
    sales_service.recompute_invoice_total(db, invoice=invoice)
    db.commit()
    db.refresh(line)
    return {"id": line.id, "product_id": line.product_id, "total": line.total}


@router.post("/invoices/{invoice_id}/transition", dependencies=[Depends(require_write_allowed)])
def transition_invoice(invoice_id: str, body: TransitionBody, db: Session = Depends(get_db),
                       actor: User = Depends(require_permission("ventas", "approve"))):
    invoice = _owned(db, SalesInvoice, invoice_id, actor.tenant_id, "INVOICE_NOT_FOUND", "Factura no encontrada")
    if body.target == "VOIDED":
        sales_service.void_invoice(db, invoice=invoice, actor=str(actor.id))
    else:
        sales_service.transition_invoice(db, invoice=invoice, target=body.target, actor=str(actor.id))
    db.commit()
    db.refresh(invoice)
    return sales_service.invoice_dict(invoice)


@router.post("/credit-notes", dependencies=[Depends(require_write_allowed)])
def create_credit_note(body: CreditNoteCreate, db: Session = Depends(get_db),
                       actor: User = Depends(require_permission("ventas", "create"))):
    note = sales_service.create_credit_note(db, company_id=actor.tenant_id, customer_id=body.customer_id,
                                            number=body.number, amount=body.amount, invoice_ref=body.invoice_ref,
                                            currency=body.currency, actor=str(actor.id))
    db.commit()
    db.refresh(note)
    return {"id": note.id, "number": note.number, "amount": note.amount, "status": note.status}


@router.post("/credit-notes/{note_id}/post", dependencies=[Depends(require_write_allowed)])
def post_credit_note(note_id: str, db: Session = Depends(get_db),
                     actor: User = Depends(require_permission("ventas", "approve"))):
    note = _owned(db, SalesCreditNote, note_id, actor.tenant_id, "CREDIT_NOTE_NOT_FOUND", "Nota no encontrada")
    sales_service.post_credit_note(db, note=note)
    db.commit()
    db.refresh(note)
    return {"id": note.id, "status": note.status}


@router.post("/credit-notes/{note_id}/apply", dependencies=[Depends(require_write_allowed)])
def apply_credit_note(note_id: str, body: ApplicationCreate, db: Session = Depends(get_db),
                      actor: User = Depends(require_permission("ventas", "apply"))):
    note = _owned(db, SalesCreditNote, note_id, actor.tenant_id, "CREDIT_NOTE_NOT_FOUND", "Nota no encontrada")
    target = sales_service.apply_credit_note(db, note=note, target_open_item_id=body.target_open_item_id,
                                             amount=body.amount, actor=str(actor.id))
    db.commit()
    db.refresh(target)
    return {"target_open_item_id": str(target.id), "balance": ap_service.open_item_balance(target)}


@router.post("/debit-notes", dependencies=[Depends(require_write_allowed)])
def create_debit_note(body: DebitNoteCreate, db: Session = Depends(get_db),
                      actor: User = Depends(require_permission("ventas", "create"))):
    note = sales_service.create_debit_note(db, company_id=actor.tenant_id, customer_id=body.customer_id,
                                           number=body.number, amount=body.amount, invoice_ref=body.invoice_ref,
                                           currency=body.currency, actor=str(actor.id))
    db.commit()
    db.refresh(note)
    return {"id": note.id, "number": note.number, "amount": note.amount, "status": note.status}


@router.post("/returns", dependencies=[Depends(require_write_allowed)])
def create_return(body: ReturnCreate, db: Session = Depends(get_db),
                  actor: User = Depends(require_permission("ventas", "create"))):
    ret = sales_service.create_return(db, company_id=actor.tenant_id, code=body.code, source_document=body.source_document,
                                      reason=body.reason, condition=body.condition,
                                      inventory_destination=body.inventory_destination, actor=str(actor.id))
    db.commit()
    db.refresh(ret)
    return {"id": ret.id, "code": ret.code, "status": ret.status}


@router.post("/returns/{return_id}/lines", dependencies=[Depends(require_write_allowed)])
def add_return_line(return_id: str, body: ReturnLineCreate, db: Session = Depends(get_db),
                    actor: User = Depends(require_permission("ventas", "create"))):
    line = sales_service.add_return_line(db, return_id=return_id, product_id=body.product_id,
                                         quantity=body.quantity, condition=body.condition)
    db.commit()
    db.refresh(line)
    return {"id": line.id, "product_id": line.product_id, "quantity": line.quantity}


# --------------------------------------------------------------------------- #
# CxC (reutiliza el motor de 004)
# --------------------------------------------------------------------------- #
@router.get("/open-items")
def list_open_items(party_id: str | None = None, status: str | None = None,
                    db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = select(OpenItem).where(OpenItem.company_id == user.tenant_id, OpenItem.item_type == "RECEIVABLE")
    if party_id:
        query = query.where(OpenItem.party_id == party_id)
    if status:
        query = query.where(OpenItem.status == status)
    items = db.execute(query.order_by(OpenItem.due_date.asc().nulls_last())).scalars().all()
    return {"items": [sales_service.open_item_dict(i) for i in items], "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.get("/collections")
def list_collections(status: str | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = select(Payment).where(Payment.company_id == user.tenant_id, Payment.direction == "IN")
    if status:
        query = query.where(Payment.status == status)
    items = db.execute(query.order_by(Payment.created_at.desc())).scalars().all()
    return {"items": [sales_service.collection_dict(p) for p in items], "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/collections", dependencies=[Depends(require_write_allowed)])
def create_collection(body: CollectionCreate, db: Session = Depends(get_db),
                      actor: User = Depends(require_permission("ventas", "create"))):
    payment = ap_service.register_payment(db, company_id=actor.tenant_id, party_id=body.party_id, amount=body.amount,
                                          currency=body.currency, instruments=body.instruments, actor=str(actor.id),
                                          idempotency_key=body.idempotency_key, direction="IN")
    db.commit()
    db.refresh(payment)
    return sales_service.collection_dict(payment)


@router.post("/collections/{collection_id}/transition", dependencies=[Depends(require_write_allowed)])
def transition_collection(collection_id: str, body: TransitionBody, db: Session = Depends(get_db),
                          actor: User = Depends(require_permission("ventas", "approve"))):
    payment = _owned(db, Payment, collection_id, actor.tenant_id, "COLLECTION_NOT_FOUND", "Cobro no encontrado")
    ap_service.transition_payment(db, payment=payment, target=body.target, actor=str(actor.id))
    db.commit()
    db.refresh(payment)
    return sales_service.collection_dict(payment)


@router.post("/applications", dependencies=[Depends(require_write_allowed)])
def create_application(body: ApplicationCreate, db: Session = Depends(get_db),
                       actor: User = Depends(require_permission("ventas", "apply"))):
    app = sales_service.apply_to_cxc(db, company_id=actor.tenant_id, source_type=body.source_type, source_id=body.source_id,
                                     target_open_item_id=body.target_open_item_id, amount=body.amount,
                                     currency=body.currency, rate=body.rate, actor=str(actor.id))
    db.commit()
    db.refresh(app)
    return {"id": app.id, "source_type": app.source_type, "source_id": app.source_id,
            "target_open_item_id": app.target_open_item_id, "amount": app.amount, "status": app.status}


@router.post("/customer-advances", dependencies=[Depends(require_write_allowed)])
def create_customer_advance(body: AdvanceCreate, db: Session = Depends(get_db),
                            actor: User = Depends(require_permission("ventas", "create"))):
    adv = ap_service.register_advance(db, company_id=actor.tenant_id, party_id=body.party_id, amount=body.amount,
                                      currency=body.currency, actor=str(actor.id), direction="IN")
    db.commit()
    db.refresh(adv)
    return {"id": adv.id, "party_id": adv.party_id, "amount": adv.amount, "available": adv.available, "status": adv.status}


@router.post("/withholdings-suffered", dependencies=[Depends(require_write_allowed)])
def create_withholding_suffered(body: WithholdingCreate, db: Session = Depends(get_db),
                                actor: User = Depends(require_permission("ventas", "create"))):
    w = ap_service.create_withholding(db, company_id=actor.tenant_id, party_id=body.party_id, tax_type=body.tax_type,
                                      rule_ref=body.rule_ref, base=body.base, rate_ref=body.rate_ref,
                                      amount=body.amount, period=body.period, source_event=body.source_event,
                                      actor=str(actor.id))
    db.commit()
    db.refresh(w)
    return {"id": w.id, "party_id": w.party_id, "tax_type": w.tax_type, "amount": w.amount, "status": w.status}


@router.post("/withholdings-suffered/{withholding_id}/transition", dependencies=[Depends(require_write_allowed)])
def transition_withholding(withholding_id: str, body: TransitionBody, db: Session = Depends(get_db),
                           actor: User = Depends(require_permission("ventas", "approve"))):
    w = _owned(db, Withholding, withholding_id, actor.tenant_id, "WITHHOLDING_NOT_FOUND", "Retención no encontrada")
    ap_service.transition_withholding(db, withholding=w, target=body.target)
    db.commit()
    db.refresh(w)
    return {"id": w.id, "status": w.status}


@router.get("/aging")
def get_aging(party_id: str | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return ap_service.aging(db, company_id=user.tenant_id, party_id=party_id, item_type="RECEIVABLE")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _owned(db: Session, model, obj_id: str, tenant: str, code: str, message: str):
    obj = db.get(model, obj_id)
    if not obj or getattr(obj, "company_id", tenant) != tenant:
        raise NotFoundError(code=code, message=message)
    return obj
