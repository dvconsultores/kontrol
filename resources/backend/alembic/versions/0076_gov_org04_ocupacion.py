"""gov org04 ocupacion

Crea funcionarios, asignaciones de cargos y su historia (ORG-04, GOV-ORG-004, GOV-ORG-009), registra `gobierno_ocupacion` y añade ORG-04 a los procesos de SoD.

Revision ID: 0076_gov_org04_ocupacion
Revises: 0075_gov_ctl10_cierres
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa

from alembic import op

revision = "0076_gov_org04_ocupacion"
down_revision = "0075_gov_ctl10_cierres"
branch_labels = None
depends_on = None

PERMISOS = {"gobierno_ocupacion": ("view", "manage", "activate", "revoke")}


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


def _proceso_sod(bind, *procesos: str) -> None:
    valores = _en(*procesos)
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE gov_sod_rules DROP CONSTRAINT ck_gov_sod_rules_proceso")
        op.execute(f"ALTER TABLE gov_sod_rules ADD CONSTRAINT ck_gov_sod_rules_proceso CHECK (proceso IN ({valores}))")
        return
    with op.batch_alter_table("gov_sod_rules") as batch:
        batch.drop_constraint("ck_gov_sod_rules_proceso", type_="check")
        batch.create_check_constraint("proceso", f"proceso IN ({valores})")


def upgrade() -> None:
    op.create_table(
        "gov_officials",
        sa.Column("id", sa.String(36), primary_key=True),
        *_tiempos(),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("version", sa.BigInteger, nullable=False, server_default="1"),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("tipo_documento", sa.String(1), nullable=False),
        sa.Column("numero_documento", sa.String(20), nullable=False),
        sa.Column("estado", sa.String(16), nullable=False, server_default="ACTIVO"),
        sa.UniqueConstraint("company_id", "codigo", name="uq_gov_officials_company_id_codigo"),
        sa.UniqueConstraint("company_id", "tipo_documento", "numero_documento", name="uq_gov_officials_documento"),
        sa.CheckConstraint("estado IN ('ACTIVO', 'INACTIVO')", name="ck_gov_officials_estado"),
        sa.CheckConstraint("tipo_documento IN ('V', 'E', 'P')", name="ck_gov_officials_tipo_documento"),
        sa.CheckConstraint("version >= 1", name="ck_gov_officials_version"),
    )
    op.create_index("ix_gov_officials_company_id", "gov_officials", ["company_id"])

    op.create_table(
        "gov_official_history",
        sa.Column("id", sa.String(36), primary_key=True),
        *_tiempos(),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("official_id", sa.String(36), sa.ForeignKey("gov_officials.id"), nullable=False),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("tipo", sa.String(16), nullable=False),
        sa.Column("detalle", sa.JSON, nullable=True),
        sa.CheckConstraint("tipo IN ('CREADO', 'EDITADO')", name="ck_gov_official_history_tipo"),
    )
    op.create_index("ix_gov_official_history_official_id", "gov_official_history", ["official_id"])
    op.create_index("ix_gov_official_history_company_id", "gov_official_history", ["company_id"])

    op.create_table(
        "gov_assignments",
        sa.Column("id", sa.String(36), primary_key=True),
        *_tiempos(),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("version", sa.BigInteger, nullable=False, server_default="1"),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("official_id", sa.String(36), sa.ForeignKey("gov_officials.id"), nullable=False),
        sa.Column("position_id", sa.String(36), sa.ForeignKey("gov_positions.id"), nullable=False),
        sa.Column("figura", sa.String(24), nullable=False),
        sa.Column("grupo", sa.String(16), nullable=False),
        sa.Column("cargo_origen_id", sa.String(36), sa.ForeignKey("gov_positions.id"), nullable=True),
        sa.Column("act_id", sa.String(36), sa.ForeignKey("gov_acts.id"), nullable=False),
        sa.Column("desde", sa.Date, nullable=False),
        sa.Column("hasta", sa.Date, nullable=True),
        sa.Column("fin_efectivo", sa.Date, nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="BORRADOR"),
        sa.Column("fundamento", sa.String(500), nullable=False),
        sa.Column("rendicion", sa.String(500), nullable=True),
        sa.Column("maxima_autoridad", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("autorizacion_concejo", sa.String(200), nullable=True),
        sa.Column("declara_delegable", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("revocation_act_id", sa.String(36), sa.ForeignKey("gov_acts.id"), nullable=True),
        sa.Column("motivo_fin", sa.String(500), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_by", sa.String(36), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_by", sa.String(36), nullable=True),
        sa.UniqueConstraint("company_id", "codigo", name="uq_gov_assignments_company_id_codigo"),
        sa.CheckConstraint("figura IN ('TITULAR', 'ENCARGADURIA', 'SUPLENCIA', 'COMISION_SERVICIO', 'DELEGACION_ATRIBUCIONES', 'DELEGACION_FIRMA')", name="ck_gov_assignments_figura"),
        sa.CheckConstraint("grupo IN ('TITULARIDAD', 'TEMPORAL', 'DELEGACION')", name="ck_gov_assignments_grupo"),
        sa.CheckConstraint("status IN ('BORRADOR', 'ACTIVO', 'REVOCADO', 'FINALIZADO', 'DESCARTADO')", name="ck_gov_assignments_status"),
        sa.CheckConstraint("version >= 1", name="ck_gov_assignments_version"),
        sa.CheckConstraint(
            "(figura = 'TITULAR' AND grupo = 'TITULARIDAD') OR "
            "(figura IN ('ENCARGADURIA','SUPLENCIA','COMISION_SERVICIO') AND grupo = 'TEMPORAL') OR "
            "(figura IN ('DELEGACION_ATRIBUCIONES','DELEGACION_FIRMA') AND grupo = 'DELEGACION')",
            name="ck_gov_assignments_grupo_de_figura",
        ),
        sa.CheckConstraint("hasta IS NULL OR hasta >= desde", name="ck_gov_assignments_vigencia"),
        sa.CheckConstraint("fin_efectivo IS NULL OR fin_efectivo >= desde", name="ck_gov_assignments_fin_tras_inicio"),
        sa.CheckConstraint("figura NOT IN ('SUPLENCIA','COMISION_SERVICIO') OR hasta IS NOT NULL", name="ck_gov_assignments_temporal_con_fin"),
        sa.CheckConstraint("grupo = 'TITULARIDAD' OR figura = 'ENCARGADURIA' OR cargo_origen_id IS NOT NULL", name="ck_gov_assignments_origen_requerido"),
        sa.CheckConstraint("grupo <> 'DELEGACION' OR (rendicion IS NOT NULL AND declara_delegable = true)", name="ck_gov_assignments_delegacion_completa"),
        sa.CheckConstraint("status NOT IN ('REVOCADO') OR (revocation_act_id IS NOT NULL AND fin_efectivo IS NOT NULL)", name="ck_gov_assignments_revocada_con_acto"),
        sa.CheckConstraint("status <> 'FINALIZADO' OR (fin_efectivo IS NOT NULL AND motivo_fin IS NOT NULL)", name="ck_gov_assignments_finalizada_con_motivo"),
        sa.CheckConstraint("status IN ('BORRADOR','DESCARTADO') OR activated_at IS NOT NULL", name="ck_gov_assignments_activada_fechada"),
    )
    op.create_index("ix_gov_assignments_company_id", "gov_assignments", ["company_id"])
    op.create_index("ix_gov_assignments_official_id", "gov_assignments", ["official_id"])
    op.create_index("ix_gov_assignments_position_id", "gov_assignments", ["position_id"])
    op.create_index("ix_gov_assignments_act_id", "gov_assignments", ["act_id"])

    op.create_table(
        "gov_assignment_competencies",
        sa.Column("id", sa.String(36), primary_key=True),
        *_tiempos(),
        sa.Column("assignment_id", sa.String(36), sa.ForeignKey("gov_assignments.id"), nullable=False),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("subject", sa.String(16), nullable=False),
        sa.Column("limit_type", sa.String(16), nullable=False),
        sa.Column("limit_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("limit_currency", sa.String(3), nullable=True),
        sa.UniqueConstraint("assignment_id", "action", "subject", name="uq_gov_assignment_competencies_assignment_id_action_subject"),
        sa.CheckConstraint(
            "action IN ('SOLICITAR', 'COMPROMETER', 'CAUSAR', 'ORDENAR_PAGO', 'PAGAR', 'REGISTRAR', 'CUSTODIAR', 'APROBAR', 'AUDITAR', 'FIRMAR')",
            name="ck_gov_assignment_competencies_action",
        ),
        sa.CheckConstraint(
            "subject IN ('PRESUPUESTO', 'CONTRATACIONES', 'TESORERIA', 'CONTABILIDAD', 'BIENES', 'EXPEDIENTE')",
            name="ck_gov_assignment_competencies_subject",
        ),
        sa.CheckConstraint(
            "limit_type IN ('SIN_LIMITE', 'MONTO')",
            name="ck_gov_assignment_competencies_limit_type",
        ),
    )
    op.create_index("ix_gov_assignment_competencies_assignment_id", "gov_assignment_competencies", ["assignment_id"])
    op.create_index("ix_gov_assignment_competencies_company_id", "gov_assignment_competencies", ["company_id"])

    op.create_table(
        "gov_assignment_history",
        sa.Column("id", sa.String(36), primary_key=True),
        *_tiempos(),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("assignment_id", sa.String(36), sa.ForeignKey("gov_assignments.id"), nullable=False),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("tipo", sa.String(16), nullable=False),
        sa.Column("detalle", sa.JSON, nullable=True),
        sa.CheckConstraint("tipo IN ('CREADA', 'EDITADA', 'ACTIVADA', 'DESCARTADA', 'REVOCADA', 'FINALIZADA', 'AVOCADA')", name="ck_gov_assignment_history_tipo"),
    )
    op.create_index("ix_gov_assignment_history_assignment_id", "gov_assignment_history", ["assignment_id"])
    op.create_index("ix_gov_assignment_history_company_id", "gov_assignment_history", ["company_id"])

    if op.get_bind().dialect.name == "postgresql":
        op.execute("CREATE OR REPLACE FUNCTION kontrol_gov_funcionario_historia_inmutable() RETURNS TRIGGER AS $$ BEGIN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_OFFICIAL_HISTORY_IMMUTABLE', DETAIL = TG_OP; END; $$ LANGUAGE plpgsql")
        op.execute("CREATE TRIGGER trg_gov_official_history_no_update BEFORE UPDATE ON gov_official_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_funcionario_historia_inmutable()")
        op.execute("CREATE TRIGGER trg_gov_official_history_no_delete BEFORE DELETE ON gov_official_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_funcionario_historia_inmutable()")
        op.execute("CREATE TRIGGER trg_gov_official_history_no_truncate BEFORE TRUNCATE ON gov_official_history FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_funcionario_historia_inmutable()")

        op.execute("CREATE OR REPLACE FUNCTION kontrol_gov_funcionario_no_borrable() RETURNS TRIGGER AS $$ BEGIN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_OFFICIAL_NOT_DELETABLE', DETAIL = TG_OP; END; $$ LANGUAGE plpgsql")
        op.execute("CREATE TRIGGER trg_gov_officials_no_delete BEFORE DELETE ON gov_officials FOR EACH ROW EXECUTE FUNCTION kontrol_gov_funcionario_no_borrable()")
        op.execute("CREATE TRIGGER trg_gov_officials_no_truncate BEFORE TRUNCATE ON gov_officials FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_funcionario_no_borrable()")

        op.execute("CREATE OR REPLACE FUNCTION kontrol_gov_asignacion_historia_inmutable() RETURNS TRIGGER AS $$ BEGIN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_ASSIGNMENT_HISTORY_IMMUTABLE', DETAIL = TG_OP; END; $$ LANGUAGE plpgsql")
        op.execute("CREATE TRIGGER trg_gov_assignment_history_no_update BEFORE UPDATE ON gov_assignment_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_asignacion_historia_inmutable()")
        op.execute("CREATE TRIGGER trg_gov_assignment_history_no_delete BEFORE DELETE ON gov_assignment_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_asignacion_historia_inmutable()")
        op.execute("CREATE TRIGGER trg_gov_assignment_history_no_truncate BEFORE TRUNCATE ON gov_assignment_history FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_asignacion_historia_inmutable()")

        op.execute("CREATE OR REPLACE FUNCTION kontrol_gov_asignacion_no_borrable() RETURNS TRIGGER AS $$ BEGIN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_ASSIGNMENT_NOT_DELETABLE', DETAIL = TG_OP; END; $$ LANGUAGE plpgsql")
        op.execute("CREATE TRIGGER trg_gov_assignments_no_delete BEFORE DELETE ON gov_assignments FOR EACH ROW EXECUTE FUNCTION kontrol_gov_asignacion_no_borrable()")
        op.execute("CREATE TRIGGER trg_gov_assignments_no_truncate BEFORE TRUNCATE ON gov_assignments FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_asignacion_no_borrable()")

        op.execute("CREATE OR REPLACE FUNCTION kontrol_gov_asignacion_no_editable() RETURNS TRIGGER AS $$ BEGIN IF OLD.status <> 'BORRADOR' AND (NEW.official_id IS DISTINCT FROM OLD.official_id OR NEW.position_id IS DISTINCT FROM OLD.position_id OR NEW.figura IS DISTINCT FROM OLD.figura OR NEW.grupo IS DISTINCT FROM OLD.grupo OR NEW.cargo_origen_id IS DISTINCT FROM OLD.cargo_origen_id OR NEW.act_id IS DISTINCT FROM OLD.act_id OR NEW.desde IS DISTINCT FROM OLD.desde OR NEW.hasta IS DISTINCT FROM OLD.hasta OR NEW.fundamento IS DISTINCT FROM OLD.fundamento OR NEW.rendicion IS DISTINCT FROM OLD.rendicion OR NEW.company_id IS DISTINCT FROM OLD.company_id) THEN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_ASSIGNMENT_NOT_EDITABLE'; END IF; IF OLD.status IN ('REVOCADO','FINALIZADO','DESCARTADO') AND (NEW.status IS DISTINCT FROM OLD.status OR NEW.fin_efectivo IS DISTINCT FROM OLD.fin_efectivo) THEN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_ASSIGNMENT_NOT_EDITABLE'; END IF; RETURN NEW; END; $$ LANGUAGE plpgsql")
        op.execute("CREATE TRIGGER trg_gov_assignments_no_editable BEFORE UPDATE ON gov_assignments FOR EACH ROW EXECUTE FUNCTION kontrol_gov_asignacion_no_editable()")

        op.execute("CREATE OR REPLACE FUNCTION kontrol_gov_asignacion_competencia_inmutable() RETURNS TRIGGER AS $$ DECLARE v_status VARCHAR(16); BEGIN IF TG_OP = 'INSERT' THEN SELECT status INTO v_status FROM gov_assignments WHERE id = NEW.assignment_id; ELSIF TG_OP = 'UPDATE' THEN SELECT status INTO v_status FROM gov_assignments WHERE id = OLD.assignment_id; ELSE SELECT status INTO v_status FROM gov_assignments WHERE id = OLD.assignment_id; END IF; IF v_status IS DISTINCT FROM 'BORRADOR' THEN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_ASSIGNMENT_COMPETENCY_IMMUTABLE'; END IF; IF TG_OP = 'DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF; END; $$ LANGUAGE plpgsql")
        op.execute("CREATE TRIGGER trg_gov_assignment_competencies_immutable BEFORE INSERT OR UPDATE OR DELETE ON gov_assignment_competencies FOR EACH ROW EXECUTE FUNCTION kontrol_gov_asignacion_competencia_inmutable()")

        op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
        op.execute("ALTER TABLE gov_assignments ADD CONSTRAINT ex_gov_assignments_ocupacion EXCLUDE USING gist (position_id WITH =, grupo WITH =, daterange(desde, COALESCE(fin_efectivo, hasta), '[]') WITH &&) WHERE (status = 'ACTIVO' AND grupo IN ('TITULARIDAD', 'TEMPORAL'))")
        op.execute("ALTER TABLE gov_assignments ADD CONSTRAINT ex_gov_assignments_delegacion EXCLUDE USING gist (position_id WITH =, official_id WITH =, daterange(desde, COALESCE(fin_efectivo, hasta), '[]') WITH &&) WHERE (status = 'ACTIVO' AND grupo = 'DELEGACION')")

    _proceso_sod(op.get_bind(), "DOC-02", "CTL-06", "TRE-01", "TRE-02", "CTL-10", "ORG-04")
    _conceder_permisos(op.get_bind())


def downgrade() -> None:
    _proceso_sod(op.get_bind(), "DOC-02", "CTL-06", "TRE-01", "TRE-02", "CTL-10")

    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_gov_official_history_no_update ON gov_official_history")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_official_history_no_delete ON gov_official_history")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_official_history_no_truncate ON gov_official_history")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_officials_no_delete ON gov_officials")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_officials_no_truncate ON gov_officials")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_assignment_history_no_update ON gov_assignment_history")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_assignment_history_no_delete ON gov_assignment_history")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_assignment_history_no_truncate ON gov_assignment_history")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_assignments_no_delete ON gov_assignments")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_assignments_no_truncate ON gov_assignments")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_assignments_no_editable ON gov_assignments")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_assignment_competencies_immutable ON gov_assignment_competencies")
        op.execute("ALTER TABLE gov_assignments DROP CONSTRAINT IF EXISTS ex_gov_assignments_ocupacion")
        op.execute("ALTER TABLE gov_assignments DROP CONSTRAINT IF EXISTS ex_gov_assignments_delegacion")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_funcionario_historia_inmutable()")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_funcionario_no_borrable()")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_asignacion_historia_inmutable()")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_asignacion_no_borrable()")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_asignacion_no_editable()")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_asignacion_competencia_inmutable()")

    bind = op.get_bind()
    permiso_ids = bind.execute(sa.text(
        "SELECT id FROM permissions WHERE resource = 'gobierno_ocupacion'")).fetchall()
    for fila in permiso_ids:
        bind.execute(sa.text(
            "DELETE FROM role_permissions WHERE permission_id = :p"),
            {"p": fila[0]})
    bind.execute(sa.text(
        "DELETE FROM permissions WHERE resource = 'gobierno_ocupacion'"))

    op.drop_table("gov_assignment_history")
    op.drop_table("gov_assignment_competencies")
    op.drop_table("gov_assignments")
    op.drop_table("gov_official_history")
    op.drop_table("gov_officials")
