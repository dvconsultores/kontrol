"""importaciones

Revision ID: 0080_importaciones
Revises: 0079_fusion_terceros_org06
Create Date: 2024-01-01 00:00:00.000000
"""
import sqlalchemy as sa

from alembic import op

revision = "0080_importaciones"
down_revision = "0079_fusion_terceros_org06"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "import_files",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("supplier_id", sa.String(36), sa.ForeignKey("parties.id"), nullable=False),
        sa.Column("order_id", sa.String(36), sa.ForeignKey("purchase_orders.id"), nullable=True),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("incoterm", sa.String(8), nullable=True),
        sa.Column("incoterm_place", sa.String(120), nullable=True),
        sa.Column("payment_conditions", sa.Text(), nullable=True),
        sa.Column("delivery_conditions", sa.Text(), nullable=True),
        sa.Column("expected_dispatch_date", sa.Date(), nullable=True),
        sa.Column("expected_arrival_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("cancel_reason", sa.String(255), nullable=True),
        sa.UniqueConstraint("company_id", "code", name="uq_import_files_company_code"),
        sa.CheckConstraint(
            "status IN ('NEGOTIATING','ORDERED','DOCUMENTS_COMPLETE','CANCELLED')",
            name="ck_import_files_status",
        ),
    )
    op.create_index("ix_import_files_company_id", "import_files", ["company_id"])
    op.create_index("ix_import_files_supplier_id", "import_files", ["supplier_id"])
    op.create_index("ix_import_files_order_id", "import_files", ["order_id"])
    op.create_index("ix_import_files_company_status", "import_files", ["company_id", "status"])

    op.create_table(
        "import_documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("file_id", sa.String(36), sa.ForeignKey("import_files.id"), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("reference", sa.String(120), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("observation", sa.String(255), nullable=True),
        sa.CheckConstraint(
            "status IN ('PENDING','RECEIVED','VALIDATED','OBSERVED')",
            name="ck_import_documents_status",
        ),
    )
    op.create_index("ix_import_documents_company_id", "import_documents", ["company_id"])
    op.create_index("ix_import_documents_file_id", "import_documents", ["file_id"])


def downgrade():
    op.drop_index("ix_import_documents_company_id", table_name="import_documents")
    op.drop_index("ix_import_documents_file_id", table_name="import_documents")
    op.drop_table("import_documents")
    op.drop_index("ix_import_files_company_status", table_name="import_files")
    op.drop_index("ix_import_files_order_id", table_name="import_files")
    op.drop_index("ix_import_files_supplier_id", table_name="import_files")
    op.drop_index("ix_import_files_company_id", table_name="import_files")
    op.drop_table("import_files")
