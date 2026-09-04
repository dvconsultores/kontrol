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
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.scope import Scope
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
    __scope__ = Scope.COMPANY
    __table_args__ = (UniqueConstraint("company_id", "code", name="uq_movement_types_company_code"),)

    #: Nulo cuando el tipo es de toda la instalación: la API lo expone como
    #: `global_scope`. El nulo **es** ese interruptor.
    company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)  # None = global
    direction: Mapped[str] = mapped_column(String(16), nullable=False)  # IN / OUT / INTERNAL
    affects_balance: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class InventoryMovement(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Movimiento de inventario balanceado e inmutable (FR-003-020/021/022)."""

    __tablename__ = "inventory_movements"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        Index("ix_inventory_movements_uom_id", "uom_id"),
        # Un movimiento sin ninguno de los dos estados no dice de dónde salió ni
        # a dónde entró: es exactamente el vacío que esta Spec viene a cerrar.
        CheckConstraint("source_state IS NOT NULL OR target_state IS NOT NULL",
                        name="state_provenance"),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    warehouse_id: Mapped[str] = mapped_column(ForeignKey("warehouses.id"), nullable=False, index=True)
    location_id: Mapped[str | None] = mapped_column(ForeignKey("warehouse_locations.id"), nullable=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False, index=True)
    movement_type_id: Mapped[str] = mapped_column(ForeignKey("movement_types.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)  # != 0; signo según dirección
    unit_id: Mapped[str | None] = mapped_column(ForeignKey("units_of_measure.id"), nullable=True)
    unit_cost: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="VED")
    fiscal_rate: Mapped[float | None] = mapped_column(Numeric(14, 6), nullable=True)
    document_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reversed_by_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="POSTED")
    idempotency_key: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)

    # --- Semántica de unidad (Spec 011, R-D0-09-1) ---
    uom_id: Mapped[str | None] = mapped_column(ForeignKey("units_of_measure.id"), nullable=True)
    presentation_id: Mapped[str | None] = mapped_column(ForeignKey("presentations.id"), nullable=True)
    conversion_factor_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    base_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    uom_source: Mapped[str | None] = mapped_column(String(24), nullable=True)

    # Procedencia de estado de mercancía (Spec 023 · `ADR-D0-010` v2, R-D0-10-5).
    # Sin esto el saldo multiestado no es reconstruible: `recompute_balances`
    # tendría que suponer un estado, y suponer `DISPONIBLE` colapsaría en uno
    # solo lo que el motor escribió en varios.
    #   entrada          → `source_state` NULL, `target_state` = destino
    #   salida           → `source_state` = origen, `target_state` NULL
    #   reclasificación  → los dos, y la cantidad viaja de uno a otro
    source_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    target_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
class InventoryLot(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Lote con vencimiento (FR-003-030/032)."""

    __tablename__ = "inventory_lots"
    __scope__ = Scope.COMPANY
    __table_args__ = (UniqueConstraint("company_id", "product_id", "lot_number", name="uq_inventory_lots_company_product_lot"),)

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
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
    __scope__ = Scope.COMPANY
    __table_args__ = (UniqueConstraint("company_id", "serial", name="uq_product_serials_company_serial"),)

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
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
    __scope__ = Scope.COMPANY
    __table_args__ = (
        # Una fila por clave de saldo. Sin esto dos transacciones que reservan
        # el mismo producto en un almacén sin saldo previo crean dos filas y el
        # bloqueo de fila (R-D0-03-3) no tiene sobre qué actuar. Las dimensiones
        # anulables se normalizan a '' para que la unicidad las vea (Spec 030).
        Index(
            "uq_inventory_balances_key",
            "company_id", "warehouse_id",
            text("COALESCE(location_id, '')"),
            "product_id",
            text("COALESCE(lot_id, '')"),
            text("COALESCE(serial_id, '')"),
            "state",
            unique=True,
        ).ddl_if(dialect="postgresql"),
        # El reservado nunca es negativo: liberar dos veces no puede dejar deuda
        # (IMP-030-059). El físico sí puede serlo, por `allow_negative`.
        CheckConstraint("qty_reserved >= 0", name="reserved_nonneg"),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
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
    qty_on_hand: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=0.0)
    qty_reserved: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=0.0)
    qty_available: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=0.0)
    last_rebuilt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Reservation(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Reserva de inventario sin cambio físico (FR-003-040/041/042/043)."""

    __tablename__ = "reservations"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        Index("ix_reservations_uom_id", "uom_id"),
        Index("ix_reservations_source_order", "source_order_id"),
        # Una reserva ACTIVE por línea de pedido (R-D0-03-3, IMP-030-018). Es
        # la base de datos, no `if not exists`, la que impide que un reintento
        # duplique la cantidad comprometida. Va en el ORM y en la migración
        # porque las suites levantan el esquema con `create_all`.
        Index(
            "uq_reservations_active_line", "source_line_id", unique=True,
            postgresql_where=text("status = 'ACTIVE' AND source_line_id IS NOT NULL"),
        ).ddl_if(dialect="postgresql"),
        CheckConstraint("quantity > 0", name="quantity_positive"),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    source_document: Mapped[str | None] = mapped_column(String(200), nullable=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False, index=True)
    warehouse_id: Mapped[str] = mapped_column(ForeignKey("warehouses.id"), nullable=False, index=True)
    lot_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    serial_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")  # ACTIVE/RELEASED/EXPIRED/FULFILLED
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # --- Identidad de la reserva (Spec 030, IMP-030-016/017) ---
    #: `SALES_ORDER` o `MANUAL`. `source_document` (texto) se conserva por
    #: compatibilidad y como único rastro de las filas anteriores a la Spec 030.
    source_type: Mapped[str | None] = mapped_column(String(24), nullable=True)
    source_order_id: Mapped[str | None] = mapped_column(ForeignKey("sales_orders.id"), nullable=True)
    source_line_id: Mapped[str | None] = mapped_column(ForeignKey("sales_order_lines.id"), nullable=True)
    #: `ORDER_CONFIRMATION` · `MANUAL` · `LEGACY_CREDIT_APPROVAL`. Es la versión
    #: de la política con la que nació: un cambio futuro no la reinterpreta (P5).
    trigger: Mapped[str | None] = mapped_column(String(32), nullable=True)
    #: Reservó por encima del disponible bajo `allow_negative` del almacén.
    oversell: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    released_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    #: `ORDER_CANCELLED` · `CREDIT_REJECTED` · `ORDER_REVERTED` · `EXPIRED` ·
    #: `DISPATCHED` · `MANUAL:{texto}` · `PICKING_SHORTAGE` (032).
    release_reason: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # --- Semántica de unidad (Spec 011, R-D0-09-1) ---
    uom_id: Mapped[str | None] = mapped_column(ForeignKey("units_of_measure.id"), nullable=True)
    presentation_id: Mapped[str | None] = mapped_column(ForeignKey("presentations.id"), nullable=True)
    conversion_factor_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    base_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    uom_source: Mapped[str | None] = mapped_column(String(24), nullable=True)
class Transfer(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, Base):
    """Transferencia entre almacenes con máquina de estados (FR-003-060/061)."""

    __tablename__ = "transfers"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    origin_warehouse_id: Mapped[str] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    destination_warehouse_id: Mapped[str] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    request_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    shipment_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    receipt_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")


class TransferLine(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "transfer_lines"
    __scope__ = Scope.COMPANY
    __scope_authority__ = "transfer_id → transfers"
    __table_args__ = (Index("ix_transfer_lines_uom_id", "uom_id"),)

    transfer_id: Mapped[str] = mapped_column(ForeignKey("transfers.id"), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False)
    lot_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    serial_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    quantity_sent: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    quantity_received: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    difference: Mapped[float | None] = mapped_column(Float, nullable=True)
    destination_state: Mapped[str] = mapped_column(String(32), nullable=False, default="DISPONIBLE")

    # --- Semántica de unidad (Spec 011, R-D0-09-1) ---
    uom_id: Mapped[str | None] = mapped_column(ForeignKey("units_of_measure.id"), nullable=True)
    presentation_id: Mapped[str | None] = mapped_column(ForeignKey("presentations.id"), nullable=True)
    conversion_factor_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    base_quantity_sent: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    base_quantity_received: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    uom_source: Mapped[str | None] = mapped_column(String(24), nullable=True)
class StockCount(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, Base):
    """Plan de conteo (FR-003-070/071)."""

    __tablename__ = "stock_counts"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    warehouse_id: Mapped[str] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    plan_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    scope: Mapped[list] = mapped_column(JSON, nullable=False, default=list)  # filtros del alcance
    freeze_policy: Mapped[str] = mapped_column(String(32), nullable=False, default="PER_PRODUCT")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")  # DRAFT/FROZEN/COUNTING/SUBMITTED/APPROVED/CLOSED


class StockCountLine(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "stock_count_lines"
    __scope__ = Scope.COMPANY
    __scope_authority__ = "count_id → stock_counts"
    __table_args__ = (Index("ix_stock_count_lines_uom_id", "uom_id"),)

    count_id: Mapped[str] = mapped_column(ForeignKey("stock_counts.id"), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False)
    location_id: Mapped[str | None] = mapped_column(ForeignKey("warehouse_locations.id"), nullable=True)
    legacy_location_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    lot_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    expected_qty: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=0.0)
    counted_qty: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    variance: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)

    # --- Semántica de unidad (Spec 011, R-D0-09-1) ---
    uom_id: Mapped[str | None] = mapped_column(ForeignKey("units_of_measure.id"), nullable=True)
    presentation_id: Mapped[str | None] = mapped_column(ForeignKey("presentations.id"), nullable=True)
    conversion_factor_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    base_expected_qty: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    base_counted_qty: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    uom_source: Mapped[str | None] = mapped_column(String(24), nullable=True)
class InventoryAdjustment(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Ajuste con motivo, evidencia, costo y aprobación (FR-003-072/073).

    Nunca edita el saldo: al aprobarse genera un `InventoryMovement`.
    """

    __tablename__ = "inventory_adjustments"
    __scope__ = Scope.COMPANY
    __table_args__ = (Index("ix_inventory_adjustments_uom_id", "uom_id"),)

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    warehouse_id: Mapped[str] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    product_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)  # >0 suma, <0 resta
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    unit_cost: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="VED")
    approver_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")  # DRAFT/SUBMITTED/APPROVED/REJECTED/APPLIED

    # --- Semántica de unidad (Spec 011, R-D0-09-1) ---
    uom_id: Mapped[str | None] = mapped_column(ForeignKey("units_of_measure.id"), nullable=True)
    presentation_id: Mapped[str | None] = mapped_column(ForeignKey("presentations.id"), nullable=True)
    conversion_factor_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    base_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    uom_source: Mapped[str | None] = mapped_column(String(24), nullable=True)
class CostLayer(UUIDMixin, TimestampMixin, Base):
    """Capa de costo (FR-003-080): recepción/producto/almacén, cantidades y costo."""

    __tablename__ = "cost_layers"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False, index=True)
    warehouse_id: Mapped[str] = mapped_column(ForeignKey("warehouses.id"), nullable=False, index=True)
    receipt_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    quantity_in: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    quantity_remaining: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    unit_cost: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="VED")
    fiscal_rate: Mapped[float | None] = mapped_column(Numeric(14, 6), nullable=True)
    landed_cost: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN")


class CostingProfile(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, VersionMixin, StatusMixin, Base):
    """Método de valoración versionado (FR-003-081, P8). Default AVERAGE."""

    __tablename__ = "costing_profiles"
    __scope__ = Scope.COMPANY

    #: Nulo cuando el tipo es de toda la instalación: la API lo expone como
    #: `global_scope`. El nulo **es** ese interruptor.
    company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)  # None = global
    product_id: Mapped[str | None] = mapped_column(ForeignKey("catalog_items.id"), nullable=True)
    method: Mapped[str] = mapped_column(String(16), nullable=False, default="AVERAGE")  # AVERAGE / FIFO
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="VED")
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)


def as_dict(instance: Any) -> dict[str, Any]:
    return {c.name: getattr(instance, c.name) for c in instance.__table__.columns}
