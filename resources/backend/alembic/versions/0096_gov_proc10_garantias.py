"""gov_proc10_garantias

Revision ID: 0096_gov_proc10_garantias
Revises: 0095_fusion_gov_planning
Create Date: 2025-01-18 00:00:00.000000
"""
import sqlalchemy as sa

from alembic import op

revision = "0096_gov_proc10_garantias"
down_revision = "0095_fusion_gov_planning"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "gov_guarantee_issuers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("tipo", sa.String(length=32), nullable=False),
        sa.Column("nombre", sa.String(length=200), nullable=False),
        sa.Column("rif", sa.String(length=20), nullable=False),
        sa.Column("bank_id", sa.String(length=36), nullable=True),
        sa.Column("estado", sa.String(length=10), nullable=False, server_default="ACTIVO"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("tipo IN ('BANCO', 'ASEGURADORA', 'SOCIEDAD_GARANTIAS_RECIPROCAS', 'OTRO')", name="ck_gov_guarantee_issuers_tipo"),
        sa.CheckConstraint("estado IN ('ACTIVO', 'INACTIVO')", name="ck_gov_guarantee_issuers_estado"),
        sa.CheckConstraint("(tipo = 'BANCO') = (bank_id IS NOT NULL)", name="ck_gov_guarantee_issuers_banco"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], name="fk_gov_guarantee_issuers_company_id"),
        sa.ForeignKeyConstraint(["bank_id"], ["gov_banks.id"], name="fk_gov_guarantee_issuers_bank_id"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "rif", name="uq_gov_guarantee_issuers_company_rif"),
    )
    op.create_index("ix_gov_guarantee_issuers_company_id", "gov_guarantee_issuers", ["company_id"])
    op.create_index("ix_gov_guarantee_issuers_bank_id", "gov_guarantee_issuers", ["bank_id"])

    op.create_table(
        "gov_guarantee_requirements",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("file_id", sa.String(length=36), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("regla_codigo", sa.String(length=40), nullable=False),
        sa.Column("regla", sa.JSON(), nullable=False),
        sa.Column("tipo", sa.String(length=32), nullable=False),
        sa.Column("etapa", sa.String(length=24), nullable=False),
        sa.Column("nombre", sa.String(length=200), nullable=True),
        sa.Column("forma", sa.String(length=16), nullable=False),
        sa.Column("porcentaje", sa.Numeric(5, 2), nullable=True),
        sa.Column("monto_fijo", sa.Numeric(18, 2), nullable=True),
        sa.Column("moneda", sa.String(length=3), nullable=True),
        sa.Column("vigencia_minima_hasta", sa.Date(), nullable=True),
        sa.Column("fundamento", sa.String(length=1000), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("document_version_id", sa.String(length=36), nullable=False),
        sa.Column("version_numero", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("registrado_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("registrado_por", sa.String(length=36), nullable=False),
        sa.Column("official_id", sa.String(length=36), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("tipo IN ('MANTENIMIENTO_OFERTA', 'ANTICIPO', 'FIEL_CUMPLIMIENTO', 'LABORAL', 'RESPONSABILIDAD_CIVIL', 'OTRA')", name="ck_gov_guarantee_requirements_tipo"),
        sa.CheckConstraint("etapa IN ('PROCEDIMIENTO', 'FORMALIZACION', 'EJECUCION_CONTRACTUAL')", name="ck_gov_guarantee_requirements_etapa"),
        sa.CheckConstraint("forma IN ('PORCENTAJE', 'MONTO_FIJO')", name="ck_gov_guarantee_requirements_forma"),
        sa.CheckConstraint("numero >= 1", name="ck_gov_guarantee_requirements_numero"),
        sa.CheckConstraint("(forma = 'PORCENTAJE') = (porcentaje IS NOT NULL)", name="ck_gov_guarantee_requirements_porcentaje_presencia"),
        sa.CheckConstraint("(forma = 'MONTO_FIJO') = (monto_fijo IS NOT NULL)", name="ck_gov_guarantee_requirements_monto_presencia"),
        sa.CheckConstraint("(forma = 'MONTO_FIJO') = (moneda IS NOT NULL)", name="ck_gov_guarantee_requirements_moneda_presencia"),
        sa.CheckConstraint("porcentaje IS NULL OR (porcentaje > 0 AND porcentaje <= 100)", name="ck_gov_guarantee_requirements_porcentaje_valor"),
        sa.CheckConstraint("monto_fijo IS NULL OR monto_fijo > 0", name="ck_gov_guarantee_requirements_monto_valor"),
        sa.CheckConstraint("moneda IS NULL OR moneda IN ('VES', 'USD', 'EUR')", name="ck_gov_guarantee_requirements_moneda_valor"),
        sa.CheckConstraint("tipo <> 'OTRA' OR nombre IS NOT NULL", name="ck_gov_guarantee_requirements_otra_nombre"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], name="fk_gov_guarantee_requirements_company_id"),
        sa.ForeignKeyConstraint(["file_id"], ["gov_procurement_files.id"], name="fk_gov_guarantee_requirements_file_id"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], name="fk_gov_guarantee_requirements_document_id"),
        sa.ForeignKeyConstraint(["document_version_id"], ["document_versions.id"], name="fk_gov_guarantee_requirements_document_version_id"),
        sa.ForeignKeyConstraint(["official_id"], ["gov_officials.id"], name="fk_gov_guarantee_requirements_official_id"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "file_id", "numero", name="uq_gov_guarantee_requirements_company_file_numero"),
    )
    op.create_index("ix_gov_guarantee_requirements_company_id", "gov_guarantee_requirements", ["company_id"])
    op.create_index("ix_gov_guarantee_requirements_file_id", "gov_guarantee_requirements", ["file_id"])
    op.create_index("ix_gov_guarantee_requirements_document_id", "gov_guarantee_requirements", ["document_id"])
    op.create_index("ix_gov_guarantee_requirements_document_version_id", "gov_guarantee_requirements", ["document_version_id"])
    op.create_index("ix_gov_guarantee_requirements_official_id", "gov_guarantee_requirements", ["official_id"])

    op.create_table(
        "gov_guarantee_instruments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("file_id", sa.String(length=36), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("requirement_id", sa.String(length=36), nullable=False),
        sa.Column("tipo", sa.String(length=32), nullable=False),
        sa.Column("etapa", sa.String(length=24), nullable=False),
        sa.Column("offer_id", sa.String(length=36), nullable=False),
        sa.Column("decision_id", sa.String(length=36), nullable=True),
        sa.Column("issuer_id", sa.String(length=36), nullable=False),
        sa.Column("referencia_emisor", sa.String(length=60), nullable=False),
        sa.Column("monto", sa.Numeric(18, 2), nullable=False),
        sa.Column("moneda", sa.String(length=3), nullable=False),
        sa.Column("fecha_emision", sa.Date(), nullable=False),
        sa.Column("vigente_desde", sa.Date(), nullable=False),
        sa.Column("vigente_hasta", sa.Date(), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("document_version_id", sa.String(length=36), nullable=False),
        sa.Column("version_numero", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("observacion", sa.String(length=1000), nullable=True),
        sa.Column("origen", sa.String(length=16), nullable=False, server_default="REGISTRO"),
        sa.Column("antecesor_id", sa.String(length=36), nullable=True),
        sa.Column("estado", sa.String(length=16), nullable=False, server_default="REGISTRADA"),
        sa.Column("afectada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("registrada_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("registrada_por", sa.String(length=36), nullable=False),
        sa.Column("official_id", sa.String(length=36), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("tipo IN ('MANTENIMIENTO_OFERTA', 'ANTICIPO', 'FIEL_CUMPLIMIENTO', 'LABORAL', 'RESPONSABILIDAD_CIVIL', 'OTRA')", name="ck_gov_guarantee_instruments_tipo"),
        sa.CheckConstraint("etapa IN ('PROCEDIMIENTO', 'FORMALIZACION', 'EJECUCION_CONTRACTUAL')", name="ck_gov_guarantee_instruments_etapa"),
        sa.CheckConstraint("origen IN ('REGISTRO', 'RENOVACION', 'SUSTITUCION')", name="ck_gov_guarantee_instruments_origen"),
        sa.CheckConstraint("estado IN ('REGISTRADA', 'RENOVADA', 'SUSTITUIDA', 'LIBERADA', 'EJECUTADA')", name="ck_gov_guarantee_instruments_estado"),
        sa.CheckConstraint("numero >= 1", name="ck_gov_guarantee_instruments_numero"),
        sa.CheckConstraint("monto > 0", name="ck_gov_guarantee_instruments_monto"),
        sa.CheckConstraint("moneda IN ('VES', 'USD', 'EUR')", name="ck_gov_guarantee_instruments_moneda"),
        sa.CheckConstraint("vigente_desde <= vigente_hasta", name="ck_gov_guarantee_instruments_vigencia"),
        sa.CheckConstraint("fecha_emision <= vigente_hasta", name="ck_gov_guarantee_instruments_emision"),
        sa.CheckConstraint("(origen = 'REGISTRO') = (antecesor_id IS NULL)", name="ck_gov_guarantee_instruments_antecesor"),
        sa.CheckConstraint("(estado = 'REGISTRADA') = (afectada_en IS NULL)", name="ck_gov_guarantee_instruments_afectada"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], name="fk_gov_guarantee_instruments_company_id"),
        sa.ForeignKeyConstraint(["file_id"], ["gov_procurement_files.id"], name="fk_gov_guarantee_instruments_file_id"),
        sa.ForeignKeyConstraint(["requirement_id"], ["gov_guarantee_requirements.id"], name="fk_gov_guarantee_instruments_requirement_id"),
        sa.ForeignKeyConstraint(["offer_id"], ["gov_procurement_offers.id"], name="fk_gov_guarantee_instruments_offer_id"),
        sa.ForeignKeyConstraint(["decision_id"], ["gov_procurement_decisions.id"], name="fk_gov_guarantee_instruments_decision_id"),
        sa.ForeignKeyConstraint(["issuer_id"], ["gov_guarantee_issuers.id"], name="fk_gov_guarantee_instruments_issuer_id"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], name="fk_gov_guarantee_instruments_document_id"),
        sa.ForeignKeyConstraint(["document_version_id"], ["document_versions.id"], name="fk_gov_guarantee_instruments_document_version_id"),
        sa.ForeignKeyConstraint(["antecesor_id"], ["gov_guarantee_instruments.id"], name="fk_gov_guarantee_instruments_antecesor_id"),
        sa.ForeignKeyConstraint(["official_id"], ["gov_officials.id"], name="fk_gov_guarantee_instruments_official_id"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "file_id", "numero", name="uq_gov_guarantee_instruments_company_file_numero"),
        sa.UniqueConstraint("antecesor_id", name="uq_gov_guarantee_instruments_antecesor_id"),
    )
    op.create_index("ix_gov_guarantee_instruments_company_id", "gov_guarantee_instruments", ["company_id"])
    op.create_index("ix_gov_guarantee_instruments_file_id", "gov_guarantee_instruments", ["file_id"])
    op.create_index("ix_gov_guarantee_instruments_requirement_id", "gov_guarantee_instruments", ["requirement_id"])
    op.create_index("ix_gov_guarantee_instruments_offer_id", "gov_guarantee_instruments", ["offer_id"])
    op.create_index("ix_gov_guarantee_instruments_decision_id", "gov_guarantee_instruments", ["decision_id"])
    op.create_index("ix_gov_guarantee_instruments_issuer_id", "gov_guarantee_instruments", ["issuer_id"])
    op.create_index("ix_gov_guarantee_instruments_document_id", "gov_guarantee_instruments", ["document_id"])
    op.create_index("ix_gov_guarantee_instruments_document_version_id", "gov_guarantee_instruments", ["document_version_id"])
    op.create_index("ix_gov_guarantee_instruments_official_id", "gov_guarantee_instruments", ["official_id"])
    op.create_index(
        "uq_gov_guarantee_instruments_emisor_referencia",
        "gov_guarantee_instruments",
        ["company_id", "issuer_id", "referencia_emisor"],
        unique=True,
        postgresql_where=sa.text("estado = 'REGISTRADA'"),
        sqlite_where=sa.text("estado = 'REGISTRADA'"),
    )

    op.create_table(
        "gov_guarantee_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("file_id", sa.String(length=36), nullable=False),
        sa.Column("instrument_id", sa.String(length=36), nullable=False),
        sa.Column("accion", sa.String(length=16), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("motivo", sa.String(length=2000), nullable=True),
        sa.Column("act_id", sa.String(length=36), nullable=True),
        sa.Column("cargo_id", sa.String(length=36), nullable=True),
        sa.Column("document_id", sa.String(length=36), nullable=True),
        sa.Column("document_version_id", sa.String(length=36), nullable=True),
        sa.Column("version_numero", sa.BigInteger(), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("nuevo_instrument_id", sa.String(length=36), nullable=True),
        sa.Column("monto", sa.Numeric(18, 2), nullable=True),
        sa.Column("moneda", sa.String(length=3), nullable=True),
        sa.Column("precondicion", sa.String(length=24), nullable=True),
        sa.Column("precondicion_detalle", sa.String(length=300), nullable=True),
        sa.Column("registrada_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("registrada_por", sa.String(length=36), nullable=False),
        sa.Column("official_id", sa.String(length=36), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("accion IN ('REGISTRO', 'RENOVACION', 'SUSTITUCION', 'LIBERACION', 'EJECUCION')", name="ck_gov_guarantee_events_accion"),
        sa.CheckConstraint("(accion IN ('LIBERACION', 'EJECUCION')) = (act_id IS NOT NULL)", name="ck_gov_guarantee_events_acto"),
        sa.CheckConstraint("accion = 'REGISTRO' OR motivo IS NOT NULL", name="ck_gov_guarantee_events_motivo"),
        sa.CheckConstraint("(accion IN ('RENOVACION', 'SUSTITUCION')) = (nuevo_instrument_id IS NOT NULL)", name="ck_gov_guarantee_events_nuevo"),
        sa.CheckConstraint("(accion = 'EJECUCION') = (monto IS NOT NULL)", name="ck_gov_guarantee_events_monto_presencia"),
        sa.CheckConstraint("(monto IS NULL) = (moneda IS NULL)", name="ck_gov_guarantee_events_moneda_presencia"),
        sa.CheckConstraint("monto IS NULL OR monto > 0", name="ck_gov_guarantee_events_monto_valor"),
        sa.CheckConstraint("(accion = 'LIBERACION') = (precondicion IS NOT NULL)", name="ck_gov_guarantee_events_precondicion_presencia"),
        sa.CheckConstraint("precondicion IS NULL OR precondicion IN ('VERIFICADA', 'SOPORTADA_POR_ACTO')", name="ck_gov_guarantee_events_precondicion_valor"),
        sa.CheckConstraint("(document_id IS NULL) = (document_version_id IS NULL)", name="ck_gov_guarantee_events_documento"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], name="fk_gov_guarantee_events_company_id"),
        sa.ForeignKeyConstraint(["file_id"], ["gov_procurement_files.id"], name="fk_gov_guarantee_events_file_id"),
        sa.ForeignKeyConstraint(["instrument_id"], ["gov_guarantee_instruments.id"], name="fk_gov_guarantee_events_instrument_id"),
        sa.ForeignKeyConstraint(["act_id"], ["gov_acts.id"], name="fk_gov_guarantee_events_act_id"),
        sa.ForeignKeyConstraint(["cargo_id"], ["gov_positions.id"], name="fk_gov_guarantee_events_cargo_id"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], name="fk_gov_guarantee_events_document_id"),
        sa.ForeignKeyConstraint(["document_version_id"], ["document_versions.id"], name="fk_gov_guarantee_events_document_version_id"),
        sa.ForeignKeyConstraint(["nuevo_instrument_id"], ["gov_guarantee_instruments.id"], name="fk_gov_guarantee_events_nuevo_instrument_id"),
        sa.ForeignKeyConstraint(["official_id"], ["gov_officials.id"], name="fk_gov_guarantee_events_official_id"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_gov_guarantee_events_company_id", "gov_guarantee_events", ["company_id"])
    op.create_index("ix_gov_guarantee_events_file_id", "gov_guarantee_events", ["file_id"])
    op.create_index("ix_gov_guarantee_events_instrument_id", "gov_guarantee_events", ["instrument_id"])
    op.create_index("ix_gov_guarantee_events_act_id", "gov_guarantee_events", ["act_id"])
    op.create_index("ix_gov_guarantee_events_cargo_id", "gov_guarantee_events", ["cargo_id"])
    op.create_index("ix_gov_guarantee_events_document_id", "gov_guarantee_events", ["document_id"])
    op.create_index("ix_gov_guarantee_events_nuevo_instrument_id", "gov_guarantee_events", ["nuevo_instrument_id"])
    op.create_index("ix_gov_guarantee_events_official_id", "gov_guarantee_events", ["official_id"])
    op.create_index(
        "uq_gov_guarantee_events_registro",
        "gov_guarantee_events",
        ["instrument_id"],
        unique=True,
        postgresql_where=sa.text("accion = 'REGISTRO'"),
        sqlite_where=sa.text("accion = 'REGISTRO'"),
    )
    op.create_index(
        "uq_gov_guarantee_events_final",
        "gov_guarantee_events",
        ["instrument_id"],
        unique=True,
        postgresql_where=sa.text("accion <> 'REGISTRO'"),
        sqlite_where=sa.text("accion <> 'REGISTRO'"),
    )

    op.execute("""
        CREATE OR REPLACE FUNCTION kontrol_gov_guarantee_immutable()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'Los requisitos y actuaciones de garantías son inmutables';
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION kontrol_gov_guarantee_instrument_guard()
        RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'DELETE' OR TG_OP = 'TRUNCATE' THEN
                RAISE EXCEPTION 'Las garantías no se borran';
            END IF;
            IF TG_OP = 'UPDATE' THEN
                IF OLD.estado = 'REGISTRADA'
                   AND NEW.estado IN ('RENOVADA', 'SUSTITUIDA', 'LIBERADA', 'EJECUTADA')
                   AND NEW.afectada_en IS NOT NULL
                   AND (to_jsonb(NEW) - 'estado' - 'afectada_en' - 'updated_at') = (to_jsonb(OLD) - 'estado' - 'afectada_en' - 'updated_at') THEN
                    RETURN NEW;
                END IF;
                RAISE EXCEPTION 'La garantía registrada solo cambia una vez a su estado final';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION kontrol_gov_guarantee_issuer_no_delete()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'Los emisores de garantías no se borran';
        END;
        $$ LANGUAGE plpgsql;
    """)

    for _accion, _momento in (
        ("update", "BEFORE UPDATE"),
        ("delete", "BEFORE DELETE"),
        ("truncate", "BEFORE TRUNCATE"),
    ):
        op.execute(f"""
            CREATE TRIGGER trg_guarantee_requirements_immutable_{_accion}
            {_momento} ON gov_guarantee_requirements
            FOR EACH {"ROW" if _accion != "truncate" else "STATEMENT"} EXECUTE FUNCTION kontrol_gov_guarantee_immutable();
        """)
        op.execute(f"""
            CREATE TRIGGER trg_guarantee_events_immutable_{_accion}
            {_momento} ON gov_guarantee_events
            FOR EACH {"ROW" if _accion != "truncate" else "STATEMENT"} EXECUTE FUNCTION kontrol_gov_guarantee_immutable();
        """)
    for _accion, _momento in (
        ("update", "BEFORE UPDATE"),
        ("delete", "BEFORE DELETE"),
        ("truncate", "BEFORE TRUNCATE"),
    ):
        op.execute(f"""
            CREATE TRIGGER trg_gov_guarantee_instruments_guard_{_accion}
            {_momento} ON gov_guarantee_instruments
            FOR EACH {"ROW" if _accion != "truncate" else "STATEMENT"} EXECUTE FUNCTION kontrol_gov_guarantee_instrument_guard();
        """)
    for _accion, _momento in (
        ("delete", "BEFORE DELETE"),
        ("truncate", "BEFORE TRUNCATE"),
    ):
        op.execute(f"""
            CREATE TRIGGER trg_gov_guarantee_issuers_no_{_accion}
            {_momento} ON gov_guarantee_issuers
            FOR EACH {"ROW" if _accion != "truncate" else "STATEMENT"} EXECUTE FUNCTION kontrol_gov_guarantee_issuer_no_delete();
        """)

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
                'DOCUMENTO', 'ACTO', 'HITO', 'CIERRE', 'DESCARTE', 'OFERTA',
                'APERTURA_OFERTA', 'EVALUACION', 'RECOMENDACION', 'RECHAZO_OFERTA',
                'ADJUDICACION', 'DESIERTA', 'TERMINACION', 'NULIDAD', 'GARANTIA'
            )
        )
    """)

    for _action in ("view", "manage", "release", "execute"):
        op.execute(f"""
            INSERT INTO permissions (id, resource, action, scope_type, created_at, updated_at)
            VALUES (
                gen_random_uuid()::varchar,
                'gobierno_garantias',
                '{_action}',
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
          AND p.resource = 'gobierno_garantias'
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM role_permissions
        WHERE permission_id IN (
            SELECT id FROM permissions WHERE resource = 'gobierno_garantias'
        )
    """)
    op.execute("""
        DELETE FROM permissions WHERE resource = 'gobierno_garantias'
    """)

    for _accion in ("delete", "truncate"):
        op.execute(f"DROP TRIGGER IF EXISTS trg_gov_guarantee_issuers_no_{_accion} ON gov_guarantee_issuers")
    for _accion in ("update", "delete", "truncate"):
        op.execute(f"DROP TRIGGER IF EXISTS trg_gov_guarantee_instruments_guard_{_accion} ON gov_guarantee_instruments")
    for _accion in ("update", "delete", "truncate"):
        op.execute(f"DROP TRIGGER IF EXISTS trg_guarantee_requirements_immutable_{_accion} ON gov_guarantee_requirements")
        op.execute(f"DROP TRIGGER IF EXISTS trg_guarantee_events_immutable_{_accion} ON gov_guarantee_events")
    op.execute("DROP FUNCTION IF EXISTS kontrol_gov_guarantee_issuer_no_delete()")
    op.execute("DROP FUNCTION IF EXISTS kontrol_gov_guarantee_instrument_guard()")
    op.execute("DROP FUNCTION IF EXISTS kontrol_gov_guarantee_immutable()")

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
                'DOCUMENTO', 'ACTO', 'HITO', 'CIERRE', 'DESCARTE', 'OFERTA',
                'APERTURA_OFERTA', 'EVALUACION', 'RECOMENDACION', 'RECHAZO_OFERTA',
                'ADJUDICACION', 'DESIERTA', 'TERMINACION', 'NULIDAD'
            )
        )
    """)

    op.drop_table("gov_guarantee_events")
    op.drop_table("gov_guarantee_instruments")
    op.drop_table("gov_guarantee_requirements")
    op.drop_table("gov_guarantee_issuers")
