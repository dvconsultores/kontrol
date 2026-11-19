"""TRE-04: pago de ordenes de pago con maker-checker, medios del ente y bloqueo de duplicados."""
from __future__ import annotations

import uuid

import sqlalchemy as sa

from alembic import op

revision = "0127_gov_tre04_pago"
down_revision = "0126_gov_assignment_policy"
branch_labels = None
depends_on = None

PERMISOS = {"gobierno_pagos": ("view", "manage", "authorize", "execute", "cancel", "policy")}
PROCESOS_SOD = ("DOC-02", "CTL-06", "TRE-01", "TRE-02", "CTL-10", "ORG-04", "ORG-06", "PROC-02", "PROC-03", "BUD-09", "TRE-03")

ESTADOS_MEDIO_PAGO = ("ACTIVO", "INACTIVO")
ESTADOS_POLITICA_PAGO = ("BORRADOR", "VIGENTE", "CERRADA")
CONTROLES_DUPLICADO_PAGO = ("BLOQUEAR", "ADVERTIR")
ETAPAS_DOCUMENTO_PAGO = ("PREPARAR", "AUTORIZAR", "REGISTRAR", "ANULAR")
ESTADOS_PAGO = ("BORRADOR", "PENDIENTE_AUTORIZACION", "AUTORIZADO", "REGISTRADO", "RECHAZADO", "ANULADO")
DECISIONES_APROBACION_PAGO = ("APROBADA", "RECHAZADA")
TIPOS_REGLA_ORDEN_PAGO = ("INSTITUTIONAL_POLICY", "OPERATIONAL_CONFIGURATION", "LEGAL_MANDATORY")
ACCIONES_COMPETENCIA = ("SOLICITAR", "COMPROMETER", "CAUSAR", "ORDENAR_PAGO", "PAGAR", "REGISTRAR", "CUSTODIAR", "APROBAR", "AUDITAR", "FIRMAR")
MATERIAS_COMPETENCIA = ("PRESUPUESTO", "CONTRATACIONES", "TESORERIA", "CONTABILIDAD", "BIENES", "EXPEDIENTE")
MONEDAS_LIMITE = ("EUR", "USD", "MXN")


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
        "gov_payment_settings",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("patron", sa.String(60), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", name="uq_gov_payment_settings_company_id"),
    )
    op.create_index("ix_gov_payment_settings_company_id", "gov_payment_settings", ["company_id"])

    op.create_table(
        "gov_payment_methods",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("nombre", sa.String(120), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("estado", sa.String(10), nullable=False, server_default="ACTIVO"),
        sa.Column("vigente_desde", sa.Date(), nullable=False),
        sa.Column("vigente_hasta", sa.Date(), nullable=True),
        sa.Column("exige_referencia", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("referencia_unica", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("patron_referencia", sa.String(200), nullable=True),
        sa.Column("fundamento", sa.String(2000), nullable=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "codigo", name="uq_gov_payment_methods_company_codigo"),
        sa.CheckConstraint(f"estado IN ({_en(*ESTADOS_MEDIO_PAGO)})", name="estado"),
        sa.CheckConstraint("vigente_hasta IS NULL OR vigente_hasta >= vigente_desde", name="vigencia"),
        sa.CheckConstraint("referencia_unica = false OR exige_referencia = true", name="referencia_unica"),
    )
    op.create_index("ix_gov_payment_methods_company_id", "gov_payment_methods", ["company_id"])

    op.create_table(
        "gov_payment_policies",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("numero_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("version_anterior_id", sa.String(36), nullable=True),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("moneda", sa.String(3), nullable=False),
        sa.Column("permite_pago_parcial", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("preparador_competencia_accion", sa.String(16), nullable=True),
        sa.Column("preparador_competencia_materia", sa.String(16), nullable=True),
        sa.Column("exige_cargo_autorizado_cuenta", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("control_duplicado", sa.String(10), nullable=False, server_default="BLOQUEAR"),
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
        sa.ForeignKeyConstraint(["version_anterior_id"], ["gov_payment_policies.id"]),
        sa.ForeignKeyConstraint(["act_id"], ["gov_acts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "codigo", "numero_version", name="uq_gov_payment_policies_company_codigo_version"),
        sa.CheckConstraint(f"estado IN ({_en(*ESTADOS_POLITICA_PAGO)})", name="estado"),
        sa.CheckConstraint(f"tipo_regla IN ({_en(*TIPOS_REGLA_ORDEN_PAGO)})", name="tipo_regla"),
        sa.CheckConstraint(f"control_duplicado IN ({_en(*CONTROLES_DUPLICADO_PAGO)})", name="control_duplicado"),
        sa.CheckConstraint(f"moneda IN ({_en(*MONEDAS_LIMITE)})", name="moneda"),
        sa.CheckConstraint("vigente_hasta IS NULL OR vigente_hasta >= vigente_desde", name="vigencia"),
        sa.CheckConstraint("estado = 'BORRADOR' OR fundamento IS NOT NULL", name="fundamento"),
        sa.CheckConstraint("(preparador_competencia_accion IS NULL) = (preparador_competencia_materia IS NULL)", name="preparador"),
        sa.CheckConstraint(f"preparador_competencia_accion IS NULL OR preparador_competencia_accion IN ({_en(*ACCIONES_COMPETENCIA)})", name="preparador_accion"),
        sa.CheckConstraint(f"preparador_competencia_materia IS NULL OR preparador_competencia_materia IN ({_en(*MATERIAS_COMPETENCIA)})", name="preparador_materia"),
        sa.CheckConstraint("numero_version >= 1", name="numero_version"),
    )
    op.create_index("ix_gov_payment_policies_company_id", "gov_payment_policies", ["company_id"])

    op.create_table(
        "gov_payment_policy_methods",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("policy_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("method_id", sa.String(36), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["policy_id"], ["gov_payment_policies.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["method_id"], ["gov_payment_methods.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("policy_id", "method_id", name="uq_gov_payment_policy_methods_policy_method"),
    )
    op.create_index("ix_gov_payment_policy_methods_policy_id", "gov_payment_policy_methods", ["policy_id"])
    op.create_index("ix_gov_payment_policy_methods_company_id", "gov_payment_policy_methods", ["company_id"])
    op.create_index("ix_gov_payment_policy_methods_method_id", "gov_payment_policy_methods", ["method_id"])

    op.create_table(
        "gov_payment_policy_bands",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("policy_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.Column("monto_desde", sa.Numeric(18, 2), nullable=False),
        sa.Column("monto_hasta", sa.Numeric(18, 2), nullable=True),
        sa.Column("requisitos", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["policy_id"], ["gov_payment_policies.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("policy_id", "orden", name="uq_gov_payment_policy_bands_policy_orden"),
        sa.CheckConstraint("monto_desde >= 0", name="desde"),
        sa.CheckConstraint("monto_hasta IS NULL OR monto_hasta > monto_desde", name="hasta"),
    )
    op.create_index("ix_gov_payment_policy_bands_policy_id", "gov_payment_policy_bands", ["policy_id"])
    op.create_index("ix_gov_payment_policy_bands_company_id", "gov_payment_policy_bands", ["company_id"])

    op.create_table(
        "gov_payment_policy_documents",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("policy_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("document_type_id", sa.String(36), nullable=False),
        sa.Column("etapa", sa.String(10), nullable=False),
        sa.Column("obligatorio", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["policy_id"], ["gov_payment_policies.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["document_type_id"], ["document_types.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("policy_id", "document_type_id", "etapa", name="uq_gov_payment_policy_documents_type_etapa"),
        sa.CheckConstraint(f"etapa IN ({_en(*ETAPAS_DOCUMENTO_PAGO)})", name="etapa"),
    )
    op.create_index("ix_gov_payment_policy_documents_policy_id", "gov_payment_policy_documents", ["policy_id"])
    op.create_index("ix_gov_payment_policy_documents_company_id", "gov_payment_policy_documents", ["company_id"])

    op.create_table(
        "gov_payment_policy_history",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("policy_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("evento", sa.String(32), nullable=False),
        sa.Column("numero_version", sa.Integer(), nullable=False),
        sa.Column("instantanea", sa.JSON(), nullable=False),
        sa.Column("actor_id", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["policy_id"], ["gov_payment_policies.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_gov_payment_policy_history_policy_id", "gov_payment_policy_history", ["policy_id"])
    op.create_index("ix_gov_payment_policy_history_company_id", "gov_payment_policy_history", ["company_id"])

    op.create_table(
        "gov_payments",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("order_id", sa.String(36), nullable=False),
        sa.Column("policy_id", sa.String(36), nullable=False),
        sa.Column("policy_numero_version", sa.Integer(), nullable=True),
        sa.Column("policy_snapshot", sa.JSON(), nullable=True),
        sa.Column("estado", sa.String(22), nullable=False, server_default="BORRADOR"),
        sa.Column("numero", sa.Integer(), nullable=True),
        sa.Column("codigo", sa.String(60), nullable=True),
        sa.Column("fecha_pago", sa.Date(), nullable=False),
        sa.Column("fecha_valor", sa.Date(), nullable=True),
        sa.Column("account_id", sa.String(36), nullable=False),
        sa.Column("method_id", sa.String(36), nullable=False),
        sa.Column("moneda", sa.String(3), nullable=False),
        sa.Column("monto", sa.Numeric(18, 2), nullable=False),
        sa.Column("concepto", sa.String(500), nullable=False),
        sa.Column("referencia_externa", sa.String(120), nullable=True),
        sa.Column("referencia_clave", sa.String(120), nullable=True),
        sa.Column("idempotency_key", sa.String(120), nullable=True),
        sa.Column("registro_idempotency_key", sa.String(120), nullable=True),
        sa.Column("documentos_preparar", sa.JSON(), nullable=True),
        sa.Column("preparador_cargo_id", sa.String(36), nullable=True),
        sa.Column("preparador_cargo_codigo", sa.String(30), nullable=True),
        sa.Column("preparador_cargo_nombre", sa.String(200), nullable=True),
        sa.Column("preparador_funcionario_id", sa.String(36), nullable=True),
        sa.Column("preparador_funcionario_nombre", sa.String(200), nullable=True),
        sa.Column("enviado_por", sa.String(36), nullable=True),
        sa.Column("enviado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("aprobaciones_requeridas", sa.Integer(), nullable=True),
        sa.Column("duplicado_confirmado", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("motivo_duplicado", sa.String(500), nullable=True),
        sa.Column("registrado_por", sa.String(36), nullable=True),
        sa.Column("registrado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rechazado_por", sa.String(36), nullable=True),
        sa.Column("rechazado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("motivo_rechazo", sa.String(500), nullable=True),
        sa.Column("anulado_por", sa.String(36), nullable=True),
        sa.Column("anulado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("motivo_anulacion", sa.String(500), nullable=True),
        sa.Column("huella", sa.String(64), nullable=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["order_id"], ["gov_payment_orders.id"]),
        sa.ForeignKeyConstraint(["policy_id"], ["gov_payment_policies.id"]),
        sa.ForeignKeyConstraint(["account_id"], ["gov_bank_accounts.id"]),
        sa.ForeignKeyConstraint(["method_id"], ["gov_payment_methods.id"]),
        sa.ForeignKeyConstraint(["preparador_cargo_id"], ["gov_positions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "codigo", name="uq_gov_payments_company_codigo"),
        sa.CheckConstraint(f"estado IN ({_en(*ESTADOS_PAGO)})", name="estado"),
        sa.CheckConstraint("monto > 0", name="monto"),
        sa.CheckConstraint("length(moneda) = 3", name="moneda"),
        sa.CheckConstraint("estado IN ('BORRADOR', 'ANULADO') OR (codigo IS NOT NULL AND enviado_por IS NOT NULL AND enviado_en IS NOT NULL AND policy_numero_version IS NOT NULL AND policy_snapshot IS NOT NULL AND aprobaciones_requeridas IS NOT NULL)", name="envio"),
        sa.CheckConstraint("(estado = 'REGISTRADO') = (registrado_por IS NOT NULL AND registrado_en IS NOT NULL AND fecha_valor IS NOT NULL)", name="registro"),
        sa.CheckConstraint("(estado = 'RECHAZADO') = (rechazado_por IS NOT NULL AND rechazado_en IS NOT NULL AND motivo_rechazo IS NOT NULL)", name="rechazo"),
        sa.CheckConstraint("(estado = 'ANULADO') = (anulado_por IS NOT NULL AND anulado_en IS NOT NULL AND motivo_anulacion IS NOT NULL)", name="anulacion"),
        sa.CheckConstraint("referencia_clave IS NULL OR estado = 'REGISTRADO'", name="referencia_clave"),
        sa.CheckConstraint("duplicado_confirmado = false OR motivo_duplicado IS NOT NULL", name="duplicado"),
        sa.CheckConstraint("aprobaciones_requeridas IS NULL OR aprobaciones_requeridas >= 1", name="aprobaciones"),
    )
    op.create_index("ix_gov_payments_company_id", "gov_payments", ["company_id"])
    op.create_index("ix_gov_payments_order_id", "gov_payments", ["order_id"])
    op.create_index("ix_gov_payments_policy_id", "gov_payments", ["policy_id"])
    op.create_index("ix_gov_payments_account_id", "gov_payments", ["account_id"])
    op.create_index("ix_gov_payments_method_id", "gov_payments", ["method_id"])
    op.create_index("uq_gov_payments_idempotency", "gov_payments", ["company_id", "idempotency_key"], unique=True, postgresql_where=sa.text("idempotency_key IS NOT NULL"), sqlite_where=sa.text("idempotency_key IS NOT NULL"))
    op.create_index("uq_gov_payments_registro_idempotency", "gov_payments", ["company_id", "registro_idempotency_key"], unique=True, postgresql_where=sa.text("registro_idempotency_key IS NOT NULL"), sqlite_where=sa.text("registro_idempotency_key IS NOT NULL"))
    op.create_index("uq_gov_payments_referencia", "gov_payments", ["company_id", "method_id", "referencia_clave"], unique=True, postgresql_where=sa.text("referencia_clave IS NOT NULL"), sqlite_where=sa.text("referencia_clave IS NOT NULL"))

    op.create_table(
        "gov_payment_approvals",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("payment_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("actor_id", sa.String(36), nullable=False),
        sa.Column("cargo_id", sa.String(36), nullable=False),
        sa.Column("cargo_codigo", sa.String(30), nullable=False),
        sa.Column("cargo_nombre", sa.String(200), nullable=False),
        sa.Column("unidad", sa.String(250), nullable=True),
        sa.Column("funcionario_id", sa.String(36), nullable=True),
        sa.Column("funcionario_nombre", sa.String(200), nullable=True),
        sa.Column("requisito_indice", sa.Integer(), nullable=True),
        sa.Column("competencia_accion", sa.String(16), nullable=True),
        sa.Column("competencia_materia", sa.String(16), nullable=True),
        sa.Column("decision", sa.String(10), nullable=False),
        sa.Column("motivo", sa.String(500), nullable=True),
        sa.Column("policy_numero_version", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["payment_id"], ["gov_payments.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["cargo_id"], ["gov_positions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payment_id", "actor_id", name="uq_gov_payment_approvals_payment_actor"),
        sa.CheckConstraint(f"decision IN ({_en(*DECISIONES_APROBACION_PAGO)})", name="decision"),
        sa.CheckConstraint("decision = 'APROBADA' OR motivo IS NOT NULL", name="motivo"),
        sa.CheckConstraint("decision = 'RECHAZADA' OR requisito_indice IS NOT NULL", name="requisito"),
    )
    op.create_index("ix_gov_payment_approvals_payment_id", "gov_payment_approvals", ["payment_id"])
    op.create_index("ix_gov_payment_approvals_company_id", "gov_payment_approvals", ["company_id"])

    op.create_table(
        "gov_payment_documents",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("payment_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("etapa", sa.String(10), nullable=False),
        sa.Column("document_id", sa.String(36), nullable=False),
        sa.Column("document_type_id", sa.String(36), nullable=False),
        sa.Column("document_version_id", sa.String(36), nullable=True),
        sa.Column("sha256", sa.String(64), nullable=True),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["payment_id"], ["gov_payments.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["document_type_id"], ["document_types.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payment_id", "document_id", "etapa", name="uq_gov_payment_documents_payment_doc_etapa"),
        sa.CheckConstraint(f"etapa IN ({_en(*ETAPAS_DOCUMENTO_PAGO)})", name="etapa"),
    )
    op.create_index("ix_gov_payment_documents_payment_id", "gov_payment_documents", ["payment_id"])
    op.create_index("ix_gov_payment_documents_company_id", "gov_payment_documents", ["company_id"])

    op.create_table(
        "gov_payment_history",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("payment_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("evento", sa.String(32), nullable=False),
        sa.Column("actor_id", sa.String(36), nullable=True),
        sa.Column("instantanea", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["payment_id"], ["gov_payments.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_gov_payment_history_payment_id", "gov_payment_history", ["payment_id"])
    op.create_index("ix_gov_payment_history_company_id", "gov_payment_history", ["company_id"])

    _proceso_sod(op.get_bind(), *PROCESOS_SOD, "TRE-04")

    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            """
CREATE OR REPLACE FUNCTION kontrol_gov_payment_guard() RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'TRUNCATE' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_PAYMENT_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_PAYMENT_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    IF OLD.estado IN ('REGISTRADO','RECHAZADO','ANULADO') THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_PAYMENT_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    IF NEW.company_id IS DISTINCT FROM OLD.company_id
        OR NEW.order_id IS DISTINCT FROM OLD.order_id
        OR NEW.created_by IS DISTINCT FROM OLD.created_by
        OR NEW.idempotency_key IS DISTINCT FROM OLD.idempotency_key THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_PAYMENT_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    RETURN NEW;
END; $$ LANGUAGE plpgsql
"""
        )
        op.execute("CREATE TRIGGER trg_gov_payments_guard BEFORE UPDATE OR DELETE ON gov_payments FOR EACH ROW EXECUTE FUNCTION kontrol_gov_payment_guard()")
        op.execute("CREATE TRIGGER trg_gov_payments_no_truncate BEFORE TRUNCATE ON gov_payments FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_payment_guard()")
        op.execute("CREATE TRIGGER trg_gov_payment_approvals_guard BEFORE UPDATE OR DELETE ON gov_payment_approvals FOR EACH ROW EXECUTE FUNCTION kontrol_gov_presupuesto_historia_inmutable()")
        op.execute("CREATE TRIGGER trg_gov_payment_approvals_no_truncate BEFORE TRUNCATE ON gov_payment_approvals FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_presupuesto_historia_inmutable()")
        op.execute("CREATE TRIGGER trg_gov_payment_documents_guard BEFORE UPDATE OR DELETE ON gov_payment_documents FOR EACH ROW EXECUTE FUNCTION kontrol_gov_presupuesto_historia_inmutable()")
        op.execute("CREATE TRIGGER trg_gov_payment_documents_no_truncate BEFORE TRUNCATE ON gov_payment_documents FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_presupuesto_historia_inmutable()")
        op.execute("CREATE TRIGGER trg_gov_payment_history_guard BEFORE UPDATE OR DELETE ON gov_payment_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_presupuesto_historia_inmutable()")
        op.execute("CREATE TRIGGER trg_gov_payment_history_no_truncate BEFORE TRUNCATE ON gov_payment_history FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_presupuesto_historia_inmutable()")
        op.execute("CREATE TRIGGER trg_gov_payment_policy_history_guard BEFORE UPDATE OR DELETE ON gov_payment_policy_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_presupuesto_historia_inmutable()")
        op.execute("CREATE TRIGGER trg_gov_payment_policy_history_no_truncate BEFORE TRUNCATE ON gov_payment_policy_history FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_presupuesto_historia_inmutable()")

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
        op.execute("DROP TRIGGER IF EXISTS trg_gov_payment_policy_history_guard ON gov_payment_policy_history")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_payment_policy_history_no_truncate ON gov_payment_policy_history")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_payment_history_guard ON gov_payment_history")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_payment_history_no_truncate ON gov_payment_history")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_payment_documents_guard ON gov_payment_documents")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_payment_documents_no_truncate ON gov_payment_documents")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_payment_approvals_guard ON gov_payment_approvals")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_payment_approvals_no_truncate ON gov_payment_approvals")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_payments_guard ON gov_payments")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_payments_no_truncate ON gov_payments")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_payment_guard()")

    op.drop_index("ix_gov_payment_history_company_id", table_name="gov_payment_history")
    op.drop_index("ix_gov_payment_history_payment_id", table_name="gov_payment_history")
    op.drop_table("gov_payment_history")

    op.drop_index("ix_gov_payment_documents_company_id", table_name="gov_payment_documents")
    op.drop_index("ix_gov_payment_documents_payment_id", table_name="gov_payment_documents")
    op.drop_table("gov_payment_documents")

    op.drop_index("ix_gov_payment_approvals_company_id", table_name="gov_payment_approvals")
    op.drop_index("ix_gov_payment_approvals_payment_id", table_name="gov_payment_approvals")
    op.drop_table("gov_payment_approvals")

    op.drop_index("uq_gov_payments_referencia", table_name="gov_payments")
    op.drop_index("uq_gov_payments_registro_idempotency", table_name="gov_payments")
    op.drop_index("uq_gov_payments_idempotency", table_name="gov_payments")
    op.drop_index("ix_gov_payments_method_id", table_name="gov_payments")
    op.drop_index("ix_gov_payments_account_id", table_name="gov_payments")
    op.drop_index("ix_gov_payments_policy_id", table_name="gov_payments")
    op.drop_index("ix_gov_payments_order_id", table_name="gov_payments")
    op.drop_index("ix_gov_payments_company_id", table_name="gov_payments")
    op.drop_table("gov_payments")

    op.drop_index("ix_gov_payment_policy_history_company_id", table_name="gov_payment_policy_history")
    op.drop_index("ix_gov_payment_policy_history_policy_id", table_name="gov_payment_policy_history")
    op.drop_table("gov_payment_policy_history")

    op.drop_index("ix_gov_payment_policy_documents_company_id", table_name="gov_payment_policy_documents")
    op.drop_index("ix_gov_payment_policy_documents_policy_id", table_name="gov_payment_policy_documents")
    op.drop_table("gov_payment_policy_documents")

    op.drop_index("ix_gov_payment_policy_bands_company_id", table_name="gov_payment_policy_bands")
    op.drop_index("ix_gov_payment_policy_bands_policy_id", table_name="gov_payment_policy_bands")
    op.drop_table("gov_payment_policy_bands")

    op.drop_index("ix_gov_payment_policy_methods_method_id", table_name="gov_payment_policy_methods")
    op.drop_index("ix_gov_payment_policy_methods_company_id", table_name="gov_payment_policy_methods")
    op.drop_index("ix_gov_payment_policy_methods_policy_id", table_name="gov_payment_policy_methods")
    op.drop_table("gov_payment_policy_methods")

    op.drop_index("ix_gov_payment_policies_company_id", table_name="gov_payment_policies")
    op.drop_table("gov_payment_policies")

    op.drop_index("ix_gov_payment_methods_company_id", table_name="gov_payment_methods")
    op.drop_table("gov_payment_methods")

    op.drop_index("ix_gov_payment_settings_company_id", table_name="gov_payment_settings")
    op.drop_table("gov_payment_settings")
