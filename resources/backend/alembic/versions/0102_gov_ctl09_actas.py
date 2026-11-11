"""CTL-09: Actas de entrega."""

import sqlalchemy as sa

from alembic import op

down_revision = "0101_receipt_count_independence"
revision = "0102_gov_ctl09_actas"


def upgrade() -> None:
    op.create_table(
        "gov_handover_acts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("estado", sa.String(16), nullable=False),
        sa.Column("ambito", sa.String(10), nullable=False),
        sa.Column("unit_id", sa.String(36), nullable=True),
        sa.Column("assignment_id", sa.String(36), sa.ForeignKey("gov_assignments.id"), nullable=False),
        sa.Column("saliente", sa.JSON(), nullable=False),
        sa.Column("receptor_official_id", sa.String(36), nullable=False),
        sa.Column("receptor_assignment_id", sa.String(36), nullable=True),
        sa.Column("receptor", sa.JSON(), nullable=False),
        sa.Column("modalidad", sa.String(24), nullable=False),
        sa.Column("testigos", sa.JSON(), nullable=False),
        sa.Column("auditor_official_id", sa.String(36), nullable=True),
        sa.Column("motivo", sa.String(1000), nullable=False),
        sa.Column("fundamento", sa.String(1000), nullable=False),
        sa.Column("lugar", sa.String(200), nullable=False),
        sa.Column("fecha_corte", sa.Date(), nullable=False),
        sa.Column("fecha_suscripcion", sa.Date(), nullable=True),
        sa.Column("errores_deficiencias", sa.String(2000), nullable=True),
        sa.Column("suscrita_por", sa.String(36), nullable=True),
        sa.Column("suscrita_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("snapshot", sa.JSON(), nullable=True),
        sa.Column("snapshot_sha256", sa.String(64), nullable=True),
        sa.Column("informe_storage_key", sa.String(255), nullable=True),
        sa.Column("informe_sha256", sa.String(64), nullable=True),
        sa.Column("informe_bytes", sa.Integer(), nullable=True),
        sa.Column("remision_uai_fecha", sa.Date(), nullable=True),
        sa.Column("remision_uai_registrada_por", sa.String(36), nullable=True),
        sa.Column("verificacion_numero", sa.String(50), nullable=True),
        sa.Column("verificacion_fecha", sa.Date(), nullable=True),
        sa.Column("verificacion_resultado", sa.String(20), nullable=True),
        sa.Column("verificacion_fundamento", sa.String(2000), nullable=True),
        sa.Column("verificada_por", sa.String(36), nullable=True),
        sa.Column("verificada_en", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("company_id", "assignment_id", name="uq_gov_handover_acts_company_assignment"),
        sa.CheckConstraint("estado IN ('BORRADOR', 'SUSCRITA', 'VERIFICADA')", name="ck_gov_handover_acts_estado"),
        sa.CheckConstraint("ambito IN ('ENTE', 'UNIDAD')", name="ck_gov_handover_acts_ambito"),
        sa.CheckConstraint("modalidad IN ('ENTREGA', 'LEVANTADA_POR_RECEPTOR')", name="ck_gov_handover_acts_modalidad"),
        sa.CheckConstraint("estado = 'BORRADOR' OR (snapshot_sha256 IS NOT NULL AND informe_sha256 IS NOT NULL)", name="ck_gov_handover_acts_suscrita_hashes"),
        sa.CheckConstraint("(estado = 'VERIFICADA') = (verificacion_resultado IS NOT NULL)", name="ck_gov_handover_acts_verificacion"),
        sa.CheckConstraint("verificacion_resultado IS NULL OR verificacion_resultado IN ('CONFORME', 'CON_OBSERVACIONES')", name="ck_gov_handover_acts_verificacion_resultado"),
        sa.CheckConstraint("modalidad <> 'LEVANTADA_POR_RECEPTOR' OR auditor_official_id IS NOT NULL", name="ck_gov_handover_acts_levantada_auditor"),
    )
    op.create_index("ix_gov_handover_acts_company_id", "gov_handover_acts", ["company_id"])
    op.create_index("ix_gov_handover_acts_estado", "gov_handover_acts", ["estado"])
    op.create_index("ix_gov_handover_acts_assignment_id", "gov_handover_acts", ["assignment_id"])

    op.create_table(
        "gov_handover_annexes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("act_id", sa.String(36), sa.ForeignKey("gov_handover_acts.id"), nullable=False),
        sa.Column("codigo", sa.String(8), nullable=False),
        sa.Column("titulo", sa.String(200), nullable=False),
        sa.Column("obligatorio", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("generable", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("incluir_generado", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("documento_ids", sa.JSON(), nullable=False),
        sa.Column("constancia", sa.String(1000), nullable=True),
        sa.Column("contenido", sa.JSON(), nullable=True),
        sa.Column("documentos", sa.JSON(), nullable=True),
        sa.UniqueConstraint("act_id", "codigo", name="uq_gov_handover_annexes_act_codigo"),
        sa.CheckConstraint("incluir_generado = false OR generable = true", name="ck_gov_handover_annexes_generable"),
    )
    op.create_index("ix_gov_handover_annexes_company_id", "gov_handover_annexes", ["company_id"])
    op.create_index("ix_gov_handover_annexes_act_id", "gov_handover_annexes", ["act_id"])

    op.create_table(
        "gov_handover_observations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("act_id", sa.String(36), sa.ForeignKey("gov_handover_acts.id"), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("texto", sa.String(2000), nullable=False),
        sa.Column("registrada_por", sa.String(36), nullable=False),
        sa.Column("registrada_en", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_gov_handover_observations_company_id", "gov_handover_observations", ["company_id"])
    op.create_index("ix_gov_handover_observations_act_id", "gov_handover_observations", ["act_id"])

    op.execute("""
        CREATE OR REPLACE FUNCTION kontrol_gov_handover_act_immutable()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'Las actas de entrega no se pueden eliminar';
            ELSIF TG_OP = 'TRUNCATE' THEN
                RAISE EXCEPTION 'Las actas de entrega no se pueden truncar';
            ELSIF TG_OP = 'UPDATE' THEN
                IF OLD.snapshot_sha256 IS NOT NULL THEN
                    IF NEW.motivo IS DISTINCT FROM OLD.motivo
                        OR NEW.fundamento IS DISTINCT FROM OLD.fundamento
                        OR NEW.lugar IS DISTINCT FROM OLD.lugar
                        OR NEW.fecha_corte IS DISTINCT FROM OLD.fecha_corte
                        OR NEW.saliente::text IS DISTINCT FROM OLD.saliente::text
                        OR NEW.receptor::text IS DISTINCT FROM OLD.receptor::text
                        OR NEW.testigos::text IS DISTINCT FROM OLD.testigos::text
                        OR NEW.modalidad IS DISTINCT FROM OLD.modalidad
                        OR NEW.assignment_id IS DISTINCT FROM OLD.assignment_id
                        OR NEW.receptor_official_id IS DISTINCT FROM OLD.receptor_official_id
                        OR NEW.auditor_official_id IS DISTINCT FROM OLD.auditor_official_id
                        OR NEW.snapshot::text IS DISTINCT FROM OLD.snapshot::text
                        OR NEW.snapshot_sha256 IS DISTINCT FROM OLD.snapshot_sha256
                        OR NEW.informe_storage_key IS DISTINCT FROM OLD.informe_storage_key
                        OR NEW.informe_sha256 IS DISTINCT FROM OLD.informe_sha256
                        OR NEW.informe_bytes IS DISTINCT FROM OLD.informe_bytes
                        OR NEW.fecha_suscripcion IS DISTINCT FROM OLD.fecha_suscripcion
                        OR NEW.errores_deficiencias IS DISTINCT FROM OLD.errores_deficiencias
                        OR NEW.codigo IS DISTINCT FROM OLD.codigo THEN
                        RAISE EXCEPTION 'No se pueden modificar campos congelados de un acta suscrita';
                    END IF;
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION kontrol_gov_handover_annex_immutable()
        RETURNS TRIGGER AS $$
        DECLARE
            v_estado TEXT;
        BEGIN
            IF TG_OP = 'TRUNCATE' THEN
                RAISE EXCEPTION 'Los anexos de actas no se pueden truncar';
            END IF;

            SELECT estado INTO v_estado
            FROM gov_handover_acts
            WHERE id = COALESCE(OLD.act_id, NEW.act_id);

            IF TG_OP = 'DELETE' THEN
                IF v_estado IS DISTINCT FROM 'BORRADOR' THEN
                    RAISE EXCEPTION 'Solo se pueden eliminar anexos en borrador';
                END IF;
                RETURN OLD;
            ELSIF TG_OP = 'UPDATE' THEN
                IF v_estado IS DISTINCT FROM 'BORRADOR' THEN
                    RAISE EXCEPTION 'Los anexos no se pueden actualizar fuera de borrador';
                END IF;
                IF NEW.company_id IS DISTINCT FROM OLD.company_id
                    OR NEW.act_id IS DISTINCT FROM OLD.act_id
                    OR NEW.codigo IS DISTINCT FROM OLD.codigo THEN
                    RAISE EXCEPTION 'Los anexos no pueden cambiar de acta, empresa ni código';
                END IF;
                RETURN NEW;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION kontrol_gov_handover_observation_immutable()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'UPDATE' THEN
                RAISE EXCEPTION 'Las observaciones de actas no se pueden actualizar';
            ELSIF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'Las observaciones de actas no se pueden eliminar';
            ELSIF TG_OP = 'TRUNCATE' THEN
                RAISE EXCEPTION 'Las observaciones de actas no se pueden truncar';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER trg_gov_handover_acts_immutable_update
        BEFORE UPDATE ON gov_handover_acts
        FOR EACH ROW EXECUTE FUNCTION kontrol_gov_handover_act_immutable();
    """)
    op.execute("""
        CREATE TRIGGER trg_gov_handover_acts_immutable_delete
        BEFORE DELETE ON gov_handover_acts
        FOR EACH ROW EXECUTE FUNCTION kontrol_gov_handover_act_immutable();
    """)
    op.execute("""
        CREATE TRIGGER trg_gov_handover_acts_immutable_truncate
        BEFORE TRUNCATE ON gov_handover_acts
        FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_handover_act_immutable();
    """)
    op.execute("""
        CREATE TRIGGER trg_gov_handover_annexes_immutable_update
        BEFORE UPDATE ON gov_handover_annexes
        FOR EACH ROW EXECUTE FUNCTION kontrol_gov_handover_annex_immutable();
    """)
    op.execute("""
        CREATE TRIGGER trg_gov_handover_annexes_immutable_delete
        BEFORE DELETE ON gov_handover_annexes
        FOR EACH ROW EXECUTE FUNCTION kontrol_gov_handover_annex_immutable();
    """)
    op.execute("""
        CREATE TRIGGER trg_gov_handover_annexes_immutable_truncate
        BEFORE TRUNCATE ON gov_handover_annexes
        FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_handover_annex_immutable();
    """)
    op.execute("""
        CREATE TRIGGER trg_gov_handover_observations_immutable_update
        BEFORE UPDATE ON gov_handover_observations
        FOR EACH ROW EXECUTE FUNCTION kontrol_gov_handover_observation_immutable();
    """)
    op.execute("""
        CREATE TRIGGER trg_gov_handover_observations_immutable_delete
        BEFORE DELETE ON gov_handover_observations
        FOR EACH ROW EXECUTE FUNCTION kontrol_gov_handover_observation_immutable();
    """)
    op.execute("""
        CREATE TRIGGER trg_gov_handover_observations_immutable_truncate
        BEFORE TRUNCATE ON gov_handover_observations
        FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_handover_observation_immutable();
    """)

    for _action in ("view", "manage", "verify"):
        op.execute(f"""
            INSERT INTO permissions (id, resource, action, scope_type, created_at, updated_at)
            VALUES (
                gen_random_uuid()::varchar,
                'gobierno_actas',
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
          AND p.resource = 'gobierno_actas'
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM role_permissions
        WHERE permission_id IN (
            SELECT id FROM permissions WHERE resource = 'gobierno_actas'
        )
    """)
    op.execute("""
        DELETE FROM permissions WHERE resource = 'gobierno_actas'
    """)

    op.execute("DROP TRIGGER IF EXISTS trg_gov_handover_acts_immutable_update ON gov_handover_acts")
    op.execute("DROP TRIGGER IF EXISTS trg_gov_handover_acts_immutable_delete ON gov_handover_acts")
    op.execute("DROP TRIGGER IF EXISTS trg_gov_handover_acts_immutable_truncate ON gov_handover_acts")
    op.execute("DROP TRIGGER IF EXISTS trg_gov_handover_annexes_immutable_update ON gov_handover_annexes")
    op.execute("DROP TRIGGER IF EXISTS trg_gov_handover_annexes_immutable_delete ON gov_handover_annexes")
    op.execute("DROP TRIGGER IF EXISTS trg_gov_handover_annexes_immutable_truncate ON gov_handover_annexes")
    op.execute("DROP TRIGGER IF EXISTS trg_gov_handover_observations_immutable_update ON gov_handover_observations")
    op.execute("DROP TRIGGER IF EXISTS trg_gov_handover_observations_immutable_delete ON gov_handover_observations")
    op.execute("DROP TRIGGER IF EXISTS trg_gov_handover_observations_immutable_truncate ON gov_handover_observations")
    op.execute("DROP FUNCTION IF EXISTS kontrol_gov_handover_act_immutable()")
    op.execute("DROP FUNCTION IF EXISTS kontrol_gov_handover_annex_immutable()")
    op.execute("DROP FUNCTION IF EXISTS kontrol_gov_handover_observation_immutable()")
    op.drop_table("gov_handover_observations")
    op.drop_table("gov_handover_annexes")
    op.drop_table("gov_handover_acts")
