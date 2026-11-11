"""Quote award

Revision ID: 0099_quote_award
Revises: 0098_dispatch_cost_relief
Create Date: 2024-01-01 00:00:00.000000
"""
import sqlalchemy as sa

from alembic import op

revision = "0099_quote_award"
down_revision = "0098_dispatch_cost_relief"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("supplier_quotes", sa.Column("awarded_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("supplier_quotes", sa.Column("awarded_by", sa.String(36), nullable=True))
    op.add_column("supplier_quotes", sa.Column("award_reason", sa.Text(), nullable=True))
    op.add_column("purchase_orders", sa.Column("quote_id", sa.String(36), nullable=True))
    op.create_foreign_key("fk_purchase_orders_quote_id", "purchase_orders", "supplier_quotes", ["quote_id"], ["id"])
    op.create_index("uq_purchase_orders_quote_id", "purchase_orders", ["quote_id"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_purchase_orders_quote_id", table_name="purchase_orders")
    op.drop_constraint("fk_purchase_orders_quote_id", "purchase_orders", type_="foreignkey")
    op.drop_column("purchase_orders", "quote_id")
    op.drop_column("supplier_quotes", "award_reason")
    op.drop_column("supplier_quotes", "awarded_by")
    op.drop_column("supplier_quotes", "awarded_at")
