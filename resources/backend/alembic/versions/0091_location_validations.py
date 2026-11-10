"""Location validations

Revision ID: 0091_location_validations
Revises: 0090_import_difference_report
Create Date: 2024-01-01 00:00:00.000000
"""
import sqlalchemy as sa

from alembic import op

revision = "0091_location_validations"
down_revision = "0090_import_difference_report"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inventory_location_validations",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("warehouse_id", sa.String(36), nullable=False),
        sa.Column("product_id", sa.String(36), nullable=False),
        sa.Column("lot_id", sa.String(36), nullable=True),
        sa.Column("serial_id", sa.String(36), nullable=True),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("registered_qty_snapshot", sa.Numeric(18, 6), nullable=False),
        sa.Column("registered_location_id", sa.String(36), nullable=False),
        sa.Column("observed_location_id", sa.String(36), nullable=False),
        sa.Column("result", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("validated_by", sa.String(36), nullable=False),
        sa.Column("import_file_id", sa.String(36), nullable=True),
        sa.Column("receipt_id", sa.String(36), nullable=True),
        sa.Column("document_ref", sa.String(200), nullable=True),
        sa.Column("movement_id", sa.String(36), nullable=True),
        sa.Column("relocated_quantity", sa.Numeric(18, 6), nullable=True),
        sa.Column("relocation_reason", sa.Text(), nullable=True),
        sa.Column("relocated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("relocated_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["catalog_items.id"]),
        sa.ForeignKeyConstraint(["registered_location_id"], ["warehouse_locations.id"]),
        sa.ForeignKeyConstraint(["observed_location_id"], ["warehouse_locations.id"]),
        sa.ForeignKeyConstraint(["import_file_id"], ["import_files.id"]),
        sa.ForeignKeyConstraint(["receipt_id"], ["goods_receipts.id"]),
        sa.ForeignKeyConstraint(["movement_id"], ["inventory_movements.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("quantity > 0", name="ck_inventory_location_validations_quantity"),
        sa.CheckConstraint(
            "result IN ('MATCH', 'MISMATCH')",
            name="ck_inventory_location_validations_result",
        ),
        sa.CheckConstraint(
            "status IN ('CONFIRMED', 'PENDING', 'RELOCATED', 'SUPERSEDED')",
            name="ck_inventory_location_validations_status",
        ),
        sa.CheckConstraint(
            "(result = 'MATCH' AND registered_location_id = observed_location_id AND status = 'CONFIRMED') OR (result = 'MISMATCH' AND registered_location_id <> observed_location_id AND status IN ('PENDING', 'RELOCATED', 'SUPERSEDED'))",
            name="ck_inventory_location_validations_coherence",
        ),
        sa.CheckConstraint(
            "(status = 'RELOCATED') = (movement_id IS NOT NULL)",
            name="ck_inventory_location_validations_movement",
        ),
        sa.UniqueConstraint(
            "movement_id", name="uq_inventory_location_validations_movement"
        ),
    )
    op.create_index(
        "ix_inventory_location_validations_identity",
        "inventory_location_validations",
        ["company_id", "warehouse_id", "product_id", "registered_location_id"],
    )
    op.create_index(
        "ix_inventory_location_validations_file",
        "inventory_location_validations",
        ["import_file_id"],
    )
    op.create_index(
        "ix_inventory_location_validations_company_id",
        "inventory_location_validations",
        ["company_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_inventory_location_validations_company_id",
        table_name="inventory_location_validations",
    )
    op.drop_index(
        "ix_inventory_location_validations_file",
        table_name="inventory_location_validations",
    )
    op.drop_index(
        "ix_inventory_location_validations_identity",
        table_name="inventory_location_validations",
    )
    op.drop_table("inventory_location_validations")
