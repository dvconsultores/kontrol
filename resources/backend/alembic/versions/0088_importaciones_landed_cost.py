"""Importaciones landed cost

Revision ID: 0088_importaciones_landed_cost
Revises: 0087_importaciones_gastos
Create Date: 2024-01-01 00:00:00.000000
"""
import sqlalchemy as sa

from alembic import op

revision = "0088_importaciones_landed_cost"
down_revision = "0087_importaciones_gastos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "import_expenses",
        sa.Column(
            "capitalization",
            sa.String(16),
            nullable=False,
            server_default="UNDETERMINED",
        ),
    )
    op.create_check_constraint(
        "ck_import_expenses_capitalization",
        "import_expenses",
        "capitalization IN ('CAPITALIZABLE','NOT_CAPITALIZABLE','UNDETERMINED')",
    )

    op.create_table(
        "import_cost_applications",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("file_id", sa.String(36), sa.ForeignKey("import_files.id"), nullable=False),
        sa.Column("expense_id", sa.String(36), sa.ForeignKey("import_expenses.id"), nullable=False),
        sa.Column("criterion", sa.String(16), nullable=False),
        sa.Column("criterion_source", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="APPLIED"),
        sa.Column("origin_currency", sa.String(8), nullable=False),
        sa.Column("origin_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("origin_rate_snapshot_id", sa.String(36), sa.ForeignKey("treasury_rate_snapshots.id"), nullable=False),
        sa.Column("origin_rate_value", sa.Numeric(24, 12), nullable=False),
        sa.Column("valuation_currency", sa.String(8), nullable=False),
        sa.Column("valuation_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("valuation_rate_snapshot_id", sa.String(36), sa.ForeignKey("treasury_rate_snapshots.id"), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_by", sa.String(36), nullable=True),
        sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reversed_by", sa.String(36), nullable=True),
        sa.Column("reversal_reason", sa.String(255), nullable=True),
        sa.CheckConstraint("criterion IN ('VALUE','QUANTITY','MANUAL')", name="ck_import_cost_applications_criterion"),
        sa.CheckConstraint("status IN ('APPLIED','REVERSED')", name="ck_import_cost_applications_status"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_import_cost_applications_company", "import_cost_applications", ["company_id"])
    op.create_index("ix_import_cost_applications_file", "import_cost_applications", ["file_id"])
    op.create_index("ix_import_cost_applications_expense", "import_cost_applications", ["expense_id"])
    op.create_index(
        "uq_import_cost_applications_applied",
        "import_cost_applications",
        ["expense_id"],
        unique=True,
        postgresql_where=sa.text("status = 'APPLIED'"),
        sqlite_where=sa.text("status = 'APPLIED'"),
    )

    op.create_table(
        "import_cost_allocations",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("application_id", sa.String(36), sa.ForeignKey("import_cost_applications.id"), nullable=False),
        sa.Column("layer_id", sa.String(36), sa.ForeignKey("cost_layers.id"), nullable=False),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("catalog_items.id"), nullable=False),
        sa.Column("allocation_base", sa.Numeric(24, 6), nullable=False),
        sa.Column("participation", sa.Numeric(12, 8), nullable=False),
        sa.Column("exact_share", sa.Numeric(18, 6), nullable=False),
        sa.Column("rounded_share", sa.Numeric(18, 2), nullable=False),
        sa.Column("residual_adjustment", sa.Numeric(18, 2), nullable=False),
        sa.Column("allocated_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("before_landed_cost", sa.Numeric(18, 2), nullable=False),
        sa.Column("after_landed_cost", sa.Numeric(18, 2), nullable=False),
        sa.Column("before_unit_cost", sa.Numeric(18, 6), nullable=False),
        sa.Column("after_unit_cost", sa.Numeric(18, 6), nullable=False),
        sa.UniqueConstraint("application_id", "layer_id", name="uq_import_cost_allocations_application_layer"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_import_cost_allocations_company", "import_cost_allocations", ["company_id"])
    op.create_index("ix_import_cost_allocations_application", "import_cost_allocations", ["application_id"])
    op.create_index("ix_import_cost_allocations_layer", "import_cost_allocations", ["layer_id"])
    op.create_index("ix_import_cost_allocations_product", "import_cost_allocations", ["product_id"])


def downgrade() -> None:
    op.drop_table("import_cost_allocations")
    op.drop_table("import_cost_applications")
    op.drop_constraint("ck_import_expenses_capitalization", "import_expenses", type_="check")
    op.drop_column("import_expenses", "capitalization")
