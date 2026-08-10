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

from datetime import date

from sqlalchemy import Boolean, Date, Float, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.mixins import CodeMixin, CreatedByMixin, TimestampMixin, UUIDMixin


# --------------------------------------------------------------------------- #
# Cotización y pedido
# --------------------------------------------------------------------------- #
class SalesQuote(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, Base):
    __tablename__ = "sales_quotes"

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("parties.id"), nullable=False, index=True)
    price_list: Mapped[str | None] = mapped_column(String(120), nullable=True)
    validity_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="VED")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


class SalesQuoteLine(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "sales_quote_lines"

    quote_id: Mapped[str] = mapped_column(ForeignKey("sales_quotes.id"), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    discount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    tax_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)


class SalesOrder(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, Base):
    __tablename__ = "sales_orders"

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("parties.id"), nullable=False, index=True)
    warehouse_id: Mapped[str | None] = mapped_column(ForeignKey("warehouses.id"), nullable=True)
    credit_decision: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON: límite/bloqueo/margen
    margin: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="VED")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    approval_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)


class SalesOrderLine(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "sales_order_lines"

    order_id: Mapped[str] = mapped_column(ForeignKey("sales_orders.id"), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    discount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    tax_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    needs_inventory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)


# --------------------------------------------------------------------------- #
# Picking y despacho (integración con 003)
# --------------------------------------------------------------------------- #
class PickList(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, Base):
    __tablename__ = "pick_lists"

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("sales_orders.id"), nullable=False, index=True)
    warehouse_id: Mapped[str] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")


class PickListLine(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "pick_list_lines"

    picklist_id: Mapped[str] = mapped_column(ForeignKey("pick_lists.id"), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False)
    lot_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    serial_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)


class Shipment(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, Base):
    __tablename__ = "shipments"

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("sales_orders.id"), nullable=False, index=True)
    origin_warehouse_id: Mapped[str] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    destination: Mapped[str | None] = mapped_column(String(255), nullable=True)
    transport: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    validation_status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")


class ShipmentLine(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "shipment_lines"

    shipment_id: Mapped[str] = mapped_column(ForeignKey("shipments.id"), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False)
    lot_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    serial_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)


# --------------------------------------------------------------------------- #
# Factura de venta y notas
# --------------------------------------------------------------------------- #
class SalesInvoice(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "sales_invoices"

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
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

    invoice_id: Mapped[str] = mapped_column(ForeignKey("sales_invoices.id"), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    tax_amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0.0)
    base_fiscal: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0.0)
    total: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0.0)
    snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)


class SalesCreditNote(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "sales_credit_notes"

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("parties.id"), nullable=False, index=True)
    invoice_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    number: Mapped[str] = mapped_column(String(120), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    applied: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="VED")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")


class SalesDebitNote(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "sales_debit_notes"

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("parties.id"), nullable=False, index=True)
    invoice_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    number: Mapped[str] = mapped_column(String(120), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="VED")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")


class SalesReturn(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, Base):
    __tablename__ = "sales_returns"

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    source_document: Mapped[str | None] = mapped_column(String(200), nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    condition: Mapped[str] = mapped_column(String(32), nullable=False, default="DEFECTUOSO")
    inventory_destination: Mapped[str] = mapped_column(String(32), nullable=False, default="CUARENTENA")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")


class SalesReturnLine(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "sales_return_lines"

    return_id: Mapped[str] = mapped_column(ForeignKey("sales_returns.id"), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    condition: Mapped[str] = mapped_column(String(32), nullable=False, default="DEFECTUOSO")
