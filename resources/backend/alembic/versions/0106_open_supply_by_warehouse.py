"""0106_open_supply_by_warehouse

Spec 015; open supply by warehouse; nullable columns; no backfill.
"""
import sqlalchemy as sa

from alembic import op

revision = "0106_open_supply_by_warehouse"
down_revision = "0105_receipt_temporary_zone"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("purchase_order_lines", sa.Column("destination_warehouse_id", sa.String(length=36), nullable=True))
    op.create_foreign_key(
        "fk_purchase_order_lines_destination_warehouse_id_warehouses",
        "purchase_order_lines",
        "warehouses",
        ["destination_warehouse_id"],
        ["id"],
    )
    op.create_index(
        "ix_purchase_order_lines_destination_warehouse_id_product_id",
        "purchase_order_lines",
        ["destination_warehouse_id", "product_id"],
    )

    for column_name in (
        "trigger_open_supply",
        "trigger_projected_available",
        "current_open_supply",
        "current_projected_available",
    ):
        op.add_column("replenishment_needs", sa.Column(column_name, sa.Numeric(18, 6), nullable=True))


def downgrade():
    for column_name in (
        "trigger_open_supply",
        "trigger_projected_available",
        "current_open_supply",
        "current_projected_available",
    ):
        op.drop_column("replenishment_needs", column_name)

    op.drop_index("ix_purchase_order_lines_destination_warehouse_id_product_id", table_name="purchase_order_lines")
    op.drop_constraint(
        "fk_purchase_order_lines_destination_warehouse_id_warehouses",
        "purchase_order_lines",
        type_="foreignkey",
    )
    op.drop_column("purchase_order_lines", "destination_warehouse_id")
