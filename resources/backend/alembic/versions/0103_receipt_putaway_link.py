"""0103_receipt_putaway_link

Backfill rule: exact match on goods_receipts.code = inventory_movements.document_ref
within the same company and warehouse, movement_type.code = 'UBICACION',
movement.status = 'POSTED', movement.reversed_by_id IS NULL,
movement.source_location_id IS NULL, and the receipt code is unique in the company.
Only first placements are linked; ambiguous codes are skipped.
Owner-authorized 2026-11-11.
"""
from uuid import uuid4

import sqlalchemy as sa

from alembic import op

revision = "0103_receipt_putaway_link"
down_revision = "0102_gov_ctl09_actas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "receipt_putaways",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("receipt_id", sa.String(length=36), nullable=False),
        sa.Column("movement_id", sa.String(length=36), nullable=False),
        sa.Column("product_id", sa.String(length=36), nullable=False),
        sa.Column("warehouse_id", sa.String(length=36), nullable=False),
        sa.Column("base_quantity", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["receipt_id"], ["goods_receipts.id"]),
        sa.ForeignKeyConstraint(["movement_id"], ["inventory_movements.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["catalog_items.id"]),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"]),
        sa.UniqueConstraint("movement_id", name="uq_receipt_putaways_movement"),
    )
    op.create_index("ix_receipt_putaways_company_id", "receipt_putaways", ["company_id"])
    op.create_index("ix_receipt_putaways_receipt_id", "receipt_putaways", ["receipt_id"])

    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            """
            SELECT
                m.id AS movement_id,
                m.company_id,
                r.id AS receipt_id,
                m.product_id,
                m.warehouse_id,
                COALESCE(m.base_quantity, m.quantity) AS base_quantity,
                m.created_by
            FROM inventory_movements m
            JOIN movement_types t
              ON t.id = m.movement_type_id
             AND t.code = 'UBICACION'
            JOIN goods_receipts r
              ON r.code = m.document_ref
             AND r.company_id = m.company_id
             AND r.warehouse_id = m.warehouse_id
            WHERE m.status = 'POSTED'
              AND m.reversed_by_id IS NULL
              AND m.source_location_id IS NULL
              AND (
                  SELECT COUNT(*)
                  FROM goods_receipts r2
                  WHERE r2.company_id = m.company_id
                    AND r2.code = m.document_ref
              ) = 1
            """
        )
    ).mappings()

    receipt_putaways = sa.table(
        "receipt_putaways",
        sa.column("id", sa.String),
        sa.column("created_by", sa.String),
        sa.column("company_id", sa.String),
        sa.column("receipt_id", sa.String),
        sa.column("movement_id", sa.String),
        sa.column("product_id", sa.String),
        sa.column("warehouse_id", sa.String),
        sa.column("base_quantity", sa.Numeric),
    )

    payload = []
    for row in rows:
        payload.append({
            "id": str(uuid4()),
            "created_by": row["created_by"],
            "company_id": row["company_id"],
            "receipt_id": row["receipt_id"],
            "movement_id": row["movement_id"],
            "product_id": row["product_id"],
            "warehouse_id": row["warehouse_id"],
            "base_quantity": row["base_quantity"],
        })

    if payload:
        op.bulk_insert(receipt_putaways, payload)


def downgrade() -> None:
    op.drop_index("ix_receipt_putaways_receipt_id", table_name="receipt_putaways")
    op.drop_index("ix_receipt_putaways_company_id", table_name="receipt_putaways")
    op.drop_table("receipt_putaways")
