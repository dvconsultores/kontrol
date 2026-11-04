"""gov ctl06 hallazgos

Crea las tablas de hallazgos, recomendaciones, acciones correctivas, avances e historia de Control Interno (CTL-06),
junto con el permiso `gobierno_hallazgos:view`, `gobierno_hallazgos:manage` y `gobierno_hallazgos:verify`.
Registra y concede estos permisos al rol protegido FUNCIONAL_COMPLETO de las instalaciones existentes.

Revision ID: 0070_gov_ctl06_hallazgos
Revises: 0069_gov_ctl04_auditoria
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa

from alembic import op

revision = "0070_gov_ctl06_hallazgos"
down_revision = "0069_gov_ctl04_auditoria"
branch_labels = None
depends_on = None

PERMISOS = {"gobierno_hallazgos": ("view", "manage", "verify")}


def _en(*valores: str) -> str:
    return ", ".join(f"'{v}'" for v in valores)


def _tiempos() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]


def _conceder_permisos(bind) -> None:
    funcional = bind.execute(sa.text(
        "SELECT id FROM roles WHERE code = 'FUNCIONAL_COMPLETO' AND company_id IS NULL LIMIT 1")).fetchone()
    for recurso, acciones in PERMISOS.items():
        for accion in acciones:
            fila = bind.execute(sa.text(
                "SELECT id FROM permissions WHERE resource = :r AND action = :a"),
                {"r": recurso, "a": accion}).fetchone()
            if fila:
                permiso = fila[0]
            else:
                permiso = str(uuid.uuid4())
                bind.execute(sa.text(
                    "INSERT INTO permissions (id, resource, action, scope_type) VALUES (:id, :r, :a, 'COMPANY')"),
                    {"id": permiso, "r": recurso, "a": accion})
            if not funcional:
                continue
            ya = bind.execute(sa.text(
                "SELECT 1 FROM role_permissions WHERE role_id = :rol AND permission_id = :p"),
                {"rol": funcional[0], "p": permiso}).fetchone()
            if not ya:
                bind.execute(sa.text(
                    "INSERT INTO role_permissions (id, role_id, permission_id) VALUES (:id, :rol, :p)"),
                    {"id": str(uuid.uuid4()), "rol": funcional[0], "p": permiso})


def upgrade() -> None:
    bind = op.get_bind()

    op.create_table(
        "gov_findings",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("titulo", sa.String(200), nullable=False),
        sa.Column("condicion", sa.Text(), nullable=False),
        sa.Column("criterio", sa.Text(), nullable=False),
        sa.Column("causa", sa.Text(), nullable=False),
        sa.Column("efecto", sa.Text(), nullable=False),
        sa.Column("riesgo", sa.String(5), nullable=False),
        sa.Column("origen", sa.String(13), nullable=False),
        sa.Column("sample_id", sa.String(36), nullable=True),
        sa.Column("origen_descripcion", sa.String(500), nullable=True),
        sa.Column("estado", sa.String(24), nullable=False, server_default="ABIERTO"),
        sa.Column("presentado_por", sa.String(36), nullable=True),
        sa.Column("presentado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verificado_por", sa.String(36), nullable=True),
        sa.Column("verificado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("nota_verificacion", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["sample_id"], ["gov_audit_samples.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "codigo", name="uq_gov_findings_company_id_codigo"),
        sa.CheckConstraint(f"riesgo IN ({_en(*('ALTO', 'MEDIO', 'BAJO'))})", name="riesgo"),
        sa.CheckConstraint(f"origen IN ({_en(*('MUESTRA', 'INDEPENDIENTE'))})", name="origen"),
        sa.CheckConstraint(f"estado IN ({_en(*('ABIERTO', 'PLAN_DE_ACCION', 'EN_REMEDIACION', 'EVIDENCIA_PRESENTADA', 'CERRADO'))})", name="estado"),
        sa.CheckConstraint(
            "(origen = 'MUESTRA' AND sample_id IS NOT NULL AND origen_descripcion IS NULL) OR "
            "(origen = 'INDEPENDIENTE' AND sample_id IS NULL AND origen_descripcion IS NOT NULL)",
            name="origen_coherente",
        ),
    )
    op.create_index("ix_gov_findings_tenant_id", "gov_findings", ["tenant_id"])
    op.create_index("ix_gov_findings_company_id", "gov_findings", ["company_id"])
    op.create_index("ix_gov_findings_sample_id", "gov_findings", ["sample_id"])

    if bind.dialect.name == "postgresql":
        op.execute("""
            CREATE OR REPLACE FUNCTION kontrol_gov_finding_no_borrable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'GOV_FINDING_NOT_DELETABLE' USING ERRCODE = 'P0001', DETAIL = TG_OP; END; $$
        """)
        op.execute("CREATE TRIGGER trg_gov_findings_no_delete BEFORE DELETE ON gov_findings FOR EACH ROW EXECUTE FUNCTION kontrol_gov_finding_no_borrable()")
        op.execute("CREATE TRIGGER trg_gov_findings_no_truncate BEFORE TRUNCATE ON gov_findings FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_finding_no_borrable()")

    op.create_table(
        "gov_finding_events",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("finding_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("audit_event_id", sa.String(36), nullable=False),
        sa.ForeignKeyConstraint(["finding_id"], ["gov_findings.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["audit_event_id"], ["audit_events.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("finding_id", "audit_event_id", name="uq_gov_finding_events_finding_id_audit_event_id"),
    )
    op.create_index("ix_gov_finding_events_finding_id", "gov_finding_events", ["finding_id"])
    op.create_index("ix_gov_finding_events_company_id", "gov_finding_events", ["company_id"])
    op.create_index("ix_gov_finding_events_audit_event_id", "gov_finding_events", ["audit_event_id"])

    if bind.dialect.name == "postgresql":
        op.execute("""
            CREATE OR REPLACE FUNCTION kontrol_gov_finding_registros_inmutables() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'GOV_FINDING_RECORD_IMMUTABLE' USING ERRCODE = 'P0001', DETAIL = TG_OP; END; $$
        """)
        op.execute("CREATE TRIGGER trg_gov_finding_events_no_update BEFORE UPDATE ON gov_finding_events FOR EACH ROW EXECUTE FUNCTION kontrol_gov_finding_registros_inmutables()")
        op.execute("CREATE TRIGGER trg_gov_finding_events_no_delete BEFORE DELETE ON gov_finding_events FOR EACH ROW EXECUTE FUNCTION kontrol_gov_finding_registros_inmutables()")
        op.execute("CREATE TRIGGER trg_gov_finding_events_no_truncate BEFORE TRUNCATE ON gov_finding_events FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_finding_registros_inmutables()")

    op.create_table(
        "gov_finding_recommendations",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("finding_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["finding_id"], ["gov_findings.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("finding_id", "orden", name="uq_gov_finding_recommendations_finding_id_orden"),
        sa.CheckConstraint("orden >= 1", name="orden"),
    )
    op.create_index("ix_gov_finding_recommendations_finding_id", "gov_finding_recommendations", ["finding_id"])
    op.create_index("ix_gov_finding_recommendations_company_id", "gov_finding_recommendations", ["company_id"])

    if bind.dialect.name == "postgresql":
        op.execute("CREATE TRIGGER trg_gov_finding_recommendations_no_update BEFORE UPDATE ON gov_finding_recommendations FOR EACH ROW EXECUTE FUNCTION kontrol_gov_finding_registros_inmutables()")
        op.execute("CREATE TRIGGER trg_gov_finding_recommendations_no_delete BEFORE DELETE ON gov_finding_recommendations FOR EACH ROW EXECUTE FUNCTION kontrol_gov_finding_registros_inmutables()")
        op.execute("CREATE TRIGGER trg_gov_finding_recommendations_no_truncate BEFORE TRUNCATE ON gov_finding_recommendations FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_finding_registros_inmutables()")

    op.create_table(
        "gov_corrective_actions",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("finding_id", sa.String(36), nullable=False),
        sa.Column("recommendation_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("position_id", sa.String(36), nullable=False),
        sa.Column("cargo_codigo", sa.String(30), nullable=False),
        sa.Column("cargo_denominacion", sa.String(200), nullable=False),
        sa.Column("unidad_id", sa.String(36), nullable=False),
        sa.Column("unidad_nombre", sa.String(200), nullable=False),
        sa.Column("ejercicio", sa.Integer(), nullable=False),
        sa.Column("fecha_objetivo", sa.Date(), nullable=False),
        sa.Column("porcentaje", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estado", sa.String(12), nullable=False, server_default="PENDIENTE"),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["finding_id"], ["gov_findings.id"]),
        sa.ForeignKeyConstraint(["recommendation_id"], ["gov_finding_recommendations.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["position_id"], ["gov_positions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("finding_id", "orden", name="uq_gov_corrective_actions_finding_id_orden"),
        sa.CheckConstraint("orden >= 1", name="orden"),
        sa.CheckConstraint("porcentaje >= 0 AND porcentaje <= 100", name="porcentaje"),
        sa.CheckConstraint(f"estado IN ({_en(*('PENDIENTE', 'EN_CURSO', 'COMPLETADA'))})", name="estado"),
    )
    op.create_index("ix_gov_corrective_actions_finding_id", "gov_corrective_actions", ["finding_id"])
    op.create_index("ix_gov_corrective_actions_recommendation_id", "gov_corrective_actions", ["recommendation_id"])
    op.create_index("ix_gov_corrective_actions_company_id", "gov_corrective_actions", ["company_id"])
    op.create_index("ix_gov_corrective_actions_position_id", "gov_corrective_actions", ["position_id"])

    if bind.dialect.name == "postgresql":
        op.execute("CREATE TRIGGER trg_gov_corrective_actions_no_delete BEFORE DELETE ON gov_corrective_actions FOR EACH ROW EXECUTE FUNCTION kontrol_gov_finding_no_borrable()")
        op.execute("CREATE TRIGGER trg_gov_corrective_actions_no_truncate BEFORE TRUNCATE ON gov_corrective_actions FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_finding_no_borrable()")

    op.create_table(
        "gov_corrective_action_progress",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("action_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("nota", sa.Text(), nullable=False),
        sa.Column("porcentaje", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["action_id"], ["gov_corrective_actions.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("porcentaje >= 0 AND porcentaje <= 100", name="porcentaje"),
    )
    op.create_index("ix_gov_corrective_action_progress_action_id", "gov_corrective_action_progress", ["action_id"])
    op.create_index("ix_gov_corrective_action_progress_company_id", "gov_corrective_action_progress", ["company_id"])
    op.create_index("ix_gov_corrective_action_progress_document_id", "gov_corrective_action_progress", ["document_id"])

    if bind.dialect.name == "postgresql":
        op.execute("CREATE TRIGGER trg_gov_corrective_action_progress_no_update BEFORE UPDATE ON gov_corrective_action_progress FOR EACH ROW EXECUTE FUNCTION kontrol_gov_finding_registros_inmutables()")
        op.execute("CREATE TRIGGER trg_gov_corrective_action_progress_no_delete BEFORE DELETE ON gov_corrective_action_progress FOR EACH ROW EXECUTE FUNCTION kontrol_gov_finding_registros_inmutables()")
        op.execute("CREATE TRIGGER trg_gov_corrective_action_progress_no_truncate BEFORE TRUNCATE ON gov_corrective_action_progress FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_finding_registros_inmutables()")

    op.create_table(
        "gov_finding_history",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("finding_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("tipo", sa.String(16), nullable=False),
        sa.Column("estado_desde", sa.String(24), nullable=True),
        sa.Column("estado_hasta", sa.String(24), nullable=True),
        sa.Column("detalle", sa.JSON(), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["finding_id"], ["gov_findings.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(f"tipo IN ({_en(*('CREADO', 'RECOMENDACION', 'ACCION', 'PLAN', 'EJECUCION', 'AVANCE', 'PRESENTADO', 'VERIFICADO', 'DEVUELTO'))})", name="tipo"),
    )
    op.create_index("ix_gov_finding_history_finding_id", "gov_finding_history", ["finding_id"])
    op.create_index("ix_gov_finding_history_company_id", "gov_finding_history", ["company_id"])

    if bind.dialect.name == "postgresql":
        op.execute("CREATE TRIGGER trg_gov_finding_history_no_update BEFORE UPDATE ON gov_finding_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_finding_registros_inmutables()")
        op.execute("CREATE TRIGGER trg_gov_finding_history_no_delete BEFORE DELETE ON gov_finding_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_finding_registros_inmutables()")
        op.execute("CREATE TRIGGER trg_gov_finding_history_no_truncate BEFORE TRUNCATE ON gov_finding_history FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_finding_registros_inmutables()")

    _conceder_permisos(bind)


def downgrade() -> None:
    bind = op.get_bind()

    for recurso, acciones in PERMISOS.items():
        for accion in acciones:
            permiso = bind.execute(sa.text(
                "SELECT id FROM permissions WHERE resource = :r AND action = :a"),
                {"r": recurso, "a": accion}).fetchone()
            if not permiso:
                continue
            bind.execute(sa.text(
                "DELETE FROM role_permissions WHERE permission_id = :p"),
                {"p": permiso[0]})
            bind.execute(sa.text(
                "DELETE FROM permissions WHERE id = :p"),
                {"p": permiso[0]})

    if bind.dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_gov_finding_history_no_update ON gov_finding_history")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_finding_history_no_delete ON gov_finding_history")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_finding_history_no_truncate ON gov_finding_history")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_corrective_action_progress_no_update ON gov_corrective_action_progress")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_corrective_action_progress_no_delete ON gov_corrective_action_progress")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_corrective_action_progress_no_truncate ON gov_corrective_action_progress")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_corrective_actions_no_delete ON gov_corrective_actions")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_corrective_actions_no_truncate ON gov_corrective_actions")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_finding_recommendations_no_update ON gov_finding_recommendations")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_finding_recommendations_no_delete ON gov_finding_recommendations")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_finding_recommendations_no_truncate ON gov_finding_recommendations")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_finding_events_no_update ON gov_finding_events")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_finding_events_no_delete ON gov_finding_events")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_finding_events_no_truncate ON gov_finding_events")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_findings_no_delete ON gov_findings")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_findings_no_truncate ON gov_findings")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_finding_registros_inmutables()")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_finding_no_borrable()")

    op.drop_index("ix_gov_finding_history_company_id", table_name="gov_finding_history")
    op.drop_index("ix_gov_finding_history_finding_id", table_name="gov_finding_history")
    op.drop_table("gov_finding_history")

    op.drop_index("ix_gov_corrective_action_progress_document_id", table_name="gov_corrective_action_progress")
    op.drop_index("ix_gov_corrective_action_progress_company_id", table_name="gov_corrective_action_progress")
    op.drop_index("ix_gov_corrective_action_progress_action_id", table_name="gov_corrective_action_progress")
    op.drop_table("gov_corrective_action_progress")

    op.drop_index("ix_gov_corrective_actions_position_id", table_name="gov_corrective_actions")
    op.drop_index("ix_gov_corrective_actions_company_id", table_name="gov_corrective_actions")
    op.drop_index("ix_gov_corrective_actions_recommendation_id", table_name="gov_corrective_actions")
    op.drop_index("ix_gov_corrective_actions_finding_id", table_name="gov_corrective_actions")
    op.drop_table("gov_corrective_actions")

    op.drop_index("ix_gov_finding_recommendations_company_id", table_name="gov_finding_recommendations")
    op.drop_index("ix_gov_finding_recommendations_finding_id", table_name="gov_finding_recommendations")
    op.drop_table("gov_finding_recommendations")

    op.drop_index("ix_gov_finding_events_audit_event_id", table_name="gov_finding_events")
    op.drop_index("ix_gov_finding_events_company_id", table_name="gov_finding_events")
    op.drop_index("ix_gov_finding_events_finding_id", table_name="gov_finding_events")
    op.drop_table("gov_finding_events")

    op.drop_index("ix_gov_findings_sample_id", table_name="gov_findings")
    op.drop_index("ix_gov_findings_company_id", table_name="gov_findings")
    op.drop_index("ix_gov_findings_tenant_id", table_name="gov_findings")
    op.drop_table("gov_findings")
