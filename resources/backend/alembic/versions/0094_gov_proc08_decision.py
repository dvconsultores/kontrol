"""gov_proc08_decision

Revision ID: 0094_gov_proc08_decision
Revises: 0093_fusion_gov_storage
Create Date: 2025-01-17 00:00:00.000000
"""
import sqlalchemy as sa

from alembic import op

revision = "0094_gov_proc08_decision"
down_revision = "0093_fusion_gov_storage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "gov_procurement_recommendations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("file_id", sa.String(length=36), nullable=False),
        sa.Column("committee_id", sa.String(length=36), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("estado", sa.String(length=16), nullable=False, server_default="EMITIDA"),
        sa.Column("resultado_recomendado", sa.String(length=24), nullable=False),
        sa.Column("causal_desierta", sa.String(length=16), nullable=True),
        sa.Column("motivacion", sa.Text(), nullable=False),
        sa.Column("examen_legal", sa.Text(), nullable=False),
        sa.Column("examen_financiero", sa.Text(), nullable=False),
        sa.Column("examen_tecnico", sa.Text(), nullable=False),
        sa.Column("resultado_matriz", sa.Text(), nullable=False),
        sa.Column("medidas_promocion", sa.Text(), nullable=True),
        sa.Column("matrix_id", sa.String(length=36), nullable=False),
        sa.Column("matrix_version", sa.Integer(), nullable=False),
        sa.Column("evaluacion_concluida_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("informe_storage_key", sa.String(length=255), nullable=False),
        sa.Column("informe_sha256", sa.String(length=64), nullable=False),
        sa.Column("informe_tamano", sa.BigInteger(), nullable=False),
        sa.Column("informe_nombre", sa.String(length=200), nullable=False),
        sa.Column("emitida_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("emitida_por", sa.String(length=36), nullable=False),
        sa.Column("official_id", sa.String(length=36), nullable=True),
        sa.Column("sustituye_id", sa.String(length=36), nullable=True),
        sa.Column("motivo_sustitucion", sa.String(length=2000), nullable=True),
        sa.Column("sustituida_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("estado IN ('EMITIDA', 'SUSTITUIDA')", name="ck_gov_procurement_recommendations_estado"),
        sa.CheckConstraint("resultado_recomendado IN ('ADJUDICAR', 'DECLARAR_DESIERTA', 'TERMINAR')", name="ck_gov_procurement_recommendations_resultado_recomendado"),
        sa.CheckConstraint("numero >= 1", name="ck_gov_procurement_recommendations_numero"),
        sa.CheckConstraint("(causal_desierta IS NOT NULL) = (resultado_recomendado = 'DECLARAR_DESIERTA')", name="ck_gov_procurement_recommendations_causal_desierta_presencia"),
        sa.CheckConstraint("causal_desierta IS NULL OR causal_desierta IN ('LCP113_1', 'LCP113_2', 'LCP113_3', 'LCP113_4', 'LCP113_5')", name="ck_gov_procurement_recommendations_causal_desierta_valor"),
        sa.CheckConstraint("(sustituye_id IS NULL) = (motivo_sustitucion IS NULL)", name="ck_gov_procurement_recommendations_sustitucion"),
        sa.CheckConstraint("(estado = 'SUSTITUIDA') = (sustituida_en IS NOT NULL)", name="ck_gov_procurement_recommendations_sustituida_en"),
        sa.CheckConstraint("matrix_version >= 1", name="ck_gov_procurement_recommendations_matrix_version"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], name="fk_gov_procurement_recommendations_company_id"),
        sa.ForeignKeyConstraint(["file_id"], ["gov_procurement_files.id"], name="fk_gov_procurement_recommendations_file_id"),
        sa.ForeignKeyConstraint(["committee_id"], ["gov_procurement_committees.id"], name="fk_gov_procurement_recommendations_committee_id"),
        sa.ForeignKeyConstraint(["matrix_id"], ["gov_procurement_eval_matrices.id"], name="fk_gov_procurement_recommendations_matrix_id"),
        sa.ForeignKeyConstraint(["official_id"], ["gov_officials.id"], name="fk_gov_procurement_recommendations_official_id"),
        sa.ForeignKeyConstraint(["sustituye_id"], ["gov_procurement_recommendations.id"], name="fk_gov_procurement_recommendations_sustituye_id"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "file_id", "numero", name="uq_gov_procurement_recommendations_company_file_numero"),
        sa.UniqueConstraint("sustituye_id", name="uq_gov_procurement_recommendations_sustituye_id"),
    )
    op.create_index(
        "uq_gov_procurement_recommendations_vigente",
        "gov_procurement_recommendations",
        ["file_id"],
        unique=True,
        postgresql_where=sa.text("estado = 'EMITIDA'"),
        sqlite_where=sa.text("estado = 'EMITIDA'"),
    )
    op.create_index("ix_gov_procurement_recommendations_company_id", "gov_procurement_recommendations", ["company_id"])
    op.create_index("ix_gov_procurement_recommendations_file_id", "gov_procurement_recommendations", ["file_id"])
    op.create_index("ix_gov_procurement_recommendations_committee_id", "gov_procurement_recommendations", ["committee_id"])
    op.create_index("ix_gov_procurement_recommendations_matrix_id", "gov_procurement_recommendations", ["matrix_id"])
    op.create_index("ix_gov_procurement_recommendations_official_id", "gov_procurement_recommendations", ["official_id"])

    op.create_table(
        "gov_procurement_recommendation_signatories",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("recommendation_id", sa.String(length=36), nullable=False),
        sa.Column("member_id", sa.String(length=36), nullable=False),
        sa.Column("official_id", sa.String(length=36), nullable=False),
        sa.Column("funcion", sa.String(length=16), nullable=False),
        sa.Column("condicion", sa.String(length=16), nullable=False),
        sa.Column("cuenta_voto", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], name="fk_gov_procurement_recommendation_signatories_company_id"),
        sa.ForeignKeyConstraint(["recommendation_id"], ["gov_procurement_recommendations.id"], name="fk_gov_procurement_recommendation_signatories_recommendation_id"),
        sa.ForeignKeyConstraint(["member_id"], ["gov_procurement_committee_members.id"], name="fk_gov_procurement_recommendation_signatories_member_id"),
        sa.ForeignKeyConstraint(["official_id"], ["gov_officials.id"], name="fk_gov_procurement_recommendation_signatories_official_id"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("recommendation_id", "member_id", name="uq_gov_proc_rec_signatories_member"),
    )
    op.create_index("ix_gov_procurement_recommendation_signatories_company_id", "gov_procurement_recommendation_signatories", ["company_id"])
    op.create_index("ix_gov_procurement_recommendation_signatories_recommendation_id", "gov_procurement_recommendation_signatories", ["recommendation_id"])
    op.create_index("ix_gov_procurement_recommendation_signatories_member_id", "gov_procurement_recommendation_signatories", ["member_id"])
    op.create_index("ix_gov_procurement_recommendation_signatories_official_id", "gov_procurement_recommendation_signatories", ["official_id"])

    op.create_table(
        "gov_procurement_recommendation_options",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("recommendation_id", sa.String(length=36), nullable=False),
        sa.Column("offer_id", sa.String(length=36), nullable=False),
        sa.Column("posicion", sa.SmallInteger(), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("posicion BETWEEN 1 AND 3", name="ck_gov_procurement_recommendation_options_posicion"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], name="fk_gov_procurement_recommendation_options_company_id"),
        sa.ForeignKeyConstraint(["recommendation_id"], ["gov_procurement_recommendations.id"], name="fk_gov_procurement_recommendation_options_recommendation_id"),
        sa.ForeignKeyConstraint(["offer_id"], ["gov_procurement_offers.id"], name="fk_gov_procurement_recommendation_options_offer_id"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("recommendation_id", "posicion", name="uq_gov_proc_rec_options_posicion"),
        sa.UniqueConstraint("recommendation_id", "offer_id", name="uq_gov_procurement_recommendation_options_recommendation_offer"),
    )
    op.create_index("ix_gov_procurement_recommendation_options_company_id", "gov_procurement_recommendation_options", ["company_id"])
    op.create_index("ix_gov_procurement_recommendation_options_recommendation_id", "gov_procurement_recommendation_options", ["recommendation_id"])
    op.create_index("ix_gov_procurement_recommendation_options_offer_id", "gov_procurement_recommendation_options", ["offer_id"])

    op.create_table(
        "gov_procurement_recommendation_rejections",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("recommendation_id", sa.String(length=36), nullable=False),
        sa.Column("offer_id", sa.String(length=36), nullable=False),
        sa.Column("causal", sa.String(length=16), nullable=False),
        sa.Column("motivacion", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("causal IN ('LCP76_1', 'LCP76_2', 'LCP76_3', 'LCP76_4', 'LCP76_5', 'LCP76_6', 'LCP76_7', 'LCP76_8', 'RLCP102_1', 'RLCP102_2', 'RLCP102_3', 'RLCP102_4', 'RLCP102_5', 'RLCP102_6')", name="ck_gov_procurement_recommendation_rejections_causal"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], name="fk_gov_procurement_recommendation_rejections_company_id"),
        sa.ForeignKeyConstraint(["recommendation_id"], ["gov_procurement_recommendations.id"], name="fk_gov_procurement_recommendation_rejections_recommendation_id"),
        sa.ForeignKeyConstraint(["offer_id"], ["gov_procurement_offers.id"], name="fk_gov_procurement_recommendation_rejections_offer_id"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("recommendation_id", "offer_id", name="uq_gov_proc_rec_rejections_offer"),
    )
    op.create_index("ix_gov_procurement_recommendation_rejections_company_id", "gov_procurement_recommendation_rejections", ["company_id"])
    op.create_index("ix_gov_procurement_recommendation_rejections_recommendation_id", "gov_procurement_recommendation_rejections", ["recommendation_id"])
    op.create_index("ix_gov_procurement_recommendation_rejections_offer_id", "gov_procurement_recommendation_rejections", ["offer_id"])

    op.create_table(
        "gov_procurement_decisions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("file_id", sa.String(length=36), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("recommendation_id", sa.String(length=36), nullable=True),
        sa.Column("resultado", sa.String(length=16), nullable=False),
        sa.Column("offer_id", sa.String(length=36), nullable=True),
        sa.Column("posicion", sa.SmallInteger(), nullable=True),
        sa.Column("causal_desierta", sa.String(length=16), nullable=True),
        sa.Column("causal_nulidad", sa.String(length=24), nullable=True),
        sa.Column("anula_id", sa.String(length=36), nullable=True),
        sa.Column("act_id", sa.String(length=36), nullable=False),
        sa.Column("cargo_id", sa.String(length=36), nullable=False),
        sa.Column("motivacion", sa.Text(), nullable=False),
        sa.Column("decidida_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decidida_por", sa.String(length=36), nullable=False),
        sa.Column("official_id", sa.String(length=36), nullable=True),
        sa.Column("estado", sa.String(length=16), nullable=False, server_default="VIGENTE"),
        sa.Column("afectada_por_id", sa.String(length=36), nullable=True),
        sa.Column("afectada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("resultado IN ('ADJUDICADA', 'DESIERTA', 'TERMINADA', 'NULIDAD')", name="ck_gov_procurement_decisions_resultado"),
        sa.CheckConstraint("estado IN ('VIGENTE', 'ANULADA', 'SUSTITUIDA')", name="ck_gov_procurement_decisions_estado"),
        sa.CheckConstraint("numero >= 1", name="ck_gov_procurement_decisions_numero"),
        sa.CheckConstraint("(offer_id IS NOT NULL) = (resultado = 'ADJUDICADA')", name="ck_gov_procurement_decisions_offer_presencia"),
        sa.CheckConstraint("(offer_id IS NULL) = (posicion IS NULL)", name="ck_gov_procurement_decisions_posicion_presencia"),
        sa.CheckConstraint("posicion IS NULL OR posicion BETWEEN 1 AND 3", name="ck_gov_procurement_decisions_posicion_valor"),
        sa.CheckConstraint("(causal_desierta IS NOT NULL) = (resultado = 'DESIERTA')", name="ck_gov_procurement_decisions_causal_desierta_presencia"),
        sa.CheckConstraint("causal_desierta IS NULL OR causal_desierta IN ('LCP113_1', 'LCP113_2', 'LCP113_3', 'LCP113_4', 'LCP113_5')", name="ck_gov_procurement_decisions_causal_desierta_valor"),
        sa.CheckConstraint("(causal_nulidad IS NOT NULL) = (resultado = 'NULIDAD')", name="ck_gov_procurement_decisions_causal_nulidad_presencia"),
        sa.CheckConstraint("causal_nulidad IS NULL OR causal_nulidad IN ('INFORMACION_FALSA', 'VIOLACION_LEGAL')", name="ck_gov_procurement_decisions_causal_nulidad_valor"),
        sa.CheckConstraint("(anula_id IS NOT NULL) = (resultado = 'NULIDAD')", name="ck_gov_procurement_decisions_anula_presencia"),
        sa.CheckConstraint("resultado = 'NULIDAD' OR recommendation_id IS NOT NULL", name="ck_gov_procurement_decisions_recommendation_presencia"),
        sa.CheckConstraint("(estado = 'VIGENTE') = (afectada_por_id IS NULL)", name="ck_gov_procurement_decisions_afectada_por_presencia"),
        sa.CheckConstraint("(afectada_por_id IS NULL) = (afectada_en IS NULL)", name="ck_gov_procurement_decisions_afectada_en_presencia"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], name="fk_gov_procurement_decisions_company_id"),
        sa.ForeignKeyConstraint(["file_id"], ["gov_procurement_files.id"], name="fk_gov_procurement_decisions_file_id"),
        sa.ForeignKeyConstraint(["recommendation_id"], ["gov_procurement_recommendations.id"], name="fk_gov_procurement_decisions_recommendation_id"),
        sa.ForeignKeyConstraint(["offer_id"], ["gov_procurement_offers.id"], name="fk_gov_procurement_decisions_offer_id"),
        sa.ForeignKeyConstraint(["anula_id"], ["gov_procurement_decisions.id"], name="fk_gov_procurement_decisions_anula_id"),
        sa.ForeignKeyConstraint(["act_id"], ["gov_acts.id"], name="fk_gov_procurement_decisions_act_id"),
        sa.ForeignKeyConstraint(["cargo_id"], ["gov_positions.id"], name="fk_gov_procurement_decisions_cargo_id"),
        sa.ForeignKeyConstraint(["official_id"], ["gov_officials.id"], name="fk_gov_procurement_decisions_official_id"),
        sa.ForeignKeyConstraint(
            ["afectada_por_id"],
            ["gov_procurement_decisions.id"],
            name="fk_gov_procurement_decisions_afectada_por_id",
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("act_id", name="uq_gov_procurement_decisions_act_id"),
        sa.UniqueConstraint("company_id", "file_id", "numero", name="uq_gov_procurement_decisions_company_file_numero"),
    )
    op.create_index(
        "uq_gov_procurement_decisions_final",
        "gov_procurement_decisions",
        ["file_id"],
        unique=True,
        postgresql_where=sa.text("estado = 'VIGENTE' AND resultado <> 'NULIDAD'"),
        sqlite_where=sa.text("estado = 'VIGENTE' AND resultado <> 'NULIDAD'"),
    )
    op.create_index("ix_gov_procurement_decisions_company_id", "gov_procurement_decisions", ["company_id"])
    op.create_index("ix_gov_procurement_decisions_file_id", "gov_procurement_decisions", ["file_id"])
    op.create_index("ix_gov_procurement_decisions_recommendation_id", "gov_procurement_decisions", ["recommendation_id"])
    op.create_index("ix_gov_procurement_decisions_offer_id", "gov_procurement_decisions", ["offer_id"])
    op.create_index("ix_gov_procurement_decisions_anula_id", "gov_procurement_decisions", ["anula_id"])
    op.create_index("ix_gov_procurement_decisions_cargo_id", "gov_procurement_decisions", ["cargo_id"])
    op.create_index("ix_gov_procurement_decisions_official_id", "gov_procurement_decisions", ["official_id"])

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

    op.execute("""
        CREATE OR REPLACE FUNCTION kontrol_gov_decision_immutable()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'Los registros de recomendación y decisión son inmutables';
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION kontrol_gov_recommendation_guard()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'Los registros de recomendación son inmutables';
            END IF;
            IF TG_OP = 'TRUNCATE' THEN
                RAISE EXCEPTION 'Los registros de recomendación son inmutables';
            END IF;
            IF TG_OP = 'UPDATE' THEN
                IF OLD.estado = 'EMITIDA' AND NEW.estado = 'SUSTITUIDA' AND NEW.sustituida_en IS NOT NULL
                   AND (to_jsonb(NEW) - 'estado' - 'sustituida_en' - 'updated_at') = (to_jsonb(OLD) - 'estado' - 'sustituida_en' - 'updated_at') THEN
                    RETURN NEW;
                END IF;
                RAISE EXCEPTION 'Los registros de recomendación son inmutables';
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION kontrol_gov_decision_guard()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'Los registros de decisión son inmutables';
            END IF;
            IF TG_OP = 'TRUNCATE' THEN
                RAISE EXCEPTION 'Los registros de decisión son inmutables';
            END IF;
            IF TG_OP = 'UPDATE' THEN
                IF OLD.estado = 'VIGENTE' AND NEW.estado IN ('ANULADA','SUSTITUIDA') AND NEW.afectada_por_id IS NOT NULL AND NEW.afectada_en IS NOT NULL
                   AND (to_jsonb(NEW) - 'estado' - 'afectada_por_id' - 'afectada_en' - 'updated_at') = (to_jsonb(OLD) - 'estado' - 'afectada_por_id' - 'afectada_en' - 'updated_at') THEN
                    RETURN NEW;
                END IF;
                RAISE EXCEPTION 'Los registros de decisión son inmutables';
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
    """)

    for _tabla in (
        "gov_procurement_recommendation_signatories",
        "gov_procurement_recommendation_options",
        "gov_procurement_recommendation_rejections",
    ):
        _nombre_corto = _tabla.split("_", 2)[-1]
        for _accion, _momento in (
            ("update", "BEFORE UPDATE"),
            ("delete", "BEFORE DELETE"),
            ("truncate", "BEFORE TRUNCATE"),
        ):
            op.execute(f"""
                CREATE TRIGGER trg_{_nombre_corto}_immutable_{_accion}
                {_momento} ON {_tabla}
                FOR EACH {"ROW" if _accion != "truncate" else "STATEMENT"} EXECUTE FUNCTION kontrol_gov_decision_immutable();
            """)

    for _accion, _momento in (
        ("update", "BEFORE UPDATE"),
        ("delete", "BEFORE DELETE"),
        ("truncate", "BEFORE TRUNCATE"),
    ):
        op.execute(f"""
            CREATE TRIGGER trg_gov_procurement_recommendations_guard_{_accion}
            {_momento} ON gov_procurement_recommendations
            FOR EACH {"ROW" if _accion != "truncate" else "STATEMENT"} EXECUTE FUNCTION kontrol_gov_recommendation_guard();
        """)
        op.execute(f"""
            CREATE TRIGGER trg_gov_procurement_decisions_guard_{_accion}
            {_momento} ON gov_procurement_decisions
            FOR EACH {"ROW" if _accion != "truncate" else "STATEMENT"} EXECUTE FUNCTION kontrol_gov_decision_guard();
        """)

    for _action in ("view", "recommend", "decide"):
        op.execute(f"""
            INSERT INTO permissions (id, resource, action, scope_type, created_at, updated_at)
            VALUES (
                gen_random_uuid()::varchar,
                'gobierno_decision',
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
          AND p.resource = 'gobierno_decision'
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM role_permissions rp
        USING permissions p
        WHERE rp.permission_id = p.id
          AND p.resource = 'gobierno_decision'
          AND rp.role_id IN (
              SELECT id FROM roles WHERE code = 'FUNCIONAL_COMPLETO' AND company_id IS NULL
          )
    """)
    op.execute("""
        DELETE FROM permissions WHERE resource = 'gobierno_decision'
    """)

    for _accion in ("update", "delete", "truncate"):
        op.execute(f"DROP TRIGGER IF EXISTS trg_gov_procurement_recommendations_guard_{_accion} ON gov_procurement_recommendations")
        op.execute(f"DROP TRIGGER IF EXISTS trg_gov_procurement_decisions_guard_{_accion} ON gov_procurement_decisions")

    for _tabla in (
        "gov_procurement_recommendation_signatories",
        "gov_procurement_recommendation_options",
        "gov_procurement_recommendation_rejections",
    ):
        _nombre_corto = _tabla.split("_", 2)[-1]
        for _accion in ("update", "delete", "truncate"):
            op.execute(f"DROP TRIGGER IF EXISTS trg_{_nombre_corto}_immutable_{_accion} ON {_tabla}")

    op.execute("DROP FUNCTION IF EXISTS kontrol_gov_decision_immutable()")
    op.execute("DROP FUNCTION IF EXISTS kontrol_gov_recommendation_guard()")
    op.execute("DROP FUNCTION IF EXISTS kontrol_gov_decision_guard()")

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
                'APERTURA_OFERTA', 'EVALUACION'
            )
        )
    """)

    op.drop_table("gov_procurement_decisions")
    op.drop_table("gov_procurement_recommendation_rejections")
    op.drop_table("gov_procurement_recommendation_options")
    op.drop_table("gov_procurement_recommendation_signatories")
    op.drop_table("gov_procurement_recommendations")
