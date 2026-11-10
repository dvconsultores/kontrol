"""API de compras y cuentas por pagar (004).

Endpoints REST `/purchasing/*` con convenciones heredadas de 001 (DOC-03 §14):
errores uniformes, `allowed_actions` en backend, transiciones explícitas,
idempotencia en POST críticos.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_permission, require_write_allowed
from app.core.errors import NotFoundError
from app.modules.identity_access.models import User
from app.modules.purchasing import service as ap_service
from app.modules.purchasing.models import (
    GoodsReceipt,
    GoodsReceiptLine,
    OpenItem,
    Payment,
    PurchaseOrder,
    PurchaseRequisition,
    PurchaseReturn,
    ReceiptConfirmation,
    ReceiptIncident,
    SupplierCreditNote,
    SupplierInvoice,
    SupplierQuote,
    TripleMatch,
    Withholding,
)
from app.shared.clock import InstanteDeEntrada

router = APIRouter(prefix="/purchasing", tags=["compras"])


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #
class RequisitionCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    requester_id: str | None = None
    cost_center_id: str | None = None
    need_date: date | None = None
    warehouse_id: str | None = None


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
    #: Etapa 2 del proceso: programar descarga y recepción.
    unloading_scheduled_at: InstanteDeEntrada | None = None
    #: Etapa 4: referencias contra las que se comparará lo recibido.
    packing_list_ref: str | None = Field(default=None, max_length=120)
    supplier_invoice_ref: str | None = Field(default=None, max_length=120)
    #: Etapa 6: bultos que el documento declara.
    packages_declared: int | None = Field(default=None, ge=0)


class ArrivalBody(BaseModel):
    """Etapa 1: confirmar arribo. Sin momento, se usa el de la confirmación."""
    model_config = ConfigDict(extra="forbid")

    arrival_at: InstanteDeEntrada | None = None
    packages_received: int | None = Field(default=None, ge=0)


class InspectionBody(BaseModel):
    """Etapas 4, 5 y 6: comparación, inspección visual y bultos contados."""
    model_config = ConfigDict(extra="forbid")

    packing_list_match: bool | None = None
    supplier_invoice_match: bool | None = None
    order_match: bool | None = None
    documentation_match: bool | None = None
    packages_received: int | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=2000)


class ReceiptLineCreate(BaseModel):
    order_line_id: str
    product_id: str
    quantity_received: float = Field(gt=0)
    quantity_accepted: float = Field(ge=0)
    quantity_rejected: float = Field(ge=0)
    lot_number: str | None = None
    expiry_date: date | None = None
    serials: list[str] | None = None
    #: Presentación con la que se recibió. La reserva de inventario se hará en
    #: cantidad base, no en la tecleada (Spec 011).
    presentation_id: str | None = None
    #: Etapa 6: lo que se observó en el muelle. La incidencia que derive de esto
    #: es de la Spec 020; el hecho observado es de esta.
    physical_condition: str | None = Field(default=None, max_length=24)
    damaged_quantity: float | None = Field(default=None, ge=0)
    damage_notes: str | None = Field(default=None, max_length=2000)
    identification_ok: bool | None = None
    reference_ok: bool | None = None


class IncidentCreate(BaseModel):
    """Etapa 8: registrar una diferencia.

    No se piden producto, unidad, presentación ni factor: ya viven en la línea
    de recepción y pedirlos otra vez crearía dos verdades para el mismo hecho.
    """
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=64)
    incident_type: str = Field(min_length=1, max_length=32)
    receipt_line_id: str | None = None
    affected_base_quantity: float | None = Field(default=None, gt=0)
    description: str | None = Field(default=None, max_length=2000)


class IncidentEscalateBody(BaseModel):
    """Etapa 10: escalar la novedad a Compras."""
    model_config = ConfigDict(extra="forbid")

    notes: str | None = Field(default=None, max_length=2000)


class IncidentResolveBody(BaseModel):
    """Tratamiento decidido. Registrarlo no es ejecutarlo: eso es de la Spec 021."""
    model_config = ConfigDict(extra="forbid")

    resolution: str = Field(min_length=1, max_length=32)
    reason: str = Field(min_length=1, max_length=2000)


class IncidentCancelBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=2000)


class QualityBody(BaseModel):
    #: Sin veredicto, la recepción confirmada pasa a calidad (QUALITY_PENDING).
    quality_status: str | None = Field(default=None, pattern="^(APPROVED|REJECTED)$")


class ReceiptCancelBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    #: Queda en la auditoría, cuyo campo de motivo admite 255 caracteres.
    reason: str = Field(min_length=1, max_length=255)


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
                      db: Session = Depends(get_db), user: User = Depends(require_permission("compras", "view")), ctx: CompanyContext = Depends(get_company_context)):
    query = select(PurchaseRequisition).where(PurchaseRequisition.company_id == ctx.company_id)
    if status:
        query = query.where(PurchaseRequisition.status == status)
    total = db.execute(select(func.count()).select_from(query.subquery())).scalar() or 0
    items = db.execute(query.order_by(PurchaseRequisition.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return {"items": [{"id": r.id, "code": r.code, "requester_id": r.requester_id, "cost_center_id": r.cost_center_id,
                       "need_date": r.need_date.isoformat() if r.need_date else None, "status": r.status,
                       "warehouse_id": r.warehouse_id} for r in items],
            "total": total, "page": page, "page_size": page_size}


@router.post("/requisitions", dependencies=[Depends(require_write_allowed)])
def create_requisition(body: RequisitionCreate, db: Session = Depends(get_db),
                       actor: User = Depends(require_permission("compras", "create")), ctx: CompanyContext = Depends(get_company_context)):
    req = ap_service.create_requisition(db, company_id=ctx.company_id, code=body.code, requester_id=body.requester_id,
                                        cost_center_id=body.cost_center_id, need_date=body.need_date,
                                        warehouse_id=body.warehouse_id, actor=str(actor.id))
    db.commit()
    db.refresh(req)
    return {"id": req.id, "code": req.code, "status": req.status, "warehouse_id": req.warehouse_id}


@router.post("/requisitions/{req_id}/lines", dependencies=[Depends(require_write_allowed)])
def add_requisition_line(req_id: str, body: RequisitionLineCreate, db: Session = Depends(get_db),
                         actor: User = Depends(require_permission("compras", "create")), ctx: CompanyContext = Depends(get_company_context)):
    req = _owned(db, PurchaseRequisition, req_id, ctx.company_id, "REQUISITION_NOT_FOUND", "Requisición no encontrada")
    line = ap_service.add_requisition_line(db, requisition_id=str(req.id), product_id=body.product_id,
                                           quantity=body.quantity, unit_id=body.unit_id, notes=body.notes)
    db.commit()
    db.refresh(line)
    return {"id": line.id, "product_id": line.product_id, "quantity": line.quantity}


@router.post("/requisitions/{req_id}/transition", dependencies=[Depends(require_write_allowed)])
def transition_requisition(req_id: str, body: TransitionBody, db: Session = Depends(get_db),
                           actor: User = Depends(require_permission("compras", "approve")), ctx: CompanyContext = Depends(get_company_context)):
    req = _owned(db, PurchaseRequisition, req_id, ctx.company_id, "REQUISITION_NOT_FOUND", "Requisición no encontrada")
    ap_service.transition_requisition(db, requisition=req, target=body.target, actor=str(actor.id))
    db.commit()
    db.refresh(req)
    return {"id": req.id, "status": req.status}


# --------------------------------------------------------------------------- #
# Cotizaciones
# --------------------------------------------------------------------------- #
@router.get("/quotes")
def list_quotes(supplier_id: str | None = None, db: Session = Depends(get_db), user: User = Depends(require_permission("compras", "view")), ctx: CompanyContext = Depends(get_company_context)):
    query = select(SupplierQuote).where(SupplierQuote.company_id == ctx.company_id)
    if supplier_id:
        query = query.where(SupplierQuote.supplier_id == supplier_id)
    items = db.execute(query.order_by(SupplierQuote.created_at.desc())).scalars().all()
    return {"items": [{"id": q.id, "code": q.code, "supplier_id": q.supplier_id, "currency": q.currency,
                       "validity_until": q.validity_until.isoformat() if q.validity_until else None, "status": q.status} for q in items],
            "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/quotes", dependencies=[Depends(require_write_allowed)])
def create_quote(body: QuoteCreate, db: Session = Depends(get_db),
                 actor: User = Depends(require_permission("compras", "create")), ctx: CompanyContext = Depends(get_company_context)):
    quote = ap_service.create_quote(db, company_id=ctx.company_id, code=body.code, supplier_id=body.supplier_id,
                                    validity_until=body.validity_until, currency=body.currency, terms=body.terms,
                                    actor=str(actor.id))
    db.commit()
    db.refresh(quote)
    return {"id": quote.id, "code": quote.code, "status": quote.status}


@router.post("/quotes/{quote_id}/lines", dependencies=[Depends(require_write_allowed)])
def add_quote_line(quote_id: str, body: QuoteLineCreate, db: Session = Depends(get_db),
                   actor: User = Depends(require_permission("compras", "create")),
                   ctx: CompanyContext = Depends(get_company_context)):
    line = ap_service.add_quote_line(db, company_id=ctx.company_id, quote_id=quote_id, product_id=body.product_id, quantity=body.quantity,
                                     unit_price=body.unit_price, discount=body.discount,
                                     delivery_days=body.delivery_days, tax_ref=body.tax_ref)
    db.commit()
    db.refresh(line)
    return {"id": line.id, "product_id": line.product_id, "unit_price": line.unit_price}


# --------------------------------------------------------------------------- #
# Órdenes de compra
# --------------------------------------------------------------------------- #
@router.get("/orders")
def list_orders(status: str | None = None, q: str = "", receivable: bool = False, supplier_id: str | None = None,
                page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                db: Session = Depends(get_db), user: User = Depends(require_permission("compras", "view")), ctx: CompanyContext = Depends(get_company_context)):
    query = select(PurchaseOrder).where(PurchaseOrder.company_id == ctx.company_id)
    if status:
        query = query.where(PurchaseOrder.status == status)
    if q:
        query = query.where(PurchaseOrder.code.ilike(f"%{q}%"))
    if supplier_id:
        query = query.where(PurchaseOrder.supplier_id == supplier_id)
    if receivable:
        query = query.where(PurchaseOrder.status.in_(ap_service.RECEIVABLE_ORDER_STATUSES))
    total = db.execute(select(func.count()).select_from(query.subquery())).scalar() or 0
    items = db.execute(query.order_by(PurchaseOrder.created_at.desc(), PurchaseOrder.id)
                       .offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return {"items": [ap_service.order_dict(db, o) for o in items], "total": total, "page": page, "page_size": page_size}


@router.post("/orders", dependencies=[Depends(require_write_allowed)])
def create_order(body: OrderCreate, db: Session = Depends(get_db),
                 actor: User = Depends(require_permission("compras", "create")), ctx: CompanyContext = Depends(get_company_context)):
    order = ap_service.create_order(db, company_id=ctx.company_id, code=body.code, supplier_id=body.supplier_id,
                                    terms=body.terms, expected_date=body.expected_date, currency=body.currency,
                                    actor=str(actor.id))
    db.commit()
    db.refresh(order)
    return ap_service.order_dict(db, order)


@router.get("/orders/{order_id}")
def get_order(order_id: str, db: Session = Depends(get_db), user: User = Depends(require_permission("compras", "view")), ctx: CompanyContext = Depends(get_company_context)):
    order = _owned(db, PurchaseOrder, order_id, ctx.company_id, "ORDER_NOT_FOUND", "Orden no encontrada")
    return ap_service.order_dict(db, order)


@router.post("/orders/{order_id}/lines", dependencies=[Depends(require_write_allowed)])
def add_order_line(order_id: str, body: OrderLineCreate, db: Session = Depends(get_db),
                   actor: User = Depends(require_permission("compras", "create")), ctx: CompanyContext = Depends(get_company_context)):
    order = _owned(db, PurchaseOrder, order_id, ctx.company_id, "ORDER_NOT_FOUND", "Orden no encontrada")
    line = ap_service.add_order_line(db, order_id=str(order.id), product_id=body.product_id,
                                     quantity_ordered=body.quantity_ordered, unit_price=body.unit_price,
                                     discount=body.discount, tax_ref=body.tax_ref, needs_inventory=body.needs_inventory,
                                     snapshot=body.snapshot)
    db.commit()
    db.refresh(line)
    return {"id": line.id, "product_id": line.product_id, "quantity_ordered": line.quantity_ordered}


@router.post("/orders/{order_id}/transition", dependencies=[Depends(require_write_allowed)])
def transition_order(order_id: str, body: TransitionBody, db: Session = Depends(get_db),
                     actor: User = Depends(require_permission("compras", "approve")), ctx: CompanyContext = Depends(get_company_context)):
    order = _owned(db, PurchaseOrder, order_id, ctx.company_id, "ORDER_NOT_FOUND", "Orden no encontrada")
    ap_service.transition_order(db, order=order, target=body.target, actor=str(actor.id), approval_ref=body.approval_ref)
    db.commit()
    db.refresh(order)
    return ap_service.order_dict(db, order)


# --------------------------------------------------------------------------- #
# Recepciones
# --------------------------------------------------------------------------- #
def _receipt_line_dict(line) -> dict:
    return {"id": line.id, "order_line_id": line.order_line_id, "product_id": line.product_id,
            "quantity_received": str(line.quantity_received),
            "quantity_accepted": str(line.quantity_accepted),
            "quantity_rejected": str(line.quantity_rejected),
            # Semántica de unidad (Spec 011): sin esto, dos cajas de doce
            # entrarían al inventario como dos unidades.
            "presentation_id": line.presentation_id, "uom_id": line.uom_id,
            "conversion_factor_snapshot": str(line.conversion_factor_snapshot)
            if line.conversion_factor_snapshot is not None else None,
            "base_quantity_received": str(line.base_quantity_received)
            if line.base_quantity_received is not None else None,
            "base_quantity_accepted": str(line.base_quantity_accepted)
            if line.base_quantity_accepted is not None else None,
            "base_quantity_rejected": str(line.base_quantity_rejected)
            if line.base_quantity_rejected is not None else None,
            "uom_source": line.uom_source,
            # Observación física de la etapa 6.
            "physical_condition": line.physical_condition,
            "damaged_quantity": str(line.damaged_quantity) if line.damaged_quantity is not None else None,
            "damage_notes": line.damage_notes,
            "identification_ok": line.identification_ok, "reference_ok": line.reference_ok,
            "overage_base_quantity": str(line.overage_base_quantity)
            if line.overage_base_quantity is not None else None,
            "lot_number": line.lot_number, "lot_id": line.lot_id,
            "expiry_date": line.expiry_date.isoformat() if line.expiry_date else None,
            "serials": line.serials, "quality": line.quality}


def _receipt_dict(db: Session, receipt) -> dict:
    lines = db.execute(select(GoodsReceiptLine).where(GoodsReceiptLine.receipt_id == receipt.id)
                       .order_by(GoodsReceiptLine.created_at, GoodsReceiptLine.id)).scalars().all()
    return {"id": receipt.id, "code": receipt.code, "order_id": receipt.order_id,
            "warehouse_id": receipt.warehouse_id, "status": receipt.status,
            "quality_status": receipt.quality_status,
            # Etapas 1 y 2: arribo confirmado y descarga programada.
            "arrival_at": receipt.arrival_at.isoformat() if receipt.arrival_at else None,
            "arrival_confirmed_by": receipt.arrival_confirmed_by,
            "unloading_scheduled_at": receipt.unloading_scheduled_at.isoformat()
            if receipt.unloading_scheduled_at else None,
            # Etapa 4: contra qué se comparó y con qué resultado.
            "packing_list_ref": receipt.packing_list_ref,
            "supplier_invoice_ref": receipt.supplier_invoice_ref,
            "packing_list_match": receipt.packing_list_match,
            "supplier_invoice_match": receipt.supplier_invoice_match,
            "order_match": receipt.order_match,
            "documentation_match": receipt.documentation_match,
            # Etapas 5 y 6: inspección y bultos.
            "inspected_at": receipt.inspected_at.isoformat() if receipt.inspected_at else None,
            "inspected_by": receipt.inspected_by, "inspection_notes": receipt.inspection_notes,
            "packages_declared": receipt.packages_declared,
            "packages_received": receipt.packages_received,
            # Etapa 11: acta emitida.
            "record_issued_at": receipt.record_issued_at.isoformat() if receipt.record_issued_at else None,
            "record_issued_by": receipt.record_issued_by,
            "allowed_actions": ap_service.receipt_allowed_actions(receipt),
            "lines": [_receipt_line_dict(x) for x in lines]}


@router.get("/receipts")
def list_receipts(status: str | None = None, db: Session = Depends(get_db), user: User = Depends(require_permission("compras", "view")), ctx: CompanyContext = Depends(get_company_context)):
    query = select(GoodsReceipt).where(GoodsReceipt.company_id == ctx.company_id)
    if status:
        query = query.where(GoodsReceipt.status == status)
    items = db.execute(query.order_by(GoodsReceipt.created_at.desc())).scalars().all()
    filas = db.execute(select(PurchaseOrder.id, PurchaseOrder.code).where(
        PurchaseOrder.company_id == ctx.company_id,
        PurchaseOrder.id.in_([r.order_id for r in items]))).all()
    codigos = {str(fila.id): fila.code for fila in filas}
    return {"items": [{"id": r.id, "code": r.code, "order_id": r.order_id,
                       "order_code": codigos.get(str(r.order_id)), "warehouse_id": r.warehouse_id,
                       "status": r.status, "quality_status": r.quality_status,
                       "arrival_at": r.arrival_at.isoformat() if r.arrival_at else None,
                       "unloading_scheduled_at": r.unloading_scheduled_at.isoformat()
                       if r.unloading_scheduled_at else None,
                       "packages_declared": r.packages_declared, "packages_received": r.packages_received,
                       "inspected_at": r.inspected_at.isoformat() if r.inspected_at else None,
                       "record_issued_at": r.record_issued_at.isoformat() if r.record_issued_at else None,
                       "allowed_actions": ap_service.receipt_allowed_actions(r)}
                      for r in items],
            "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/receipts", dependencies=[Depends(require_write_allowed)])
def create_receipt(body: ReceiptCreate, db: Session = Depends(get_db),
                   actor: User = Depends(require_permission("compras", "create")), ctx: CompanyContext = Depends(get_company_context)):
    receipt = ap_service.create_receipt(db, company_id=ctx.company_id, code=body.code, order_id=body.order_id,
                                        warehouse_id=body.warehouse_id, actor=str(actor.id),
                                        unloading_scheduled_at=body.unloading_scheduled_at,
                                        packing_list_ref=body.packing_list_ref,
                                        supplier_invoice_ref=body.supplier_invoice_ref,
                                        packages_declared=body.packages_declared)
    db.commit()
    db.refresh(receipt)
    return _receipt_dict(db, receipt)


@router.get("/receipts/{receipt_id}")
def get_receipt(receipt_id: str, db: Session = Depends(get_db), user: User = Depends(require_permission("compras", "view")),
                ctx: CompanyContext = Depends(get_company_context)):
    receipt = _owned(db, GoodsReceipt, receipt_id, ctx.company_id, "RECEIPT_NOT_FOUND", "Recepción no encontrada")
    return _receipt_dict(db, receipt)


def _incident_dict(x) -> dict:
    return {"id": x.id, "code": x.code, "receipt_id": x.receipt_id,
            "receipt_line_id": x.receipt_line_id, "incident_type": x.incident_type,
            "affected_base_quantity": str(x.affected_base_quantity)
            if x.affected_base_quantity is not None else None,
            "description": x.description, "status": x.status,
            "escalated_at": x.escalated_at.isoformat() if x.escalated_at else None,
            "escalated_by": x.escalated_by, "escalation_notes": x.escalation_notes,
            "resolution": x.resolution, "resolution_reason": x.resolution_reason,
            "resolved_at": x.resolved_at.isoformat() if x.resolved_at else None,
            "resolved_by": x.resolved_by, "approval_request_id": x.approval_request_id,
            "cancelled_reason": x.cancelled_reason}


@router.get("/incidencias")
def list_incidents(status: str | None = None, incident_type: str | None = None,
                   db: Session = Depends(get_db), user: User = Depends(require_permission("compras", "view")),
                   ctx: CompanyContext = Depends(get_company_context)):
    """Bandeja de incidencias de la empresa, para verlas sin ir recepción a recepción."""
    query = select(ReceiptIncident).where(ReceiptIncident.company_id == ctx.company_id)
    if status:
        query = query.where(ReceiptIncident.status == status)
    if incident_type:
        query = query.where(ReceiptIncident.incident_type == incident_type)
    items = db.execute(query.order_by(ReceiptIncident.created_at.desc())).scalars().all()
    return {"items": [_incident_dict(x) for x in items], "total": len(items),
            "page": 1, "page_size": len(items) or 1}


# --------------------------------------------------------------------------
# Spec 021 — confirmación y conciliación del inventario recibido
# --------------------------------------------------------------------------


class CountBody(BaseModel):
    counted_base_quantity: Decimal = Field(..., description="Contado en unidad base")
    difference_kinds: list[str] = Field(default_factory=list)


class ConfirmationDecision(BaseModel):
    receipt_line_id: str
    target_state: str
    base_quantity: Decimal
    source_state: str = "RECIBIDO"
    incident_id: str | None = None
    reason: str | None = None


class ConfirmationBody(BaseModel):
    decisions: list[ConfirmationDecision]


def _confirmation_dict(x) -> dict:
    return {"id": str(x.id), "receipt_id": x.receipt_id, "receipt_line_id": x.receipt_line_id,
            "source_state": x.source_state, "target_state": x.target_state,
            "base_quantity": str(x.base_quantity), "movement_id": x.movement_id,
            "incident_id": x.incident_id, "reason": x.reason,
            "created_by": x.created_by,
            "created_at": x.created_at.isoformat() if x.created_at else None}


@router.post("/receipts/{receipt_id}/lines/{line_id}/conteo",
             dependencies=[Depends(require_write_allowed)])
def count_receipt_line(receipt_id: str, line_id: str, body: CountBody,
                       db: Session = Depends(get_db),
                       actor: User = Depends(require_permission("inventario", "confirm")),
                       ctx: CompanyContext = Depends(get_company_context)):
    """Etapa 1 del proceso: conteo detallado por SKU, en unidad base."""
    receipt = _owned(db, GoodsReceipt, receipt_id, ctx.company_id,
                     "RECEIPT_NOT_FOUND", "Recepción no encontrada")
    line = ap_service.registrar_conteo(
        db, receipt=receipt, line_id=line_id,
        counted_base_quantity=body.counted_base_quantity,
        difference_kinds=body.difference_kinds, actor=str(actor.id))
    db.commit()
    return _receipt_line_dict(line)


@router.get("/receipts/{receipt_id}/conciliacion")
def receipt_reconciliation(receipt_id: str, db: Session = Depends(get_db),
                           user: User = Depends(require_permission("inventario", "view")),
                           ctx: CompanyContext = Depends(get_company_context)):
    """Etapas 2 a 4 y 9: la comparación por línea y qué falta para confirmar."""
    receipt = _owned(db, GoodsReceipt, receipt_id, ctx.company_id,
                     "RECEIPT_NOT_FOUND", "Recepción no encontrada")
    return ap_service.resultado_de_conciliacion(db, company_id=ctx.company_id, receipt=receipt)


@router.post("/receipts/{receipt_id}/confirmacion-inventario",
             dependencies=[Depends(require_write_allowed)])
def confirm_receipt_inventory(receipt_id: str, body: ConfirmationBody,
                              db: Session = Depends(get_db),
                              actor: User = Depends(require_permission("inventario", "confirm")),
                              ctx: CompanyContext = Depends(get_company_context)):
    """Etapas 13 y 14: confirmar el inventario conciliado y liberar el lote."""
    receipt = _owned(db, GoodsReceipt, receipt_id, ctx.company_id,
                     "RECEIPT_NOT_FOUND", "Recepción no encontrada")
    resultado = ap_service.confirmar_inventario(
        db, receipt=receipt, decisiones=[d.model_dump() for d in body.decisions],
        actor=str(actor.id))
    db.commit()
    return resultado


@router.get("/receipts/{receipt_id}/confirmacion-inventario")
def list_receipt_confirmations(receipt_id: str, db: Session = Depends(get_db),
                               user: User = Depends(require_permission("inventario", "view")),
                               ctx: CompanyContext = Depends(get_company_context)):
    _owned(db, GoodsReceipt, receipt_id, ctx.company_id,
           "RECEIPT_NOT_FOUND", "Recepción no encontrada")
    filas = db.execute(select(ReceiptConfirmation).where(
        ReceiptConfirmation.receipt_id == receipt_id,
        ReceiptConfirmation.company_id == ctx.company_id)).scalars().all()
    return {"items": [_confirmation_dict(x) for x in filas], "total": len(filas),
            "page": 1, "page_size": len(filas) or 1}


@router.get("/receipts/{receipt_id}/incidencias")
def list_receipt_incidents(receipt_id: str, db: Session = Depends(get_db),
                           user: User = Depends(require_permission("compras", "view")),
                           ctx: CompanyContext = Depends(get_company_context)):
    _owned(db, GoodsReceipt, receipt_id, ctx.company_id, "RECEIPT_NOT_FOUND", "Recepción no encontrada")
    items = ap_service.incidencias_de_recepcion(db, company_id=ctx.company_id, receipt_id=receipt_id)
    return {"items": [_incident_dict(x) for x in items], "total": len(items),
            "page": 1, "page_size": len(items) or 1}


@router.get("/receipts/{receipt_id}/incidencias/resultado")
def receipt_incident_outcome(receipt_id: str, db: Session = Depends(get_db),
                             user: User = Depends(require_permission("compras", "view")),
                             ctx: CompanyContext = Depends(get_company_context)):
    """Contrato de salida para la Spec 021: qué se decidió, por línea y tipo."""
    _owned(db, GoodsReceipt, receipt_id, ctx.company_id, "RECEIPT_NOT_FOUND", "Recepción no encontrada")
    return ap_service.resultado_de_incidencias(db, company_id=ctx.company_id, receipt_id=receipt_id)


@router.post("/receipts/{receipt_id}/incidencias", dependencies=[Depends(require_write_allowed)])
def create_receipt_incident(receipt_id: str, body: IncidentCreate, db: Session = Depends(get_db),
                            actor: User = Depends(require_permission("compras", "quality")),
                            ctx: CompanyContext = Depends(get_company_context)):
    _owned(db, GoodsReceipt, receipt_id, ctx.company_id, "RECEIPT_NOT_FOUND", "Recepción no encontrada")
    incident = ap_service.registrar_incidencia(
        db, company_id=ctx.company_id, receipt_id=receipt_id, code=body.code,
        incident_type=body.incident_type, receipt_line_id=body.receipt_line_id,
        affected_base_quantity=body.affected_base_quantity, description=body.description,
        actor=str(actor.id))
    db.commit()
    db.refresh(incident)
    return _incident_dict(incident)


def _owned_incident(db: Session, receipt_id: str, incident_id: str, company_id: str):
    """La cadena entera: empresa → recepción → incidencia.

    Que la incidencia exista y sea alcanzable no la hace de esta recepción.
    """
    _owned(db, GoodsReceipt, receipt_id, company_id, "RECEIPT_NOT_FOUND", "Recepción no encontrada")
    incident = _owned(db, ReceiptIncident, incident_id, company_id,
                      "RECEIPT_INCIDENT_NOT_FOUND", "Incidencia no encontrada")
    if str(incident.receipt_id) != str(receipt_id):
        raise NotFoundError(code="RECEIPT_INCIDENT_NOT_FOUND", message="Incidencia no encontrada")
    return incident


@router.get("/receipts/{receipt_id}/incidencias/{incident_id}")
def get_receipt_incident(receipt_id: str, incident_id: str, db: Session = Depends(get_db),
                         user: User = Depends(require_permission("compras", "view")),
                         ctx: CompanyContext = Depends(get_company_context)):
    return _incident_dict(_owned_incident(db, receipt_id, incident_id, ctx.company_id))


@router.post("/receipts/{receipt_id}/incidencias/{incident_id}/escalate",
             dependencies=[Depends(require_write_allowed)])
def escalate_receipt_incident(receipt_id: str, incident_id: str, body: IncidentEscalateBody,
                              db: Session = Depends(get_db),
                              actor: User = Depends(require_permission("compras", "quality")),
                              ctx: CompanyContext = Depends(get_company_context)):
    _owned_incident(db, receipt_id, incident_id, ctx.company_id)
    incident = ap_service.escalar_incidencia(db, company_id=ctx.company_id, incident_id=incident_id,
                                             notes=body.notes, actor=str(actor.id))
    db.commit()
    db.refresh(incident)
    return _incident_dict(incident)


@router.post("/receipts/{receipt_id}/incidencias/{incident_id}/resolve",
             dependencies=[Depends(require_write_allowed)])
def resolve_receipt_incident(receipt_id: str, incident_id: str, body: IncidentResolveBody,
                             db: Session = Depends(get_db),
                             actor: User = Depends(require_permission("compras", "approve")),
                             ctx: CompanyContext = Depends(get_company_context)):
    _owned_incident(db, receipt_id, incident_id, ctx.company_id)
    incident = ap_service.resolver_incidencia(db, company_id=ctx.company_id, incident_id=incident_id,
                                              resolution=body.resolution, reason=body.reason,
                                              actor=str(actor.id))
    db.commit()
    db.refresh(incident)
    return _incident_dict(incident)


@router.post("/receipts/{receipt_id}/incidencias/{incident_id}/cancel",
             dependencies=[Depends(require_write_allowed)])
def cancel_receipt_incident(receipt_id: str, incident_id: str, body: IncidentCancelBody,
                            db: Session = Depends(get_db),
                            actor: User = Depends(require_permission("compras", "quality")),
                            ctx: CompanyContext = Depends(get_company_context)):
    _owned_incident(db, receipt_id, incident_id, ctx.company_id)
    incident = ap_service.anular_incidencia(db, company_id=ctx.company_id, incident_id=incident_id,
                                            reason=body.reason, actor=str(actor.id))
    db.commit()
    db.refresh(incident)
    return _incident_dict(incident)


@router.post("/receipts/{receipt_id}/arrival", dependencies=[Depends(require_write_allowed)])
def confirm_arrival(receipt_id: str, body: ArrivalBody, db: Session = Depends(get_db),
                    actor: User = Depends(require_permission("compras", "create")),
                    ctx: CompanyContext = Depends(get_company_context)):
    """Etapa 1: confirmar el arribo de la mercancía."""
    _owned(db, GoodsReceipt, receipt_id, ctx.company_id, "RECEIPT_NOT_FOUND", "Recepción no encontrada")
    receipt = ap_service.confirmar_arribo(db, company_id=ctx.company_id, receipt_id=receipt_id,
                                          arrival_at=body.arrival_at, packages_received=body.packages_received,
                                          actor=str(actor.id))
    db.commit()
    db.refresh(receipt)
    return _receipt_dict(db, receipt)


@router.post("/receipts/{receipt_id}/inspection", dependencies=[Depends(require_write_allowed)])
def register_inspection(receipt_id: str, body: InspectionBody, db: Session = Depends(get_db),
                        actor: User = Depends(require_permission("compras", "quality")),
                        ctx: CompanyContext = Depends(get_company_context)):
    """Etapas 4, 5 y 6: comparar contra los documentos, inspeccionar y contar bultos."""
    _owned(db, GoodsReceipt, receipt_id, ctx.company_id, "RECEIPT_NOT_FOUND", "Recepción no encontrada")
    receipt = ap_service.registrar_inspeccion(
        db, company_id=ctx.company_id, receipt_id=receipt_id,
        packing_list_match=body.packing_list_match, supplier_invoice_match=body.supplier_invoice_match,
        order_match=body.order_match, documentation_match=body.documentation_match,
        packages_received=body.packages_received, notes=body.notes, actor=str(actor.id))
    db.commit()
    db.refresh(receipt)
    return _receipt_dict(db, receipt)


@router.post("/receipts/{receipt_id}/lines", dependencies=[Depends(require_write_allowed)])
def add_receipt_line(receipt_id: str, body: ReceiptLineCreate, db: Session = Depends(get_db),
                     actor: User = Depends(require_permission("compras", "create")),
                     ctx: CompanyContext = Depends(get_company_context)):
    _owned(db, GoodsReceipt, receipt_id, ctx.company_id, "RECEIPT_NOT_FOUND", "Recepción no encontrada")
    line = ap_service.add_receipt_line(db, company_id=ctx.company_id, receipt_id=receipt_id, order_line_id=body.order_line_id,
                                       product_id=body.product_id, quantity_received=body.quantity_received,
                                       quantity_accepted=body.quantity_accepted, quantity_rejected=body.quantity_rejected,
                                       lot_number=body.lot_number, expiry_date=body.expiry_date, serials=body.serials,
                                       presentation_id=body.presentation_id,
                                       physical_condition=body.physical_condition,
                                       damaged_quantity=body.damaged_quantity, damage_notes=body.damage_notes,
                                       identification_ok=body.identification_ok, reference_ok=body.reference_ok)
    db.commit()
    db.refresh(line)
    return _receipt_line_dict(line)


@router.post("/receipts/{receipt_id}/confirm", dependencies=[Depends(require_write_allowed)])
def confirm_receipt(receipt_id: str, db: Session = Depends(get_db),
                    actor: User = Depends(require_permission("compras", "create")), ctx: CompanyContext = Depends(get_company_context)):
    receipt = _owned(db, GoodsReceipt, receipt_id, ctx.company_id, "RECEIPT_NOT_FOUND", "Recepción no encontrada")
    ap_service.confirm_receipt(db, receipt=receipt, actor=str(actor.id))
    db.commit()
    db.refresh(receipt)
    return {"id": receipt.id, "status": receipt.status}


@router.post("/receipts/{receipt_id}/quality", dependencies=[Depends(require_write_allowed)])
def set_receipt_quality(receipt_id: str, body: QualityBody, db: Session = Depends(get_db),
                        actor: User = Depends(require_permission("compras", "quality")), ctx: CompanyContext = Depends(get_company_context)):
    receipt = _owned(db, GoodsReceipt, receipt_id, ctx.company_id, "RECEIPT_NOT_FOUND", "Recepción no encontrada")
    if body.quality_status is None:
        ap_service.enviar_a_calidad(db, receipt=receipt, actor=str(actor.id))
    else:
        ap_service.registrar_conformidad(db, receipt=receipt, quality_status=body.quality_status,
                                         actor=str(actor.id))
    db.commit()
    db.refresh(receipt)
    return {"id": receipt.id, "status": receipt.status, "quality_status": receipt.quality_status}


@router.post("/receipts/{receipt_id}/accept", dependencies=[Depends(require_write_allowed)])
def accept_receipt(receipt_id: str, db: Session = Depends(get_db),
                   actor: User = Depends(require_permission("compras", "quality")), ctx: CompanyContext = Depends(get_company_context)):
    receipt = _owned(db, GoodsReceipt, receipt_id, ctx.company_id, "RECEIPT_NOT_FOUND", "Recepción no encontrada")
    ap_service.accept_receipt(db, receipt=receipt, actor=str(actor.id))
    db.commit()
    db.refresh(receipt)
    return {"id": receipt.id, "status": receipt.status}


@router.post("/receipts/{receipt_id}/close", dependencies=[Depends(require_write_allowed)])
def close_receipt(receipt_id: str, db: Session = Depends(get_db),
                  actor: User = Depends(require_permission("compras", "approve")),
                  ctx: CompanyContext = Depends(get_company_context)):
    receipt = _owned(db, GoodsReceipt, receipt_id, ctx.company_id, "RECEIPT_NOT_FOUND", "Recepción no encontrada")
    ap_service.cerrar_recepcion(db, receipt=receipt, actor=str(actor.id))
    db.commit()
    db.refresh(receipt)
    return {"id": receipt.id, "status": receipt.status}


@router.post("/receipts/{receipt_id}/cancel", dependencies=[Depends(require_write_allowed)])
def cancel_receipt(receipt_id: str, body: ReceiptCancelBody, db: Session = Depends(get_db),
                   actor: User = Depends(require_permission("compras", "approve")),
                   ctx: CompanyContext = Depends(get_company_context)):
    receipt = _owned(db, GoodsReceipt, receipt_id, ctx.company_id, "RECEIPT_NOT_FOUND", "Recepción no encontrada")
    ap_service.anular_recepcion(db, receipt=receipt, reason=body.reason, actor=str(actor.id))
    db.commit()
    db.refresh(receipt)
    return {"id": receipt.id, "status": receipt.status}


# --------------------------------------------------------------------------- #
# Facturas del proveedor y conciliación triple
# --------------------------------------------------------------------------- #
@router.get("/supplier-invoices")
def list_invoices(status: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                  db: Session = Depends(get_db), user: User = Depends(require_permission("compras", "view")), ctx: CompanyContext = Depends(get_company_context)):
    query = select(SupplierInvoice).where(SupplierInvoice.company_id == ctx.company_id)
    if status:
        query = query.where(SupplierInvoice.status == status)
    total = db.execute(select(func.count()).select_from(query.subquery())).scalar() or 0
    items = db.execute(query.order_by(SupplierInvoice.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return {"items": [ap_service.invoice_dict(i) for i in items], "total": total, "page": page, "page_size": page_size}


@router.post("/supplier-invoices", dependencies=[Depends(require_write_allowed)])
def create_invoice(body: InvoiceCreate, db: Session = Depends(get_db),
                   actor: User = Depends(require_permission("compras", "create")), ctx: CompanyContext = Depends(get_company_context)):
    invoice = ap_service.create_invoice(db, company_id=ctx.company_id, supplier_id=body.supplier_id,
                                        invoice_number=body.invoice_number, control_number=body.control_number,
                                        issue_date=body.issue_date, currency=body.currency, actor=str(actor.id),
                                        idempotency_key=body.idempotency_key)
    db.commit()
    db.refresh(invoice)
    return ap_service.invoice_dict(invoice)


@router.get("/supplier-invoices/{invoice_id}")
def get_invoice(invoice_id: str, db: Session = Depends(get_db), user: User = Depends(require_permission("compras", "view")), ctx: CompanyContext = Depends(get_company_context)):
    invoice = _owned(db, SupplierInvoice, invoice_id, ctx.company_id, "INVOICE_NOT_FOUND", "Factura no encontrada")
    return ap_service.invoice_dict(invoice)


@router.post("/supplier-invoices/{invoice_id}/lines", dependencies=[Depends(require_write_allowed)])
def add_invoice_line(invoice_id: str, body: InvoiceLineCreate, db: Session = Depends(get_db),
                     actor: User = Depends(require_permission("compras", "create")), ctx: CompanyContext = Depends(get_company_context)):
    invoice = _owned(db, SupplierInvoice, invoice_id, ctx.company_id, "INVOICE_NOT_FOUND", "Factura no encontrada")
    line = ap_service.add_invoice_line(db, invoice_id=invoice_id, product_id=body.product_id, quantity=body.quantity,
                                       unit_price=body.unit_price, tax_amount=body.tax_amount,
                                       order_line_id=body.order_line_id, receipt_line_id=body.receipt_line_id,
                                       snapshot=body.snapshot)
    ap_service.recompute_invoice_total(db, invoice=invoice)
    db.commit()
    db.refresh(line)
    return {"id": line.id, "product_id": line.product_id, "total": line.total}


@router.post("/supplier-invoices/{invoice_id}/transition", dependencies=[Depends(require_write_allowed)])
def transition_invoice(invoice_id: str, body: TransitionBody, db: Session = Depends(get_db),
                       actor: User = Depends(require_permission("compras", "approve")), ctx: CompanyContext = Depends(get_company_context)):
    invoice = _owned(db, SupplierInvoice, invoice_id, ctx.company_id, "INVOICE_NOT_FOUND", "Factura no encontrada")
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
def list_triple_match(invoice_id: str | None = None, db: Session = Depends(get_db), user: User = Depends(require_permission("compras", "view")), ctx: CompanyContext = Depends(get_company_context)):
    query = select(TripleMatch).where(TripleMatch.company_id == ctx.company_id)
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
def list_returns(db: Session = Depends(get_db), user: User = Depends(require_permission("compras", "view")), ctx: CompanyContext = Depends(get_company_context)):
    items = db.execute(select(PurchaseReturn).where(PurchaseReturn.company_id == ctx.company_id)
                       .order_by(PurchaseReturn.created_at.desc())).scalars().all()
    return {"items": [{"id": r.id, "code": r.code, "source_document": r.source_document,
                        "reason": r.reason, "condition": r.condition,
                        "inventory_destination": r.inventory_destination, "status": r.status} for r in items],
            "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/returns", dependencies=[Depends(require_write_allowed)])
def create_return(body: ReturnCreate, db: Session = Depends(get_db),
                  actor: User = Depends(require_permission("compras", "create")), ctx: CompanyContext = Depends(get_company_context)):
    ret = ap_service.create_return(db, company_id=ctx.company_id, code=body.code, source_document=body.source_document,
                                   reason=body.reason, condition=body.condition,
                                   inventory_destination=body.inventory_destination, actor=str(actor.id))
    db.commit()
    db.refresh(ret)
    return {"id": ret.id, "code": ret.code, "status": ret.status}


@router.post("/returns/{return_id}/lines", dependencies=[Depends(require_write_allowed)])
def add_return_line(return_id: str, body: ReturnLineCreate, db: Session = Depends(get_db),
                    actor: User = Depends(require_permission("compras", "create")),
                    ctx: CompanyContext = Depends(get_company_context)):
    line = ap_service.add_return_line(db, company_id=ctx.company_id, return_id=return_id, product_id=body.product_id,
                                      quantity=body.quantity, condition=body.condition)
    db.commit()
    db.refresh(line)
    return {"id": line.id, "product_id": line.product_id, "quantity": line.quantity}


@router.get("/credit-notes")
def list_credit_notes(db: Session = Depends(get_db), user: User = Depends(require_permission("compras", "view")), ctx: CompanyContext = Depends(get_company_context)):
    items = db.execute(select(SupplierCreditNote).where(SupplierCreditNote.company_id == ctx.company_id)
                       .order_by(SupplierCreditNote.created_at.desc())).scalars().all()
    return {"items": [{"id": n.id, "number": n.number, "party_id": n.supplier_id,
                        "invoice_ref": n.invoice_ref, "amount": float(n.amount), "applied": float(n.applied),
                        "currency": n.currency, "status": n.status} for n in items],
            "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/credit-notes", dependencies=[Depends(require_write_allowed)])
def create_credit_note(body: CreditNoteCreate, db: Session = Depends(get_db),
                       actor: User = Depends(require_permission("compras", "create")), ctx: CompanyContext = Depends(get_company_context)):
    note = ap_service.create_credit_note(db, company_id=ctx.company_id, supplier_id=body.supplier_id,
                                         number=body.number, amount=body.amount, invoice_ref=body.invoice_ref,
                                         currency=body.currency, actor=str(actor.id))
    db.commit()
    db.refresh(note)
    return {"id": note.id, "number": note.number, "amount": note.amount, "status": note.status}


@router.post("/credit-notes/{note_id}/post", dependencies=[Depends(require_write_allowed)])
def post_credit_note(note_id: str, db: Session = Depends(get_db),
                     actor: User = Depends(require_permission("compras", "approve")), ctx: CompanyContext = Depends(get_company_context)):
    note = _owned(db, SupplierCreditNote, note_id, ctx.company_id, "CREDIT_NOTE_NOT_FOUND", "Nota de crédito no encontrada")
    ap_service.post_credit_note(db, note=note)
    db.commit()
    db.refresh(note)
    return {"id": note.id, "status": note.status}


# --------------------------------------------------------------------------- #
# CxP — open items, pagos, aplicaciones, anticipos, retenciones, aging
# --------------------------------------------------------------------------- #
@router.get("/open-items")
def list_open_items(party_id: str | None = None, status: str | None = None,
                    db: Session = Depends(get_db), user: User = Depends(require_permission("compras", "view")), ctx: CompanyContext = Depends(get_company_context)):
    query = select(OpenItem).where(OpenItem.company_id == ctx.company_id)
    if party_id:
        query = query.where(OpenItem.party_id == party_id)
    if status:
        query = query.where(OpenItem.status == status)
    items = db.execute(query.order_by(OpenItem.due_date.asc().nulls_last())).scalars().all()
    return {"items": [ap_service.open_item_dict(i) for i in items], "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.get("/payments")
def list_payments(status: str | None = None, db: Session = Depends(get_db), user: User = Depends(require_permission("compras", "view")), ctx: CompanyContext = Depends(get_company_context)):
    query = select(Payment).where(Payment.company_id == ctx.company_id)
    if status:
        query = query.where(Payment.status == status)
    items = db.execute(query.order_by(Payment.created_at.desc())).scalars().all()
    return {"items": [ap_service.payment_dict(p) for p in items], "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/payments", dependencies=[Depends(require_write_allowed)])
def create_payment(body: PaymentCreate, db: Session = Depends(get_db),
                   actor: User = Depends(require_permission("compras", "create")), ctx: CompanyContext = Depends(get_company_context)):
    payment = ap_service.register_payment(db, company_id=ctx.company_id, party_id=body.party_id, amount=body.amount,
                                          currency=body.currency, instruments=body.instruments, actor=str(actor.id),
                                          idempotency_key=body.idempotency_key)
    db.commit()
    db.refresh(payment)
    return ap_service.payment_dict(payment)


@router.post("/payments/{payment_id}/transition", dependencies=[Depends(require_write_allowed)])
def transition_payment(payment_id: str, body: TransitionBody, db: Session = Depends(get_db),
                       actor: User = Depends(require_permission("compras", "approve")), ctx: CompanyContext = Depends(get_company_context)):
    payment = _owned(db, Payment, payment_id, ctx.company_id, "PAYMENT_NOT_FOUND", "Pago no encontrado")
    ap_service.transition_payment(db, payment=payment, target=body.target, actor=str(actor.id))
    db.commit()
    db.refresh(payment)
    return ap_service.payment_dict(payment)


@router.post("/applications", dependencies=[Depends(require_write_allowed)])
def create_application(body: ApplicationCreate, db: Session = Depends(get_db),
                       actor: User = Depends(require_permission("compras", "apply")), ctx: CompanyContext = Depends(get_company_context)):
    app = ap_service.apply_source(db, company_id=ctx.company_id, source_type=body.source_type, source_id=body.source_id,
                                  target_open_item_id=body.target_open_item_id, amount=body.amount,
                                  currency=body.currency, rate=body.rate, actor=str(actor.id))
    db.commit()
    db.refresh(app)
    return {"id": app.id, "source_type": app.source_type, "source_id": app.source_id,
            "target_open_item_id": app.target_open_item_id, "amount": app.amount, "status": app.status}


@router.post("/advances", dependencies=[Depends(require_write_allowed)])
def create_advance(body: AdvanceCreate, db: Session = Depends(get_db),
                   actor: User = Depends(require_permission("compras", "create")), ctx: CompanyContext = Depends(get_company_context)):
    adv = ap_service.register_advance(db, company_id=ctx.company_id, party_id=body.party_id, amount=body.amount,
                                      currency=body.currency, actor=str(actor.id))
    db.commit()
    db.refresh(adv)
    return {"id": adv.id, "party_id": adv.party_id, "amount": adv.amount, "available": adv.available, "status": adv.status}


@router.post("/withholdings", dependencies=[Depends(require_write_allowed)])
def create_withholding(body: WithholdingCreate, db: Session = Depends(get_db),
                       actor: User = Depends(require_permission("compras", "create")), ctx: CompanyContext = Depends(get_company_context)):
    w = ap_service.create_withholding(db, company_id=ctx.company_id, party_id=body.party_id, tax_type=body.tax_type,
                                      rule_ref=body.rule_ref, base=body.base, rate_ref=body.rate_ref,
                                      amount=body.amount, period=body.period, source_event=body.source_event,
                                      actor=str(actor.id), party_role="PROVEEDOR")
    db.commit()
    db.refresh(w)
    return {"id": w.id, "party_id": w.party_id, "tax_type": w.tax_type, "amount": w.amount, "status": w.status}


@router.post("/withholdings/{withholding_id}/transition", dependencies=[Depends(require_write_allowed)])
def transition_withholding(withholding_id: str, body: TransitionBody, db: Session = Depends(get_db),
                           actor: User = Depends(require_permission("compras", "approve")), ctx: CompanyContext = Depends(get_company_context)):
    w = _owned(db, Withholding, withholding_id, ctx.company_id, "WITHHOLDING_NOT_FOUND", "Retención no encontrada")
    ap_service.transition_withholding(db, withholding=w, target=body.target)
    db.commit()
    db.refresh(w)
    return {"id": w.id, "status": w.status}


@router.get("/aging")
def get_aging(party_id: str | None = None, db: Session = Depends(get_db), user: User = Depends(require_permission("compras", "view")), ctx: CompanyContext = Depends(get_company_context)):
    return ap_service.aging(db, company_id=ctx.company_id, party_id=party_id)


@router.post("/payment-schedules", dependencies=[Depends(require_write_allowed)])
def create_schedule(body: ScheduleCreate, db: Session = Depends(get_db),
                    actor: User = Depends(require_permission("compras", "create")), ctx: CompanyContext = Depends(get_company_context)):
    schedule = ap_service.create_schedule(db, company_id=ctx.company_id, party_id=body.party_id,
                                          due_date=body.due_date, amount=body.amount, actor=str(actor.id))
    db.commit()
    db.refresh(schedule)
    return {"id": schedule.id, "party_id": schedule.party_id, "due_date": schedule.due_date.isoformat() if schedule.due_date else None,
            "amount": schedule.amount, "status": schedule.status}


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _owned(db: Session, model, obj_id: str, tenant: str, code: str, message: str):
    if "company_id" not in model.__table__.c:
        raise TypeError(f"{model.__name__} no tiene company_id: su propiedad se comprueba por su ruta de autoridad")
    obj = db.get(model, obj_id)
    if obj is None or obj.company_id != tenant:
        raise NotFoundError(code=code, message=message)
    return obj
