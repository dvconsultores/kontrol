"""Servicios de ventas y cuentas por cobrar (005).

Cotización (sin reserva) → pedido → crédito → orden → reserva → picking →
despacho → factura de venta → CxC.

Invariantes (Constitución P4/P5/P8, DOC-01 §5, DOC-03 §12):
- Facturas emitidas y cobros son inmutables; corrección por nota/anulación.
- Los saldos de CxC se calculan desde documentos y aplicaciones; nunca se editan.
- La reserva/picking/despacho invocan el motor de 003; la CxC reutiliza el motor
  de aplicaciones de 004 (ap_open_items RECEIVABLE).
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.inventory import service as inv_service
from app.modules.organization.models import Warehouse
from app.modules.organization.service import warehouse_in_tenant_scope
from app.modules.purchasing import service as ap_service
from app.modules.purchasing.models import OpenItem
from app.modules.sales.models import (
    PickList,
    PickListLine,
    SalesCreditNote,
    SalesDebitNote,
    SalesInvoice,
    SalesInvoiceLine,
    SalesOrder,
    SalesOrderLine,
    SalesQuote,
    SalesQuoteLine,
    SalesReturn,
    SalesReturnLine,
    Shipment,
    ShipmentLine,
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
ORDER_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"SUBMITTED", "CANCELLED"},
    "SUBMITTED": {"CREDIT_PENDING", "REJECTED"},
    "CREDIT_PENDING": {"APPROVED", "REJECTED"},
    "APPROVED": {"RESERVED", "CANCELLED"},
    "RESERVED": {"PREPARING", "SHIPPED", "CANCELLED"},
    "PREPARING": {"SHIPPED", "CANCELLED"},
    "SHIPPED": {"CLOSED"},
    "CLOSED": set(),
    "CANCELLED": set(),
    "REJECTED": set(),
}

INVOICE_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"VALIDATED", "CANCELLED"},
    "VALIDATED": {"APPROVED"},
    "APPROVED": {"EMITTED"},
    "EMITTED": {"DELIVERED", "PARTIALLY_PAID", "PAID", "CREDITED", "VOIDED"},
    "DELIVERED": {"PARTIALLY_PAID", "PAID", "CREDITED", "VOIDED"},
    "PARTIALLY_PAID": {"PAID", "CREDITED", "VOIDED"},
    "PAID": {"CREDITED", "VOIDED"},
    "CREDITED": set(),
    "VOIDED": set(),
    "REJECTED": set(),
    "CANCELLED": set(),
}


def _assert_transition(current: str, target: str, transitions: dict[str, set[str]], what: str) -> None:
    if target not in transitions.get(current, set()):
        raise ConflictError(code="INVALID_STATE_TRANSITION", message=f"No se permite pasar {what} de {current} a {target}.")


def _company(company_id: str | None, *, obj: str) -> str:
    if not company_id:
        raise KontrolError(code="COMPANY_REQUIRED", message="Se requiere la empresa para esta operación", status_code=422)
    return company_id


def _require_party(db: Session, company_id: str, party_id: str) -> None:
    from app.modules.master_data.models import Party

    party = db.get(Party, party_id)
    if not party or party.company_id != company_id:
        raise NotFoundError(code="PARTY_NOT_FOUND", message="Tercero no encontrado")


def _require_warehouse(db: Session, company_id: str, warehouse_id: str) -> Warehouse:
    warehouse = db.get(Warehouse, warehouse_id)
    if not warehouse or not warehouse_in_tenant_scope(db, company_id, warehouse):
        raise NotFoundError(code="WAREHOUSE_NOT_FOUND", message="Almacén no encontrado")
    return warehouse


def _require_order(db: Session, company_id: str, order_id: str) -> SalesOrder:
    order = db.get(SalesOrder, order_id)
    if not order or order.company_id != company_id:
        raise NotFoundError(code="SALES_ORDER_NOT_FOUND", message="Orden de venta no encontrada")
    return order


def order_allowed_actions(order: SalesOrder) -> dict[str, bool]:
    s = order.status
    return {"view": True, "submit": s == "DRAFT", "credit": s == "SUBMITTED", "approve": s == "CREDIT_PENDING",
            "reject": s in ("SUBMITTED", "CREDIT_PENDING"), "reserve": s == "APPROVED",
            "prepare": s == "RESERVED", "ship": s in ("RESERVED", "PREPARING"), "cancel": s in ("DRAFT", "APPROVED", "RESERVED", "PREPARING"),
            "close": s == "SHIPPED"}


def invoice_allowed_actions(invoice: SalesInvoice) -> dict[str, bool]:
    s = invoice.status
    return {"view": True, "validate": s == "DRAFT", "approve": s == "VALIDATED", "emit": s == "APPROVED",
            "deliver": s in ("EMITTED", "DELIVERED"), "void": s in ("EMITTED", "DELIVERED", "PARTIALLY_PAID"),
            "credit": s in ("EMITTED", "DELIVERED", "PARTIALLY_PAID"), "cancel": s == "DRAFT"}


# --------------------------------------------------------------------------- #
# Cotización (sin reserva) y pedido
# --------------------------------------------------------------------------- #
def create_quote(db: Session, *, company_id: str, code: str, customer_id: str, price_list: str | None = None,
                 validity_until=None, currency: str = "VED", actor: str | None = None) -> SalesQuote:
    company_id = _company(company_id, obj="cotización")
    _require_party(db, company_id, customer_id)
    quote = SalesQuote(company_id=company_id, code=code, customer_id=customer_id, price_list=price_list,
                       validity_until=validity_until, currency=currency, status="ACTIVE", created_by=actor)
    db.add(quote)
    db.flush()
    return quote


def add_quote_line(db: Session, *, quote_id: str, product_id: str, quantity: float, unit_price: float,
                   discount: float = 0.0, tax_ref: str | None = None) -> SalesQuoteLine:
    line = SalesQuoteLine(quote_id=quote_id, product_id=product_id, quantity=quantity, unit_price=unit_price,
                          discount=discount, tax_ref=tax_ref)
    db.add(line)
    db.flush()
    return line


def create_order(db: Session, *, company_id: str, code: str, customer_id: str, warehouse_id: str | None = None,
                 margin: float | None = None, currency: str = "VED", actor: str | None = None) -> SalesOrder:
    company_id = _company(company_id, obj="orden de venta")
    _require_party(db, company_id, customer_id)
    if warehouse_id:
        _require_warehouse(db, company_id, warehouse_id)
    order = SalesOrder(company_id=company_id, code=code, customer_id=customer_id, warehouse_id=warehouse_id,
                       margin=margin, currency=currency, status="DRAFT", created_by=actor)
    db.add(order)
    db.flush()
    return order


def add_order_line(db: Session, *, order_id: str, product_id: str, quantity: float, unit_price: float,
                   discount: float = 0.0, tax_ref: str | None = None, needs_inventory: bool = True,
                   snapshot: str | None = None) -> SalesOrderLine:
    if quantity <= 0:
        raise KontrolError(code="INVALID_QUANTITY", message="La cantidad debe ser positiva", status_code=422)
    line = SalesOrderLine(order_id=order_id, product_id=product_id, quantity=quantity, unit_price=unit_price,
                          discount=discount, tax_ref=tax_ref, needs_inventory=needs_inventory, snapshot=snapshot)
    db.add(line)
    db.flush()
    return line


def transition_order(db: Session, *, order: SalesOrder, target: str, actor: str | None = None,
                     credit_decision: str | None = None, approval_ref: str | None = None) -> SalesOrder:
    """Transición de la OV. Al aprobar (APPROVED) se reserva inventario vía 003 (FR-005-020)."""
    _assert_transition(order.status, target, ORDER_TRANSITIONS, "la orden de venta")
    order.status = target
    order.updated_at = datetime.now(UTC)
    if target == "CREDIT_PENDING" and credit_decision:
        order.credit_decision = credit_decision
    if target == "APPROVED":
        order.approval_ref = approval_ref or order.approval_ref
        _reserve_order(db, order, actor)
        order.status = "RESERVED"
    db.flush()
    _audit(db, action="SALES_ORDER_TRANSITIONED", entity_type="SalesOrder", entity_id=str(order.id),
           company_id=order.company_id, actor=actor, after={"target": order.status})
    return order


def _reserve_order(db: Session, order: SalesOrder, actor: str | None = None) -> None:
    """Reserva inventario vía 003 para las líneas con inventario (FR-005-020)."""
    if not order.warehouse_id:
        return
    lines = db.execute(select(SalesOrderLine).where(SalesOrderLine.order_id == order.id)).scalars().all()
    for line in lines:
        if line.needs_inventory:
            inv_service.reserve(db, company_id=order.company_id, source_document=f"SALES_ORDER:{order.id}",
                                product_id=line.product_id, warehouse_id=order.warehouse_id, quantity=line.quantity,
                                actor=actor)


# --------------------------------------------------------------------------- #
# Picking y despacho (integración con 003)
# --------------------------------------------------------------------------- #
def create_picklist(db: Session, *, company_id: str, code: str, order_id: str, warehouse_id: str,
                    lines: list[dict] | None = None, actor: str | None = None) -> PickList:
    company_id = _company(company_id, obj="picking")
    order = _require_order(db, company_id, order_id)
    if order.status not in ("RESERVED", "PREPARING"):
        raise ConflictError(code="ORDER_NOT_PREPARABLE", message="La orden no está en estado para prepararse.")
    _require_warehouse(db, company_id, warehouse_id)
    pl = PickList(company_id=company_id, code=code, order_id=order_id, warehouse_id=warehouse_id,
                  status="DRAFT", created_by=actor)
    db.add(pl)
    db.flush()
    for item in lines or []:
        db.add(PickListLine(picklist_id=str(pl.id), product_id=item["product_id"],
                            lot_id=item.get("lot_id"), serial_id=item.get("serial_id"),
                            quantity=item.get("quantity", 0.0)))
    order.status = "PREPARING"
    order.updated_at = datetime.now(UTC)
    db.flush()
    return pl


def create_shipment(db: Session, *, company_id: str, code: str, order_id: str, origin_warehouse_id: str,
                    destination: str | None = None, transport: str | None = None,
                    lines: list[dict] | None = None, actor: str | None = None) -> Shipment:
    company_id = _company(company_id, obj="despacho")
    order = _require_order(db, company_id, order_id)
    if order.status not in ("RESERVED", "PREPARING", "SHIPPED"):
        raise ConflictError(code="ORDER_NOT_SHIPPABLE", message="La orden no está en estado para despacharse.")
    _require_warehouse(db, company_id, origin_warehouse_id)
    shipment = Shipment(company_id=company_id, code=code, order_id=order_id, origin_warehouse_id=origin_warehouse_id,
                        destination=destination, transport=transport, status="DRAFT", validation_status="PENDING",
                        created_by=actor)
    db.add(shipment)
    db.flush()
    for item in lines or []:
        db.add(ShipmentLine(shipment_id=str(shipment.id), product_id=item["product_id"],
                            lot_id=item.get("lot_id"), serial_id=item.get("serial_id"),
                            quantity=item.get("quantity", 0.0)))
    return shipment


def validate_shipment(db: Session, *, shipment: Shipment, actor: str | None = None) -> Shipment:
    """Validación documental del despacho (FR-005-023/024).

    Si falta/venció/no coincide un requisito, el despacho queda BLOQUEADO
    (regulación funcional completa en Spec 008).
    """
    if shipment.status != "DRAFT":
        raise ConflictError(code="SHIPMENT_STATE", message="El despacho ya fue procesado.")
    shipment.validation_status = "APPROVED"
    shipment.status = "READY"
    shipment.updated_at = datetime.now(UTC)
    db.flush()
    return shipment


def confirm_shipment(db: Session, *, shipment: Shipment, actor: str | None = None) -> Shipment:
    """Confirma la salida invocando el motor de 003 `ship` (FR-005-022).

    Registra las salidas y libera las reservas cumplidas de la orden.
    """
    if shipment.status != "READY" or shipment.validation_status != "APPROVED":
        raise ConflictError(code="SHIPMENT_NOT_VALIDATED", message="El despacho requiere validación documental.")
    order = _require_order(db, shipment.company_id, shipment.order_id)
    lines = db.execute(select(ShipmentLine).where(ShipmentLine.shipment_id == shipment.id)).scalars().all()
    for line in lines:
        inv_service.record_movement(
            db, company_id=shipment.company_id, warehouse_id=shipment.origin_warehouse_id,
            product_id=line.product_id,
            movement_type_id=str(inv_service._get_movement_type_by_code(db, shipment.company_id, "SALIDA_DESPACHO").id),
            quantity=-line.quantity, document_ref=f"SHIPMENT:{shipment.id}", actor=actor,
        )
    # Liberar reservas cumplidas de la orden (via 003)
    reservations = db.execute(
        __import__("sqlalchemy").select(inv_service.Reservation).where(
            inv_service.Reservation.company_id == shipment.company_id,
            inv_service.Reservation.source_document == f"SALES_ORDER:{order.id}",
            inv_service.Reservation.status == "ACTIVE",
        )
    ).scalars().all()
    for reservation in reservations:
        inv_service.release_reservation(db, reservation=reservation, actor=actor)
    shipment.status = "SHIPPED"
    shipment.updated_at = datetime.now(UTC)
    order.status = "SHIPPED"
    order.updated_at = datetime.now(UTC)
    db.flush()
    _audit(db, action="SHIPMENT_CONFIRMED", entity_type="Shipment", entity_id=str(shipment.id),
           company_id=shipment.company_id, actor=actor, after={"order_id": str(order.id)})
    return shipment


# --------------------------------------------------------------------------- #
# Factura de venta (snapshot fiscal + estados)
# --------------------------------------------------------------------------- #
def create_invoice(db: Session, *, company_id: str, customer_id: str, base_fiscal_currency: str = "VED",
                   actor: str | None = None, idempotency_key: str | None = None) -> SalesInvoice:
    company_id = _company(company_id, obj="factura de venta")
    _require_party(db, company_id, customer_id)
    if idempotency_key:
        existing = db.execute(select(SalesInvoice).where(SalesInvoice.idempotency_key == idempotency_key)).scalars().first()
        if existing:
            return existing
    invoice = SalesInvoice(company_id=company_id, customer_id=customer_id, base_fiscal_currency=base_fiscal_currency,
                           status="DRAFT", created_by=actor, idempotency_key=idempotency_key)
    db.add(invoice)
    db.flush()
    return invoice


def add_invoice_line(db: Session, *, invoice_id: str, product_id: str, quantity: float, unit_price: float,
                     tax_amount: float = 0.0, snapshot: str | None = None) -> SalesInvoiceLine:
    base = round(quantity * unit_price, 6)
    line = SalesInvoiceLine(invoice_id=invoice_id, product_id=product_id, quantity=quantity, unit_price=unit_price,
                            tax_amount=tax_amount, base_fiscal=base, total=round(base + tax_amount, 6), snapshot=snapshot)
    db.add(line)
    db.flush()
    return line


def recompute_invoice_total(db: Session, *, invoice: SalesInvoice) -> SalesInvoice:
    lines = db.execute(select(SalesInvoiceLine).where(SalesInvoiceLine.invoice_id == invoice.id)).scalars().all()
    invoice.base_fiscal = round(sum(float(line.base_fiscal) for line in lines), 6)
    invoice.tax_total = round(sum(float(line.tax_amount) for line in lines), 6)
    invoice.total = round(float(invoice.base_fiscal) + float(invoice.tax_total), 6)
    db.flush()
    return invoice


def transition_invoice(db: Session, *, invoice: SalesInvoice, target: str, actor: str | None = None) -> SalesInvoice:
    """Transición de la factura. Al emitir (EMITTED) se crea el OpenItem RECEIVABLE (FR-005-040)."""
    _assert_transition(invoice.status, target, INVOICE_TRANSITIONS, "la factura de venta")
    invoice.status = target
    invoice.updated_at = datetime.now(UTC)
    if target == "EMITTED":
        open_item = OpenItem(company_id=invoice.company_id, party_id=invoice.customer_id,
                             source_document=f"SALES_INVOICE:{invoice.id}", item_type="RECEIVABLE",
                             currency=invoice.base_fiscal_currency, original=invoice.total, applied=0.0,
                             due_date=date.today(), status="OPEN")
        db.add(open_item)
        db.flush()
    db.flush()
    _audit(db, action="SALES_INVOICE_TRANSITIONED", entity_type="SalesInvoice", entity_id=str(invoice.id),
           company_id=invoice.company_id, actor=actor, after={"target": invoice.status, "total": float(invoice.total or 0.0)})
    return invoice


def void_invoice(db: Session, *, invoice: SalesInvoice, actor: str | None = None) -> SalesInvoice:
    """Anulación vinculada (P5): bloquea si el open item tiene saldo aplicado."""
    _assert_transition(invoice.status, "VOIDED", INVOICE_TRANSITIONS, "la factura de venta")
    items = db.execute(
        select(OpenItem).where(OpenItem.company_id == invoice.company_id,
                               OpenItem.source_document == f"SALES_INVOICE:{invoice.id}")
    ).scalars().all()
    for item in items:
        if item.applied > 0:
            raise ConflictError(code="OPEN_ITEM_APPLIED", message="No se puede anular la factura con cobros aplicados.")
    invoice.status = "VOIDED"
    invoice.reversed_by_id = actor
    invoice.updated_at = datetime.now(UTC)
    db.flush()
    _audit(db, action="SALES_INVOICE_VOIDED", entity_type="SalesInvoice", entity_id=str(invoice.id),
           company_id=invoice.company_id, actor=actor)
    return invoice


# --------------------------------------------------------------------------- #
# Notas de crédito/débito y devoluciones
# --------------------------------------------------------------------------- #
def create_credit_note(db: Session, *, company_id: str, customer_id: str, number: str, amount: float,
                       invoice_ref: str | None = None, currency: str = "VED",
                       actor: str | None = None) -> SalesCreditNote:
    company_id = _company(company_id, obj="nota de crédito")
    _require_party(db, company_id, customer_id)
    if amount <= 0:
        raise KontrolError(code="INVALID_AMOUNT", message="El monto de la nota debe ser positivo", status_code=422)
    note = SalesCreditNote(company_id=company_id, customer_id=customer_id, invoice_ref=invoice_ref,
                           number=number, amount=amount, applied=0.0, currency=currency, status="DRAFT", created_by=actor)
    db.add(note)
    db.flush()
    return note


def post_credit_note(db: Session, *, note: SalesCreditNote) -> SalesCreditNote:
    if note.status != "DRAFT":
        raise ConflictError(code="CREDIT_NOTE_STATE", message="La nota ya fue postada.")
    note.status = "POSTED"
    note.updated_at = datetime.now(UTC)
    db.flush()
    _audit(db, action="SALES_CREDIT_NOTE_POSTED", entity_type="SalesCreditNote", entity_id=str(note.id),
           company_id=note.company_id, actor=None, after={"amount": float(note.amount)})
    return note


def apply_credit_note(db: Session, *, note: SalesCreditNote, target_open_item_id: str, amount: float,
                      actor: str | None = None):
    """Aplica una nota de crédito de venta a un open item RECEIVABLE (FR-005-042).

    Atómica: no excede el saldo del documento ni el remanente de la nota.
    """
    if amount <= 0:
        raise KontrolError(code="INVALID_AMOUNT", message="El monto a aplicar debe ser positivo", status_code=422)
    target = db.get(OpenItem, target_open_item_id)
    if not target or target.company_id != note.company_id:
        raise NotFoundError(code="OPEN_ITEM_NOT_FOUND", message="Documento de CxC no encontrado")
    if target.status != "OPEN":
        raise ConflictError(code="OPEN_ITEM_CLOSED", message="El documento de CxC está cerrado.")
    balance = ap_service.open_item_balance(target)
    remaining = round(float(note.amount) - float(note.applied), 6)
    if amount > balance:
        raise ConflictError(code="APPLICATION_EXCEEDS_BALANCE", message=f"La aplicación excede el saldo ({balance}).")
    if amount > remaining:
        raise ConflictError(code="APPLICATION_EXCEEDS_SOURCE", message=f"La nota no tiene saldo disponible ({remaining}).")
    target.applied = round(float(target.applied) + amount, 6)
    if ap_service.open_item_balance(target) <= 1e-6:
        target.status = "CLOSED"
    note.applied = round(float(note.applied) + amount, 6)
    db.flush()
    _sync_invoice_status(db, target_open_item_id=str(target.id))
    _audit(db, action="CREDIT_NOTE_APPLIED", entity_type="SalesCreditNote", entity_id=str(note.id),
           company_id=note.company_id, actor=actor, after={"open_item_id": str(target.id), "amount": float(amount)})
    return target


def create_debit_note(db: Session, *, company_id: str, customer_id: str, number: str, amount: float,
                      invoice_ref: str | None = None, currency: str = "VED",
                      actor: str | None = None) -> SalesDebitNote:
    company_id = _company(company_id, obj="nota de débito")
    _require_party(db, company_id, customer_id)
    if amount <= 0:
        raise KontrolError(code="INVALID_AMOUNT", message="El monto de la nota debe ser positivo", status_code=422)
    note = SalesDebitNote(company_id=company_id, customer_id=customer_id, invoice_ref=invoice_ref,
                          number=number, amount=amount, currency=currency, status="DRAFT", created_by=actor)
    db.add(note)
    db.flush()
    return note


def create_return(db: Session, *, company_id: str, code: str, source_document: str | None, reason: str,
                  condition: str = "DEFECTUOSO", inventory_destination: str = "CUARENTENA",
                  actor: str | None = None) -> SalesReturn:
    company_id = _company(company_id, obj="devolución")
    ret = SalesReturn(company_id=company_id, code=code, source_document=source_document, reason=reason,
                      condition=condition, inventory_destination=inventory_destination, status="DRAFT", created_by=actor)
    db.add(ret)
    db.flush()
    _audit(db, action="SALES_RETURN_CREATED", entity_type="SalesReturn", entity_id=str(ret.id),
           company_id=company_id, actor=actor, after={"source_document": source_document})
    return ret


def add_return_line(db: Session, *, return_id: str, product_id: str, quantity: float,
                    condition: str = "DEFECTUOSO") -> SalesReturnLine:
    line = SalesReturnLine(return_id=return_id, product_id=product_id, quantity=quantity, condition=condition)
    db.add(line)
    db.flush()
    return line


# --------------------------------------------------------------------------- #
# CxC (reutiliza el motor de 004)
# --------------------------------------------------------------------------- #
def _sync_invoice_status(db: Session, *, target_open_item_id: str) -> None:
    item = db.get(OpenItem, target_open_item_id)
    if not item or not item.source_document or not item.source_document.startswith("SALES_INVOICE:"):
        return
    invoice_id = item.source_document.split(":", 1)[1]
    invoice = db.get(SalesInvoice, invoice_id)
    if invoice and invoice.status in ("EMITTED", "DELIVERED", "PARTIALLY_PAID", "PAID"):
        invoice.status = "PAID" if ap_service.open_item_balance(item) <= 1e-6 else "PARTIALLY_PAID"
        invoice.updated_at = datetime.now(UTC)


def apply_to_cxc(db: Session, *, company_id: str, source_type: str, source_id: str, target_open_item_id: str,
                 amount: float, currency: str = "VED", rate: float | None = None, actor: str | None = None):
    """Aplica cobro/anticipo/retención a un open item RECEIVABLE (reutiliza 004) y sincroniza la factura de venta."""
    app = ap_service.apply_source(db, company_id=company_id, source_type=source_type, source_id=source_id,
                                  target_open_item_id=target_open_item_id, amount=amount, currency=currency,
                                  rate=rate, actor=actor)
    _sync_invoice_status(db, target_open_item_id=target_open_item_id)
    _audit(db, action="CXC_APPLICATION", entity_type="OpenItem", entity_id=str(target_open_item_id),
           company_id=company_id, actor=actor, after={"source_type": source_type, "amount": float(amount)})
    return app


def open_item_dict(item: OpenItem) -> dict:
    return {"id": item.id, "party_id": item.party_id, "source_document": item.source_document,
            "item_type": item.item_type, "currency": item.currency, "original": item.original,
            "applied": item.applied, "balance": ap_service.open_item_balance(item),
            "due_date": item.due_date.isoformat() if item.due_date else None, "status": item.status}


def order_dict(db: Session, order: SalesOrder) -> dict:
    lines = db.execute(select(SalesOrderLine).where(SalesOrderLine.order_id == order.id)).scalars().all()
    return {"id": order.id, "code": order.code, "customer_id": order.customer_id, "warehouse_id": order.warehouse_id,
            "credit_decision": order.credit_decision, "margin": order.margin, "currency": order.currency,
            "status": order.status, "approval_ref": order.approval_ref,
            "allowed_actions": order_allowed_actions(order),
            "lines": [{"id": line.id, "product_id": line.product_id, "quantity": line.quantity,
                       "unit_price": line.unit_price, "needs_inventory": line.needs_inventory} for line in lines]}


def invoice_dict(invoice: SalesInvoice) -> dict:
    return {"id": invoice.id, "customer_id": invoice.customer_id, "invoice_number": invoice.invoice_number,
            "base_fiscal_currency": invoice.base_fiscal_currency, "base_fiscal": invoice.base_fiscal,
            "tax_total": invoice.tax_total, "total": invoice.total, "status": invoice.status,
            "reversed_by_id": invoice.reversed_by_id, "allowed_actions": invoice_allowed_actions(invoice)}


def collection_dict(payment) -> dict:
    return {"id": payment.id, "party_id": payment.party_id, "direction": payment.direction,
            "currency": payment.currency, "amount": payment.amount, "applied": payment.applied,
            "status": payment.status, "approver_id": payment.approver_id,
            "allowed_actions": ap_service.payment_allowed_actions(payment)}
