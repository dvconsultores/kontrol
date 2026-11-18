"""TRE-03: orden de pago desde obligaciones causadas."""
from __future__ import annotations

import uuid

import sqlalchemy as sa

from alembic import op

revision = "0124_gov_tre03_orden_pago"
down_revision = "0123_gov_bud09_causado"
branch_labels = None
depends_on = None

PERMISOS = {"gobierno_ordenes_pago": ("view", "manage", "issue", "cancel", "policy")}
PROCESOS_SOD = ("DOC-02", "CTL-06", "TRE-01", "TRE-02", "CTL-10", "ORG-04", "ORG-06", "PROC-02", "PROC-03", "BUD-09")

ESTADOS_POLITICA_ORDEN_PAGO = ("BORRADOR", "VIGENTE", "CERRADA")
TIPOS_REGLA_ORDEN_PAGO = ("INSTITUTIONAL_POLICY", "OPERATIONAL_CONFIGURATION", "LEGAL_MANDATORY")
ETAPAS_DOCUMENTO_ORDEN_PAGO = ("EMISION",)
ESTADOS_ORDEN_PAGO = ("BORRADOR", "EMITIDA", "ANULADA")

ACCIONES_COMPETENCIA = ("SOLICITAR", "COMPROMETER", "CAUSAR", "ORDENAR_PAGO", "PAGAR", "REGISTRAR", "CUSTODIAR", "APROBAR", "AUDITAR", "FIRMAR")
MATERIAS_COMPETENCIA = ("PRESUPUESTO", "CONTRATACIONES", "TESORERIA", "CONTABILIDAD", "BIENES", "EXPEDIENTE")


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
        "gov_payment_order_settings",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("patron", sa.String(60), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", name="uq_gov_payment_order_settings_company_id"),
    )
    op.create_index("ix_gov_payment_order_settings_company_id", "gov_payment_order_settings", ["company_id"])

    op.create_table(
        "gov_payment_order_policies",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("tipo_gasto", sa.String(40), nullable=True),
        sa.Column("requiere_expediente_completo", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("competencia_accion", sa.String(16), nullable=False, server_default="ORDENAR_PAGO"),
        sa.Column("competencia_materia", sa.String(16), nullable=False, server_default="TESORERIA"),
        sa.Column("vigente_desde", sa.Date(), nullable=False),
        sa.Column("vigente_hasta", sa.Date(), nullable=True),
        sa.Column("fundamento", sa.String(2000), nullable=True),
        sa.Column("act_id", sa.String(36), nullable=True),
        sa.Column("tipo_regla", sa.String(26), nullable=False, server_default="INSTITUTIONAL_POLICY"),
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
        sa.UniqueConstraint("company_id", "codigo", name="uq_gov_payment_order_policies_company_codigo"),
        sa.CheckConstraint(f"estado IN ({_en(*ESTADOS_POLITICA_ORDEN_PAGO)})", name="estado"),
        sa.CheckConstraint(f"tipo_regla IN ({_en(*TIPOS_REGLA_ORDEN_PAGO)})", name="tipo_regla"),
        sa.CheckConstraint(f"competencia_accion IN ({_en(*ACCIONES_COMPETENCIA)})", name="competencia_accion"),
        sa.CheckConstraint(f"competencia_materia IN ({_en(*MATERIAS_COMPETENCIA)})", name="competencia_materia"),
        sa.CheckConstraint("vigente_hasta IS NULL OR vigente_hasta >= vigente_desde", name="vigencia"),
        sa.CheckConstraint("estado = 'BORRADOR' OR fundamento IS NOT NULL", name="fundamento"),
    )
    op.create_index("ix_gov_payment_order_policies_company_id", "gov_payment_order_policies", ["company_id"])

    op.create_table(
        "gov_payment_order_policy_documents",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("policy_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("document_type_id", sa.String(36), nullable=False),
        sa.Column("obligatorio", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("etapa", sa.String(10), nullable=False, server_default="EMISION"),
        sa.Column("condicion", sa.String(300), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["policy_id"], ["gov_payment_order_policies.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["document_type_id"], ["document_types.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("policy_id", "document_type_id", name="uq_gov_payment_order_policy_docs_type"),
        sa.CheckConstraint(f"etapa IN ({_en(*ETAPAS_DOCUMENTO_ORDEN_PAGO)})", name="etapa"),
    )
    op.create_index("ix_gov_payment_order_policy_documents_policy_id", "gov_payment_order_policy_documents", ["policy_id"])
    op.create_index("ix_gov_payment_order_policy_documents_company_id", "gov_payment_order_policy_documents", ["company_id"])

    op.create_table(
        "gov_payment_order_policy_history",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("policy_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("evento", sa.String(32), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("instantanea", sa.JSON(), nullable=False),
        sa.Column("actor_id", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["policy_id"], ["gov_payment_order_policies.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_gov_payment_order_policy_history_policy_id", "gov_payment_order_policy_history", ["policy_id"])
    op.create_index("ix_gov_payment_order_policy_history_company_id", "gov_payment_order_policy_history", ["company_id"])

    op.create_table(
        "gov_payment_orders",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("year_id", sa.String(36), nullable=False),
        sa.Column("policy_id", sa.String(36), nullable=False),
        sa.Column("policy_version", sa.Integer(), nullable=False),
        sa.Column("estado", sa.String(10), nullable=False, server_default="BORRADOR"),
        sa.Column("numero", sa.Integer(), nullable=True),
        sa.Column("codigo", sa.String(60), nullable=True),
        sa.Column("fecha_orden", sa.Date(), nullable=False),
        sa.Column("moneda", sa.String(3), nullable=False),
        sa.Column("monto", sa.Numeric(18, 2), nullable=False),
        sa.Column("concepto", sa.String(500), nullable=False),
        sa.Column("beneficiario", sa.String(200), nullable=True),
        sa.Column("autoridad_cargo_id", sa.String(36), nullable=True),
        sa.Column("autoridad_cargo_codigo", sa.String(30), nullable=True),
        sa.Column("autoridad_cargo_nombre", sa.String(200), nullable=True),
        sa.Column("autoridad_unidad", sa.String(250), nullable=True),
        sa.Column("autoridad_funcionario_id", sa.String(36), nullable=True),
        sa.Column("autoridad_funcionario_nombre", sa.String(200), nullable=True),
        sa.Column("emitida_por", sa.String(36), nullable=True),
        sa.Column("emitida_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("snapshot", sa.JSON(), nullable=True),
        sa.Column("huella", sa.String(64), nullable=True),
        sa.Column("anulada_por", sa.String(36), nullable=True),
        sa.Column("anulada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("motivo_anulacion", sa.String(500), nullable=True),
        sa.Column("anulacion_cargo_id", sa.String(36), nullable=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["year_id"], ["gov_budget_years.id"]),
        sa.ForeignKeyConstraint(["policy_id"], ["gov_payment_order_policies.id"]),
        sa.ForeignKeyConstraint(["autoridad_cargo_id"], ["gov_positions.id"]),
        sa.ForeignKeyConstraint(["anulacion_cargo_id"], ["gov_positions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "codigo", name="uq_gov_payment_orders_company_codigo"),
        sa.UniqueConstraint("year_id", "numero", name="uq_gov_payment_orders_year_numero"),
        sa.CheckConstraint(f"estado IN ({_en(*ESTADOS_ORDEN_PAGO)})", name="estado"),
        sa.CheckConstraint("monto > 0", name="monto"),
        sa.CheckConstraint("length(moneda) = 3", name="moneda"),
        sa.CheckConstraint(
            "estado = 'BORRADOR' OR (beneficiario IS NOT NULL AND codigo IS NOT NULL AND emitida_por IS NOT NULL AND emitida_en IS NOT NULL AND huella IS NOT NULL)",
            name="emision",
        ),
        sa.CheckConstraint("(estado = 'ANULADA') = (anulada_por IS NOT NULL AND anulada_en IS NOT NULL AND motivo_anulacion IS NOT NULL)", name="anulacion"),
    )
    op.create_index("ix_gov_payment_orders_company_id", "gov_payment_orders", ["company_id"])
    op.create_index("ix_gov_payment_orders_year_id", "gov_payment_orders", ["year_id"])
    op.create_index("ix_gov_payment_orders_policy_id", "gov_payment_orders", ["policy_id"])

    op.create_table(
        "gov_payment_order_lines",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("order_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("cause_id", sa.String(36), nullable=False),
        sa.Column("monto", sa.Numeric(18, 2), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["order_id"], ["gov_payment_orders.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["cause_id"], ["gov_budget_causes.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", "cause_id", name="uq_gov_payment_order_lines_order_cause"),
        sa.CheckConstraint("monto > 0", name="monto"),
    )
    op.create_index("ix_gov_payment_order_lines_order_id", "gov_payment_order_lines", ["order_id"])
    op.create_index("ix_gov_payment_order_lines_company_id", "gov_payment_order_lines", ["company_id"])
    op.create_index("ix_gov_payment_order_lines_cause_id", "gov_payment_order_lines", ["cause_id"])

    op.create_table(
        "gov_payment_order_documents",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("order_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("document_id", sa.String(36), nullable=False),
        sa.Column("document_type_id", sa.String(36), nullable=False),
        sa.Column("document_version_id", sa.String(36), nullable=True),
        sa.Column("sha256", sa.String(64), nullable=True),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["order_id"], ["gov_payment_orders.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["document_type_id"], ["document_types.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", "document_id", name="uq_gov_payment_order_documents_order_doc"),
    )
    op.create_index("ix_gov_payment_order_documents_order_id", "gov_payment_order_documents", ["order_id"])
    op.create_index("ix_gov_payment_order_documents_company_id", "gov_payment_order_documents", ["company_id"])

    op.create_table(
        "gov_payment_order_history",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("order_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("evento", sa.String(32), nullable=False),
        sa.Column("actor_id", sa.String(36), nullable=True),
        sa.Column("instantanea", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["order_id"], ["gov_payment_orders.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_gov_payment_order_history_order_id", "gov_payment_order_history", ["order_id"])
    op.create_index("ix_gov_payment_order_history_company_id", "gov_payment_order_history", ["company_id"])

    _proceso_sod(op.get_bind(), *PROCESOS_SOD, "TRE-03")

    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            """
CREATE OR REPLACE FUNCTION kontrol_gov_payment_order_guard() RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'TRUNCATE' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_PAYMENT_ORDER_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    IF TG_OP = 'DELETE' THEN
        IF OLD.estado <> 'BORRADOR' THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_PAYMENT_ORDER_IMMUTABLE', DETAIL = TG_OP;
        END IF;
        RETURN OLD;
    END IF;
    IF OLD.estado = 'ANULADA' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_PAYMENT_ORDER_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    IF OLD.estado = 'EMITIDA' THEN
        IF NOT (NEW.estado = 'ANULADA'
            AND NEW.numero IS NOT DISTINCT FROM OLD.numero
            AND NEW.codigo IS NOT DISTINCT FROM OLD.codigo
            AND NEW.fecha_orden IS NOT DISTINCT FROM OLD.fecha_orden
            AND NEW.moneda IS NOT DISTINCT FROM OLD.moneda
            AND NEW.monto IS NOT DISTINCT FROM OLD.monto
            AND NEW.concepto IS NOT DISTINCT FROM OLD.concepto
            AND NEW.beneficiario IS NOT DISTINCT FROM OLD.beneficiario
            AND NEW.autoridad_cargo_id IS NOT DISTINCT FROM OLD.autoridad_cargo_id
            AND NEW.autoridad_cargo_codigo IS NOT DISTINCT FROM OLD.autoridad_cargo_codigo
            AND NEW.autoridad_cargo_nombre IS NOT DISTINCT FROM OLD.autoridad_cargo_nombre
            AND NEW.autoridad_unidad IS NOT DISTINCT FROM OLD.autoridad_unidad
            AND NEW.autoridad_funcionario_id IS NOT DISTINCT FROM OLD.autoridad_funcionario_id
            AND NEW.autoridad_funcionario_nombre IS NOT DISTINCT FROM OLD.autoridad_funcionario_nombre
            AND NEW.emitida_por IS NOT DISTINCT FROM OLD.emitida_por
            AND NEW.emitida_en IS NOT DISTINCT FROM OLD.emitida_en
            AND NEW.snapshot::text IS NOT DISTINCT FROM OLD.snapshot::text
            AND NEW.huella IS NOT DISTINCT FROM OLD.huella
            AND NEW.policy_id IS NOT DISTINCT FROM OLD.policy_id
            AND NEW.policy_version IS NOT DISTINCT FROM OLD.policy_version
            AND NEW.year_id IS NOT DISTINCT FROM OLD.year_id) THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_PAYMENT_ORDER_IMMUTABLE', DETAIL = TG_OP;
        END IF;
    END IF;
    IF NEW.company_id IS DISTINCT FROM OLD.company_id
        OR NEW.year_id IS DISTINCT FROM OLD.year_id
        OR NEW.policy_id IS DISTINCT FROM OLD.policy_id
        OR NEW.policy_version IS DISTINCT FROM OLD.policy_version
        OR NEW.created_by IS DISTINCT FROM OLD.created_by THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_PAYMENT_ORDER_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    RETURN NEW;
END; $$ LANGUAGE plpgsql
"""
        )
        op.execute("CREATE TRIGGER trg_gov_payment_orders_guard BEFORE UPDATE OR DELETE ON gov_payment_orders FOR EACH ROW EXECUTE FUNCTION kontrol_gov_payment_order_guard()")
        op.execute("CREATE TRIGGER trg_gov_payment_orders_no_truncate BEFORE TRUNCATE ON gov_payment_orders FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_payment_order_guard()")
        op.execute(
            """
CREATE OR REPLACE FUNCTION kontrol_gov_payment_order_children_guard() RETURNS TRIGGER AS $$
DECLARE
    v_estado TEXT;
BEGIN
    IF TG_OP = 'TRUNCATE' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_PAYMENT_ORDER_CHILDREN_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    IF TG_OP = 'UPDATE' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_PAYMENT_ORDER_CHILDREN_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    SELECT estado INTO v_estado FROM gov_payment_orders WHERE id = COALESCE(NEW.order_id, OLD.order_id);
    IF v_estado IS DISTINCT FROM 'BORRADOR' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_PAYMENT_ORDER_CHILDREN_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END; $$ LANGUAGE plpgsql
"""
        )
        op.execute("CREATE TRIGGER trg_gov_payment_order_lines_guard BEFORE INSERT OR UPDATE OR DELETE ON gov_payment_order_lines FOR EACH ROW EXECUTE FUNCTION kontrol_gov_payment_order_children_guard()")
        op.execute("CREATE TRIGGER trg_gov_payment_order_lines_no_truncate BEFORE TRUNCATE ON gov_payment_order_lines FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_payment_order_children_guard()")
        op.execute("CREATE TRIGGER trg_gov_payment_order_documents_guard BEFORE INSERT OR UPDATE OR DELETE ON gov_payment_order_documents FOR EACH ROW EXECUTE FUNCTION kontrol_gov_payment_order_children_guard()")
        op.execute("CREATE TRIGGER trg_gov_payment_order_documents_no_truncate BEFORE TRUNCATE ON gov_payment_order_documents FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_payment_order_children_guard()")
        op.execute("CREATE TRIGGER trg_gov_payment_order_history_guard BEFORE UPDATE OR DELETE ON gov_payment_order_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_presupuesto_historia_inmutable()")
        op.execute("CREATE TRIGGER trg_gov_payment_order_history_no_truncate BEFORE TRUNCATE ON gov_payment_order_history FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_presupuesto_historia_inmutable()")
        op.execute("CREATE TRIGGER trg_gov_payment_order_policy_history_guard BEFORE UPDATE OR DELETE ON gov_payment_order_policy_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_presupuesto_historia_inmutable()")
        op.execute("CREATE TRIGGER trg_gov_payment_order_policy_history_no_truncate BEFORE TRUNCATE ON gov_payment_order_policy_history FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_presupuesto_historia_inmutable()")

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
        op.execute("DROP TRIGGER IF EXISTS trg_gov_payment_order_policy_history_guard ON gov_payment_order_policy_history")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_payment_order_policy_history_no_truncate ON gov_payment_order_policy_history")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_payment_order_history_guard ON gov_payment_order_history")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_payment_order_history_no_truncate ON gov_payment_order_history")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_payment_order_documents_guard ON gov_payment_order_documents")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_payment_order_documents_no_truncate ON gov_payment_order_documents")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_payment_order_lines_guard ON gov_payment_order_lines")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_payment_order_lines_no_truncate ON gov_payment_order_lines")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_payment_orders_guard ON gov_payment_orders")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_payment_orders_no_truncate ON gov_payment_orders")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_payment_order_children_guard()")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_payment_order_guard()")

    op.drop_index("ix_gov_payment_order_history_company_id", table_name="gov_payment_order_history")
    op.drop_index("ix_gov_payment_order_history_order_id", table_name="gov_payment_order_history")
    op.drop_table("gov_payment_order_history")

    op.drop_index("ix_gov_payment_order_documents_company_id", table_name="gov_payment_order_documents")
    op.drop_index("ix_gov_payment_order_documents_order_id", table_name="gov_payment_order_documents")
    op.drop_table("gov_payment_order_documents")

    op.drop_index("ix_gov_payment_order_lines_cause_id", table_name="gov_payment_order_lines")
    op.drop_index("ix_gov_payment_order_lines_company_id", table_name="gov_payment_order_lines")
    op.drop_index("ix_gov_payment_order_lines_order_id", table_name="gov_payment_order_lines")
    op.drop_table("gov_payment_order_lines")

    op.drop_index("ix_gov_payment_orders_policy_id", table_name="gov_payment_orders")
    op.drop_index("ix_gov_payment_orders_year_id", table_name="gov_payment_orders")
    op.drop_index("ix_gov_payment_orders_company_id", table_name="gov_payment_orders")
    op.drop_table("gov_payment_orders")

    op.drop_index("ix_gov_payment_order_policy_history_company_id", table_name="gov_payment_order_policy_history")
    op.drop_index("ix_gov_payment_order_policy_history_policy_id", table_name="gov_payment_order_policy_history")
    op.drop_table("gov_payment_order_policy_history")

    op.drop_index("ix_gov_payment_order_policy_documents_company_id", table_name="gov_payment_order_policy_documents")
    op.drop_index("ix_gov_payment_order_policy_documents_policy_id", table_name="gov_payment_order_policy_documents")
    op.drop_table("gov_payment_order_policy_documents")

    op.drop_index("ix_gov_payment_order_policies_company_id", table_name="gov_payment_order_policies")
    op.drop_table("gov_payment_order_policies")

    op.drop_index("ix_gov_payment_order_settings_company_id", table_name="gov_payment_order_settings")
    op.drop_table("gov_payment_order_settings")
