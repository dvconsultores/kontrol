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

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.approvals import integration as approvals_integration
from app.modules.approvals import service as approvals_service
from app.modules.fiscal import service as fiscal_service
from app.modules.inventory import service as inv_service
from app.modules.inventory.models import InventoryBalance, Reservation
from app.modules.master_data import uom as uom_engine
from app.modules.organization.models import Company, Warehouse
from app.modules.organization.service import warehouse_belongs_to
from app.modules.organization.structure import physical_order_query
from app.modules.purchasing import service as ap_service
from app.modules.purchasing.models import Application, OpenItem
from app.modules.regulatory import service as regulatory_service
from app.modules.regulatory.models import TransportDriver, TransportVehicle
from app.modules.sales.models import (
    PICK_DISCREPANCY_KINDS,
    PLAN_ACTIVE_STATUSES,
    OrderConfirmation,
    OrderConfirmationLine,
    PickList,
    PickListLine,
    SalesCreditNote,
    SalesCreditNoteLine,
    SalesDebitNote,
    SalesDebitNoteLine,
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
from app.shared.clock import hoy_de_negocio


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
    "RELEASED": {"PREPARING", "CANCELLED", "DRAFT"},
    # `RELEASED` de vuelta: `R-D0-15-19`. Cancelar un plan de picking confirmado
    # antes de cualquier efecto físico devuelve el pedido a la cola. Sin esta
    # arista quedaría varado en `PREPARING` con la reserva viva, sin plan y sin
    # camino de vuelta.
    # `PREPARED` lo declara `ADR-D0-012`: «`RESERVED → PREPARING → PREPARED →
    # CONFIRMED → …`», y su §65 lo llama «el correlato comercial de `PREPARADO`»
    # como estado de mercancía. Existe para que la confirmación independiente de
    # la Spec 033 tenga un estado de entrada distinguible.
    # `SHIPPED` deja de salir de aquí. El ¶103 exige «Pedido preparado + Pedido
    # confirmado + **Factura emitida**» antes de la salida física, y la Spec 035
    # lo hace cumplir: despachar sin factura era la deuda que este tramo dejó
    # anotada al cerrar la 034, y se cierra quitando la arista, no solo
    # comprobándola.
    "PREPARING": {"CANCELLED", "RELEASED", "PREPARED"},
    # `CONFIRMED` y la vuelta a `PREPARING` las declara `ADR-D0-012`: conforme →
    # `CONFIRMED` (`R-D0-12-4`, ¶81); no conforme → «el pedido regresa a
    # preparación/corrección» (`R-D0-12-3`, ¶77). `READY_FOR_BILLING` no se añade
    # aquí: lo escribirá la Spec 034, igual que la 032 dejó `CONFIRMED` para esta.
    "PREPARED": {"CANCELLED", "CONFIRMED", "PREPARING"},
    "CONFIRMED": {"CANCELLED", "READY_FOR_BILLING"},
    "READY_FOR_BILLING": {"INVOICED", "CANCELLED"},
    "INVOICED": {"SHIPPED", "CANCELLED"},
    "SHIPPED": {"CLOSED"},
    "CLOSED": set(),
    "CANCELLED": set(),
    "REJECTED": set(),
    "EXPIRED": set(),
}

#: Estados en los que el pedido tiene (y debe tener) su reserva viva.
ORDER_RESERVED_STATES = frozenset({"SUBMITTED", "RELEASED", "PREPARING", "PREPARED",
                                  "CONFIRMED", "READY_FOR_BILLING", "INVOICED"})
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


#: Base e IVA se expresan al céntimo: la norma pide discriminarlos, no
#: arrastrar decimales de una proporción.
_CENTIMO = Decimal("0.01")


def _dec(value: Any) -> Decimal:
    """Coerción a `Decimal` en la frontera del servicio.

    La misma razón que en inventario: la API recibe números y mezclar `float`
    con `Decimal` en aritmética es el defecto que rompió factura, pago y notas.
    """
    if value is None:
        return Decimal(0)
    return value if isinstance(value, Decimal) else Decimal(str(value))


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
    return cotizacion.validity_until < (hoy or hoy_de_negocio())


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
    # El pedido **no** sale de la cola al crear el borrador (`R-D0-15-18`). Un
    # `DRAFT` puede ser parcial y no lo puede ejecutar nadie, así que el pedido
    # sigue esperando a ser planificado. Antes se movía aquí, y un borrador
    # parcial lo habría sacado de la fila sin que ningún plan pudiera ejecutarse.
    # Lo mueve `confirm_plan`, que es cuando la planificación está completa.
    order.updated_at = datetime.now(UTC)
    db.flush()
    return pl


# =========================================================================== #
# Spec 031 · cola, asignación por ubicación y ruta de picking
#
# Planificar no es recoger. Todo lo que hay aquí decide **de dónde** se sacará
# la mercancía y **en qué orden se recorrerá el almacén**; nada de esto mueve
# una sola unidad. El movimiento físico es de la Spec 032.
#
# Las reglas las cerró `D0-15`. Las tres que gobiernan el diseño:
#   · la cola se ordena por `released_at`, que es el sello del acto que mete el
#     pedido en ella, con desempate por `id` (`R-D0-15-2/3`);
#   · un plan parcial puede existir, pero solo en `DRAFT` (`R-D0-15-6`);
#   · confirmar exige el 100 % de lo reservado (`R-D0-15-8`).
# =========================================================================== #


def _base_de(reserva: Reservation) -> Decimal:
    """La cantidad reservada **en unidad base**.

    `base_quantity` es lo que la Spec 011 congela; `quantity` está en la unidad
    de la línea. Dos cajas de doce son veinticuatro, y el picking asigna
    veinticuatro. Si el snapshot falta, la reserva no se hizo con unidad y la
    cantidad ya es base.
    """
    return _dec(reserva.base_quantity if reserva.base_quantity is not None else reserva.quantity)


def _reserva_de_linea(db: Session, *, company_id: str, order_line_id: str) -> Reservation:
    """La reserva activa que respalda una línea de pedido."""
    reserva = db.execute(
        select(Reservation).where(Reservation.company_id == company_id,
                                  Reservation.source_line_id == order_line_id,
                                  Reservation.status == "ACTIVE")
    ).scalars().first()
    if reserva is None:
        raise ConflictError(code="PICKING_LINE_NOT_RESERVED",
                            message="La línea no tiene reserva activa que planificar.")
    return reserva


def picking_queue(db: Session, *, company_id: str, warehouse_id: str | None = None) -> list[SalesOrder]:
    """La cola de preparación: pedidos liberados, en orden de entrada.

    `RELEASED` es el estado que mete el pedido en esta cola —lo dice
    `FR-030-050` y lo escribe `_a_released`— y `released_at` es el sello de ese
    acto. Ordenar por él no elige un criterio entre varios: ordena por el
    momento de entrada, que es lo único que el proceso pide sin añadir una
    dimensión de prioridad que `D0-03` §8 mantiene diferida.

    El desempate es `id`, clave primaria: dos liberaciones en el mismo instante
    son posibles y sin él el residuo lo decidiría el orden natural de
    PostgreSQL, que no es un orden. Nunca se ordena por `code`: no tiene
    restricción de unicidad y no haría total la secuencia.
    """
    company_id = _company(company_id, obj="picking")
    reservada = (
        select(Reservation.source_order_id)
        .where(Reservation.company_id == company_id, Reservation.status == "ACTIVE",
               Reservation.source_order_id.isnot(None))
    )
    q = (select(SalesOrder)
         .where(SalesOrder.company_id == company_id,
                SalesOrder.status == ORDER_HANDOFF_STATE,
                SalesOrder.id.in_(reservada))
         .order_by(SalesOrder.released_at.asc(), SalesOrder.id.asc()))
    if warehouse_id:
        q = q.where(SalesOrder.warehouse_id == warehouse_id)
    return list(db.execute(q).scalars().all())


def _require_plan(db: Session, company_id: str, plan_id: str, *, lock: bool = False) -> PickList:
    q = select(PickList).where(PickList.id == plan_id)
    if lock:
        q = q.with_for_update()
    plan = db.execute(q).scalars().first()
    if plan is None or str(plan.company_id) != str(company_id):
        raise NotFoundError(code="PICKING_PLAN_NOT_FOUND", message="Plan de picking no encontrado")
    return plan


def get_plan(db: Session, *, company_id: str, plan_id: str) -> PickList:
    """El plan resuelto bajo el contexto de empresa."""
    return _require_plan(db, _company(company_id, obj="picking"), plan_id)


def _lineas_del_plan(db: Session, plan: PickList) -> list[PickListLine]:
    return list(db.execute(
        select(PickListLine).where(PickListLine.picklist_id == str(plan.id))
    ).scalars().all())


def _asignado_en_identidad(db: Session, *, company_id: str, location_id: str, product_id: str,
                           state: str, lot_id: str | None, serial_id: str | None,
                           excepto_linea: str | None = None) -> Decimal:
    """Lo que los planes **vivos** ya tienen tomado de esa identidad física.

    Una asignación está viva si y solo si su plan lo está (`DRAFT` o
    `CONFIRMED`). No hay estado por línea a propósito: sería una segunda verdad
    capaz de contradecir al plan que la contiene.
    """
    q = (select(func.coalesce(func.sum(PickListLine.base_quantity), 0))
         .join(PickList, PickList.id == PickListLine.picklist_id)
         .where(PickList.company_id == company_id,
                PickList.status.in_(PLAN_ACTIVE_STATUSES),
                PickListLine.location_id == location_id,
                PickListLine.product_id == product_id,
                PickListLine.state == state))
    q = q.where(PickListLine.lot_id == lot_id) if lot_id is not None else q.where(PickListLine.lot_id.is_(None))
    q = q.where(PickListLine.serial_id == serial_id) if serial_id is not None else q.where(PickListLine.serial_id.is_(None))
    if excepto_linea:
        q = q.where(PickListLine.id != excepto_linea)
    return _dec(db.execute(q).scalar() or 0)


def _asignado_a_linea(db: Session, *, plan_id: str, order_line_id: str,
                      excepto_linea: str | None = None) -> Decimal:
    q = (select(func.coalesce(func.sum(PickListLine.base_quantity), 0))
         .where(PickListLine.picklist_id == plan_id,
                PickListLine.order_line_id == order_line_id,
                PickListLine.location_id.isnot(None)))
    if excepto_linea:
        q = q.where(PickListLine.id != excepto_linea)
    return _dec(db.execute(q).scalar() or 0)


def picking_candidates(db: Session, *, company_id: str, plan_id: str, order_line_id: str) -> list[dict]:
    """De qué ubicaciones se puede recoger esa línea, en orden de recorrido.

    Candidata es la existencia **ubicada y vendible** cuyo asignable sea
    positivo. No se descuenta `qty_reserved`: el compromiso comercial es de
    almacén y ya está representado en la propia reserva que estamos
    satisfaciendo; restarlo aquí lo contaría dos veces.
    """
    company_id = _company(company_id, obj="picking")
    plan = _require_plan(db, company_id, plan_id)
    reserva = _reserva_de_linea(db, company_id=company_id, order_line_id=order_line_id)
    saldos = inv_service.located_sellable_balances(
        db, company_id=company_id, warehouse_id=str(plan.warehouse_id),
        product_id=str(reserva.product_id), lot_id=reserva.lot_id, serial_id=reserva.serial_id)
    orden = _orden_fisico(db, str(plan.warehouse_id))
    salida = []
    for saldo in saldos:
        tomado = _asignado_en_identidad(
            db, company_id=company_id, location_id=str(saldo.location_id),
            product_id=str(saldo.product_id), state=saldo.state,
            lot_id=saldo.lot_id, serial_id=saldo.serial_id)
        asignable = _dec(saldo.qty_on_hand) - tomado
        if asignable <= 0:
            continue
        salida.append({"location_id": str(saldo.location_id), "product_id": str(saldo.product_id),
                       "state": saldo.state, "lot_id": saldo.lot_id, "serial_id": saldo.serial_id,
                       "on_hand": str(_dec(saldo.qty_on_hand)), "allocatable": str(asignable),
                       "sequence": orden.get(str(saldo.location_id), len(orden))})
    salida.sort(key=lambda c: (c["sequence"], c["location_id"]))
    return salida


def _orden_fisico(db: Session, warehouse_id: str) -> dict[str, int]:
    """Ubicación → puesto en el recorrido, según la autoridad de la Spec 008.

    No se calcula ninguna ruta aquí. `physical_order_query` ya devuelve el orden
    físico total y determinista —zona, pasillo, rack, nivel, ubicación, con
    desempate por código (`FR-008-033`)— y esto solo lo numera.
    """
    filas = db.execute(physical_order_query(warehouse_id)).all()
    return {str(fila[0].id): i for i, fila in enumerate(filas)}


def _resecuenciar(db: Session, plan: PickList) -> None:
    """Numera el recorrido según el orden físico de la Spec 008.

    Se rehace cada vez que cambian las asignaciones para que un `DRAFT` ya
    enseñe su ruta. El desempate final por `id` de línea la hace total: dos
    asignaciones en la misma ubicación deben salir siempre en el mismo orden.
    """
    orden = _orden_fisico(db, str(plan.warehouse_id))
    lineas = [ln for ln in _lineas_del_plan(db, plan) if ln.location_id is not None]
    lineas.sort(key=lambda ln: (orden.get(str(ln.location_id), len(orden)),
                                str(ln.location_id), str(ln.id)))
    for puesto, linea in enumerate(lineas, start=1):
        linea.sequence = puesto


def _saldo_candidato(db: Session, *, company_id: str, warehouse_id: str, location_id: str,
                     product_id: str, lot_id: str | None, serial_id: str | None,
                     state: str | None) -> InventoryBalance:
    """La fila física de la que se va a tomar, **bloqueada**.

    El bloqueo es lo que impide que dos planes se lleven las mismas unidades:
    sin él, ambos leerían el mismo disponible y ambos cabrían.
    """
    q = (select(InventoryBalance)
         .where(InventoryBalance.company_id == company_id,
                InventoryBalance.warehouse_id == warehouse_id,
                InventoryBalance.location_id == location_id,
                InventoryBalance.product_id == product_id,
                InventoryBalance.state.in_(tuple(inv_service.state_authority.SELLABLE_STATES)))
         .with_for_update())
    q = q.where(InventoryBalance.lot_id == lot_id) if lot_id is not None else q.where(InventoryBalance.lot_id.is_(None))
    q = q.where(InventoryBalance.serial_id == serial_id) if serial_id is not None else q.where(InventoryBalance.serial_id.is_(None))
    if state is not None:
        q = q.where(InventoryBalance.state == state)
    filas = list(db.execute(q).scalars().all())
    if not filas:
        raise ConflictError(code="PICKING_LOCATION_NOT_ELIGIBLE",
                            message="La ubicación no tiene existencia vendible de ese producto.")
    if len(filas) > 1:
        raise ConflictError(code="PICKING_STATE_AMBIGUOUS",
                            message="Hay varios estados vendibles en esa ubicación: indique cuál.")
    return filas[0]


def allocate(db: Session, *, company_id: str, plan_id: str, order_line_id: str, location_id: str,
             quantity: Decimal | float | str, state: str | None = None,
             actor: str | None = None) -> PickList:
    """Fija cuánto se recoge de una ubicación para una línea del pedido.

    **Fija, no suma.** Repetir la misma petición deja el mismo resultado, que es
    lo que hace la operación idempotente sin necesidad de una clave de cliente:
    un doble envío no asigna el doble. Cantidad cero retira la asignación.

    Dos invariantes se comprueban con la fila bloqueada, nunca antes:
    lo asignado a la línea no puede exceder lo reservado para ella, y lo tomado
    de una ubicación no puede exceder lo que físicamente hay allí.
    """
    company_id = _company(company_id, obj="picking")
    plan = _require_plan(db, company_id, plan_id, lock=True)
    if plan.status != "DRAFT":
        raise ConflictError(code="PICKING_PLAN_NOT_DRAFT",
                            message="Solo un plan en borrador admite cambios de asignación.")
    order = _lock_order(db, company_id, str(plan.order_id))
    if order.status != ORDER_HANDOFF_STATE:
        raise ConflictError(code="PICKING_ORDER_NOT_ELIGIBLE",
                            message="El pedido ya no está liberado para preparación.")
    reserva = _reserva_de_linea(db, company_id=company_id, order_line_id=order_line_id)
    if str(reserva.source_order_id) != str(plan.order_id):
        raise ConflictError(code="PICKING_LINE_FOREIGN",
                            message="La línea no pertenece al pedido del plan.")

    cantidad = _dec(quantity)
    if cantidad < 0:
        raise KontrolError(code="PICKING_QUANTITY_INVALID",
                           message="La cantidad no puede ser negativa.", status_code=422)

    ubicacion = inv_service.location_in_warehouse(
        db, company_id=company_id, warehouse_id=str(plan.warehouse_id), location_id=location_id)
    saldo = _saldo_candidato(
        db, company_id=company_id, warehouse_id=str(plan.warehouse_id), location_id=str(ubicacion.id),
        product_id=str(reserva.product_id), lot_id=reserva.lot_id, serial_id=reserva.serial_id,
        state=state)

    existente = db.execute(
        select(PickListLine).where(PickListLine.picklist_id == str(plan.id),
                                   PickListLine.order_line_id == order_line_id,
                                   PickListLine.location_id == str(ubicacion.id),
                                   PickListLine.state == saldo.state)
    ).scalars().first()
    excepto = str(existente.id) if existente is not None else None

    requerido = _base_de(reserva)
    ya_en_linea = _asignado_a_linea(db, plan_id=str(plan.id), order_line_id=order_line_id,
                                    excepto_linea=excepto)
    if ya_en_linea + cantidad > requerido:
        raise ConflictError(
            code="PICKING_OVER_RESERVATION",
            message=f"Excede lo reservado para la línea: {ya_en_linea + cantidad} sobre {requerido}.")

    tomado = _asignado_en_identidad(
        db, company_id=company_id, location_id=str(ubicacion.id), product_id=str(saldo.product_id),
        state=saldo.state, lot_id=saldo.lot_id, serial_id=saldo.serial_id, excepto_linea=excepto)
    if tomado + cantidad > _dec(saldo.qty_on_hand):
        raise ConflictError(
            code="PICKING_OVER_LOCATION",
            message=f"La ubicación solo tiene {_dec(saldo.qty_on_hand) - tomado} asignable.")

    if cantidad == 0:
        if existente is not None:
            db.delete(existente)
    elif existente is not None:
        existente.base_quantity = cantidad
        existente.quantity = cantidad
    else:
        db.add(PickListLine(
            picklist_id=str(plan.id), order_line_id=order_line_id, product_id=str(saldo.product_id),
            location_id=str(ubicacion.id), state=saldo.state, lot_id=saldo.lot_id,
            serial_id=saldo.serial_id, quantity=cantidad, base_quantity=cantidad, sequence=0))
    db.flush()
    _resecuenciar(db, plan)
    db.flush()
    _audit(db, action="PICKING_ALLOCATED", entity_type="PickList", entity_id=str(plan.id),
           company_id=plan.company_id, actor=actor,
           after={"order_line_id": order_line_id, "location_id": str(ubicacion.id),
                  "base_quantity": str(cantidad)})
    return plan


def confirm_plan(db: Session, *, company_id: str, plan_id: str, actor: str | None = None) -> PickList:
    """Cierra la planificación. Exige el 100 % y mueve el pedido a preparación.

    `R-D0-15-8`: mientras quede cantidad reservada sin asignar, el plan no es
    ejecutable y no se confirma. Y `R-D0-15-18`: **este** es el momento en que
    el pedido sale de la cola, no cuando se creó el borrador.
    """
    company_id = _company(company_id, obj="picking")
    plan = _require_plan(db, company_id, plan_id, lock=True)
    if plan.status != "DRAFT":
        raise ConflictError(code="PICKING_PLAN_NOT_DRAFT",
                            message="Solo un plan en borrador puede confirmarse.")
    order = _lock_order(db, company_id, str(plan.order_id))
    if order.status != ORDER_HANDOFF_STATE:
        raise ConflictError(code="PICKING_ORDER_NOT_ELIGIBLE",
                            message="El pedido ya no está liberado para preparación.")

    reservas = inv_service.order_reservations(db, company_id=company_id, order_id=str(order.id))
    if not reservas:
        raise ConflictError(code="PICKING_NO_RESERVATION",
                            message="El pedido no tiene reservas activas que planificar.")
    for reserva in reservas:
        if reserva.source_line_id is None:
            continue
        requerido = _base_de(reserva)
        asignado = _asignado_a_linea(db, plan_id=str(plan.id), order_line_id=str(reserva.source_line_id))
        if asignado != requerido:
            raise ConflictError(
                code="PICKING_PLAN_INCOMPLETE",
                message=f"Falta asignar {requerido - asignado} de una línea; el plan no está completo.")

    # Revalidar contra la existencia real: entre el borrador y ahora la
    # mercancía pudo moverse. Confirmar un plan sobre existencia que ya no está
    # mandaría al almacenista a una ubicación vacía.
    for linea in _lineas_del_plan(db, plan):
        if linea.location_id is None:
            continue
        saldo = _saldo_candidato(
            db, company_id=company_id, warehouse_id=str(plan.warehouse_id),
            location_id=str(linea.location_id), product_id=str(linea.product_id),
            lot_id=linea.lot_id, serial_id=linea.serial_id, state=linea.state)
        tomado = _asignado_en_identidad(
            db, company_id=company_id, location_id=str(linea.location_id),
            product_id=str(linea.product_id), state=str(linea.state),
            lot_id=linea.lot_id, serial_id=linea.serial_id)
        if tomado > _dec(saldo.qty_on_hand):
            raise ConflictError(code="PICKING_LOCATION_DRIFTED",
                                message="La existencia de una ubicación cambió: replanifique.")

    _resecuenciar(db, plan)
    ahora = datetime.now(UTC)
    plan.status = "CONFIRMED"
    plan.confirmed_at = ahora
    plan.confirmed_by = actor
    plan.updated_at = ahora
    _assert_transition(order.status, "PREPARING", ORDER_TRANSITIONS, "el pedido")
    order.status = "PREPARING"
    order.updated_at = ahora
    db.flush()
    _audit(db, action="PICKING_PLAN_CONFIRMED", entity_type="PickList", entity_id=str(plan.id),
           company_id=plan.company_id, actor=actor,
           after={"status": "CONFIRMED", "order_status": "PREPARING"})
    return plan


def _cerrar_plan(db: Session, *, company_id: str, plan_id: str, destino: str, reason: str | None,
                 actor: str | None) -> PickList:
    """Tronco común de cancelar e invalidar.

    Lo que ambos hacen es idéntico y es poco: el plan pasa a terminal y con eso
    sus asignaciones dejan de estar vivas, porque «viva» se deriva del estado
    del plan. **No se toca la reserva comercial** —`R-D0-15-13`, solo la Spec
    030 la libera— ni la existencia física. Si el plan estaba confirmado, el
    pedido vuelve a la cola: un pedido con reserva viva y sin plan tiene que
    poder volver a planificarse (`R-D0-15-19`).
    """
    plan = _require_plan(db, company_id, plan_id, lock=True)
    if plan.status not in PLAN_ACTIVE_STATUSES:
        raise ConflictError(code="PICKING_PLAN_NOT_ACTIVE",
                            message="El plan ya no está vivo.")
    # `R-D0-15-16` dejó a la Spec 032 definir cuál es el primer efecto físico
    # irreversible. Es **la primera recogida registrada**: a partir de ahí hay
    # mercancía en `PICKING` y el contador de reservado ya bajó, y retirar el
    # plan la dejaría en un estado de custodia sin dueño, porque devolverla a
    # `DISPONIBLE` exigiría una arista que nadie ha declarado.
    recogidas = [ln for ln in _lineas_del_plan(db, plan) if ln.picked_at is not None]
    if recogidas:
        raise ConflictError(
            code="PICKING_ALREADY_STARTED",
            message=("La preparación ya empezó: hay "
                     f"{len(recogidas)} parada(s) recogida(s). El plan no se retira."))
    motivo = _motivo(reason)
    order = _lock_order(db, company_id, str(plan.order_id))
    ahora = datetime.now(UTC)
    estado_previo = plan.status
    plan.status = destino
    plan.status_reason = motivo
    plan.updated_at = ahora
    if destino == "CANCELLED":
        plan.cancelled_at = ahora
    else:
        plan.invalidated_at = ahora
    devuelto = False
    if order.status == "PREPARING":
        _assert_transition(order.status, ORDER_HANDOFF_STATE, ORDER_TRANSITIONS, "el pedido")
        order.status = ORDER_HANDOFF_STATE
        order.updated_at = ahora
        devuelto = True
    db.flush()
    _audit(db, action=f"PICKING_PLAN_{destino}", entity_type="PickList", entity_id=str(plan.id),
           company_id=plan.company_id, actor=actor, reason=motivo,
           before={"status": estado_previo},
           after={"status": destino, "order_returned_to_queue": devuelto})
    return plan


def cancel_plan(db: Session, *, company_id: str, plan_id: str, reason: str | None = None,
                actor: str | None = None) -> PickList:
    """Cancelación deliberada del plan, antes de cualquier efecto físico."""
    return _cerrar_plan(db, company_id=_company(company_id, obj="picking"), plan_id=plan_id,
                        destino="CANCELLED", reason=reason, actor=actor)


def invalidate_plan(db: Session, *, company_id: str, plan_id: str, reason: str | None = None,
                    actor: str | None = None) -> PickList:
    """El plan pierde validez porque una precondición aguas arriba se cayó.

    No es un sinónimo de cancelar: exige que la precondición **esté**
    efectivamente perdida. Invalidar un plan sano borraría de la auditoría la
    diferencia entre lo que alguien decidió y lo que le ocurrió.
    """
    company_id = _company(company_id, obj="picking")
    plan = _require_plan(db, company_id, plan_id)
    order = _require_order(db, company_id, str(plan.order_id))
    reservas = inv_service.order_reservations(db, company_id=company_id, order_id=str(order.id))
    if order.status in (ORDER_HANDOFF_STATE, "PREPARING") and reservas:
        raise ConflictError(code="PICKING_PLAN_STILL_VALID",
                            message="El plan sigue siendo válido: para retirarlo, cancélelo.")
    return _cerrar_plan(db, company_id=company_id, plan_id=plan_id, destino="INVALIDATED",
                        reason=reason, actor=actor)


def plan_dict(db: Session, plan: PickList) -> dict:
    """El plan con su recorrido y, sobre todo, con lo que falta.

    El remanente se deriva de la reserva activa y de lo asignado. No se guarda:
    persistirlo crearía una tercera cifra capaz de discrepar de las otras dos.
    """
    lineas = sorted((ln for ln in _lineas_del_plan(db, plan) if ln.location_id is not None),
                    key=lambda ln: (ln.sequence or 0, str(ln.id)))
    demanda = []
    pendiente = Decimal(0)
    for reserva in inv_service.order_reservations(db, company_id=str(plan.company_id),
                                                  order_id=str(plan.order_id)):
        if reserva.source_line_id is None:
            continue
        requerido = _base_de(reserva)
        asignado = _asignado_a_linea(db, plan_id=str(plan.id), order_line_id=str(reserva.source_line_id))
        pendiente += requerido - asignado
        demanda.append({"order_line_id": str(reserva.source_line_id),
                        "product_id": str(reserva.product_id),
                        "required_base_quantity": str(requerido),
                        "allocated_base_quantity": str(asignado),
                        "remaining_base_quantity": str(requerido - asignado)})
    return {
        "id": str(plan.id), "code": plan.code, "order_id": str(plan.order_id),
        "warehouse_id": str(plan.warehouse_id), "status": plan.status,
        "status_reason": plan.status_reason,
        "confirmed_at": plan.confirmed_at.isoformat() if plan.confirmed_at else None,
        "cancelled_at": plan.cancelled_at.isoformat() if plan.cancelled_at else None,
        "invalidated_at": plan.invalidated_at.isoformat() if plan.invalidated_at else None,
        "remaining_base_quantity": str(pendiente),
        "confirmable": plan.status == "DRAFT" and pendiente == 0 and bool(lineas),
        "demand": demanda,
        "route": [{"id": str(ln.id), "sequence": ln.sequence, "location_id": str(ln.location_id),
                   "order_line_id": str(ln.order_line_id) if ln.order_line_id else None,
                   "product_id": str(ln.product_id), "state": ln.state, "lot_id": ln.lot_id,
                   "serial_id": ln.serial_id, "base_quantity": str(_dec(ln.base_quantity))}
                  for ln in lineas],
    }


# =========================================================================== #
# Spec 032 · ejecución física del picking y consolidación
#
# La 031 planificó: dijo de qué ubicación sale cuánto y en qué orden. Aquí se
# ejecuta. Lo que se recoge **de verdad** se guarda aparte de lo planificado,
# porque sin las dos cifras no hay diferencia que registrar, y el proceso es
# explícito: «debe registrarse la diferencia» (¶47) y el pedido «no debería
# simplemente modificarse sin dejar evidencia» (¶53).
#
# La mercancía **no sale del almacén** aquí. Cambia de estado de custodia
# —`DISPONIBLE → PICKING → PREPARADO`, las dos aristas que la matriz de `D0-10`
# declaró para 031/032— y acaba en el Área de Confirmación. La salida física es
# del despacho, y es allí donde la reserva se consume.
# =========================================================================== #


def _plan_ejecutable(db: Session, company_id: str, plan_id: str) -> tuple[PickList, SalesOrder]:
    """El plan y su pedido, bloqueados, en estado de ejecutarse."""
    plan = _require_plan(db, company_id, plan_id, lock=True)
    if plan.status != "CONFIRMED":
        raise ConflictError(code="PICKING_PLAN_NOT_EXECUTABLE",
                            message="Solo un plan confirmado se puede preparar.")
    order = _lock_order(db, company_id, str(plan.order_id))
    if order.status != "PREPARING":
        raise ConflictError(code="PICKING_ORDER_NOT_PREPARING",
                            message="El pedido no está en preparación.")
    return plan, order


def execute_pick(db: Session, *, company_id: str, plan_id: str, line_id: str,
                 quantity: Decimal | float | str, discrepancy_kind: str | None = None,
                 discrepancy_note: str | None = None, actor: str | None = None) -> PickList:
    """Registra lo recogido en una parada del recorrido (¶33-39).

    Idempotente por línea: una asignación se recoge una vez. Reintentar la misma
    petición no vuelve a extraer mercancía ni duplica el movimiento.

    Recoger de menos exige motivo —uno de los cinco del ¶48-52— y libera la
    diferencia de la reserva (`POL-D0-002` §8). Recoger de más está bloqueado:
    ninguna autoridad lo permite y `R-D0-10-7` deniega por defecto.
    """
    company_id = _company(company_id, obj="picking")
    plan, order = _plan_ejecutable(db, company_id, plan_id)
    linea = db.execute(
        select(PickListLine).where(PickListLine.id == line_id,
                                   PickListLine.picklist_id == str(plan.id)).with_for_update()
    ).scalars().first()
    if linea is None or linea.location_id is None:
        raise NotFoundError(code="PICKING_ALLOCATION_NOT_FOUND",
                            message="La asignación no existe en este plan.")
    if linea.picked_at is not None:
        raise ConflictError(code="PICKING_ALREADY_PICKED",
                            message="Esa asignación ya se recogió.")

    planificado = _dec(linea.base_quantity)
    recogido = _dec(quantity)
    if recogido < 0:
        raise KontrolError(code="PICKING_QUANTITY_INVALID",
                           message="La cantidad recogida no puede ser negativa.", status_code=422)
    if recogido > planificado:
        raise ConflictError(
            code="PICKING_OVER_PICK",
            message=f"No se puede recoger más de lo planificado: {recogido} sobre {planificado}.")
    faltante = planificado - recogido
    if faltante > 0:
        if discrepancy_kind not in PICK_DISCREPANCY_KINDS:
            raise KontrolError(
                code="PICKING_DISCREPANCY_REASON_REQUIRED",
                message=("Recoger menos de lo planificado exige indicar el motivo: "
                         + ", ".join(PICK_DISCREPANCY_KINDS) + "."),
                status_code=422)
    elif discrepancy_kind is not None:
        raise KontrolError(code="PICKING_DISCREPANCY_WITHOUT_DIFFERENCE",
                           message="No hay diferencia que justificar.", status_code=422)

    if recogido > 0:
        # La extracción es un cambio de estado de custodia sobre la identidad
        # exacta: misma ubicación, mismo lote, mismo serial. No se elige otra.
        inv_service.reclassify(
            db, company_id=company_id, warehouse_id=str(plan.warehouse_id),
            product_id=str(linea.product_id), source_state=str(linea.state),
            target_state="PICKING", quantity=recogido, location_id=str(linea.location_id),
            lot_id=linea.lot_id, serial_id=linea.serial_id,
            document_ref=f"PICKLIST:{plan.id}", actor=actor)

    reserva = _reserva_de_linea(db, company_id=company_id, order_line_id=str(linea.order_line_id))
    if recogido > 0:
        inv_service.consume_on_pick(db, reservation=reserva, quantity=recogido, actor=actor)
    if faltante > 0:
        inv_service.release_picking_shortage(db, reservation=reserva, quantity=faltante, actor=actor)

    ahora = datetime.now(UTC)
    linea.picked_base_quantity = recogido
    linea.picked_at = ahora
    linea.picked_by = actor
    linea.discrepancy_kind = discrepancy_kind
    linea.discrepancy_note = discrepancy_note
    plan.updated_at = ahora
    db.flush()
    _audit(db, action="PICK_RECORDED", entity_type="PickList", entity_id=str(plan.id),
           company_id=plan.company_id, actor=actor, reason=discrepancy_note,
           before={"planned_base_quantity": str(planificado)},
           after={"line_id": str(linea.id), "location_id": str(linea.location_id),
                  "picked_base_quantity": str(recogido), "difference": str(-faltante),
                  "discrepancy_kind": discrepancy_kind})
    return plan


def consolidate(db: Session, *, company_id: str, plan_id: str, location_id: str,
                actor: str | None = None) -> PickList:
    """Concentra lo recogido como un único pedido y lo traslada (¶55-58).

    Exige haber recorrido **todas** las paradas (¶41): consolidar a medio
    recorrido daría por preparado un pedido que nadie terminó de recoger. No
    exige que no haya diferencias —el ¶45 manda el pedido al área de
    confirmación igual—, pero las diferencias viajan registradas.

    Al terminar, el pedido queda `PREPARED`: «pedido preparado pendiente de
    control» (¶59). Quien decide si está correcto es la Spec 033, que es un
    control **independiente** (¶61). Aquí no se certifica nada.
    """
    company_id = _company(company_id, obj="picking")
    plan, order = _plan_ejecutable(db, company_id, plan_id)
    lineas = [ln for ln in _lineas_del_plan(db, plan) if ln.location_id is not None]
    if not lineas:
        raise ConflictError(code="PICKING_NOTHING_TO_CONSOLIDATE",
                            message="El plan no tiene asignaciones.")
    pendientes = [ln for ln in lineas if ln.picked_at is None]
    if pendientes:
        raise ConflictError(
            code="PICKING_ROUTE_INCOMPLETE",
            message=f"Faltan {len(pendientes)} paradas del recorrido por registrar.")

    destino = inv_service.location_in_warehouse(
        db, company_id=company_id, warehouse_id=str(plan.warehouse_id), location_id=location_id)

    for linea in sorted(lineas, key=lambda ln: (ln.sequence or 0, str(ln.id))):
        recogido = _dec(linea.picked_base_quantity)
        if recogido <= 0:
            continue
        # Dos pasos, dos movimientos, y por eso la procedencia queda entera: de
        # qué ubicación salió cada unidad y en qué estado, y a cuál llegó.
        inv_service.reclassify(
            db, company_id=company_id, warehouse_id=str(plan.warehouse_id),
            product_id=str(linea.product_id), source_state="PICKING", target_state="PREPARADO",
            quantity=recogido, location_id=str(linea.location_id),
            lot_id=linea.lot_id, serial_id=linea.serial_id,
            document_ref=f"PICKLIST:{plan.id}", actor=actor)
        inv_service.putaway(
            db, company_id=company_id, warehouse_id=str(plan.warehouse_id),
            product_id=str(linea.product_id), target_location_id=str(destino.id),
            quantity=recogido, source_location_id=str(linea.location_id), state="PREPARADO",
            lot_id=linea.lot_id, serial_id=linea.serial_id,
            document_ref=f"PICKLIST:{plan.id}", actor=actor)

    ahora = datetime.now(UTC)
    plan.status = "CLOSED"
    plan.consolidation_location_id = str(destino.id)
    plan.consolidated_at = ahora
    plan.consolidated_by = actor
    plan.updated_at = ahora
    _assert_transition(order.status, "PREPARED", ORDER_TRANSITIONS, "el pedido")
    order.status = "PREPARED"
    order.updated_at = ahora
    db.flush()
    _audit(db, action="PICKING_CONSOLIDATED", entity_type="PickList", entity_id=str(plan.id),
           company_id=plan.company_id, actor=actor,
           after={"status": "CLOSED", "order_status": "PREPARED",
                  "consolidation_location_id": str(destino.id)})
    return plan


def preparation_dict(db: Session, plan: PickList) -> dict:
    """Lo preparado, línea a línea, para el control independiente de la 033.

    Entrega hechos, no un veredicto: lo planificado, lo recogido de verdad, la
    diferencia y su motivo. Comparar y confirmar es de la 033 (¶61).
    """
    base = plan_dict(db, plan)
    lineas = sorted((ln for ln in _lineas_del_plan(db, plan) if ln.location_id is not None),
                    key=lambda ln: (ln.sequence or 0, str(ln.id)))
    preparado: dict[str, Decimal] = {}
    for ln in lineas:
        clave = str(ln.order_line_id)
        preparado[clave] = preparado.get(clave, Decimal(0)) + _dec(ln.picked_base_quantity)
    base["consolidation_location_id"] = (str(plan.consolidation_location_id)
                                         if plan.consolidation_location_id else None)
    base["consolidated_at"] = plan.consolidated_at.isoformat() if plan.consolidated_at else None
    base["picking"] = [
        {"id": str(ln.id), "sequence": ln.sequence, "order_line_id": str(ln.order_line_id),
         "location_id": str(ln.location_id), "product_id": str(ln.product_id),
         "lot_id": ln.lot_id, "serial_id": ln.serial_id,
         "planned_base_quantity": str(_dec(ln.base_quantity)),
         "picked_base_quantity": (str(_dec(ln.picked_base_quantity))
                                  if ln.picked_base_quantity is not None else None),
         "difference": (str(_dec(ln.picked_base_quantity) - _dec(ln.base_quantity))
                        if ln.picked_base_quantity is not None else None),
         "discrepancy_kind": ln.discrepancy_kind, "discrepancy_note": ln.discrepancy_note,
         "picked_at": ln.picked_at.isoformat() if ln.picked_at else None,
         "picked_by": ln.picked_by}
        for ln in lineas]
    for demanda in base["demand"]:
        demanda["prepared_base_quantity"] = str(preparado.get(demanda["order_line_id"], Decimal(0)))
    base["has_discrepancy"] = any(ln.discrepancy_kind for ln in lineas)
    base["route_complete"] = all(ln.picked_at is not None for ln in lineas) and bool(lineas)
    return base


# =========================================================================== #
# Spec 033 · confirmación independiente del pedido
#
# El ¶61 llama a esto «un control independiente después del picking», y el ¶90
# explica para qué: «Almacén prepara. Confirmación verifica. Facturación factura
# sobre un pedido previamente confirmado». Es separación funcional, no un paso
# administrativo.
#
# Por eso aquí no se recoge, no se mueve, no se reclasifica y no se toca la
# reserva. Se cuenta otra vez y se deja constancia.
#
# `R-D0-12-2` fija contra qué se compara, y la frase importa: «contra el pedido,
# **no contra la lista de picking**: comparar la preparación consigo misma no es
# un control».
# =========================================================================== #


def _pedido_preparado(db: Session, company_id: str, order_id: str,
                      *, lock: bool = False) -> tuple[SalesOrder, PickList]:
    """El pedido preparado y **la** preparación sobre la que se pronuncia.

    Sin fijar el plan, una confirmación no dice sobre qué se pronunció: el ¶63
    manda obtener el pedido original y el ¶62 recibir *el pedido preparado*, en
    singular.
    """
    order = (_lock_order(db, company_id, order_id) if lock
             else _require_order(db, company_id, order_id))
    if order.status != "PREPARED":
        raise ConflictError(code="CONFIRMATION_ORDER_NOT_PREPARED",
                            message="El pedido no está preparado pendiente de control.")
    plan = db.execute(
        select(PickList).where(PickList.company_id == company_id,
                               PickList.order_id == str(order.id),
                               PickList.status == "CLOSED")
        .order_by(PickList.consolidated_at.desc())
    ).scalars().first()
    if plan is None:
        raise ConflictError(code="CONFIRMATION_NO_PREPARATION",
                            message="El pedido no tiene una preparación consolidada que verificar.")
    return order, plan


def _lineas_del_pedido(db: Session, order: SalesOrder) -> list[SalesOrderLine]:
    return list(db.execute(
        select(SalesOrderLine).where(SalesOrderLine.order_id == str(order.id))
        .order_by(SalesOrderLine.id)
    ).scalars().all())


def _requerido_de(linea: SalesOrderLine) -> Decimal:
    """Lo que el **pedido** pide, en unidad base.

    No lo que quedó reservado: un picking corto encogió la reserva, y comparar
    contra ella daría por conforme un pedido incompleto. `R-D0-12-2` compara
    contra el pedido original justamente para que eso no pase.
    """
    return _dec(linea.base_quantity if linea.base_quantity is not None else linea.quantity)


def _preparado_por_linea(db: Session, plan: PickList) -> dict[str, Decimal]:
    filas = db.execute(
        select(PickListLine.order_line_id,
               func.coalesce(func.sum(PickListLine.picked_base_quantity), 0))
        .where(PickListLine.picklist_id == str(plan.id),
               PickListLine.location_id.isnot(None))
        .group_by(PickListLine.order_line_id)
    ).all()
    return {str(order_line_id): _dec(total) for order_line_id, total in filas if order_line_id}


def _preparadores(db: Session, plan: PickList) -> set[str]:
    """Quién preparó: todos los que recogieron y quien consolidó."""
    quienes = {str(ln.picked_by) for ln in _lineas_del_plan(db, plan) if ln.picked_by}
    if plan.consolidated_by:
        quienes.add(str(plan.consolidated_by))
    return quienes


def _segregacion_permitida(db: Session, company_id: str) -> bool:
    empresa = db.get(Company, company_id)
    return bool(empresa is not None and empresa.confirmation_same_user_allowed)


def pending_confirmations(db: Session, *, company_id: str) -> list[SalesOrder]:
    """Los pedidos que esperan control: preparados y sin confirmar."""
    company_id = _company(company_id, obj="confirmación")
    confirmados = select(OrderConfirmation.order_id).where(
        OrderConfirmation.company_id == company_id,
        OrderConfirmation.status == "CONFIRMED")
    return list(db.execute(
        select(SalesOrder).where(SalesOrder.company_id == company_id,
                                 SalesOrder.status == "PREPARED",
                                 SalesOrder.id.not_in(confirmados))
        .order_by(SalesOrder.updated_at.asc(), SalesOrder.id.asc())
    ).scalars().all())


def confirmation_worksheet(db: Session, *, company_id: str, order_id: str) -> dict:
    """Lo que el verificador tiene delante: el pedido original y lo preparado.

    El ¶63 manda obtener el pedido original; el ¶64, hacer un nuevo chequeo
    físico. Se muestran las dos cifras porque ni el proceso ni el `ADR` piden
    conteo ciego, y `R-D0-12-6` prohíbe codificar la política de un cliente
    concreto: quien la quiera, la configurará.
    """
    company_id = _company(company_id, obj="confirmación")
    order, plan = _pedido_preparado(db, company_id, order_id)
    preparado = _preparado_por_linea(db, plan)
    intentos = db.execute(
        select(OrderConfirmation).where(OrderConfirmation.order_id == str(order.id))
        .order_by(OrderConfirmation.attempt)
    ).scalars().all()
    return {
        "order_id": str(order.id), "code": order.code, "status": order.status,
        "picklist_id": str(plan.id), "warehouse_id": str(plan.warehouse_id),
        "consolidation_location_id": (str(plan.consolidation_location_id)
                                      if plan.consolidation_location_id else None),
        "prepared_by": sorted(_preparadores(db, plan)),
        "same_user_allowed": _segregacion_permitida(db, company_id),
        "attempts": [{"id": str(c.id), "attempt": c.attempt, "status": c.status,
                      "checked_by": c.checked_by,
                      "checked_at": c.checked_at.isoformat() if c.checked_at else None,
                      "notes": c.notes} for c in intentos],
        "lines": [{"order_line_id": str(ln.id), "product_id": str(ln.product_id),
                   "presentation_id": str(ln.presentation_id) if ln.presentation_id else None,
                   "conversion_factor_snapshot": (str(_dec(ln.conversion_factor_snapshot))
                                                  if ln.conversion_factor_snapshot else None),
                   "quantity": str(_dec(ln.quantity)),
                   "required_base_quantity": str(_requerido_de(ln)),
                   "prepared_base_quantity": str(preparado.get(str(ln.id), Decimal(0)))}
                  for ln in _lineas_del_pedido(db, order) if ln.needs_inventory],
    }


def _dictamen_de_linea(*, requerido: Decimal, verificado: Decimal, presentation_ok: bool,
                       condition_ok: bool, preparado: Decimal) -> str | None:
    """En qué dimensión falla, o `None` si conforma.

    El orden importa: se informa la falla más gruesa. Que falte la línea entera
    es más que una diferencia de cantidad, y una diferencia de cantidad es más
    que una observación sobre el empaque.
    """
    if requerido > 0 and preparado == 0 and verificado == 0:
        return "LINEA_FALTANTE"
    if verificado != requerido:
        return "CANTIDAD"
    if not presentation_ok:
        return "PRESENTACION"
    if not condition_ok:
        return "CONDICION"
    return None


def confirm_order(db: Session, *, company_id: str, order_id: str, lines: list[dict],
                  notes: str | None = None, actor: str | None = None) -> OrderConfirmation:
    """El control independiente, entero, en un acto.

    El verificador cuenta producto por producto (¶65-69) y el backend dictamina:
    el resultado **no lo envía el cliente**, se calcula aquí comparando contra el
    pedido. Conforme → `CONFIRMED` y el pedido queda formalmente confirmado
    (¶81). No conforme → se registra la incidencia y el pedido **regresa a
    preparación** (¶77), que es lo que el proceso manda hacer.

    `R-D0-12-3`: tras una corrección hace falta una confirmación **completa**,
    no parcial. Por eso cada intento verifica todas las líneas y se guarda
    entero; el rechazo anterior no se borra, es la evidencia de por qué hubo otro.
    """
    company_id = _company(company_id, obj="confirmación")
    order, plan = _pedido_preparado(db, company_id, order_id, lock=True)

    if actor and not _segregacion_permitida(db, company_id):
        preparadores = _preparadores(db, plan)
        if str(actor) in preparadores:
            raise ConflictError(
                code="CONFIRMATION_SEGREGATION_REQUIRED",
                message=("Quien preparó el pedido no puede confirmarlo: el control dejaría de ser "
                         "independiente. La empresa puede permitirlo explícitamente."))

    del_pedido = {str(ln.id): ln for ln in _lineas_del_pedido(db, order) if ln.needs_inventory}
    if not del_pedido:
        raise ConflictError(code="CONFIRMATION_NOTHING_TO_CHECK",
                            message="El pedido no tiene líneas de inventario que verificar.")
    enviadas = {str(item.get("order_line_id")): item for item in lines or []}
    sobrantes = set(enviadas) - set(del_pedido)
    faltan = set(del_pedido) - set(enviadas)
    if faltan:
        raise KontrolError(
            code="CONFIRMATION_INCOMPLETE",
            message=(f"El control es completo o no es control: faltan {len(faltan)} línea(s) por "
                     "verificar."), status_code=422)

    preparado = _preparado_por_linea(db, plan)
    previos = db.execute(
        select(func.count(OrderConfirmation.id)).where(OrderConfirmation.order_id == str(order.id))
    ).scalar() or 0
    ahora = datetime.now(UTC)
    confirmacion = OrderConfirmation(
        company_id=company_id, order_id=str(order.id), picklist_id=str(plan.id),
        attempt=previos + 1, status="CONFIRMED", checked_by=actor, checked_at=ahora,
        notes=notes, created_by=actor)
    db.add(confirmacion)
    db.flush()

    conforme = True
    for clave, linea in sorted(del_pedido.items()):
        item = enviadas[clave]
        verificado = _dec(item.get("checked_base_quantity"))
        if verificado < 0:
            raise KontrolError(code="CONFIRMATION_QUANTITY_INVALID",
                               message="La cantidad verificada no puede ser negativa.",
                               status_code=422)
        presentation_ok = bool(item.get("presentation_ok", True))
        condition_ok = bool(item.get("condition_ok", True))
        requerido = _requerido_de(linea)
        motivo = _dictamen_de_linea(
            requerido=requerido, verificado=verificado, presentation_ok=presentation_ok,
            condition_ok=condition_ok, preparado=preparado.get(clave, Decimal(0)))
        conforme = conforme and motivo is None
        db.add(OrderConfirmationLine(
            confirmation_id=str(confirmacion.id), order_line_id=clave,
            product_id=str(linea.product_id), required_base_quantity=requerido,
            prepared_base_quantity=preparado.get(clave, Decimal(0)),
            checked_base_quantity=verificado, presentation_id=linea.presentation_id,
            presentation_ok=presentation_ok, condition_ok=condition_ok,
            conforms=motivo is None, difference_kind=motivo,
            note=(item.get("note") or None)))
    for clave in sorted(sobrantes):
        item = enviadas[clave]
        conforme = False
        db.add(OrderConfirmationLine(
            confirmation_id=str(confirmacion.id), order_line_id=None,
            product_id=str(item.get("product_id") or ""), required_base_quantity=Decimal(0),
            prepared_base_quantity=Decimal(0),
            checked_base_quantity=_dec(item.get("checked_base_quantity")),
            presentation_ok=True, condition_ok=True, conforms=False,
            difference_kind="LINEA_SOBRANTE", note=(item.get("note") or None)))

    confirmacion.status = "CONFIRMED" if conforme else "REJECTED"
    destino = "CONFIRMED" if conforme else "PREPARING"
    _assert_transition(order.status, destino, ORDER_TRANSITIONS, "el pedido")
    order.status = destino
    order.updated_at = ahora
    db.flush()
    _audit(db, action=f"ORDER_CONFIRMATION_{confirmacion.status}", entity_type="OrderConfirmation",
           entity_id=str(confirmacion.id), company_id=company_id, actor=actor, reason=notes,
           before={"order_status": "PREPARED"},
           after={"status": confirmacion.status, "attempt": confirmacion.attempt,
                  "order_status": destino, "picklist_id": str(plan.id)})
    return confirmacion


def confirmation_dict(db: Session, confirmation: OrderConfirmation) -> dict:
    lineas = db.execute(
        select(OrderConfirmationLine)
        .where(OrderConfirmationLine.confirmation_id == str(confirmation.id))
        .order_by(OrderConfirmationLine.id)
    ).scalars().all()
    return {
        "id": str(confirmation.id), "order_id": str(confirmation.order_id),
        "picklist_id": str(confirmation.picklist_id), "attempt": confirmation.attempt,
        "status": confirmation.status, "checked_by": confirmation.checked_by,
        "checked_at": confirmation.checked_at.isoformat() if confirmation.checked_at else None,
        "notes": confirmation.notes,
        "lines": [{"order_line_id": str(ln.order_line_id) if ln.order_line_id else None,
                   "product_id": str(ln.product_id),
                   "required_base_quantity": str(_dec(ln.required_base_quantity)),
                   "prepared_base_quantity": str(_dec(ln.prepared_base_quantity)),
                   "checked_base_quantity": str(_dec(ln.checked_base_quantity)),
                   "presentation_id": str(ln.presentation_id) if ln.presentation_id else None,
                   "presentation_ok": ln.presentation_ok, "condition_ok": ln.condition_ok,
                   "conforms": ln.conforms, "difference_kind": ln.difference_kind,
                   "note": ln.note} for ln in lineas],
    }


def billing_eligibility(db: Session, *, company_id: str, order_id: str) -> dict:
    """La única autoridad que la Spec 034 debe consultar.

    El ¶83 dice que el Área de Confirmación **autoriza** que el pedido pueda
    facturarse, y el ¶89 que Facturación factura «sobre un pedido previamente
    confirmado». Esto responde esa pregunta en un sitio, no en varios indicios
    dispersos que alguien tenga que recomponer.
    """
    company_id = _company(company_id, obj="confirmación")
    order = _require_order(db, company_id, order_id)
    confirmacion = db.execute(
        select(OrderConfirmation).where(OrderConfirmation.order_id == str(order.id),
                                        OrderConfirmation.status == "CONFIRMED")
    ).scalars().first()
    return {
        "order_id": str(order.id), "order_status": order.status,
        "eligible_for_billing": confirmacion is not None and order.status == "CONFIRMED",
        "confirmation_id": str(confirmacion.id) if confirmacion else None,
        "confirmed_at": (confirmacion.checked_at.isoformat()
                         if confirmacion and confirmacion.checked_at else None),
        "checked_by": confirmacion.checked_by if confirmacion else None,
    }


# =========================================================================== #
# Spec 034 · liberación y facturación
#
# El ¶90 explica la separación que gobierna todo esto: «Almacén prepara.
# Confirmación verifica. **Facturación factura sobre un pedido previamente
# confirmado**». Aquí no se recoge, no se verifica de nuevo y no se despacha.
#
# El proceso separa dos actos que es fácil confundir: **generar la factura**
# (¶95) es comercial, y **emitir el documento fiscal** (¶97) es lo que consume
# correlativo y número de control. La 034 hace los dos, pero la numeración no es
# suya: la pide a la Spec 042, que la asigna atómicamente.
# =========================================================================== #


def _confirmacion_vigente(db: Session, company_id: str, order_id: str) -> OrderConfirmation:
    """La confirmación independiente sobre la que se factura (`B-060`)."""
    confirmacion = db.execute(
        select(OrderConfirmation).where(OrderConfirmation.company_id == company_id,
                                        OrderConfirmation.order_id == order_id,
                                        OrderConfirmation.status == "CONFIRMED")
    ).scalars().first()
    if confirmacion is None:
        raise ConflictError(
            code="BILLING_NOT_CONFIRMED",
            message="El pedido no tiene confirmación independiente: no se factura sin ella.")
    return confirmacion


def billable_orders(db: Session, *, company_id: str) -> list[SalesOrder]:
    """Pedidos confirmados a la espera de que se solicite su facturación (¶85)."""
    company_id = _company(company_id, obj="facturación")
    return list(db.execute(
        select(SalesOrder).where(SalesOrder.company_id == company_id,
                                 SalesOrder.status.in_(("CONFIRMED", "READY_FOR_BILLING")))
        .order_by(SalesOrder.updated_at.asc(), SalesOrder.id.asc())
    ).scalars().all())


def request_billing(db: Session, *, company_id: str, order_id: str,
                    actor: str | None = None) -> SalesOrder:
    """La solicitud de facturación del ¶84.

    El ¶83 dice que **el Área de Confirmación autoriza**; esto es esa
    autorización, con su autor y su momento. Sin los sellos, «solicitud
    explícita» sería solo un cambio de estado que nadie firmó.
    """
    company_id = _company(company_id, obj="facturación")
    order = _lock_order(db, company_id, order_id)
    if order.status != "CONFIRMED":
        raise ConflictError(code="BILLING_ORDER_NOT_CONFIRMED",
                            message="Solo se solicita la facturación de un pedido confirmado.")
    _confirmacion_vigente(db, company_id, str(order.id))
    ahora = datetime.now(UTC)
    _assert_transition(order.status, "READY_FOR_BILLING", ORDER_TRANSITIONS, "el pedido")
    order.status = "READY_FOR_BILLING"
    order.billing_requested_at = ahora
    order.billing_requested_by = actor
    order.updated_at = ahora
    db.flush()
    _audit(db, action="BILLING_REQUESTED", entity_type="SalesOrder", entity_id=str(order.id),
           company_id=company_id, actor=actor,
           before={"status": "CONFIRMED"}, after={"status": "READY_FOR_BILLING"})
    return order


def _precio_de(linea: SalesOrderLine) -> Decimal:
    """El precio **congelado** de la línea, no el del maestro de hoy.

    `resolved_unit_price` es lo que la Spec 029 dejó resuelto con su versión de
    lista; `unit_price` es lo que se tecleó. Ninguno se recalcula: cambiar una
    tarifa no puede reescribir una venta ya cerrada.
    """
    return _dec(linea.resolved_unit_price if linea.resolved_unit_price is not None
                else linea.unit_price)


def generate_invoice(db: Session, *, company_id: str, order_id: str,
                     actor: str | None = None) -> SalesInvoice:
    """Genera la factura del pedido y la asocia a él (¶95-96).

    Todo el contenido comercial sale de las líneas del pedido: cantidad tecleada,
    presentación, factor congelado, cantidad base, precio y descuento. El maestro
    actual no participa. El impuesto lo resuelve la Spec 039 con su regla
    versionada y fechada; aquí no hay ninguna tasa escrita.
    """
    company_id = _company(company_id, obj="facturación")
    order = _lock_order(db, company_id, order_id)
    if order.status != "READY_FOR_BILLING":
        raise ConflictError(
            code="BILLING_NOT_REQUESTED",
            message="La facturación no se ha solicitado para este pedido.")
    confirmacion = _confirmacion_vigente(db, company_id, str(order.id))

    viva = db.execute(
        select(SalesInvoice).where(SalesInvoice.order_id == str(order.id),
                                   SalesInvoice.status != "CANCELLED")
    ).scalars().first()
    if viva is not None:
        raise ConflictError(code="ORDER_ALREADY_INVOICED",
                            message="El pedido ya tiene una factura viva.",
                            details={"invoice_id": str(viva.id), "status": viva.status})

    lineas = list(db.execute(
        select(SalesOrderLine).where(SalesOrderLine.order_id == str(order.id))
        .order_by(SalesOrderLine.id)).scalars().all())
    if not lineas:
        raise ConflictError(code="BILLING_ORDER_EMPTY", message="El pedido no tiene líneas.")

    invoice = SalesInvoice(company_id=company_id,
                           customer_id=str(order.customer_id), order_id=str(order.id),
                           confirmation_id=str(confirmacion.id),
                           base_fiscal_currency=order.currency or "VED",
                           status="DRAFT", created_by=actor)
    db.add(invoice)
    db.flush()

    base_total = Decimal(0)
    impuesto_total = Decimal(0)
    for linea in lineas:
        cantidad = _dec(linea.quantity)
        precio = _precio_de(linea)
        descuento = _dec(linea.discount)
        base = cantidad * precio - descuento
        impuesto = Decimal(0)
        if linea.tax_ref:
            # La regla la elige el motor fiscal por código y fecha. Si la regla
            # no existe o no está vigente, esto falla: facturar con una regla
            # desconocida sería peor que no facturar.
            calculo = fiscal_service.calculate_tax(
                db, company_id=company_id, tax_code=linea.tax_ref, base=float(base),
                document_ref=f"INVOICE:{invoice.id}", line_ref=str(linea.id))
            impuesto = _dec(calculo.amount)
        db.add(SalesInvoiceLine(
            invoice_id=str(invoice.id), product_id=str(linea.product_id), quantity=cantidad,
            unit_price=precio, tax_amount=impuesto, base_fiscal=base, total=base + impuesto,
            uom_id=linea.uom_id, presentation_id=linea.presentation_id,
            conversion_factor_snapshot=linea.conversion_factor_snapshot,
            base_quantity=linea.base_quantity, uom_source=linea.uom_source,
            snapshot=linea.snapshot))
        base_total += base
        impuesto_total += impuesto

    invoice.base_fiscal = base_total
    invoice.tax_total = impuesto_total
    invoice.total = base_total + impuesto_total
    db.flush()
    _audit(db, action="INVOICE_GENERATED", entity_type="SalesInvoice", entity_id=str(invoice.id),
           company_id=company_id, actor=actor,
           after={"order_id": str(order.id), "confirmation_id": str(confirmacion.id),
                  "total": str(invoice.total), "lines": len(lineas)})
    return invoice


def issue_invoice(db: Session, *, company_id: str, invoice_id: str, series_id: str,
                  batch_id: str, actor: str | None = None) -> SalesInvoice:
    """Emite el documento fiscal (¶97) y deja el pedido facturado (¶99).

    La numeración **no es de esta Spec**: `emit_document` de la 042 consume el
    correlativo y el número de control en una sola transacción, y es idempotente
    por `INVOICE:{id}`. Reintentar no gasta dos números.

    Se recorre la máquina de la factura hasta `EMITTED` en vez de saltarla: los
    estados intermedios son de la Spec 005 y siguen disponibles para quien quiera
    separarlos en pasos humanos con el endpoint de transición.
    """
    company_id = _company(company_id, obj="facturación")
    invoice = db.execute(
        select(SalesInvoice).where(SalesInvoice.id == invoice_id).with_for_update()
    ).scalars().first()
    if invoice is None or str(invoice.company_id) != str(company_id):
        raise NotFoundError(code="SALES_INVOICE_NOT_FOUND", message="Factura de venta no encontrada")
    if invoice.status == "EMITTED":
        return invoice
    if invoice.order_id is None:
        raise ConflictError(code="INVOICE_WITHOUT_ORDER",
                            message="No se emite una factura que no está asociada a un pedido.")
    order = _lock_order(db, company_id, str(invoice.order_id))
    if order.status != "READY_FOR_BILLING":
        raise ConflictError(code="BILLING_ORDER_NOT_READY",
                            message="El pedido no está liberado para facturación.")
    _confirmacion_vigente(db, company_id, str(order.id))

    emitido = fiscal_service.emit_document(
        db, company_id=company_id, business_document=f"INVOICE:{invoice.id}",
        series_id=series_id, batch_id=batch_id, actor=actor)

    for destino in ("VALIDATED", "APPROVED", "EMITTED"):
        if invoice.status == destino:
            continue
        _assert_transition(invoice.status, destino, INVOICE_TRANSITIONS, "la factura de venta")
        invoice.status = destino
    ahora = datetime.now(UTC)
    invoice.invoice_number = emitido.get("invoice_number")
    invoice.control_number = emitido.get("control_number")
    invoice.fiscal_document_id = emitido.get("id")
    invoice.issued_at = ahora
    invoice.updated_at = ahora
    # «9. Emitir factura → 10. Crear CxC». Sin esto la factura salía al mundo sin
    # documento por cobrar y no había nada que la nota de crédito pudiera ajustar.
    _abrir_cuenta_por_cobrar(db, invoice)
    _assert_transition(order.status, "INVOICED", ORDER_TRANSITIONS, "el pedido")
    order.status = "INVOICED"
    order.invoiced_at = ahora
    order.updated_at = ahora
    db.flush()
    _audit(db, action="INVOICE_ISSUED", entity_type="SalesInvoice", entity_id=str(invoice.id),
           company_id=company_id, actor=actor,
           after={"invoice_number": invoice.invoice_number, "control_number": invoice.control_number,
                  "fiscal_document_id": invoice.fiscal_document_id, "order_status": "INVOICED"})
    return invoice


def order_invoice_dict(db: Session, *, company_id: str, order_id: str) -> dict:
    """El estado de facturación de un pedido, para la Spec 035.

    El ¶103 dice que el despacho verifica «Pedido preparado + Pedido confirmado +
    **Factura emitida**». Esto responde la tercera parte sin que la 035 tenga que
    reconstruirla.
    """
    company_id = _company(company_id, obj="facturación")
    order = _require_order(db, company_id, order_id)
    invoice = db.execute(
        select(SalesInvoice).where(SalesInvoice.company_id == company_id,
                                   SalesInvoice.order_id == str(order.id),
                                   SalesInvoice.status != "CANCELLED")
    ).scalars().first()
    return {
        "order_id": str(order.id), "order_status": order.status,
        "invoiced": invoice is not None and invoice.status == "EMITTED",
        "invoice": billing_invoice_dict(db, invoice) if invoice is not None else None,
    }


def billing_invoice_dict(db: Session, invoice: SalesInvoice) -> dict:
    """La factura con su origen y sus líneas, para la Spec 034.

    Se llama distinto del `invoice_dict` que ya existía a propósito: aquel
    serializa el listado de facturas de la Spec 005 y no lleva líneas ni
    procedencia. Dos nombres iguales en el mismo módulo habrían dejado uno
    muerto.
    """
    lineas = db.execute(
        select(SalesInvoiceLine).where(SalesInvoiceLine.invoice_id == str(invoice.id))
        .order_by(SalesInvoiceLine.id)).scalars().all()
    return {
        "id": str(invoice.id), "status": invoice.status,
        "order_id": str(invoice.order_id) if invoice.order_id else None,
        "confirmation_id": str(invoice.confirmation_id) if invoice.confirmation_id else None,
        "customer_id": str(invoice.customer_id),
        "currency": invoice.base_fiscal_currency,
        "base_fiscal": str(_dec(invoice.base_fiscal)),
        "tax_total": str(_dec(invoice.tax_total)),
        "total": str(_dec(invoice.total)),
        "invoice_number": invoice.invoice_number, "control_number": invoice.control_number,
        "fiscal_document_id": invoice.fiscal_document_id,
        "issued_at": invoice.issued_at.isoformat() if invoice.issued_at else None,
        # Visible a propósito: una línea sin clasificación fiscal factura sin
        # impuesto, y eso tiene que verse antes de emitir (¶93), no descubrirse
        # después en el libro.
        "lines_without_tax": sum(1 for ln in lineas if _dec(ln.tax_amount) == 0),
        "lines": [{"product_id": str(ln.product_id), "quantity": str(_dec(ln.quantity)),
                   "unit_price": str(_dec(ln.unit_price)),
                   "base_quantity": (str(_dec(ln.base_quantity))
                                     if ln.base_quantity is not None else None),
                   "presentation_id": str(ln.presentation_id) if ln.presentation_id else None,
                   "conversion_factor_snapshot": (str(_dec(ln.conversion_factor_snapshot))
                                                  if ln.conversion_factor_snapshot else None),
                   "tax_amount": str(_dec(ln.tax_amount)), "base_fiscal": str(_dec(ln.base_fiscal)),
                   "total": str(_dec(ln.total))} for ln in lineas],
    }


# =========================================================================== #
# Spec 035 · despacho, transporte y regulación
#
# El último acto del proceso, y el único en el que la mercancía cruza la puerta.
# El ¶103 dice qué se verifica antes de dejarla salir: «Pedido preparado +
# Pedido confirmado + Factura emitida». Ninguna de las tres se vuelve a hacer
# aquí —cada una tiene su Spec— pero las tres se comprueban, y la cuarta, la
# regulatoria, se le pide al módulo que ya sabía calcularla.
#
# El bloque empieza aquí y no donde empiece la primera función de despacho: los
# guardias de la 034 cortan por esta cabecera, y sin ella cualquier auxiliar que
# se añada delante de `create_shipment` acaba contándose como código de la 034.
# =========================================================================== #
def _live_shipment(db: Session, company_id: str, order_id: str) -> Shipment | None:
    """El despacho no cancelado de un pedido. Un pedido sale una vez."""
    return db.execute(
        select(Shipment).where(Shipment.company_id == company_id,
                               Shipment.order_id == str(order_id),
                               Shipment.status != "CANCELLED")).scalars().first()


def _require_vehicle(db: Session, company_id: str, vehicle_id: str) -> TransportVehicle:
    vehiculo = db.get(TransportVehicle, vehicle_id)
    if vehiculo is None or str(vehiculo.company_id) != str(company_id):
        raise NotFoundError(code="VEHICLE_NOT_FOUND", message="Vehículo no encontrado")
    return vehiculo


def _require_driver(db: Session, company_id: str, driver_id: str) -> TransportDriver:
    conductor = db.get(TransportDriver, driver_id)
    if conductor is None or str(conductor.company_id) != str(company_id):
        raise NotFoundError(code="DRIVER_NOT_FOUND", message="Conductor no encontrado")
    return conductor


def _lineas_consolidadas(db: Session, company_id: str, order: SalesOrder) -> list[dict]:
    """Lo que hay físicamente en el Área de Confirmación, para despacharlo.

    No se escribe a mano lo que sale: sale lo que la Spec 032 recogió y
    consolidó, con su lote y su serie. Escribir una cantidad aquí sería inventar
    un despacho parcial, y el proceso no lo contempla —la 033 no confirma un
    pedido incompleto y la 034 no lo factura a medias— (§21 del ciclo).

    El plan trabaja en unidad **base** y estas líneas heredan eso tal cual: sin
    presentación ni factor, porque la cifra no es de cajas. La vista comercial
    —dos cajas de doce— la tiene la factura, que es el documento que acompaña a
    la mercancía (¶106). Colgarle aquí una presentación que no corresponde a la
    cifra es exactamente el error que este ciclo encontró en la salida.
    """
    plan = db.execute(
        select(PickList).where(PickList.company_id == company_id,
                               PickList.order_id == str(order.id),
                               PickList.status == "CLOSED")
        .order_by(PickList.consolidated_at.desc())).scalars().first()
    if plan is None:
        return []
    paradas = db.execute(
        select(PickListLine).where(PickListLine.picklist_id == str(plan.id))
        .order_by(PickListLine.sequence, PickListLine.id)).scalars().all()
    return [{"product_id": str(p.product_id), "quantity": _dec(p.quantity),
             "base_quantity": (p.picked_base_quantity if p.picked_base_quantity is not None
                               else p.base_quantity),
             "uom_id": p.uom_id, "presentation_id": p.presentation_id,
             "conversion_factor_snapshot": p.conversion_factor_snapshot,
             "lot_id": p.lot_id, "serial_id": p.serial_id}
            for p in paradas if p.picked_at is not None]


def create_shipment(db: Session, *, company_id: str, code: str, order_id: str,
                    origin_warehouse_id: str | None = None,
                    destination: str | None = None, transport: str | None = None,
                    vehicle_id: str | None = None, driver_id: str | None = None,
                    lines: list[dict] | None = None, actor: str | None = None) -> Shipment:
    """Registra la salida de un pedido **facturado** (¶101).

    El almacén de origen no se pregunta: la mercancía está consolidada en el del
    pedido y elegir otro sería describir un traslado que no ocurrió. Se admite
    explícito porque las pruebas lo usan para probar el ajeno.
    """
    company_id = _company(company_id, obj="despacho")
    order = _require_order(db, company_id, order_id)
    origin_warehouse_id = origin_warehouse_id or str(order.warehouse_id)
    _require_warehouse(db, company_id, origin_warehouse_id)
    # `SHIPPED` se admitía aquí para que el segundo despacho llegara al índice
    # de la base. Con la comprobación de abajo esa rama era inalcanzable, y una
    # rama inalcanzable en una compuerta dice que se puede algo que no se puede.
    if order.status != "INVOICED":
        raise ConflictError(code="ORDER_NOT_SHIPPABLE",
                            message="Solo un pedido facturado pasa a despacho.")
    # Quien de verdad impide el segundo despacho es `uq_shipments_live_order`,
    # que es lo único que resiste a dos despachadores simultáneos. Esta
    # comprobación existe para que el caso corriente —alguien pulsa dos veces—
    # reciba un conflicto legible en vez del error de integridad en crudo.
    if _live_shipment(db, company_id, str(order.id)) is not None:
        raise ConflictError(code="ORDER_ALREADY_SHIPPED",
                            message="El pedido ya tiene un despacho vivo.")
    # El ¶105 admite «transportista, cliente o responsable»; ninguno es
    # obligatorio, pero el que se indique tiene que ser de esta empresa.
    if vehicle_id:
        _require_vehicle(db, company_id, vehicle_id)
    if driver_id:
        _require_driver(db, company_id, driver_id)
    shipment = Shipment(company_id=company_id, code=code, order_id=order_id, origin_warehouse_id=origin_warehouse_id,
                        destination=destination, transport=transport, status="DRAFT", validation_status="PENDING",
                        vehicle_id=vehicle_id, driver_id=driver_id, created_by=actor)
    db.add(shipment)
    db.flush()
    for item in lines if lines is not None else _lineas_consolidadas(db, company_id, order):
        db.add(ShipmentLine(shipment_id=str(shipment.id), product_id=item["product_id"],
                            lot_id=item.get("lot_id"), serial_id=item.get("serial_id"),
                            quantity=item.get("quantity", 0.0),
                            base_quantity=item.get("base_quantity"),
                            uom_id=item.get("uom_id"),
                            presentation_id=item.get("presentation_id"),
                            conversion_factor_snapshot=item.get("conversion_factor_snapshot")))
    return shipment


def validate_shipment(db: Session, *, shipment: Shipment, actor: str | None = None) -> Shipment:
    """La compuerta del ¶103, que hasta este ciclo aprobaba siempre.

    «Se verifica que corresponda: **Pedido preparado + Pedido confirmado +
    Factura emitida**». Las tres tienen autoridad consultable —la 032, la 033 y
    la 034— y aquí se consultan las tres. La cuarta, la regulatoria, la resuelve
    `regulatory.evaluate_shipment`, que existía y a la que el despacho no
    llamaba.

    Aprobar sin comprobar no era una simplificación: era una compuerta que
    dejaba salir cualquier cosa mientras su docstring decía lo contrario.
    """
    if shipment.status != "DRAFT":
        raise ConflictError(code="SHIPMENT_STATE", message="El despacho ya fue procesado.")
    company_id = str(shipment.company_id)
    order = _lock_order(db, company_id, str(shipment.order_id))

    # 1 y 2 · preparado y confirmado. El estado del pedido no basta: la Spec 033
    # ya demostró que un estado se puede poner a mano.
    confirmacion = db.execute(
        select(OrderConfirmation).where(OrderConfirmation.company_id == company_id,
                                        OrderConfirmation.order_id == str(order.id),
                                        OrderConfirmation.status == "CONFIRMED")
    ).scalars().first()
    if confirmacion is None:
        raise ConflictError(
            code="DISPATCH_NOT_CONFIRMED",
            message="El pedido no tiene confirmación independiente: no sale del almacén sin ella.")

    # 3 · factura **emitida**, no generada. El ¶95 y el ¶97 son dos actos y el
    # ¶103 exige el segundo.
    factura = db.execute(
        select(SalesInvoice).where(SalesInvoice.company_id == company_id,
                                   SalesInvoice.order_id == str(order.id),
                                   SalesInvoice.status != "CANCELLED")
    ).scalars().first()
    if factura is None or factura.status != "EMITTED":
        raise ConflictError(
            code="DISPATCH_NOT_INVOICED",
            message="El pedido no tiene factura emitida: la mercancía sale con su factura.")
    if order.status != "INVOICED":
        raise ConflictError(code="DISPATCH_ORDER_NOT_INVOICED",
                            message="El pedido no está facturado.")

    # 4 · el mecanismo de entrega y su destino (¶105). No se exige transportista:
    # el proceso admite «transportista, cliente o responsable del traslado».
    if not (shipment.destination or "").strip() or not (shipment.transport or "").strip():
        raise KontrolError(
            code="DISPATCH_TRANSPORT_REQUIRED",
            message="Indique el destino y a quién se entrega la mercancía.", status_code=422)

    # 5 · los requisitos regulatorios que apliquen, uno por uno. Sin API oficial
    # la validación es contra lo registrado: se registra, se valida, se adjunta y
    # se bloquea; **no se emite ni se verifica en línea** (Spec 044, v1).
    evaluacion = regulatory_service.evaluate_shipment(
        db, company_id=company_id, shipment_id=str(shipment.id), actor=actor)
    shipment.regulatory_status = evaluacion["status"]
    if evaluacion["status"] == "BLOCKED":
        db.flush()
        raise ConflictError(
            code="DISPATCH_REGULATORY_BLOCKED",
            message=f"Faltan requisitos regulatorios en {evaluacion['blocked']} línea(s).",
            details={"evaluated": evaluacion["evaluated"], "blocked": evaluacion["blocked"]})

    ahora = datetime.now(UTC)
    shipment.invoice_id = str(factura.id)
    shipment.validation_status = "APPROVED"
    shipment.status = "READY"
    shipment.validated_at = ahora
    shipment.validated_by = actor
    shipment.updated_at = ahora
    db.flush()
    _audit(db, action="SHIPMENT_VALIDATED", entity_type="Shipment", entity_id=str(shipment.id),
           company_id=company_id, actor=actor,
           after={"invoice_id": str(factura.id), "confirmation_id": str(confirmacion.id),
                  "regulatory_status": evaluacion["status"]})
    return shipment


def confirm_shipment(db: Session, *, shipment: Shipment, actor: str | None = None) -> Shipment:
    """Confirma la salida invocando el motor de 003 `ship` (FR-005-022).

    Registra las salidas y libera las reservas cumplidas de la orden.
    """
    if shipment.dispatched_at is not None:
        return shipment
    if shipment.status != "READY" or shipment.validation_status != "APPROVED":
        raise ConflictError(code="SHIPMENT_NOT_VALIDATED", message="El despacho requiere validación documental.")
    company_id = str(shipment.company_id)
    order = _lock_order(db, company_id, str(shipment.order_id))
    lines = db.execute(select(ShipmentLine).where(ShipmentLine.shipment_id == shipment.id)).scalars().all()
    if not lines:
        raise ConflictError(code="SHIPMENT_EMPTY", message="El despacho no tiene líneas.")
    plan = db.execute(
        select(PickList).where(PickList.company_id == company_id,
                               PickList.order_id == str(order.id),
                               PickList.status == "CLOSED")
        .order_by(PickList.consolidated_at.desc())).scalars().first()
    if plan is None or plan.consolidation_location_id is None:
        raise ConflictError(code="DISPATCH_WITHOUT_PREPARATION",
                            message="El pedido no tiene una preparación consolidada de la que salir.")
    for line in lines:
        # En cantidad **base**: despachar dos cajas de doce saca veinticuatro
        # unidades, no dos. Y desde `PREPARADO` en el Área de Confirmación, que
        # es donde la Spec 032 dejó la mercancía: descontar de `DISPONIBLE`
        # tocaría una fila que ya no tiene esas unidades.
        salida = _dec(line.base_quantity if line.base_quantity is not None else line.quantity)
        inv_service.reclassify(
            db, company_id=company_id, warehouse_id=str(shipment.origin_warehouse_id),
            product_id=str(line.product_id), source_state="PREPARADO", target_state="DESPACHADO",
            quantity=salida, location_id=str(plan.consolidation_location_id),
            lot_id=line.lot_id, serial_id=line.serial_id,
            document_ref=f"SHIPMENT:{shipment.id}", actor=actor)
    # La salida física **consume** la reserva (R-D0-03-7): `FULFILLED`, no
    # `RELEASED`. Lo que salió no vuelve al disponible.
    for reservation in inv_service.order_reservations(db, company_id=shipment.company_id, order_id=str(order.id)):
        inv_service.fulfill_reservation(db, reservation=reservation, actor=actor)
    ahora = datetime.now(UTC)
    shipment.status = "SHIPPED"
    shipment.dispatched_at = ahora
    shipment.dispatched_by = actor
    shipment.updated_at = ahora
    _assert_transition(order.status, "SHIPPED", ORDER_TRANSITIONS, "el pedido")
    order.status = "SHIPPED"
    order.updated_at = ahora
    db.flush()
    _audit(db, action="SHIPMENT_CONFIRMED", entity_type="Shipment", entity_id=str(shipment.id),
           company_id=shipment.company_id, actor=actor, after={"order_id": str(order.id)})
    return shipment


def shipment_dict(db: Session, shipment: Shipment) -> dict:
    """El despacho entero, incluida la razón por la que puede o no salir."""
    lineas = db.execute(
        select(ShipmentLine).where(ShipmentLine.shipment_id == str(shipment.id))
        .order_by(ShipmentLine.id)).scalars().all()
    return {
        "id": str(shipment.id), "code": shipment.code, "order_id": str(shipment.order_id),
        "origin_warehouse_id": str(shipment.origin_warehouse_id),
        "status": shipment.status, "validation_status": shipment.validation_status,
        "regulatory_status": shipment.regulatory_status,
        "invoice_id": str(shipment.invoice_id) if shipment.invoice_id else None,
        "destination": shipment.destination, "transport": shipment.transport,
        "vehicle_id": str(shipment.vehicle_id) if shipment.vehicle_id else None,
        "driver_id": str(shipment.driver_id) if shipment.driver_id else None,
        "validated_at": shipment.validated_at.isoformat() if shipment.validated_at else None,
        "validated_by": shipment.validated_by,
        "dispatched_at": shipment.dispatched_at.isoformat() if shipment.dispatched_at else None,
        "dispatched_by": shipment.dispatched_by,
        "lines": [{"product_id": str(ln.product_id), "quantity": str(_dec(ln.quantity)),
                   "base_quantity": (str(_dec(ln.base_quantity))
                                     if ln.base_quantity is not None else None),
                   "presentation_id": str(ln.presentation_id) if ln.presentation_id else None,
                   "conversion_factor_snapshot": (str(_dec(ln.conversion_factor_snapshot))
                                                  if ln.conversion_factor_snapshot else None),
                   "lot_id": ln.lot_id, "serial_id": ln.serial_id} for ln in lineas],
    }


def dispatch_queue(db: Session, *, company_id: str) -> list[dict]:
    """Los pedidos facturados que esperan salida.

    El orden es por `invoiced_at` y es **presentacional**: a diferencia de la
    cola de picking, aquí no se reparte nada escaso —la mercancía de cada pedido
    ya está consolidada y apartada—, así que este orden no decide quién cobra
    primero ni necesita una decisión material que lo respalde.
    """
    company_id = _company(company_id, obj="cola de despacho")
    pedidos = db.execute(
        select(SalesOrder).where(SalesOrder.company_id == company_id,
                                 SalesOrder.status == "INVOICED")
        .order_by(SalesOrder.invoiced_at, SalesOrder.id)).scalars().all()
    salida = []
    for pedido in pedidos:
        factura = db.execute(
            select(SalesInvoice).where(SalesInvoice.company_id == company_id,
                                       SalesInvoice.order_id == str(pedido.id),
                                       SalesInvoice.status != "CANCELLED")).scalars().first()
        despacho = _live_shipment(db, company_id, str(pedido.id))
        salida.append({
            "order_id": str(pedido.id), "code": pedido.code, "status": pedido.status,
            "invoice_id": str(factura.id) if factura else None,
            "invoice_number": factura.invoice_number if factura else None,
            "invoice_status": factura.status if factura else None,
            "shipment_id": str(despacho.id) if despacho else None,
            "shipment_code": despacho.code if despacho else None,
            "shipment_status": despacho.status if despacho else None,
        })
    return salida


def order_dispatch_dict(db: Session, *, company_id: str, order_id: str) -> dict:
    company_id = _company(company_id, obj="despacho")
    order = _require_order(db, company_id, order_id)
    despacho = _live_shipment(db, company_id, str(order.id))
    return {"order_id": str(order.id), "order_status": order.status,
            "shipment": shipment_dict(db, despacho) if despacho else None}


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
    invoice.total = _dec(invoice.base_fiscal) + _dec(invoice.tax_total)
    db.flush()
    return invoice


def _abrir_cuenta_por_cobrar(db: Session, invoice: SalesInvoice) -> OpenItem | None:
    """Crea el documento por cobrar de una factura emitida. Idempotente.

    Delta dirigido de la Spec 036 sobre la 034. El proceso de ventas dice
    «9. Emitir factura → **10. Crear CxC**», y esto solo ocurría por el camino
    heredado `transition_invoice`. `issue_invoice` —el camino que la 034
    construyó y el único que emite el documento fiscal— ponía el estado a mano y
    se saltaba la creación: las facturas emitidas por el proceso real nacían sin
    cuenta por cobrar. Se descubrió al ir a aplicarles una nota de crédito y no
    encontrar nada que ajustar.
    """
    existente = db.execute(
        select(OpenItem).where(OpenItem.company_id == invoice.company_id,
                               OpenItem.source_document == f"SALES_INVOICE:{invoice.id}")
    ).scalars().first()
    if existente is not None:
        return existente
    item = OpenItem(company_id=invoice.company_id, party_id=invoice.customer_id,
                    source_document=f"SALES_INVOICE:{invoice.id}", item_type="RECEIVABLE",
                    currency=invoice.base_fiscal_currency, original=invoice.total, applied=0.0,
                    due_date=hoy_de_negocio(), status="OPEN")
    db.add(item)
    db.flush()
    return item


def transition_invoice(db: Session, *, invoice: SalesInvoice, target: str, actor: str | None = None) -> SalesInvoice:
    """Transición de la factura. Al emitir (EMITTED) se crea el OpenItem RECEIVABLE (FR-005-040)."""
    _assert_transition(invoice.status, target, INVOICE_TRANSITIONS, "la factura de venta")
    invoice.status = target
    invoice.updated_at = datetime.now(UTC)
    if target == "EMITTED":
        _abrir_cuenta_por_cobrar(db, invoice)
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
           company_id=note.company_id, actor=None, after={"amount": str(_dec(note.amount))})
    return note


def apply_credit_note(db: Session, *, note: SalesCreditNote, target_open_item_id: str,
                      amount: Decimal | float, actor: str | None = None):
    """Aplica el crédito de una nota a un documento por cobrar (Spec 037).

    Tres cosas que antes no hacía y que no son opcionales:

    **Comprueba el cliente.** Comprobaba la empresa y nada más, así que el
    crédito de un cliente podía aplicarse al documento de otro dentro de la
    misma empresa. Un crédito es de quien lo tiene.

    **Deja rastro.** Mutaba los dos saldos y no escribía nada. La arquitectura
    funcional §9 dice que «cada aplicación relaciona origen, destino, moneda,
    tasa, monto nominal, monto fiscal y fecha»: una aplicación sin fila no se
    puede reconstruir, ni auditar, ni revertir.

    **Exige la misma moneda.** Las diferencias cambiarias «se calculan al
    aplicar o valorar **según política**», y esa política no existe todavía.
    Aplicar entre monedas sin ella sería inventar un tipo de cambio.
    """
    aplicar = _dec(amount)
    if aplicar <= 0:
        raise KontrolError(code="INVALID_AMOUNT", message="El monto a aplicar debe ser positivo", status_code=422)
    target = db.execute(
        select(OpenItem).where(OpenItem.id == target_open_item_id).with_for_update()
    ).scalars().first()
    if not target or str(target.company_id) != str(note.company_id):
        raise NotFoundError(code="OPEN_ITEM_NOT_FOUND", message="Documento de CxC no encontrado")
    # La empresa no basta: el crédito es del cliente que lo tiene.
    if str(target.party_id) != str(note.customer_id):
        raise ConflictError(
            code="CREDIT_CUSTOMER_MISMATCH",
            message="El crédito de un cliente no se aplica al documento de otro.",
            details={"credit_customer_id": str(note.customer_id),
                     "document_customer_id": str(target.party_id)})
    if (target.currency or "") != (note.currency or ""):
        raise ConflictError(
            code="CREDIT_CURRENCY_MISMATCH",
            message="No se aplica un crédito en otra moneda: falta la política de diferencia cambiaria.",
            details={"credit_currency": note.currency, "document_currency": target.currency})
    if target.status != "OPEN":
        raise ConflictError(code="OPEN_ITEM_CLOSED", message="El documento de CxC está cerrado.")
    balance = ap_service.open_item_balance(target)
    # Lo aplicable es lo emitido menos **las tres formas de gastarlo**: lo ya
    # aplicado a documentos, lo reservado para una devolución en dinero y lo ya
    # devuelto. Delta dirigido de la Spec 038: hasta que existió el reembolso
    # solo había una forma, y esta resta solo contemplaba esa. Con dos, el mismo
    # crédito podía reservarse para devolver y aplicarse a una factura.
    remaining = (_dec(note.amount) - _dec(note.applied)
                 - _dec(note.refund_reserved) - _dec(note.refunded))
    if aplicar > balance:
        raise ConflictError(code="APPLICATION_EXCEEDS_BALANCE", message=f"La aplicación excede el saldo ({balance}).")
    if aplicar > remaining:
        raise ConflictError(code="APPLICATION_EXCEEDS_SOURCE", message=f"La nota no tiene saldo disponible ({remaining}).")
    target.applied = _dec(target.applied) + aplicar
    if ap_service.open_item_balance(target) <= 0:
        target.status = "CLOSED"
    note.applied = _dec(note.applied) + aplicar
    # El hecho económico, con su fila. `rate` es 1 porque origen y destino están
    # en la misma moneda: no hay conversión que registrar.
    db.add(Application(company_id=str(note.company_id), source_type="CREDIT",
                       source_id=str(note.id), target_open_item_id=str(target.id),
                       amount=aplicar, currency=note.currency or "VED",
                       rate=Decimal(1), date=hoy_de_negocio(), status="APPLIED"))
    db.flush()
    _sync_invoice_status(db, target_open_item_id=str(target.id))
    _audit(db, action="CREDIT_NOTE_APPLIED", entity_type="SalesCreditNote", entity_id=str(note.id),
           company_id=note.company_id, actor=actor,
           after={"open_item_id": str(target.id), "customer_id": str(note.customer_id),
                  "amount": str(aplicar), "currency": note.currency})
    return target


def customer_balance(db: Session, *, company_id: str, customer_id: str) -> dict:
    """El saldo del cliente, tal como lo escribe la arquitectura funcional §9.

    > CxC — Saldo = documentos + débitos − cobros − retenciones − créditos.

    Cada sumando es una consulta, no un campo guardado: «los saldos **no se
    editan**; se calculan desde movimientos y aplicaciones».

    Los débitos no se suman aparte porque la nota de débito **crea su propio
    documento por cobrar** (Spec 036): ya está dentro de «documentos». Y los
    cobros y las retenciones entran como lo aplicado a esos documentos, que es
    donde el motor de la 028 los registra.

    El crédito se resta **una sola vez**. Un crédito sin imputar ya baja el
    saldo del cliente —eso es tener saldo a favor—; al imputarlo, baja el
    documento y baja el crédito disponible en la misma cantidad, y el neto no se
    mueve. Imputar no crea ni destruye dinero.

    Con el reembolso de la Spec 038 hay **dos cifras distintas** donde antes
    bastaba una, y confundirlas es contar el mismo dinero dos veces:

    - `credit_available` es lo **imputable** a documentos. Lo reservado para
      devolver en efectivo ya no lo es: está comprometido.
    - el crédito que baja el saldo es lo que todavía **se debe** al cliente.
      Una reserva sin ejecutar se sigue debiendo —solo cambió la forma en que
      se pagará—, así que el saldo no se mueve al reservar. Se mueve al
      ejecutar: ahí salió el dinero del banco y la deuda quedó pagada.

    Antes de la 038 ambas restas coincidían porque reservado y devuelto eran
    siempre cero; ninguna cifra ya certificada cambia de valor.
    """
    company_id = _company(company_id, obj="saldo del cliente")
    documentos = db.execute(
        select(OpenItem).where(OpenItem.company_id == company_id,
                               OpenItem.party_id == str(customer_id),
                               OpenItem.item_type == "RECEIVABLE")).scalars().all()
    original = sum((_dec(x.original) for x in documentos), Decimal(0))
    aplicado = sum((_dec(x.applied) for x in documentos), Decimal(0))

    notas = db.execute(
        select(SalesCreditNote).where(SalesCreditNote.company_id == company_id,
                                      SalesCreditNote.customer_id == str(customer_id),
                                      SalesCreditNote.status != "CANCELLED")).scalars().all()
    creditos = sum((_dec(n.amount) for n in notas), Decimal(0))
    credito_aplicado = sum((_dec(n.applied) for n in notas), Decimal(0))
    credito_reservado = sum((_dec(n.refund_reserved) for n in notas), Decimal(0))
    credito_devuelto = sum((_dec(n.refunded) for n in notas), Decimal(0))

    # `documentos − aplicado` es lo que queda por cobrar de los documentos. Lo
    # aplicado incluye los cobros, las retenciones y los créditos ya imputados,
    # así que al restar los créditos hay que restar **solo los no imputados**:
    # los imputados ya están dentro de `aplicado`.
    pendiente_documentos = original - aplicado
    credito_imputable = creditos - credito_aplicado - credito_reservado - credito_devuelto
    credito_por_pagar = creditos - credito_aplicado - credito_devuelto
    return {
        "customer_id": str(customer_id),
        "documents": str(original),
        "applied": str(aplicado),
        "outstanding": str(pendiente_documentos),
        "credits": str(creditos),
        "credit_applied": str(credito_aplicado),
        "credit_refund_reserved": str(credito_reservado),
        "credit_refunded": str(credito_devuelto),
        "credit_available": str(credito_imputable),
        "balance": str(pendiente_documentos - credito_por_pagar),
    }


def customer_credits(db: Session, *, company_id: str, customer_id: str) -> list[dict]:
    """Los créditos del cliente con importe todavía sin aplicar.

    Es lo que la pantalla necesita para ofrecer un origen, y lo calcula el
    backend: el remanente no se acepta del navegador.
    """
    company_id = _company(company_id, obj="créditos del cliente")
    notas = db.execute(
        select(SalesCreditNote).where(SalesCreditNote.company_id == company_id,
                                      SalesCreditNote.customer_id == str(customer_id),
                                      SalesCreditNote.status != "CANCELLED")
        .order_by(SalesCreditNote.issued_at)).scalars().all()
    salida = []
    for n in notas:
        # Lo reservado por un reembolso (Spec 038) y lo ya devuelto **no** están
        # disponibles: son el mismo dinero. Ofrecerlos aquí sería enseñar dos
        # veces el saldo y dejar que la pantalla intente aplicar algo que el
        # servicio rechaza. Es la misma resta que usa el estado de cuenta.
        disponible = (_dec(n.amount) - _dec(n.applied)
                      - _dec(n.refund_reserved) - _dec(n.refunded))
        if disponible <= 0:
            continue
        salida.append({
            "id": str(n.id), "number": n.invoice_number or n.number,
            "control_number": n.control_number, "cause": n.cause,
            "invoice_id": str(n.invoice_id) if n.invoice_id else None,
            "currency": n.currency, "amount": str(_dec(n.amount)),
            "applied": str(_dec(n.applied)),
            "refund_reserved": str(_dec(n.refund_reserved)),
            "refunded": str(_dec(n.refunded)),
            "available": str(disponible),
            "issued_at": n.issued_at.isoformat() if n.issued_at else None,
        })
    return salida


def open_item_applications(db: Session, *, company_id: str, open_item_id: str) -> list[dict]:
    """Lo aplicado a un documento, incluidos los reversos.

    Los reversos están porque «no eliminan»: la historia de un documento
    incluye lo que se le aplicó y lo que se le deshizo.
    """
    company_id = _company(company_id, obj="aplicaciones")
    item = db.get(OpenItem, open_item_id)
    if item is None or str(item.company_id) != str(company_id):
        raise NotFoundError(code="OPEN_ITEM_NOT_FOUND", message="Documento de CxC no encontrado")
    filas = db.execute(
        select(Application).where(Application.company_id == company_id,
                                  Application.target_open_item_id == str(item.id))
        .order_by(Application.created_at)).scalars().all()
    return [{"id": str(a.id), "source_type": a.source_type, "source_id": str(a.source_id),
             "target_open_item_id": str(a.target_open_item_id),
             "amount": str(_dec(a.amount)), "currency": a.currency,
             "rate": str(_dec(a.rate)) if a.rate is not None else None,
             "date": a.date.isoformat() if a.date else None, "status": a.status,
             "created_at": a.created_at.isoformat() if a.created_at else None}
            for a in filas]


def customer_statement(db: Session, *, company_id: str, customer_id: str) -> dict:
    """El estado de cuenta: la cronología que lo explica.

    No es aritmética de pantalla. Cada línea es un hecho económico con su
    documento detrás, y el saldo final es el mismo que devuelve
    `customer_balance`.
    """
    company_id = _company(company_id, obj="estado de cuenta")
    entradas: list[dict] = []
    for item in db.execute(
            select(OpenItem).where(OpenItem.company_id == company_id,
                                   OpenItem.party_id == str(customer_id),
                                   OpenItem.item_type == "RECEIVABLE")
            .order_by(OpenItem.created_at)).scalars().all():
        entradas.append({
            "type": "DOCUMENT", "id": str(item.id), "reference": item.source_document,
            "date": item.created_at.isoformat() if item.created_at else None,
            "currency": item.currency, "debit": str(_dec(item.original)),
            "credit": "0", "outstanding": str(ap_service.open_item_balance(item)),
            "status": item.status,
        })
    for nota in db.execute(
            select(SalesCreditNote).where(SalesCreditNote.company_id == company_id,
                                          SalesCreditNote.customer_id == str(customer_id),
                                          SalesCreditNote.status != "CANCELLED")
            .order_by(SalesCreditNote.created_at)).scalars().all():
        entradas.append({
            "type": "CREDIT_NOTE", "id": str(nota.id),
            "reference": nota.invoice_number or nota.number,
            "date": nota.issued_at.isoformat() if nota.issued_at else None,
            "currency": nota.currency, "debit": "0", "credit": str(_dec(nota.amount)),
            "available": str(_dec(nota.amount) - _dec(nota.applied)), "status": nota.status,
        })
        for app in db.execute(
                select(Application).where(Application.company_id == company_id,
                                          Application.source_type == "CREDIT",
                                          Application.source_id == str(nota.id))
                .order_by(Application.created_at)).scalars().all():
            entradas.append({
                "type": "APPLICATION" if app.status == "APPLIED" else "APPLICATION_REVERSAL",
                "id": str(app.id), "reference": str(app.target_open_item_id),
                "date": app.date.isoformat() if app.date else None,
                "currency": app.currency, "debit": "0", "credit": str(_dec(app.amount)),
                "status": app.status,
            })
    entradas.sort(key=lambda x: (x["date"] or ""))
    saldo = customer_balance(db, company_id=company_id, customer_id=customer_id)
    return {"customer_id": str(customer_id), "entries": entradas, **saldo}


def reverse_credit_application(db: Session, *, company_id: str, application_id: str,
                               reason: str, actor: str | None = None) -> Application:
    """Revierte una aplicación de crédito **sin borrarla**.

    «Los reversos **no eliminan**; crean evento inverso y reapertura
    controlada» (arquitectura funcional §9). La fila original se queda donde
    está: lo que hubo, hubo. Lo que se añade es su inverso, y el documento y el
    crédito vuelven a quedar disponibles por ese importe.
    """
    company_id = _company(company_id, obj="reverso de aplicación")
    original = db.execute(
        select(Application).where(Application.id == application_id).with_for_update()
    ).scalars().first()
    if original is None or str(original.company_id) != str(company_id):
        raise NotFoundError(code="APPLICATION_NOT_FOUND", message="Aplicación no encontrada")
    if original.source_type != "CREDIT":
        raise ConflictError(code="APPLICATION_NOT_CREDIT",
                            message="Este reverso es el de una aplicación de crédito.")
    if original.status != "APPLIED":
        raise ConflictError(code="APPLICATION_ALREADY_REVERSED",
                            message="La aplicación ya fue revertida.")
    if not (reason or "").strip():
        raise KontrolError(code="REVERSAL_REASON_REQUIRED",
                           message="Revertir una aplicación exige motivo.", status_code=422)

    nota = db.get(SalesCreditNote, str(original.source_id))
    target = db.execute(
        select(OpenItem).where(OpenItem.id == str(original.target_open_item_id)).with_for_update()
    ).scalars().first()
    if nota is None or target is None:
        raise NotFoundError(code="APPLICATION_NOT_FOUND", message="Aplicación no encontrada")

    importe = _dec(original.amount)
    target.applied = _dec(target.applied) - importe
    # Reapertura controlada: el documento vuelve a estar abierto porque vuelve a
    # tener saldo, no porque alguien le cambie el estado a mano.
    if ap_service.open_item_balance(target) > 0:
        target.status = "OPEN"
    nota.applied = _dec(nota.applied) - importe
    original.status = "REVERSED"
    inverso = Application(company_id=company_id, source_type="CREDIT",
                          source_id=str(nota.id), target_open_item_id=str(target.id),
                          amount=-importe, currency=original.currency,
                          rate=original.rate, date=hoy_de_negocio(), status="REVERSAL")
    db.add(inverso)
    db.flush()
    _sync_invoice_status(db, target_open_item_id=str(target.id))
    _audit(db, action="CREDIT_APPLICATION_REVERSED", entity_type="Application",
           entity_id=str(original.id), company_id=company_id, actor=actor,
           after={"reversal_id": str(inverso.id), "amount": str(importe), "reason": reason})
    return inverso


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
        invoice.status = "PAID" if ap_service.open_item_balance(item) <= 0 else "PARTIALLY_PAID"
        invoice.updated_at = datetime.now(UTC)


def apply_to_cxc(db: Session, *, company_id: str, source_type: str, source_id: str, target_open_item_id: str,
                 amount: float, currency: str = "VED", rate: float | None = None, actor: str | None = None):
    """Aplica cobro/anticipo/retención a un open item RECEIVABLE (reutiliza 004) y sincroniza la factura de venta."""
    app = ap_service.apply_source(db, company_id=company_id, source_type=source_type, source_id=source_id,
                                  target_open_item_id=target_open_item_id, amount=amount, currency=currency,
                                  rate=rate, actor=actor)
    _sync_invoice_status(db, target_open_item_id=target_open_item_id)
    _audit(db, action="CXC_APPLICATION", entity_type="OpenItem", entity_id=str(target_open_item_id),
           company_id=company_id, actor=actor, after={"source_type": source_type, "amount": str(_dec(amount))})
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


# =========================================================================== #
# Spec 036 · devoluciones, notas de crédito y notas de débito
#
# La norma escribe el proceso entero y en este orden: «Solicitud → Verificación
# física → Aprobación → **Entrada de inventario** → Nota de crédito vinculada →
# Ajuste de IVA → Ajuste de cuenta por cobrar → Registro en libro de ventas».
#
# Cuatro actos antes de tocar el inventario. Una solicitud no aumenta
# existencia; recibir la mercancía tampoco la hace vendible. Y la nota va
# **después** y **vinculada**, porque «la devolución física no sustituye una
# nota de crédito» (documento maestro) y porque emitirla es un acto fiscal con
# su consecutivo y su número de control, igual que la 034 separó generar la
# factura de emitir el documento.
#
# Lo que no se decide aquí: los estados de mercancía son de `D0-10`, que concede
# a esta Spec exactamente `DESPACHADO → DEVUELTO` y `DEVUELTO → DISPONIBLE ·
# RECHAZADO`; las reservas son de `D0-03`, que dice «re-reservar tras liberar =
# nueva fila, nunca reactivación» y por eso una devolución no resucita ninguna;
# la numeración es de la 042; el efecto en CxC es del motor de la 004/037.
# =========================================================================== #

#: Los actos del flujo, cada uno un estado. No son nombres inventados: son las
#: cuatro etapas que la norma nombra, más el cierre y las dos salidas.
RETURN_TRANSITIONS: dict[str, set[str]] = {
    "REQUESTED": {"RECEIVED", "CANCELLED"},
    "RECEIVED": {"INSPECTED", "CANCELLED"},
    "INSPECTED": {"APPROVED", "REJECTED"},
    "APPROVED": {"CLOSED"},
    "CLOSED": set(),
    "REJECTED": set(),
    "CANCELLED": set(),
    # Estado de las devoluciones anteriores a esta Spec. No se migra ni se
    # reinterpreta: sin factura ni despacho detrás no hay forma de saber qué era.
    "DRAFT": set(),
}

#: `D0-10`: «`DEVUELTO` → `DISPONIBLE` · `RECHAZADO` | 036». Dos, no cinco. Los
#: otros destinos que la arquitectura funcional nombra tienen otro dueño:
#: `CUARENTENA` entra por la incidencia de la 020 y `DESECHO` es una baja de la
#: 025. «Reparación» no es un estado de mercancía: en la norma es un motivo de
#: traslado de una guía de despacho.
#:
#: No se escribe aquí: se le pide al módulo que es la autoridad única del
#: catálogo. Copiar tres etiquetas en otro módulo es empezar a tener dos motores.
RETURN_DISPOSITIONS: frozenset[str] = inv_service.state_authority.RETURN_DISPOSITIONS


def _consolidacion_del_pedido(db: Session, company_id: str, order_id: str | None) -> str:
    """Dónde dejó la preparación la mercancía de ese pedido.

    Es el mismo plan cerrado que `confirm_shipment` consultó para sacarla, y por
    eso es donde el saldo `DESPACHADO` está.
    """
    if order_id is None:
        raise ConflictError(code="RETURN_WITHOUT_ORDER",
                            message="La devolución no dice de qué pedido viene.")
    plan = db.execute(
        select(PickList).where(PickList.company_id == company_id,
                               PickList.order_id == str(order_id),
                               PickList.status == "CLOSED")
        .order_by(PickList.consolidated_at.desc())).scalars().first()
    if plan is None or plan.consolidation_location_id is None:
        raise ConflictError(code="RETURN_WITHOUT_PREPARATION",
                            message="El pedido no tiene una preparación consolidada de la que saliera.")
    return str(plan.consolidation_location_id)


def _require_return_036(db: Session, company_id: str, return_id: str, *, lock: bool = False) -> SalesReturn:
    consulta = select(SalesReturn).where(SalesReturn.id == return_id)
    if lock:
        consulta = consulta.with_for_update()
    devolucion = db.execute(consulta).scalars().first()
    if devolucion is None or str(devolucion.company_id) != str(company_id):
        raise NotFoundError(code="SALES_RETURN_NOT_FOUND", message="Devolución no encontrada")
    return devolucion


def _lineas_de_devolucion(db: Session, return_id: str) -> list[SalesReturnLine]:
    return list(db.execute(
        select(SalesReturnLine).where(SalesReturnLine.return_id == str(return_id))
        .order_by(SalesReturnLine.id)).scalars().all())


def _base_de_linea(linea: SalesReturnLine) -> Decimal:
    """Lo que sale o entra es siempre la cantidad **base**.

    Devolver una caja de doce reingresa doce unidades. Es el mismo defecto que
    la 035 encontró en la salida, y aquí se evita desde el principio.
    """
    return _dec(linea.base_quantity if linea.base_quantity is not None else linea.quantity)


def _devuelto_acumulado(db: Session, company_id: str, invoice_line_id: str,
                        *, excluir_devolucion: str | None = None) -> Decimal:
    """Lo ya devuelto contra una línea de factura, en cantidad base.

    Cuenta todas las devoluciones vivas, no solo las cerradas: una devolución
    solicitada ya compromete esa cantidad, y si no contara, dos solicitudes
    simultáneas podrían sumar más de lo despachado.
    """
    filas = db.execute(
        select(SalesReturnLine, SalesReturn)
        .join(SalesReturn, SalesReturn.id == SalesReturnLine.return_id)
        .where(SalesReturn.company_id == company_id,
               SalesReturnLine.invoice_line_id == str(invoice_line_id),
               SalesReturn.status.notin_(("CANCELLED", "REJECTED")))).all()
    total = Decimal(0)
    for linea, devolucion in filas:
        if excluir_devolucion and str(devolucion.id) == str(excluir_devolucion):
            continue
        total += _base_de_linea(linea)
    return total


def _despachado_de_linea(db: Session, company_id: str, invoice_line: SalesInvoiceLine) -> Decimal:
    """Lo que salió del almacén por esa línea, en cantidad base.

    El tope de la devolución no es lo facturado sino lo **despachado**: no se
    devuelve lo que nunca salió. Si la línea no tiene cantidad base —facturas
    anteriores a la Spec 011— se usa la comercial, que es toda la verdad que hay
    sobre ellas.
    """
    return _dec(invoice_line.base_quantity if invoice_line.base_quantity is not None
                else invoice_line.quantity)


def return_eligibility(db: Session, *, company_id: str, invoice_id: str) -> dict:
    """Qué se puede devolver de una factura y cuánto queda.

    Lo calcula el backend y no la pantalla: la regla de integridad del modelo de
    datos dice «no ajustar por encima de cantidades/base/IVA **pendientes** del
    original», y «pendiente» es una resta que solo el que ve todas las
    devoluciones puede hacer.
    """
    company_id = _company(company_id, obj="devolución")
    invoice = db.get(SalesInvoice, invoice_id)
    if invoice is None or str(invoice.company_id) != str(company_id):
        raise NotFoundError(code="SALES_INVOICE_NOT_FOUND", message="Factura de venta no encontrada")
    lineas = db.execute(
        select(SalesInvoiceLine).where(SalesInvoiceLine.invoice_id == str(invoice.id))
        .order_by(SalesInvoiceLine.id)).scalars().all()
    despacho = _live_shipment(db, company_id, str(invoice.order_id)) if invoice.order_id else None
    salidas = []
    for linea in lineas:
        despachado = _despachado_de_linea(db, company_id, linea)
        devuelto = _devuelto_acumulado(db, company_id, str(linea.id))
        salidas.append({
            "invoice_line_id": str(linea.id), "product_id": str(linea.product_id),
            "quantity": str(_dec(linea.quantity)),
            "dispatched_base_quantity": str(despachado),
            "returned_base_quantity": str(devuelto),
            "returnable_base_quantity": str(max(Decimal(0), despachado - devuelto)),
            "presentation_id": str(linea.presentation_id) if linea.presentation_id else None,
            "conversion_factor_snapshot": (str(_dec(linea.conversion_factor_snapshot))
                                           if linea.conversion_factor_snapshot else None),
        })
    return {
        "invoice_id": str(invoice.id), "invoice_status": invoice.status,
        "invoice_number": invoice.invoice_number, "control_number": invoice.control_number,
        "order_id": str(invoice.order_id) if invoice.order_id else None,
        "customer_id": str(invoice.customer_id),
        "shipment_id": str(despacho.id) if despacho else None,
        # Solo se devuelve lo que salió: el ¶106 hace salir la mercancía con su
        # factura, y sin esa salida no hay nada que devolver.
        "dispatched": despacho is not None and despacho.status == "SHIPPED",
        "lines": salidas,
    }


def request_return(db: Session, *, company_id: str, code: str, invoice_id: str, reason: str,
                   lines: list[dict], warehouse_id: str | None = None,
                   actor: str | None = None) -> SalesReturn:
    """«Solicitud»: el primer acto. No mueve una sola unidad.

    Lo único que hace es declarar qué se pretende devolver y contra qué. La
    mercancía sigue con el cliente y el inventario no se entera.
    """
    company_id = _company(company_id, obj="devolución")
    elegibilidad = return_eligibility(db, company_id=company_id, invoice_id=invoice_id)
    if not elegibilidad["dispatched"]:
        raise ConflictError(code="RETURN_NOT_DISPATCHED",
                            message="No se devuelve lo que no salió del almacén.")
    if not (reason or "").strip():
        raise KontrolError(code="RETURN_REASON_REQUIRED",
                           message="Indique el motivo de la devolución.", status_code=422)
    if not lines:
        raise KontrolError(code="RETURN_EMPTY", message="La devolución no tiene líneas.",
                           status_code=422)
    invoice = db.get(SalesInvoice, invoice_id)
    almacen = warehouse_id or (str(invoice.order.warehouse_id)
                               if getattr(invoice, "order", None) else None)
    if almacen is None and invoice.order_id:
        pedido = db.get(SalesOrder, str(invoice.order_id))
        almacen = str(pedido.warehouse_id) if pedido else None
    if almacen:
        _require_warehouse(db, company_id, almacen)

    devolucion = SalesReturn(
        company_id=company_id, code=code, reason=reason,
        source_document=f"SALES_INVOICE:{invoice.id}",
        customer_id=str(invoice.customer_id), invoice_id=str(invoice.id),
        order_id=str(invoice.order_id) if invoice.order_id else None,
        shipment_id=elegibilidad["shipment_id"], warehouse_id=almacen,
        status="REQUESTED", requested_at=datetime.now(UTC), requested_by=actor,
        created_by=actor)
    db.add(devolucion)
    db.flush()

    disponible = {x["invoice_line_id"]: _dec(x["returnable_base_quantity"])
                  for x in elegibilidad["lines"]}
    for item in lines:
        invoice_line_id = str(item["invoice_line_id"])
        if invoice_line_id not in disponible:
            raise NotFoundError(code="INVOICE_LINE_NOT_FOUND",
                                message="La línea no pertenece a esta factura")
        linea_factura = db.get(SalesInvoiceLine, invoice_line_id)
        pedida = _dec(item.get("base_quantity", item.get("quantity", 0)))
        if pedida <= 0:
            raise KontrolError(code="RETURN_QUANTITY_INVALID",
                               message="La cantidad a devolver debe ser positiva.", status_code=422)
        if pedida > disponible[invoice_line_id]:
            raise ConflictError(
                code="RETURN_EXCEEDS_DISPATCHED",
                message="No se devuelve más de lo que se despachó.",
                details={"invoice_line_id": invoice_line_id,
                         "returnable_base_quantity": str(disponible[invoice_line_id]),
                         "requested_base_quantity": str(pedida)})
        disponible[invoice_line_id] -= pedida
        # La presentación y el factor se copian de la factura, no del maestro de
        # hoy: devolver una caja de doce devuelve las doce que se facturaron,
        # aunque la caja pase a ser de veinte mañana.
        db.add(SalesReturnLine(
            return_id=str(devolucion.id), invoice_line_id=invoice_line_id,
            product_id=str(linea_factura.product_id),
            quantity=_dec(item.get("quantity", pedida)), base_quantity=pedida,
            condition=item.get("condition", "DEFECTUOSO"),
            lot_id=item.get("lot_id"), serial_id=item.get("serial_id"),
            uom_id=linea_factura.uom_id, presentation_id=linea_factura.presentation_id,
            conversion_factor_snapshot=linea_factura.conversion_factor_snapshot,
            uom_source=linea_factura.uom_source))
    db.flush()
    _audit(db, action="SALES_RETURN_REQUESTED", entity_type="SalesReturn",
           entity_id=str(devolucion.id), company_id=company_id, actor=actor,
           after={"invoice_id": str(invoice.id), "lines": len(lines), "reason": reason})
    return devolucion


def receive_return(db: Session, *, company_id: str, return_id: str, location_id: str,
                   actor: str | None = None) -> SalesReturn:
    """«Recepción»: la custodia vuelve a la empresa, pero no la disponibilidad.

    Aquí ocurre `DESPACHADO → DEVUELTO`, la arista que `D0-10` reservó para esta
    Spec. La mercancía está en el almacén y **no es vendible**: `D0-10` es
    tajante en que «disponible para venta es exclusivamente `DISPONIBLE`», y
    todavía falta la verificación física que la norma exige.
    """
    company_id = _company(company_id, obj="devolución")
    devolucion = _require_return_036(db, company_id, return_id, lock=True)
    if devolucion.received_at is not None:
        return devolucion
    _assert_transition(devolucion.status, "RECEIVED", RETURN_TRANSITIONS, "la devolución")
    if devolucion.warehouse_id is None:
        raise ConflictError(code="RETURN_WITHOUT_WAREHOUSE",
                            message="La devolución no dice a qué almacén entra.")
    destino = inv_service.location_in_warehouse(
        db, company_id=company_id, warehouse_id=str(devolucion.warehouse_id),
        location_id=location_id)
    # De dónde sale el saldo `DESPACHADO`: de donde la Spec 035 lo dejó, que es
    # el Área de Confirmación del plan que se consolidó. No es un detalle de
    # implementación sino el lugar que el ledger dice: la mercancía salió de
    # allí y la reclasificación tiene que ocurrir donde está la fila.
    salida = _consolidacion_del_pedido(db, company_id, str(devolucion.order_id))
    lineas = _lineas_de_devolucion(db, str(devolucion.id))
    if not lineas:
        raise ConflictError(code="RETURN_EMPTY", message="La devolución no tiene líneas.")
    for linea in lineas:
        cantidad = _base_de_linea(linea)
        inv_service.reclassify(
            db, company_id=company_id, warehouse_id=str(devolucion.warehouse_id),
            product_id=str(linea.product_id), source_state=inv_service.state_authority.DISPATCHED_STATE,
            target_state=inv_service.state_authority.RETURNED_STATE,
            quantity=cantidad, location_id=salida,
            lot_id=linea.lot_id, serial_id=linea.serial_id,
            document_ref=f"SALES_RETURN:{devolucion.id}", actor=actor)
        # Y de allí al área de devoluciones. Es un traslado de ubicación dentro
        # del mismo almacén, que es exactamente lo que `putaway` hace y lo que
        # la Spec 022 dejó como camino canónico. La mercancía devuelta no se
        # queda en la ubicación desde la que salió a la calle.
        if salida != str(destino.id):
            inv_service.putaway(
                db, company_id=company_id, warehouse_id=str(devolucion.warehouse_id),
                product_id=str(linea.product_id), target_location_id=str(destino.id),
                quantity=cantidad, source_location_id=salida,
                state=inv_service.state_authority.RETURNED_STATE,
                lot_id=linea.lot_id, serial_id=linea.serial_id,
                document_ref=f"SALES_RETURN:{devolucion.id}", actor=actor)
    ahora = datetime.now(UTC)
    devolucion.location_id = str(destino.id)
    devolucion.status = "RECEIVED"
    devolucion.received_at = ahora
    devolucion.received_by = actor
    devolucion.updated_at = ahora
    db.flush()
    _audit(db, action="SALES_RETURN_RECEIVED", entity_type="SalesReturn",
           entity_id=str(devolucion.id), company_id=company_id, actor=actor,
           after={"location_id": str(destino.id), "lines": len(lineas)})
    return devolucion


def inspect_return(db: Session, *, company_id: str, return_id: str, lines: list[dict],
                   actor: str | None = None) -> SalesReturn:
    """«Verificación física»: qué vuelve a existencia y qué no.

    El destino es por línea y solo puede ser uno de los dos que `D0-10` concede.
    La cantidad aceptada puede ser menor que la recibida: media caja puede estar
    intacta y la otra media no, y eso hay que poder decirlo.
    """
    company_id = _company(company_id, obj="devolución")
    devolucion = _require_return_036(db, company_id, return_id, lock=True)
    _assert_transition(devolucion.status, "INSPECTED", RETURN_TRANSITIONS, "la devolución")
    por_id = {str(x.id): x for x in _lineas_de_devolucion(db, str(devolucion.id))}
    if not lines:
        raise KontrolError(code="RETURN_INSPECTION_EMPTY",
                           message="La verificación no dictaminó ninguna línea.", status_code=422)
    vistas: set[str] = set()
    for item in lines:
        line_id = str(item["return_line_id"])
        linea = por_id.get(line_id)
        if linea is None:
            raise NotFoundError(code="RETURN_LINE_NOT_FOUND",
                                message="La línea no pertenece a esta devolución")
        destino = str(item.get("disposition", "")).upper()
        if destino not in RETURN_DISPOSITIONS:
            raise KontrolError(
                code="RETURN_DISPOSITION_INVALID",
                message="El destino de la mercancía devuelta no está declarado.",
                details={"allowed": sorted(RETURN_DISPOSITIONS)}, status_code=422)
        recibida = _base_de_linea(linea)
        aceptada = _dec(item.get("accepted_base_quantity", recibida))
        if aceptada < 0 or aceptada > recibida:
            raise ConflictError(
                code="RETURN_ACCEPTED_EXCEEDS_RECEIVED",
                message="No se acepta más de lo que se recibió.",
                details={"received_base_quantity": str(recibida),
                         "accepted_base_quantity": str(aceptada)})
        linea.disposition = destino
        linea.accepted_base_quantity = aceptada
        linea.inspection_note = item.get("note")
        vistas.add(line_id)
    faltan = set(por_id) - vistas
    if faltan:
        raise ConflictError(code="RETURN_INSPECTION_INCOMPLETE",
                            message="Todas las líneas recibidas necesitan dictamen.",
                            details={"pending": sorted(faltan)})
    ahora = datetime.now(UTC)
    devolucion.status = "INSPECTED"
    devolucion.inspected_at = ahora
    devolucion.inspected_by = actor
    devolucion.updated_at = ahora
    db.flush()
    _audit(db, action="SALES_RETURN_INSPECTED", entity_type="SalesReturn",
           entity_id=str(devolucion.id), company_id=company_id, actor=actor,
           after={"lines": len(lines)})
    return devolucion


def decide_return(db: Session, *, company_id: str, return_id: str, approved: bool,
                  reason: str | None = None, actor: str | None = None) -> SalesReturn:
    """«Aprobación»: el tercer acto, antes de tocar el inventario.

    Si se deniega, la devolución termina y la mercancía se queda en `DEVUELTO`.
    Qué hacer después con esa mercancía —devolvérsela al cliente, desecharla—
    **no lo decide esta Spec**: sería una salida nueva y ninguna fuente la
    declara. Queda en custodia, que es la verdad.
    """
    company_id = _company(company_id, obj="devolución")
    devolucion = _require_return_036(db, company_id, return_id, lock=True)
    destino = "APPROVED" if approved else "REJECTED"
    _assert_transition(devolucion.status, destino, RETURN_TRANSITIONS, "la devolución")
    if not approved and not (reason or "").strip():
        raise KontrolError(code="RETURN_REJECTION_REASON_REQUIRED",
                           message="Denegar una devolución exige motivo.", status_code=422)
    ahora = datetime.now(UTC)
    devolucion.status = destino
    devolucion.status_reason = reason
    devolucion.approved_at = ahora
    devolucion.approved_by = actor
    devolucion.updated_at = ahora
    db.flush()
    _audit(db, action=f"SALES_RETURN_{destino}", entity_type="SalesReturn",
           entity_id=str(devolucion.id), company_id=company_id, actor=actor,
           after={"reason": reason})
    return devolucion


def reenter_return(db: Session, *, company_id: str, return_id: str,
                   actor: str | None = None) -> SalesReturn:
    """«Entrada de inventario»: el cuarto acto, y el único que crea existencia.

    Cada línea va al destino que la verificación le dictaminó: `DISPONIBLE` si
    vuelve a ser vendible, `RECHAZADO` si no. Lo aceptado y lo no aceptado se
    separan aquí: si la inspección aceptó ocho de doce, ocho van al destino y
    cuatro se quedan en `DEVUELTO`, que sigue siendo custodia de la empresa.
    """
    company_id = _company(company_id, obj="devolución")
    devolucion = _require_return_036(db, company_id, return_id, lock=True)
    if devolucion.reentered_at is not None:
        return devolucion
    _assert_transition(devolucion.status, "CLOSED", RETURN_TRANSITIONS, "la devolución")
    lineas = _lineas_de_devolucion(db, str(devolucion.id))
    for linea in lineas:
        if linea.disposition is None:
            raise ConflictError(code="RETURN_INSPECTION_INCOMPLETE",
                                message="Hay líneas sin dictamen.")
        aceptada = _dec(linea.accepted_base_quantity
                        if linea.accepted_base_quantity is not None else _base_de_linea(linea))
        if aceptada <= 0:
            continue
        inv_service.reclassify(
            db, company_id=company_id, warehouse_id=str(devolucion.warehouse_id),
            product_id=str(linea.product_id),
            source_state=inv_service.state_authority.RETURNED_STATE,
            target_state=linea.disposition, quantity=aceptada,
            location_id=str(devolucion.location_id), lot_id=linea.lot_id,
            serial_id=linea.serial_id,
            document_ref=f"SALES_RETURN:{devolucion.id}", actor=actor)
    ahora = datetime.now(UTC)
    devolucion.status = "CLOSED"
    devolucion.reentered_at = ahora
    devolucion.reentered_by = actor
    devolucion.updated_at = ahora
    db.flush()
    _audit(db, action="SALES_RETURN_REENTERED", entity_type="SalesReturn",
           entity_id=str(devolucion.id), company_id=company_id, actor=actor,
           after={"lines": len(lineas)})
    return devolucion


def return_dict(db: Session, devolucion: SalesReturn) -> dict:
    lineas = _lineas_de_devolucion(db, str(devolucion.id))
    return {
        "id": str(devolucion.id), "code": devolucion.code, "status": devolucion.status,
        "status_reason": devolucion.status_reason, "reason": devolucion.reason,
        "invoice_id": str(devolucion.invoice_id) if devolucion.invoice_id else None,
        "order_id": str(devolucion.order_id) if devolucion.order_id else None,
        "shipment_id": str(devolucion.shipment_id) if devolucion.shipment_id else None,
        "customer_id": str(devolucion.customer_id) if devolucion.customer_id else None,
        "warehouse_id": str(devolucion.warehouse_id) if devolucion.warehouse_id else None,
        "location_id": str(devolucion.location_id) if devolucion.location_id else None,
        "requested_at": devolucion.requested_at.isoformat() if devolucion.requested_at else None,
        "received_at": devolucion.received_at.isoformat() if devolucion.received_at else None,
        "inspected_at": devolucion.inspected_at.isoformat() if devolucion.inspected_at else None,
        "approved_at": devolucion.approved_at.isoformat() if devolucion.approved_at else None,
        "reentered_at": devolucion.reentered_at.isoformat() if devolucion.reentered_at else None,
        "lines": [{"id": str(ln.id), "product_id": str(ln.product_id),
                   "invoice_line_id": str(ln.invoice_line_id) if ln.invoice_line_id else None,
                   "quantity": str(_dec(ln.quantity)),
                   "base_quantity": str(_base_de_linea(ln)),
                   "accepted_base_quantity": (str(_dec(ln.accepted_base_quantity))
                                              if ln.accepted_base_quantity is not None else None),
                   "disposition": ln.disposition, "condition": ln.condition,
                   "lot_id": ln.lot_id, "serial_id": ln.serial_id,
                   "presentation_id": str(ln.presentation_id) if ln.presentation_id else None,
                   "conversion_factor_snapshot": (str(_dec(ln.conversion_factor_snapshot))
                                                  if ln.conversion_factor_snapshot else None)}
                  for ln in lineas],
    }


# --------------------------------------------------------------------------- #
# Nota de crédito
#
# «La nota de crédito se utiliza para disminuir o dejar sin efecto, total o
# parcialmente, una factura emitida». La norma enumera sus causas —devolución de
# mercancía, anulación, descuento posterior, bonificación, corrección de precio,
# disminución de cantidad, devolución de envases, reversión— y solo dos traen
# mercancía de vuelta. Por eso la nota **no** se emite sola al aceptar una
# devolución, y por eso puede existir sin ninguna.
#
# Y exige, literalmente: consecutivo propio, número de control, referencia a la
# factura original con su fecha, número y control, motivo, líneas, cantidades y
# montos, «recalcular **proporcionalmente** base imponible e IVA» y «mantener la
# misma clasificación tributaria de la operación original».
# --------------------------------------------------------------------------- #

def _notas_vivas(db: Session, company_id: str, invoice_id: str) -> list[SalesCreditNote]:
    return list(db.execute(
        select(SalesCreditNote).where(SalesCreditNote.company_id == company_id,
                                      SalesCreditNote.invoice_id == str(invoice_id),
                                      SalesCreditNote.status != "CANCELLED")).scalars().all())


def _acreditado_de_linea(db: Session, company_id: str, invoice_line_id: str,
                         *, excluir_nota: str | None = None) -> Decimal:
    """Lo ya acreditado contra una línea, en cantidad comercial.

    La regla de integridad dice «no ajustar por encima de cantidades/base/IVA
    **pendientes** del original». Pendiente, no total: el tope es acumulativo y
    hay que sumar todas las notas vivas, no solo las emitidas.
    """
    filas = db.execute(
        select(SalesCreditNoteLine, SalesCreditNote)
        .join(SalesCreditNote, SalesCreditNote.id == SalesCreditNoteLine.note_id)
        .where(SalesCreditNote.company_id == company_id,
               SalesCreditNoteLine.invoice_line_id == str(invoice_line_id),
               SalesCreditNote.status != "CANCELLED")).all()
    total = Decimal(0)
    for linea, nota in filas:
        if excluir_nota and str(nota.id) == str(excluir_nota):
            continue
        total += _dec(linea.quantity)
    return total


def credit_eligibility(db: Session, *, company_id: str, invoice_id: str) -> dict:
    """Cuánto queda por acreditar de cada línea, y en cuánto dinero."""
    company_id = _company(company_id, obj="nota de crédito")
    invoice = db.get(SalesInvoice, invoice_id)
    if invoice is None or str(invoice.company_id) != str(company_id):
        raise NotFoundError(code="SALES_INVOICE_NOT_FOUND", message="Factura de venta no encontrada")
    lineas = db.execute(
        select(SalesInvoiceLine).where(SalesInvoiceLine.invoice_id == str(invoice.id))
        .order_by(SalesInvoiceLine.id)).scalars().all()
    salidas = []
    for linea in lineas:
        facturada = _dec(linea.quantity)
        acreditada = _acreditado_de_linea(db, company_id, str(linea.id))
        salidas.append({
            "invoice_line_id": str(linea.id), "product_id": str(linea.product_id),
            "quantity": str(facturada), "credited_quantity": str(acreditada),
            "creditable_quantity": str(max(Decimal(0), facturada - acreditada)),
            "unit_price": str(_dec(linea.unit_price)),
            "base_fiscal": str(_dec(linea.base_fiscal)),
            "tax_amount": str(_dec(linea.tax_amount)),
        })
    return {
        "invoice_id": str(invoice.id), "invoice_status": invoice.status,
        "invoice_number": invoice.invoice_number, "control_number": invoice.control_number,
        "issued_at": invoice.issued_at.isoformat() if invoice.issued_at else None,
        "customer_id": str(invoice.customer_id), "currency": invoice.base_fiscal_currency,
        # Solo se acredita una factura que exista fiscalmente: la norma habla de
        # «disminuir o dejar sin efecto **una factura emitida**».
        "creditable": invoice.status in ("EMITTED", "DELIVERED", "PARTIALLY_PAID", "PAID"),
        "lines": salidas,
    }


def generate_credit_note(db: Session, *, company_id: str, invoice_id: str, cause: str,
                         lines: list[dict], return_id: str | None = None,
                         actor: str | None = None) -> SalesCreditNote:
    """Construye la nota contra la factura original. **No la emite.**

    El impuesto no se vuelve a calcular con las reglas de hoy: se reparte el que
    la factura ya lleva, en proporción a la cantidad que se acredita. Eso es lo
    que dice la norma —«recalcular proporcionalmente base imponible e IVA»— y a
    la vez lo único que «mantiene la misma clasificación tributaria de la
    operación original», porque no vuelve a clasificar nada.
    """
    company_id = _company(company_id, obj="nota de crédito")
    if not (cause or "").strip():
        raise KontrolError(code="CREDIT_NOTE_CAUSE_REQUIRED",
                           message="Indique el motivo de la nota de crédito.", status_code=422)
    elegibilidad = credit_eligibility(db, company_id=company_id, invoice_id=invoice_id)
    if not elegibilidad["creditable"]:
        raise ConflictError(code="INVOICE_NOT_CREDITABLE",
                            message="Solo se acredita una factura emitida.")
    if not lines:
        raise KontrolError(code="CREDIT_NOTE_EMPTY", message="La nota no tiene líneas.",
                           status_code=422)
    invoice = db.get(SalesInvoice, invoice_id)
    devolucion = None
    if return_id:
        devolucion = _require_return_036(db, company_id, return_id)
        if str(devolucion.invoice_id) != str(invoice.id):
            raise ConflictError(code="RETURN_INVOICE_MISMATCH",
                                message="La devolución no es de esta factura.")

    nota = SalesCreditNote(
        company_id=company_id, customer_id=str(invoice.customer_id),
        invoice_id=str(invoice.id), invoice_ref=str(invoice.id),
        return_id=str(devolucion.id) if devolucion else None,
        number="", amount=Decimal(0), applied=Decimal(0),
        currency=invoice.base_fiscal_currency or "VED", cause=cause,
        status="DRAFT", created_by=actor)
    db.add(nota)
    db.flush()

    disponible = {x["invoice_line_id"]: _dec(x["creditable_quantity"])
                  for x in elegibilidad["lines"]}
    base_total = Decimal(0)
    impuesto_total = Decimal(0)
    for item in lines:
        invoice_line_id = str(item["invoice_line_id"])
        if invoice_line_id not in disponible:
            raise NotFoundError(code="INVOICE_LINE_NOT_FOUND",
                                message="La línea no pertenece a esta factura")
        linea = db.get(SalesInvoiceLine, invoice_line_id)
        cantidad = _dec(item["quantity"])
        if cantidad <= 0:
            raise KontrolError(code="CREDIT_QUANTITY_INVALID",
                               message="La cantidad a acreditar debe ser positiva.", status_code=422)
        if cantidad > disponible[invoice_line_id]:
            raise ConflictError(
                code="CREDIT_EXCEEDS_INVOICE",
                message="No se acredita por encima de lo pendiente del original.",
                details={"invoice_line_id": invoice_line_id,
                         "creditable_quantity": str(disponible[invoice_line_id]),
                         "requested_quantity": str(cantidad)})
        disponible[invoice_line_id] -= cantidad
        facturada = _dec(linea.quantity)
        proporcion = (cantidad / facturada) if facturada else Decimal(0)
        base = (_dec(linea.base_fiscal) * proporcion).quantize(_CENTIMO)
        impuesto = (_dec(linea.tax_amount) * proporcion).quantize(_CENTIMO)
        factor = linea.conversion_factor_snapshot
        db.add(SalesCreditNoteLine(
            note_id=str(nota.id), invoice_line_id=invoice_line_id,
            product_id=str(linea.product_id), quantity=cantidad,
            unit_price=_dec(linea.unit_price), base_fiscal=base, tax_amount=impuesto,
            total=base + impuesto, uom_id=linea.uom_id, presentation_id=linea.presentation_id,
            conversion_factor_snapshot=factor,
            base_quantity=(cantidad * _dec(factor)) if factor else None))
        base_total += base
        impuesto_total += impuesto

    nota.base_fiscal = base_total
    nota.tax_total = impuesto_total
    nota.amount = base_total + impuesto_total
    db.flush()
    _audit(db, action="SALES_CREDIT_NOTE_GENERATED", entity_type="SalesCreditNote",
           entity_id=str(nota.id), company_id=company_id, actor=actor,
           after={"invoice_id": str(invoice.id), "return_id": str(devolucion.id) if devolucion else None,
                  "total": str(nota.amount), "cause": cause})
    return nota


def issue_credit_note(db: Session, *, company_id: str, note_id: str, series_id: str,
                      batch_id: str, actor: str | None = None) -> SalesCreditNote:
    """Emite el documento fiscal de la nota y ajusta la cuenta por cobrar.

    El consecutivo y el número de control los da la 042, igual que a la factura,
    y por la misma razón: aquí no se numera. La tasa de cambio tampoco se
    revisa: la Providencia considera alteración fiscal el «cambio retroactivo
    del tipo de cambio», y una nota que ajusta proporcionalmente una factura ya
    emitida no puede traer una tasa distinta de la suya.
    """
    company_id = _company(company_id, obj="nota de crédito")
    nota = db.execute(
        select(SalesCreditNote).where(SalesCreditNote.id == note_id).with_for_update()
    ).scalars().first()
    if nota is None or str(nota.company_id) != str(company_id):
        raise NotFoundError(code="CREDIT_NOTE_NOT_FOUND", message="Nota de crédito no encontrada")
    if nota.issued_at is not None:
        return nota
    if nota.invoice_id is None:
        raise ConflictError(code="CREDIT_NOTE_WITHOUT_INVOICE",
                            message="No se emite una nota que no referencia una factura.")
    invoice = db.execute(
        select(SalesInvoice).where(SalesInvoice.id == str(nota.invoice_id)).with_for_update()
    ).scalars().first()

    emitido = fiscal_service.emit_document(
        db, company_id=company_id, business_document=f"CREDIT_NOTE:{nota.id}",
        series_id=series_id, batch_id=batch_id, actor=actor)

    ahora = datetime.now(UTC)
    nota.number = emitido.get("invoice_number") or nota.number
    nota.invoice_number = emitido.get("invoice_number")
    nota.control_number = emitido.get("control_number")
    nota.fiscal_document_id = emitido.get("id")
    nota.status = "POSTED"
    nota.issued_at = ahora
    nota.issued_by = actor
    nota.updated_at = ahora
    db.flush()

    _aplicar_nota_a_cxc(db, company_id=company_id, nota=nota, invoice=invoice, actor=actor)

    # `CREDITED` solo cuando la factura queda acreditada por entero. Una nota
    # parcial no la cierra: el estado existía en la máquina desde la Spec 005 y
    # es terminal, así que ponerlo antes de tiempo mataría la factura.
    pendiente = [x for x in credit_eligibility(db, company_id=company_id,
                                               invoice_id=str(invoice.id))["lines"]
                 if _dec(x["creditable_quantity"]) > 0]
    if not pendiente and invoice.status in INVOICE_TRANSITIONS and \
            "CREDITED" in INVOICE_TRANSITIONS[invoice.status]:
        invoice.status = "CREDITED"
        invoice.updated_at = ahora
    db.flush()
    _audit(db, action="SALES_CREDIT_NOTE_ISSUED", entity_type="SalesCreditNote",
           entity_id=str(nota.id), company_id=company_id, actor=actor,
           after={"invoice_number": nota.invoice_number, "control_number": nota.control_number,
                  "invoice_id": str(invoice.id), "invoice_status": invoice.status})
    return nota


def _aplicar_nota_a_cxc(db: Session, *, company_id: str, nota: SalesCreditNote,
                        invoice: SalesInvoice, actor: str | None) -> None:
    """«Ajuste de cuenta por cobrar», con el motor que ya existe.

    Si la factura ya está cobrada no hay saldo que reducir y la nota queda sin
    aplicar. Eso **no** es un error: la norma no condiciona la nota a que la
    factura esté pendiente, y qué hacer con un crédito a favor del cliente
    —imputarlo a otra factura, devolverlo— es de CxC y de tesorería, no de aquí.
    """
    item = db.execute(
        select(OpenItem).where(OpenItem.company_id == company_id,
                               OpenItem.source_document == f"SALES_INVOICE:{invoice.id}",
                               OpenItem.status == "OPEN").with_for_update()).scalars().first()
    if item is None:
        return
    saldo = _dec(ap_service.open_item_balance(item))
    pendiente = _dec(nota.amount) - _dec(nota.applied)
    aplicar = min(saldo, pendiente)
    if aplicar <= 0:
        return
    apply_credit_note(db, note=nota, target_open_item_id=str(item.id),
                      amount=aplicar, actor=actor)


def credit_note_dict(db: Session, nota: SalesCreditNote) -> dict:
    lineas = db.execute(
        select(SalesCreditNoteLine).where(SalesCreditNoteLine.note_id == str(nota.id))
        .order_by(SalesCreditNoteLine.id)).scalars().all()
    return {
        "id": str(nota.id), "status": nota.status, "cause": nota.cause,
        "invoice_id": str(nota.invoice_id) if nota.invoice_id else None,
        "return_id": str(nota.return_id) if nota.return_id else None,
        "customer_id": str(nota.customer_id), "currency": nota.currency,
        "base_fiscal": str(_dec(nota.base_fiscal)), "tax_total": str(_dec(nota.tax_total)),
        "total": str(_dec(nota.amount)), "applied": str(_dec(nota.applied)),
        "invoice_number": nota.invoice_number, "control_number": nota.control_number,
        "fiscal_document_id": nota.fiscal_document_id,
        "issued_at": nota.issued_at.isoformat() if nota.issued_at else None,
        "lines": [{"invoice_line_id": str(ln.invoice_line_id) if ln.invoice_line_id else None,
                   "product_id": str(ln.product_id), "quantity": str(_dec(ln.quantity)),
                   "unit_price": str(_dec(ln.unit_price)),
                   "base_quantity": (str(_dec(ln.base_quantity))
                                     if ln.base_quantity is not None else None),
                   "base_fiscal": str(_dec(ln.base_fiscal)),
                   "tax_amount": str(_dec(ln.tax_amount)), "total": str(_dec(ln.total))}
                  for ln in lineas],
    }


# --------------------------------------------------------------------------- #
# Nota de débito
#
# «La nota de débito aumenta el valor de una operación ya facturada». Su flujo
# no tiene una sola etapa física: «Identificación del concepto → Aprobación →
# Nota de débito vinculada → Ajuste de base e IVA → Cuenta por cobrar →
# Registro fiscal». Por eso aquí no se toca inventario, y por eso no hay tope
# contra el original: una nota de débito **suma**.
#
# Lo que sí es obligatorio es el vínculo: «no puede utilizarse como una factura
# independiente ni para encubrir una nueva venta».
# --------------------------------------------------------------------------- #

def generate_debit_note(db: Session, *, company_id: str, invoice_id: str, cause: str,
                        lines: list[dict], actor: str | None = None) -> SalesDebitNote:
    company_id = _company(company_id, obj="nota de débito")
    if not (cause or "").strip():
        raise KontrolError(code="DEBIT_NOTE_CAUSE_REQUIRED",
                           message="Indique el motivo de la nota de débito.", status_code=422)
    invoice = db.get(SalesInvoice, invoice_id)
    if invoice is None or str(invoice.company_id) != str(company_id):
        raise NotFoundError(code="SALES_INVOICE_NOT_FOUND", message="Factura de venta no encontrada")
    if invoice.status not in ("EMITTED", "DELIVERED", "PARTIALLY_PAID", "PAID"):
        raise ConflictError(code="INVOICE_NOT_DEBITABLE",
                            message="Solo se carga sobre una factura emitida.")
    if not lines:
        raise KontrolError(code="DEBIT_NOTE_EMPTY", message="La nota no tiene conceptos.",
                           status_code=422)

    nota = SalesDebitNote(
        company_id=company_id, customer_id=str(invoice.customer_id),
        invoice_id=str(invoice.id), invoice_ref=str(invoice.id), number="",
        amount=Decimal(0), currency=invoice.base_fiscal_currency or "VED",
        cause=cause, status="DRAFT", created_by=actor)
    db.add(nota)
    db.flush()

    base_total = Decimal(0)
    impuesto_total = Decimal(0)
    for item in lines:
        concepto = str(item.get("concept", "")).strip()
        if not concepto:
            raise KontrolError(code="DEBIT_CONCEPT_REQUIRED",
                               message="Cada concepto debe decir qué se cobra.", status_code=422)
        base = _dec(item.get("base_fiscal", 0)).quantize(_CENTIMO)
        if base <= 0:
            raise KontrolError(code="DEBIT_AMOUNT_INVALID",
                               message="El monto del concepto debe ser positivo.", status_code=422)
        impuesto = Decimal(0)
        linea_factura = None
        if item.get("invoice_line_id"):
            linea_factura = db.get(SalesInvoiceLine, str(item["invoice_line_id"]))
            if linea_factura is None or str(linea_factura.invoice_id) != str(invoice.id):
                raise NotFoundError(code="INVOICE_LINE_NOT_FOUND",
                                    message="La línea no pertenece a esta factura")
            # «Discriminar nuevamente base e impuesto», con la misma proporción
            # de impuesto que la línea original ya lleva: es lo que mantiene la
            # clasificación tributaria de la operación.
            base_original = _dec(linea_factura.base_fiscal)
            if base_original:
                impuesto = (base * _dec(linea_factura.tax_amount) / base_original).quantize(_CENTIMO)
        db.add(SalesDebitNoteLine(
            note_id=str(nota.id),
            invoice_line_id=str(linea_factura.id) if linea_factura else None,
            product_id=str(linea_factura.product_id) if linea_factura else None,
            concept=concepto, base_fiscal=base, tax_amount=impuesto, total=base + impuesto))
        base_total += base
        impuesto_total += impuesto

    nota.base_fiscal = base_total
    nota.tax_total = impuesto_total
    nota.amount = base_total + impuesto_total
    db.flush()
    _audit(db, action="SALES_DEBIT_NOTE_GENERATED", entity_type="SalesDebitNote",
           entity_id=str(nota.id), company_id=company_id, actor=actor,
           after={"invoice_id": str(invoice.id), "total": str(nota.amount), "cause": cause})
    return nota


def issue_debit_note(db: Session, *, company_id: str, note_id: str, series_id: str,
                     batch_id: str, actor: str | None = None) -> SalesDebitNote:
    """Emite el documento fiscal y **aumenta** la cuenta por cobrar."""
    company_id = _company(company_id, obj="nota de débito")
    nota = db.execute(
        select(SalesDebitNote).where(SalesDebitNote.id == note_id).with_for_update()
    ).scalars().first()
    if nota is None or str(nota.company_id) != str(company_id):
        raise NotFoundError(code="DEBIT_NOTE_NOT_FOUND", message="Nota de débito no encontrada")
    if nota.issued_at is not None:
        return nota
    if nota.invoice_id is None:
        raise ConflictError(code="DEBIT_NOTE_WITHOUT_INVOICE",
                            message="No se emite una nota que no referencia una factura.")

    emitido = fiscal_service.emit_document(
        db, company_id=company_id, business_document=f"DEBIT_NOTE:{nota.id}",
        series_id=series_id, batch_id=batch_id, actor=actor)

    ahora = datetime.now(UTC)
    nota.number = emitido.get("invoice_number") or nota.number
    nota.invoice_number = emitido.get("invoice_number")
    nota.control_number = emitido.get("control_number")
    nota.fiscal_document_id = emitido.get("id")
    nota.status = "POSTED"
    nota.issued_at = ahora
    nota.issued_by = actor
    nota.updated_at = ahora
    # La nota de débito no reduce nada: crea su propio documento por cobrar, con
    # su propio saldo. Meterla en el de la factura mezclaría dos documentos
    # fiscales distintos en una sola cuenta.
    db.add(OpenItem(company_id=company_id, party_id=str(nota.customer_id),
                    source_document=f"SALES_DEBIT_NOTE:{nota.id}", item_type="RECEIVABLE",
                    currency=nota.currency, original=nota.amount, applied=0.0,
                    due_date=hoy_de_negocio(), status="OPEN"))
    db.flush()
    _audit(db, action="SALES_DEBIT_NOTE_ISSUED", entity_type="SalesDebitNote",
           entity_id=str(nota.id), company_id=company_id, actor=actor,
           after={"invoice_number": nota.invoice_number, "control_number": nota.control_number,
                  "invoice_id": str(nota.invoice_id), "total": str(nota.amount)})
    return nota


def debit_note_dict(db: Session, nota: SalesDebitNote) -> dict:
    lineas = db.execute(
        select(SalesDebitNoteLine).where(SalesDebitNoteLine.note_id == str(nota.id))
        .order_by(SalesDebitNoteLine.id)).scalars().all()
    return {
        "id": str(nota.id), "status": nota.status, "cause": nota.cause,
        "invoice_id": str(nota.invoice_id) if nota.invoice_id else None,
        "customer_id": str(nota.customer_id), "currency": nota.currency,
        "base_fiscal": str(_dec(nota.base_fiscal)), "tax_total": str(_dec(nota.tax_total)),
        "total": str(_dec(nota.amount)),
        "invoice_number": nota.invoice_number, "control_number": nota.control_number,
        "fiscal_document_id": nota.fiscal_document_id,
        "issued_at": nota.issued_at.isoformat() if nota.issued_at else None,
        "lines": [{"invoice_line_id": str(ln.invoice_line_id) if ln.invoice_line_id else None,
                   "product_id": str(ln.product_id) if ln.product_id else None,
                   "concept": ln.concept, "base_fiscal": str(_dec(ln.base_fiscal)),
                   "tax_amount": str(_dec(ln.tax_amount)), "total": str(_dec(ln.total))}
                  for ln in lineas],
    }
