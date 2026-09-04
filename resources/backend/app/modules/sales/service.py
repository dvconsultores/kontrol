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

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.approvals import integration as approvals_integration
from app.modules.approvals import service as approvals_service
from app.modules.inventory import service as inv_service
from app.modules.master_data import uom as uom_engine
from app.modules.organization.models import Company, Warehouse
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

#: Máquina del pedido (FR-030-002, ADR-D0-003 v2 R-D0-03-11).
#:
#: La reserva nace en `DRAFT → SUBMITTED`. Sin solicitud de crédito el pedido
#: sigue a `RELEASED` en la misma transacción; con solicitud espera en
#: `SUBMITTED` hasta que la Spec 045 resuelve. `RELEASED` es la entrega a la
#: cola de preparación (031). `CREDIT_PENDING`, `APPROVED` y `RESERVED` dejaron
#: de existir: la migración 0043 los reclasificó.
ORDER_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"SUBMITTED", "CANCELLED"},
    "SUBMITTED": {"RELEASED", "REJECTED", "CANCELLED", "EXPIRED", "DRAFT"},
    "RELEASED": {"PREPARING", "SHIPPED", "CANCELLED", "DRAFT"},
    "PREPARING": {"SHIPPED", "CANCELLED"},
    "SHIPPED": {"CLOSED"},
    "CLOSED": set(),
    "CANCELLED": set(),
    "REJECTED": set(),
    "EXPIRED": set(),
}

#: Estados en los que el pedido tiene (y debe tener) su reserva viva.
ORDER_RESERVED_STATES = frozenset({"SUBMITTED", "RELEASED", "PREPARING"})
#: Estado que habilita la cola de la Spec 031 (IMP-030-053).
ORDER_HANDOFF_STATE = "RELEASED"
#: `RESERVATION TRIGGER = ORDER_CONFIRMATION` — fijo, no configurable (D0-03).
RESERVATION_TRIGGER = "ORDER_CONFIRMATION"

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
    return {"view": True,
            # `submit` se conserva como alias de `confirm` para clientes antiguos.
            "confirm": s == "DRAFT", "submit": s == "DRAFT",
            "release": s == "SUBMITTED", "reject": s == "SUBMITTED",
            "revert": s in ("SUBMITTED", "RELEASED"),
            "cancel": s in ("DRAFT", "SUBMITTED", "RELEASED", "PREPARING"),
            "prepare": s == "RELEASED", "ship": s in ("RELEASED", "PREPARING"),
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
    unidad = _unidad(db, product_id=product_id, presentation_id=presentation_id, quantity=quantity)
    line = SalesQuoteLine(quote_id=quote_id, product_id=product_id, quantity=quantity,
                          unit_price=precio, discount=discount, tax_ref=tax_ref,
                          presentation_id=presentation_id, **unidad, **origen)
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
    if order.status != "DRAFT":
        # Un pedido emitido ya comprometió inventario: una línea añadida por
        # debajo quedaría sin reserva (CD-10). Se revierte a borrador y se
        # reemite (FR-030-020/021).
        raise ConflictError(code="ORDER_NOT_EDITABLE",
                            message="Solo un borrador admite líneas nuevas; revierta el pedido a borrador.")
    empresa = company_id or str(order.company_id)
    origen = _origen_comercial(
        db, company_id=empresa, product_id=product_id, customer_id=str(order.customer_id),
        presentation_id=presentation_id, quantity=quantity, unit_price=unit_price,
        discount=discount, manual_reason=manual_reason)
    origen.pop("requires_approval", None)
    precio = origen.pop("unit_price")
    unidad = _unidad(db, product_id=product_id, presentation_id=presentation_id, quantity=quantity)
    line = SalesOrderLine(order_id=order_id, product_id=product_id, quantity=quantity,
                          unit_price=precio, discount=discount, tax_ref=tax_ref,
                          needs_inventory=needs_inventory, snapshot=snapshot,
                          presentation_id=presentation_id, **unidad, **origen)
    db.add(line)
    db.flush()
    return line


def _unidad(db: Session, *, product_id: str, presentation_id: str | None, quantity: float) -> dict[str, Any]:
    """Semántica de unidad de una línea (Spec 011, R-D0-09-1), capturada al nacer.

    La reserva compara y compromete **cantidad base** (IMP-030-007). Sin
    presentación la cantidad ya está en base y el factor es 1; con presentación
    resuelve la versión vigente y la congela: mañana el maestro puede cambiar y
    la línea seguirá diciendo con qué factor se vendió (IMP-030-008).
    """
    conversion = uom_engine.to_base(db, Decimal(str(quantity)), product_id, presentation_id)
    return {"uom_id": str(conversion.base_uom_id) if conversion.base_uom_id else None, "conversion_factor_snapshot": conversion.factor,
            "base_quantity": conversion.base_quantity, "uom_source": uom_engine.SOURCE_CAPTURED}


def _asegurar_unidad(db: Session, line: SalesOrderLine) -> None:
    """Una línea anterior a la Spec 030 no tiene base: se captura al confirmar.

    Es la primera captura, no un recálculo: no había nada que recalcular.
    """
    if line.base_quantity is not None:
        return
    for k, v in _unidad(db, product_id=str(line.product_id), presentation_id=line.presentation_id,
                        quantity=float(line.quantity)).items():
        setattr(line, k, v)


def _lock_order(db: Session, company_id: str, order_id: str) -> SalesOrder:
    """El pedido bloqueado para la transición: dos confirmaciones simultáneas
    del mismo pedido se serializan aquí, antes de tocar el inventario."""
    order = db.execute(select(SalesOrder).where(SalesOrder.id == order_id).with_for_update()).scalars().first()
    if order is None or str(order.company_id) != str(company_id):
        raise NotFoundError(code="SALES_ORDER_NOT_FOUND", message="Orden de venta no encontrada")
    return order


def _motivo(reason: str | None) -> str:
    motivo = (reason or "").strip()
    if not motivo:
        raise KontrolError(code="REASON_REQUIRED", message="Debe indicar el motivo.", status_code=422)
    return motivo


def _lineas_de_pedido(db: Session, order_id: str) -> list[SalesOrderLine]:
    return list(db.execute(select(SalesOrderLine).where(SalesOrderLine.order_id == order_id)
                           .order_by(SalesOrderLine.created_at, SalesOrderLine.id)).scalars().all())


def _ttl_de_reserva(db: Session, company_id: str) -> int | None:
    empresa = db.get(Company, company_id)
    return empresa.reservation_ttl_days if empresa is not None else None


def _cancelar_solicitud_de_credito(db: Session, order: SalesOrder, actor: str | None, reason: str) -> bool:
    """Si 045 tiene una solicitud viva para el pedido, la cancela con el motivo.

    Una aprobación no sobrevive al documento que la pidió (IMP-030-047): al
    cancelar, rechazar, revertir o expirar el pedido, la solicitud se cierra en
    el motor, no se deja huérfana.
    """
    estado = approvals_service.status(db, company_id=str(order.company_id), document_type="SalesOrder",
                                      document_id=str(order.id))
    actual = estado.get("current")
    if actual and estado.get("blocks_advance"):
        approvals_service.cancel(db, company_id=str(order.company_id), request_id=actual["id"],
                                 actor_id=actor or "system", reason=reason)
        return True
    return False


def _liberar_reservas(db: Session, order: SalesOrder, *, actor: str | None, reason: str) -> int:
    """Libera todo lo ACTIVE del pedido. Idempotente: lo ya cerrado no resta."""
    liberadas = 0
    for reserva in inv_service.order_reservations(db, company_id=str(order.company_id), order_id=str(order.id)):
        if inv_service.release_if_active(db, reservation=reserva, actor=actor, reason=reason):
            liberadas += 1
    return liberadas


def _a_released(db: Session, order: SalesOrder, actor: str | None) -> None:
    """`→ RELEASED`: la reserva se hace firme y el pedido entra en la cola de 031."""
    _assert_transition(order.status, "RELEASED", ORDER_TRANSITIONS, "el pedido")
    ahora = datetime.now(UTC)
    for reserva in inv_service.order_reservations(db, company_id=str(order.company_id), order_id=str(order.id)):
        reserva.expires_at = None
    order.status = "RELEASED"
    order.released_at = ahora
    order.updated_at = ahora
    db.flush()
    _audit(db, action="SALES_ORDER_TRANSITIONED", entity_type="SalesOrder", entity_id=str(order.id),
           company_id=order.company_id, actor=actor, after={"target": "RELEASED"})


def confirmar_pedido(db: Session, *, company_id: str, order_id: str, actor: str | None = None) -> SalesOrder:
    """`DRAFT → SUBMITTED` con reserva: **el** disparador (ADR-D0-003 v2).

    Todo o nada: se bloquean los saldos de todas las líneas en orden
    determinista, se comprueba la disponibilidad bajo bloqueo y solo entonces
    se reserva. Si una línea no alcanza, ninguna se reserva y el pedido sigue en
    borrador con el detalle de lo que falta (FR-030-010/011). Después pregunta a
    la Spec 045 si hace falta crédito: sin solicitud, el pedido queda
    `RELEASED` en la misma transacción; con solicitud, espera en `SUBMITTED`.
    """
    order = _lock_order(db, company_id, order_id)
    _assert_transition(order.status, "SUBMITTED", ORDER_TRANSITIONS, "el pedido")
    lineas = _lineas_de_pedido(db, str(order.id))
    if not lineas:
        raise KontrolError(code="ORDER_EMPTY", message="Un pedido sin líneas no se confirma.", status_code=422)
    inventariables = [linea for linea in lineas if linea.needs_inventory]
    ahora = datetime.now(UTC)

    if inventariables:
        if not order.warehouse_id:
            raise KontrolError(code="WAREHOUSE_REQUIRED",
                               message="Indique el almacén antes de confirmar un pedido con inventario.",
                               status_code=422)
        warehouse = _require_warehouse(db, company_id, order.warehouse_id)
        for linea in inventariables:
            _asegurar_unidad(db, linea)
        # Orden determinista de bloqueo (IMP-030-023): producto y luego línea.
        ordenadas = sorted(inventariables, key=lambda linea: (str(linea.product_id), str(linea.id)))
        permite_negativo = inv_service._allow_negative(warehouse)
        faltantes: list[dict[str, Any]] = []
        for linea in ordenadas:
            saldo = inv_service.lock_balance(db, company_id=company_id, warehouse_id=order.warehouse_id,
                                             product_id=str(linea.product_id))
            disponible = inv_service.available_under_lock(db, saldo)
            if Decimal(str(linea.base_quantity)) > disponible and not permite_negativo:
                faltantes.append({"line_id": str(linea.id), "product_id": str(linea.product_id),
                                  "requested_base": str(linea.base_quantity), "available_base": str(disponible)})
        if faltantes:
            raise ConflictError(code="INSUFFICIENT_AVAILABLE",
                                message="No hay disponible suficiente para confirmar el pedido.",
                                details={"lines": faltantes})
        for linea in ordenadas:
            inv_service.reserve(
                db, company_id=company_id, source_document=f"SALES_ORDER:{order.id}",
                product_id=str(linea.product_id), warehouse_id=order.warehouse_id,
                quantity=float(linea.quantity), actor=actor,
                source_type=inv_service.RESERVATION_SOURCE_ORDER, source_order_id=str(order.id),
                source_line_id=str(linea.id), trigger=RESERVATION_TRIGGER,
                uom_id=linea.uom_id, presentation_id=linea.presentation_id,
                conversion_factor_snapshot=linea.conversion_factor_snapshot,
                base_quantity=linea.base_quantity, uom_source=linea.uom_source)

    order.status = "SUBMITTED"
    order.submitted_at = ahora
    order.status_reason = None
    order.updated_at = ahora
    db.flush()
    _audit(db, action="SALES_ORDER_TRANSITIONED", entity_type="SalesOrder", entity_id=str(order.id),
           company_id=order.company_id, actor=actor,
           after={"target": "SUBMITTED", "trigger": RESERVATION_TRIGGER, "reserved_lines": len(inventariables)})

    resultado = approvals_integration.require_for_document(
        db, company_id=company_id, process_type=approvals_integration.PROCESS_SALES_CREDIT,
        document_type="SalesOrder", document_id=str(order.id),
        context=_order_credit_context(db, order), actor=actor)
    if resultado.get("requires_approval"):
        order.approval_ref = str(resultado["request"].id)
        ttl = _ttl_de_reserva(db, company_id)
        if ttl:
            vence = ahora + timedelta(days=int(ttl))
            for reserva in inv_service.order_reservations(db, company_id=company_id, order_id=str(order.id)):
                reserva.expires_at = vence
        db.flush()
        return order
    _a_released(db, order, actor)
    return order


def liberar_pedido(db: Session, *, company_id: str, order_id: str, actor: str | None = None) -> SalesOrder:
    """`SUBMITTED → RELEASED` cuando la Spec 045 resolvió a favor.

    No vuelve a reservar ni recalcula stock (IMP-030-028): la reserva ya existe
    desde la confirmación; aquí solo se hace firme.
    """
    order = _lock_order(db, company_id, order_id)
    _assert_transition(order.status, "RELEASED", ORDER_TRANSITIONS, "el pedido")
    approvals_integration.ensure_approved(db, company_id=company_id, document_type="SalesOrder",
                                          document_id=str(order.id), what="el pedido")
    _a_released(db, order, actor)
    return order


def rechazar_pedido(db: Session, *, company_id: str, order_id: str, actor: str | None = None,
                    reason: str | None = None) -> SalesOrder:
    """`SUBMITTED → REJECTED`: se cierra la solicitud de crédito viva, se libera
    toda la reserva y se registra el motivo. Una sola transacción (IMP-030-033)."""
    order = _lock_order(db, company_id, order_id)
    motivo = _motivo(reason)
    _assert_transition(order.status, "REJECTED", ORDER_TRANSITIONS, "el pedido")
    _cancelar_solicitud_de_credito(db, order, actor, motivo)
    liberadas = _liberar_reservas(db, order, actor=actor, reason="CREDIT_REJECTED")
    ahora = datetime.now(UTC)
    order.status = "REJECTED"
    order.status_reason = motivo
    order.updated_at = ahora
    db.flush()
    _audit(db, action="SALES_ORDER_TRANSITIONED", entity_type="SalesOrder", entity_id=str(order.id),
           company_id=order.company_id, actor=actor, reason=motivo,
           after={"target": "REJECTED", "released_reservations": liberadas})
    return order


def revertir_pedido(db: Session, *, company_id: str, order_id: str, actor: str | None = None,
                    reason: str | None = None) -> SalesOrder:
    """`→ DRAFT`: la única forma de modificar un pedido comprometido (R-D0-03-7).

    Libera **toda** la reserva —sin ajustar diferencias— y cierra la solicitud
    de crédito: al reemitir se reserva desde cero y se vuelve a pedir crédito.
    """
    order = _lock_order(db, company_id, order_id)
    motivo = _motivo(reason)
    _assert_transition(order.status, "DRAFT", ORDER_TRANSITIONS, "el pedido")
    estado_previo = order.status
    _cancelar_solicitud_de_credito(db, order, actor, f"ORDER_REVERTED: {motivo}")
    liberadas = _liberar_reservas(db, order, actor=actor, reason="ORDER_REVERTED")
    ahora = datetime.now(UTC)
    order.status = "DRAFT"
    order.status_reason = motivo
    order.submitted_at = None
    order.released_at = None
    order.approval_ref = None
    order.updated_at = ahora
    db.flush()
    _audit(db, action="SALES_ORDER_REVERTED", entity_type="SalesOrder", entity_id=str(order.id),
           company_id=order.company_id, actor=actor, reason=motivo,
           before={"status": estado_previo}, after={"target": "DRAFT", "released_reservations": liberadas})
    return order


def cancelar_pedido(db: Session, *, company_id: str, order_id: str, actor: str | None = None,
                    reason: str | None = None) -> SalesOrder:
    """`→ CANCELLED` desde cualquier estado vivo. Libera lo ACTIVE, cierra la
    solicitud de crédito y guarda el motivo. Un segundo intento choca con la
    máquina de estados; la liberación es idempotente por sí misma."""
    order = _lock_order(db, company_id, order_id)
    motivo = _motivo(reason)
    _assert_transition(order.status, "CANCELLED", ORDER_TRANSITIONS, "el pedido")
    estado_previo = order.status
    _cancelar_solicitud_de_credito(db, order, actor, f"ORDER_CANCELLED: {motivo}")
    liberadas = _liberar_reservas(db, order, actor=actor, reason="ORDER_CANCELLED")
    ahora = datetime.now(UTC)
    order.status = "CANCELLED"
    order.status_reason = motivo
    order.updated_at = ahora
    db.flush()
    _audit(db, action="SALES_ORDER_TRANSITIONED", entity_type="SalesOrder", entity_id=str(order.id),
           company_id=order.company_id, actor=actor, reason=motivo,
           before={"status": estado_previo}, after={"target": "CANCELLED", "released_reservations": liberadas})
    return order


def expirar_reservas_de_pedidos(db: Session, *, company_id: str, actor: str | None = None,
                                now: datetime | None = None) -> dict[str, int]:
    """Vence las reservas de pedidos con TTL cumplido **y** los pedidos que las
    sostenían (R-D0-03-8): nunca queda un pedido vivo sin reserva.

    Lo ejecuta un operador o, cuando exista, el planificador de la plataforma
    (Spec 047). Idempotente: la segunda pasada no encuentra nada.
    """
    vencidas = inv_service.expire_due_reservations(db, company_id=company_id,
                                                   source_type=inv_service.RESERVATION_SOURCE_ORDER,
                                                   now=now, actor=actor)
    pedidos: dict[str, int] = {}
    for reserva in vencidas:
        if reserva.source_order_id:
            pedidos[reserva.source_order_id] = pedidos.get(reserva.source_order_id, 0) + 1
    expirados = 0
    for order_id in pedidos:
        order = _lock_order(db, company_id, order_id)
        if order.status != "SUBMITTED":
            continue
        _cancelar_solicitud_de_credito(db, order, actor, "EXPIRED")
        for reserva in inv_service.order_reservations(db, company_id=company_id, order_id=str(order.id)):
            inv_service.expire_if_active(db, reservation=reserva, actor=actor)
        order.status = "EXPIRED"
        order.status_reason = "EXPIRED"
        order.updated_at = datetime.now(UTC)
        db.flush()
        _audit(db, action="SALES_ORDER_TRANSITIONED", entity_type="SalesOrder", entity_id=str(order.id),
               company_id=order.company_id, actor=actor, reason="EXPIRED",
               after={"target": "EXPIRED", "expired_reservations": pedidos[order_id]})
        expirados += 1
    return {"expired_reservations": len(vencidas), "expired_orders": expirados}


def politica_de_reserva(db: Session, *, company_id: str) -> dict[str, Any]:
    return {"reservation_trigger": RESERVATION_TRIGGER, "trigger_configurable": False,
            "reservation_ttl_days": _ttl_de_reserva(db, company_id)}


def configurar_reserva(db: Session, *, company_id: str, reservation_ttl_days: int | None,
                       actor: str | None = None) -> dict[str, Any]:
    """Lo único configurable de la política es la vigencia mientras se evalúa el
    crédito (IMP-030-040/041). El disparador no se toca."""
    if reservation_ttl_days is not None and reservation_ttl_days < 1:
        raise KontrolError(code="INVALID_TTL", message="La vigencia debe ser al menos un día o nula.",
                           status_code=422)
    empresa = db.get(Company, company_id)
    if empresa is None:
        raise NotFoundError(code="COMPANY_NOT_FOUND", message="Empresa no encontrada")
    anterior = empresa.reservation_ttl_days
    empresa.reservation_ttl_days = reservation_ttl_days
    db.flush()
    _audit(db, action="COMPANY_RESERVATION_POLICY_CHANGED", entity_type="Company", entity_id=str(empresa.id),
           company_id=company_id, actor=actor,
           before={"reservation_ttl_days": anterior}, after={"reservation_ttl_days": reservation_ttl_days})
    return politica_de_reserva(db, company_id=company_id)


def transition_order(db: Session, *, order: SalesOrder, target: str, actor: str | None = None,
                     credit_decision: str | None = None, approval_ref: str | None = None,
                     reason: str | None = None) -> SalesOrder:
    """Transición genérica (compatibilidad). Los destinos de la Spec 030 delegan
    en sus servicios; `PREPARING`, `SHIPPED` y `CLOSED` se mueven aquí."""
    company_id = str(order.company_id)
    delegadas = {
        "SUBMITTED": lambda: confirmar_pedido(db, company_id=company_id, order_id=str(order.id), actor=actor),
        "RELEASED": lambda: liberar_pedido(db, company_id=company_id, order_id=str(order.id), actor=actor),
        "REJECTED": lambda: rechazar_pedido(db, company_id=company_id, order_id=str(order.id), actor=actor,
                                            reason=reason),
        "DRAFT": lambda: revertir_pedido(db, company_id=company_id, order_id=str(order.id), actor=actor,
                                         reason=reason),
        "CANCELLED": lambda: cancelar_pedido(db, company_id=company_id, order_id=str(order.id), actor=actor,
                                             reason=reason),
    }
    if target in delegadas:
        return delegadas[target]()
    _assert_transition(order.status, target, ORDER_TRANSITIONS, "el pedido")
    order.status = target
    order.updated_at = datetime.now(UTC)
    if credit_decision:
        order.credit_decision = credit_decision
    if approval_ref:
        order.approval_ref = approval_ref
    db.flush()
    _audit(db, action="SALES_ORDER_TRANSITIONED", entity_type="SalesOrder", entity_id=str(order.id),
           company_id=order.company_id, actor=actor, after={"target": order.status})
    return order


# --------------------------------------------------------------------------- #
# Picking y despacho (integración con 003)
# --------------------------------------------------------------------------- #
def create_picklist(db: Session, *, company_id: str, code: str, order_id: str, warehouse_id: str,
                    lines: list[dict] | None = None, actor: str | None = None) -> PickList:
    company_id = _company(company_id, obj="picking")
    order = _require_order(db, company_id, order_id)
    if order.status not in ("RELEASED", "PREPARING"):
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
    if order.status not in ("RELEASED", "PREPARING", "SHIPPED"):
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
    # La salida física **consume** la reserva (R-D0-03-7): `FULFILLED`, no
    # `RELEASED`. Lo que salió no vuelve al disponible.
    for reservation in inv_service.order_reservations(db, company_id=shipment.company_id, order_id=str(order.id)):
        inv_service.fulfill_reservation(db, reservation=reservation, actor=actor)
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


def _reserva_dict(r: Any) -> dict:
    return {"id": str(r.id), "status": r.status, "quantity": str(r.quantity),
            "base_quantity": str(r.base_quantity) if r.base_quantity is not None else None,
            "warehouse_id": r.warehouse_id, "trigger": r.trigger, "oversell": bool(r.oversell),
            "expires_at": r.expires_at.isoformat() if r.expires_at else None,
            "release_reason": r.release_reason}


def orders_dict(db: Session, orders: list[SalesOrder]) -> list[dict]:
    """Serializa varios pedidos con dos consultas, no con dos por pedido.

    `order_dict` necesita líneas y reservas; llamarlo en un bucle sobre una
    página de cien pedidos son doscientas consultas. Aquí se traen de una vez.
    """
    if not orders:
        return []
    ids = [str(o.id) for o in orders]
    empresa = str(orders[0].company_id)
    lineas: dict[str, list[SalesOrderLine]] = {}
    for linea in db.execute(
            select(SalesOrderLine).where(SalesOrderLine.order_id.in_(ids))
            .order_by(SalesOrderLine.created_at, SalesOrderLine.id)).scalars():
        lineas.setdefault(str(linea.order_id), []).append(linea)
    reservas: dict[str, list[Any]] = {}
    for r in inv_service.reservations_for_orders(db, company_id=empresa, order_ids=ids):
        reservas.setdefault(str(r.source_order_id), []).append(r)
    return [order_dict(db, o, lines=lineas.get(str(o.id), []), reservations=reservas.get(str(o.id), []))
            for o in orders]


def order_dict(db: Session, order: SalesOrder, *, lines: list[SalesOrderLine] | None = None,
               reservations: list[Any] | None = None) -> dict:
    if lines is None:
        lines = list(db.execute(
            select(SalesOrderLine).where(SalesOrderLine.order_id == order.id)
            .order_by(SalesOrderLine.created_at, SalesOrderLine.id)).scalars().all())
    if reservations is None:
        reservations = inv_service.order_reservations(
            db, company_id=str(order.company_id), order_id=str(order.id), only_active=False)
    # Las reservas viajan con el pedido: es lo que la Spec 031 recibe (IMP-030-053).
    reservas: dict[str, list[dict]] = {}
    for r in reservations:
        reservas.setdefault(str(r.source_line_id), []).append(_reserva_dict(r))
    return {"id": order.id, "code": order.code, "customer_id": order.customer_id, "warehouse_id": order.warehouse_id,
            "credit_decision": order.credit_decision, "margin": order.margin, "currency": order.currency,
            "status": order.status, "approval_ref": order.approval_ref,
            "status_reason": order.status_reason,
            "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
            "released_at": order.released_at.isoformat() if order.released_at else None,
            "reservation_trigger": RESERVATION_TRIGGER,
            "eligible_for_picking": order.status == ORDER_HANDOFF_STATE,
            "allowed_actions": order_allowed_actions(order),
            "quote_id": str(order.quote_id) if order.quote_id else None,
            "lines": [{
                "id": line.id, "product_id": line.product_id,
                "quantity": str(line.quantity), "unit_price": str(line.unit_price),
                "discount": str(line.discount or 0),
                "needs_inventory": line.needs_inventory,
                "presentation_id": line.presentation_id, "uom_id": line.uom_id,
                "conversion_factor_snapshot": (str(line.conversion_factor_snapshot)
                                               if line.conversion_factor_snapshot is not None else None),
                "base_quantity": str(line.base_quantity) if line.base_quantity is not None else None,
                "reservations": reservas.get(str(line.id), []),
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
