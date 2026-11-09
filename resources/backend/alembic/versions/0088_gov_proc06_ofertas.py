"""gov_proc06_ofertas

Revision ID: 0088_gov_proc06_ofertas
Revises: 0087_importaciones_gastos
Create Date: 2025-01-15 00:00:00.000000
"""
import sqlalchemy as sa

from alembic import op

revision = "0088_gov_proc06_ofertas"
down_revision = "0087_importaciones_gastos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_seals",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=36), nullable=False),
        sa.Column("motivo", sa.String(length=300), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_by", sa.String(length=36), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], name="fk_document_seals_company_id"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], name="fk_document_seals_document_id"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_document_seals_company_id", "document_seals", ["company_id"])
    op.create_index("ix_document_seals_document_id", "document_seals", ["document_id"])
    op.create_index(
        "uq_document_seals_document_active",
        "document_seals",
        ["document_id"],
        unique=True,
        postgresql_where=sa.text("released_at IS NULL"),
    )

    op.create_table(
        "gov_procurement_offers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("file_id", sa.String(length=36), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("oferente_nombre", sa.String(length=300), nullable=False),
        sa.Column("oferente_documento", sa.String(length=40), nullable=False),
        sa.Column("representante", sa.String(length=200), nullable=True),
        sa.Column("tipo_sobre", sa.String(length=16), nullable=False),
        sa.Column("canal", sa.String(length=24), nullable=False),
        sa.Column("recibida_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("official_id", sa.String(length=36), nullable=False),
        sa.Column("receptor_etiqueta", sa.String(length=400), nullable=False),
        sa.Column("condicion_sobre", sa.String(length=500), nullable=True),
        sa.Column("confidencial", sa.Boolean(), nullable=False),
        sa.Column("fundamento_confidencialidad", sa.String(length=300), nullable=False),
        sa.Column("modalidad_al_recibir", sa.String(length=24), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("numero >= 1", name="ck_gov_procurement_offers_numero"),
        sa.CheckConstraint(
            "tipo_sobre IN ('UNICO', 'CALIFICACION', 'OFERTA')",
            name="ck_gov_procurement_offers_tipo_sobre",
        ),
        sa.CheckConstraint(
            "canal IN ('ACTO_PUBLICO', 'UNIDAD_CONTRATANTE', 'MEDIO_ELECTRONICO')",
            name="ck_gov_procurement_offers_canal",
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], name="fk_gov_procurement_offers_company_id"),
        sa.ForeignKeyConstraint(["file_id"], ["gov_procurement_files.id"], name="fk_gov_procurement_offers_file_id"),
        sa.ForeignKeyConstraint(["official_id"], ["gov_officials.id"], name="fk_gov_procurement_offers_official_id"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "file_id", "numero", name="uq_gov_procurement_offers_file_numero"),
        sa.UniqueConstraint(
            "company_id",
            "file_id",
            "oferente_documento",
            "tipo_sobre",
            name="uq_gov_procurement_offers_oferente_sobre",
        ),
    )
    op.create_index("ix_gov_procurement_offers_company_id", "gov_procurement_offers", ["company_id"])
    op.create_index("ix_gov_procurement_offers_file_id", "gov_procurement_offers", ["file_id"])
    op.create_index("ix_gov_procurement_offers_official_id", "gov_procurement_offers", ["official_id"])

    op.create_table(
        "gov_procurement_offer_documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("offer_id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("document_version_id", sa.String(length=36), nullable=False),
        sa.Column("version_numero", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], name="fk_gov_procurement_offer_documents_company_id"),
        sa.ForeignKeyConstraint(["offer_id"], ["gov_procurement_offers.id"], name="fk_gov_procurement_offer_documents_offer_id"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], name="fk_gov_procurement_offer_documents_document_id"),
        sa.ForeignKeyConstraint(
            ["document_version_id"],
            ["document_versions.id"],
            name="fk_gov_procurement_offer_documents_document_version_id",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", name="uq_gov_procurement_offer_documents_document"),
    )
    op.create_index("ix_gov_procurement_offer_documents_company_id", "gov_procurement_offer_documents", ["company_id"])
    op.create_index("ix_gov_procurement_offer_documents_offer_id", "gov_procurement_offer_documents", ["offer_id"])
    op.create_index("ix_gov_procurement_offer_documents_document_id", "gov_procurement_offer_documents", ["document_id"])
    op.create_index(
        "ix_gov_procurement_offer_documents_document_version_id",
        "gov_procurement_offer_documents",
        ["document_version_id"],
    )

    op.add_column("gov_procurement_files", sa.Column("recepcion_concluida_en", sa.DateTime(timezone=True), nullable=True))
    op.add_column("gov_procurement_files", sa.Column("recepcion_concluida_por", sa.String(length=36), nullable=True))

    op.execute("""
        ALTER TABLE gov_procurement_file_events
        DROP CONSTRAINT IF EXISTS ck_gov_procurement_file_events_ck_gov_procurement_file__de56
    """)
    op.execute("""
        ALTER TABLE gov_procurement_file_events
        ADD CONSTRAINT ck_gov_procurement_file_events_ck_gov_procurement_file__de56
        CHECK (
            clase IN (
                'APERTURA', 'DATOS', 'RESPONSABLE', 'COMISION', 'ACTUACION', 'DECISION',
                'DOCUMENTO', 'ACTO', 'HITO', 'CIERRE', 'DESCARTE', 'OFERTA'
            )
        )
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION kontrol_gov_offer_immutable()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'Las ofertas son inmutables';
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_gov_offer_immutable_update
        BEFORE UPDATE ON gov_procurement_offers
        FOR EACH ROW EXECUTE FUNCTION kontrol_gov_offer_immutable();
    """)
    op.execute("""
        CREATE TRIGGER trg_gov_offer_immutable_delete
        BEFORE DELETE ON gov_procurement_offers
        FOR EACH ROW EXECUTE FUNCTION kontrol_gov_offer_immutable();
    """)
    op.execute("""
        CREATE TRIGGER trg_gov_offer_immutable_truncate
        BEFORE TRUNCATE ON gov_procurement_offers
        FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_offer_immutable();
    """)
    op.execute("""
        CREATE TRIGGER trg_gov_offer_document_immutable_update
        BEFORE UPDATE ON gov_procurement_offer_documents
        FOR EACH ROW EXECUTE FUNCTION kontrol_gov_offer_immutable();
    """)
    op.execute("""
        CREATE TRIGGER trg_gov_offer_document_immutable_delete
        BEFORE DELETE ON gov_procurement_offer_documents
        FOR EACH ROW EXECUTE FUNCTION kontrol_gov_offer_immutable();
    """)
    op.execute("""
        CREATE TRIGGER trg_gov_offer_document_immutable_truncate
        BEFORE TRUNCATE ON gov_procurement_offer_documents
        FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_offer_immutable();
    """)

    op.execute("""
        INSERT INTO permissions (id, resource, action, scope_type, created_at, updated_at)
        VALUES (
            gen_random_uuid()::varchar,
            'gobierno_ofertas',
            'view',
            'COMPANY',
            now(),
            now()
        )
    """)
    op.execute("""
        INSERT INTO permissions (id, resource, action, scope_type, created_at, updated_at)
        VALUES (
            gen_random_uuid()::varchar,
            'gobierno_ofertas',
            'receive',
            'COMPANY',
            now(),
            now()
        )
    """)
    op.execute("""
        INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
        SELECT
            gen_random_uuid()::varchar,
            r.id,
            p.id,
            now(),
            now()
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.code = 'FUNCIONAL_COMPLETO'
          AND r.company_id IS NULL
          AND p.resource = 'gobierno_ofertas'
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM role_permissions rp
        USING permissions p
        WHERE rp.permission_id = p.id
          AND p.resource = 'gobierno_ofertas'
          AND rp.role_id IN (
              SELECT id FROM roles WHERE code = 'FUNCIONAL_COMPLETO' AND company_id IS NULL
          )
    """)
    op.execute("""
        DELETE FROM permissions WHERE resource = 'gobierno_ofertas'
    """)

    op.execute("DROP TRIGGER IF EXISTS trg_gov_offer_immutable_update ON gov_procurement_offers")
    op.execute("DROP TRIGGER IF EXISTS trg_gov_offer_immutable_delete ON gov_procurement_offers")
    op.execute("DROP TRIGGER IF EXISTS trg_gov_offer_immutable_truncate ON gov_procurement_offers")
    op.execute("DROP TRIGGER IF EXISTS trg_gov_offer_document_immutable_update ON gov_procurement_offer_documents")
    op.execute("DROP TRIGGER IF EXISTS trg_gov_offer_document_immutable_delete ON gov_procurement_offer_documents")
    op.execute("DROP TRIGGER IF EXISTS trg_gov_offer_document_immutable_truncate ON gov_procurement_offer_documents")
    op.execute("DROP FUNCTION IF EXISTS kontrol_gov_offer_immutable()")

    op.execute("""
        ALTER TABLE gov_procurement_file_events
        DROP CONSTRAINT IF EXISTS ck_gov_procurement_file_events_ck_gov_procurement_file__de56
    """)
    op.execute("""
        ALTER TABLE gov_procurement_file_events
        ADD CONSTRAINT ck_gov_procurement_file_events_ck_gov_procurement_file__de56
        CHECK (
            clase IN (
                'APERTURA', 'DATOS', 'RESPONSABLE', 'COMISION', 'ACTUACION', 'DECISION',
                'DOCUMENTO', 'ACTO', 'HITO', 'CIERRE', 'DESCARTE'
            )
        )
    """)

    op.drop_column("gov_procurement_files", "recepcion_concluida_por")
    op.drop_column("gov_procurement_files", "recepcion_concluida_en")

    op.drop_index("ix_gov_procurement_offer_documents_document_version_id", table_name="gov_procurement_offer_documents")
    op.drop_index("ix_gov_procurement_offer_documents_document_id", table_name="gov_procurement_offer_documents")
    op.drop_index("ix_gov_procurement_offer_documents_offer_id", table_name="gov_procurement_offer_documents")
    op.drop_index("ix_gov_procurement_offer_documents_company_id", table_name="gov_procurement_offer_documents")
    op.drop_table("gov_procurement_offer_documents")

    op.drop_index("ix_gov_procurement_offers_official_id", table_name="gov_procurement_offers")
    op.drop_index("ix_gov_procurement_offers_file_id", table_name="gov_procurement_offers")
    op.drop_index("ix_gov_procurement_offers_company_id", table_name="gov_procurement_offers")
    op.drop_table("gov_procurement_offers")

    op.drop_index("uq_document_seals_document_active", table_name="document_seals")
    op.drop_index("ix_document_seals_document_id", table_name="document_seals")
    op.drop_index("ix_document_seals_company_id", table_name="document_seals")
    op.drop_table("document_seals")
