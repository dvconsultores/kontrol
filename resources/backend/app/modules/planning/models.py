from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy import (
    false as sa_false,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.scope import Scope
from app.shared.mixins import TimestampMixin, UUIDMixin, VersionMixin


class PlanningPolicy(UUIDMixin, TimestampMixin, VersionMixin, Base):
    __tablename__ = "planning_policies"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_planning_policies_company_code"),
        CheckConstraint("demand_source IN ('DISPATCHED_SALES', 'INVENTORY_ISSUES')", name="demand_source"),
        CheckConstraint("lookback_days > 0", name="lookback_positive"),
        CheckConstraint("horizon_days > 0", name="horizon_positive"),
        CheckConstraint("lead_time_days >= 0", name="lead_time_nonneg"),
        CheckConstraint("safety_mode IN ('NONE', 'FIXED_QTY', 'DAYS')", name="safety_mode"),
        CheckConstraint("safety_value >= 0", name="safety_value_nonneg"),
        CheckConstraint("rotation_metric IN ('DEMAND_VELOCITY', 'TURNOVER')", name="rotation_metric"),
        CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="status"),
        CheckConstraint("valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from", name="validity_range"),
    )

    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    warehouse_id: Mapped[str | None] = mapped_column(ForeignKey("warehouses.id"), nullable=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    demand_source: Mapped[str] = mapped_column(String(32), nullable=False)
    lookback_days: Mapped[int] = mapped_column(Integer, nullable=False)
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=False)
    safety_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    safety_value: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    rotation_metric: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    auto_replenishment_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=sa_false())


class RotationBand(UUIDMixin, TimestampMixin, VersionMixin, Base):
    __tablename__ = "rotation_bands"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_rotation_bands_company_code"),
        CheckConstraint("metric IN ('DEMAND_VELOCITY', 'TURNOVER')", name="metric"),
        CheckConstraint("lower_bound >= 0", name="lower_nonneg"),
        CheckConstraint("upper_bound IS NULL OR upper_bound > lower_bound", name="range"),
        CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="status"),
    )

    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    metric: Mapped[str] = mapped_column(String(32), nullable=False)
    lower_bound: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    upper_bound: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")


class RequisitionLinePlan(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "requisition_line_plans"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("requisition_line_id", name="uq_requisition_line_plans_line"),
        CheckConstraint("status IN ('OK', 'INSUFFICIENT_HISTORY', 'PLAN_NOT_CONFIGURED')", name="status"),
        Index("ix_requisition_line_plans_requisition_id", "requisition_id"),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    requisition_id: Mapped[str] = mapped_column(ForeignKey("purchase_requisitions.id"), nullable=False)
    requisition_line_id: Mapped[str] = mapped_column(ForeignKey("purchase_requisition_lines.id"), nullable=False)
    warehouse_id: Mapped[str] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    product_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    method: Mapped[str] = mapped_column(String(40), nullable=False)
    policy_id: Mapped[str | None] = mapped_column(ForeignKey("planning_policies.id"), nullable=True)
    policy_version: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    policy_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    demand_source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lookback_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    horizon_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lead_time_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    safety_mode: Mapped[str | None] = mapped_column(String(16), nullable=True)
    safety_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    history_partial: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    observed_history_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    demand_events: Mapped[int | None] = mapped_column(Integer, nullable=True)
    demand_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    first_demand_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_demand_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    net_demand: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    avg_daily_demand: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    projected_demand: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    safety_stock: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    reorder_point: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    on_hand: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    reserved: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    available: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    open_supply: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    demand_velocity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    turnover: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    avg_on_hand: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    coverage_days: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    recommended_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    open_supply_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rotation_metric: Mapped[str | None] = mapped_column(String(32), nullable=True)
    rotation_band_id: Mapped[str | None] = mapped_column(ForeignKey("rotation_bands.id"), nullable=True)
    rotation_band_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    requested_base_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    difference: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    accepted_recommendation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    calculated_by: Mapped[str] = mapped_column(String(36), nullable=False)
    replenishment_need_id: Mapped[str | None] = mapped_column(ForeignKey("replenishment_needs.id"), nullable=True, index=True)


class ReplenishmentNeed(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "replenishment_needs"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        CheckConstraint("status IN ('ACTIVE', 'RESOLVED')", name="status"),
        CheckConstraint("resolution_reason IS NULL OR resolution_reason IN ('CONDITION_CLEARED', 'PLAN_UNAVAILABLE', 'POLICY_DISABLED', 'PRODUCT_INACTIVE', 'WAREHOUSE_INACTIVE')", name="resolution_reason"),
        CheckConstraint("(status = 'ACTIVE' AND resolved_at IS NULL AND resolution_reason IS NULL) OR (status = 'RESOLVED' AND resolved_at IS NOT NULL AND resolution_reason IS NOT NULL)", name="resolution_state"),
        Index("uq_replenishment_needs_active", "company_id", "warehouse_id", "product_id", unique=True,
              postgresql_where=text("status = 'ACTIVE'"), sqlite_where=text("status = 'ACTIVE'")),
        Index("ix_replenishment_needs_company_status", "company_id", "status"),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    warehouse_id: Mapped[str] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    product_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False)

    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")
    trigger_method: Mapped[str] = mapped_column(String(64), nullable=False)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)

    trigger_policy_id: Mapped[str] = mapped_column(ForeignKey("planning_policies.id"), nullable=False)
    trigger_policy_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    trigger_policy_code: Mapped[str] = mapped_column(String(64), nullable=False)
    trigger_available: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    trigger_on_hand: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    trigger_reserved: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    trigger_reorder_point: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    trigger_projected_demand: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    trigger_avg_daily_demand: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    trigger_safety_stock: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    trigger_recommended_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    trigger_rotation_band_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    trigger_calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    trigger_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)

    last_evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_policy_version: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    current_available: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    current_reorder_point: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    current_projected_demand: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    current_recommended_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    current_rotation_band_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    alert_id: Mapped[str | None] = mapped_column(ForeignKey("alerts.id"), nullable=True)


class ReplenishmentScanCursor(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "replenishment_scan_cursors"
    __scope__ = Scope.COMPANY
    __table_args__ = (UniqueConstraint("company_id", name="uq_replenishment_scan_cursors_company"),)

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False)
    last_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
