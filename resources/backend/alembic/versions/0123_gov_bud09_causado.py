"""BUD-09: causado / devengado presupuestario contra compromisos vigentes."""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "0123_gov_bud09_causado"
down_revision = "0122_gov_cnt07_terminacion"
branch_labels = None
depends_on = None

PERMISOS = {"gobierno_presupuesto": ("cause", "cause_policy")}
PROCESOS_SOD = ("DOC-02", "CTL-06", "TRE-01", "TRE-02", "CTL-10", "ORG-04", "ORG-06", "PROC-02", "PROC-03")

ESTADOS_POLITICA_CAUSADO = ("BORRADOR", "VIGENTE", "CERRADA")
DISPARADORES_CAUSADO = ("RECEIPT_ACCEPTED", "VALUATION_APPROVED", "DELIVERY_ACCEPTED", "INVOICE_CONFORMED", "DOCUMENTARY")
TIPOS_REGLA_CAUSADO = ("INSTITUTIONAL_POLICY", "LEGAL_MANDATORY")
ETAPAS_DOCUMENTO_CAUSADO = ("PREPARACION", "FORMALIZACION")
ESTADOS_CAUSADO = ("BORRADOR", "FORMALIZADO", "ANULADO")
TIPOS_EVIDENCIA_CAUSADO = ("CONTRACT_RECEIPT", "CONTRACT_VALUATION", "CONTRACT_DELIVERY", "CONTRACT_INVOICE", "DOCUMENT")

ACCIONES_COMPETENCIA = ("SOLICITAR", "COMPROMETER", "CAUSAR", "ORDENAR_PAGO", "PAGAR", "REGISTRAR", "CUSTODIAR", "APROBAR", "AUDITAR", "FIRMAR")
MATERIAS_COMPETENCIA = ("PRESUPUESTO", "CONTRATACIONES", "TESORERIA", "CONTABILIDAD", "BIENES", "EXPEDIENTE")
TIPOS_FUENTE_CAUSADO = ("CONTRACT", "PROCUREMENT_FILE", "OTHER")


def _en(*valores: str) -> str:
    return ", ".join(f"'{v}'" for v in valores)


def _tiempos() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]


def _conceder_permisos(bind) -> None:
    funcional = bind.execute(
        sa.text("SELECT id FROM roles WHERE code = 'FUNCIONAL_COMPLETO' AND company_id IS NULL LIMIT 1")
    ).fetchone()
    for recurso, acciones in PERMISOS.items():
        for accion in acciones:
            fila = bind.execute(
                sa.text("SELECT id FROM permissions WHERE resource = :r AND action = :a"),
                {"r": recurso, "a": accion},
            ).fetchone()
            if fila:
                permiso = fila[0]
            else:
                permiso = str(uuid.uuid4())
                bind.execute(
                    sa.text(
                        "INSERT INTO permissions (id, resource, action, scope_type) VALUES (:id, :r, :a, 'COMPANY')"
                    ),
                    {"id": permiso, "r": recurso, "a": accion},
                )
            if not funcional:
                continue
            ya = bind.execute(
                sa.text(
                    "SELECT 1 FROM role_permissions WHERE role_id = :rol AND permission_id = :p"
                ),
                {"rol": funcional[0], "p": permiso},
            ).fetchone()
            if not ya:
                bind.execute(
                    sa.text(
                        "INSERT INTO role_permissions (id, role_id, permission_id) VALUES (:id, :rol, :p)"
                    ),
                    {"id": str(uuid.uuid4()), "rol": funcional[0], "p": permiso},
                )


def _proceso_sod(bind, *procesos: str) -> None:
    """SQL directo en PostgreSQL: `create_check_constraint` duplicaría el prefijo de la convención de nombres."""
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
        "gov_budget_cause_settings",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("patron", sa.String(60), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", name="uq_gov_budget_cause_settings_company_id"),
        sa.CheckConstraint("length(patron) BETWEEN 9 AND 60", name="patron"),
    )
    op.create_index("ix_gov_budget_cause_settings_company_id", "gov_budget_cause_settings", ["company_id"])

    op.create_table(
        "gov_budget_causing_policies",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("tipo_gasto", sa.String(40), nullable=False),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("disparador", sa.String(24), nullable=False),
        sa.Column("requiere_recepcion", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("requiere_valuacion", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("requiere_conformidad", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("competencia_accion", sa.String(16), nullable=False, server_default="CAUSAR"),
        sa.Column("competencia_materia", sa.String(16), nullable=False, server_default="PRESUPUESTO"),
        sa.Column("vigente_desde", sa.Date(), nullable=False),
        sa.Column("vigente_hasta", sa.Date(), nullable=True),
        sa.Column("fundamento", sa.String(2000), nullable=True),
        sa.Column("act_id", sa.String(36), nullable=True),
        sa.Column("tipo_regla", sa.String(24), nullable=False, server_default="INSTITUTIONAL_POLICY"),
        sa.Column("estado", sa.String(10), nullable=False, server_default="BORRADOR"),
        sa.Column("activada_por", sa.String(36), nullable=True),
        sa.Column("activada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cerrada_por", sa.String(36), nullable=True),
        sa.Column("cerrada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("motivo_cierre", sa.String(500), nullable=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["act_id"], ["gov_acts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "codigo", name="uq_gov_budget_causing_policies_company_id_codigo"),
        sa.CheckConstraint(f"estado IN ({_en(*ESTADOS_POLITICA_CAUSADO)})", name="estado"),
        sa.CheckConstraint(f"disparador IN ({_en(*DISPARADORES_CAUSADO)})", name="disparador"),
        sa.CheckConstraint(f"tipo_regla IN ({_en(*TIPOS_REGLA_CAUSADO)})", name="tipo_regla"),
        sa.CheckConstraint(f"competencia_accion IN ({_en(*ACCIONES_COMPETENCIA)})", name="competencia_accion"),
        sa.CheckConstraint(f"competencia_materia IN ({_en(*MATERIAS_COMPETENCIA)})", name="competencia_materia"),
        sa.CheckConstraint("vigente_hasta IS NULL OR vigente_hasta >= vigente_desde", name="vigencia"),
        sa.CheckConstraint("estado = 'BORRADOR' OR fundamento IS NOT NULL", name="fundamento"),
    )
    op.create_index("ix_gov_budget_causing_policies_company_id", "gov_budget_causing_policies", ["company_id"])

    op.create_table(
        "gov_budget_causing_policy_documents",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("policy_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("document_type_id", sa.String(36), nullable=False),
        sa.Column("obligatorio", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("etapa", sa.String(14), nullable=False),
        sa.Column("condicion", sa.String(300), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["policy_id"], ["gov_budget_causing_policies.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["document_type_id"], ["document_types.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("policy_id", "document_type_id", name="uq_gov_budget_causing_policy_docs_type"),
        sa.CheckConstraint(f"etapa IN ({_en(*ETAPAS_DOCUMENTO_CAUSADO)})", name="etapa"),
    )
    op.create_index("ix_gov_budget_causing_policy_documents_policy_id", "gov_budget_causing_policy_documents", ["policy_id"])
    op.create_index("ix_gov_budget_causing_policy_documents_company_id", "gov_budget_causing_policy_documents", ["company_id"])

    op.create_table(
        "gov_budget_causing_policy_history",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("policy_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("evento", sa.String(32), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("instantanea", sa.JSON(), nullable=False),
        sa.Column("actor_id", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["policy_id"], ["gov_budget_causing_policies.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_gov_budget_causing_policy_history_policy_id", "gov_budget_causing_policy_history", ["policy_id"])
    op.create_index("ix_gov_budget_causing_policy_history_company_id", "gov_budget_causing_policy_history", ["company_id"])

    op.create_table(
        "gov_budget_causes",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("year_id", sa.String(36), nullable=False),
        sa.Column("commitment_id", sa.String(36), nullable=False),
        sa.Column("policy_id", sa.String(36), nullable=False),
        sa.Column("policy_version", sa.Integer(), nullable=False),
        sa.Column("estado", sa.String(12), nullable=False, server_default="BORRADOR"),
        sa.Column("numero", sa.Integer(), nullable=True),
        sa.Column("codigo", sa.String(60), nullable=True),
        sa.Column("fecha_efectiva", sa.Date(), nullable=False),
        sa.Column("moneda", sa.String(3), nullable=False),
        sa.Column("monto", sa.Numeric(18, 2), nullable=False),
        sa.Column("concepto", sa.String(500), nullable=False),
        sa.Column("beneficiario", sa.String(200), nullable=True),
        sa.Column("source_resource_type", sa.String(20), nullable=True),
        sa.Column("source_resource_id", sa.String(36), nullable=True),
        sa.Column("autoridad_cargo_id", sa.String(36), nullable=True),
        sa.Column("autoridad_cargo_codigo", sa.String(30), nullable=True),
        sa.Column("autoridad_cargo_nombre", sa.String(200), nullable=True),
        sa.Column("autoridad_unidad", sa.String(250), nullable=True),
        sa.Column("autoridad_funcionario_id", sa.String(36), nullable=True),
        sa.Column("autoridad_funcionario_nombre", sa.String(200), nullable=True),
        sa.Column("formalizado_por", sa.String(36), nullable=True),
        sa.Column("formalizado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("snapshot", sa.JSON(), nullable=True),
        sa.Column("huella", sa.String(64), nullable=True),
        sa.Column("anulado_por", sa.String(36), nullable=True),
        sa.Column("anulado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("motivo_anulacion", sa.String(500), nullable=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["year_id"], ["gov_budget_years.id"]),
        sa.ForeignKeyConstraint(["commitment_id"], ["gov_budget_commitments.id"]),
        sa.ForeignKeyConstraint(["policy_id"], ["gov_budget_causing_policies.id"]),
        sa.ForeignKeyConstraint(["autoridad_cargo_id"], ["gov_positions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "codigo", name="uq_gov_budget_causes_company_id_codigo"),
        sa.UniqueConstraint("year_id", "numero", name="uq_gov_budget_causes_year_id_numero"),
        sa.CheckConstraint(f"estado IN ({_en(*ESTADOS_CAUSADO)})", name="estado"),
        sa.CheckConstraint("monto > 0", name="monto"),
        sa.CheckConstraint("length(moneda) = 3", name="moneda"),
        sa.CheckConstraint(f"source_resource_type IS NULL OR source_resource_type IN ({_en(*TIPOS_FUENTE_CAUSADO)})", name="fuente"),
        sa.CheckConstraint("(source_resource_type IS NULL) = (source_resource_id IS NULL)", name="fuente_par"),
        sa.CheckConstraint(
            "estado = 'BORRADOR' OR (numero IS NOT NULL AND codigo IS NOT NULL AND formalizado_por IS NOT NULL AND formalizado_en IS NOT NULL AND snapshot IS NOT NULL AND huella IS NOT NULL AND autoridad_cargo_id IS NOT NULL)",
            name="completitud",
        ),
        sa.CheckConstraint("(estado = 'ANULADO') = (anulado_por IS NOT NULL AND anulado_en IS NOT NULL AND motivo_anulacion IS NOT NULL)", name="anulacion"),
    )
    op.create_index("ix_gov_budget_causes_company_id", "gov_budget_causes", ["company_id"])
    op.create_index("ix_gov_budget_causes_year_id", "gov_budget_causes", ["year_id"])
    op.create_index("ix_gov_budget_causes_commitment_id", "gov_budget_causes", ["commitment_id"])
    op.create_index("ix_gov_budget_causes_policy_id", "gov_budget_causes", ["policy_id"])

    op.create_table(
        "gov_budget_cause_lines",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("cause_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("commitment_line_id", sa.String(36), nullable=False),
        sa.Column("monto", sa.Numeric(18, 2), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["cause_id"], ["gov_budget_causes.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["commitment_line_id"], ["gov_budget_commitment_lines.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cause_id", "commitment_line_id", name="uq_gov_budget_cause_lines_cause_id_commitment_line_id"),
        sa.CheckConstraint("monto > 0", name="monto"),
    )
    op.create_index("ix_gov_budget_cause_lines_cause_id", "gov_budget_cause_lines", ["cause_id"])
    op.create_index("ix_gov_budget_cause_lines_company_id", "gov_budget_cause_lines", ["company_id"])
    op.create_index("ix_gov_budget_cause_lines_commitment_line_id", "gov_budget_cause_lines", ["commitment_line_id"])

    op.create_table(
        "gov_budget_cause_evidences",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("cause_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("resource_type", sa.String(20), nullable=False),
        sa.Column("resource_id", sa.String(36), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["cause_id"], ["gov_budget_causes.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cause_id", "resource_type", "resource_id", name="uq_gov_budget_cause_evidences_recurso"),
        sa.CheckConstraint(f"resource_type IN ({_en(*TIPOS_EVIDENCIA_CAUSADO)})", name="resource_type"),
    )
    op.create_index("ix_gov_budget_cause_evidences_cause_id", "gov_budget_cause_evidences", ["cause_id"])
    op.create_index("ix_gov_budget_cause_evidences_company_id", "gov_budget_cause_evidences", ["company_id"])

    op.create_table(
        "gov_budget_cause_history",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("cause_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("evento", sa.String(32), nullable=False),
        sa.Column("actor_id", sa.String(36), nullable=True),
        sa.Column("instantanea", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["cause_id"], ["gov_budget_causes.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_gov_budget_cause_history_cause_id", "gov_budget_cause_history", ["cause_id"])
    op.create_index("ix_gov_budget_cause_history_company_id", "gov_budget_cause_history", ["company_id"])

    _proceso_sod(op.get_bind(), *PROCESOS_SOD, "BUD-09")

    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            """
CREATE OR REPLACE FUNCTION kontrol_gov_budget_cause_guard() RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'TRUNCATE' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_BUDGET_CAUSE_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    IF TG_OP = 'DELETE' THEN
        IF OLD.estado <> 'BORRADOR' THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_BUDGET_CAUSE_IMMUTABLE', DETAIL = TG_OP;
        END IF;
        RETURN OLD;
    END IF;
    IF OLD.estado = 'ANULADO' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_BUDGET_CAUSE_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    IF OLD.estado = 'FORMALIZADO' THEN
        IF NOT (NEW.estado = 'ANULADO'
            AND NEW.numero IS NOT DISTINCT FROM OLD.numero
            AND NEW.codigo IS NOT DISTINCT FROM OLD.codigo
            AND NEW.fecha_efectiva IS NOT DISTINCT FROM OLD.fecha_efectiva
            AND NEW.moneda IS NOT DISTINCT FROM OLD.moneda
            AND NEW.monto IS NOT DISTINCT FROM OLD.monto
            AND NEW.concepto IS NOT DISTINCT FROM OLD.concepto
            AND NEW.beneficiario IS NOT DISTINCT FROM OLD.beneficiario
            AND NEW.source_resource_type IS NOT DISTINCT FROM OLD.source_resource_type
            AND NEW.source_resource_id IS NOT DISTINCT FROM OLD.source_resource_id
            AND NEW.autoridad_cargo_id IS NOT DISTINCT FROM OLD.autoridad_cargo_id
            AND NEW.autoridad_cargo_codigo IS NOT DISTINCT FROM OLD.autoridad_cargo_codigo
            AND NEW.autoridad_cargo_nombre IS NOT DISTINCT FROM OLD.autoridad_cargo_nombre
            AND NEW.autoridad_unidad IS NOT DISTINCT FROM OLD.autoridad_unidad
            AND NEW.autoridad_funcionario_id IS NOT DISTINCT FROM OLD.autoridad_funcionario_id
            AND NEW.autoridad_funcionario_nombre IS NOT DISTINCT FROM OLD.autoridad_funcionario_nombre
            AND NEW.formalizado_por IS NOT DISTINCT FROM OLD.formalizado_por
            AND NEW.formalizado_en IS NOT DISTINCT FROM OLD.formalizado_en
            AND NEW.snapshot::text IS NOT DISTINCT FROM OLD.snapshot::text
            AND NEW.huella IS NOT DISTINCT FROM OLD.huella
            AND NEW.policy_id IS NOT DISTINCT FROM OLD.policy_id
            AND NEW.policy_version IS NOT DISTINCT FROM OLD.policy_version
            AND NEW.year_id IS NOT DISTINCT FROM OLD.year_id) THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_BUDGET_CAUSE_IMMUTABLE', DETAIL = TG_OP;
        END IF;
    END IF;
    IF NEW.company_id IS DISTINCT FROM OLD.company_id
        OR NEW.year_id IS DISTINCT FROM OLD.year_id
        OR NEW.commitment_id IS DISTINCT FROM OLD.commitment_id
        OR NEW.created_by IS DISTINCT FROM OLD.created_by THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_BUDGET_CAUSE_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    RETURN NEW;
END; $$ LANGUAGE plpgsql
"""
        )
        op.execute("CREATE TRIGGER trg_gov_budget_causes_guard BEFORE UPDATE OR DELETE ON gov_budget_causes FOR EACH ROW EXECUTE FUNCTION kontrol_gov_budget_cause_guard()")
        op.execute("CREATE TRIGGER trg_gov_budget_causes_no_truncate BEFORE TRUNCATE ON gov_budget_causes FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_budget_cause_guard()")
        op.execute(
            """
CREATE OR REPLACE FUNCTION kontrol_gov_budget_cause_children_guard() RETURNS TRIGGER AS $$
DECLARE
    v_estado TEXT;
BEGIN
    IF TG_OP = 'TRUNCATE' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_BUDGET_CAUSE_CHILDREN_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    IF TG_OP = 'UPDATE' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_BUDGET_CAUSE_CHILDREN_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    SELECT estado INTO v_estado FROM gov_budget_causes WHERE id = COALESCE(NEW.cause_id, OLD.cause_id);
    IF v_estado IS DISTINCT FROM 'BORRADOR' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_BUDGET_CAUSE_CHILDREN_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END; $$ LANGUAGE plpgsql
"""
        )
        op.execute("CREATE TRIGGER trg_gov_budget_cause_lines_guard BEFORE INSERT OR UPDATE OR DELETE ON gov_budget_cause_lines FOR EACH ROW EXECUTE FUNCTION kontrol_gov_budget_cause_children_guard()")
        op.execute("CREATE TRIGGER trg_gov_budget_cause_lines_no_truncate BEFORE TRUNCATE ON gov_budget_cause_lines FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_budget_cause_children_guard()")
        op.execute("CREATE TRIGGER trg_gov_budget_cause_evidences_guard BEFORE INSERT OR UPDATE OR DELETE ON gov_budget_cause_evidences FOR EACH ROW EXECUTE FUNCTION kontrol_gov_budget_cause_children_guard()")
        op.execute("CREATE TRIGGER trg_gov_budget_cause_evidences_no_truncate BEFORE TRUNCATE ON gov_budget_cause_evidences FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_budget_cause_children_guard()")
        op.execute("CREATE TRIGGER trg_gov_budget_cause_history_guard BEFORE UPDATE OR DELETE ON gov_budget_cause_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_presupuesto_historia_inmutable()")
        op.execute("CREATE TRIGGER trg_gov_budget_cause_history_no_truncate BEFORE TRUNCATE ON gov_budget_cause_history FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_presupuesto_historia_inmutable()")
        op.execute("CREATE TRIGGER trg_gov_budget_causing_policy_history_guard BEFORE UPDATE OR DELETE ON gov_budget_causing_policy_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_presupuesto_historia_inmutable()")
        op.execute("CREATE TRIGGER trg_gov_budget_causing_policy_history_no_truncate BEFORE TRUNCATE ON gov_budget_causing_policy_history FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_presupuesto_historia_inmutable()")

    _conceder_permisos(op.get_bind())


def downgrade() -> None:
    bind = op.get_bind()

    for recurso, acciones in PERMISOS.items():
        for accion in acciones:
            permisos = bind.execute(
                sa.text("SELECT id FROM permissions WHERE resource = :r AND action = :a"),
                {"r": recurso, "a": accion},
            ).fetchall()
            for permiso in permisos:
                bind.execute(sa.text("DELETE FROM role_permissions WHERE permission_id = :p"), {"p": permiso[0]})
                bind.execute(sa.text("DELETE FROM permissions WHERE id = :p"), {"p": permiso[0]})

    _proceso_sod(bind, *PROCESOS_SOD)

    if bind.dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_gov_budget_causing_policy_history_guard ON gov_budget_causing_policy_history")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_budget_causing_policy_history_no_truncate ON gov_budget_causing_policy_history")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_budget_cause_history_guard ON gov_budget_cause_history")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_budget_cause_history_no_truncate ON gov_budget_cause_history")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_budget_cause_evidences_guard ON gov_budget_cause_evidences")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_budget_cause_evidences_no_truncate ON gov_budget_cause_evidences")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_budget_cause_lines_guard ON gov_budget_cause_lines")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_budget_cause_lines_no_truncate ON gov_budget_cause_lines")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_budget_causes_guard ON gov_budget_causes")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_budget_causes_no_truncate ON gov_budget_causes")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_budget_cause_children_guard()")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_budget_cause_guard()")

    op.drop_index("ix_gov_budget_cause_history_company_id", table_name="gov_budget_cause_history")
    op.drop_index("ix_gov_budget_cause_history_cause_id", table_name="gov_budget_cause_history")
    op.drop_table("gov_budget_cause_history")

    op.drop_index("ix_gov_budget_cause_evidences_company_id", table_name="gov_budget_cause_evidences")
    op.drop_index("ix_gov_budget_cause_evidences_cause_id", table_name="gov_budget_cause_evidences")
    op.drop_table("gov_budget_cause_evidences")

    op.drop_index("ix_gov_budget_cause_lines_commitment_line_id", table_name="gov_budget_cause_lines")
    op.drop_index("ix_gov_budget_cause_lines_company_id", table_name="gov_budget_cause_lines")
    op.drop_index("ix_gov_budget_cause_lines_cause_id", table_name="gov_budget_cause_lines")
    op.drop_table("gov_budget_cause_lines")

    op.drop_index("ix_gov_budget_causes_policy_id", table_name="gov_budget_causes")
    op.drop_index("ix_gov_budget_causes_commitment_id", table_name="gov_budget_causes")
    op.drop_index("ix_gov_budget_causes_year_id", table_name="gov_budget_causes")
    op.drop_index("ix_gov_budget_causes_company_id", table_name="gov_budget_causes")
    op.drop_table("gov_budget_causes")

    op.drop_index("ix_gov_budget_causing_policy_history_company_id", table_name="gov_budget_causing_policy_history")
    op.drop_index("ix_gov_budget_causing_policy_history_policy_id", table_name="gov_budget_causing_policy_history")
    op.drop_table("gov_budget_causing_policy_history")

    op.drop_index("ix_gov_budget_causing_policy_documents_company_id", table_name="gov_budget_causing_policy_documents")
    op.drop_index("ix_gov_budget_causing_policy_documents_policy_id", table_name="gov_budget_causing_policy_documents")
    op.drop_table("gov_budget_causing_policy_documents")

    op.drop_index("ix_gov_budget_causing_policies_company_id", table_name="gov_budget_causing_policies")
    op.drop_table("gov_budget_causing_policies")

    op.drop_index("ix_gov_budget_cause_settings_company_id", table_name="gov_budget_cause_settings")
    op.drop_table("gov_budget_cause_settings")
