"""Replenishment detection

Revision ID: 0096_replenishment_detection
Revises: 0095_fusion_gov_planning
Create Date: 2024-01-01 00:00:00.000000
"""
import sqlalchemy as sa

from alembic import op

revision = "0096_replenishment_detection"
down_revision = "0095_fusion_gov_planning"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "planning_policies",
        sa.Column("auto_replenishment_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "replenishment_needs",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("warehouse_id", sa.String(36), nullable=False),
        sa.Column("product_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="ACTIVE"),
        sa.Column("trigger_method", sa.String(64), nullable=False),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_reason", sa.String(32), nullable=True),
        sa.Column("trigger_policy_id", sa.String(36), nullable=False),
        sa.Column("trigger_policy_version", sa.BigInteger(), nullable=False),
        sa.Column("trigger_policy_code", sa.String(64), nullable=False),
        sa.Column("trigger_available", sa.Numeric(18, 6), nullable=False),
        sa.Column("trigger_on_hand", sa.Numeric(18, 6), nullable=False),
        sa.Column("trigger_reserved", sa.Numeric(18, 6), nullable=False),
        sa.Column("trigger_reorder_point", sa.Numeric(18, 6), nullable=False),
        sa.Column("trigger_projected_demand", sa.Numeric(18, 6), nullable=False),
        sa.Column("trigger_avg_daily_demand", sa.Numeric(18, 6), nullable=False),
        sa.Column("trigger_safety_stock", sa.Numeric(18, 6), nullable=False),
        sa.Column("trigger_recommended_quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("trigger_rotation_band_code", sa.String(64), nullable=True),
        sa.Column("trigger_calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("trigger_snapshot", sa.JSON(), nullable=False),
        sa.Column("last_evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_policy_version", sa.BigInteger(), nullable=True),
        sa.Column("current_available", sa.Numeric(18, 6), nullable=True),
        sa.Column("current_reorder_point", sa.Numeric(18, 6), nullable=True),
        sa.Column("current_projected_demand", sa.Numeric(18, 6), nullable=True),
        sa.Column("current_recommended_quantity", sa.Numeric(18, 6), nullable=True),
        sa.Column("current_rotation_band_code", sa.String(64), nullable=True),
        sa.Column("alert_id", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["catalog_items.id"]),
        sa.ForeignKeyConstraint(["trigger_policy_id"], ["planning_policies.id"]),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("status IN ('ACTIVE', 'RESOLVED')", name=op.f("ck_replenishment_needs_status")),
        sa.CheckConstraint("resolution_reason IS NULL OR resolution_reason IN ('CONDITION_CLEARED', 'PLAN_UNAVAILABLE', 'POLICY_DISABLED', 'PRODUCT_INACTIVE', 'WAREHOUSE_INACTIVE')", name=op.f("ck_replenishment_needs_resolution_reason")),
        sa.CheckConstraint("(status = 'ACTIVE' AND resolved_at IS NULL AND resolution_reason IS NULL) OR (status = 'RESOLVED' AND resolved_at IS NOT NULL AND resolution_reason IS NOT NULL)", name=op.f("ck_replenishment_needs_resolution_state")),
    )
    op.create_index("ix_replenishment_needs_company_id", "replenishment_needs", ["company_id"])
    op.create_index("ix_replenishment_needs_company_status", "replenishment_needs", ["company_id", "status"])
    op.create_index(
        "uq_replenishment_needs_active",
        "replenishment_needs",
        ["company_id", "warehouse_id", "product_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
        sqlite_where=sa.text("status = 'ACTIVE'"),
    )

    op.create_table(
        "replenishment_scan_cursors",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("last_key", sa.String(80), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", name="uq_replenishment_scan_cursors_company"),
    )

    op.add_column(
        "requisition_line_plans",
        sa.Column("replenishment_need_id", sa.String(36), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_requisition_line_plans_replenishment_need_id_replenishment_needs"),
        "requisition_line_plans",
        "replenishment_needs",
        ["replenishment_need_id"],
        ["id"],
    )
    op.create_index(
        op.f("ix_requisition_line_plans_replenishment_need_id"),
        "requisition_line_plans",
        ["replenishment_need_id"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_requisition_line_plans_replenishment_need_id"), table_name="requisition_line_plans")
    op.drop_constraint(
        op.f("fk_requisition_line_plans_replenishment_need_id_replenishment_needs"),
        "requisition_line_plans",
        type_="foreignkey",
    )
    op.drop_column("requisition_line_plans", "replenishment_need_id")

    op.drop_table("replenishment_scan_cursors")
    op.drop_index("uq_replenishment_needs_active", table_name="replenishment_needs")
    op.drop_index("ix_replenishment_needs_company_status", table_name="replenishment_needs")
    op.drop_index("ix_replenishment_needs_company_id", table_name="replenishment_needs")
    op.drop_table("replenishment_needs")

    op.drop_column("planning_policies", "auto_replenishment_enabled")
