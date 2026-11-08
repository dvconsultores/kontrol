"""importaciones seguimiento

Revision ID: 0082_importaciones_seguimiento
Revises: 0081_fusion_importaciones_ctl02
Create Date: 2024-01-01 00:00:00.000000
"""
import sqlalchemy as sa

from alembic import op

revision = "0082_importaciones_seguimiento"
down_revision = "0081_fusion_importaciones_ctl02"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("import_files", schema=None) as batch_op:
        batch_op.add_column(sa.Column("agent_party_id", sa.String(36), nullable=True))
        batch_op.add_column(sa.Column("carrier_party_id", sa.String(36), nullable=True))
        batch_op.add_column(sa.Column("transport_document", sa.String(120), nullable=True))
        batch_op.add_column(sa.Column("origin", sa.String(120), nullable=True))
        batch_op.add_column(sa.Column("destination", sa.String(120), nullable=True))
        batch_op.add_column(sa.Column("actual_departure_date", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("dispatched_at", sa.Date(), nullable=True))
        batch_op.create_foreign_key("fk_import_files_agent_party_id", "parties", ["agent_party_id"], ["id"])
        batch_op.create_foreign_key("fk_import_files_carrier_party_id", "parties", ["carrier_party_id"], ["id"])
        batch_op.create_index("ix_import_files_agent_party_id", ["agent_party_id"], unique=False)
        batch_op.create_index("ix_import_files_carrier_party_id", ["carrier_party_id"], unique=False)
        batch_op.drop_constraint("ck_import_files_status", type_="check")
        batch_op.create_check_constraint(
            "ck_import_files_status",
            "status IN ('NEGOTIATING','ORDERED','DOCUMENTS_COMPLETE','DISPATCHED','CANCELLED')",
        )

    op.create_table(
        "import_tracking_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("file_id", sa.String(36), nullable=False),
        sa.Column("milestone", sa.String(32), nullable=False),
        sa.Column("occurred_on", sa.Date(), nullable=False),
        sa.Column("location", sa.String(200), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["file_id"], ["import_files.id"]),
        sa.CheckConstraint(
            "milestone IN ('BOOKED','DEPARTED','IN_TRANSIT','TRANSSHIPMENT','DELAYED','OTHER')",
            name="ck_import_tracking_events_milestone",
        ),
    )
    op.create_index("ix_import_tracking_events_company_id", "import_tracking_events", ["company_id"], unique=False)
    op.create_index("ix_import_tracking_events_file_id", "import_tracking_events", ["file_id"], unique=False)

    op.create_table(
        "import_financial_links",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("file_id", sa.String(36), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("target_id", sa.String(36), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["file_id"], ["import_files.id"]),
        sa.UniqueConstraint(
            "company_id",
            "kind",
            "target_id",
            name="uq_import_financial_links_company_kind_target",
        ),
        sa.CheckConstraint("kind IN ('PAYMENT','ADVANCE')", name="ck_import_financial_links_kind"),
    )
    op.create_index("ix_import_financial_links_company_id", "import_financial_links", ["company_id"], unique=False)
    op.create_index("ix_import_financial_links_file_id", "import_financial_links", ["file_id"], unique=False)

    op.create_table(
        "import_corrections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("file_id", sa.String(36), nullable=False),
        sa.Column("document_id", sa.String(36), nullable=True),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("action_required", sa.Text(), nullable=True),
        sa.Column("responsible", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["file_id"], ["import_files.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["import_documents.id"]),
        sa.CheckConstraint("kind IN ('FALTANTE','CORRECCION_DOCUMENTAL')", name="ck_import_corrections_kind"),
        sa.CheckConstraint("responsible IN ('PROVEEDOR','AGENTE','IMPORTACION')", name="ck_import_corrections_responsible"),
        sa.CheckConstraint("status IN ('OPEN','RESOLVED','CANCELLED')", name="ck_import_corrections_status"),
    )
    op.create_index("ix_import_corrections_company_id", "import_corrections", ["company_id"], unique=False)
    op.create_index("ix_import_corrections_file_id", "import_corrections", ["file_id"], unique=False)
    op.create_index("ix_import_corrections_document_id", "import_corrections", ["document_id"], unique=False)


def downgrade():
    with op.batch_alter_table("import_files", schema=None) as batch_op:
        batch_op.drop_constraint("ck_import_files_status", type_="check")
        batch_op.create_check_constraint(
            "ck_import_files_status",
            "status IN ('NEGOTIATING','ORDERED','CANCELLED')",
        )
        batch_op.drop_index("ix_import_files_agent_party_id")
        batch_op.drop_index("ix_import_files_carrier_party_id")
        batch_op.drop_constraint("fk_import_files_agent_party_id", type_="foreignkey")
        batch_op.drop_constraint("fk_import_files_carrier_party_id", type_="foreignkey")
        batch_op.drop_column("agent_party_id")
        batch_op.drop_column("carrier_party_id")
        batch_op.drop_column("transport_document")
        batch_op.drop_column("origin")
        batch_op.drop_column("destination")
        batch_op.drop_column("actual_departure_date")
        batch_op.drop_column("dispatched_at")

    op.drop_table("import_corrections")
    op.drop_table("import_financial_links")
    op.drop_table("import_tracking_events")
