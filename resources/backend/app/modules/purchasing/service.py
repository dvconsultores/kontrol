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

from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.core.integrity import es_violacion_unica
from app.modules.approvals import integration as approvals_integration
from app.modules.inventory import service as inv_service
from app.modules.inventory import states as inv_states
from app.modules.master_data import uom as uom_engine
from app.modules.master_data.models import Party
from app.modules.organization.models import Company, Warehouse
from app.modules.organization.service import warehouse_belongs_to
from app.modules.purchasing.models import (
    CONFIRMATION_TARGET_STATES,
    COUNT_DIFFERENCE_KINDS,
    INCIDENT_RESOLUTION_APPROVED,
    INCIDENT_RESOLUTIONS,
    INCIDENT_TYPE_DOCUMENTAL,
    INCIDENT_TYPES,
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
    ReceiptConfirmation,
    ReceiptIncident,
    RequisitionLine,
    SupplierCreditNote,
    SupplierInvoice,
    SupplierInvoiceLine,
    SupplierQuote,
    TripleMatch,
    Withholding,
)
from app.shared import audit as audit_service
from app.shared.clock import hoy_de_negocio


def _dec(value: Any, places: int = 6) -> Decimal:
    """Coerción a `Decimal` en la frontera del servicio (Spec 011).

    Las cantidades son `NUMERIC` desde 011; mezclarlas con `float` en
    aritmética reintroduciría el defecto `KQA-100`.
    """
    if value is None:
        return Decimal(0)
    if isinstance(value, Decimal):
        return value.quantize(Decimal(1).scaleb(-places))
    return Decimal(str(value)).quantize(Decimal(1).scaleb(-places))


#: La escala de las columnas monetarias del módulo, que es `NUMERIC(18, 2)`.
#: Su autoridad es el maestro de monedas —`Currency.decimal_places`, por defecto
#: 2—: si alguna vez hiciera falta otra escala, lo que cambiaría es la columna.
_MONEY_PLACES = 2


def _money(value: Any) -> Decimal:
    """Dinero como `Decimal` exacto, **sin pasar por `float`**.

    `ADR-D0-001` registra `KQA-100` como defecto CRÍTICO: «`Decimal + float`…
    que SQLite no reveló y que rompió factura, pago, cobro». La Spec 011 lo
    corrigió en las cantidades y dejó el patrón con nombre; el motor de saldos
    nunca lo recibió y seguía calculando el dinero en coma flotante.

    No se decide aquí ninguna política de redondeo, y no hace falta: los dos
    operandos vienen de columnas de escala 2, su resta es exacta y la
    cuantización solo existe para que Python y PostgreSQL digan el mismo número.
    """
    if value is None:
        return Decimal(0)
    entrada = value if isinstance(value, Decimal) else Decimal(str(value))
    return entrada.quantize(Decimal(1).scaleb(-_MONEY_PLACES))


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

#: una orden recibida aún admite recepción porque un sobrante se registra, no se impide (FR-019-012)
RECEIVABLE_ORDER_STATUSES = ("APPROVED", "PARTIALLY_RECEIVED", "RECEIVED")
#: como en las ubicaciones, lo que no está activo no recibe mercancía nueva
RECEIPT_WAREHOUSE_ALLOWED_STATUSES = ("ACTIVE",)

RECEIPT_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"CONFIRMED", "CANCELLED"},
    "CONFIRMED": {"QUALITY_PENDING"},
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
def _require_party(db: Session, company_id: str, party_id: str, *, role: str, require_active: bool) -> None:
    from app.modules.master_data import service as master_service

    master_service.require_eligible_party(db, company_id=company_id, party_id=party_id, role=role, require_active=require_active)


def _require_supplier_approved(db: Session, party_id: str, direction: str) -> None:
    if direction != "OUT":
        return
    from app.modules.master_data import service as master_service

    master_service.require_supplier_approved(db, party_id=party_id)


def _role_for_direction(direction: str) -> str:
    """OUT liquida con un proveedor (CxP); IN con un cliente (CxC)."""
    if direction == "OUT":
        return "PROVEEDOR"
    if direction == "IN":
        return "CLIENTE"
    raise KontrolError(code="INVALID_DIRECTION", message="La dirección debe ser IN u OUT", status_code=422)


def _require_product(db: Session, company_id: str, product_id: str) -> None:
    from app.modules.master_data.models import CatalogItem

    item = db.get(CatalogItem, product_id)
    if not item or item.company_id != company_id:
        raise NotFoundError(code="PRODUCT_NOT_FOUND", message="Producto no encontrado")


def compare_quotes(db: Session, *, company_id: str, product_id: str) -> dict:
    """Compara cotizaciones activas/adjudicadas/convertidas de un producto."""
    _require_product(db, company_id, product_id)

    stmt = (
        select(QuoteLine, SupplierQuote, Party)
        .join(SupplierQuote, QuoteLine.quote_id == SupplierQuote.id)
        .join(Party, SupplierQuote.supplier_id == Party.id)
        .where(
            QuoteLine.product_id == product_id,
            SupplierQuote.company_id == company_id,
            SupplierQuote.status.in_(["ACTIVE", "AWARDED", "CONVERTED"]),
        )
    )
    rows = db.execute(stmt).all()
    items = []
    for line, quote, party in rows:
        qty = Decimal(str(line.quantity))
        unit = Decimal(str(line.unit_price)).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
        line_amount = (qty * unit).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
        discount = Decimal(str(line.discount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
        expired = _quote_expired(quote)
        items.append({
            "quote_id": quote.id,
            "quote_code": quote.code,
            "quote_status": quote.status,
            "supplier_id": quote.supplier_id,
            "supplier_name": party.name,
            "currency": quote.currency,
            "quantity": str(qty),
            "unit_price": str(unit),
            "discount": str(discount),
            "line_amount": str(line_amount),
            "delivery_days": line.delivery_days,
            "validity_until": quote.validity_until.isoformat() if quote.validity_until else None,
            "expired": expired,
            "terms": quote.terms,
            "can_award": quote.status == "ACTIVE" and not expired,
        })

    items.sort(key=lambda x: (
        x["currency"],
        Decimal(x["unit_price"]),
        (x["delivery_days"] is None, x["delivery_days"] if x["delivery_days"] is not None else 0),
        x["quote_code"],
    ))
    return {"product_id": product_id, "items": items}


def award_quote(db: Session, *, company_id: str, quote_id: str, reason: str,
                actor: str | None = None) -> SupplierQuote:
    reason = reason.strip()
    if not reason:
        raise KontrolError(code="REASON_REQUIRED", message="El motivo de adjudicación es obligatorio", status_code=422)

    quote = _lock_quote(db, company_id, quote_id)

    if quote.status in ("AWARDED", "CONVERTED"):
        raise ConflictError(code="QUOTE_ALREADY_AWARDED", message="La cotización ya fue adjudicada")
    if quote.status != "ACTIVE":
        raise ConflictError(code="QUOTE_NOT_AWARDABLE", message="La cotización no puede adjudicarse en su estado actual")
    if _quote_expired(quote):
        raise ConflictError(code="QUOTE_EXPIRED", message="La cotización venció y no puede adjudicarse")

    lines = db.execute(select(QuoteLine).where(QuoteLine.quote_id == quote.id)).scalars().all()
    if not lines:
        raise ConflictError(code="QUOTE_EMPTY", message="Una cotización sin líneas no puede adjudicarse")

    _require_party(db, company_id, quote.supplier_id, role="PROVEEDOR", require_active=True)

    quote.status = "AWARDED"
    quote.awarded_at = datetime.now(UTC)
    quote.awarded_by = actor
    quote.award_reason = reason
    _audit(db, action="PURCHASE_QUOTE_AWARDED", entity_type="SupplierQuote",
           entity_id=str(quote.id), company_id=company_id, actor=actor,
           after={"status": quote.status, "supplier_id": quote.supplier_id, "reason": quote.award_reason})
    db.flush()
    return quote


def order_from_quote(db: Session, *, company_id: str, quote_id: str, code: str,
                     actor: str | None = None) -> tuple[PurchaseOrder, bool]:
    code = code.strip()
    if not code:
        raise KontrolError(code="CODE_REQUIRED", message="El código es obligatorio", status_code=422)

    quote = _lock_quote(db, company_id, quote_id)

    existing = _existing_order_for_quote(db, str(quote.id))
    if existing is not None:
        return existing, False

    if quote.status != "AWARDED":
        raise ConflictError(code="QUOTE_NOT_AWARDED", message="Solo se puede convertir una cotización adjudicada")
    if _quote_expired(quote):
        raise ConflictError(code="QUOTE_EXPIRED", message="La cotización venció y no puede convertirse.")

    lines = db.execute(select(QuoteLine).where(QuoteLine.quote_id == quote.id)).scalars().all()
    if not lines:
        raise ConflictError(code="QUOTE_EMPTY", message="Una cotización sin líneas no produce una orden")

    try:
        with db.begin_nested():
            order = create_order(db, company_id=company_id, code=code, supplier_id=quote.supplier_id,
                                 terms=quote.terms, currency=quote.currency, actor=actor)
            order.quote_id = str(quote.id)
            db.flush()
    except IntegrityError as error:
        if not es_violacion_unica(error, "uq_purchase_orders_quote_id"):
            raise
        existente = _existing_order_for_quote(db, str(quote.id))
        if existente is None:
            raise
        return existente, False

    for line in lines:
        add_order_line(db, order_id=str(order.id), product_id=line.product_id,
                       quantity_ordered=line.quantity, unit_price=line.unit_price,
                       discount=line.discount, tax_ref=line.tax_ref, needs_inventory=True)

    quote.status = "CONVERTED"
    _audit(db, action="PURCHASE_QUOTE_CONVERTED", entity_type="SupplierQuote",
           entity_id=str(quote.id), company_id=company_id, actor=actor,
           after={"order_id": str(order.id), "status": quote.status})
    db.flush()
    return order, True


def _require_order(db: Session, company_id: str, order_id: str) -> PurchaseOrder:
    order = db.get(PurchaseOrder, order_id)
    if not order or order.company_id != company_id:
        raise NotFoundError(code="ORDER_NOT_FOUND", message="Orden de compra no encontrada")
    return order


def order_allowed_actions(order: PurchaseOrder) -> dict[str, bool]:
    s = order.status
    return {"view": True, "submit": s == "DRAFT", "approve": s == "SUBMITTED", "reject": s == "SUBMITTED",
            "cancel": s in ("DRAFT", "APPROVED"), "receive": s in RECEIVABLE_ORDER_STATUSES, "close": s == "RECEIVED"}


def receipt_allowed_actions(receipt: GoodsReceipt) -> dict[str, bool]:
    """Acciones permitidas por la máquina de FR-004-031; el backend las revalida en cada operación."""
    s = receipt.status
    return {"confirm": s == "DRAFT", "cancel": s == "DRAFT", "send_to_quality": s == "CONFIRMED",
            "record_quality": s == "QUALITY_PENDING" and receipt.quality_status != "APPROVED",
            "accept": s == "QUALITY_PENDING" and receipt.quality_status == "APPROVED",
            "close": (s in ("ACCEPTED", "PARTIALLY_ACCEPTED") and receipt.confirmation_status == CONFIRMATION_DONE)
            or s == "REJECTED"}


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
                       cost_center_id: str | None = None, need_date=None, warehouse_id: str | None = None,
                       actor: str | None = None) -> PurchaseRequisition:
    company_id = _company(company_id, obj="requisición")
    if warehouse_id:
        warehouse = db.get(Warehouse, warehouse_id)
        if not warehouse or not warehouse_belongs_to(company_id, warehouse):
            raise NotFoundError(code="WAREHOUSE_NOT_FOUND", message="Almacén no encontrado")
    req = PurchaseRequisition(company_id=company_id, code=code, requester_id=requester_id,
                              cost_center_id=cost_center_id, need_date=need_date, warehouse_id=warehouse_id,
                              status="DRAFT", created_by=actor)
    db.add(req)
    db.flush()
    return req


def add_requisition_line(db: Session, *, requisition_id: str, product_id: str, quantity: float,
                         unit_id: str | None = None, notes: str | None = None) -> RequisitionLine:
    req = db.get(PurchaseRequisition, requisition_id)
    if req is None:
        raise NotFoundError(code="REQUISITION_NOT_FOUND", message="Requisición no encontrada")
    _require_product(db, req.company_id, product_id)
    if unit_id:
        from app.modules.master_data.models import UnitOfMeasure
        unidad = db.get(UnitOfMeasure, unit_id)
        if unidad is None or (unidad.company_id is not None and unidad.company_id != req.company_id):
            raise NotFoundError(code="UOM_NOT_FOUND", message="Unidad no encontrada")
    line = RequisitionLine(requisition_id=requisition_id, product_id=product_id, quantity=quantity,
                           unit_id=unit_id, notes=notes)
    db.add(line)
    db.flush()
    return line


def transition_requisition(db: Session, *, requisition: PurchaseRequisition, target: str,
                           actor: str | None = None) -> PurchaseRequisition:
    """Transición de la requisición, gobernada por el motor de aprobaciones (Spec 045).

    Sin política activa el comportamiento es idéntico al anterior (AC-20).
    """
    _assert_transition(requisition.status, target, REQUISITION_TRANSITIONS, "la requisición")
    if target == "SUBMITTED":
        approvals_integration.require_for_document(
            db, company_id=requisition.company_id,
            process_type=approvals_integration.PROCESS_PURCHASE_REQUISITION,
            document_type="PurchaseRequisition", document_id=str(requisition.id),
            context=_requisition_context(db, requisition), actor=actor)
    if target == "APPROVED":
        approvals_integration.ensure_approved(
            db, company_id=requisition.company_id, document_type="PurchaseRequisition",
            document_id=str(requisition.id), what="la requisición")
    requisition.status = target
    requisition.updated_at = datetime.now(UTC)
    db.flush()
    _audit(db, action="PURCHASE_REQUISITION_TRANSITIONED", entity_type="PurchaseRequisition",
           entity_id=str(requisition.id), company_id=requisition.company_id, actor=actor,
           after={"target": requisition.status})
    return requisition


def _requisition_context(db: Session, requisition: PurchaseRequisition) -> dict[str, Any]:
    lines = db.execute(select(RequisitionLine).where(
        RequisitionLine.requisition_id == str(requisition.id))).scalars().all()
    # La requisición no lleva precio: la política de este proceso se configura
    # sobre cantidad, centro de costo o solicitante, no sobre monto.
    return {"quantity_total": sum(float(line.quantity or 0) for line in lines),
            "line_count": len(lines),
            "cost_center_id": requisition.cost_center_id,
            "requester_id": requisition.requester_id}


# --------------------------------------------------------------------------- #
# Cotización
# --------------------------------------------------------------------------- #
def create_quote(db: Session, *, company_id: str, code: str, supplier_id: str, validity_until=None,
                 currency: str = "VED", terms: str | None = None, actor: str | None = None) -> SupplierQuote:
    company_id = _company(company_id, obj="cotización")
    _require_party(db, company_id, supplier_id, role="PROVEEDOR", require_active=True)
    quote = SupplierQuote(company_id=company_id, code=code, supplier_id=supplier_id, validity_until=validity_until,
                          currency=currency, terms=terms, status="ACTIVE", created_by=actor)
    db.add(quote)
    db.flush()
    return quote


def _require_quote(db: Session, company_id: str, quote_id: str) -> SupplierQuote:
    quote = db.get(SupplierQuote, quote_id)
    if not quote or quote.company_id != company_id:
        raise NotFoundError(code="QUOTE_NOT_FOUND", message="Cotización de compra no encontrada")
    return quote


def _quote_expired(quote: SupplierQuote, hoy: date | None = None) -> bool:
    """Nula significa **sin vencimiento**, no «vencida»."""
    if quote.validity_until is None:
        return False
    return quote.validity_until < (hoy or hoy_de_negocio())


def _lock_quote(db: Session, company_id: str, quote_id: str) -> SupplierQuote:
    quote = db.execute(
        select(SupplierQuote)
        .where(SupplierQuote.id == quote_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalars().first()
    if not quote or quote.company_id != company_id:
        raise NotFoundError(code="QUOTE_NOT_FOUND", message="Cotización de compra no encontrada")
    return quote


def _existing_order_for_quote(db: Session, quote_id: str) -> PurchaseOrder | None:
    return db.execute(
        select(PurchaseOrder).where(PurchaseOrder.quote_id == quote_id)
    ).scalars().first()


def _require_receipt(db: Session, company_id: str, receipt_id: str) -> GoodsReceipt:
    receipt = db.get(GoodsReceipt, receipt_id)
    if not receipt or receipt.company_id != company_id:
        raise NotFoundError(code="RECEIPT_NOT_FOUND", message="Recepción no encontrada")
    return receipt


def _require_return(db: Session, company_id: str, return_id: str) -> PurchaseReturn:
    ret = db.get(PurchaseReturn, return_id)
    if not ret or ret.company_id != company_id:
        raise NotFoundError(code="PURCHASE_RETURN_NOT_FOUND", message="Devolución de compra no encontrada")
    return ret


def add_quote_line(db: Session, *, company_id: str, quote_id: str, product_id: str, quantity: float,
                   unit_price: float, discount: float = 0.0, delivery_days: int | None = None,
                   tax_ref: str | None = None) -> QuoteLine:
    _require_quote(db, company_id, quote_id)
    _require_product(db, company_id, product_id)
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
    _require_party(db, company_id, supplier_id, role="PROVEEDOR", require_active=True)
    order = PurchaseOrder(company_id=company_id, code=code, supplier_id=supplier_id, terms=terms,
                          expected_date=expected_date, currency=currency, status="DRAFT", created_by=actor)
    db.add(order)
    db.flush()
    return order


def add_order_line(db: Session, *, order_id: str, product_id: str, quantity_ordered: float | Decimal, unit_price: float,
                   discount: float = 0.0, tax_ref: str | None = None, needs_inventory: bool = True,
                   snapshot: str | None = None) -> PurchaseOrderLine:
    if quantity_ordered <= 0:
        raise KontrolError(code="INVALID_QUANTITY", message="La cantidad ordenada debe ser positiva", status_code=422)
    order = db.get(PurchaseOrder, order_id)
    if order is None:
        raise NotFoundError(code="ORDER_NOT_FOUND", message="Orden no encontrada")
    _require_product(db, order.company_id, product_id)
    line = PurchaseOrderLine(order_id=order_id, product_id=product_id, quantity_ordered=quantity_ordered,
                             quantity_received=0.0, unit_price=unit_price, discount=discount, tax_ref=tax_ref,
                             needs_inventory=needs_inventory, snapshot=snapshot)
    db.add(line)
    db.flush()
    return line


def transition_order(db: Session, *, order: PurchaseOrder, target: str, actor: str | None = None,
                     approval_ref: str | None = None) -> PurchaseOrder:
    _assert_transition(order.status, target, ORDER_TRANSITIONS, "la orden")
    if target == "SUBMITTED":
        approvals_integration.require_for_document(
            db, company_id=order.company_id,
            process_type=approvals_integration.PROCESS_PURCHASE_ORDER,
            document_type="PurchaseOrder", document_id=str(order.id),
            context=_order_context(db, order), actor=actor)
    if target == "APPROVED":
        approvals_integration.ensure_approved(
            db, company_id=order.company_id, document_type="PurchaseOrder",
            document_id=str(order.id), what="la orden")
    order.status = target
    order.updated_at = datetime.now(UTC)
    if target == "APPROVED":
        order.approval_ref = approval_ref or order.approval_ref
    db.flush()
    _audit(db, action="PURCHASE_ORDER_TRANSITIONED", entity_type="PurchaseOrder", entity_id=str(order.id),
           company_id=order.company_id, actor=actor, after={"target": order.status})
    return order


def _order_context(db: Session, order: PurchaseOrder) -> dict[str, Any]:
    """Contexto plano para el motor. El dominio lo construye; el motor no conoce el dominio."""
    lines = db.execute(select(PurchaseOrderLine).where(
        PurchaseOrderLine.order_id == str(order.id))).scalars().all()
    total = sum(float(line.unit_price or 0) * float(line.quantity_ordered or 0) for line in lines)
    return {"amount": total, "currency": getattr(order, "currency", "VED") or "VED",
            "rate_snapshot": getattr(order, "rate_snapshot", None),
            "supplier_id": order.supplier_id,
            "branch_id": getattr(order, "branch_id", None)}


# --------------------------------------------------------------------------- #
# Recepción (invoca el motor de inventario de 003)
# --------------------------------------------------------------------------- #
def _requiere_almacen_operable(warehouse: Warehouse | None) -> None:
    if warehouse is None or warehouse.status not in RECEIPT_WAREHOUSE_ALLOWED_STATUSES:
        raise ConflictError(code="WAREHOUSE_NOT_ELIGIBLE",
                            message="El almacén no está activo y no puede recibir mercancía.")


def create_receipt(db: Session, *, company_id: str, code: str, order_id: str, warehouse_id: str,
                   actor: str | None = None, unloading_scheduled_at: datetime | None = None,
                   packing_list_ref: str | None = None, supplier_invoice_ref: str | None = None,
                   packages_declared: int | None = None) -> GoodsReceipt:
    company_id = _company(company_id, obj="recepción")
    order = _require_order(db, company_id, order_id)
    if order.status not in RECEIVABLE_ORDER_STATUSES:
        raise ConflictError(code="ORDER_NOT_RECEIVABLE", message="La orden no está en estado para recibirse.")
    warehouse = db.get(Warehouse, warehouse_id)
    if not warehouse or not warehouse_belongs_to(company_id, warehouse):
        raise NotFoundError(code="WAREHOUSE_NOT_FOUND", message="Almacén no encontrado")
    _requiere_almacen_operable(warehouse)
    if packages_declared is not None and packages_declared < 0:
        raise KontrolError(code="INVALID_PACKAGES", message="Los bultos declarados no pueden ser negativos.",
                           status_code=422)
    receipt = GoodsReceipt(company_id=company_id, code=code, order_id=order_id, warehouse_id=warehouse_id,
                           status="DRAFT", quality_status="PENDING", created_by=actor,
                           unloading_scheduled_at=unloading_scheduled_at,
                           packing_list_ref=packing_list_ref, supplier_invoice_ref=supplier_invoice_ref,
                           packages_declared=packages_declared)
    db.add(receipt)
    db.flush()
    _audit(db, action="RECEIPT_CREATED", entity_type="GoodsReceipt", entity_id=str(receipt.id),
           company_id=company_id, actor=actor,
           after={"order_id": str(order_id), "warehouse_id": warehouse_id,
                  "packing_list_ref": packing_list_ref, "supplier_invoice_ref": supplier_invoice_ref,
                  "packages_declared": packages_declared,
                  "unloading_scheduled_at": unloading_scheduled_at.isoformat() if unloading_scheduled_at else None})
    return receipt


def confirmar_arribo(db: Session, *, company_id: str, receipt_id: str, arrival_at: datetime | None = None,
                     packages_received: int | None = None, actor: str | None = None) -> GoodsReceipt:
    """Etapa 1 del DOCX §2: confirmar el arribo de la mercancía.

    El instante en que llegó y cuántos bultos bajaron del camión no se
    reconstruyen después (`P23`). Si no se indica el momento se usa el de la
    confirmación, que es lo más cerca de la verdad que el sistema puede estar.
    """
    receipt = _require_receipt(db, company_id, receipt_id)
    if receipt.status not in ("DRAFT", "CONFIRMED"):
        raise ConflictError(code="RECEIPT_NOT_OPEN",
                            message="Solo una recepción abierta admite confirmar el arribo.")
    if packages_received is not None and packages_received < 0:
        raise KontrolError(code="INVALID_PACKAGES", message="Los bultos recibidos no pueden ser negativos.",
                           status_code=422)
    receipt.arrival_at = arrival_at or datetime.now(UTC)
    receipt.arrival_confirmed_by = actor
    if packages_received is not None:
        receipt.packages_received = packages_received
    receipt.updated_at = datetime.now(UTC)
    db.flush()
    _audit(db, action="RECEIPT_ARRIVAL_CONFIRMED", entity_type="GoodsReceipt", entity_id=str(receipt.id),
           company_id=company_id, actor=actor,
           after={"arrival_at": receipt.arrival_at.isoformat(),
                  "packages_declared": receipt.packages_declared,
                  "packages_received": receipt.packages_received})
    return receipt


def registrar_inspeccion(db: Session, *, company_id: str, receipt_id: str,
                         packing_list_match: bool | None = None, supplier_invoice_match: bool | None = None,
                         order_match: bool | None = None, documentation_match: bool | None = None,
                         packages_received: int | None = None, notes: str | None = None,
                         actor: str | None = None) -> GoodsReceipt:
    """Etapas 4, 5 y 6: comparar, inspeccionar y validar bultos.

    Guarda el resultado de cada comparación, no solo que se hizo: saber que
    alguien comparó sin saber contra qué ni con qué resultado deja la etapa sin
    valor probatorio. El veredicto de conformidad es la etapa 7 y vive en
    `quality_status`: aquí se registra la inspección que lo sostiene.
    """
    receipt = _require_receipt(db, company_id, receipt_id)
    if receipt.status not in ("DRAFT", "CONFIRMED", "QUALITY_PENDING"):
        raise ConflictError(code="RECEIPT_NOT_OPEN",
                            message="Solo una recepción abierta admite registrar la inspección.")
    if packages_received is not None:
        if packages_received < 0:
            raise KontrolError(code="INVALID_PACKAGES", message="Los bultos recibidos no pueden ser negativos.",
                               status_code=422)
        receipt.packages_received = packages_received
    for campo, valor in (("packing_list_match", packing_list_match),
                         ("supplier_invoice_match", supplier_invoice_match),
                         ("order_match", order_match),
                         ("documentation_match", documentation_match)):
        if valor is not None:
            setattr(receipt, campo, valor)
    receipt.inspected_at = datetime.now(UTC)
    receipt.inspected_by = actor
    if notes is not None:
        receipt.inspection_notes = notes
    receipt.updated_at = datetime.now(UTC)
    db.flush()
    _audit(db, action="RECEIPT_INSPECTED", entity_type="GoodsReceipt", entity_id=str(receipt.id),
           company_id=company_id, actor=actor,
           after={"packing_list_ref": receipt.packing_list_ref,
                  "packing_list_match": receipt.packing_list_match,
                  "supplier_invoice_ref": receipt.supplier_invoice_ref,
                  "supplier_invoice_match": receipt.supplier_invoice_match,
                  "order_match": receipt.order_match,
                  "documentation_match": receipt.documentation_match,
                  "packages_declared": receipt.packages_declared,
                  "packages_received": receipt.packages_received,
                  "notes": receipt.inspection_notes})
    return receipt


def _unidad_recibida(db: Session, *, product_id: str, presentation_id: str | None,
                     cantidades: dict[str, float]) -> dict[str, Any]:
    """Semántica de unidad de la línea de recepción (Spec 011, `R-D0-09-1`).

    Congela el factor de la presentación con la que **se recibió**. Es la pieza
    que faltaba: las columnas existen desde la Spec 011 y ningún código las
    escribía, de modo que el asiento de inventario tomaba la cantidad tecleada
    como si fuera la base. Dos cajas de doce entraban al ledger como dos
    unidades.
    """
    salida: dict[str, Any] = {}
    factor = None
    for nombre, cantidad in cantidades.items():
        conversion = uom_engine.to_base(db, Decimal(str(cantidad)), product_id, presentation_id)
        salida[f"base_quantity_{nombre}"] = conversion.base_quantity
        factor = conversion.factor
        salida["uom_id"] = str(conversion.base_uom_id) if conversion.base_uom_id else None
    salida["conversion_factor_snapshot"] = factor
    salida["uom_source"] = uom_engine.SOURCE_CAPTURED
    return salida


def _sobrante_observado(db: Session, order_line_id: str, base_recibida: Decimal | None) -> Decimal | None:
    """Exceso sobre lo que faltaba por recibir, medido en el muelle.

    El DOCX manda **registrar** el sobrante (etapa 8); tratarlo es de la Spec
    020. Aquí solo se congela la observación: si la orden se edita después, lo
    que se vio al recibir no cambia.
    """
    if base_recibida is None:
        return None
    order_line = db.get(PurchaseOrderLine, order_line_id)
    if order_line is None:
        return None
    # La línea de orden no captura presentación, así que lo pedido ya está en
    # unidad base. Cuando la columna base exista se usa; si no, la cantidad
    # ordenada **es** la base (misma convención que `LEGACY_ASSUMED_BASE`).
    ordenado = (order_line.base_quantity_ordered
                if order_line.base_quantity_ordered is not None else order_line.quantity_ordered)
    pendiente = _dec(ordenado) - _dec(order_line.quantity_received)
    exceso = _dec(base_recibida) - pendiente
    return exceso if exceso > 0 else None


def add_receipt_line(db: Session, *, company_id: str, receipt_id: str, order_line_id: str, product_id: str, quantity_received: float,
                     quantity_accepted: float, quantity_rejected: float, lot_number: str | None = None,
                     expiry_date=None, serials: list[str] | str | None = None,
                     presentation_id: str | None = None, physical_condition: str | None = None,
                     damaged_quantity: float | None = None, damage_notes: str | None = None,
                     identification_ok: bool | None = None, reference_ok: bool | None = None) -> GoodsReceiptLine:
    """Registra lo recibido de una línea, con su unidad y lo que se observó.

    `serials` acepta lista o texto y se normaliza a texto separado por comas:
    la API enviaba una lista a una columna de texto y `accept_receipt` esperaba
    la cadena, de modo que los dos extremos no hablaban el mismo idioma.
    """
    receipt = _require_receipt(db, company_id, receipt_id)
    if receipt.status not in ("DRAFT", "CONFIRMED"):
        raise ConflictError(code="RECEIPT_NOT_OPEN",
                            message="Solo una recepción abierta admite líneas nuevas.")
    if quantity_received <= 0:
        raise KontrolError(code="INVALID_QUANTITY", message="La cantidad recibida debe ser positiva", status_code=422)
    if quantity_accepted < 0 or quantity_rejected < 0:
        raise KontrolError(code="INVALID_QUANTITY", message="Las cantidades no pueden ser negativas", status_code=422)
    if _dec(quantity_accepted) + _dec(quantity_rejected) > _dec(quantity_received):
        raise KontrolError(code="RECEIPT_QUANTITY_MISMATCH",
                           message="Aceptado más rechazado no puede superar lo recibido.", status_code=422)
    if damaged_quantity is not None:
        if damaged_quantity < 0:
            raise KontrolError(code="INVALID_QUANTITY", message="La cantidad dañada no puede ser negativa",
                               status_code=422)
        if _dec(damaged_quantity) > _dec(quantity_received):
            raise KontrolError(code="RECEIPT_DAMAGE_EXCEEDS_RECEIVED",
                               message="No se puede observar más daño que lo recibido.", status_code=422)
    order_line = db.get(PurchaseOrderLine, order_line_id)
    if order_line is None:
        raise NotFoundError(code="PURCHASE_ORDER_LINE_NOT_FOUND", message="Línea de orden no encontrada")
    if str(order_line.order_id) != str(receipt.order_id):
        # La línea de la que se recibe tiene que ser de la orden de esta
        # recepción: sin esta comprobación se podría recibir contra la orden de
        # otra empresa pasando su identificador por el cuerpo.
        raise NotFoundError(code="PURCHASE_ORDER_LINE_NOT_FOUND", message="Línea de orden no encontrada")
    inv_service._require_product(db, company_id, product_id)

    if str(order_line.product_id) != str(product_id):
        # Lo recibido contra una línea de orden debe ser el producto de esa línea.
        # Aceptar toma el costo de la línea y mete inventario del producto; si difieren, el costo y la cantidad recibida quedan sobre otro producto.
        raise KontrolError(code="RECEIPT_LINE_PRODUCT_MISMATCH",
                           message="El producto no corresponde a la línea de la orden.", status_code=422)

    unidad = _unidad_recibida(db, product_id=product_id, presentation_id=presentation_id,
                              cantidades={"received": quantity_received, "accepted": quantity_accepted,
                                          "rejected": quantity_rejected})
    if isinstance(serials, list):
        serials = ",".join(str(x).strip() for x in serials if str(x).strip()) or None
    line = GoodsReceiptLine(receipt_id=receipt_id, order_line_id=order_line_id, product_id=product_id,
                            quantity_received=quantity_received, quantity_accepted=quantity_accepted,
                            quantity_rejected=quantity_rejected, lot_number=lot_number, expiry_date=expiry_date,
                            serials=serials, quality="PENDING", presentation_id=presentation_id,
                            physical_condition=physical_condition, damaged_quantity=damaged_quantity,
                            damage_notes=damage_notes, identification_ok=identification_ok,
                            reference_ok=reference_ok, **unidad)
    line.overage_base_quantity = _sobrante_observado(db, order_line_id, unidad.get("base_quantity_received"))
    db.add(line)
    db.flush()
    _audit(db, action="RECEIPT_LINE_ADDED", entity_type="GoodsReceiptLine", entity_id=str(line.id),
           company_id=company_id, actor=None,
           after={"receipt_id": str(receipt_id), "order_line_id": str(order_line_id),
                  "product_id": str(product_id),
                  "quantity_received": str(line.quantity_received),
                  "base_quantity_received": str(line.base_quantity_received),
                  "presentation_id": presentation_id,
                  "conversion_factor_snapshot": str(line.conversion_factor_snapshot)
                  if line.conversion_factor_snapshot is not None else None,
                  "physical_condition": physical_condition,
                  "damaged_quantity": str(damaged_quantity) if damaged_quantity is not None else None,
                  "identification_ok": identification_ok, "reference_ok": reference_ok,
                  "overage_base_quantity": str(line.overage_base_quantity)
                  if line.overage_base_quantity is not None else None,
                  "lot_number": lot_number,
                  "expiry_date": expiry_date.isoformat() if expiry_date else None,
                  "serials": serials})
    return line


def _transicionar_recepcion(db: Session, receipt: GoodsReceipt, target: str, *, actor: str | None,
                            reason: str | None = None) -> None:
    """Todo cambio de estado de la recepción pasa por aquí y queda auditado."""
    origen = receipt.status
    _assert_transition(origen, target, RECEIPT_TRANSITIONS, "la recepción")
    receipt.status = target
    receipt.updated_at = datetime.now(UTC)
    db.flush()
    _audit(db, action="RECEIPT_TRANSITIONED", entity_type="GoodsReceipt", entity_id=str(receipt.id),
           company_id=receipt.company_id, actor=actor, reason=reason,
           after={"source": origen, "target": target, "reason": reason})


def confirm_receipt(db: Session, *, receipt: GoodsReceipt, actor: str | None = None) -> GoodsReceipt:
    _transicionar_recepcion(db, receipt, "CONFIRMED", actor=actor)
    return receipt


def enviar_a_calidad(db: Session, *, receipt: GoodsReceipt, actor: str | None = None) -> GoodsReceipt:
    """Etapa 5: la calidad toma la recepción confirmada y ya no se añaden líneas."""
    if receipt.status == "CONFIRMED" and db.execute(
            select(GoodsReceiptLine.id).where(GoodsReceiptLine.receipt_id == receipt.id)).first() is None:
        raise ConflictError(code="RECEIPT_EMPTY", message="Una recepción sin líneas no pasa a calidad.")
    _transicionar_recepcion(db, receipt, "QUALITY_PENDING", actor=actor)
    return receipt


def _requiere_lineas_integras(db: Session, receipt: GoodsReceipt, lines: Sequence[GoodsReceiptLine]) -> None:
    """Revalida las filas anteriores al invariante; nada se corrige adivinando."""
    for line in lines:
        order_line = db.get(PurchaseOrderLine, line.order_line_id)
        if (order_line is None or str(order_line.order_id) != str(receipt.order_id)
                or str(order_line.product_id) != str(line.product_id)):
            raise ConflictError(code="RECEIPT_LINE_INTEGRITY",
                                message="Una línea de la recepción no corresponde a su línea de orden.",
                                details={"line_id": str(line.id)})


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
    if not lines:
        raise ConflictError(code="RECEIPT_EMPTY", message="Una recepción sin líneas no se acepta.")
    _requiere_almacen_operable(db.get(Warehouse, receipt.warehouse_id))
    _requiere_lineas_integras(db, receipt, lines)
    order = db.get(PurchaseOrder, receipt.order_id)
    if order is None:
        raise NotFoundError(code="PURCHASE_ORDER_NOT_FOUND", message="Orden de compra no encontrada.")
    if sum(_dec(x.quantity_accepted) for x in lines) <= 0:
        raise ConflictError(code="RECEIPT_NOTHING_ACCEPTED",
                            message="No hay cantidad aceptada: la recepción se rechaza con el veredicto de calidad.")
    # Se compara contra lo recibido, no contra lo pedido: la orden ya tiene su PARTIALLY_RECEIVED.
    destino = ("ACCEPTED" if all(_dec(x.quantity_accepted) == _dec(x.quantity_received) for x in lines)
               else "PARTIALLY_ACCEPTED")
    for line in lines:
        if line.quantity_accepted > 0:
            # La línea de orden se bloquea antes de acumular: dos recepciones
            # simultáneas contra la misma línea harían lectura-modificación-
            # escritura y una de las dos acumulaciones se perdería.
            order_line = db.execute(
                select(PurchaseOrderLine).where(PurchaseOrderLine.id == line.order_line_id)
                .with_for_update().execution_options(populate_existing=True)).scalars().first()
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
                # La presentación viaja al motor: sin ella, `to_base` aplicaría
                # factor 1 y dos cajas de doce entrarían al ledger como dos
                # unidades. La ubicación va nula a propósito: recibir no es
                # ubicar, y colocar es de la Spec 022.
                inv_service.record_movement(
                    db, company_id=receipt.company_id, warehouse_id=receipt.warehouse_id, product_id=line.product_id,
                    movement_type_id=str(mtype.id), quantity=float(line.quantity_accepted),
                    unit_cost=order_line.unit_price if order_line else None, currency=order.currency,
                    document_ref=f"RECEIPT:{receipt.id}", actor=actor,
                    presentation_id=line.presentation_id, location_id=None,
                    # `R-D0-10-4`: recibir no es liberar. La mercancía entra en
                    # `RECIBIDO` —«físicamente recibido, aún no conciliado»— y
                    # solo la confirmación de la Spec 021 la pasa a `DISPONIBLE`.
                    # El ADR reservó este cambio de comportamiento para aquí.
                    state=inv_states.RECEIVED_STATE,
                )
            # Acumular recibido en la línea de orden, en la misma unidad en que
            # se guarda lo pedido: comparar cajas contra unidades daría por
            # recibida una orden que no lo está.
            if order_line:
                aceptado = (line.base_quantity_accepted
                            if line.base_quantity_accepted is not None else line.quantity_accepted)
                order_line.quantity_received = _dec(order_line.quantity_received) + _dec(aceptado)
    receipt.status = destino
    # Etapa 11: recepción conforme, acta emitida. El acta no es un documento
    # nuevo: es el registro de recepción, fechado y con responsable.
    receipt.record_issued_at = datetime.now(UTC)
    receipt.record_issued_by = actor
    receipt.updated_at = datetime.now(UTC)
    db.flush()
    _sync_order_status(db, receipt.order_id)
    _audit(db, action="RECEIPT_ACCEPTED", entity_type="GoodsReceipt", entity_id=str(receipt.id),
           company_id=receipt.company_id, actor=actor,
           after={"status": receipt.status, "order_id": str(receipt.order_id), "warehouse_id": receipt.warehouse_id,
                  "record_issued_at": receipt.record_issued_at.isoformat(),
                  "arrival_at": receipt.arrival_at.isoformat() if receipt.arrival_at else None,
                  "packages_declared": receipt.packages_declared,
                  "packages_received": receipt.packages_received,
                  "lines": [{"line_id": str(x.id), "product_id": str(x.product_id),
                             "quantity_accepted": str(x.quantity_accepted),
                             "base_quantity_accepted": str(x.base_quantity_accepted)
                             if x.base_quantity_accepted is not None else None,
                             "presentation_id": x.presentation_id,
                             "conversion_factor_snapshot": str(x.conversion_factor_snapshot)
                             if x.conversion_factor_snapshot is not None else None}
                            for x in lines]})
    return receipt


def registrar_conformidad(db: Session, *, receipt: GoodsReceipt, quality_status: str,
                          actor: str | None = None) -> GoodsReceipt:
    """Registra la conformidad de la etapa 7."""
    if receipt.status != "QUALITY_PENDING":
        raise ConflictError(code="QUALITY_NOT_PENDING",
                            message="El veredicto se registra con la recepción en calidad.")
    if quality_status == "REJECTED":
        reject_receipt(db, receipt=receipt, actor=actor)
    else:
        receipt.quality_status = quality_status
        receipt.updated_at = datetime.now(UTC)
        db.flush()
    _audit(db, action="RECEIPT_QUALITY_RECORDED", entity_type="GoodsReceipt", entity_id=str(receipt.id),
           company_id=receipt.company_id, actor=actor,
           after={"quality_status": receipt.quality_status, "status": receipt.status})
    return receipt


def reject_receipt(db: Session, *, receipt: GoodsReceipt, actor: str | None = None) -> GoodsReceipt:
    _assert_transition(receipt.status, "REJECTED", RECEIPT_TRANSITIONS, "la recepción")
    receipt.status = "REJECTED"
    receipt.quality_status = "REJECTED"
    receipt.updated_at = datetime.now(UTC)
    db.flush()
    return receipt


def cerrar_recepcion(db: Session, *, receipt: GoodsReceipt, actor: str | None = None) -> GoodsReceipt:
    """Fin del ciclo de vida de la recepción.

    Reutiliza el estado de las Specs 020 y 021; no mueve inventario ni toca
    cantidades, incidencias, lotes ni la orden.
    """
    _assert_transition(receipt.status, "CLOSED", RECEIPT_TRANSITIONS, "la recepción")
    if receipt.status in ("ACCEPTED", "PARTIALLY_ACCEPTED") and receipt.confirmation_status != CONFIRMATION_DONE:
        raise ConflictError(code="RECEIPT_NOT_RECONCILED",
                            message="Una recepción aceptada se cierra después de confirmar su inventario.")
    if receipt.status == "REJECTED" and resultado_de_incidencias(
            db, company_id=receipt.company_id, receipt_id=str(receipt.id))["unresolved"]:
        raise ConflictError(code="RECEIPT_INCIDENTS_OPEN",
                            message="La recepción tiene incidencias sin resolver.")
    _transicionar_recepcion(db, receipt, "CLOSED", actor=actor)
    return receipt


def anular_recepcion(db: Session, *, receipt: GoodsReceipt, reason: str | None,
                     actor: str | None = None) -> GoodsReceipt:
    """Anula un borrador creado por error; sin efectos definitivos porque el inventario solo entra al aceptar."""
    motivo = (reason or "").strip()
    if not motivo:
        raise KontrolError(code="REASON_REQUIRED", message="Anular una recepción exige un motivo.",
                           status_code=422)
    _assert_transition(receipt.status, "CANCELLED", RECEIPT_TRANSITIONS, "la recepción")
    if resultado_de_incidencias(db, company_id=receipt.company_id, receipt_id=str(receipt.id))["unresolved"]:
        raise ConflictError(code="RECEIPT_INCIDENTS_OPEN",
                            message="La recepción tiene incidencias sin resolver.")
    _transicionar_recepcion(db, receipt, "CANCELLED", actor=actor, reason=motivo)
    return receipt


# --------------------------------------------------------------------------- #
# Incidencias de recepción (Spec 020, etapas 8, 9 y 10 del proceso)
# --------------------------------------------------------------------------- #
#: Transiciones de la incidencia. `RESUELTA` y `ANULADA` son terminales: una
#: decisión tomada no cambia porque después cambie la recepción o un maestro.
INCIDENT_TRANSITIONS: dict[str, set[str]] = {
    "REGISTRADA": {"ESCALADA", "PENDIENTE_AUTORIZACION", "RESUELTA", "ANULADA"},
    "ESCALADA": {"PENDIENTE_AUTORIZACION", "RESUELTA", "ANULADA"},
    "PENDIENTE_AUTORIZACION": {"RESUELTA", "ANULADA"},
    "RESUELTA": set(),
    "ANULADA": set(),
}

#: Estados en los que la incidencia sigue comprometiendo cantidad de la línea.
INCIDENT_LIVE_STATES = ("REGISTRADA", "ESCALADA", "PENDIENTE_AUTORIZACION", "RESUELTA")


def _require_incident(db: Session, company_id: str, incident_id: str) -> ReceiptIncident:
    incident = db.get(ReceiptIncident, incident_id)
    if not incident or str(incident.company_id) != str(company_id):
        raise NotFoundError(code="RECEIPT_INCIDENT_NOT_FOUND", message="Incidencia no encontrada")
    return incident


def _tope_de_cantidad(db: Session, line: GoodsReceiptLine, incident_type: str) -> Decimal:
    """Cuánto puede afectar como máximo una incidencia de este tipo sobre esta línea.

    No es el mismo tope para todos, y tratarlo como si lo fuera sería falso: un
    faltante habla de mercancía que **no** llegó, así que su techo es lo que se
    pidió; los otros tres hablan de mercancía que sí llegó, y su techo es lo
    recibido.
    """
    if incident_type == "FALTANTE":
        order_line = db.get(PurchaseOrderLine, line.order_line_id)
        if order_line is None:  # pragma: no cover - la línea existe por clave foránea
            return Decimal(0)
        ordenado = (order_line.base_quantity_ordered
                    if order_line.base_quantity_ordered is not None else order_line.quantity_ordered)
        return _dec(ordenado)
    recibido = (line.base_quantity_received
                if line.base_quantity_received is not None else line.quantity_received)
    return _dec(recibido)


def _afectado_vivo(db: Session, line_id: str, incident_type: str, excluir: str | None = None) -> Decimal:
    """Suma de lo ya comprometido por otras incidencias del mismo tipo sobre la línea."""
    stmt = select(ReceiptIncident).where(
        ReceiptIncident.receipt_line_id == line_id,
        ReceiptIncident.incident_type == incident_type,
        ReceiptIncident.status.in_(INCIDENT_LIVE_STATES))
    total = Decimal(0)
    for otra in db.execute(stmt).scalars().all():
        if excluir and str(otra.id) == str(excluir):
            continue
        total += _dec(otra.affected_base_quantity)
    return total


def registrar_incidencia(db: Session, *, company_id: str, receipt_id: str, code: str,
                         incident_type: str, receipt_line_id: str | None = None,
                         affected_base_quantity: float | None = None,
                         description: str | None = None, actor: str | None = None) -> ReceiptIncident:
    """Etapa 8: registrar una diferencia observada en la recepción.

    La incidencia **no repite** el hecho físico: apunta a la línea, donde la
    Spec 019 dejó producto, cantidades, unidad, presentación, factor congelado,
    estado físico y daño observado. Aquí se clasifica y se le da ciclo de vida.
    """
    company_id = _company(company_id, obj="incidencia de recepción")
    receipt = _require_receipt(db, company_id, receipt_id)
    if receipt.status == "CANCELLED":
        raise ConflictError(code="RECEIPT_CANCELLED",
                            message="Una recepción anulada no admite incidencias.")
    if receipt.status == "CLOSED":
        raise ConflictError(code="RECEIPT_CLOSED",
                            message="Una recepción cerrada no admite incidencias.")
    if incident_type not in INCIDENT_TYPES:
        raise KontrolError(code="INVALID_INCIDENT_TYPE",
                           message=f"Tipo de incidencia no reconocido: {incident_type}.",
                           status_code=422, details={"allowed": list(INCIDENT_TYPES)})

    documental = incident_type == INCIDENT_TYPE_DOCUMENTAL
    if documental:
        if receipt_line_id is not None or affected_base_quantity is not None:
            raise KontrolError(code="INCIDENT_DOCUMENTAL_HAS_NO_LINE",
                               message="Una diferencia documental es del documento: no lleva línea ni cantidad.",
                               status_code=422)
        line = None
    else:
        if receipt_line_id is None or affected_base_quantity is None:
            raise KontrolError(code="INCIDENT_REQUIRES_LINE_AND_QUANTITY",
                               message="Una diferencia de mercancía exige línea y cantidad afectada.",
                               status_code=422)
        if affected_base_quantity <= 0:
            raise KontrolError(code="INVALID_QUANTITY",
                               message="La cantidad afectada debe ser positiva.", status_code=422)
        # Se bloquea la línea: dos incidencias simultáneas del mismo tipo sobre
        # la misma línea podrían comprometer entre las dos más de lo que llegó.
        line = db.execute(
            select(GoodsReceiptLine).where(GoodsReceiptLine.id == receipt_line_id)
            .with_for_update().execution_options(populate_existing=True)).scalars().first()
        if line is None or str(line.receipt_id) != str(receipt.id):
            raise NotFoundError(code="RECEIPT_LINE_NOT_FOUND",
                                message="Línea de recepción no encontrada en esta recepción")
        tope = _tope_de_cantidad(db, line, incident_type)
        ya = _afectado_vivo(db, str(line.id), incident_type)
        if ya + _dec(affected_base_quantity) > tope:
            raise ConflictError(
                code="INCIDENT_QUANTITY_EXCEEDED",
                message="La cantidad afectada supera lo que ese tipo de incidencia admite en la línea.",
                details={"incident_type": incident_type, "cap_base": str(tope),
                         "already_affected_base": str(ya), "requested_base": str(affected_base_quantity)})

    incident = ReceiptIncident(
        company_id=company_id, receipt_id=str(receipt.id), receipt_line_id=receipt_line_id,
        code=code, incident_type=incident_type,
        affected_base_quantity=None if documental else _dec(affected_base_quantity),
        description=description, status="REGISTRADA", created_by=actor)
    db.add(incident)
    db.flush()
    _audit(db, action="RECEIPT_INCIDENT_REGISTERED", entity_type="ReceiptIncident",
           entity_id=str(incident.id), company_id=company_id, actor=actor,
           after={"receipt_id": str(receipt.id), "receipt_line_id": receipt_line_id,
                  "product_id": str(line.product_id) if line is not None else None,
                  "incident_type": incident_type,
                  "affected_base_quantity": str(incident.affected_base_quantity)
                  if incident.affected_base_quantity is not None else None,
                  "status": "REGISTRADA", "code": code})
    return incident


def escalar_incidencia(db: Session, *, company_id: str, incident_id: str,
                       notes: str | None = None, actor: str | None = None) -> ReceiptIncident:
    """Etapa 10: escalar la novedad a Compras."""
    incident = _require_incident(db, company_id, incident_id)
    _assert_transition(incident.status, "ESCALADA", INCIDENT_TRANSITIONS, "la incidencia")
    incident.status = "ESCALADA"
    incident.escalated_at = datetime.now(UTC)
    incident.escalated_by = actor
    incident.escalation_notes = notes
    incident.updated_at = datetime.now(UTC)
    db.flush()
    _audit(db, action="RECEIPT_INCIDENT_ESCALATED", entity_type="ReceiptIncident",
           entity_id=str(incident.id), company_id=company_id, actor=actor,
           after={"status": "ESCALADA", "notes": notes})
    return incident


def _contexto_de_incidencia(incident: ReceiptIncident) -> dict[str, Any]:
    return {"incident_type": incident.incident_type,
            "amount": float(incident.affected_base_quantity or 0),
            "currency": "VED",
            "receipt_id": str(incident.receipt_id),
            "resolution": INCIDENT_RESOLUTION_APPROVED}


def resolver_incidencia(db: Session, *, company_id: str, incident_id: str, resolution: str,
                        reason: str | None = None, actor: str | None = None) -> ReceiptIncident:
    """Registra el tratamiento decidido para la incidencia.

    Registrar no es ejecutar: confirmar el inventario y escribir el estado de la
    mercancía es de la Spec 021. Aquí queda la decisión, estructurada, para que
    aquella la consuma sin interpretar texto libre.

    El ajuste autorizado es el único tratamiento que pasa por el motor de
    aprobaciones, porque el proceso lo declara control crítico.
    """
    motivo = (reason or "").strip()
    if not motivo:
        raise KontrolError(code="REASON_REQUIRED", message="Debe indicar el motivo del tratamiento.",
                           status_code=422)
    if resolution not in INCIDENT_RESOLUTIONS:
        raise KontrolError(code="INVALID_INCIDENT_RESOLUTION",
                           message=f"Tratamiento no reconocido: {resolution}.", status_code=422,
                           details={"allowed": list(INCIDENT_RESOLUTIONS)})
    # Se bloquea la incidencia: dos resoluciones simultáneas no pueden tomar dos
    # decisiones distintas sobre la misma diferencia.
    incident = db.execute(
        select(ReceiptIncident).where(ReceiptIncident.id == incident_id)
        .with_for_update().execution_options(populate_existing=True)).scalars().first()
    if incident is None or str(incident.company_id) != str(company_id):
        raise NotFoundError(code="RECEIPT_INCIDENT_NOT_FOUND", message="Incidencia no encontrada")

    if resolution == INCIDENT_RESOLUTION_APPROVED and incident.status != "PENDIENTE_AUTORIZACION":
        resultado = approvals_integration.require_for_document(
            db, company_id=company_id, process_type=approvals_integration.PROCESS_RECEIPT_INCIDENT,
            document_type="ReceiptIncident", document_id=str(incident.id),
            context=_contexto_de_incidencia(incident), actor=actor)
        if resultado.get("requires_approval"):
            _assert_transition(incident.status, "PENDIENTE_AUTORIZACION", INCIDENT_TRANSITIONS,
                               "la incidencia")
            incident.status = "PENDIENTE_AUTORIZACION"
            incident.approval_request_id = str(resultado["request"].id)
            incident.resolution_reason = motivo
            incident.updated_at = datetime.now(UTC)
            db.flush()
            _audit(db, action="RECEIPT_INCIDENT_APPROVAL_REQUESTED", entity_type="ReceiptIncident",
                   entity_id=str(incident.id), company_id=company_id, actor=actor, reason=motivo,
                   after={"status": "PENDIENTE_AUTORIZACION", "resolution": resolution,
                          "approval_request_id": incident.approval_request_id})
            return incident
    if resolution == INCIDENT_RESOLUTION_APPROVED:
        approvals_integration.ensure_approved(
            db, company_id=company_id, document_type="ReceiptIncident",
            document_id=str(incident.id), what="la incidencia")

    _assert_transition(incident.status, "RESUELTA", INCIDENT_TRANSITIONS, "la incidencia")
    incident.status = "RESUELTA"
    incident.resolution = resolution
    incident.resolution_reason = motivo
    incident.resolved_at = datetime.now(UTC)
    incident.resolved_by = actor
    incident.updated_at = datetime.now(UTC)
    db.flush()
    _audit(db, action="RECEIPT_INCIDENT_RESOLVED", entity_type="ReceiptIncident",
           entity_id=str(incident.id), company_id=company_id, actor=actor, reason=motivo,
           after={"status": "RESUELTA", "resolution": resolution,
                  "incident_type": incident.incident_type,
                  "receipt_line_id": incident.receipt_line_id,
                  "affected_base_quantity": str(incident.affected_base_quantity)
                  if incident.affected_base_quantity is not None else None,
                  "approval_request_id": incident.approval_request_id})
    return incident


def anular_incidencia(db: Session, *, company_id: str, incident_id: str, reason: str | None = None,
                      actor: str | None = None) -> ReceiptIncident:
    """Se registró por error. Libera la cantidad que comprometía."""
    motivo = (reason or "").strip()
    if not motivo:
        raise KontrolError(code="REASON_REQUIRED", message="Debe indicar el motivo.", status_code=422)
    incident = _require_incident(db, company_id, incident_id)
    _assert_transition(incident.status, "ANULADA", INCIDENT_TRANSITIONS, "la incidencia")
    previo = incident.status
    incident.status = "ANULADA"
    incident.cancelled_reason = motivo
    incident.updated_at = datetime.now(UTC)
    db.flush()
    _audit(db, action="RECEIPT_INCIDENT_CANCELLED", entity_type="ReceiptIncident",
           entity_id=str(incident.id), company_id=company_id, actor=actor, reason=motivo,
           before={"status": previo}, after={"status": "ANULADA"})
    return incident


def incidencias_de_recepcion(db: Session, *, company_id: str, receipt_id: str) -> list[ReceiptIncident]:
    return list(db.execute(
        select(ReceiptIncident).where(ReceiptIncident.company_id == company_id,
                                      ReceiptIncident.receipt_id == receipt_id)
        .order_by(ReceiptIncident.created_at)).scalars().all())


def resultado_de_incidencias(db: Session, *, company_id: str, receipt_id: str) -> dict[str, Any]:
    """Contrato de salida para la Spec 021.

    Estructurado a propósito: la confirmación de inventario no debería tener que
    leer texto libre para saber qué se decidió. Devuelve, por línea y tipo, la
    cantidad base afectada y el tratamiento, más si queda algo sin resolver.
    """
    incidencias = incidencias_de_recepcion(db, company_id=company_id, receipt_id=receipt_id)
    vivas = [x for x in incidencias if x.status != "ANULADA"]
    pendientes = [x for x in vivas if x.status != "RESUELTA"]
    return {
        "receipt_id": str(receipt_id),
        "total": len(vivas),
        "unresolved": len(pendientes),
        "ready_for_confirmation": not pendientes,
        "items": [
            {"incident_id": str(x.id), "code": x.code, "incident_type": x.incident_type,
             "receipt_line_id": x.receipt_line_id,
             "affected_base_quantity": str(x.affected_base_quantity)
             if x.affected_base_quantity is not None else None,
             "status": x.status, "resolution": x.resolution,
             "approval_request_id": x.approval_request_id}
            for x in vivas
        ],
    }


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

# ---------------------------------------------------------------------------
# Spec 021 — confirmación y conciliación del inventario recibido
# ---------------------------------------------------------------------------
#
# El proceso documentado (DOCX §3) pide, en este orden: contar por SKU, comparar
# contra la orden, contra el packing list y contra la recepción física,
# identificar las diferencias, diferenciar el inventario por estado, y —una vez
# conciliado— confirmar y liberar el lote.
#
# Lo que esta Spec **no** hace: no resuelve incidencias (es de la 020), no mueve
# saldos por su cuenta (es de la 023) y no ubica nada (es de la 022).

CONFIRMATION_PENDING = "PENDIENTE"
CONFIRMATION_DONE = "CONFIRMADA"


def _requiere_linea(db: Session, receipt: GoodsReceipt, line_id: str) -> GoodsReceiptLine:
    """La línea debe ser de esta recepción. Un id ajeno no abre nada."""
    line = db.execute(select(GoodsReceiptLine).where(
        GoodsReceiptLine.id == line_id,
        GoodsReceiptLine.receipt_id == str(receipt.id))).scalars().first()
    if line is None:
        raise NotFoundError(message="La línea de recepción no existe en esta recepción")
    return line


def _base_recibida(line: GoodsReceiptLine) -> Decimal:
    """Lo recibido en unidad base. Con presentación, lo tecleado no sirve."""
    if line.base_quantity_received is not None:
        return _dec(line.base_quantity_received)
    return _dec(line.quantity_received)


def _conteo_independiente_activo(db: Session, company_id: str) -> bool:
    """El control está activo si la empresa no permite que la misma persona
    registre/acepte y cuente una recepción (Spec 021, R-D0-10-9)."""
    company = db.get(Company, company_id)
    return bool(company is not None and not company.receipt_count_same_user_allowed)


def _receptores(receipt: GoodsReceipt) -> set[str]:
    return {str(user_id) for user_id in (receipt.created_by, receipt.record_issued_by)
            if user_id is not None}


def politica_de_conteo(db: Session, *, company_id: str) -> dict[str, Any]:
    company = db.get(Company, company_id)
    if company is None:
        raise NotFoundError(code="COMPANY_NOT_FOUND", message="Empresa no encontrada")
    return {"receipt_count_same_user_allowed": bool(company.receipt_count_same_user_allowed),
            "independent_count_required": not company.receipt_count_same_user_allowed}


def configurar_conteo(db: Session, *, company_id: str,
                      receipt_count_same_user_allowed: bool,
                      actor: str | None = None) -> dict[str, Any]:
    company = db.get(Company, company_id)
    if company is None:
        raise NotFoundError(code="COMPANY_NOT_FOUND", message="Empresa no encontrada")
    anterior = bool(company.receipt_count_same_user_allowed)
    company.receipt_count_same_user_allowed = receipt_count_same_user_allowed
    db.flush()
    _audit(db, action="COMPANY_RECEIPT_COUNT_POLICY_CHANGED", entity_type="Company",
           entity_id=str(company.id), company_id=company_id, actor=actor,
           before={"receipt_count_same_user_allowed": anterior},
           after={"receipt_count_same_user_allowed": bool(receipt_count_same_user_allowed)})
    return politica_de_conteo(db, company_id=company_id)


def registrar_conteo(db: Session, *, receipt: GoodsReceipt, line_id: str,
                     counted_base_quantity: Decimal | float | str,
                     difference_kinds: list[str] | None = None,
                     actor: str | None = None) -> GoodsReceiptLine:
    """Etapas 1 y 6: conteo detallado por SKU y diferencias identificadas.

    El conteo es en **unidad base**. Contar cajas y compararlas contra unidades
    no concilia nada: era el defecto que la Spec 019 cerró en el asiento y que
    aquí volvería por otra puerta.
    """
    receipt = db.execute(
        select(GoodsReceipt)
        .where(GoodsReceipt.id == receipt.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalars().one()
    if receipt.confirmation_status == CONFIRMATION_DONE:
        raise ConflictError(code="ALREADY_CONFIRMED",
                            message="La recepción ya está confirmada; el conteo no se rehace.")
    if _conteo_independiente_activo(db, receipt.company_id) and actor is not None \
            and actor in _receptores(receipt):
        raise ConflictError(
            code="INDEPENDENT_COUNT_REQUIRED",
            message="El conteo debe hacerlo una persona distinta de quien registró o aceptó la recepción.",
            details={"rule": "RECEIVER_NOT_COUNTER"})
    line = _requiere_linea(db, receipt, line_id)
    contado = _dec(counted_base_quantity)
    if contado < 0:
        raise KontrolError(code="INVALID_QUANTITY", status_code=422,
                           message="La cantidad contada no puede ser negativa.")

    tipos = [k.strip().upper() for k in (difference_kinds or []) if k and k.strip()]
    invalidos = [k for k in tipos if k not in COUNT_DIFFERENCE_KINDS]
    if invalidos:
        raise KontrolError(
            code="COUNT_DIFFERENCE_KIND_UNKNOWN", status_code=422,
            message=f"Diferencia no reconocida: {', '.join(invalidos)}",
            details={"allowed": list(COUNT_DIFFERENCE_KINDS)})

    line.counted_base_quantity = contado
    line.counted_at = datetime.now(UTC)
    line.counted_by = actor
    line.count_difference_kinds = ",".join(dict.fromkeys(tipos)) or None
    line.updated_at = datetime.now(UTC)
    db.flush()
    _audit(db, action="RECEIPT_LINE_COUNTED", entity_type="GoodsReceiptLine", entity_id=str(line.id),
           company_id=receipt.company_id, actor=actor,
           after={"counted_base_quantity": str(contado), "difference_kinds": line.count_difference_kinds,
                  "base_received": str(_base_recibida(line))})
    return line


def resultado_de_conciliacion(db: Session, *, company_id: str, receipt: GoodsReceipt) -> dict[str, Any]:
    """Etapas 2 a 4 y 9: la comparación a cuatro bandas, por línea.

    Compara lo contado contra lo pedido, contra lo recibido físicamente y contra
    lo que la documentación decía. Las tres primeras son cantidades; la cuarta
    —el packing list— es el veredicto que la Spec 019 capturó en el muelle, y no
    se recalcula aquí: se lee.
    """
    lines = db.execute(select(GoodsReceiptLine).where(
        GoodsReceiptLine.receipt_id == str(receipt.id))).scalars().all()
    incidencias = resultado_de_incidencias(db, company_id=company_id, receipt_id=str(receipt.id))
    confirmadas = _confirmado_por_linea(db, receipt)

    items: list[dict[str, Any]] = []
    for line in lines:
        order_line = db.get(PurchaseOrderLine, line.order_line_id) if line.order_line_id else None
        pedido = _dec(order_line.quantity_ordered) if order_line else None
        recibido = _base_recibida(line)
        contado = _dec(line.counted_base_quantity) if line.counted_base_quantity is not None else None
        ya = confirmadas.get(str(line.id), Decimal(0))
        items.append({
            "receipt_line_id": str(line.id),
            "product_id": line.product_id,
            "base_quantity_received": str(recibido),
            "base_quantity_ordered": str(pedido) if pedido is not None else None,
            "counted_base_quantity": str(contado) if contado is not None else None,
            "counted": contado is not None,
            "matches_order": None if (contado is None or pedido is None) else contado == pedido,
            "matches_physical": None if contado is None else contado == recibido,
            "difference_kinds": (line.count_difference_kinds or "").split(",")
            if line.count_difference_kinds else [],
            "already_confirmed_base": str(ya),
            "pending_base": str(recibido - ya),
        })

    sin_contar = [x for x in items if not x["counted"]]
    return {
        "receipt_id": str(receipt.id),
        "confirmation_status": receipt.confirmation_status,
        # El veredicto documental es de la Spec 019 y aquí solo se transporta.
        "packing_list_match": receipt.packing_list_match,
        "supplier_invoice_match": receipt.supplier_invoice_match,
        "order_match": receipt.order_match,
        "documentation_match": receipt.documentation_match,
        "quality_status": receipt.quality_status,
        "incidents": {"total": incidencias["total"], "unresolved": incidencias["unresolved"],
                      "ready_for_confirmation": incidencias["ready_for_confirmation"]},
        "lines_pending_count": [x["receipt_line_id"] for x in sin_contar],
        "ready_for_confirmation": bool(items) and not sin_contar
        and incidencias["ready_for_confirmation"]
        and receipt.confirmation_status != CONFIRMATION_DONE,
        "items": items,
    }


def _confirmado_por_linea(db: Session, receipt: GoodsReceipt) -> dict[str, Decimal]:
    filas = db.execute(select(ReceiptConfirmation).where(
        ReceiptConfirmation.receipt_id == str(receipt.id))).scalars().all()
    acumulado: dict[str, Decimal] = {}
    for f in filas:
        acumulado[f.receipt_line_id] = acumulado.get(f.receipt_line_id, Decimal(0)) + _dec(f.base_quantity)
    return acumulado


def confirmar_inventario(db: Session, *, receipt: GoodsReceipt, decisiones: list[dict[str, Any]],
                         actor: str | None = None) -> dict[str, Any]:
    """Etapas 13 y 14: «una vez conciliado, confirmar inventario» y liberar el lote.

    Cada decisión dice qué cantidad base de qué línea pasa de qué estado a cuál.
    Una línea puede producir varias —noventa liberadas y diez rechazadas—: la
    etapa 9 lo exige y un solo campo por línea no podría representarlo.

    La transición **no se ejecuta aquí**: se solicita al motor canónico de la
    Spec 023, que la valida contra la matriz de `ADR-D0-010` v2. Esta Spec decide
    qué debe ocurrir; aquella decide si puede ocurrir y lo materializa.
    """
    receipt = db.execute(
        select(GoodsReceipt)
        .where(GoodsReceipt.id == receipt.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalars().one()
    if receipt.status not in ("ACCEPTED", "PARTIALLY_ACCEPTED"):
        raise ConflictError(
            code="RECEIPT_NOT_ACCEPTED",
            message="Solo se confirma el inventario de una recepción aceptada.")
    if receipt.confirmation_status == CONFIRMATION_DONE:
        raise ConflictError(code="ALREADY_CONFIRMED",
                            message="Esta recepción ya fue confirmada.")
    if not decisiones:
        raise KontrolError(code="NO_DECISIONS", status_code=422,
                           message="Confirmar exige al menos una decisión sobre una línea.")

    incidencias = resultado_de_incidencias(db, company_id=receipt.company_id, receipt_id=str(receipt.id))
    if not incidencias["ready_for_confirmation"]:
        raise ConflictError(
            code="INCIDENTS_UNRESOLVED",
            message=("No se confirma con incidencias abiertas: "
                     f"{incidencias['unresolved']} sin resolver."),
            details={"unresolved": incidencias["unresolved"]})

    if _conteo_independiente_activo(db, receipt.company_id):
        receptores = _receptores(receipt)
        for decision in decisiones:
            line_id = str(decision.get("receipt_line_id") or "")
            line = _requiere_linea(db, receipt, line_id)
            if line.counted_base_quantity is None:
                raise ConflictError(
                    code="COUNT_REQUIRED_BEFORE_CONFIRMATION",
                    message="Cada línea debe contarse antes de confirmar el inventario.",
                    details={"receipt_line_id": str(line.id)})
            if line.counted_by is not None and line.counted_by in receptores:
                raise ConflictError(
                    code="INDEPENDENT_COUNT_REQUIRED",
                    message="El conteo debe hacerlo una persona distinta de quien registró o aceptó la recepción.",
                    details={"rule": "RECEIVER_NOT_COUNTER", "receipt_line_id": str(line.id)})

    ya_confirmado = _confirmado_por_linea(db, receipt)
    por_linea: dict[str, Decimal] = {}
    resultados: list[dict[str, Any]] = []

    for decision in decisiones:
        line = _requiere_linea(db, receipt, str(decision.get("receipt_line_id") or ""))
        if decision.get("incident_id"):
            incidencia = _require_incident(db, receipt.company_id, str(decision["incident_id"]))
            if str(incidencia.receipt_id) != str(receipt.id):
                raise NotFoundError(code="RECEIPT_INCIDENT_NOT_FOUND", message="Incidencia no encontrada")
        origen = str(decision.get("source_state") or inv_states.RECEIVED_STATE)
        destino = str(decision.get("target_state") or "")
        cantidad = _dec(decision.get("base_quantity") or 0)
        motivo = decision.get("reason")

        if destino not in CONFIRMATION_TARGET_STATES:
            raise KontrolError(
                code="CONFIRMATION_TARGET_UNKNOWN", status_code=422,
                message=f"La confirmación no decide el destino «{destino}».",
                details={"allowed": list(CONFIRMATION_TARGET_STATES)})
        if cantidad <= 0:
            raise KontrolError(code="INVALID_QUANTITY", status_code=422,
                               message="Cada decisión mueve una cantidad mayor que cero.")

        # La invariante de cantidad: entre todo lo ya confirmado y lo que se
        # pide ahora no se puede superar lo que bajó del camión.
        recibido = _base_recibida(line)
        acumulado = ya_confirmado.get(str(line.id), Decimal(0)) + por_linea.get(str(line.id), Decimal(0))
        if acumulado + cantidad > recibido:
            raise ConflictError(
                code="CONFIRMED_EXCEEDS_RECEIVED",
                message=(f"La línea recibió {recibido} y se pretende confirmar "
                         f"{acumulado + cantidad}."),
                details={"receipt_line_id": str(line.id), "base_received": str(recibido),
                         "already_confirmed": str(acumulado), "requested": str(cantidad)})
        por_linea[str(line.id)] = por_linea.get(str(line.id), Decimal(0)) + cantidad

        movimiento = inv_service.reclassify(
            db, company_id=receipt.company_id, warehouse_id=receipt.warehouse_id,
            product_id=line.product_id, source_state=origen, target_state=destino,
            quantity=cantidad, location_id=None,
            document_ref=f"RECEIPT_CONFIRMATION:{receipt.id}", reason=motivo, actor=actor)

        registro = ReceiptConfirmation(
            company_id=receipt.company_id, receipt_id=str(receipt.id),
            receipt_line_id=str(line.id), source_state=origen, target_state=destino,
            base_quantity=cantidad, movement_id=str(movimiento.id),
            incident_id=decision.get("incident_id"), reason=motivo, created_by=actor)
        db.add(registro)
        db.flush()
        resultados.append({"receipt_line_id": str(line.id), "source_state": origen,
                           "target_state": destino, "base_quantity": str(cantidad),
                           "movement_id": str(movimiento.id), "confirmation_id": str(registro.id)})

    receipt.confirmation_status = CONFIRMATION_DONE
    receipt.confirmed_at = datetime.now(UTC)
    receipt.confirmed_by = actor
    receipt.updated_at = datetime.now(UTC)
    db.flush()

    _audit(db, action="RECEIPT_INVENTORY_CONFIRMED", entity_type="GoodsReceipt",
           entity_id=str(receipt.id), company_id=receipt.company_id, actor=actor,
           before={"confirmation_status": CONFIRMATION_PENDING},
           after={"confirmation_status": CONFIRMATION_DONE, "decisions": resultados})
    return {"receipt_id": str(receipt.id), "confirmation_status": receipt.confirmation_status,
            "decisions": resultados}

def create_invoice(db: Session, *, company_id: str, supplier_id: str, invoice_number: str,
                   control_number: str | None = None, issue_date=None, currency: str = "VED",
                   actor: str | None = None, idempotency_key: str | None = None) -> SupplierInvoice:
    company_id = _company(company_id, obj="factura")
    _require_party(db, company_id, supplier_id, role="PROVEEDOR", require_active=True)
    if idempotency_key:
        existing = db.execute(
            select(SupplierInvoice).where(SupplierInvoice.idempotency_key == idempotency_key,
                                          SupplierInvoice.company_id == company_id)).scalars().first()
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
    invoice = db.get(SupplierInvoice, invoice_id)
    if invoice is None:
        raise NotFoundError(code="INVOICE_NOT_FOUND", message="Factura no encontrada")
    _require_product(db, invoice.company_id, product_id)
    if order_line_id:
        ol = db.get(PurchaseOrderLine, order_line_id)
        orden = db.get(PurchaseOrder, ol.order_id) if ol else None
        if orden is None or orden.company_id != invoice.company_id:
            raise NotFoundError(code="ORDER_LINE_NOT_FOUND", message="Línea de orden no encontrada")
    if receipt_line_id:
        rl = db.get(GoodsReceiptLine, receipt_line_id)
        receipt = db.get(GoodsReceipt, rl.receipt_id) if rl else None
        if receipt is None or receipt.company_id != invoice.company_id:
            raise NotFoundError(code="RECEIPT_LINE_NOT_FOUND", message="Línea de recepción no encontrada")
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
        variance_qty = _dec(line.quantity) - _dec(
            order_line.quantity_received if order_line else line.quantity)
        variance_price = ((_money(line.unit_price) - _money(order_line.unit_price))
                          * _dec(line.quantity)) if order_line else Decimal(0)
        # El impuesto esperado de la orden es **cero** en este motor: la orden de
        # compra no lo lleva. El código anterior lo escribía como
        # `precio * cantidad * 0.0`, que es la misma cifra con más pasos. Se
        # conserva la semántica —no es de este delta decidir qué impuesto espera
        # la conciliación triple, que es de su dueña— y se deja anotado.
        variance_tax = _money(line.tax_amount)
        match = TripleMatch(company_id=invoice.company_id, invoice_id=str(invoice.id),
                            order_line_id=line.order_line_id, receipt_line_id=line.receipt_line_id,
                            invoice_line_id=str(line.id), variance_qty=variance_qty,
                            variance_price=variance_price, variance_tax=variance_tax,
                            resolution="PENDING", approved_by=actor)
        db.add(match)
        matches.append(match)
        if variance_qty != 0 or variance_price != 0 or variance_tax != 0:
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
                         due_date=(hoy_de_negocio() + timedelta(days=due_days)) if due_days else None,
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


def add_return_line(db: Session, *, company_id: str, return_id: str, product_id: str, quantity: float,
                    condition: str = "DEFECTUOSO") -> PurchaseReturnLine:
    _require_return(db, company_id, return_id)
    line = PurchaseReturnLine(return_id=return_id, product_id=product_id, quantity=quantity, condition=condition)
    db.add(line)
    db.flush()
    return line


def create_credit_note(db: Session, *, company_id: str, supplier_id: str, number: str, amount: float,
                       invoice_ref: str | None = None, currency: str = "VED",
                       actor: str | None = None) -> SupplierCreditNote:
    company_id = _company(company_id, obj="nota de crédito")
    _require_party(db, company_id, supplier_id, role="PROVEEDOR", require_active=False)
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
           company_id=note.company_id, actor=None, after={"amount": str(_money(note.amount))})
    return note


# --------------------------------------------------------------------------- #
# CxP — open items, pagos, aplicaciones, anticipos, retenciones, aging
# --------------------------------------------------------------------------- #
def open_item_balance(item: OpenItem) -> Decimal:
    """El saldo pendiente de un documento. **Autoridad única del saldo.**

    «Saldo = documentos + débitos − cobros − retenciones − créditos»
    (arquitectura funcional §9), y «los saldos **no se editan**; se calculan
    desde movimientos y aplicaciones» (documento maestro). Aquí se calcula el
    de un documento: lo que vale menos lo que se le ha aplicado.

    Devolvía `round(float(a) - float(b), 6)`. Ese `6` no era una política: era
    el margen que hacía falta para que el error binario no se viera. Con
    `Decimal` la resta es exacta y no hace falta margen ninguno.
    """
    return _money(item.original) - _money(item.applied)


def register_payment(db: Session, *, company_id: str, party_id: str, amount: float | Decimal, currency: str = "VED",
                     instruments: list[dict] | None = None, actor: str | None = None,
                     idempotency_key: str | None = None, direction: str = "OUT") -> Payment:
    company_id = _company(company_id, obj="pago")
    _require_party(db, company_id, party_id, role=_role_for_direction(direction), require_active=False)
    if amount <= 0:
        raise KontrolError(code="INVALID_AMOUNT", message="El monto del pago debe ser positivo", status_code=422)
    if idempotency_key:
        # Acotada por empresa: una clave repetida en otra empresa devolvía su
        # pago, entregando el identificador de un tercero como si fuera propio.
        existing = db.execute(
            select(Payment).where(Payment.idempotency_key == idempotency_key,
                                  Payment.company_id == company_id)).scalars().first()
        if existing:
            return existing
    _require_supplier_approved(db, party_id, direction)
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
    if target in ("APPROVED", "POSTED"):
        _require_supplier_approved(db, payment.party_id, payment.direction)
    payment.status = target
    payment.updated_at = datetime.now(UTC)
    if target in ("APPROVED", "REJECTED"):
        payment.approver_id = actor
    db.flush()
    _audit(db, action="PAYMENT_TRANSITIONED", entity_type="Payment", entity_id=str(payment.id),
           company_id=payment.company_id, actor=actor, after={"target": payment.status, "amount": str(_money(payment.amount))})
    return payment


_MODELO_DE_FUENTE = {"PAYMENT": Payment, "ADVANCE": Advance,
                     "CREDIT": SupplierCreditNote, "WITHHOLDING": Withholding}


def _require_source(db: Session, company_id: str, source_type: str, source_id: str) -> Any:
    """La fuente de una aplicación debe ser de la misma empresa que el destino.

    Sin esta comprobación, un pago de otra empresa del mismo tenant podía
    cancelar una deuda propia: los saldos cuadran a ambos lados y no queda
    ningún síntoma visible, porque el dinero salió de una caja y la deuda se
    extinguió en otra. Son dos personas jurídicas distintas; si una paga por la
    otra, eso es un préstamo entre empresas y necesita su propio documento.
    """
    modelo = _MODELO_DE_FUENTE.get(source_type)
    if modelo is None:
        raise KontrolError(code="INVALID_SOURCE_TYPE",
                           message="Tipo de fuente de aplicación no válido", status_code=422)
    fuente = db.get(modelo, source_id)
    if fuente is None or fuente.company_id != company_id:
        raise NotFoundError(code="APPLICATION_SOURCE_NOT_FOUND",
                            message="Fuente de aplicación no encontrada")
    return fuente


def _source_available(db: Session, *, source_type: str, source_id: str) -> Decimal:
    """Lo que queda por aplicar de una fuente, en `Decimal` exacto."""
    if source_type == "PAYMENT":
        p = db.get(Payment, source_id)
        return _money(p.amount) - _money(p.applied) if p else Decimal(0)
    if source_type == "ADVANCE":
        a = db.get(Advance, source_id)
        return _money(a.available) if a else Decimal(0)
    if source_type == "CREDIT":
        c = db.get(SupplierCreditNote, source_id)
        return _money(c.amount) - _money(c.applied) if c else Decimal(0)
    if source_type == "WITHHOLDING":
        w = db.get(Withholding, source_id)
        return _money(w.amount) if w and w.status not in ("REVERSADA",) else Decimal(0)
    raise KontrolError(code="INVALID_SOURCE_TYPE", message="Tipo de fuente de aplicación no válido", status_code=422)


def _reduce_source(db: Session, *, source_type: str, source_id: str,
                   amount: Decimal | float) -> None:
    aplicado = _money(amount)
    if source_type == "PAYMENT":
        p = db.get(Payment, source_id)
        if p:
            p.applied = _money(p.applied) + aplicado
    elif source_type == "ADVANCE":
        a = db.get(Advance, source_id)
        if a:
            a.available = max(_money(a.available) - aplicado, Decimal(0))
    elif source_type == "CREDIT":
        c = db.get(SupplierCreditNote, source_id)
        if c:
            c.applied = _money(c.applied) + aplicado
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
    _require_source(db, company_id, source_type, source_id)
    balance = open_item_balance(target)
    if amount > balance:
        raise ConflictError(code="APPLICATION_EXCEEDS_BALANCE", message=f"La aplicación excede el saldo disponible ({balance}).")
    available = _source_available(db, source_type=source_type, source_id=source_id)
    if amount > available:
        raise ConflictError(code="APPLICATION_EXCEEDS_SOURCE", message=f"La fuente no tiene saldo disponible ({available}).")

    target.applied = _money(target.applied) + _money(amount)
    # Con `Decimal` el cero es cero. El `1e-6` era el margen que necesitaba la
    # coma flotante para no dejar documentos abiertos por un residuo binario.
    if open_item_balance(target) <= 0:
        target.status = "CLOSED"
    _reduce_source(db, source_type=source_type, source_id=source_id, amount=amount)
    app = Application(company_id=company_id, source_type=source_type, source_id=source_id,
                      target_open_item_id=target_open_item_id, amount=amount, currency=currency,
                      rate=rate, date=hoy_de_negocio(), status="APPLIED")
    db.add(app)
    db.flush()
    _sync_invoice_paid(db, target_open_item_id=str(target.id))
    _audit(db, action="CXP_APPLICATION", entity_type="OpenItem", entity_id=str(target_open_item_id),
           company_id=company_id, actor=actor, after={"source_type": source_type, "amount": str(_money(amount))})
    return app


def _sync_invoice_paid(db: Session, *, target_open_item_id: str) -> None:
    item = db.get(OpenItem, target_open_item_id)
    if not item:
        return
    if item.source_document and item.source_document.startswith("INVOICE:"):
        invoice_id = item.source_document.split(":", 1)[1]
        invoice = db.get(SupplierInvoice, invoice_id)
        if invoice and invoice.status in ("POSTED", "PARTIALLY_PAID"):
            invoice.status = "PAID" if open_item_balance(item) <= 0 else "PARTIALLY_PAID"
            invoice.updated_at = datetime.now(UTC)


def register_advance(db: Session, *, company_id: str, party_id: str, amount: float | Decimal, currency: str = "VED",
                     actor: str | None = None, direction: str = "OUT") -> Advance:
    company_id = _company(company_id, obj="anticipo")
    _require_party(db, company_id, party_id, role=_role_for_direction(direction), require_active=True)
    if amount <= 0:
        raise KontrolError(code="INVALID_AMOUNT", message="El monto del anticipo debe ser positivo", status_code=422)
    _require_supplier_approved(db, party_id, direction)
    adv = Advance(company_id=company_id, party_id=party_id, direction=direction, currency=currency,
                  amount=amount, available=amount, status="ACTIVE", created_by=actor)
    db.add(adv)
    db.flush()
    return adv


def create_withholding(db: Session, *, company_id: str, party_id: str, tax_type: str, rule_ref: str | None,
                       base: float, rate_ref: str | None, amount: float, period: str | None = None,
                       source_event: str | None = None, actor: str | None = None, party_role: str) -> Withholding:
    company_id = _company(company_id, obj="retención")
    _require_party(db, company_id, party_id, role=party_role, require_active=False)
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
    today = hoy_de_negocio()
    buckets = {"0-30": Decimal(0), "31-60": Decimal(0), "61-90": Decimal(0), "90+": Decimal(0)}
    total = Decimal(0)
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
    _require_party(db, company_id, party_id, role="PROVEEDOR", require_active=False)
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
            "quote_id": order.quote_id,
            "allowed_actions": order_allowed_actions(order),
            "lines": [{"id": line.id, "product_id": line.product_id, "quantity_ordered": line.quantity_ordered,
                       "quantity_received": line.quantity_received, "unit_price": line.unit_price,
                       "needs_inventory": line.needs_inventory} for line in lines]}


def quote_dict(db: Session, quote: SupplierQuote) -> dict:
    lines = db.execute(select(QuoteLine).where(QuoteLine.quote_id == quote.id)).scalars().all()
    order = _existing_order_for_quote(db, str(quote.id))
    party = db.get(Party, quote.supplier_id)
    return {
        "id": quote.id,
        "code": quote.code,
        "supplier_id": quote.supplier_id,
        "supplier_name": party.name if party else None,
        "currency": quote.currency,
        "validity_until": quote.validity_until.isoformat() if quote.validity_until else None,
        "status": quote.status,
        "awarded_at": quote.awarded_at.isoformat() if quote.awarded_at else None,
        "awarded_by": quote.awarded_by,
        "award_reason": quote.award_reason,
        "order_id": order.id if order else None,
        "expired": _quote_expired(quote),
        "line_count": len(lines),
        "terms": quote.terms,
    }


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
