"""Modelos de ventas y cuentas por cobrar (005, data-model.md).

Ciclo: cotización (sin reserva) → pedido → crédito → orden → reserva → picking
→ despacho → factura de venta → CxC.

Invariantes (Constitución P4/P5/P8, DOC-01 §5, DOC-03 §12):
- Facturas emitidas y cobros son inmutables; corrección por nota/anulación.
- Los saldos de CxC se calculan desde documentos y aplicaciones; nunca se editan.
- Snapshot por línea (producto, precio, impuesto, tasa).
- La reserva/picking/despacho invocan el motor de 003; la CxC reutiliza el motor
  de aplicaciones de 004 (ap_open_items RECEIVABLE, ap_applications, etc.).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import JSON, Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy import column as sql_column_pl
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.expression import column as sql_column

from app.core.database import Base
from app.core.scope import Scope
from app.shared.mixins import CodeMixin, CreatedByMixin, TimestampMixin, UUIDMixin


# --------------------------------------------------------------------------- #
# Cotización y pedido
# --------------------------------------------------------------------------- #
class SalesQuote(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, Base):
    __tablename__ = "sales_quotes"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("parties.id"), nullable=False, index=True)
    #: La cadena original. **No se borra** (`FR-012-080`): una cotización antigua
    #: la escribió alguien y ese texto es el único rastro que dejó.
    price_list: Mapped[str | None] = mapped_column(String(120), nullable=True)
    #: La lista de precios **como referencia**, no como texto (Spec 012).
    price_list_id: Mapped[str | None] = mapped_column(ForeignKey("price_lists.id"), nullable=True)
    validity_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="VED")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")


class SalesQuoteLine(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "sales_quote_lines"
    __scope__ = Scope.COMPANY
    __scope_authority__ = "quote_id → sales_quotes"
    __table_args__ = (Index("ix_sales_quote_lines_uom_id", "uom_id"),)

    quote_id: Mapped[str] = mapped_column(ForeignKey("sales_quotes.id"), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    discount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0.0)
    tax_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # --- Semántica de unidad (Spec 011, R-D0-09-1) ---
    uom_id: Mapped[str | None] = mapped_column(ForeignKey("units_of_measure.id"), nullable=True)
    presentation_id: Mapped[str | None] = mapped_column(ForeignKey("presentations.id"), nullable=True)
    conversion_factor_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    base_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    uom_source: Mapped[str | None] = mapped_column(String(24), nullable=True)
    # -- Origen comercial (`P23`, Spec 012 §11) -------------------------------
    # Un precio sin origen no se puede reconstruir, y no porque el dato se
    # pierda: es que nunca se captura. Ninguna migración posterior lo repara,
    # así que se captura ahora, cuando todavía se sabe.
    #
    # Anulables a propósito: las líneas que ya existían no reciben un origen
    # inventado. Su `pricing_source` dice `LEGACY_FREETEXT` y eso es toda la
    # verdad que hay sobre ellas.
    #: La versión que produjo el precio. No la lista: la versión.
    price_source_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("price_list_versions.id"), nullable=True)
    #: El ítem concreto de esa versión.
    price_source_item_id: Mapped[str | None] = mapped_column(
        ForeignKey("price_list_items.id"), nullable=True)
    #: `RESOLVED` · `MANUAL_JUSTIFIED` · `LEGACY_FREETEXT`.
    pricing_source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    #: Lo que dijo el resolutor **antes** de que alguien lo cambiara a mano.
    #: Sin esto, un precio manual y uno resuelto son indistinguibles después.
    resolved_unit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    #: Motivo del cambio manual. Obligatorio cuando `pricing_source` lo es.
    manual_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    #: Qué política autorizó el descuento, y en qué versión.
    discount_policy_id: Mapped[str | None] = mapped_column(
        ForeignKey("discount_policies.id"), nullable=True)
    discount_policy_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    #: Si hizo falta aprobación, la solicitud de la Spec 045.
    discount_approval_request_id: Mapped[str | None] = mapped_column(
        ForeignKey("approval_requests.id"), nullable=True)
    #: La condición de pago **entera**, congelada. No su identificador: si el
    #: maestro cambia mañana, el documento tiene que seguir diciendo lo que dijo.
    payment_term_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)

class SalesOrder(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, Base):
    __tablename__ = "sales_orders"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        # Una cotización produce **un** pedido. Va en el ORM y no solo en la
        # migración porque las suites levantan el esquema con `create_all`:
        # dejarla únicamente en la migración haría que las pruebas
        # interrogaran un esquema más débil que el de producción.
        Index("uq_sales_orders_quote", "quote_id", unique=True,
              postgresql_where=sql_column("quote_id").isnot(None)
              ).ddl_if(dialect="postgresql"),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("parties.id"), nullable=False, index=True)
    warehouse_id: Mapped[str | None] = mapped_column(ForeignKey("warehouses.id"), nullable=True)
    credit_decision: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON: límite/bloqueo/margen
    margin: Mapped[float | None] = mapped_column(Numeric(14, 6), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="VED")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    approval_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    #: La cotización de la que nació, si nació de una. Único: una cotización
    #: produce **un** pedido. Convertir dos veces devuelve el mismo, no crea otro.
    quote_id: Mapped[str | None] = mapped_column(ForeignKey("sales_quotes.id"), nullable=True)
    #: Motivo de la última transición que lo exige (cancelar, revertir,
    #: rechazar). La auditoría lo guarda también; aquí queda a la vista.
    status_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    #: Momento de la confirmación comercial (`DRAFT → SUBMITTED`): el instante
    #: en que nació la reserva (ADR-D0-003 v2, R-D0-03-1).
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    #: Momento de la liberación a preparación (`→ RELEASED`): desde aquí el
    #: pedido es elegible para la cola de la Spec 031.
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class SalesOrderLine(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "sales_order_lines"
    __scope__ = Scope.COMPANY
    __scope_authority__ = "order_id → sales_orders"
    __table_args__ = (Index("ix_sales_order_lines_uom_id", "uom_id"),)

    order_id: Mapped[str] = mapped_column(ForeignKey("sales_orders.id"), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    discount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0.0)
    tax_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    needs_inventory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)

    # -- Origen comercial (`P23`, Spec 012 §11) -------------------------------
    # Un precio sin origen no se puede reconstruir, y no porque el dato se
    # pierda: es que nunca se captura. Ninguna migración posterior lo repara,
    # así que se captura ahora, cuando todavía se sabe.
    #
    # Anulables a propósito: las líneas que ya existían no reciben un origen
    # inventado. Su `pricing_source` dice `LEGACY_FREETEXT` y eso es toda la
    # verdad que hay sobre ellas.
    #: La versión que produjo el precio. No la lista: la versión.
    price_source_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("price_list_versions.id"), nullable=True)
    #: El ítem concreto de esa versión.
    price_source_item_id: Mapped[str | None] = mapped_column(
        ForeignKey("price_list_items.id"), nullable=True)
    #: `RESOLVED` · `MANUAL_JUSTIFIED` · `LEGACY_FREETEXT`.
    pricing_source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    #: Lo que dijo el resolutor **antes** de que alguien lo cambiara a mano.
    #: Sin esto, un precio manual y uno resuelto son indistinguibles después.
    resolved_unit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    #: Motivo del cambio manual. Obligatorio cuando `pricing_source` lo es.
    manual_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    #: Qué política autorizó el descuento, y en qué versión.
    discount_policy_id: Mapped[str | None] = mapped_column(
        ForeignKey("discount_policies.id"), nullable=True)
    discount_policy_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    #: Si hizo falta aprobación, la solicitud de la Spec 045.
    discount_approval_request_id: Mapped[str | None] = mapped_column(
        ForeignKey("approval_requests.id"), nullable=True)
    #: La condición de pago **entera**, congelada. No su identificador: si el
    #: maestro cambia mañana, el documento tiene que seguir diciendo lo que dijo.
    payment_term_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)



# --------------------------------------------------------------------------- #
# Picking y despacho (integración con 003)
# --------------------------------------------------------------------------- #

    # --- Semántica de unidad (Spec 011, R-D0-09-1) ---
    uom_id: Mapped[str | None] = mapped_column(ForeignKey("units_of_measure.id"), nullable=True)
    presentation_id: Mapped[str | None] = mapped_column(ForeignKey("presentations.id"), nullable=True)
    conversion_factor_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    base_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    uom_source: Mapped[str | None] = mapped_column(String(24), nullable=True)
#: Ciclo de vida del plan de picking (`D0-15`, `R-D0-15-10`).
#:
#: `DRAFT` planifica y puede ser parcial · `CONFIRMED` está completo y listo para
#: la Spec 032 · `CLOSED` lo escribe la ejecución física de la 032, nunca la 031 ·
#: `CANCELLED` es un acto deliberado · `INVALIDATED`, la consecuencia de perder
#: una precondición aguas arriba. Los tres últimos son terminales.
PLAN_STATUSES = ("DRAFT", "CONFIRMED", "CLOSED", "CANCELLED", "INVALIDATED")

#: Estados en los que el plan retiene existencia: sus líneas son asignaciones
#: vivas y descuentan lo asignable de la ubicación (`R-D0-15-12`, `R-D0-15-22`).
PLAN_ACTIVE_STATUSES = ("DRAFT", "CONFIRMED")


class PickList(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, Base):
    __tablename__ = "pick_lists"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'CONFIRMED', 'CLOSED', 'CANCELLED', 'INVALIDATED')",
            name="pick_list_status"),
        # Un pedido no puede tener dos planes vivos a la vez: dos almacenistas
        # asignando la misma demanda por separado la comprometerían dos veces.
        # Va en el ORM además de en la migración porque las suites levantan el
        # esquema con `create_all`.
        Index("uq_pick_lists_active_order", "order_id", unique=True,
              postgresql_where=sql_column_pl("status").in_(("DRAFT", "CONFIRMED"))
              ).ddl_if(dialect="postgresql"),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("sales_orders.id"), nullable=False, index=True)
    warehouse_id: Mapped[str] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")

    # --- Ciclo de vida (Spec 031, `D0-15`) ---
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    invalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class PickListLine(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "pick_list_lines"
    __scope__ = Scope.COMPANY
    __scope_authority__ = "picklist_id → pick_lists"
    __table_args__ = (
        Index("ix_pick_list_lines_uom_id", "uom_id"),
        # Una asignación es «de aquí, tanto, en este puesto del recorrido»: o
        # están los cuatro campos o no está ninguno. Nacen anulables porque el
        # esqueleto anterior pudo crear líneas sin ubicación y una migración no
        # inventa historia; lo que la restricción impide es la forma a medias.
        CheckConstraint(
            "(location_id IS NULL AND sequence IS NULL AND state IS NULL) OR "
            "(location_id IS NOT NULL AND sequence IS NOT NULL AND state IS NOT NULL "
            " AND base_quantity IS NOT NULL)",
            name="pick_list_line_allocation_shape"),
    )

    picklist_id: Mapped[str] = mapped_column(ForeignKey("pick_lists.id"), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False)
    lot_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    serial_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)

    # --- Asignación por ubicación (Spec 031, `R-D0-15-7`, `R-D0-15-22`) ---
    #: La demanda que satisface. Sin ella no se puede comprobar que lo asignado
    #: no exceda lo reservado de esa línea.
    order_line_id: Mapped[str | None] = mapped_column(ForeignKey("sales_order_lines.id"), nullable=True)
    #: De dónde se recoge. Nunca nula en una asignación real: la mercancía sin
    #: ubicar no es candidata.
    location_id: Mapped[str | None] = mapped_column(ForeignKey("warehouse_locations.id"), nullable=True)
    #: Estado de mercancía, para parear con la identidad exacta del saldo.
    state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    #: Puesto en el recorrido, derivado del orden físico de la Spec 008.
    sequence: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # --- Semántica de unidad (Spec 011, R-D0-09-1) ---
    uom_id: Mapped[str | None] = mapped_column(ForeignKey("units_of_measure.id"), nullable=True)
    presentation_id: Mapped[str | None] = mapped_column(ForeignKey("presentations.id"), nullable=True)
    conversion_factor_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    base_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    uom_source: Mapped[str | None] = mapped_column(String(24), nullable=True)
class Shipment(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, Base):
    __tablename__ = "shipments"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("sales_orders.id"), nullable=False, index=True)
    origin_warehouse_id: Mapped[str] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    destination: Mapped[str | None] = mapped_column(String(255), nullable=True)
    transport: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    validation_status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")


class ShipmentLine(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "shipment_lines"
    __scope__ = Scope.COMPANY
    __scope_authority__ = "shipment_id → shipments"
    __table_args__ = (Index("ix_shipment_lines_uom_id", "uom_id"),)

    shipment_id: Mapped[str] = mapped_column(ForeignKey("shipments.id"), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False)
    lot_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    serial_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)


# --------------------------------------------------------------------------- #
# Factura de venta y notas
# --------------------------------------------------------------------------- #

    # --- Semántica de unidad (Spec 011, R-D0-09-1) ---
    uom_id: Mapped[str | None] = mapped_column(ForeignKey("units_of_measure.id"), nullable=True)
    presentation_id: Mapped[str | None] = mapped_column(ForeignKey("presentations.id"), nullable=True)
    conversion_factor_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    base_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    uom_source: Mapped[str | None] = mapped_column(String(24), nullable=True)
    uom_symbol_snapshot: Mapped[str | None] = mapped_column(String(16), nullable=True)
    presentation_label_snapshot: Mapped[str | None] = mapped_column(String(120), nullable=True)
class SalesInvoice(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "sales_invoices"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("parties.id"), nullable=False, index=True)
    invoice_number: Mapped[str | None] = mapped_column(String(120), nullable=True)  # correlativo asignado por 007
    base_fiscal_currency: Mapped[str] = mapped_column(String(8), nullable=False, default="VED")
    base_fiscal: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0.0)
    tax_total: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0.0)
    total: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    reversed_by_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)


class SalesInvoiceLine(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "sales_invoice_lines"
    __scope__ = Scope.COMPANY
    __scope_authority__ = "invoice_id → sales_invoices"
    __table_args__ = (Index("ix_sales_invoice_lines_uom_id", "uom_id"),)

    invoice_id: Mapped[str] = mapped_column(ForeignKey("sales_invoices.id"), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    tax_amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0.0)
    base_fiscal: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0.0)
    total: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0.0)
    snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- Semántica de unidad (Spec 011, R-D0-09-1) ---
    uom_id: Mapped[str | None] = mapped_column(ForeignKey("units_of_measure.id"), nullable=True)
    presentation_id: Mapped[str | None] = mapped_column(ForeignKey("presentations.id"), nullable=True)
    conversion_factor_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    base_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    uom_source: Mapped[str | None] = mapped_column(String(24), nullable=True)
    uom_symbol_snapshot: Mapped[str | None] = mapped_column(String(16), nullable=True)
    presentation_label_snapshot: Mapped[str | None] = mapped_column(String(120), nullable=True)
class SalesCreditNote(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "sales_credit_notes"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("parties.id"), nullable=False, index=True)
    invoice_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    number: Mapped[str] = mapped_column(String(120), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    applied: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0.0)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="VED")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")


class SalesDebitNote(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "sales_debit_notes"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("parties.id"), nullable=False, index=True)
    invoice_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    number: Mapped[str] = mapped_column(String(120), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="VED")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")


class SalesReturn(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, Base):
    __tablename__ = "sales_returns"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    source_document: Mapped[str | None] = mapped_column(String(200), nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    condition: Mapped[str] = mapped_column(String(32), nullable=False, default="DEFECTUOSO")
    inventory_destination: Mapped[str] = mapped_column(String(32), nullable=False, default="CUARENTENA")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")


class SalesReturnLine(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "sales_return_lines"
    __scope__ = Scope.COMPANY
    __scope_authority__ = "return_id → sales_returns"
    __table_args__ = (Index("ix_sales_return_lines_uom_id", "uom_id"),)

    return_id: Mapped[str] = mapped_column(ForeignKey("sales_returns.id"), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    condition: Mapped[str] = mapped_column(String(32), nullable=False, default="DEFECTUOSO")

    # --- Semántica de unidad (Spec 011, R-D0-09-1) ---
    uom_id: Mapped[str | None] = mapped_column(ForeignKey("units_of_measure.id"), nullable=True)
    presentation_id: Mapped[str | None] = mapped_column(ForeignKey("presentations.id"), nullable=True)
    conversion_factor_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    base_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    uom_source: Mapped[str | None] = mapped_column(String(24), nullable=True)
    uom_symbol_snapshot: Mapped[str | None] = mapped_column(String(16), nullable=True)
    presentation_label_snapshot: Mapped[str | None] = mapped_column(String(120), nullable=True)
