"""Importaciones gastos

Revision ID: 0087_importaciones_gastos
Revises: 0086_importaciones_timestamps
Create Date: 2024-01-01 00:00:00.000000
"""
import sqlalchemy as sa

from alembic import op

revision = "0087_importaciones_gastos"
down_revision = "0086_importaciones_timestamps"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "import_expenses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column(
            "version",
            sa.BigInteger(),
            server_default="1",
            nullable=False,
        ),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("file_id", sa.String(36), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("supplier_id", sa.String(36), nullable=False),
        sa.Column("supplier_invoice_id", sa.String(36), nullable=True),
        sa.Column("reference", sa.String(120), nullable=False),
        sa.Column("concept", sa.String(200), nullable=False),
        sa.Column("expense_date", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("functional_currency", sa.String(8), nullable=False),
        sa.Column("functional_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("rate_snapshot_id", sa.String(36), nullable=False),
        sa.Column("import_document_id", sa.String(36), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="REGISTERED"),
        sa.Column("void_reason", sa.String(255), nullable=True),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("voided_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["file_id"], ["import_files.id"]),
        sa.ForeignKeyConstraint(["supplier_id"], ["parties.id"]),
        sa.ForeignKeyConstraint(["supplier_invoice_id"], ["supplier_invoices.id"]),
        sa.ForeignKeyConstraint(["rate_snapshot_id"], ["treasury_rate_snapshots.id"]),
        sa.ForeignKeyConstraint(["import_document_id"], ["import_documents.id"]),
        sa.CheckConstraint("amount > 0", name="ck_import_expenses_amount_positive"),
        sa.CheckConstraint(
            "status IN ('REGISTERED','VOIDED')", name="ck_import_expenses_status"
        ),
        sa.CheckConstraint(
            "kind IN ('DIRECT_IMPORT_EXPENSE','LINKED_SUPPLIER_INVOICE')",
            name="ck_import_expenses_kind",
        ),
        sa.CheckConstraint(
            "(kind = 'LINKED_SUPPLIER_INVOICE' AND supplier_invoice_id IS NOT NULL) OR "
            "(kind = 'DIRECT_IMPORT_EXPENSE' AND supplier_invoice_id IS NULL)",
            name="ck_import_expenses_invoice_kind",
        ),
    )
    op.create_index(
        "ix_import_expenses_company_id", "import_expenses", ["company_id"], unique=False
    )
    op.create_index(
        "ix_import_expenses_file_id", "import_expenses", ["file_id"], unique=False
    )
    op.create_index(
        "ix_import_expenses_supplier_id", "import_expenses", ["supplier_id"], unique=False
    )
    op.create_index(
        "ix_import_expenses_supplier_invoice_id",
        "import_expenses",
        ["supplier_invoice_id"],
        unique=False,
    )
    op.create_index(
        "ix_import_expenses_import_document_id",
        "import_expenses",
        ["import_document_id"],
        unique=False,
    )
    op.create_index(
        "ix_import_expenses_rate_snapshot_id",
        "import_expenses",
        ["rate_snapshot_id"],
        unique=False,
    )
    op.create_index(
        "ix_import_expenses_company_file",
        "import_expenses",
        ["company_id", "file_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_import_expenses_company_file", table_name="import_expenses")
    op.drop_index("ix_import_expenses_rate_snapshot_id", table_name="import_expenses")
    op.drop_index("ix_import_expenses_import_document_id", table_name="import_expenses")
    op.drop_index("ix_import_expenses_supplier_invoice_id", table_name="import_expenses")
    op.drop_index("ix_import_expenses_supplier_id", table_name="import_expenses")
    op.drop_index("ix_import_expenses_file_id", table_name="import_expenses")
    op.drop_index("ix_import_expenses_company_id", table_name="import_expenses")
    op.drop_table("import_expenses")
