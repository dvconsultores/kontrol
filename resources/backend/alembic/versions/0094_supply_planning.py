"""Supply planning

Revision ID: 0094_supply_planning
Revises: 0093_fusion_gov_storage
Create Date: 2024-01-01 00:00:00.000000
"""
import sqlalchemy as sa

from alembic import op

revision = "0094_supply_planning"
down_revision = "0093_fusion_gov_storage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "planning_policies",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("warehouse_id", sa.String(36), nullable=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("demand_source", sa.String(32), nullable=False),
        sa.Column("lookback_days", sa.Integer(), nullable=False),
        sa.Column("horizon_days", sa.Integer(), nullable=False),
        sa.Column("lead_time_days", sa.Integer(), nullable=False),
        sa.Column("safety_mode", sa.String(16), nullable=False),
        sa.Column("safety_value", sa.Numeric(18, 6), nullable=False),
        sa.Column("rotation_metric", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "code", name="uq_planning_policies_company_code"),
        sa.CheckConstraint("demand_source IN ('DISPATCHED_SALES', 'INVENTORY_ISSUES')", name="demand_source"),
        sa.CheckConstraint("lookback_days > 0", name="lookback_positive"),
        sa.CheckConstraint("horizon_days > 0", name="horizon_positive"),
        sa.CheckConstraint("lead_time_days >= 0", name="lead_time_nonneg"),
        sa.CheckConstraint("safety_mode IN ('NONE', 'FIXED_QTY', 'DAYS')", name="safety_mode"),
        sa.CheckConstraint("safety_value >= 0", name="safety_value_nonneg"),
        sa.CheckConstraint("rotation_metric IN ('DEMAND_VELOCITY', 'TURNOVER')", name="rotation_metric"),
        sa.CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="status"),
        sa.CheckConstraint("valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from", name="validity_range"),
    )
    op.create_index("ix_planning_policies_company_id", "planning_policies", ["company_id"])

    op.create_table(
        "rotation_bands",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("metric", sa.String(32), nullable=False),
        sa.Column("lower_bound", sa.Numeric(18, 6), nullable=False),
        sa.Column("upper_bound", sa.Numeric(18, 6), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "code", name="uq_rotation_bands_company_code"),
        sa.CheckConstraint("metric IN ('DEMAND_VELOCITY', 'TURNOVER')", name="metric"),
        sa.CheckConstraint("lower_bound >= 0", name="lower_nonneg"),
        sa.CheckConstraint("upper_bound IS NULL OR upper_bound > lower_bound", name="range"),
        sa.CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="status"),
    )
    op.create_index("ix_rotation_bands_company_id", "rotation_bands", ["company_id"])

    op.create_table(
        "requisition_line_plans",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("requisition_id", sa.String(36), nullable=False),
        sa.Column("requisition_line_id", sa.String(36), nullable=False),
        sa.Column("warehouse_id", sa.String(36), nullable=False),
        sa.Column("product_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("method", sa.String(40), nullable=False),
        sa.Column("policy_id", sa.String(36), nullable=True),
        sa.Column("policy_version", sa.BigInteger(), nullable=True),
        sa.Column("policy_code", sa.String(64), nullable=True),
        sa.Column("demand_source", sa.String(32), nullable=True),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lookback_days", sa.Integer(), nullable=True),
        sa.Column("horizon_days", sa.Integer(), nullable=True),
        sa.Column("lead_time_days", sa.Integer(), nullable=True),
        sa.Column("safety_mode", sa.String(16), nullable=True),
        sa.Column("safety_value", sa.Numeric(18, 6), nullable=True),
        sa.Column("history_partial", sa.Boolean(), nullable=False),
        sa.Column("observed_history_days", sa.Integer(), nullable=True),
        sa.Column("demand_events", sa.Integer(), nullable=True),
        sa.Column("demand_days", sa.Integer(), nullable=True),
        sa.Column("first_demand_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_demand_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("net_demand", sa.Numeric(18, 6), nullable=True),
        sa.Column("avg_daily_demand", sa.Numeric(18, 6), nullable=True),
        sa.Column("projected_demand", sa.Numeric(18, 6), nullable=True),
        sa.Column("safety_stock", sa.Numeric(18, 6), nullable=True),
        sa.Column("reorder_point", sa.Numeric(18, 6), nullable=True),
        sa.Column("on_hand", sa.Numeric(18, 6), nullable=True),
        sa.Column("reserved", sa.Numeric(18, 6), nullable=True),
        sa.Column("available", sa.Numeric(18, 6), nullable=True),
        sa.Column("open_supply", sa.Numeric(18, 6), nullable=True),
        sa.Column("demand_velocity", sa.Numeric(18, 6), nullable=True),
        sa.Column("turnover", sa.Numeric(18, 6), nullable=True),
        sa.Column("avg_on_hand", sa.Numeric(18, 6), nullable=True),
        sa.Column("coverage_days", sa.Numeric(18, 6), nullable=True),
        sa.Column("recommended_quantity", sa.Numeric(18, 6), nullable=True),
        sa.Column("open_supply_available", sa.Boolean(), nullable=False),
        sa.Column("rotation_metric", sa.String(32), nullable=True),
        sa.Column("rotation_band_id", sa.String(36), nullable=True),
        sa.Column("rotation_band_code", sa.String(64), nullable=True),
        sa.Column("requested_base_quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("difference", sa.Numeric(18, 6), nullable=True),
        sa.Column("accepted_recommendation", sa.Boolean(), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("calculated_by", sa.String(36), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["requisition_id"], ["purchase_requisitions.id"]),
        sa.ForeignKeyConstraint(["requisition_line_id"], ["purchase_requisition_lines.id"]),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["catalog_items.id"]),
        sa.ForeignKeyConstraint(["policy_id"], ["planning_policies.id"]),
        sa.ForeignKeyConstraint(["rotation_band_id"], ["rotation_bands.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("requisition_line_id", name="uq_requisition_line_plans_line"),
        sa.CheckConstraint("status IN ('OK', 'INSUFFICIENT_HISTORY', 'PLAN_NOT_CONFIGURED')", name="status"),
    )
    op.create_index("ix_requisition_line_plans_company_id", "requisition_line_plans", ["company_id"])
    op.create_index("ix_requisition_line_plans_requisition_id", "requisition_line_plans", ["requisition_id"])

    op.add_column("purchase_requisitions", sa.Column("warehouse_id", sa.String(36), nullable=True))
    op.create_foreign_key(
        op.f("fk_purchase_requisitions_warehouse_id_warehouses"),
        "purchase_requisitions",
        "warehouses",
        ["warehouse_id"],
        ["id"],
    )

    op.add_column("storage_rules", sa.Column("rotation_band_id", sa.String(36), nullable=True))
    op.create_foreign_key(
        op.f("fk_storage_rules_rotation_band_id_rotation_bands"),
        "storage_rules",
        "rotation_bands",
        ["rotation_band_id"],
        ["id"],
    )

    op.add_column("storage_classifications", sa.Column("input_rotation_band", sa.String(64), nullable=True))

    op.drop_constraint(op.f("ck_storage_rules_has_criterion"), "storage_rules", type_="check")
    op.create_check_constraint(
        op.f("ck_storage_rules_has_criterion"),
        "storage_rules",
        "taxonomy_id IS NOT NULL OR size_class_id IS NOT NULL OR condition_id IS NOT NULL OR "
        "min_weight IS NOT NULL OR max_weight IS NOT NULL OR min_volume IS NOT NULL OR max_volume IS NOT NULL "
        "OR rotation_band_id IS NOT NULL",
    )

    op.create_index(
        "ix_inventory_movements_planning",
        "inventory_movements",
        ["company_id", "warehouse_id", "product_id", "occurred_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_inventory_movements_planning", table_name="inventory_movements")

    op.drop_constraint(op.f("ck_storage_rules_has_criterion"), "storage_rules", type_="check")
    op.create_check_constraint(
        op.f("ck_storage_rules_has_criterion"),
        "storage_rules",
        "taxonomy_id IS NOT NULL OR size_class_id IS NOT NULL OR condition_id IS NOT NULL OR "
        "min_weight IS NOT NULL OR max_weight IS NOT NULL OR min_volume IS NOT NULL OR max_volume IS NOT NULL",
    )

    op.drop_column("storage_classifications", "input_rotation_band")
    op.drop_constraint(
        op.f("fk_storage_rules_rotation_band_id_rotation_bands"),
        "storage_rules",
        type_="foreignkey",
    )
    op.drop_column("storage_rules", "rotation_band_id")
    op.drop_constraint(
        op.f("fk_purchase_requisitions_warehouse_id_warehouses"),
        "purchase_requisitions",
        type_="foreignkey",
    )
    op.drop_column("purchase_requisitions", "warehouse_id")

    op.drop_index("ix_requisition_line_plans_requisition_id", table_name="requisition_line_plans")
    op.drop_index("ix_requisition_line_plans_company_id", table_name="requisition_line_plans")
    op.drop_table("requisition_line_plans")
    op.drop_index("ix_rotation_bands_company_id", table_name="rotation_bands")
    op.drop_table("rotation_bands")
    op.drop_index("ix_planning_policies_company_id", table_name="planning_policies")
    op.drop_table("planning_policies")
