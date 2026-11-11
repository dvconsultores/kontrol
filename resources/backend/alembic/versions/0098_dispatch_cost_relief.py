"""Dispatch cost relief

Revision ID: 0098_dispatch_cost_relief
Revises: 0097_fusion_gov_replenishment
Create Date: 2024-01-01 00:00:00.000000
"""
import sqlalchemy as sa

from alembic import op

revision = "0098_dispatch_cost_relief"
down_revision = "0097_fusion_gov_replenishment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dispatch_cost_reliefs",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("shipment_id", sa.String(36), nullable=False),
        sa.Column("shipment_line_id", sa.String(36), nullable=False),
        sa.Column("movement_id", sa.String(36), nullable=False),
        sa.Column("cost_layer_id", sa.String(36), nullable=False),
        sa.Column("product_id", sa.String(36), nullable=False),
        sa.Column("warehouse_id", sa.String(36), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("effective_unit_cost", sa.Numeric(18, 6), nullable=False),
        sa.Column("total_cost", sa.Numeric(18, 6), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False, server_default="VED"),
        sa.Column("method", sa.String(32), nullable=False, server_default="AVERAGE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["cost_layer_id"], ["cost_layers.id"]),
        sa.ForeignKeyConstraint(["movement_id"], ["inventory_movements.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["catalog_items.id"]),
        sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"]),
        sa.ForeignKeyConstraint(["shipment_line_id"], ["shipment_lines.id"]),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shipment_line_id", "cost_layer_id",
                            name="uq_dispatch_relief_shipment_line_layer"),
    )
    op.create_index("ix_dispatch_cost_reliefs_company_id", "dispatch_cost_reliefs", ["company_id"])
    op.create_index("ix_dispatch_cost_reliefs_shipment_id", "dispatch_cost_reliefs", ["shipment_id"])
    op.create_index("ix_dispatch_cost_reliefs_shipment_line_id", "dispatch_cost_reliefs", ["shipment_line_id"])
    op.create_index("ix_dispatch_cost_reliefs_product_id", "dispatch_cost_reliefs", ["product_id"])
    op.create_index("ix_dispatch_cost_reliefs_warehouse_id", "dispatch_cost_reliefs", ["warehouse_id"])


def downgrade() -> None:
    op.drop_index("ix_dispatch_cost_reliefs_warehouse_id", table_name="dispatch_cost_reliefs")
    op.drop_index("ix_dispatch_cost_reliefs_product_id", table_name="dispatch_cost_reliefs")
    op.drop_index("ix_dispatch_cost_reliefs_shipment_line_id", table_name="dispatch_cost_reliefs")
    op.drop_index("ix_dispatch_cost_reliefs_shipment_id", table_name="dispatch_cost_reliefs")
    op.drop_index("ix_dispatch_cost_reliefs_company_id", table_name="dispatch_cost_reliefs")
    op.drop_table("dispatch_cost_reliefs")
