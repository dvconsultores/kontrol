"""Modelos de inventario y logística (003-inventario-logistica, data-model.md).

Existencias, movimientos (inmutables y balanceados), lotes, seriales, reservas,
transferencias, conteos, ajustes y costos por capa.

Invariantes (Constitución P5/P8, DOC-01 §5, DOC-03 §12):
- Los movimientos NO se editan ni eliminan físicamente; toda corrección es un
  reverso vinculado.
- Los saldos NO se editan; se calculan desde movimientos. `InventoryBalance`
  es una proyección/cache reconstruible.
- Datos críticos (lotes, seriales, vencimientos, costos) en columnas tipadas,
  nunca en EAV/JSON libre.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.mixins import (
    CodeMixin,
    CreatedByMixin,
    NameMixin,
    StatusMixin,
    TimestampMixin,
    UUIDMixin,
    VersionMixin,
)

# NOTA: Warehouse y Location (custodia) se definen en el módulo organization
# (001-fundacion, tablas `warehouses`/`locations`, DOC-02 §3). El módulo de
# inventario los REUTILIZA (FKs a warehouses.id / locations.id) y no los
# duplica (CL-003-02). El comportamiento de negocio (allow_negative, etc.) se
# lee de `warehouse.policies` (JSON gobernado, P8).


class MovementType(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, NameMixin, VersionMixin, StatusMixin, Base):
    """Tipo de movimiento versionado y configurable (FR-003-023, P8)."""

    __tablename__ = "movement_types"
    __table_args__ = (UniqueConstraint("company_id", "code", name="uq_movement_types_company_code"),)

    company_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)  # None = global
    direction: Mapped[str] = mapped_column(String(16), nullable=False)  # IN / OUT / INTERNAL
    affects_balance: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class InventoryMovement(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Movimiento de inventario balanceado e inmutable (FR-003-020/021/022)."""

    __tablename__ = "inventory_movements"

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    warehouse_id: Mapped[str] = mapped_column(ForeignKey("warehouses.id"), nullable=False, index=True)
    location_id: Mapped[str | None] = mapped_column(ForeignKey("warehouse_locations.id"), nullable=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False, index=True)
    movement_type_id: Mapped[str] = mapped_column(ForeignKey("movement_types.id"), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)  # != 0; signo según dirección
    unit_id: Mapped[str | None] = mapped_column(ForeignKey("units_of_measure.id"), nullable=True)
    unit_cost: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="VED")
    fiscal_rate: Mapped[float | None] = mapped_column(Numeric(14, 6), nullable=True)
    document_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reversed_by_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="POSTED")
    idempotency_key: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)


class InventoryLot(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Lote con vencimiento (FR-003-030/032)."""

    __tablename__ = "inventory_lots"
    __table_args__ = (UniqueConstraint("company_id", "product_id", "lot_number", name="uq_inventory_lots_company_product_lot"),)

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False, index=True)
    lot_number: Mapped[str] = mapped_column(String(120), nullable=False)
    manufacture_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    supplier_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    receipt_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DISPONIBLE")


class ProductSerial(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Serial/IMEI único con historial (FR-003-031/033)."""

    __tablename__ = "product_serials"
    __table_args__ = (UniqueConstraint("company_id", "serial", name="uq_product_serials_company_serial"),)

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False, index=True)
    serial: Mapped[str] = mapped_column(String(120), nullable=False)  # texto
    imei1: Mapped[str | None] = mapped_column(String(40), nullable=True)
    imei2: Mapped[str | None] = mapped_column(String(40), nullable=True)
    mac: Mapped[str | None] = mapped_column(String(40), nullable=True)
    lot_id: Mapped[str | None] = mapped_column(ForeignKey("inventory_lots.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DISPONIBLE")
    warehouse_id: Mapped[str | None] = mapped_column(ForeignKey("warehouses.id"), nullable=True)
    purchase_line_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    sale_line_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    warranty_until: Mapped[date | None] = mapped_column(Date, nullable=True)


class InventoryBalance(UUIDMixin, TimestampMixin, Base):
    """Proyección/cache de existencias (FR-003-010). Reconstruible desde movimientos.

    `location_id`/`lot_id`/`serial_id` opcionales (None = sin dimensión).
    El servicio mantiene una fila por combinación (upsert); no se editan saldos
    manualmente: la fuente es `InventoryMovement`.
    """

    __tablename__ = "inventory_balances"

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    warehouse_id: Mapped[str] = mapped_column(ForeignKey("warehouses.id"), nullable=False, index=True)
    # FK real desde la Spec 008: la ubicación es una dimensión del saldo, no
    # una referencia lógica sin integridad (FR-008-054, P23).
    location_id: Mapped[str | None] = mapped_column(ForeignKey("warehouse_locations.id"), nullable=True)
    # Valor original cuando `0018` reparó o anuló la referencia. Nunca se
    # pierde el rastro (FR-008-101).
    legacy_location_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False, index=True)
    lot_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    serial_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="DISPONIBLE")
    qty_on_hand: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    qty_reserved: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    qty_available: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    last_rebuilt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Reservation(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Reserva de inventario sin cambio físico (FR-003-040/041/042/043)."""

    __tablename__ = "reservations"

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    source_document: Mapped[str | None] = mapped_column(String(200), nullable=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False, index=True)
    warehouse_id: Mapped[str] = mapped_column(ForeignKey("warehouses.id"), nullable=False, index=True)
    lot_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    serial_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")  # ACTIVE/RELEASED/EXPIRED/FULFILLED
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Transfer(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, Base):
    """Transferencia entre almacenes con máquina de estados (FR-003-060/061)."""

    __tablename__ = "transfers"

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    origin_warehouse_id: Mapped[str] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    destination_warehouse_id: Mapped[str] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    request_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    shipment_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    receipt_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")


class TransferLine(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "transfer_lines"

    transfer_id: Mapped[str] = mapped_column(ForeignKey("transfers.id"), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False)
    lot_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    serial_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    quantity_sent: Mapped[float] = mapped_column(Float, nullable=False)
    quantity_received: Mapped[float | None] = mapped_column(Float, nullable=True)
    difference: Mapped[float | None] = mapped_column(Float, nullable=True)
    destination_state: Mapped[str] = mapped_column(String(32), nullable=False, default="DISPONIBLE")


class StockCount(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, Base):
    """Plan de conteo (FR-003-070/071)."""

    __tablename__ = "stock_counts"

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    warehouse_id: Mapped[str] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    plan_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    scope: Mapped[list] = mapped_column(JSON, nullable=False, default=list)  # filtros del alcance
    freeze_policy: Mapped[str] = mapped_column(String(32), nullable=False, default="PER_PRODUCT")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")  # DRAFT/FROZEN/COUNTING/SUBMITTED/APPROVED/CLOSED


class StockCountLine(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "stock_count_lines"

    count_id: Mapped[str] = mapped_column(ForeignKey("stock_counts.id"), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False)
    location_id: Mapped[str | None] = mapped_column(ForeignKey("warehouse_locations.id"), nullable=True)
    legacy_location_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    lot_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    expected_qty: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    counted_qty: Mapped[float | None] = mapped_column(Float, nullable=True)
    variance: Mapped[float | None] = mapped_column(Float, nullable=True)


class InventoryAdjustment(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Ajuste con motivo, evidencia, costo y aprobación (FR-003-072/073).

    Nunca edita el saldo: al aprobarse genera un `InventoryMovement`.
    """

    __tablename__ = "inventory_adjustments"

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    warehouse_id: Mapped[str] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    product_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)  # >0 suma, <0 resta
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    unit_cost: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="VED")
    approver_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")  # DRAFT/SUBMITTED/APPROVED/REJECTED/APPLIED


class CostLayer(UUIDMixin, TimestampMixin, Base):
    """Capa de costo (FR-003-080): recepción/producto/almacén, cantidades y costo."""

    __tablename__ = "cost_layers"

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False, index=True)
    warehouse_id: Mapped[str] = mapped_column(ForeignKey("warehouses.id"), nullable=False, index=True)
    receipt_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    quantity_in: Mapped[float] = mapped_column(Float, nullable=False)
    quantity_remaining: Mapped[float] = mapped_column(Float, nullable=False)
    unit_cost: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="VED")
    fiscal_rate: Mapped[float | None] = mapped_column(Numeric(14, 6), nullable=True)
    landed_cost: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN")


class CostingProfile(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, VersionMixin, StatusMixin, Base):
    """Método de valoración versionado (FR-003-081, P8). Default AVERAGE."""

    __tablename__ = "costing_profiles"

    company_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)  # None = global
    product_id: Mapped[str | None] = mapped_column(ForeignKey("catalog_items.id"), nullable=True)
    method: Mapped[str] = mapped_column(String(16), nullable=False, default="AVERAGE")  # AVERAGE / FIFO
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="VED")
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)


def as_dict(instance: Any) -> dict[str, Any]:
    return {c.name: getattr(instance, c.name) for c in instance.__table__.columns}
