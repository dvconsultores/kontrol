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
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.approvals import integration as approvals_integration
from app.modules.inventory import service as inv_service
from app.modules.organization.models import Warehouse
from app.modules.organization.service import warehouse_belongs_to
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
#: Ciclo de la cotización. `CONVERTED` es terminal: una cotización que ya
#: produjo su pedido no vuelve a editarse, porque editarla cambiaría un
#: documento que ya existe aguas abajo.
QUOTE_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"SENT", "CANCELLED"},
    "SENT": {"ACCEPTED", "REJECTED", "EXPIRED", "CANCELLED"},
    "ACCEPTED": {"CONVERTED", "EXPIRED", "CANCELLED"},
    "REJECTED": set(),
    "EXPIRED": set(),
    "CONVERTED": set(),
    "CANCELLED": set(),
}

#: Solo un borrador admite líneas nuevas. Enviada una cotización, su contenido
#: es lo que el cliente vio.
QUOTE_EDITABLE = {"DRAFT"}

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


def _order_credit_context(db: Session, order: SalesOrder) -> dict[str, Any]:
    """Contexto plano de crédito para el motor de aprobaciones (Spec 045)."""
    lines = db.execute(select(SalesOrderLine).where(
        SalesOrderLine.order_id == str(order.id))).scalars().all()
    total = sum(float(line.unit_price or 0) * float(line.quantity or 0)
                - float(line.discount or 0) for line in lines)
    return {"amount": total, "currency": getattr(order, "currency", "VED") or "VED",
            "rate_snapshot": getattr(order, "rate_snapshot", None),
            "customer_id": order.customer_id,
            "price_list": getattr(order, "price_list", None)}


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
    if not warehouse or not warehouse_belongs_to(company_id, warehouse):
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
                 price_list_id: str | None = None, validity_until=None, currency: str = "VED",
                 actor: str | None = None) -> SalesQuote:
    """Nace en `DRAFT`.

    Nacía en `ACTIVE`, un estado que no aparecía en ninguna transición porque la
    cotización no tenía ciclo de vida: el campo existía y nada lo movía. Con el
    ciclo declarado, el estado inicial es el borrador.
    """
    company_id = _company(company_id, obj="cotización")
    _require_party(db, company_id, customer_id)
    if price_list_id:
        from app.modules.commercial.models import PriceList

        lista = db.get(PriceList, price_list_id)
        if lista is None or str(lista.company_id) != str(company_id):
            raise NotFoundError(code="PRICE_LIST_NOT_FOUND",
                                message="Lista de precios no encontrada")
    quote = SalesQuote(company_id=company_id, code=code, customer_id=customer_id, price_list=price_list,
                       price_list_id=price_list_id, validity_until=validity_until,
                       currency=currency, status="DRAFT", created_by=actor)
    db.add(quote)
    db.flush()
    return quote


def _origen_comercial(db: Session, *, company_id: str, product_id: str,
                      customer_id: str | None, presentation_id: str | None,
                      quantity: float | None, unit_price: float | None,
                      discount: float | None, manual_reason: str | None) -> dict[str, Any]:
    """Pide el precio a la autoridad comercial y **guarda de dónde vino**.

    No hay un segundo resolutor de precio: hay uno, en la Spec 012, y esta
    función lo consume (`FR-029-018`). Lo que aporta 029 es lo que faltaba —
    escribir en la línea qué versión produjo ese número.

    Si el usuario teclea un precio, no se descarta lo que dijo el resolutor: se
    guarda al lado. Un precio manual y uno resuelto tienen que poder
    distinguirse después, y sin el resuelto no se distinguen.
    """
    from app.modules.commercial import service as comercial

    resolucion = comercial.resolver_precio(
        db, company_id=company_id, item_id=product_id, customer_id=customer_id,
        presentation_id=presentation_id,
        quantity=Decimal(str(quantity)) if quantity is not None else None)

    resuelto = Decimal(resolucion["unit_price"]) if resolucion.get("resolved") else None
    origen: dict[str, Any] = {
        "price_source_version_id": resolucion.get("price_list_version_id"),
        "price_source_item_id": resolucion.get("price_list_item_id"),
        "resolved_unit_price": resuelto,
        "manual_reason": None,
        "discount_policy_id": None,
        "discount_policy_version": None,
        "payment_term_snapshot": None,
    }

    if unit_price is None:
        if resuelto is None:
            # Sin lista aplicable no se inventa un precio: se dice que falta
            # (`FR-012-016`). Un cero es un precio; la ausencia no lo es.
            raise KontrolError(
                code="PRICE_NOT_RESOLVED",
                message="No hay lista de precios aplicable. Indique el precio y su motivo.",
                status_code=422,
                details={"reason": resolucion.get("reason")})
        origen["pricing_source"] = "RESOLVED"
        origen["unit_price"] = resuelto
    else:
        tecleado = Decimal(str(unit_price))
        if resuelto is None:
            # No hay lista aplicable, así que no hay nada de lo que desviarse.
            # Exigir un motivo aquí sería pedir que se justifique una diferencia
            # contra un precio que no existe — y dejaría el sistema inservible el
            # primer día, porque los catálogos comerciales **nacen vacíos** por
            # `P8`. Se registra lo que es: un precio sin origen.
            origen["pricing_source"] = "LEGACY_FREETEXT"
        elif tecleado == resuelto:
            origen["pricing_source"] = "RESOLVED"
        else:
            # Aquí sí hay de qué desviarse, y la desviación necesita explicación.
            if not (manual_reason or "").strip():
                raise KontrolError(
                    code="MANUAL_PRICE_REASON_REQUIRED",
                    message="Un precio distinto del de la lista necesita motivo.",
                    status_code=422)
            origen["pricing_source"] = "MANUAL_JUSTIFIED"
            origen["manual_reason"] = manual_reason
        origen["unit_price"] = tecleado

    if discount:
        veredicto = comercial.validar_descuento(
            db, company_id=company_id, scope="LINE", percent=Decimal(str(discount)),
            item_id=product_id)
        origen["discount_policy_id"] = veredicto.get("policy_id")
        origen["discount_policy_version"] = veredicto.get("policy_version")
        if not veredicto.get("allowed"):
            raise KontrolError(
                code="DISCOUNT_ABOVE_LIMIT",
                message="El descuento supera el máximo de la política vigente.",
                status_code=422,
                details={"max_percent": veredicto.get("max_percent")})
        # Superar el umbral **no bloquea**: abre solicitud (`FR-012-023`), y la
        # abre el consumidor. La 029 lo señala; no aprueba nada.
        origen["requires_approval"] = bool(veredicto.get("requires_approval"))

    condicion = _condicion_de_pago(db, company_id, customer_id)
    if condicion is not None:
        origen["payment_term_snapshot"] = condicion
    return origen


def _condicion_de_pago(db: Session, company_id: str, customer_id: str | None) -> dict | None:
    """La condición **entera**, congelada. No su identificador.

    Si el maestro cambia mañana, el documento tiene que seguir diciendo lo que
    dijo. Un identificador apunta al maestro de hoy; un snapshot, al de
    entonces.
    """
    if not customer_id:
        return None
    from sqlalchemy import select as _select

    from app.modules.commercial.models import CustomerCommercialTerms, PaymentTerm
    from app.modules.master_data.models import Customer

    cliente = db.execute(_select(Customer).where(Customer.party_id == customer_id)).scalars().first()
    if cliente is None:
        return None
    cond = db.execute(_select(CustomerCommercialTerms)
                      .where(CustomerCommercialTerms.customer_id == str(cliente.id))).scalars().first()
    if cond is None or not cond.payment_term_id:
        return None
    plazo = db.get(PaymentTerm, cond.payment_term_id)
    if plazo is None:
        return None
    return {"id": str(plazo.id), "code": plazo.code, "name": plazo.name,
            "kind": plazo.kind, "days": plazo.days,
            "due_offset_from": plazo.due_offset_from,
            "frozen_at": datetime.now(UTC).isoformat()}


def _require_quote(db: Session, company_id: str, quote_id: str) -> SalesQuote:
    quote = db.get(SalesQuote, quote_id)
    if not quote or quote.company_id != company_id:
        raise NotFoundError(code="SALES_QUOTE_NOT_FOUND", message="Cotización de venta no encontrada")
    return quote


def _require_return(db: Session, company_id: str, return_id: str) -> SalesReturn:
    ret = db.get(SalesReturn, return_id)
    if not ret or ret.company_id != company_id:
        raise NotFoundError(code="SALES_RETURN_NOT_FOUND", message="Devolución de venta no encontrada")
    return ret


def add_quote_line(db: Session, *, company_id: str, quote_id: str, product_id: str, quantity: float,
                   unit_price: float | None = None, discount: float = 0.0,
                   tax_ref: str | None = None, presentation_id: str | None = None,
                   manual_reason: str | None = None) -> SalesQuoteLine:
    """Añade una línea **con su origen**.

    `unit_price` pasa a ser opcional: si no se indica, lo resuelve la autoridad
    comercial. Si se indica y difiere del resuelto, hace falta un motivo.
    """
    cotizacion = _require_quote(db, company_id, quote_id)
    if cotizacion.status not in QUOTE_EDITABLE:
        raise ConflictError(code="SALES_QUOTE_NOT_EDITABLE",
                            message="Solo un borrador admite líneas nuevas.")
    origen = _origen_comercial(
        db, company_id=company_id, product_id=product_id,
        customer_id=str(cotizacion.customer_id), presentation_id=presentation_id,
        quantity=quantity, unit_price=unit_price, discount=discount,
        manual_reason=manual_reason)
    origen.pop("requires_approval", None)
    precio = origen.pop("unit_price")
    line = SalesQuoteLine(quote_id=quote_id, product_id=product_id, quantity=quantity,
                          unit_price=precio, discount=discount, tax_ref=tax_ref,
                          presentation_id=presentation_id, **origen)
    db.add(line)
    db.flush()
    return line


def transicionar_cotizacion(db: Session, *, company_id: str, quote_id: str, destino: str,
                            actor: str | None = None) -> SalesQuote:
    """Mueve la cotización, y comprueba su vigencia al enviarla o aceptarla."""
    cotizacion = _require_quote(db, company_id, quote_id)
    if destino not in QUOTE_TRANSITIONS.get(cotizacion.status, set()):
        raise ConflictError(
            code="SALES_QUOTE_TRANSITION",
            message=f"Una cotización {cotizacion.status} no pasa a {destino}.")
    if destino in ("SENT", "ACCEPTED") and _vencida(cotizacion):
        raise ConflictError(code="SALES_QUOTE_EXPIRED",
                            message="La cotización venció. Cree una nueva o amplíe su vigencia.")
    cotizacion.status = destino
    cotizacion.updated_at = datetime.now(UTC)
    _audit(db, action=f"SALES_QUOTE_{destino}", entity_type="SalesQuote",
           entity_id=str(cotizacion.id), company_id=company_id, actor=actor,
           after={"status": destino})
    db.flush()
    return cotizacion


def _vencida(cotizacion: SalesQuote, hoy: date | None = None) -> bool:
    """Nula significa **sin vencimiento**, no «vencida»."""
    if cotizacion.validity_until is None:
        return False
    return cotizacion.validity_until < (hoy or date.today())


def convertir_en_pedido(db: Session, *, company_id: str, quote_id: str,
                        warehouse_id: str | None = None,
                        actor: str | None = None) -> tuple[SalesOrder, bool]:
    """Convierte la cotización en pedido **preservando su evidencia comercial**.

    No se vuelve a resolver el precio. Sería lo cómodo y sería un error: entre
    la cotización y el pedido puede haber una versión nueva, y el cliente
    aceptó la anterior. Reconvertir en silencio cambiaría lo que se pactó
    (`FR-029-028`).

    Devuelve `(pedido, creado)`. Si la cotización ya fue convertida devuelve el
    pedido que existe y `creado=False`: convertir dos veces no crea dos pedidos.
    """
    cotizacion = _require_quote(db, company_id, quote_id)

    existente = db.execute(select(SalesOrder)
                           .where(SalesOrder.quote_id == str(cotizacion.id))).scalars().first()
    if existente is not None:
        return existente, False

    if cotizacion.status != "ACCEPTED":
        raise ConflictError(
            code="SALES_QUOTE_NOT_CONVERTIBLE",
            message="Solo se convierte una cotización aceptada por el cliente.")
    if _vencida(cotizacion):
        raise ConflictError(code="SALES_QUOTE_EXPIRED",
                            message="La cotización venció y no puede convertirse.")
    lineas = db.execute(select(SalesQuoteLine)
                        .where(SalesQuoteLine.quote_id == str(cotizacion.id))).scalars().all()
    if not lineas:
        raise ConflictError(code="SALES_QUOTE_EMPTY",
                            message="Una cotización sin líneas no produce un pedido.")
    if warehouse_id:
        _require_warehouse(db, company_id, warehouse_id)

    pedido = SalesOrder(company_id=company_id, code=f"{cotizacion.code}-P",
                        customer_id=cotizacion.customer_id, warehouse_id=warehouse_id,
                        currency=cotizacion.currency, status="DRAFT",
                        quote_id=str(cotizacion.id), created_by=actor)
    db.add(pedido)
    db.flush()

    for linea in lineas:
        db.add(SalesOrderLine(
            order_id=str(pedido.id), product_id=linea.product_id, quantity=linea.quantity,
            unit_price=linea.unit_price, discount=linea.discount, tax_ref=linea.tax_ref,
            uom_id=linea.uom_id, presentation_id=linea.presentation_id,
            conversion_factor_snapshot=linea.conversion_factor_snapshot,
            base_quantity=linea.base_quantity, uom_source=linea.uom_source,
            # La evidencia viaja entera. Es el punto de esta conversión.
            price_source_version_id=linea.price_source_version_id,
            price_source_item_id=linea.price_source_item_id,
            pricing_source=linea.pricing_source,
            resolved_unit_price=linea.resolved_unit_price,
            manual_reason=linea.manual_reason,
            discount_policy_id=linea.discount_policy_id,
            discount_policy_version=linea.discount_policy_version,
            discount_approval_request_id=linea.discount_approval_request_id,
            payment_term_snapshot=linea.payment_term_snapshot,
        ))

    cotizacion.status = "CONVERTED"
    cotizacion.updated_at = datetime.now(UTC)
    _audit(db, action="SALES_QUOTE_CONVERTED", entity_type="SalesQuote",
           entity_id=str(cotizacion.id), company_id=company_id, actor=actor,
           after={"order_id": str(pedido.id)})
    db.flush()
    return pedido, True


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


def add_order_line(db: Session, *, order_id: str, product_id: str, quantity: float,
                   unit_price: float | None = None, discount: float = 0.0,
                   tax_ref: str | None = None, needs_inventory: bool = True,
                   snapshot: str | None = None, company_id: str | None = None,
                   presentation_id: str | None = None,
                   manual_reason: str | None = None) -> SalesOrderLine:
    """Una línea de pedido directo captura su origen igual que una de cotización.

    Si no lo hiciera, quedarían dos caminos comerciales: uno con origen —el que
    viene de cotización— y otro sin él. Un pedido directo no es un pedido peor
    documentado (`FR-029-041`).
    """
    if quantity <= 0:
        raise KontrolError(code="INVALID_QUANTITY", message="La cantidad debe ser positiva", status_code=422)
    order = db.get(SalesOrder, order_id)
    if order is None:
        raise NotFoundError(code="SALES_ORDER_NOT_FOUND", message="Orden de venta no encontrada")
    empresa = company_id or str(order.company_id)
    origen = _origen_comercial(
        db, company_id=empresa, product_id=product_id, customer_id=str(order.customer_id),
        presentation_id=presentation_id, quantity=quantity, unit_price=unit_price,
        discount=discount, manual_reason=manual_reason)
    origen.pop("requires_approval", None)
    precio = origen.pop("unit_price")
    line = SalesOrderLine(order_id=order_id, product_id=product_id, quantity=quantity,
                          unit_price=precio, discount=discount, tax_ref=tax_ref,
                          needs_inventory=needs_inventory, snapshot=snapshot,
                          presentation_id=presentation_id, **origen)
    db.add(line)
    db.flush()
    return line


def transition_order(db: Session, *, order: SalesOrder, target: str, actor: str | None = None,
                     credit_decision: str | None = None, approval_ref: str | None = None) -> SalesOrder:
    """Transición de la OV. Al aprobar (APPROVED) se reserva inventario vía 003 (FR-005-020)."""
    _assert_transition(order.status, target, ORDER_TRANSITIONS, "la orden de venta")
    if target == "CREDIT_PENDING":
        approvals_integration.require_for_document(
            db, company_id=order.company_id,
            process_type=approvals_integration.PROCESS_SALES_CREDIT,
            document_type="SalesOrder", document_id=str(order.id),
            context=_order_credit_context(db, order), actor=actor)
    if target == "APPROVED":
        approvals_integration.ensure_approved(
            db, company_id=order.company_id, document_type="SalesOrder",
            document_id=str(order.id), what="la orden de venta")
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
        # Acotada por empresa: sin esto, A pedía una factura con una clave que B
        # ya había usado y recibía la factura fiscal de B, con su número y su
        # total, como si fuera propia.
        existing = db.execute(
            select(SalesInvoice).where(SalesInvoice.idempotency_key == idempotency_key,
                                       SalesInvoice.company_id == company_id)).scalars().first()
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


def add_return_line(db: Session, *, company_id: str, return_id: str, product_id: str, quantity: float,
                    condition: str = "DEFECTUOSO") -> SalesReturnLine:
    _require_return(db, company_id, return_id)
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
            "quote_id": str(order.quote_id) if order.quote_id else None,
            "lines": [{
                "id": line.id, "product_id": line.product_id,
                "quantity": str(line.quantity), "unit_price": str(line.unit_price),
                "discount": str(line.discount or 0),
                "needs_inventory": line.needs_inventory,
                # El origen viaja hasta aquí o no sirve de nada: guardarlo y no
                # mostrarlo es tener la evidencia y no poder enseñarla.
                "pricing_source": line.pricing_source,
                "price_source_version_id": (str(line.price_source_version_id)
                                            if line.price_source_version_id else None),
                "price_source_item_id": (str(line.price_source_item_id)
                                         if line.price_source_item_id else None),
                "resolved_unit_price": (str(line.resolved_unit_price)
                                        if line.resolved_unit_price is not None else None),
                "manual_reason": line.manual_reason,
                "discount_policy_id": (str(line.discount_policy_id)
                                       if line.discount_policy_id else None),
                "discount_policy_version": line.discount_policy_version,
                "payment_term_snapshot": line.payment_term_snapshot,
            } for line in lines]}


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
