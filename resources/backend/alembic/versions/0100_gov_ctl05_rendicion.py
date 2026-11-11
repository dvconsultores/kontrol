"""CTL-05: Expediente de cuenta y reportes de rendicion."""

import sqlalchemy as sa

from alembic import op

down_revision = "0099_quote_award"
revision = "0100_gov_ctl05_rendicion"


def upgrade() -> None:
    op.create_table(
        "gov_rendition_files",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("numero_version", sa.Integer(), nullable=False),
        sa.Column("anterior_id", sa.String(36), sa.ForeignKey("gov_rendition_files.id"), nullable=True),
        sa.Column("denominacion", sa.String(200), nullable=False),
        sa.Column("ejercicio", sa.Integer(), nullable=True),
        sa.Column("periodo_desde", sa.Date(), nullable=False),
        sa.Column("periodo_hasta", sa.Date(), nullable=False),
        sa.Column("fecha_corte", sa.Date(), nullable=False),
        sa.Column("observaciones", sa.String(1000), nullable=True),
        sa.Column("assignment_id", sa.String(36), sa.ForeignKey("gov_assignments.id"), nullable=False),
        sa.Column("responsable", sa.JSON(), nullable=False),
        sa.Column("responsable_official_id", sa.String(36), nullable=False),
        sa.Column("estado", sa.String(16), nullable=False),
        sa.Column("formado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("formado_por", sa.String(36), nullable=True),
        sa.Column("snapshot", sa.JSON(), nullable=True),
        sa.Column("snapshot_sha256", sa.String(64), nullable=True),
        sa.Column("informe_storage_key", sa.String(255), nullable=True),
        sa.Column("informe_sha256", sa.String(64), nullable=True),
        sa.Column("informe_bytes", sa.Integer(), nullable=True),
        sa.Column("participacion_fecha", sa.Date(), nullable=True),
        sa.Column("participacion_oficio", sa.String(100), nullable=True),
        sa.Column("participacion_registrada_por", sa.String(36), nullable=True),
        sa.Column("participacion_registrada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("calificacion", sa.String(10), nullable=True),
        sa.Column("calificacion_organo", sa.String(200), nullable=True),
        sa.Column("calificacion_informe_numero", sa.String(50), nullable=True),
        sa.Column("calificacion_informe_fecha", sa.Date(), nullable=True),
        sa.Column("calificacion_fundamento", sa.String(1000), nullable=True),
        sa.Column("calificacion_registrada_por", sa.String(36), nullable=True),
        sa.Column("calificacion_registrada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fenecimiento_auto_numero", sa.String(50), nullable=True),
        sa.Column("fenecimiento_auto_fecha", sa.Date(), nullable=True),
        sa.Column("fenecimiento_fundamento", sa.String(1000), nullable=True),
        sa.Column("fenecimiento_registrado_por", sa.String(36), nullable=True),
        sa.Column("fenecimiento_registrado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sustitucion_motivo", sa.String(500), nullable=True),
        sa.CheckConstraint("numero_version >= 1", name="ck_gov_rendition_files_version_positive"),
        sa.CheckConstraint("periodo_desde <= periodo_hasta", name="ck_gov_rendition_files_period"),
        sa.CheckConstraint("fecha_corte >= periodo_desde AND fecha_corte <= periodo_hasta", name="ck_gov_rendition_files_corte"),
        sa.CheckConstraint("estado IN ('EN_FORMACION', 'FORMADA', 'PARTICIPADA', 'CALIFICADA', 'FENECIDA', 'SUSTITUIDA')", name="ck_gov_rendition_files_estado"),
        sa.CheckConstraint("estado = 'EN_FORMACION' OR (snapshot_sha256 IS NOT NULL AND informe_sha256 IS NOT NULL)", name="ck_gov_rendition_files_formada_hashes"),
        sa.CheckConstraint("(estado IN ('CALIFICADA', 'FENECIDA')) = (calificacion IS NOT NULL)", name="ck_gov_rendition_files_calificacion"),
        sa.UniqueConstraint("company_id", "codigo", "numero_version", name="uq_gov_rendition_files_company_code_version"),
    )
    op.create_index("ix_gov_rendition_files_company_id", "gov_rendition_files", ["company_id"])
    op.create_index("ix_gov_rendition_files_estado", "gov_rendition_files", ["estado"])
    op.create_index("ix_gov_rendition_files_assignment_id", "gov_rendition_files", ["assignment_id"])

    op.create_table(
        "gov_rendition_pieces",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("file_id", sa.String(36), sa.ForeignKey("gov_rendition_files.id"), nullable=False),
        sa.Column("audit_event_id", sa.String(36), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=True),
        sa.Column("fecha", sa.DateTime(timezone=True), nullable=False),
        sa.Column("proceso", sa.String(16), nullable=False),
        sa.Column("accion", sa.String(80), nullable=False),
        sa.Column("entidad", sa.String(80), nullable=False),
        sa.Column("entidad_id", sa.String(36), nullable=True),
        sa.Column("referencia", sa.String(300), nullable=False),
        sa.Column("objeto", sa.JSON(), nullable=True),
        sa.Column("documentos", sa.JSON(), nullable=False),
        sa.Column("huella", sa.String(64), nullable=False),
        sa.Column("incorporada_por", sa.String(36), nullable=True),
        sa.Column("incorporada_en", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("file_id", "audit_event_id", name="uq_gov_rendition_pieces_file_event"),
        sa.UniqueConstraint("file_id", "ordinal", name="uq_gov_rendition_pieces_file_ordinal"),
    )
    op.create_index("ix_gov_rendition_pieces_company_id", "gov_rendition_pieces", ["company_id"])
    op.create_index("ix_gov_rendition_pieces_file_id", "gov_rendition_pieces", ["file_id"])

    op.execute("""
        CREATE OR REPLACE FUNCTION kontrol_gov_rendition_file_immutable()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'Los expedientes de rendicion no se pueden eliminar';
            ELSIF TG_OP = 'TRUNCATE' THEN
                RAISE EXCEPTION 'Los expedientes de rendicion no se pueden truncar';
            ELSIF TG_OP = 'UPDATE' THEN
                IF OLD.snapshot_sha256 IS NOT NULL THEN
                    IF NEW.snapshot::text IS DISTINCT FROM OLD.snapshot::text
                        OR NEW.snapshot_sha256 IS DISTINCT FROM OLD.snapshot_sha256
                        OR NEW.informe_storage_key IS DISTINCT FROM OLD.informe_storage_key
                        OR NEW.informe_sha256 IS DISTINCT FROM OLD.informe_sha256
                        OR NEW.informe_bytes IS DISTINCT FROM OLD.informe_bytes
                        OR NEW.denominacion IS DISTINCT FROM OLD.denominacion
                        OR NEW.ejercicio IS DISTINCT FROM OLD.ejercicio
                        OR NEW.periodo_desde IS DISTINCT FROM OLD.periodo_desde
                        OR NEW.periodo_hasta IS DISTINCT FROM OLD.periodo_hasta
                        OR NEW.fecha_corte IS DISTINCT FROM OLD.fecha_corte
                        OR NEW.observaciones IS DISTINCT FROM OLD.observaciones
                        OR NEW.assignment_id IS DISTINCT FROM OLD.assignment_id
                        OR NEW.responsable::text IS DISTINCT FROM OLD.responsable::text
                        OR NEW.responsable_official_id IS DISTINCT FROM OLD.responsable_official_id
                        OR NEW.codigo IS DISTINCT FROM OLD.codigo
                        OR NEW.numero_version IS DISTINCT FROM OLD.numero_version THEN
                        RAISE EXCEPTION 'No se pueden modificar campos congelados de un expediente formado';
                    END IF;
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION kontrol_gov_rendition_piece_immutable()
        RETURNS TRIGGER AS $$
        DECLARE
            v_estado TEXT;
        BEGIN
            IF TG_OP = 'TRUNCATE' THEN
                RAISE EXCEPTION 'Las piezas de rendicion no se pueden truncar';
            END IF;

            SELECT estado INTO v_estado
            FROM gov_rendition_files
            WHERE id = COALESCE(OLD.file_id, NEW.file_id);

            IF TG_OP = 'DELETE' THEN
                IF v_estado IS DISTINCT FROM 'EN_FORMACION' THEN
                    RAISE EXCEPTION 'Solo se pueden eliminar piezas en formacion';
                END IF;
            ELSIF TG_OP = 'UPDATE' THEN
                IF NEW.ordinal IS DISTINCT FROM OLD.ordinal THEN
                    IF v_estado IS DISTINCT FROM 'EN_FORMACION' THEN
                        RAISE EXCEPTION 'Solo se puede reordenar en formacion';
                    END IF;
                ELSE
                    RAISE EXCEPTION 'Las piezas de rendicion no se pueden actualizar';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER trg_gov_rendition_files_immutable_update
        BEFORE UPDATE ON gov_rendition_files
        FOR EACH ROW EXECUTE FUNCTION kontrol_gov_rendition_file_immutable();
    """)
    op.execute("""
        CREATE TRIGGER trg_gov_rendition_files_immutable_delete
        BEFORE DELETE ON gov_rendition_files
        FOR EACH ROW EXECUTE FUNCTION kontrol_gov_rendition_file_immutable();
    """)
    op.execute("""
        CREATE TRIGGER trg_gov_rendition_files_immutable_truncate
        BEFORE TRUNCATE ON gov_rendition_files
        FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_rendition_file_immutable();
    """)
    op.execute("""
        CREATE TRIGGER trg_gov_rendition_pieces_immutable_update
        BEFORE UPDATE ON gov_rendition_pieces
        FOR EACH ROW EXECUTE FUNCTION kontrol_gov_rendition_piece_immutable();
    """)
    op.execute("""
        CREATE TRIGGER trg_gov_rendition_pieces_immutable_delete
        BEFORE DELETE ON gov_rendition_pieces
        FOR EACH ROW EXECUTE FUNCTION kontrol_gov_rendition_piece_immutable();
    """)
    op.execute("""
        CREATE TRIGGER trg_gov_rendition_pieces_immutable_truncate
        BEFORE TRUNCATE ON gov_rendition_pieces
        FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_rendition_piece_immutable();
    """)

    for _action in ("view", "form", "qualify"):
        op.execute(f"""
            INSERT INTO permissions (id, resource, action, scope_type, created_at, updated_at)
            VALUES (
                gen_random_uuid()::varchar,
                'gobierno_rendicion',
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
          AND p.resource = 'gobierno_rendicion'
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM role_permissions
        WHERE permission_id IN (
            SELECT id FROM permissions WHERE resource = 'gobierno_rendicion'
        )
    """)
    op.execute("""
        DELETE FROM permissions WHERE resource = 'gobierno_rendicion'
    """)

    op.execute("DROP TRIGGER IF EXISTS trg_gov_rendition_files_immutable_update ON gov_rendition_files")
    op.execute("DROP TRIGGER IF EXISTS trg_gov_rendition_files_immutable_delete ON gov_rendition_files")
    op.execute("DROP TRIGGER IF EXISTS trg_gov_rendition_files_immutable_truncate ON gov_rendition_files")
    op.execute("DROP TRIGGER IF EXISTS trg_gov_rendition_pieces_immutable_update ON gov_rendition_pieces")
    op.execute("DROP TRIGGER IF EXISTS trg_gov_rendition_pieces_immutable_delete ON gov_rendition_pieces")
    op.execute("DROP TRIGGER IF EXISTS trg_gov_rendition_pieces_immutable_truncate ON gov_rendition_pieces")
    op.execute("DROP FUNCTION IF EXISTS kontrol_gov_rendition_file_immutable()")
    op.execute("DROP FUNCTION IF EXISTS kontrol_gov_rendition_piece_immutable()")
    op.drop_table("gov_rendition_pieces")
    op.drop_table("gov_rendition_files")
