"""0104_receipt_temporary_zone

Spec 018 §2; nullable reference; no backfill.
"""
import sqlalchemy as sa

from alembic import op

revision = "0104_receipt_temporary_zone"
down_revision = "0103_receipt_putaway_link"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("goods_receipts", sa.Column("temporary_location_id", sa.String(length=36), nullable=True))
    op.create_foreign_key(
        "fk_goods_receipts_temporary_location_id_warehouse_locations",
        "goods_receipts",
        "warehouse_locations",
        ["temporary_location_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_goods_receipts_temporary_location_id_warehouse_locations",
        "goods_receipts",
        type_="foreignkey",
    )
    op.drop_column("goods_receipts", "temporary_location_id")
