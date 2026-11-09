"""Import difference report

Revision ID: 0090_import_difference_report
Revises: 0089_fusion_gov_landed
Create Date: 2024-01-01 00:00:00.000000
"""
import sqlalchemy as sa

from alembic import op

revision = "0090_import_difference_report"
down_revision = "0089_fusion_gov_landed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "import_difference_reports",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("import_file_id", sa.String(36), sa.ForeignKey("import_files.id"), nullable=False),
        sa.Column("receipt_id", sa.String(36), sa.ForeignKey("goods_receipts.id"), nullable=False),
        sa.Column("chain_number", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("reference", sa.String(32), nullable=False),
        sa.Column("supersedes_id", sa.String(36), sa.ForeignKey("import_difference_reports.id"), nullable=True),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("issued_by", sa.String(36), nullable=False),
        sa.Column("issued_by_name", sa.String(64), nullable=False),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("file_code", sa.String(64), nullable=False),
        sa.Column("order_code", sa.String(64), nullable=True),
        sa.Column("supplier_name", sa.String(200), nullable=True),
        sa.Column("receipt_code", sa.String(64), nullable=False),
        sa.Column("warehouse_name", sa.String(200), nullable=True),
        sa.Column("line_count", sa.Integer(), nullable=False),
        sa.Column("incident_count", sa.Integer(), nullable=False),
        sa.Column("evidence_count", sa.Integer(), nullable=False),
        sa.Column("snapshot_hash", sa.String(64), nullable=False),
        sa.Column("storage_key", sa.String(255), nullable=False),
        sa.Column("file_sha256", sa.String(64), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("file_name", sa.String(120), nullable=False),
        sa.UniqueConstraint("company_id", "reference", name="uq_import_difference_reports_company_reference"),
        sa.UniqueConstraint("company_id", "chain_number", "revision", name="uq_import_difference_reports_chain_revision"),
        sa.UniqueConstraint("receipt_id", "revision", name="uq_import_difference_reports_receipt_revision"),
        sa.CheckConstraint("revision >= 1", name="ck_import_difference_reports_revision_positive"),
        sa.CheckConstraint("chain_number >= 1", name="ck_import_difference_reports_chain_positive"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_import_difference_reports_company", "import_difference_reports", ["company_id"])
    op.create_index("ix_import_difference_reports_receipt", "import_difference_reports", ["receipt_id"])
    op.create_index("ix_import_difference_reports_file", "import_difference_reports", ["import_file_id"])
    op.create_index(
        "uq_import_difference_reports_storage_key",
        "import_difference_reports",
        ["storage_key"],
        unique=True,
    )

    op.create_table(
        "import_difference_report_lines",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("report_id", sa.String(36), sa.ForeignKey("import_difference_reports.id"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("receipt_line_id", sa.String(36), nullable=False),
        sa.Column("product_code", sa.String(64), nullable=True),
        sa.Column("product_name", sa.String(200), nullable=True),
        sa.Column("presentation_code", sa.String(64), nullable=True),
        sa.Column("base_uom", sa.String(16), nullable=True),
        sa.Column("conversion_factor", sa.Numeric(18, 6), nullable=True),
        sa.Column("ordered_base", sa.Numeric(18, 6), nullable=True),
        sa.Column("received_base", sa.Numeric(18, 6), nullable=True),
        sa.Column("counted_base", sa.Numeric(18, 6), nullable=True),
        sa.Column("accepted_base", sa.Numeric(18, 6), nullable=True),
        sa.Column("rejected_base", sa.Numeric(18, 6), nullable=True),
        sa.Column("damaged_base", sa.Numeric(18, 6), nullable=True),
        sa.Column("overage_base", sa.Numeric(18, 6), nullable=True),
        sa.Column("difference_kinds", sa.String(200), nullable=True),
        sa.Column("physical_condition", sa.String(24), nullable=True),
        sa.Column("observation", sa.Text(), nullable=True),
        sa.UniqueConstraint("report_id", "position", name="uq_import_difference_report_lines_position"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_import_difference_report_lines_company", "import_difference_report_lines", ["company_id"])
    op.create_index("ix_import_difference_report_lines_report", "import_difference_report_lines", ["report_id"])

    op.create_table(
        "import_difference_report_incidents",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("report_id", sa.String(36), sa.ForeignKey("import_difference_reports.id"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("incident_id", sa.String(36), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("incident_type", sa.String(32), nullable=False),
        sa.Column("receipt_line_id", sa.String(36), nullable=True),
        sa.Column("product_name", sa.String(200), nullable=True),
        sa.Column("affected_base_quantity", sa.Numeric(18, 6), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("escalated_by_name", sa.String(64), nullable=True),
        sa.Column("escalation_notes", sa.Text(), nullable=True),
        sa.Column("resolution", sa.String(32), nullable=True),
        sa.Column("resolution_reason", sa.Text(), nullable=True),
        sa.Column("authorization_status", sa.String(32), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by_name", sa.String(64), nullable=True),
        sa.Column("registered_by_name", sa.String(64), nullable=False),
        sa.UniqueConstraint("report_id", "position", name="uq_import_difference_report_incidents_position"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_import_difference_report_incidents_company", "import_difference_report_incidents", ["company_id"])
    op.create_index("ix_import_difference_report_incidents_report", "import_difference_report_incidents", ["report_id"])

    op.create_table(
        "import_difference_report_evidence",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("report_id", sa.String(36), sa.ForeignKey("import_difference_reports.id"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("resource_code", sa.String(64), nullable=False),
        sa.Column("document_title", sa.String(200), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=True),
        sa.Column("file_name", sa.String(255), nullable=True),
        sa.Column("sha256", sa.String(64), nullable=True),
        sa.UniqueConstraint("report_id", "position", name="uq_import_difference_report_evidence_position"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_import_difference_report_evidence_company", "import_difference_report_evidence", ["company_id"])
    op.create_index("ix_import_difference_report_evidence_report", "import_difference_report_evidence", ["report_id"])


def downgrade() -> None:
    op.drop_table("import_difference_report_evidence")
    op.drop_table("import_difference_report_incidents")
    op.drop_table("import_difference_report_lines")
    op.drop_table("import_difference_reports")
