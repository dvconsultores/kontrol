"""expedientes de contratacion (PROC-03)

Revision ID: 0080_gov_proc03_expedientes
Revises: 0079_gov_proc02_comisiones
Create Date: 2026-01-01 00:00:00.000000
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa

from alembic import op

revision = "0080_gov_proc03_expedientes"
down_revision = "0079_gov_proc02_comisiones"
branch_labels = None
depends_on = None

PERMISOS = {"gobierno_expedientes": ("view", "manage", "close")}


def _en(*valores: str) -> str:
    return ", ".join(f"'{v}'" for v in valores)


def _tiempos() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]


def _conceder_permisos(bind) -> None:
    rol = bind.execute(
        sa.text("SELECT id FROM roles WHERE code = 'FUNCIONAL_COMPLETO' AND company_id IS NULL")
    ).fetchone()
    for recurso, acciones in PERMISOS.items():
        for accion in acciones:
            permiso = bind.execute(
                sa.text("SELECT id FROM permissions WHERE resource = :r AND action = :a"),
                {"r": recurso, "a": accion},
            ).fetchone()
            if permiso is None:
                permiso_id = str(uuid.uuid4())
                bind.execute(
                    sa.text(
                        "INSERT INTO permissions (id, resource, action, scope_type) "
                        "VALUES (:id, :r, :a, 'COMPANY')"
                    ),
                    {"id": permiso_id, "r": recurso, "a": accion},
                )
            else:
                permiso_id = permiso[0]
            if rol is not None:
                existe = bind.execute(
                    sa.text(
                        "SELECT id FROM role_permissions WHERE role_id = :role AND permission_id = :perm"
                    ),
                    {"role": rol[0], "perm": permiso_id},
                ).fetchone()
                if existe is None:
                    bind.execute(
                        sa.text(
                            "INSERT INTO role_permissions (id, role_id, permission_id) "
                            "VALUES (:id, :role, :perm)"
                        ),
                        {"id": str(uuid.uuid4()), "role": rol[0], "perm": permiso_id},
                    )


def _proceso_sod(bind, *procesos: str) -> None:
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE gov_sod_rules DROP CONSTRAINT ck_gov_sod_rules_proceso")
        op.execute(
            "ALTER TABLE gov_sod_rules ADD CONSTRAINT ck_gov_sod_rules_proceso "
            f"CHECK (proceso IN ({_en(*procesos)}))"
        )
    else:
        with op.batch_alter_table("gov_sod_rules") as batch:
            batch.drop_constraint("ck_gov_sod_rules_proceso", type_="check")
            batch.create_check_constraint("proceso", f"proceso IN ({_en(*procesos)})")


def upgrade() -> None:
    op.create_table(
        "gov_procurement_files",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False, index=True),
        sa.Column("numero", sa.String(40), nullable=False),
        sa.Column("fecha_inicio", sa.Date, nullable=False),
        sa.Column("objeto", sa.String(1000), nullable=False),
        sa.Column("partes", sa.String(1000), nullable=True),
        sa.Column("tipo_contratacion", sa.String(16), nullable=False),
        sa.Column("modalidad_declarada", sa.String(24), nullable=True),
        sa.Column("modalidad_fundamento", sa.String(1000), nullable=True),
        sa.Column("modalidad_fuente", sa.String(300), nullable=True),
        sa.Column("unidad_id", sa.String(36), sa.ForeignKey("gov_units.id"), nullable=False, index=True),
        sa.Column("unidad_nombre", sa.String(200), nullable=False),
        sa.Column("committee_id", sa.String(36), sa.ForeignKey("gov_procurement_committees.id"), nullable=True, index=True),
        sa.Column("comision_no_aplica_motivo", sa.String(500), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="ABIERTO"),
        sa.Column("cierre_fecha", sa.Date, nullable=True),
        sa.Column("cierre_motivo", sa.String(1000), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_by", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        *_tiempos(),
        sa.UniqueConstraint("company_id", "numero", name="uq_gov_procurement_files_numero"),
        sa.CheckConstraint(f"status IN ({_en('ABIERTO', 'CERRADO', 'DESCARTADO')})", name="ck_gov_procurement_files_status"),
        sa.CheckConstraint(f"tipo_contratacion IN ({_en('BIENES', 'SERVICIOS', 'OBRAS')})", name="ck_gov_procurement_files_tipo_contratacion"),
        sa.CheckConstraint(
            f"modalidad_declarada IS NULL OR modalidad_declarada IN ({_en('CONCURSO_ABIERTO', 'CONCURSO_CERRADO', 'CONSULTA_PRECIOS', 'CONTRATACION_DIRECTA')})",
            name="ck_gov_procurement_files_modalidad",
        ),
        sa.CheckConstraint(
            "modalidad_declarada IS NULL OR modalidad_fundamento IS NOT NULL",
            name="ck_gov_procurement_files_modalidad_con_fundamento",
        ),
        sa.CheckConstraint(
            "committee_id IS NULL OR comision_no_aplica_motivo IS NULL",
            name="ck_gov_procurement_files_comision_o_motivo",
        ),
        sa.CheckConstraint(
            "status = 'ABIERTO' OR (cierre_fecha IS NOT NULL AND cierre_motivo IS NOT NULL)",
            name="ck_gov_procurement_files_cierre_con_motivo",
        ),
        sa.CheckConstraint("version >= 1", name="ck_gov_procurement_files_version"),
    )

    op.create_table(
        "gov_procurement_file_responsibles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False, index=True),
        sa.Column("file_id", sa.String(36), sa.ForeignKey("gov_procurement_files.id"), nullable=False, index=True),
        sa.Column("official_id", sa.String(36), sa.ForeignKey("gov_officials.id"), nullable=False, index=True),
        sa.Column("rol", sa.String(16), nullable=False),
        sa.Column("funcionario_nombre", sa.String(200), nullable=False),
        sa.Column("cargo_nombre", sa.String(200), nullable=True),
        sa.Column("unidad_nombre", sa.String(200), nullable=True),
        sa.Column("desde", sa.Date, nullable=False),
        sa.Column("fin_efectivo", sa.Date, nullable=True),
        sa.Column("motivo_fin", sa.String(500), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        *_tiempos(),
        sa.CheckConstraint(f"rol IN ({_en('RESPONSABLE', 'REQUIRENTE', 'SUSTANCIACION', 'CUSTODIA')})", name="ck_gov_procurement_file_responsibles_rol"),
        sa.CheckConstraint("fin_efectivo IS NULL OR fin_efectivo >= desde", name="ck_gov_procurement_file_responsibles_fin_tras_inicio"),
        sa.CheckConstraint("(fin_efectivo IS NULL) = (motivo_fin IS NULL)", name="ck_gov_procurement_file_responsibles_fin_con_motivo"),
    )
    op.create_index(
        "uq_gov_file_responsible_vigente",
        "gov_procurement_file_responsibles",
        ["file_id", "official_id", "rol"],
        unique=True,
        postgresql_where=sa.text("fin_efectivo IS NULL"),
        sqlite_where=sa.text("fin_efectivo IS NULL"),
    )
    op.create_index(
        "uq_gov_file_principal_vigente",
        "gov_procurement_file_responsibles",
        ["file_id"],
        unique=True,
        postgresql_where=sa.text("fin_efectivo IS NULL AND rol = 'RESPONSABLE'"),
        sqlite_where=sa.text("fin_efectivo IS NULL AND rol = 'RESPONSABLE'"),
    )

    op.create_table(
        "gov_procurement_file_milestones",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False, index=True),
        sa.Column("file_id", sa.String(36), sa.ForeignKey("gov_procurement_files.id"), nullable=False, index=True),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("fuente", sa.String(300), nullable=True),
        sa.Column("fecha_prevista", sa.Date, nullable=False),
        sa.Column("fecha_real", sa.Date, nullable=True),
        sa.Column("official_id", sa.String(36), sa.ForeignKey("gov_officials.id"), nullable=True),
        sa.Column("responsable_etiqueta", sa.String(400), nullable=True),
        sa.Column("estado", sa.String(16), nullable=False, server_default="PREVISTO"),
        sa.Column("motivo_no_aplica", sa.String(500), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        *_tiempos(),
        sa.CheckConstraint(f"estado IN ({_en('PREVISTO', 'CUMPLIDO', 'NO_APLICA')})", name="ck_gov_procurement_file_milestones_estado"),
        sa.CheckConstraint("(estado = 'CUMPLIDO') = (fecha_real IS NOT NULL)", name="ck_gov_procurement_file_milestones_cumplido_con_fecha"),
        sa.CheckConstraint("(estado = 'NO_APLICA') = (motivo_no_aplica IS NOT NULL)", name="ck_gov_procurement_file_milestones_no_aplica_con_motivo"),
    )

    op.create_table(
        "gov_procurement_file_folios",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False, index=True),
        sa.Column("file_id", sa.String(36), sa.ForeignKey("gov_procurement_files.id"), nullable=False, index=True),
        sa.Column("numero", sa.Integer, nullable=False),
        sa.Column("clase", sa.String(24), nullable=False),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=True, index=True),
        sa.Column("document_version_id", sa.String(36), sa.ForeignKey("document_versions.id"), nullable=True),
        sa.Column("act_id", sa.String(36), sa.ForeignKey("gov_acts.id"), nullable=True, index=True),
        sa.Column("etiqueta", sa.String(400), nullable=False),
        sa.Column("tipo_etiqueta", sa.String(120), nullable=False),
        sa.Column("version_numero", sa.Integer, nullable=True),
        sa.Column("fecha_documento", sa.Date, nullable=True),
        sa.Column("fecha_incorporacion", sa.Date, nullable=False),
        sa.Column("reservado", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("motivo_reserva", sa.String(500), nullable=True),
        sa.Column("milestone_id", sa.String(36), sa.ForeignKey("gov_procurement_file_milestones.id"), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        *_tiempos(),
        sa.UniqueConstraint("file_id", "numero", name="uq_gov_file_folio_numero"),
        sa.CheckConstraint(
            f"clase IN ({_en('SOLICITUD', 'AUTORIZACION_INICIO', 'PLIEGO', 'ACTOS_MOTIVADOS', 'LLAMADO_INVITACION', 'MODIFICACIONES_PLIEGO', 'ACTA_RECEPCION', 'OFERTAS', 'INFORME_RECOMENDACION', 'ADJUDICACION', 'NOTIFICACION', 'CONTRATO', 'OTRO_SELECCION', 'GARANTIAS', 'ACTAS_EJECUCION', 'MODIFICACION_CONTRATO', 'FORMULARIOS_PAGO', 'APROBACIONES_PAGO', 'PAGOS', 'FINIQUITO', 'LIBERACION_GARANTIAS', 'EVALUACION_CONTRATISTA', 'OTRO_ADMINISTRACION')})",
            name="ck_gov_procurement_file_folios_clase",
        ),
        sa.CheckConstraint("numero >= 1", name="ck_gov_procurement_file_folios_numero"),
        sa.CheckConstraint("(document_id IS NULL) <> (act_id IS NULL)", name="ck_gov_procurement_file_folios_documento_o_acto"),
        sa.CheckConstraint("reservado = false OR motivo_reserva IS NOT NULL", name="ck_gov_procurement_file_folios_reserva_con_motivo"),
    )

    op.create_table(
        "gov_procurement_file_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False, index=True),
        sa.Column("file_id", sa.String(36), sa.ForeignKey("gov_procurement_files.id"), nullable=False, index=True),
        sa.Column("secuencia", sa.Integer, nullable=False),
        sa.Column("fecha", sa.Date, nullable=False),
        sa.Column("clase", sa.String(16), nullable=False),
        sa.Column("titulo", sa.String(300), nullable=False),
        sa.Column("detalle", sa.String(2000), nullable=True),
        sa.Column("resultado", sa.String(500), nullable=True),
        sa.Column("official_id", sa.String(36), sa.ForeignKey("gov_officials.id"), nullable=True),
        sa.Column("responsable_etiqueta", sa.String(400), nullable=True),
        sa.Column("act_id", sa.String(36), sa.ForeignKey("gov_acts.id"), nullable=True),
        sa.Column("acto_etiqueta", sa.String(400), nullable=True),
        sa.Column("folio_id", sa.String(36), sa.ForeignKey("gov_procurement_file_folios.id"), nullable=True),
        sa.Column("folio_etiqueta", sa.String(400), nullable=True),
        sa.Column("milestone_id", sa.String(36), sa.ForeignKey("gov_procurement_file_milestones.id"), nullable=True),
        sa.Column("hito_etiqueta", sa.String(200), nullable=True),
        sa.Column("estado_expediente", sa.String(16), nullable=False),
        sa.Column("rectifica_id", sa.String(36), sa.ForeignKey("gov_procurement_file_events.id"), nullable=True),
        sa.Column("motivo", sa.String(1000), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        *_tiempos(),
        sa.UniqueConstraint("file_id", "secuencia", name="uq_gov_file_event_secuencia"),
        sa.CheckConstraint(
            f"clase IN ({_en('APERTURA', 'DATOS', 'RESPONSABLE', 'COMISION', 'ACTUACION', 'DECISION', 'DOCUMENTO', 'ACTO', 'HITO', 'CIERRE', 'DESCARTE')})",
            name="ck_gov_procurement_file_events_clase",
        ),
        sa.CheckConstraint("clase <> 'DECISION' OR resultado IS NOT NULL", name="ck_gov_procurement_file_events_decision_con_resultado"),
        sa.CheckConstraint("rectifica_id IS NULL OR motivo IS NOT NULL", name="ck_gov_procurement_file_events_rectificacion_con_motivo"),
    )

    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION kontrol_gov_expediente_inmutable() RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'GOV_PROCUREMENT_FILE_IMMUTABLE';
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        for tabla in ("gov_procurement_file_folios", "gov_procurement_file_events"):
            sufijo = "folios" if tabla.endswith("folios") else "events"
            op.execute(
                f"CREATE TRIGGER trg_gov_file_{sufijo}_no_update BEFORE UPDATE ON {tabla} "
                "FOR EACH ROW EXECUTE FUNCTION kontrol_gov_expediente_inmutable();"
            )
            op.execute(
                f"CREATE TRIGGER trg_gov_file_{sufijo}_no_delete BEFORE DELETE ON {tabla} "
                "FOR EACH ROW EXECUTE FUNCTION kontrol_gov_expediente_inmutable();"
            )
            op.execute(
                f"CREATE TRIGGER trg_gov_file_{sufijo}_no_truncate BEFORE TRUNCATE ON {tabla} "
                "FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_expediente_inmutable();"
            )

    bind = op.get_bind()
    _proceso_sod(bind, "DOC-02", "CTL-06", "TRE-01", "TRE-02", "CTL-10", "ORG-04", "ORG-06", "PROC-02", "PROC-03")
    _conceder_permisos(bind)


def downgrade() -> None:
    bind = op.get_bind()
    _proceso_sod(bind, "DOC-02", "CTL-06", "TRE-01", "TRE-02", "CTL-10", "ORG-04", "ORG-06", "PROC-02")

    rol = bind.execute(
        sa.text("SELECT id FROM roles WHERE code = 'FUNCIONAL_COMPLETO' AND company_id IS NULL")
    ).fetchone()
    for recurso, acciones in PERMISOS.items():
        for accion in acciones:
            permiso = bind.execute(
                sa.text("SELECT id FROM permissions WHERE resource = :r AND action = :a"),
                {"r": recurso, "a": accion},
            ).fetchone()
            if permiso is None:
                continue
            if rol is not None:
                bind.execute(
                    sa.text("DELETE FROM role_permissions WHERE role_id = :role AND permission_id = :perm"),
                    {"role": rol[0], "perm": permiso[0]},
                )
            bind.execute(
                sa.text("DELETE FROM permissions WHERE id = :id"),
                {"id": permiso[0]},
            )

    if bind.dialect.name == "postgresql":
        for tabla in ("gov_procurement_file_folios", "gov_procurement_file_events"):
            sufijo = "folios" if tabla.endswith("folios") else "events"
            op.execute(f"DROP TRIGGER IF EXISTS trg_gov_file_{sufijo}_no_update ON {tabla}")
            op.execute(f"DROP TRIGGER IF EXISTS trg_gov_file_{sufijo}_no_delete ON {tabla}")
            op.execute(f"DROP TRIGGER IF EXISTS trg_gov_file_{sufijo}_no_truncate ON {tabla}")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_expediente_inmutable()")

    op.drop_table("gov_procurement_file_events")
    op.drop_table("gov_procurement_file_folios")
    op.drop_table("gov_procurement_file_milestones")
    op.drop_table("gov_procurement_file_responsibles")
    op.drop_table("gov_procurement_files")
