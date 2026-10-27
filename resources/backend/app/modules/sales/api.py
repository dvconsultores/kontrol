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
from app.core.dependencies import require_permission, require_write_allowed
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
    #: Opcional desde la Spec 035: por defecto, el almacén del pedido, que es
    #: donde la preparación dejó la mercancía consolidada.
    origin_warehouse_id: str | None = None
    destination: str | None = None
    transport: str | None = None
    vehicle_id: str | None = None
    driver_id: str | None = None
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
def list_quotes(customer_id: str | None = None, db: Session = Depends(get_db), user: User = Depends(require_permission("ventas", "view")), ctx: CompanyContext = Depends(get_company_context)):
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
              user: User = Depends(require_permission("ventas", "view")),
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
                db: Session = Depends(get_db), user: User = Depends(require_permission("ventas", "view")), ctx: CompanyContext = Depends(get_company_context)):
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
def get_order(order_id: str, db: Session = Depends(get_db), user: User = Depends(require_permission("ventas", "view")), ctx: CompanyContext = Depends(get_company_context)):
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
def get_reservation_policy(db: Session = Depends(get_db), user: User = Depends(require_permission("ventas", "view")),
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
def list_pick_lists(order_id: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                    db: Session = Depends(get_db),
                    user: User = Depends(require_permission("ventas", "view")), ctx: CompanyContext = Depends(get_company_context)):
    """Listas de preparación de la empresa, con el sobre de listados del contrato (`{items, total, page, page_size}`).

    Devolvía la colección entera con un sobre que solo lo parecía (`page` 1, `page_size` = cuántas había). Ahora
    `total` cuenta dentro de la empresa y del filtro **antes** de cortar la página, y el orden es determinista: la
    más reciente primero y, a igual instante, `id` como desempate (el precedente del listado de empresas).
    """
    query = select(PickList).where(PickList.company_id == ctx.company_id)
    if order_id:
        query = query.where(PickList.order_id == order_id)
    total = int(db.execute(select(func.count()).select_from(query.subquery())).scalar_one())
    items = db.execute(query.order_by(PickList.created_at.desc(), PickList.id)
                       .offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return {"items": [{"id": p.id, "code": p.code, "order_id": p.order_id,
                        "warehouse_id": p.warehouse_id, "status": p.status} for p in items],
            "total": total, "page": page, "page_size": page_size}


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


# --------------------------------------------------------------------------- #
# Spec 032 · ejecución física del picking y consolidación
#
# Aquí sí se mueve mercancía: se extrae de su ubicación y se lleva al Área de
# Confirmación. Lo que no se hace es verificar de nuevo ni aprobar: eso es de la
# Spec 033, y la frontera entre las dos la marca esta cabecera.
# --------------------------------------------------------------------------- #
class PickBody(BaseModel):
    """Lo recogido en una parada. Menos de lo planificado exige motivo, y el
    motivo es uno de los cinco que enumera el proceso fuente."""
    model_config = ConfigDict(extra="forbid")

    line_id: str
    quantity: Decimal = Field(ge=0)
    discrepancy_kind: str | None = None
    discrepancy_note: str | None = Field(default=None, max_length=500)


class ConsolidationBody(BaseModel):
    """El Área de Confirmación es una ubicación del almacén."""
    model_config = ConfigDict(extra="forbid")

    location_id: str


@router.get("/picking/{plan_id}/preparacion")
def picking_preparation(plan_id: str, db: Session = Depends(get_db),
                        user: User = Depends(require_permission("ventas", "view")),
                        ctx: CompanyContext = Depends(get_company_context)):
    """Lo planificado, lo recogido y la diferencia. Es lo que consume la 033."""
    plan = sales_service.get_plan(db, company_id=ctx.company_id, plan_id=plan_id)
    return sales_service.preparation_dict(db, plan)


@router.post("/picking/{plan_id}/recoger", dependencies=[Depends(require_write_allowed)])
def execute_pick(plan_id: str, body: PickBody, db: Session = Depends(get_db),
                 actor: User = Depends(require_permission("ventas", "create")),
                 ctx: CompanyContext = Depends(get_company_context)):
    plan = sales_service.execute_pick(
        db, company_id=ctx.company_id, plan_id=plan_id, line_id=body.line_id,
        quantity=body.quantity, discrepancy_kind=body.discrepancy_kind,
        discrepancy_note=body.discrepancy_note, actor=str(actor.id))
    db.commit()
    db.refresh(plan)
    return sales_service.preparation_dict(db, plan)


@router.post("/picking/{plan_id}/consolidar", dependencies=[Depends(require_write_allowed)])
def consolidate_picking(plan_id: str, body: ConsolidationBody, db: Session = Depends(get_db),
                        actor: User = Depends(require_permission("ventas", "create")),
                        ctx: CompanyContext = Depends(get_company_context)):
    plan = sales_service.consolidate(db, company_id=ctx.company_id, plan_id=plan_id,
                                     location_id=body.location_id, actor=str(actor.id))
    db.commit()
    db.refresh(plan)
    return sales_service.preparation_dict(db, plan)


# --------------------------------------------------------------------------- #
# Spec 033 · confirmación independiente del pedido
#
# El resultado **no lo envía el cliente**: el verificador manda lo que contó y el
# backend dictamina. Un control cuyo veredicto llega desde el navegador no es un
# control.
# --------------------------------------------------------------------------- #
class ConfirmationLineBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_line_id: str
    checked_base_quantity: Decimal = Field(ge=0)
    presentation_ok: bool = True
    condition_ok: bool = True
    product_id: str | None = None
    note: str | None = Field(default=None, max_length=500)


class ConfirmationBody(BaseModel):
    """El control es completo o no es control (`R-D0-12-3`): se envían todas las
    líneas de inventario del pedido, no las que se quiera."""
    model_config = ConfigDict(extra="forbid")

    lines: list[ConfirmationLineBody]
    notes: str | None = Field(default=None, max_length=1000)


@router.get("/confirmacion/pendientes")
def pending_confirmations(db: Session = Depends(get_db),
                          user: User = Depends(require_permission("ventas", "quality")),
                          ctx: CompanyContext = Depends(get_company_context)):
    """Pedidos preparados que esperan el control independiente."""
    ordenes = sales_service.pending_confirmations(db, company_id=ctx.company_id)
    items = [{"order_id": str(o.id), "code": o.code, "customer_id": o.customer_id,
              "warehouse_id": str(o.warehouse_id), "status": o.status,
              "updated_at": o.updated_at.isoformat() if o.updated_at else None}
             for o in ordenes]
    return {"items": items, "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.get("/confirmacion/{order_id}")
def confirmation_worksheet(order_id: str, db: Session = Depends(get_db),
                           user: User = Depends(require_permission("ventas", "quality")),
                           ctx: CompanyContext = Depends(get_company_context)):
    """El pedido original y lo preparado, para verificar producto por producto."""
    return sales_service.confirmation_worksheet(db, company_id=ctx.company_id, order_id=order_id)


@router.post("/confirmacion/{order_id}", dependencies=[Depends(require_write_allowed)])
def confirm_order(order_id: str, body: ConfirmationBody, db: Session = Depends(get_db),
                  actor: User = Depends(require_permission("ventas", "quality")),
                  ctx: CompanyContext = Depends(get_company_context)):
    confirmacion = sales_service.confirm_order(
        db, company_id=ctx.company_id, order_id=order_id,
        lines=[ln.model_dump() for ln in body.lines], notes=body.notes, actor=str(actor.id))
    db.commit()
    db.refresh(confirmacion)
    return sales_service.confirmation_dict(db, confirmacion)


@router.get("/confirmacion/{order_id}/facturable")
def billing_eligibility(order_id: str, db: Session = Depends(get_db),
                        user: User = Depends(require_permission("ventas", "view")),
                        ctx: CompanyContext = Depends(get_company_context)):
    """La autoridad única sobre si un pedido puede facturarse (¶83, ¶89)."""
    return sales_service.billing_eligibility(db, company_id=ctx.company_id, order_id=order_id)


# --------------------------------------------------------------------------- #
# Spec 034 · liberación y facturación
#
# «Facturación factura sobre un pedido previamente confirmado» (¶89). La
# compuerta no es una convención: sin confirmación independiente vigente no hay
# solicitud, sin solicitud no hay factura, y sin pedido no hay emisión.
# --------------------------------------------------------------------------- #
class IssueInvoiceBody(BaseModel):
    """La numeración la asigna la Spec 042; aquí solo se dice de qué serie y de
    qué lote de control sale."""
    model_config = ConfigDict(extra="forbid")

    series_id: str
    batch_id: str


@router.get("/facturacion/pendientes")
def billable_orders(db: Session = Depends(get_db),
                    user: User = Depends(require_permission("ventas", "view")),
                    ctx: CompanyContext = Depends(get_company_context)):
    """Pedidos confirmados y pedidos ya liberados a la espera de su factura."""
    ordenes = sales_service.billable_orders(db, company_id=ctx.company_id)
    items = [{"order_id": str(o.id), "code": o.code, "customer_id": o.customer_id,
              "status": o.status, "currency": o.currency,
              "billing_requested_at": (o.billing_requested_at.isoformat()
                                       if o.billing_requested_at else None)}
             for o in ordenes]
    return {"items": items, "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/facturacion/{order_id}/solicitar", dependencies=[Depends(require_write_allowed)])
def request_billing(order_id: str, db: Session = Depends(get_db),
                    actor: User = Depends(require_permission("ventas", "quality")),
                    ctx: CompanyContext = Depends(get_company_context)):
    """La solicitud del ¶84. La firma el Área de Confirmación, que es quien
    autoriza (¶83), y por eso exige su mismo permiso."""
    order = sales_service.request_billing(db, company_id=ctx.company_id, order_id=order_id,
                                          actor=str(actor.id))
    db.commit()
    db.refresh(order)
    return sales_service.order_dict(db, order)


@router.post("/facturacion/{order_id}/generar", dependencies=[Depends(require_write_allowed)])
def generate_invoice(order_id: str, db: Session = Depends(get_db),
                     actor: User = Depends(require_permission("ventas", "create")),
                     ctx: CompanyContext = Depends(get_company_context)):
    """Genera la factura desde las líneas del pedido (¶95-96)."""
    invoice = sales_service.generate_invoice(db, company_id=ctx.company_id, order_id=order_id,
                                             actor=str(actor.id))
    db.commit()
    db.refresh(invoice)
    return sales_service.billing_invoice_dict(db, invoice)


@router.post("/facturacion/{invoice_id}/emitir", dependencies=[Depends(require_write_allowed)])
def issue_invoice(invoice_id: str, body: IssueInvoiceBody, db: Session = Depends(get_db),
                  actor: User = Depends(require_permission("ventas", "approve")),
                  ctx: CompanyContext = Depends(get_company_context)):
    """Emite el documento fiscal (¶97) y deja el pedido facturado (¶99)."""
    invoice = sales_service.issue_invoice(db, company_id=ctx.company_id, invoice_id=invoice_id,
                                          series_id=body.series_id, batch_id=body.batch_id,
                                          actor=str(actor.id))
    db.commit()
    db.refresh(invoice)
    return sales_service.billing_invoice_dict(db, invoice)


@router.get("/facturacion/{order_id}/factura")
def order_invoice(order_id: str, db: Session = Depends(get_db),
                  user: User = Depends(require_permission("ventas", "view")),
                  ctx: CompanyContext = Depends(get_company_context)):
    """La factura de un pedido. Lo que la Spec 035 necesita antes de despachar."""
    return sales_service.order_invoice_dict(db, company_id=ctx.company_id, order_id=order_id)


# --------------------------------------------------------------------------- #
# Spec 035 · despacho, transporte y regulación
#
# La salida física y su compuerta. Empieza aquí y no en la primera ruta de
# despacho: los guardias de la 034 cortan por esta cabecera, y sin ella
# cualquier ruta que se añada delante de `/shipments` se cuenta como facturación.
# --------------------------------------------------------------------------- #
@router.get("/despacho/pendientes")
def dispatch_queue(db: Session = Depends(get_db),
                   user: User = Depends(require_permission("ventas", "view")),
                   ctx: CompanyContext = Depends(get_company_context)):
    """Los pedidos facturados que esperan salida física (¶101)."""
    items = sales_service.dispatch_queue(db, company_id=ctx.company_id)
    return {"items": items, "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.get("/despacho/{order_id}/despacho")
def order_dispatch(order_id: str, db: Session = Depends(get_db),
                   user: User = Depends(require_permission("ventas", "view")),
                   ctx: CompanyContext = Depends(get_company_context)):
    """El despacho vivo de un pedido, si lo tiene."""
    return sales_service.order_dispatch_dict(db, company_id=ctx.company_id, order_id=order_id)


@router.post("/shipments", dependencies=[Depends(require_write_allowed)])
def create_shipment(body: ShipmentCreate, db: Session = Depends(get_db),
                    actor: User = Depends(require_permission("ventas", "create")), ctx: CompanyContext = Depends(get_company_context)):
    shipment = sales_service.create_shipment(db, company_id=ctx.company_id, code=body.code, order_id=body.order_id,
                                             origin_warehouse_id=body.origin_warehouse_id, destination=body.destination,
                                             transport=body.transport, vehicle_id=body.vehicle_id,
                                             driver_id=body.driver_id, lines=body.lines, actor=str(actor.id))
    db.commit()
    db.refresh(shipment)
    return sales_service.shipment_dict(db, shipment)


@router.post("/shipments/{shipment_id}/validate", dependencies=[Depends(require_write_allowed)])
def validate_shipment(shipment_id: str, db: Session = Depends(get_db),
                      actor: User = Depends(require_permission("ventas", "quality")), ctx: CompanyContext = Depends(get_company_context)):
    shipment = _owned(db, Shipment, shipment_id, ctx.company_id, "SHIPMENT_NOT_FOUND", "Despacho no encontrado")
    sales_service.validate_shipment(db, shipment=shipment, actor=str(actor.id))
    db.commit()
    db.refresh(shipment)
    return sales_service.shipment_dict(db, shipment)


@router.post("/shipments/{shipment_id}/confirm", dependencies=[Depends(require_write_allowed)])
def confirm_shipment(shipment_id: str, db: Session = Depends(get_db),
                     actor: User = Depends(require_permission("ventas", "quality")), ctx: CompanyContext = Depends(get_company_context)):
    shipment = _owned(db, Shipment, shipment_id, ctx.company_id, "SHIPMENT_NOT_FOUND", "Despacho no encontrado")
    sales_service.confirm_shipment(db, shipment=shipment, actor=str(actor.id))
    db.commit()
    db.refresh(shipment)
    return sales_service.shipment_dict(db, shipment)


@router.get("/shipments")
def list_shipments(status: str | None = None, db: Session = Depends(get_db), user: User = Depends(require_permission("ventas", "view")), ctx: CompanyContext = Depends(get_company_context)):
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
                  db: Session = Depends(get_db), user: User = Depends(require_permission("ventas", "view")), ctx: CompanyContext = Depends(get_company_context)):
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
def list_credit_notes(db: Session = Depends(get_db), user: User = Depends(require_permission("ventas", "view")), ctx: CompanyContext = Depends(get_company_context)):
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
def list_debit_notes(db: Session = Depends(get_db), user: User = Depends(require_permission("ventas", "view")), ctx: CompanyContext = Depends(get_company_context)):
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
def list_returns(db: Session = Depends(get_db), user: User = Depends(require_permission("ventas", "view")), ctx: CompanyContext = Depends(get_company_context)):
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
# Spec 036 · devoluciones, notas de crédito y notas de débito
#
# El orden de la norma, un endpoint por acto: «Solicitud → Verificación física →
# Aprobación → Entrada de inventario → Nota de crédito vinculada». No se fusionan
# porque no son lo mismo: una solicitud no mueve inventario y recibir la
# mercancía no la hace vendible.
# --------------------------------------------------------------------------- #
class ReturnRequestLine(BaseModel):
    invoice_line_id: str
    base_quantity: float = Field(gt=0)
    quantity: float | None = None
    condition: str = "DEFECTUOSO"
    lot_id: str | None = None
    serial_id: str | None = None


class ReturnRequestBody(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    invoice_id: str
    reason: str = Field(min_length=3, max_length=2000)
    warehouse_id: str | None = None
    lines: list[ReturnRequestLine] = Field(min_length=1)


class ReturnReceiveBody(BaseModel):
    location_id: str


class ReturnInspectLine(BaseModel):
    return_line_id: str
    #: `DISPONIBLE` o `RECHAZADO`. El backend lo comprueba contra `D0-10`: el
    #: cliente no elige el estado de mercancía.
    disposition: str
    accepted_base_quantity: float | None = None
    note: str | None = None


class ReturnInspectBody(BaseModel):
    lines: list[ReturnInspectLine] = Field(min_length=1)


class ReturnDecisionBody(BaseModel):
    approved: bool
    reason: str | None = None


class NoteLineBody(BaseModel):
    invoice_line_id: str
    quantity: float = Field(gt=0)


class CreditNoteBody(BaseModel):
    cause: str = Field(min_length=3, max_length=2000)
    return_id: str | None = None
    lines: list[NoteLineBody] = Field(min_length=1)


class DebitNoteLineBody(BaseModel):
    concept: str = Field(min_length=1, max_length=2000)
    base_fiscal: float = Field(gt=0)
    invoice_line_id: str | None = None


class DebitNoteBody(BaseModel):
    cause: str = Field(min_length=3, max_length=2000)
    lines: list[DebitNoteLineBody] = Field(min_length=1)


class NoteIssueBody(BaseModel):
    series_id: str
    batch_id: str


@router.get("/devoluciones/elegibles/{invoice_id}")
def return_eligibility(invoice_id: str, db: Session = Depends(get_db),
                       user: User = Depends(require_permission("ventas", "view")),
                       ctx: CompanyContext = Depends(get_company_context)):
    """Qué se puede devolver de una factura y cuánto queda. Lo calcula el backend."""
    return sales_service.return_eligibility(db, company_id=ctx.company_id, invoice_id=invoice_id)


@router.get("/devoluciones")
def list_sales_returns(status: str | None = None, db: Session = Depends(get_db),
                       user: User = Depends(require_permission("ventas", "view")),
                       ctx: CompanyContext = Depends(get_company_context)):
    consulta = select(SalesReturn).where(SalesReturn.company_id == ctx.company_id)
    if status:
        consulta = consulta.where(SalesReturn.status == status)
    items = db.execute(consulta.order_by(SalesReturn.created_at.desc())).scalars().all()
    return {"items": [sales_service.return_dict(db, r) for r in items],
            "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.get("/devoluciones/{return_id}")
def get_sales_return(return_id: str, db: Session = Depends(get_db),
                     user: User = Depends(require_permission("ventas", "view")),
                     ctx: CompanyContext = Depends(get_company_context)):
    devolucion = _owned(db, SalesReturn, return_id, ctx.company_id,
                        "SALES_RETURN_NOT_FOUND", "Devolución no encontrada")
    return sales_service.return_dict(db, devolucion)


@router.post("/devoluciones", dependencies=[Depends(require_write_allowed)])
def request_sales_return(body: ReturnRequestBody, db: Session = Depends(get_db),
                         actor: User = Depends(require_permission("ventas", "create")),
                         ctx: CompanyContext = Depends(get_company_context)):
    devolucion = sales_service.request_return(
        db, company_id=ctx.company_id, code=body.code, invoice_id=body.invoice_id,
        reason=body.reason, warehouse_id=body.warehouse_id,
        lines=[x.model_dump() for x in body.lines], actor=str(actor.id))
    db.commit()
    db.refresh(devolucion)
    return sales_service.return_dict(db, devolucion)


@router.post("/devoluciones/{return_id}/recibir", dependencies=[Depends(require_write_allowed)])
def receive_sales_return(return_id: str, body: ReturnReceiveBody, db: Session = Depends(get_db),
                         actor: User = Depends(require_permission("ventas", "create")),
                         ctx: CompanyContext = Depends(get_company_context)):
    """La custodia vuelve a la empresa. **No** la hace vendible."""
    devolucion = sales_service.receive_return(db, company_id=ctx.company_id, return_id=return_id,
                                              location_id=body.location_id, actor=str(actor.id))
    db.commit()
    db.refresh(devolucion)
    return sales_service.return_dict(db, devolucion)


@router.post("/devoluciones/{return_id}/verificar", dependencies=[Depends(require_write_allowed)])
def inspect_sales_return(return_id: str, body: ReturnInspectBody, db: Session = Depends(get_db),
                         actor: User = Depends(require_permission("ventas", "quality")),
                         ctx: CompanyContext = Depends(get_company_context)):
    devolucion = sales_service.inspect_return(db, company_id=ctx.company_id, return_id=return_id,
                                              lines=[x.model_dump() for x in body.lines],
                                              actor=str(actor.id))
    db.commit()
    db.refresh(devolucion)
    return sales_service.return_dict(db, devolucion)


@router.post("/devoluciones/{return_id}/decidir", dependencies=[Depends(require_write_allowed)])
def decide_sales_return(return_id: str, body: ReturnDecisionBody, db: Session = Depends(get_db),
                        actor: User = Depends(require_permission("ventas", "approve")),
                        ctx: CompanyContext = Depends(get_company_context)):
    devolucion = sales_service.decide_return(db, company_id=ctx.company_id, return_id=return_id,
                                             approved=body.approved, reason=body.reason,
                                             actor=str(actor.id))
    db.commit()
    db.refresh(devolucion)
    return sales_service.return_dict(db, devolucion)


@router.post("/devoluciones/{return_id}/reingresar", dependencies=[Depends(require_write_allowed)])
def reenter_sales_return(return_id: str, db: Session = Depends(get_db),
                         actor: User = Depends(require_permission("ventas", "quality")),
                         ctx: CompanyContext = Depends(get_company_context)):
    """«Entrada de inventario»: el cuarto acto, y el único que crea existencia."""
    devolucion = sales_service.reenter_return(db, company_id=ctx.company_id, return_id=return_id,
                                              actor=str(actor.id))
    db.commit()
    db.refresh(devolucion)
    return sales_service.return_dict(db, devolucion)


@router.get("/notas/acreditable/{invoice_id}")
def credit_eligibility(invoice_id: str, db: Session = Depends(get_db),
                       user: User = Depends(require_permission("ventas", "view")),
                       ctx: CompanyContext = Depends(get_company_context)):
    """Cuánto queda por acreditar: «no ajustar por encima de lo pendiente»."""
    return sales_service.credit_eligibility(db, company_id=ctx.company_id, invoice_id=invoice_id)


@router.post("/notas/credito/{invoice_id}/generar", dependencies=[Depends(require_write_allowed)])
def generate_sales_credit_note(invoice_id: str, body: CreditNoteBody, db: Session = Depends(get_db),
                               actor: User = Depends(require_permission("ventas", "create")),
                               ctx: CompanyContext = Depends(get_company_context)):
    nota = sales_service.generate_credit_note(
        db, company_id=ctx.company_id, invoice_id=invoice_id, cause=body.cause,
        return_id=body.return_id, lines=[x.model_dump() for x in body.lines], actor=str(actor.id))
    db.commit()
    db.refresh(nota)
    return sales_service.credit_note_dict(db, nota)


@router.post("/notas/credito/{note_id}/emitir", dependencies=[Depends(require_write_allowed)])
def issue_sales_credit_note(note_id: str, body: NoteIssueBody, db: Session = Depends(get_db),
                            actor: User = Depends(require_permission("ventas", "approve")),
                            ctx: CompanyContext = Depends(get_company_context)):
    """El consecutivo y el número de control los da la 042, no esta pantalla."""
    nota = sales_service.issue_credit_note(db, company_id=ctx.company_id, note_id=note_id,
                                           series_id=body.series_id, batch_id=body.batch_id,
                                           actor=str(actor.id))
    db.commit()
    db.refresh(nota)
    return sales_service.credit_note_dict(db, nota)


@router.get("/notas/credito/{note_id}")
def get_sales_credit_note(note_id: str, db: Session = Depends(get_db),
                          user: User = Depends(require_permission("ventas", "view")),
                          ctx: CompanyContext = Depends(get_company_context)):
    nota = _owned(db, SalesCreditNote, note_id, ctx.company_id,
                  "CREDIT_NOTE_NOT_FOUND", "Nota de crédito no encontrada")
    return sales_service.credit_note_dict(db, nota)


@router.post("/notas/debito/{invoice_id}/generar", dependencies=[Depends(require_write_allowed)])
def generate_sales_debit_note(invoice_id: str, body: DebitNoteBody, db: Session = Depends(get_db),
                              actor: User = Depends(require_permission("ventas", "create")),
                              ctx: CompanyContext = Depends(get_company_context)):
    nota = sales_service.generate_debit_note(
        db, company_id=ctx.company_id, invoice_id=invoice_id, cause=body.cause,
        lines=[x.model_dump() for x in body.lines], actor=str(actor.id))
    db.commit()
    db.refresh(nota)
    return sales_service.debit_note_dict(db, nota)


@router.post("/notas/debito/{note_id}/emitir", dependencies=[Depends(require_write_allowed)])
def issue_sales_debit_note(note_id: str, body: NoteIssueBody, db: Session = Depends(get_db),
                           actor: User = Depends(require_permission("ventas", "approve")),
                           ctx: CompanyContext = Depends(get_company_context)):
    nota = sales_service.issue_debit_note(db, company_id=ctx.company_id, note_id=note_id,
                                          series_id=body.series_id, batch_id=body.batch_id,
                                          actor=str(actor.id))
    db.commit()
    db.refresh(nota)
    return sales_service.debit_note_dict(db, nota)


@router.get("/notas/debito/{note_id}")
def get_sales_debit_note(note_id: str, db: Session = Depends(get_db),
                         user: User = Depends(require_permission("ventas", "view")),
                         ctx: CompanyContext = Depends(get_company_context)):
    nota = _owned(db, SalesDebitNote, note_id, ctx.company_id,
                  "DEBIT_NOTE_NOT_FOUND", "Nota de débito no encontrada")
    return sales_service.debit_note_dict(db, nota)


# --------------------------------------------------------------------------- #
# CxC (reutiliza el motor de 004)
# --------------------------------------------------------------------------- #
@router.get("/open-items")
def list_open_items(party_id: str | None = None, status: str | None = None,
                    db: Session = Depends(get_db), user: User = Depends(require_permission("ventas", "view")), ctx: CompanyContext = Depends(get_company_context)):
    query = select(OpenItem).where(OpenItem.company_id == ctx.company_id, OpenItem.item_type == "RECEIVABLE")
    if party_id:
        query = query.where(OpenItem.party_id == party_id)
    if status:
        query = query.where(OpenItem.status == status)
    items = db.execute(query.order_by(OpenItem.due_date.asc().nulls_last())).scalars().all()
    return {"items": [sales_service.open_item_dict(i) for i in items], "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.get("/collections")
def list_collections(status: str | None = None, db: Session = Depends(get_db), user: User = Depends(require_permission("ventas", "view")), ctx: CompanyContext = Depends(get_company_context)):
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


# --------------------------------------------------------------------------- #
# Spec 037 · cuentas por cobrar: saldo, aplicaciones y reversos
#
# «Saldo = documentos + débitos − cobros − retenciones − créditos»
# (arquitectura funcional §9). El saldo lo calcula el backend con el motor
# compartido de la Spec 028: la pantalla no hace aritmética monetaria.
#
# La empresa la manda el contexto y el cliente se comprueba en cada aplicación:
# la misma empresa **no** basta, porque un crédito es de quien lo tiene.
# --------------------------------------------------------------------------- #
class CreditApplicationBody(BaseModel):
    target_open_item_id: str
    amount: Decimal = Field(gt=0)


class ApplicationReversalBody(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)


@router.get("/cxc/clientes/{customer_id}/saldo")
def customer_balance(customer_id: str, db: Session = Depends(get_db),
                     user: User = Depends(require_permission("ventas", "view")),
                     ctx: CompanyContext = Depends(get_company_context)):
    """El saldo del cliente, con sus sumandos a la vista."""
    return sales_service.customer_balance(db, company_id=ctx.company_id, customer_id=customer_id)


@router.get("/cxc/clientes/{customer_id}/estado-de-cuenta")
def customer_statement(customer_id: str, db: Session = Depends(get_db),
                       user: User = Depends(require_permission("ventas", "view")),
                       ctx: CompanyContext = Depends(get_company_context)):
    """La cronología que explica el saldo. Cada línea es un hecho con documento."""
    return sales_service.customer_statement(db, company_id=ctx.company_id, customer_id=customer_id)


@router.get("/cxc/clientes/{customer_id}/creditos")
def customer_credits(customer_id: str, db: Session = Depends(get_db),
                     user: User = Depends(require_permission("ventas", "view")),
                     ctx: CompanyContext = Depends(get_company_context)):
    """Los créditos del cliente que todavía tienen importe sin aplicar."""
    return {"items": sales_service.customer_credits(db, company_id=ctx.company_id,
                                                    customer_id=customer_id)}


@router.get("/cxc/documentos/{open_item_id}/aplicaciones")
def open_item_applications(open_item_id: str, db: Session = Depends(get_db),
                           user: User = Depends(require_permission("ventas", "view")),
                           ctx: CompanyContext = Depends(get_company_context)):
    """Lo que se ha aplicado a un documento, con sus reversos."""
    return {"items": sales_service.open_item_applications(db, company_id=ctx.company_id,
                                                          open_item_id=open_item_id)}


@router.post("/cxc/creditos/{note_id}/aplicar", dependencies=[Depends(require_write_allowed)])
def apply_customer_credit(note_id: str, body: CreditApplicationBody, db: Session = Depends(get_db),
                          actor: User = Depends(require_permission("ventas", "apply")),
                          ctx: CompanyContext = Depends(get_company_context)):
    """Aplica el crédito de una nota a un documento **del mismo cliente**."""
    note = _owned(db, SalesCreditNote, note_id, ctx.company_id,
                  "CREDIT_NOTE_NOT_FOUND", "Nota de crédito no encontrada")
    target = sales_service.apply_credit_note(db, note=note,
                                             target_open_item_id=body.target_open_item_id,
                                             amount=body.amount, actor=str(actor.id))
    db.commit()
    db.refresh(target)
    db.refresh(note)
    return {"target_open_item_id": str(target.id),
            "target_outstanding": str(ap_service.open_item_balance(target)),
            "target_status": target.status,
            "credit_remaining": str(sales_service._dec(note.amount) - sales_service._dec(note.applied)),
            "currency": note.currency}


@router.post("/cxc/aplicaciones/{application_id}/revertir",
             dependencies=[Depends(require_write_allowed)])
def reverse_application(application_id: str, body: ApplicationReversalBody,
                        db: Session = Depends(get_db),
                        actor: User = Depends(require_permission("ventas", "approve")),
                        ctx: CompanyContext = Depends(get_company_context)):
    """Revierte una aplicación **sin borrarla**: crea su evento inverso."""
    inverso = sales_service.reverse_credit_application(
        db, company_id=ctx.company_id, application_id=application_id,
        reason=body.reason, actor=str(actor.id))
    db.commit()
    db.refresh(inverso)
    return {"reversal_id": str(inverso.id), "original_id": application_id,
            "amount": str(inverso.amount), "currency": inverso.currency,
            "status": inverso.status}


@router.get("/aging")
def get_aging(party_id: str | None = None, db: Session = Depends(get_db), user: User = Depends(require_permission("ventas", "view")), ctx: CompanyContext = Depends(get_company_context)):
    return ap_service.aging(db, company_id=ctx.company_id, party_id=party_id, item_type="RECEIVABLE")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _owned(db: Session, model, obj_id: str, tenant: str, code: str, message: str):
    obj = db.get(model, obj_id)
    if not obj or getattr(obj, "company_id", tenant) != tenant:
        raise NotFoundError(code=code, message=message)
    return obj
