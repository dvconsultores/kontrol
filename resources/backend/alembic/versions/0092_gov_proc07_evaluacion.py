"""gov_proc07_evaluacion

Revision ID: 0092_gov_proc07_evaluacion
Revises: 0091_location_validations
Create Date: 2025-01-16 00:00:00.000000
"""
import sqlalchemy as sa

from alembic import op

revision = "0092_gov_proc07_evaluacion"
down_revision = "0091_location_validations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "gov_procurement_eval_matrices",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("file_id", sa.String(length=36), nullable=False),
        sa.Column("estado", sa.String(length=16), nullable=False),
        sa.Column("pliego_document_id", sa.String(length=36), nullable=False),
        sa.Column("pliego_version_id", sa.String(length=36), nullable=False),
        sa.Column("pliego_sha256", sa.String(length=64), nullable=False),
        sa.Column("transcripcion", sa.Boolean(), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.String(length=36), nullable=True),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("estado IN ('BORRADOR', 'BLOQUEADA')", name="ck_gov_procurement_eval_matrices_estado"),
        sa.CheckConstraint("version >= 1", name="ck_gov_procurement_eval_matrices_version"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], name="fk_gov_procurement_eval_matrices_company_id"),
        sa.ForeignKeyConstraint(["file_id"], ["gov_procurement_files.id"], name="fk_gov_procurement_eval_matrices_file_id"),
        sa.ForeignKeyConstraint(["pliego_document_id"], ["documents.id"], name="fk_gov_procurement_eval_matrices_pliego_document_id"),
        sa.ForeignKeyConstraint(
            ["pliego_version_id"],
            ["document_versions.id"],
            name="fk_gov_procurement_eval_matrices_pliego_version_id",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("file_id", name="uq_gov_procurement_eval_matrices_file"),
    )
    op.create_index("ix_gov_procurement_eval_matrices_company_id", "gov_procurement_eval_matrices", ["company_id"])
    op.create_index("ix_gov_procurement_eval_matrices_file_id", "gov_procurement_eval_matrices", ["file_id"])
    op.create_index("ix_gov_procurement_eval_matrices_pliego_document_id", "gov_procurement_eval_matrices", ["pliego_document_id"])
    op.create_index("ix_gov_procurement_eval_matrices_pliego_version_id", "gov_procurement_eval_matrices", ["pliego_version_id"])

    op.create_table(
        "gov_procurement_eval_criteria",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("matrix_id", sa.String(length=36), nullable=False),
        sa.Column("aspecto", sa.String(length=16), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=300), nullable=False),
        sa.Column("descripcion", sa.String(length=2000), nullable=True),
        sa.Column("escala", sa.String(length=16), nullable=False),
        sa.Column("puntaje_maximo", sa.Numeric(9, 2), nullable=True),
        sa.Column("ponderacion", sa.Numeric(7, 4), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "aspecto IN ('TECNICO', 'ECONOMICO', 'LEGAL')",
            name="ck_gov_procurement_eval_criteria_aspecto",
        ),
        sa.CheckConstraint("orden >= 1", name="ck_gov_procurement_eval_criteria_orden"),
        sa.CheckConstraint(
            "escala IN ('PUNTAJE', 'CUMPLE')",
            name="ck_gov_procurement_eval_criteria_escala",
        ),
        sa.CheckConstraint(
            "(escala = 'PUNTAJE' AND puntaje_maximo IS NOT NULL AND puntaje_maximo > 0) OR (escala = 'CUMPLE' AND puntaje_maximo IS NULL)",
            name="ck_gov_procurement_eval_criteria_puntaje",
        ),
        sa.CheckConstraint(
            "ponderacion IS NULL OR ponderacion > 0",
            name="ck_gov_procurement_eval_criteria_ponderacion",
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], name="fk_gov_procurement_eval_criteria_company_id"),
        sa.ForeignKeyConstraint(
            ["matrix_id"],
            ["gov_procurement_eval_matrices.id"],
            name="fk_gov_procurement_eval_criteria_matrix_id",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "matrix_id",
            "aspecto",
            "orden",
            name="uq_gov_procurement_eval_criteria_aspecto_orden",
        ),
    )
    op.create_index("ix_gov_procurement_eval_criteria_company_id", "gov_procurement_eval_criteria", ["company_id"])
    op.create_index("ix_gov_procurement_eval_criteria_matrix_id", "gov_procurement_eval_criteria", ["matrix_id"])

    op.create_table(
        "gov_procurement_openings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("file_id", sa.String(length=36), nullable=False),
        sa.Column("committee_id", sa.String(length=36), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("abierta_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acta_document_id", sa.String(length=36), nullable=False),
        sa.Column("acta_version_id", sa.String(length=36), nullable=False),
        sa.Column("acta_sha256", sa.String(length=64), nullable=False),
        sa.Column("observaciones", sa.String(length=2000), nullable=True),
        sa.Column("miembros_con_voto", sa.Integer(), nullable=False),
        sa.Column("asistentes_con_voto", sa.Integer(), nullable=False),
        sa.Column("quorum_requerido", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("numero >= 1", name="ck_gov_procurement_openings_numero"),
        sa.CheckConstraint("miembros_con_voto >= 1", name="ck_gov_procurement_openings_miembros_con_voto"),
        sa.CheckConstraint("asistentes_con_voto >= 1", name="ck_gov_procurement_openings_asistentes_con_voto"),
        sa.CheckConstraint("quorum_requerido >= 1", name="ck_gov_procurement_openings_quorum_requerido"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], name="fk_gov_procurement_openings_company_id"),
        sa.ForeignKeyConstraint(["file_id"], ["gov_procurement_files.id"], name="fk_gov_procurement_openings_file_id"),
        sa.ForeignKeyConstraint(
            ["committee_id"],
            ["gov_procurement_committees.id"],
            name="fk_gov_procurement_openings_committee_id",
        ),
        sa.ForeignKeyConstraint(
            ["acta_document_id"],
            ["documents.id"],
            name="fk_gov_procurement_openings_acta_document_id",
        ),
        sa.ForeignKeyConstraint(
            ["acta_version_id"],
            ["document_versions.id"],
            name="fk_gov_procurement_openings_acta_version_id",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "file_id", "numero", name="uq_gov_procurement_openings_file_numero"),
    )
    op.create_index("ix_gov_procurement_openings_company_id", "gov_procurement_openings", ["company_id"])
    op.create_index("ix_gov_procurement_openings_file_id", "gov_procurement_openings", ["file_id"])
    op.create_index("ix_gov_procurement_openings_committee_id", "gov_procurement_openings", ["committee_id"])
    op.create_index("ix_gov_procurement_openings_acta_document_id", "gov_procurement_openings", ["acta_document_id"])
    op.create_index("ix_gov_procurement_openings_acta_version_id", "gov_procurement_openings", ["acta_version_id"])

    op.create_table(
        "gov_procurement_opening_attendees",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("opening_id", sa.String(length=36), nullable=False),
        sa.Column("member_id", sa.String(length=36), nullable=False),
        sa.Column("official_id", sa.String(length=36), nullable=False),
        sa.Column("funcion", sa.String(length=16), nullable=False),
        sa.Column("condicion", sa.String(length=16), nullable=False),
        sa.Column("cuenta_voto", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "funcion IN ('MIEMBRO', 'SECRETARIO')",
            name="ck_gov_procurement_opening_attendees_funcion",
        ),
        sa.CheckConstraint(
            "condicion IN ('PRINCIPAL', 'SUPLENTE')",
            name="ck_gov_procurement_opening_attendees_condicion",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name="fk_gov_procurement_opening_attendees_company_id",
        ),
        sa.ForeignKeyConstraint(
            ["opening_id"],
            ["gov_procurement_openings.id"],
            name="fk_gov_procurement_opening_attendees_opening_id",
        ),
        sa.ForeignKeyConstraint(
            ["member_id"],
            ["gov_procurement_committee_members.id"],
            name="fk_gov_procurement_opening_attendees_member_id",
        ),
        sa.ForeignKeyConstraint(
            ["official_id"],
            ["gov_officials.id"],
            name="fk_gov_procurement_opening_attendees_official_id",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("opening_id", "member_id", name="uq_gov_procurement_opening_attendees_member"),
    )
    op.create_index("ix_gov_procurement_opening_attendees_company_id", "gov_procurement_opening_attendees", ["company_id"])
    op.create_index("ix_gov_procurement_opening_attendees_opening_id", "gov_procurement_opening_attendees", ["opening_id"])
    op.create_index("ix_gov_procurement_opening_attendees_member_id", "gov_procurement_opening_attendees", ["member_id"])
    op.create_index("ix_gov_procurement_opening_attendees_official_id", "gov_procurement_opening_attendees", ["official_id"])

    op.create_table(
        "gov_procurement_opening_offers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("opening_id", sa.String(length=36), nullable=False),
        sa.Column("offer_id", sa.String(length=36), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name="fk_gov_procurement_opening_offers_company_id",
        ),
        sa.ForeignKeyConstraint(
            ["opening_id"],
            ["gov_procurement_openings.id"],
            name="fk_gov_procurement_opening_offers_opening_id",
        ),
        sa.ForeignKeyConstraint(
            ["offer_id"],
            ["gov_procurement_offers.id"],
            name="fk_gov_procurement_opening_offers_offer_id",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("offer_id", name="uq_gov_procurement_opening_offers_offer"),
    )
    op.create_index("ix_gov_procurement_opening_offers_company_id", "gov_procurement_opening_offers", ["company_id"])
    op.create_index("ix_gov_procurement_opening_offers_opening_id", "gov_procurement_opening_offers", ["opening_id"])
    op.create_index("ix_gov_procurement_opening_offers_offer_id", "gov_procurement_opening_offers", ["offer_id"])

    op.create_table(
        "gov_procurement_eval_contributions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("offer_id", sa.String(length=36), nullable=False),
        sa.Column("criterion_id", sa.String(length=36), nullable=False),
        sa.Column("matrix_id", sa.String(length=36), nullable=False),
        sa.Column("matrix_version", sa.Integer(), nullable=False),
        sa.Column("member_id", sa.String(length=36), nullable=False),
        sa.Column("official_id", sa.String(length=36), nullable=False),
        sa.Column("puntaje", sa.Numeric(9, 2), nullable=True),
        sa.Column("cumple", sa.Boolean(), nullable=True),
        sa.Column("observacion", sa.String(length=2000), nullable=True),
        sa.Column("evidencia_document_id", sa.String(length=36), nullable=True),
        sa.Column("evidencia_version_id", sa.String(length=36), nullable=True),
        sa.Column("reemplaza_id", sa.String(length=36), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "matrix_version >= 1",
            name="ck_gov_procurement_eval_contributions_matrix_version",
        ),
        sa.CheckConstraint(
            "(puntaje IS NULL AND cumple IS NOT NULL) OR (puntaje IS NOT NULL AND cumple IS NULL)",
            name="ck_gov_procurement_eval_contributions_valor",
        ),
        sa.CheckConstraint(
            "puntaje IS NULL OR puntaje >= 0",
            name="ck_gov_procurement_eval_contributions_puntaje",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name="fk_gov_procurement_eval_contributions_company_id",
        ),
        sa.ForeignKeyConstraint(
            ["offer_id"],
            ["gov_procurement_offers.id"],
            name="fk_gov_procurement_eval_contributions_offer_id",
        ),
        sa.ForeignKeyConstraint(
            ["criterion_id"],
            ["gov_procurement_eval_criteria.id"],
            name="fk_gov_procurement_eval_contributions_criterion_id",
        ),
        sa.ForeignKeyConstraint(
            ["matrix_id"],
            ["gov_procurement_eval_matrices.id"],
            name="fk_gov_procurement_eval_contributions_matrix_id",
        ),
        sa.ForeignKeyConstraint(
            ["member_id"],
            ["gov_procurement_committee_members.id"],
            name="fk_gov_procurement_eval_contributions_member_id",
        ),
        sa.ForeignKeyConstraint(
            ["official_id"],
            ["gov_officials.id"],
            name="fk_gov_procurement_eval_contributions_official_id",
        ),
        sa.ForeignKeyConstraint(
            ["evidencia_document_id"],
            ["documents.id"],
            name="fk_gov_procurement_eval_contributions_evidencia_document_id",
        ),
        sa.ForeignKeyConstraint(
            ["evidencia_version_id"],
            ["document_versions.id"],
            name="fk_gov_procurement_eval_contributions_evidencia_version_id",
        ),
        sa.ForeignKeyConstraint(
            ["reemplaza_id"],
            ["gov_procurement_eval_contributions.id"],
            name="fk_gov_procurement_eval_contributions_reemplaza_id",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_gov_procurement_eval_contributions_company_id", "gov_procurement_eval_contributions", ["company_id"])
    op.create_index("ix_gov_procurement_eval_contributions_offer_id", "gov_procurement_eval_contributions", ["offer_id"])
    op.create_index("ix_gov_procurement_eval_contributions_criterion_id", "gov_procurement_eval_contributions", ["criterion_id"])
    op.create_index("ix_gov_procurement_eval_contributions_matrix_id", "gov_procurement_eval_contributions", ["matrix_id"])
    op.create_index("ix_gov_procurement_eval_contributions_member_id", "gov_procurement_eval_contributions", ["member_id"])
    op.create_index("ix_gov_procurement_eval_contributions_official_id", "gov_procurement_eval_contributions", ["official_id"])
    op.create_index("ix_gov_procurement_eval_contributions_evidencia_document_id", "gov_procurement_eval_contributions", ["evidencia_document_id"])
    op.create_index("ix_gov_procurement_eval_contributions_evidencia_version_id", "gov_procurement_eval_contributions", ["evidencia_version_id"])
    op.create_index("ix_gov_procurement_eval_contributions_reemplaza_id", "gov_procurement_eval_contributions", ["reemplaza_id"], unique=True)
    op.create_index(
        "uq_gov_procurement_eval_contributions_raiz",
        "gov_procurement_eval_contributions",
        ["company_id", "offer_id", "criterion_id", "member_id"],
        unique=True,
        postgresql_where=sa.text("reemplaza_id IS NULL"),
    )

    op.create_table(
        "gov_procurement_eval_results",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("offer_id", sa.String(length=36), nullable=False),
        sa.Column("criterion_id", sa.String(length=36), nullable=False),
        sa.Column("matrix_id", sa.String(length=36), nullable=False),
        sa.Column("matrix_version", sa.Integer(), nullable=False),
        sa.Column("member_id", sa.String(length=36), nullable=False),
        sa.Column("official_id", sa.String(length=36), nullable=False),
        sa.Column("puntaje", sa.Numeric(9, 2), nullable=True),
        sa.Column("cumple", sa.Boolean(), nullable=True),
        sa.Column("observacion", sa.String(length=2000), nullable=True),
        sa.Column("evidencia_document_id", sa.String(length=36), nullable=True),
        sa.Column("evidencia_version_id", sa.String(length=36), nullable=True),
        sa.Column("reemplaza_id", sa.String(length=36), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "matrix_version >= 1",
            name="ck_gov_procurement_eval_results_matrix_version",
        ),
        sa.CheckConstraint(
            "(puntaje IS NULL AND cumple IS NOT NULL) OR (puntaje IS NOT NULL AND cumple IS NULL)",
            name="ck_gov_procurement_eval_results_valor",
        ),
        sa.CheckConstraint(
            "puntaje IS NULL OR puntaje >= 0",
            name="ck_gov_procurement_eval_results_puntaje",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name="fk_gov_procurement_eval_results_company_id",
        ),
        sa.ForeignKeyConstraint(
            ["offer_id"],
            ["gov_procurement_offers.id"],
            name="fk_gov_procurement_eval_results_offer_id",
        ),
        sa.ForeignKeyConstraint(
            ["criterion_id"],
            ["gov_procurement_eval_criteria.id"],
            name="fk_gov_procurement_eval_results_criterion_id",
        ),
        sa.ForeignKeyConstraint(
            ["matrix_id"],
            ["gov_procurement_eval_matrices.id"],
            name="fk_gov_procurement_eval_results_matrix_id",
        ),
        sa.ForeignKeyConstraint(
            ["member_id"],
            ["gov_procurement_committee_members.id"],
            name="fk_gov_procurement_eval_results_member_id",
        ),
        sa.ForeignKeyConstraint(
            ["official_id"],
            ["gov_officials.id"],
            name="fk_gov_procurement_eval_results_official_id",
        ),
        sa.ForeignKeyConstraint(
            ["evidencia_document_id"],
            ["documents.id"],
            name="fk_gov_procurement_eval_results_evidencia_document_id",
        ),
        sa.ForeignKeyConstraint(
            ["evidencia_version_id"],
            ["document_versions.id"],
            name="fk_gov_procurement_eval_results_evidencia_version_id",
        ),
        sa.ForeignKeyConstraint(
            ["reemplaza_id"],
            ["gov_procurement_eval_results.id"],
            name="fk_gov_procurement_eval_results_reemplaza_id",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_gov_procurement_eval_results_company_id", "gov_procurement_eval_results", ["company_id"])
    op.create_index("ix_gov_procurement_eval_results_offer_id", "gov_procurement_eval_results", ["offer_id"])
    op.create_index("ix_gov_procurement_eval_results_criterion_id", "gov_procurement_eval_results", ["criterion_id"])
    op.create_index("ix_gov_procurement_eval_results_matrix_id", "gov_procurement_eval_results", ["matrix_id"])
    op.create_index("ix_gov_procurement_eval_results_member_id", "gov_procurement_eval_results", ["member_id"])
    op.create_index("ix_gov_procurement_eval_results_official_id", "gov_procurement_eval_results", ["official_id"])
    op.create_index("ix_gov_procurement_eval_results_evidencia_document_id", "gov_procurement_eval_results", ["evidencia_document_id"])
    op.create_index("ix_gov_procurement_eval_results_evidencia_version_id", "gov_procurement_eval_results", ["evidencia_version_id"])
    op.create_index("ix_gov_procurement_eval_results_reemplaza_id", "gov_procurement_eval_results", ["reemplaza_id"], unique=True)
    op.create_index(
        "uq_gov_procurement_eval_results_raiz",
        "gov_procurement_eval_results",
        ["company_id", "offer_id", "criterion_id"],
        unique=True,
        postgresql_where=sa.text("reemplaza_id IS NULL"),
    )

    op.add_column("document_seals", sa.Column("released_reason", sa.String(length=300), nullable=True))
    op.add_column("document_seals", sa.Column("released_resource_type", sa.String(length=64), nullable=True))
    op.add_column("document_seals", sa.Column("released_resource_id", sa.String(length=36), nullable=True))

    op.add_column("gov_procurement_files", sa.Column("evaluacion_concluida_en", sa.DateTime(timezone=True), nullable=True))
    op.add_column("gov_procurement_files", sa.Column("evaluacion_concluida_por", sa.String(length=36), nullable=True))

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

    op.execute("""
        CREATE OR REPLACE FUNCTION kontrol_gov_eval_criterio_bloqueado()
        RETURNS trigger AS $$
        DECLARE
            v_estado varchar(16);
        BEGIN
            SELECT estado INTO v_estado
            FROM gov_procurement_eval_matrices
            WHERE id = COALESCE(NEW.matrix_id, OLD.matrix_id);
            IF v_estado = 'BLOQUEADA' THEN
                RAISE EXCEPTION 'La matriz está bloqueada';
            END IF;
            RETURN COALESCE(NEW, OLD);
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_gov_eval_criterio_bloqueado_insert
        BEFORE INSERT ON gov_procurement_eval_criteria
        FOR EACH ROW EXECUTE FUNCTION kontrol_gov_eval_criterio_bloqueado();
    """)
    op.execute("""
        CREATE TRIGGER trg_gov_eval_criterio_bloqueado_update
        BEFORE UPDATE ON gov_procurement_eval_criteria
        FOR EACH ROW EXECUTE FUNCTION kontrol_gov_eval_criterio_bloqueado();
    """)
    op.execute("""
        CREATE TRIGGER trg_gov_eval_criterio_bloqueado_delete
        BEFORE DELETE ON gov_procurement_eval_criteria
        FOR EACH ROW EXECUTE FUNCTION kontrol_gov_eval_criterio_bloqueado();
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION kontrol_gov_eval_immutable()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'Los registros de evaluación son inmutables';
        END;
        $$ LANGUAGE plpgsql;
    """)
    for _tabla in (
        "gov_procurement_openings",
        "gov_procurement_opening_attendees",
        "gov_procurement_opening_offers",
        "gov_procurement_eval_contributions",
        "gov_procurement_eval_results",
    ):
        op.execute(f"""
            CREATE TRIGGER trg_{_tabla.split('_', 2)[-1]}_immutable_update
            BEFORE UPDATE ON {_tabla}
            FOR EACH ROW EXECUTE FUNCTION kontrol_gov_eval_immutable();
        """)
        op.execute(f"""
            CREATE TRIGGER trg_{_tabla.split('_', 2)[-1]}_immutable_delete
            BEFORE DELETE ON {_tabla}
            FOR EACH ROW EXECUTE FUNCTION kontrol_gov_eval_immutable();
        """)
        op.execute(f"""
            CREATE TRIGGER trg_{_tabla.split('_', 2)[-1]}_immutable_truncate
            BEFORE TRUNCATE ON {_tabla}
            FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_eval_immutable();
        """)

    for _action in ("view", "criteria", "open", "evaluate"):
        op.execute(f"""
            INSERT INTO permissions (id, resource, action, scope_type, created_at, updated_at)
            VALUES (
                gen_random_uuid()::varchar,
                'gobierno_evaluacion',
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
          AND p.resource = 'gobierno_evaluacion'
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM role_permissions rp
        USING permissions p
        WHERE rp.permission_id = p.id
          AND p.resource = 'gobierno_evaluacion'
          AND rp.role_id IN (
              SELECT id FROM roles WHERE code = 'FUNCIONAL_COMPLETO' AND company_id IS NULL
          )
    """)
    op.execute("""
        DELETE FROM permissions WHERE resource = 'gobierno_evaluacion'
    """)

    for _tabla in (
        "gov_procurement_openings",
        "gov_procurement_opening_attendees",
        "gov_procurement_opening_offers",
        "gov_procurement_eval_contributions",
        "gov_procurement_eval_results",
    ):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{_tabla.split('_', 2)[-1]}_immutable_update ON {_tabla}")
        op.execute(f"DROP TRIGGER IF EXISTS trg_{_tabla.split('_', 2)[-1]}_immutable_delete ON {_tabla}")
        op.execute(f"DROP TRIGGER IF EXISTS trg_{_tabla.split('_', 2)[-1]}_immutable_truncate ON {_tabla}")
    op.execute("DROP FUNCTION IF EXISTS kontrol_gov_eval_immutable()")

    op.execute("DROP TRIGGER IF EXISTS trg_gov_eval_criterio_bloqueado_insert ON gov_procurement_eval_criteria")
    op.execute("DROP TRIGGER IF EXISTS trg_gov_eval_criterio_bloqueado_update ON gov_procurement_eval_criteria")
    op.execute("DROP TRIGGER IF EXISTS trg_gov_eval_criterio_bloqueado_delete ON gov_procurement_eval_criteria")
    op.execute("DROP FUNCTION IF EXISTS kontrol_gov_eval_criterio_bloqueado()")

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

    op.drop_column("gov_procurement_files", "evaluacion_concluida_por")
    op.drop_column("gov_procurement_files", "evaluacion_concluida_en")

    op.drop_column("document_seals", "released_resource_id")
    op.drop_column("document_seals", "released_resource_type")
    op.drop_column("document_seals", "released_reason")

    op.drop_index("ix_gov_procurement_eval_results_reemplaza_id", table_name="gov_procurement_eval_results")
    op.drop_index("ix_gov_procurement_eval_results_evidencia_version_id", table_name="gov_procurement_eval_results")
    op.drop_index("ix_gov_procurement_eval_results_evidencia_document_id", table_name="gov_procurement_eval_results")
    op.drop_index("ix_gov_procurement_eval_results_official_id", table_name="gov_procurement_eval_results")
    op.drop_index("ix_gov_procurement_eval_results_member_id", table_name="gov_procurement_eval_results")
    op.drop_index("ix_gov_procurement_eval_results_matrix_id", table_name="gov_procurement_eval_results")
    op.drop_index("ix_gov_procurement_eval_results_criterion_id", table_name="gov_procurement_eval_results")
    op.drop_index("ix_gov_procurement_eval_results_offer_id", table_name="gov_procurement_eval_results")
    op.drop_index("ix_gov_procurement_eval_results_company_id", table_name="gov_procurement_eval_results")
    op.drop_index("uq_gov_procurement_eval_results_raiz", table_name="gov_procurement_eval_results")
    op.drop_table("gov_procurement_eval_results")

    op.drop_index("ix_gov_procurement_eval_contributions_reemplaza_id", table_name="gov_procurement_eval_contributions")
    op.drop_index("ix_gov_procurement_eval_contributions_evidencia_version_id", table_name="gov_procurement_eval_contributions")
    op.drop_index("ix_gov_procurement_eval_contributions_evidencia_document_id", table_name="gov_procurement_eval_contributions")
    op.drop_index("ix_gov_procurement_eval_contributions_official_id", table_name="gov_procurement_eval_contributions")
    op.drop_index("ix_gov_procurement_eval_contributions_member_id", table_name="gov_procurement_eval_contributions")
    op.drop_index("ix_gov_procurement_eval_contributions_matrix_id", table_name="gov_procurement_eval_contributions")
    op.drop_index("ix_gov_procurement_eval_contributions_criterion_id", table_name="gov_procurement_eval_contributions")
    op.drop_index("ix_gov_procurement_eval_contributions_offer_id", table_name="gov_procurement_eval_contributions")
    op.drop_index("ix_gov_procurement_eval_contributions_company_id", table_name="gov_procurement_eval_contributions")
    op.drop_index("uq_gov_procurement_eval_contributions_raiz", table_name="gov_procurement_eval_contributions")
    op.drop_table("gov_procurement_eval_contributions")

    op.drop_index("ix_gov_procurement_opening_offers_offer_id", table_name="gov_procurement_opening_offers")
    op.drop_index("ix_gov_procurement_opening_offers_opening_id", table_name="gov_procurement_opening_offers")
    op.drop_index("ix_gov_procurement_opening_offers_company_id", table_name="gov_procurement_opening_offers")
    op.drop_table("gov_procurement_opening_offers")

    op.drop_index("ix_gov_procurement_opening_attendees_official_id", table_name="gov_procurement_opening_attendees")
    op.drop_index("ix_gov_procurement_opening_attendees_member_id", table_name="gov_procurement_opening_attendees")
    op.drop_index("ix_gov_procurement_opening_attendees_opening_id", table_name="gov_procurement_opening_attendees")
    op.drop_index("ix_gov_procurement_opening_attendees_company_id", table_name="gov_procurement_opening_attendees")
    op.drop_table("gov_procurement_opening_attendees")

    op.drop_index("ix_gov_procurement_openings_acta_version_id", table_name="gov_procurement_openings")
    op.drop_index("ix_gov_procurement_openings_acta_document_id", table_name="gov_procurement_openings")
    op.drop_index("ix_gov_procurement_openings_committee_id", table_name="gov_procurement_openings")
    op.drop_index("ix_gov_procurement_openings_file_id", table_name="gov_procurement_openings")
    op.drop_index("ix_gov_procurement_openings_company_id", table_name="gov_procurement_openings")
    op.drop_table("gov_procurement_openings")

    op.drop_index("ix_gov_procurement_eval_criteria_matrix_id", table_name="gov_procurement_eval_criteria")
    op.drop_index("ix_gov_procurement_eval_criteria_company_id", table_name="gov_procurement_eval_criteria")
    op.drop_table("gov_procurement_eval_criteria")

    op.drop_index("ix_gov_procurement_eval_matrices_pliego_version_id", table_name="gov_procurement_eval_matrices")
    op.drop_index("ix_gov_procurement_eval_matrices_pliego_document_id", table_name="gov_procurement_eval_matrices")
    op.drop_index("ix_gov_procurement_eval_matrices_file_id", table_name="gov_procurement_eval_matrices")
    op.drop_index("ix_gov_procurement_eval_matrices_company_id", table_name="gov_procurement_eval_matrices")
    op.drop_table("gov_procurement_eval_matrices")
