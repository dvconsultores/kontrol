"""API de ventas y cuentas por cobrar (005).

Endpoints REST `/sales/*` con convenciones heredadas de 001 (DOC-03 §14):
errores uniformes, `allowed_actions` en backend, transiciones explícitas,
idempotencia en POST críticos.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission, require_write_allowed
from app.core.errors import NotFoundError
from app.modules.identity_access.models import User
from app.modules.purchasing import service as ap_service
from app.modules.purchasing.models import OpenItem, Payment, Withholding
from app.modules.sales import service as sales_service
from app.modules.sales.models import (
    PickList,
    SalesCreditNote,
    SalesDebitNote,
    SalesInvoice,
    SalesOrder,
    SalesQuote,
    SalesQuoteLine,
    SalesReturn,
    Shipment,
)

router = APIRouter(prefix="/sales", tags=["ventas"])


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #
class QuoteCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    customer_id: str
    #: Texto libre heredado. Se conserva; la referencia real es `price_list_id`.
    price_list: str | None = None
    price_list_id: str | None = None
    validity_until: date | None = None
    currency: str = "VED"


class QuoteLineCreate(BaseModel):
    product_id: str
    quantity: float = Field(gt=0)
    #: Opcional: si no viene, lo resuelve la autoridad comercial (Spec 012).
    unit_price: float | None = Field(default=None, ge=0)
    discount: float = 0.0
    tax_ref: str | None = None
    presentation_id: str | None = None
    #: Obligatorio cuando el precio difiere del resuelto.
    manual_reason: str | None = None


class OrderCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    customer_id: str
    warehouse_id: str | None = None
    margin: float | None = None
    currency: str = "VED"


class OrderLineCreate(BaseModel):
    product_id: str
    quantity: float = Field(gt=0)
    #: Opcional: si no viene, lo resuelve la autoridad comercial (Spec 012),
    #: igual que en la cotización (FR-029-041).
    unit_price: float | None = Field(default=None, ge=0)
    discount: float = 0.0
    tax_ref: str | None = None
    needs_inventory: bool = True
    snapshot: str | None = None
    #: Presentación comercial: la reserva se hará en cantidad base (Spec 011).
    presentation_id: str | None = None
    manual_reason: str | None = None


class TransitionBody(BaseModel):
    target: str
    credit_decision: str | None = None
    approval_ref: str | None = None
    #: Obligatorio para `REJECTED`, `CANCELLED` y `DRAFT` (Spec 030).
    reason: str | None = None


class ReasonBody(BaseModel):
    """Rechazar, revertir y cancelar exigen motivo (IMP-030-035). El cuerpo es
    estricto: `company_id` u otro campo ajeno responde 422, nunca se lee."""
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=500)


class ReservationPolicyBody(BaseModel):
    """Lo único configurable de la reserva: la vigencia mientras se evalúa el
    crédito. El disparador es fijo (D0-03)."""
    model_config = ConfigDict(extra="forbid")

    reservation_ttl_days: int | None = Field(default=None, ge=1, le=3650)


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
def list_quotes(customer_id: str | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user), ctx: CompanyContext = Depends(get_company_context)):
    query = select(SalesQuote).where(SalesQuote.company_id == ctx.company_id)
    if customer_id:
        query = query.where(SalesQuote.customer_id == customer_id)
    items = db.execute(query.order_by(SalesQuote.created_at.desc())).scalars().all()
    return {"items": [{"id": q.id, "code": q.code, "customer_id": q.customer_id, "currency": q.currency, "status": q.status} for q in items],
            "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/quotes", dependencies=[Depends(require_write_allowed)])
def create_quote(body: QuoteCreate, db: Session = Depends(get_db),
                 actor: User = Depends(require_permission("ventas", "create")), ctx: CompanyContext = Depends(get_company_context)):
    quote = sales_service.create_quote(db, company_id=ctx.company_id, code=body.code, customer_id=body.customer_id,
                                       price_list=body.price_list, price_list_id=body.price_list_id, validity_until=body.validity_until,
                                       currency=body.currency, actor=str(actor.id))
    db.commit()
    db.refresh(quote)
    return {"id": quote.id, "code": quote.code, "status": quote.status}


@router.post("/quotes/{quote_id}/lines", dependencies=[Depends(require_write_allowed)])
def add_quote_line(quote_id: str, body: QuoteLineCreate, db: Session = Depends(get_db),
                   actor: User = Depends(require_permission("ventas", "create")),
                   ctx: CompanyContext = Depends(get_company_context)):
    line = sales_service.add_quote_line(
        db, company_id=ctx.company_id, quote_id=quote_id, product_id=body.product_id,
        quantity=body.quantity, unit_price=body.unit_price, discount=body.discount,
        tax_ref=body.tax_ref, presentation_id=body.presentation_id,
        manual_reason=body.manual_reason)
    db.commit()
    db.refresh(line)
    return _linea(line)


def _linea(f) -> dict:
    """La línea **con su origen**. Sin esto, la evidencia se guarda y no se ve."""
    return {
        "id": str(f.id), "product_id": str(f.product_id), "quantity": str(f.quantity),
        "unit_price": str(f.unit_price), "discount": str(f.discount or 0),
        "presentation_id": str(f.presentation_id) if f.presentation_id else None,
        "pricing_source": f.pricing_source,
        "price_source_version_id": str(f.price_source_version_id) if f.price_source_version_id else None,
        "price_source_item_id": str(f.price_source_item_id) if f.price_source_item_id else None,
        "resolved_unit_price": str(f.resolved_unit_price) if f.resolved_unit_price is not None else None,
        "manual_reason": f.manual_reason,
        "discount_policy_id": str(f.discount_policy_id) if f.discount_policy_id else None,
        "discount_policy_version": f.discount_policy_version,
        "payment_term_snapshot": f.payment_term_snapshot,
    }


class QuoteTransitionIn(BaseModel):
    target: str = Field(pattern="^(SENT|ACCEPTED|REJECTED|EXPIRED|CANCELLED)$")


class QuoteConvertIn(BaseModel):
    warehouse_id: str | None = None


@router.get("/quotes/{quote_id}")
def get_quote(quote_id: str, db: Session = Depends(get_db),
              user: User = Depends(get_current_user),
              ctx: CompanyContext = Depends(get_company_context)):
    """La cotización con sus líneas y el origen de cada precio."""
    quote = _owned(db, SalesQuote, quote_id, ctx.company_id,
                   "SALES_QUOTE_NOT_FOUND", "Cotización no encontrada")
    lineas = db.execute(select(SalesQuoteLine)
                        .where(SalesQuoteLine.quote_id == str(quote.id))).scalars().all()
    pedido = db.execute(select(SalesOrder)
                        .where(SalesOrder.quote_id == str(quote.id))).scalars().first()
    return {"id": str(quote.id), "code": quote.code, "status": quote.status,
            "customer_id": str(quote.customer_id), "currency": quote.currency,
            "validity_until": str(quote.validity_until) if quote.validity_until else None,
            "price_list_id": str(quote.price_list_id) if quote.price_list_id else None,
            "price_list_legacy": quote.price_list,
            "order_id": str(pedido.id) if pedido else None,
            "lines": [_linea(f) for f in lineas]}


@router.post("/quotes/{quote_id}/transition", dependencies=[Depends(require_write_allowed)])
def transition_quote(quote_id: str, body: QuoteTransitionIn, db: Session = Depends(get_db),
                     actor: User = Depends(require_permission("ventas", "create")),
                     ctx: CompanyContext = Depends(get_company_context)):
    quote = sales_service.transicionar_cotizacion(
        db, company_id=ctx.company_id, quote_id=quote_id, destino=body.target,
        actor=str(actor.id))
    db.commit()
    db.refresh(quote)
    return {"id": str(quote.id), "status": quote.status}


@router.post("/quotes/{quote_id}/convertir", dependencies=[Depends(require_write_allowed)])
def convert_quote(quote_id: str, body: QuoteConvertIn, db: Session = Depends(get_db),
                  actor: User = Depends(require_permission("ventas", "create")),
                  ctx: CompanyContext = Depends(get_company_context)):
    """Convierte la cotización en pedido, **una sola vez**.

    Convertir dos veces devuelve el pedido que ya existe con `201` la primera y
    `200` después: un doble clic no produce dos pedidos.
    """
    pedido, creado = sales_service.convertir_en_pedido(
        db, company_id=ctx.company_id, quote_id=quote_id,
        warehouse_id=body.warehouse_id, actor=str(actor.id))
    db.commit()
    db.refresh(pedido)
    return JSONResponse(
        status_code=201 if creado else 200,
        content={"id": str(pedido.id), "code": pedido.code, "status": pedido.status,
                 "quote_id": str(pedido.quote_id), "created": creado})


@router.get("/orders")
def list_orders(status: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                db: Session = Depends(get_db), user: User = Depends(get_current_user), ctx: CompanyContext = Depends(get_company_context)):
    query = select(SalesOrder).where(SalesOrder.company_id == ctx.company_id)
    if status:
        query = query.where(SalesOrder.status == status)
    total = db.execute(select(func.count()).select_from(query.subquery())).scalar() or 0
    items = db.execute(query.order_by(SalesOrder.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return {"items": sales_service.orders_dict(db, list(items)), "total": total, "page": page, "page_size": page_size}


@router.post("/orders", dependencies=[Depends(require_write_allowed)])
def create_order(body: OrderCreate, db: Session = Depends(get_db),
                 actor: User = Depends(require_permission("ventas", "create")), ctx: CompanyContext = Depends(get_company_context)):
    order = sales_service.create_order(db, company_id=ctx.company_id, code=body.code, customer_id=body.customer_id,
                                       warehouse_id=body.warehouse_id, margin=body.margin, currency=body.currency,
                                       actor=str(actor.id))
    db.commit()
    db.refresh(order)
    return sales_service.order_dict(db, order)


@router.get("/orders/{order_id}")
def get_order(order_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user), ctx: CompanyContext = Depends(get_company_context)):
    order = _owned(db, SalesOrder, order_id, ctx.company_id, "SALES_ORDER_NOT_FOUND", "Orden no encontrada")
    return sales_service.order_dict(db, order)


@router.post("/orders/{order_id}/lines", dependencies=[Depends(require_write_allowed)])
def add_order_line(order_id: str, body: OrderLineCreate, db: Session = Depends(get_db),
                   actor: User = Depends(require_permission("ventas", "create")), ctx: CompanyContext = Depends(get_company_context)):
    order = _owned(db, SalesOrder, order_id, ctx.company_id, "SALES_ORDER_NOT_FOUND", "Orden no encontrada")
    line = sales_service.add_order_line(db, order_id=str(order.id), product_id=body.product_id, quantity=body.quantity,
                                        unit_price=body.unit_price, discount=body.discount, tax_ref=body.tax_ref,
                                        needs_inventory=body.needs_inventory, snapshot=body.snapshot,
                                        company_id=ctx.company_id, presentation_id=body.presentation_id,
                                        manual_reason=body.manual_reason)
    db.commit()
    db.refresh(line)
    return {"id": line.id, "product_id": line.product_id, "quantity": line.quantity,
            "unit_price": str(line.unit_price), "pricing_source": line.pricing_source,
            "presentation_id": line.presentation_id,
            "base_quantity": str(line.base_quantity) if line.base_quantity is not None else None,
            "conversion_factor_snapshot": (str(line.conversion_factor_snapshot)
                                           if line.conversion_factor_snapshot is not None else None)}


# --------------------------------------------------------------------------- #
# Spec 030 — confirmación, crédito, reserva y ciclo del pedido
# --------------------------------------------------------------------------- #
@router.post("/orders/expire-reservations", dependencies=[Depends(require_write_allowed)])
def expire_order_reservations(db: Session = Depends(get_db),
                              actor: User = Depends(require_permission("ventas", "approve")),
                              ctx: CompanyContext = Depends(get_company_context)):
    """Vence las reservas de pedidos con TTL cumplido y los pedidos que las
    sostenían. Idempotente. Lo lanza un operador o el planificador de la
    plataforma cuando exista (Spec 047); aquí no hay worker."""
    resultado = sales_service.expirar_reservas_de_pedidos(db, company_id=ctx.company_id, actor=str(actor.id))
    db.commit()
    return resultado


@router.get("/settings/reservation")
def get_reservation_policy(db: Session = Depends(get_db), user: User = Depends(get_current_user),
                           ctx: CompanyContext = Depends(get_company_context)):
    return sales_service.politica_de_reserva(db, company_id=ctx.company_id)


@router.put("/settings/reservation", dependencies=[Depends(require_write_allowed)])
def put_reservation_policy(body: ReservationPolicyBody, db: Session = Depends(get_db),
                           actor: User = Depends(require_permission("ventas", "approve")),
                           ctx: CompanyContext = Depends(get_company_context)):
    resultado = sales_service.configurar_reserva(db, company_id=ctx.company_id,
                                                 reservation_ttl_days=body.reservation_ttl_days,
                                                 actor=str(actor.id))
    db.commit()
    return resultado


@router.post("/orders/{order_id}/submit", dependencies=[Depends(require_write_allowed)])
def submit_order(order_id: str, db: Session = Depends(get_db),
                 actor: User = Depends(require_permission("ventas", "submit")),
                 ctx: CompanyContext = Depends(get_company_context)):
    """Confirmación comercial: `DRAFT → SUBMITTED` con reserva (ADR-D0-003 v2)."""
    order = _owned(db, SalesOrder, order_id, ctx.company_id, "SALES_ORDER_NOT_FOUND", "Orden no encontrada")
    order = sales_service.confirmar_pedido(db, company_id=ctx.company_id, order_id=str(order.id), actor=str(actor.id))
    db.commit()
    db.refresh(order)
    return sales_service.order_dict(db, order)


@router.post("/orders/{order_id}/release", dependencies=[Depends(require_write_allowed)])
def release_order(order_id: str, db: Session = Depends(get_db),
                  actor: User = Depends(require_permission("ventas", "approve")),
                  ctx: CompanyContext = Depends(get_company_context)):
    """`SUBMITTED → RELEASED` tras la decisión favorable de la Spec 045."""
    order = _owned(db, SalesOrder, order_id, ctx.company_id, "SALES_ORDER_NOT_FOUND", "Orden no encontrada")
    order = sales_service.liberar_pedido(db, company_id=ctx.company_id, order_id=str(order.id), actor=str(actor.id))
    db.commit()
    db.refresh(order)
    return sales_service.order_dict(db, order)


@router.post("/orders/{order_id}/reject", dependencies=[Depends(require_write_allowed)])
def reject_order(order_id: str, body: ReasonBody, db: Session = Depends(get_db),
                 actor: User = Depends(require_permission("ventas", "approve")),
                 ctx: CompanyContext = Depends(get_company_context)):
    order = _owned(db, SalesOrder, order_id, ctx.company_id, "SALES_ORDER_NOT_FOUND", "Orden no encontrada")
    order = sales_service.rechazar_pedido(db, company_id=ctx.company_id, order_id=str(order.id),
                                          actor=str(actor.id), reason=body.reason)
    db.commit()
    db.refresh(order)
    return sales_service.order_dict(db, order)


@router.post("/orders/{order_id}/revert", dependencies=[Depends(require_write_allowed)])
def revert_order(order_id: str, body: ReasonBody, db: Session = Depends(get_db),
                 actor: User = Depends(require_permission("ventas", "submit")),
                 ctx: CompanyContext = Depends(get_company_context)):
    order = _owned(db, SalesOrder, order_id, ctx.company_id, "SALES_ORDER_NOT_FOUND", "Orden no encontrada")
    order = sales_service.revertir_pedido(db, company_id=ctx.company_id, order_id=str(order.id),
                                          actor=str(actor.id), reason=body.reason)
    db.commit()
    db.refresh(order)
    return sales_service.order_dict(db, order)


@router.post("/orders/{order_id}/cancel", dependencies=[Depends(require_write_allowed)])
def cancel_order(order_id: str, body: ReasonBody, db: Session = Depends(get_db),
                 actor: User = Depends(require_permission("ventas", "submit")),
                 ctx: CompanyContext = Depends(get_company_context)):
    order = _owned(db, SalesOrder, order_id, ctx.company_id, "SALES_ORDER_NOT_FOUND", "Orden no encontrada")
    order = sales_service.cancelar_pedido(db, company_id=ctx.company_id, order_id=str(order.id),
                                          actor=str(actor.id), reason=body.reason)
    db.commit()
    db.refresh(order)
    return sales_service.order_dict(db, order)


@router.post("/orders/{order_id}/transition", dependencies=[Depends(require_write_allowed)])
def transition_order(order_id: str, body: TransitionBody, db: Session = Depends(get_db),
                     actor: User = Depends(require_permission("ventas", "approve")), ctx: CompanyContext = Depends(get_company_context)):
    order = _owned(db, SalesOrder, order_id, ctx.company_id, "SALES_ORDER_NOT_FOUND", "Orden no encontrada")
    order = sales_service.transition_order(db, order=order, target=body.target, actor=str(actor.id),
                                           credit_decision=body.credit_decision, approval_ref=body.approval_ref,
                                           reason=body.reason)
    db.commit()
    db.refresh(order)
    return sales_service.order_dict(db, order)


# --------------------------------------------------------------------------- #
# Picking y despacho
# --------------------------------------------------------------------------- #
@router.get("/pick-lists")
def list_pick_lists(order_id: str | None = None, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user), ctx: CompanyContext = Depends(get_company_context)):
    query = select(PickList).where(PickList.company_id == ctx.company_id)
    if order_id:
        query = query.where(PickList.order_id == order_id)
    items = db.execute(query.order_by(PickList.created_at.desc())).scalars().all()
    return {"items": [{"id": p.id, "code": p.code, "order_id": p.order_id,
                        "warehouse_id": p.warehouse_id, "status": p.status} for p in items],
            "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/pick-lists", dependencies=[Depends(require_write_allowed)])
def create_picklist(body: PickListCreate, db: Session = Depends(get_db),
                    actor: User = Depends(require_permission("ventas", "create")), ctx: CompanyContext = Depends(get_company_context)):
    pl = sales_service.create_picklist(db, company_id=ctx.company_id, code=body.code, order_id=body.order_id,
                                       warehouse_id=body.warehouse_id, lines=body.lines, actor=str(actor.id))
    db.commit()
    db.refresh(pl)
    return {"id": pl.id, "code": pl.code, "status": pl.status}


# --------------------------------------------------------------------------- #
# Spec 031 · cola, asignación y ruta de picking
#
# Todo lo de aquí planifica. Nada mueve mercancía: el efecto físico es de la
# Spec 032. Los permisos son los que ya existen —`ventas:view` para leer y
# `ventas:create` para planificar—; no se inventa ninguno.
# --------------------------------------------------------------------------- #
class AllocationBody(BaseModel):
    """**Fija** cuánto se recoge de una ubicación para una línea. No suma: un
    doble envío deja el mismo resultado. Cantidad cero retira la asignación."""
    model_config = ConfigDict(extra="forbid")

    order_line_id: str
    location_id: str
    quantity: Decimal = Field(ge=0)
    state: str | None = None


@router.get("/picking/cola")
def picking_queue(warehouse_id: str | None = None, db: Session = Depends(get_db),
                  user: User = Depends(require_permission("ventas", "view")),
                  ctx: CompanyContext = Depends(get_company_context)):
    """Los pedidos que esperan preparación, en orden de entrada a la cola."""
    ordenes = sales_service.picking_queue(db, company_id=ctx.company_id, warehouse_id=warehouse_id)
    items = [{"position": i, "order_id": str(o.id), "code": o.code, "customer_id": o.customer_id,
              "warehouse_id": str(o.warehouse_id),
              "released_at": o.released_at.isoformat() if o.released_at else None}
             for i, o in enumerate(ordenes, start=1)]
    return {"items": items, "total": len(items), "page": 1, "page_size": len(items) or 1,
            "order_by": "released_at ASC, id ASC"}


@router.get("/picking/{plan_id}")
def get_picking_plan(plan_id: str, db: Session = Depends(get_db),
                     user: User = Depends(require_permission("ventas", "view")),
                     ctx: CompanyContext = Depends(get_company_context)):
    plan = sales_service.get_plan(db, company_id=ctx.company_id, plan_id=plan_id)
    return sales_service.plan_dict(db, plan)


@router.get("/picking/{plan_id}/candidatas")
def picking_candidates(plan_id: str, order_line_id: str, db: Session = Depends(get_db),
                       user: User = Depends(require_permission("ventas", "view")),
                       ctx: CompanyContext = Depends(get_company_context)):
    """Ubicaciones de las que se puede recoger esa línea, en orden de recorrido."""
    items = sales_service.picking_candidates(db, company_id=ctx.company_id, plan_id=plan_id,
                                             order_line_id=order_line_id)
    return {"items": items, "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/picking/{plan_id}/asignaciones", dependencies=[Depends(require_write_allowed)])
def allocate_picking(plan_id: str, body: AllocationBody, db: Session = Depends(get_db),
                     actor: User = Depends(require_permission("ventas", "create")),
                     ctx: CompanyContext = Depends(get_company_context)):
    plan = sales_service.allocate(db, company_id=ctx.company_id, plan_id=plan_id,
                                  order_line_id=body.order_line_id, location_id=body.location_id,
                                  quantity=body.quantity, state=body.state, actor=str(actor.id))
    db.commit()
    db.refresh(plan)
    return sales_service.plan_dict(db, plan)


@router.post("/picking/{plan_id}/confirmar", dependencies=[Depends(require_write_allowed)])
def confirm_picking(plan_id: str, db: Session = Depends(get_db),
                    actor: User = Depends(require_permission("ventas", "create")),
                    ctx: CompanyContext = Depends(get_company_context)):
    plan = sales_service.confirm_plan(db, company_id=ctx.company_id, plan_id=plan_id,
                                      actor=str(actor.id))
    db.commit()
    db.refresh(plan)
    return sales_service.plan_dict(db, plan)


@router.post("/picking/{plan_id}/cancelar", dependencies=[Depends(require_write_allowed)])
def cancel_picking(plan_id: str, body: ReasonBody, db: Session = Depends(get_db),
                   actor: User = Depends(require_permission("ventas", "create")),
                   ctx: CompanyContext = Depends(get_company_context)):
    plan = sales_service.cancel_plan(db, company_id=ctx.company_id, plan_id=plan_id,
                                     reason=body.reason, actor=str(actor.id))
    db.commit()
    db.refresh(plan)
    return sales_service.plan_dict(db, plan)


@router.post("/picking/{plan_id}/invalidar", dependencies=[Depends(require_write_allowed)])
def invalidate_picking(plan_id: str, body: ReasonBody, db: Session = Depends(get_db),
                       actor: User = Depends(require_permission("ventas", "create")),
                       ctx: CompanyContext = Depends(get_company_context)):
    plan = sales_service.invalidate_plan(db, company_id=ctx.company_id, plan_id=plan_id,
                                         reason=body.reason, actor=str(actor.id))
    db.commit()
    db.refresh(plan)
    return sales_service.plan_dict(db, plan)


@router.post("/shipments", dependencies=[Depends(require_write_allowed)])
def create_shipment(body: ShipmentCreate, db: Session = Depends(get_db),
                    actor: User = Depends(require_permission("ventas", "create")), ctx: CompanyContext = Depends(get_company_context)):
    shipment = sales_service.create_shipment(db, company_id=ctx.company_id, code=body.code, order_id=body.order_id,
                                             origin_warehouse_id=body.origin_warehouse_id, destination=body.destination,
                                             transport=body.transport, lines=body.lines, actor=str(actor.id))
    db.commit()
    db.refresh(shipment)
    return {"id": shipment.id, "code": shipment.code, "status": shipment.status, "validation_status": shipment.validation_status}


@router.post("/shipments/{shipment_id}/validate", dependencies=[Depends(require_write_allowed)])
def validate_shipment(shipment_id: str, db: Session = Depends(get_db),
                      actor: User = Depends(require_permission("ventas", "quality")), ctx: CompanyContext = Depends(get_company_context)):
    shipment = _owned(db, Shipment, shipment_id, ctx.company_id, "SHIPMENT_NOT_FOUND", "Despacho no encontrado")
    sales_service.validate_shipment(db, shipment=shipment, actor=str(actor.id))
    db.commit()
    db.refresh(shipment)
    return {"id": shipment.id, "status": shipment.status, "validation_status": shipment.validation_status}


@router.post("/shipments/{shipment_id}/confirm", dependencies=[Depends(require_write_allowed)])
def confirm_shipment(shipment_id: str, db: Session = Depends(get_db),
                     actor: User = Depends(require_permission("ventas", "quality")), ctx: CompanyContext = Depends(get_company_context)):
    shipment = _owned(db, Shipment, shipment_id, ctx.company_id, "SHIPMENT_NOT_FOUND", "Despacho no encontrado")
    sales_service.confirm_shipment(db, shipment=shipment, actor=str(actor.id))
    db.commit()
    db.refresh(shipment)
    return {"id": shipment.id, "status": shipment.status}


@router.get("/shipments")
def list_shipments(status: str | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user), ctx: CompanyContext = Depends(get_company_context)):
    """Lista despachos (consumido por 008-regulacion-traslados)."""
    query = select(Shipment).where(Shipment.company_id == ctx.company_id)
    if status:
        query = query.where(Shipment.status == status)
    items = db.execute(query.order_by(Shipment.created_at.desc())).scalars().all()
    return {"items": [{"id": s.id, "code": s.code, "order_id": s.order_id,
                       "origin_warehouse_id": s.origin_warehouse_id, "status": s.status,
                       "validation_status": s.validation_status} for s in items],
            "total": len(items), "page": 1, "page_size": len(items) or 1}


# --------------------------------------------------------------------------- #
# Factura de venta y notas
# --------------------------------------------------------------------------- #
@router.get("/invoices")
def list_invoices(status: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                  db: Session = Depends(get_db), user: User = Depends(get_current_user), ctx: CompanyContext = Depends(get_company_context)):
    query = select(SalesInvoice).where(SalesInvoice.company_id == ctx.company_id)
    if status:
        query = query.where(SalesInvoice.status == status)
    total = db.execute(select(func.count()).select_from(query.subquery())).scalar() or 0
    items = db.execute(query.order_by(SalesInvoice.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return {"items": [sales_service.invoice_dict(i) for i in items], "total": total, "page": page, "page_size": page_size}


@router.post("/invoices", dependencies=[Depends(require_write_allowed)])
def create_invoice(body: InvoiceCreate, db: Session = Depends(get_db),
                   actor: User = Depends(require_permission("ventas", "create")), ctx: CompanyContext = Depends(get_company_context)):
    invoice = sales_service.create_invoice(db, company_id=ctx.company_id, customer_id=body.customer_id,
                                           base_fiscal_currency=body.base_fiscal_currency, actor=str(actor.id),
                                           idempotency_key=body.idempotency_key)
    db.commit()
    db.refresh(invoice)
    return sales_service.invoice_dict(invoice)


@router.post("/invoices/{invoice_id}/lines", dependencies=[Depends(require_write_allowed)])
def add_invoice_line(invoice_id: str, body: InvoiceLineCreate, db: Session = Depends(get_db),
                     actor: User = Depends(require_permission("ventas", "create")), ctx: CompanyContext = Depends(get_company_context)):
    invoice = _owned(db, SalesInvoice, invoice_id, ctx.company_id, "INVOICE_NOT_FOUND", "Factura no encontrada")
    line = sales_service.add_invoice_line(db, invoice_id=str(invoice.id), product_id=body.product_id,
                                          quantity=body.quantity, unit_price=body.unit_price,
                                          tax_amount=body.tax_amount, snapshot=body.snapshot)
    sales_service.recompute_invoice_total(db, invoice=invoice)
    db.commit()
    db.refresh(line)
    return {"id": line.id, "product_id": line.product_id, "total": line.total}


@router.post("/invoices/{invoice_id}/transition", dependencies=[Depends(require_write_allowed)])
def transition_invoice(invoice_id: str, body: TransitionBody, db: Session = Depends(get_db),
                       actor: User = Depends(require_permission("ventas", "approve")), ctx: CompanyContext = Depends(get_company_context)):
    invoice = _owned(db, SalesInvoice, invoice_id, ctx.company_id, "INVOICE_NOT_FOUND", "Factura no encontrada")
    if body.target == "VOIDED":
        sales_service.void_invoice(db, invoice=invoice, actor=str(actor.id))
    else:
        sales_service.transition_invoice(db, invoice=invoice, target=body.target, actor=str(actor.id))
    db.commit()
    db.refresh(invoice)
    return sales_service.invoice_dict(invoice)


@router.get("/credit-notes")
def list_credit_notes(db: Session = Depends(get_db), user: User = Depends(get_current_user), ctx: CompanyContext = Depends(get_company_context)):
    items = db.execute(select(SalesCreditNote).where(SalesCreditNote.company_id == ctx.company_id)
                       .order_by(SalesCreditNote.created_at.desc())).scalars().all()
    return {"items": [{"id": n.id, "number": n.number, "party_id": n.customer_id,
                        "invoice_ref": n.invoice_ref, "amount": float(n.amount), "applied": float(n.applied),
                        "currency": n.currency, "status": n.status} for n in items],
            "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/credit-notes", dependencies=[Depends(require_write_allowed)])
def create_credit_note(body: CreditNoteCreate, db: Session = Depends(get_db),
                       actor: User = Depends(require_permission("ventas", "create")), ctx: CompanyContext = Depends(get_company_context)):
    note = sales_service.create_credit_note(db, company_id=ctx.company_id, customer_id=body.customer_id,
                                            number=body.number, amount=body.amount, invoice_ref=body.invoice_ref,
                                            currency=body.currency, actor=str(actor.id))
    db.commit()
    db.refresh(note)
    return {"id": note.id, "number": note.number, "amount": note.amount, "status": note.status}


@router.post("/credit-notes/{note_id}/post", dependencies=[Depends(require_write_allowed)])
def post_credit_note(note_id: str, db: Session = Depends(get_db),
                     actor: User = Depends(require_permission("ventas", "approve")), ctx: CompanyContext = Depends(get_company_context)):
    note = _owned(db, SalesCreditNote, note_id, ctx.company_id, "CREDIT_NOTE_NOT_FOUND", "Nota no encontrada")
    sales_service.post_credit_note(db, note=note)
    db.commit()
    db.refresh(note)
    return {"id": note.id, "status": note.status}


@router.post("/credit-notes/{note_id}/apply", dependencies=[Depends(require_write_allowed)])
def apply_credit_note(note_id: str, body: ApplicationCreate, db: Session = Depends(get_db),
                      actor: User = Depends(require_permission("ventas", "apply")), ctx: CompanyContext = Depends(get_company_context)):
    note = _owned(db, SalesCreditNote, note_id, ctx.company_id, "CREDIT_NOTE_NOT_FOUND", "Nota no encontrada")
    target = sales_service.apply_credit_note(db, note=note, target_open_item_id=body.target_open_item_id,
                                             amount=body.amount, actor=str(actor.id))
    db.commit()
    db.refresh(target)
    return {"target_open_item_id": str(target.id), "balance": ap_service.open_item_balance(target)}


@router.get("/debit-notes")
def list_debit_notes(db: Session = Depends(get_db), user: User = Depends(get_current_user), ctx: CompanyContext = Depends(get_company_context)):
    items = db.execute(select(SalesDebitNote).where(SalesDebitNote.company_id == ctx.company_id)
                       .order_by(SalesDebitNote.created_at.desc())).scalars().all()
    return {"items": [{"id": n.id, "number": n.number, "customer_id": n.customer_id,
                        "invoice_ref": n.invoice_ref, "amount": float(n.amount),
                        "currency": n.currency, "status": n.status} for n in items],
            "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/debit-notes", dependencies=[Depends(require_write_allowed)])
def create_debit_note(body: DebitNoteCreate, db: Session = Depends(get_db),
                      actor: User = Depends(require_permission("ventas", "create")), ctx: CompanyContext = Depends(get_company_context)):
    note = sales_service.create_debit_note(db, company_id=ctx.company_id, customer_id=body.customer_id,
                                           number=body.number, amount=body.amount, invoice_ref=body.invoice_ref,
                                           currency=body.currency, actor=str(actor.id))
    db.commit()
    db.refresh(note)
    return {"id": note.id, "number": note.number, "amount": note.amount, "status": note.status}


@router.get("/returns")
def list_returns(db: Session = Depends(get_db), user: User = Depends(get_current_user), ctx: CompanyContext = Depends(get_company_context)):
    items = db.execute(select(SalesReturn).where(SalesReturn.company_id == ctx.company_id)
                       .order_by(SalesReturn.created_at.desc())).scalars().all()
    return {"items": [{"id": r.id, "code": r.code, "source_document": r.source_document,
                        "reason": r.reason, "condition": r.condition,
                        "inventory_destination": r.inventory_destination, "status": r.status} for r in items],
            "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/returns", dependencies=[Depends(require_write_allowed)])
def create_return(body: ReturnCreate, db: Session = Depends(get_db),
                  actor: User = Depends(require_permission("ventas", "create")), ctx: CompanyContext = Depends(get_company_context)):
    ret = sales_service.create_return(db, company_id=ctx.company_id, code=body.code, source_document=body.source_document,
                                      reason=body.reason, condition=body.condition,
                                      inventory_destination=body.inventory_destination, actor=str(actor.id))
    db.commit()
    db.refresh(ret)
    return {"id": ret.id, "code": ret.code, "status": ret.status}


@router.post("/returns/{return_id}/lines", dependencies=[Depends(require_write_allowed)])
def add_return_line(return_id: str, body: ReturnLineCreate, db: Session = Depends(get_db),
                    actor: User = Depends(require_permission("ventas", "create")),
                    ctx: CompanyContext = Depends(get_company_context)):
    line = sales_service.add_return_line(db, company_id=ctx.company_id, return_id=return_id, product_id=body.product_id,
                                         quantity=body.quantity, condition=body.condition)
    db.commit()
    db.refresh(line)
    return {"id": line.id, "product_id": line.product_id, "quantity": line.quantity}


# --------------------------------------------------------------------------- #
# CxC (reutiliza el motor de 004)
# --------------------------------------------------------------------------- #
@router.get("/open-items")
def list_open_items(party_id: str | None = None, status: str | None = None,
                    db: Session = Depends(get_db), user: User = Depends(get_current_user), ctx: CompanyContext = Depends(get_company_context)):
    query = select(OpenItem).where(OpenItem.company_id == ctx.company_id, OpenItem.item_type == "RECEIVABLE")
    if party_id:
        query = query.where(OpenItem.party_id == party_id)
    if status:
        query = query.where(OpenItem.status == status)
    items = db.execute(query.order_by(OpenItem.due_date.asc().nulls_last())).scalars().all()
    return {"items": [sales_service.open_item_dict(i) for i in items], "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.get("/collections")
def list_collections(status: str | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user), ctx: CompanyContext = Depends(get_company_context)):
    query = select(Payment).where(Payment.company_id == ctx.company_id, Payment.direction == "IN")
    if status:
        query = query.where(Payment.status == status)
    items = db.execute(query.order_by(Payment.created_at.desc())).scalars().all()
    return {"items": [sales_service.collection_dict(p) for p in items], "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/collections", dependencies=[Depends(require_write_allowed)])
def create_collection(body: CollectionCreate, db: Session = Depends(get_db),
                      actor: User = Depends(require_permission("ventas", "create")), ctx: CompanyContext = Depends(get_company_context)):
    payment = ap_service.register_payment(db, company_id=ctx.company_id, party_id=body.party_id, amount=body.amount,
                                          currency=body.currency, instruments=body.instruments, actor=str(actor.id),
                                          idempotency_key=body.idempotency_key, direction="IN")
    db.commit()
    db.refresh(payment)
    return sales_service.collection_dict(payment)


@router.post("/collections/{collection_id}/transition", dependencies=[Depends(require_write_allowed)])
def transition_collection(collection_id: str, body: TransitionBody, db: Session = Depends(get_db),
                          actor: User = Depends(require_permission("ventas", "approve")), ctx: CompanyContext = Depends(get_company_context)):
    payment = _owned(db, Payment, collection_id, ctx.company_id, "COLLECTION_NOT_FOUND", "Cobro no encontrado")
    ap_service.transition_payment(db, payment=payment, target=body.target, actor=str(actor.id))
    db.commit()
    db.refresh(payment)
    return sales_service.collection_dict(payment)


@router.post("/applications", dependencies=[Depends(require_write_allowed)])
def create_application(body: ApplicationCreate, db: Session = Depends(get_db),
                       actor: User = Depends(require_permission("ventas", "apply")), ctx: CompanyContext = Depends(get_company_context)):
    app = sales_service.apply_to_cxc(db, company_id=ctx.company_id, source_type=body.source_type, source_id=body.source_id,
                                     target_open_item_id=body.target_open_item_id, amount=body.amount,
                                     currency=body.currency, rate=body.rate, actor=str(actor.id))
    db.commit()
    db.refresh(app)
    return {"id": app.id, "source_type": app.source_type, "source_id": app.source_id,
            "target_open_item_id": app.target_open_item_id, "amount": app.amount, "status": app.status}


@router.post("/customer-advances", dependencies=[Depends(require_write_allowed)])
def create_customer_advance(body: AdvanceCreate, db: Session = Depends(get_db),
                            actor: User = Depends(require_permission("ventas", "create")), ctx: CompanyContext = Depends(get_company_context)):
    adv = ap_service.register_advance(db, company_id=ctx.company_id, party_id=body.party_id, amount=body.amount,
                                      currency=body.currency, actor=str(actor.id), direction="IN")
    db.commit()
    db.refresh(adv)
    return {"id": adv.id, "party_id": adv.party_id, "amount": adv.amount, "available": adv.available, "status": adv.status}


@router.post("/withholdings-suffered", dependencies=[Depends(require_write_allowed)])
def create_withholding_suffered(body: WithholdingCreate, db: Session = Depends(get_db),
                                actor: User = Depends(require_permission("ventas", "create")), ctx: CompanyContext = Depends(get_company_context)):
    w = ap_service.create_withholding(db, company_id=ctx.company_id, party_id=body.party_id, tax_type=body.tax_type,
                                      rule_ref=body.rule_ref, base=body.base, rate_ref=body.rate_ref,
                                      amount=body.amount, period=body.period, source_event=body.source_event,
                                      actor=str(actor.id))
    db.commit()
    db.refresh(w)
    return {"id": w.id, "party_id": w.party_id, "tax_type": w.tax_type, "amount": w.amount, "status": w.status}


@router.post("/withholdings-suffered/{withholding_id}/transition", dependencies=[Depends(require_write_allowed)])
def transition_withholding(withholding_id: str, body: TransitionBody, db: Session = Depends(get_db),
                           actor: User = Depends(require_permission("ventas", "approve")), ctx: CompanyContext = Depends(get_company_context)):
    w = _owned(db, Withholding, withholding_id, ctx.company_id, "WITHHOLDING_NOT_FOUND", "Retención no encontrada")
    ap_service.transition_withholding(db, withholding=w, target=body.target)
    db.commit()
    db.refresh(w)
    return {"id": w.id, "status": w.status}


@router.get("/aging")
def get_aging(party_id: str | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user), ctx: CompanyContext = Depends(get_company_context)):
    return ap_service.aging(db, company_id=ctx.company_id, party_id=party_id, item_type="RECEIVABLE")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _owned(db: Session, model, obj_id: str, tenant: str, code: str, message: str):
    obj = db.get(model, obj_id)
    if not obj or getattr(obj, "company_id", tenant) != tenant:
        raise NotFoundError(code=code, message=message)
    return obj
