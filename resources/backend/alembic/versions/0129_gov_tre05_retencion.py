"""TRE-05: retenciones con maker-checker, politica de retencion y comprobantes."""
from __future__ import annotations

import uuid

import sqlalchemy as sa

from alembic import op

revision = "0129_gov_tre05_retencion"
down_revision = "0128_gov_tre04_pago"
branch_labels = None
depends_on = None

PERMISOS = {"gobierno_retenciones": ("view", "manage", "calculate", "policy", "approve", "cancel")}
PROCESOS_SOD = ("DOC-02", "CTL-06", "TRE-01", "TRE-02", "CTL-10", "ORG-04", "ORG-06", "PROC-02", "PROC-03", "BUD-09", "TRE-03", "TRE-04")

TIPOS_CATALOGO_RETENCION = ("CONCEPTO", "CONDICION")
CLASES_CONCEPTO_RETENCION = ("TRIBUTARIA", "CONTRACTUAL", "OTRA")
ESTADOS_CATALOGO_RETENCION = ("ACTIVO", "INACTIVO")
ESTADOS_POLITICA_RETENCION = ("BORRADOR", "VIGENTE", "CERRADA")
VERIFICACION_REGLA_RETENCION = ("PENDING_PIN", "VERIFIED")
MODOS_REDONDEO_RETENCION = ("HALF_UP", "HALF_EVEN", "DOWN")
BASES_RETENCION = ("MONTO_BRUTO", "PORCENTAJE_DEL_BRUTO")
UMBRALES_RETENCION = ("NINGUNO", "MONTO", "MULTIPLO_TASA")
TIPOS_PERSONA_RETENCION = ("NATURAL", "JURIDICA")
ESTADOS_LIQUIDACION_RETENCION = ("CALCULADA", "APROBADA", "APLICADA", "ANULADA")
MOTIVOS_NO_APLICA_RETENCION = ("CONCEPTO_NO_SELECCIONADO", "TIPO_PERSONA", "CONDICION_FALTANTE", "EXCLUSION", "UMBRAL", "SIN_MONTO")
ESTADOS_COMPROBANTE_RETENCION = ("EMITIDO", "ANULADO")
RECURSOS_HISTORIA_RETENCION = ("POLITICA", "LIQUIDACION", "COMPROBANTE")
TIPOS_REGLA_ORDEN_PAGO = ("INSTITUTIONAL_POLICY", "OPERATIONAL_CONFIGURATION", "LEGAL_MANDATORY")
ACCIONES_COMPETENCIA = ("SOLICITAR", "COMPROMETER", "CAUSAR", "ORDENAR_PAGO", "PAGAR", "REGISTRAR", "CUSTODIAR", "APROBAR", "AUDITAR", "FIRMAR")
MATERIAS_COMPETENCIA = ("PRESUPUESTO", "CONTRATACIONES", "TESORERIA", "CONTABILIDAD", "BIENES", "EXPEDIENTE")
MONEDAS_LIMITE = ("VES", "USD", "EUR")
MONEDAS_TASA = ("USD", "EUR")


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
    bind = op.get_bind()

    op.create_table(
        "gov_withholding_settings",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("patron", sa.String(60), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", name="uq_gov_withholding_settings_company_id"),
    )
    op.create_index("ix_gov_withholding_settings_company_id", "gov_withholding_settings", ["company_id"])

    op.create_table(
        "gov_withholding_catalog",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("tipo", sa.String(10), nullable=False),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("nombre", sa.String(120), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("clase", sa.String(12), nullable=True),
        sa.Column("serie_comprobante", sa.String(10), nullable=True),
        sa.Column("estado", sa.String(10), nullable=False, server_default="ACTIVO"),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "tipo", "codigo", name="uq_gov_withholding_catalog_company_tipo_codigo"),
        sa.CheckConstraint(f"tipo IN ({_en(*TIPOS_CATALOGO_RETENCION)})", name="tipo"),
        sa.CheckConstraint(f"estado IN ({_en(*ESTADOS_CATALOGO_RETENCION)})", name="estado"),
        sa.CheckConstraint(f"clase IS NULL OR clase IN ({_en(*CLASES_CONCEPTO_RETENCION)})", name="clase_valor"),
        sa.CheckConstraint("(tipo = 'CONCEPTO') = (clase IS NOT NULL)", name="clase"),
        sa.CheckConstraint("tipo = 'CONCEPTO' OR serie_comprobante IS NULL", name="serie"),
    )
    op.create_index("ix_gov_withholding_catalog_company_id", "gov_withholding_catalog", ["company_id"])

    op.create_table(
        "gov_withholding_policies",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("numero_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("version_anterior_id", sa.String(36), nullable=True),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("moneda", sa.String(3), nullable=False),
        sa.Column("tipo_regla", sa.String(26), nullable=False, server_default="INSTITUTIONAL_POLICY"),
        sa.Column("estado_verificacion", sa.String(12), nullable=False, server_default="PENDING_PIN"),
        sa.Column("fuente_descripcion", sa.String(500), nullable=True),
        sa.Column("fuente_referencia", sa.String(200), nullable=True),
        sa.Column("fuente_documento_id", sa.String(36), nullable=True),
        sa.Column("act_id", sa.String(36), nullable=True),
        sa.Column("aprobador_competencia_accion", sa.String(16), nullable=False),
        sa.Column("aprobador_competencia_materia", sa.String(16), nullable=False),
        sa.Column("permite_ajuste", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("redondeo_decimales", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("redondeo_modo", sa.String(10), nullable=False, server_default="HALF_UP"),
        sa.Column("vigente_desde", sa.Date(), nullable=False),
        sa.Column("vigente_hasta", sa.Date(), nullable=True),
        sa.Column("fundamento", sa.String(2000), nullable=True),
        sa.Column("estado", sa.String(10), nullable=False, server_default="BORRADOR"),
        sa.Column("activada_por", sa.String(36), nullable=True),
        sa.Column("activada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cerrada_por", sa.String(36), nullable=True),
        sa.Column("cerrada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("motivo_cierre", sa.String(500), nullable=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["version_anterior_id"], ["gov_withholding_policies.id"]),
        sa.ForeignKeyConstraint(["fuente_documento_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["act_id"], ["gov_acts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "codigo", "numero_version", name="uq_gov_withholding_policies_company_codigo_version"),
        sa.CheckConstraint(f"estado IN ({_en(*ESTADOS_POLITICA_RETENCION)})", name="estado"),
        sa.CheckConstraint(f"tipo_regla IN ({_en(*TIPOS_REGLA_ORDEN_PAGO)})", name="tipo_regla"),
        sa.CheckConstraint(f"estado_verificacion IN ({_en(*VERIFICACION_REGLA_RETENCION)})", name="verificacion"),
        sa.CheckConstraint(f"moneda IN ({_en(*MONEDAS_LIMITE)})", name="moneda"),
        sa.CheckConstraint(f"redondeo_modo IN ({_en(*MODOS_REDONDEO_RETENCION)})", name="redondeo_modo"),
        sa.CheckConstraint(f"aprobador_competencia_accion IN ({_en(*ACCIONES_COMPETENCIA)})", name="aprobador_accion"),
        sa.CheckConstraint(f"aprobador_competencia_materia IN ({_en(*MATERIAS_COMPETENCIA)})", name="aprobador_materia"),
        sa.CheckConstraint("redondeo_decimales BETWEEN 0 AND 4", name="decimales"),
        sa.CheckConstraint("numero_version >= 1", name="numero_version"),
        sa.CheckConstraint("vigente_hasta IS NULL OR vigente_hasta >= vigente_desde", name="vigencia"),
        sa.CheckConstraint("estado = 'BORRADOR' OR (fundamento IS NOT NULL AND fuente_descripcion IS NOT NULL)", name="fundamento"),
        sa.CheckConstraint("tipo_regla <> 'LEGAL_MANDATORY' OR estado_verificacion = 'VERIFIED'", name="legal"),
    )
    op.create_index("ix_gov_withholding_policies_company_id", "gov_withholding_policies", ["company_id"])
    op.create_index("ix_gov_withholding_policies_version_anterior_id", "gov_withholding_policies", ["version_anterior_id"])
    op.create_index("ix_gov_withholding_policies_fuente_documento_id", "gov_withholding_policies", ["fuente_documento_id"])
    op.create_index("ix_gov_withholding_policies_act_id", "gov_withholding_policies", ["act_id"])

    op.create_table(
        "gov_withholding_policy_rules",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("policy_id", sa.String(36), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.Column("concept_id", sa.String(36), nullable=False),
        sa.Column("base_tipo", sa.String(20), nullable=False),
        sa.Column("base_porcentaje", sa.Numeric(9, 4), nullable=True),
        sa.Column("tasa", sa.Numeric(9, 4), nullable=False),
        sa.Column("umbral_tipo", sa.String(16), nullable=False, server_default="NINGUNO"),
        sa.Column("umbral_monto", sa.Numeric(18, 2), nullable=True),
        sa.Column("umbral_multiplo", sa.Numeric(18, 4), nullable=True),
        sa.Column("umbral_moneda_tasa", sa.String(3), nullable=True),
        sa.Column("sustraendo", sa.Numeric(18, 2), nullable=True),
        sa.Column("tope", sa.Numeric(18, 2), nullable=True),
        sa.Column("condiciones_exigidas", sa.JSON(), nullable=False),
        sa.Column("exclusiones", sa.JSON(), nullable=False),
        sa.Column("tipos_persona", sa.JSON(), nullable=True),
        sa.Column("exige_comprobante", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["policy_id"], ["gov_withholding_policies.id"]),
        sa.ForeignKeyConstraint(["concept_id"], ["gov_withholding_catalog.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("policy_id", "orden", name="uq_gov_withholding_policy_rules_policy_orden"),
        sa.UniqueConstraint("policy_id", "concept_id", name="uq_gov_withholding_policy_rules_policy_concept"),
        sa.CheckConstraint(f"base_tipo IN ({_en(*BASES_RETENCION)})", name="base_tipo"),
        sa.CheckConstraint(f"umbral_tipo IN ({_en(*UMBRALES_RETENCION)})", name="umbral_tipo"),
        sa.CheckConstraint("orden >= 1", name="orden"),
        sa.CheckConstraint("tasa > 0 AND tasa <= 100", name="tasa"),
        sa.CheckConstraint("(base_tipo = 'PORCENTAJE_DEL_BRUTO') = (base_porcentaje IS NOT NULL)", name="base"),
        sa.CheckConstraint("base_porcentaje IS NULL OR (base_porcentaje > 0 AND base_porcentaje <= 100)", name="base_porcentaje"),
        sa.CheckConstraint("(umbral_tipo = 'MONTO') = (umbral_monto IS NOT NULL)", name="umbral_monto"),
        sa.CheckConstraint("(umbral_tipo = 'MULTIPLO_TASA') = (umbral_multiplo IS NOT NULL AND umbral_moneda_tasa IS NOT NULL)", name="umbral_tasa"),
        sa.CheckConstraint("umbral_monto IS NULL OR umbral_monto >= 0", name="umbral_monto_valor"),
        sa.CheckConstraint("umbral_multiplo IS NULL OR umbral_multiplo > 0", name="umbral_multiplo_valor"),
        sa.CheckConstraint(f"umbral_moneda_tasa IS NULL OR umbral_moneda_tasa IN ({_en(*MONEDAS_TASA)})", name="umbral_moneda_tasa"),
        sa.CheckConstraint("sustraendo IS NULL OR sustraendo >= 0", name="sustraendo"),
        sa.CheckConstraint("tope IS NULL OR tope > 0", name="tope"),
    )
    op.create_index("ix_gov_withholding_policy_rules_company_id", "gov_withholding_policy_rules", ["company_id"])
    op.create_index("ix_gov_withholding_policy_rules_policy_id", "gov_withholding_policy_rules", ["policy_id"])
    op.create_index("ix_gov_withholding_policy_rules_concept_id", "gov_withholding_policy_rules", ["concept_id"])

    op.create_table(
        "gov_withholding_settlements",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("payment_id", sa.String(36), nullable=False),
        sa.Column("policy_id", sa.String(36), nullable=False),
        sa.Column("policy_numero_version", sa.Integer(), nullable=False),
        sa.Column("policy_snapshot", sa.JSON(), nullable=False),
        sa.Column("estado", sa.String(10), nullable=False, server_default="CALCULADA"),
        sa.Column("fecha_referencia", sa.Date(), nullable=False),
        sa.Column("moneda", sa.String(3), nullable=False),
        sa.Column("bruto", sa.Numeric(18, 2), nullable=False),
        sa.Column("total_retenido", sa.Numeric(18, 2), nullable=False),
        sa.Column("neto", sa.Numeric(18, 2), nullable=False),
        sa.Column("conceptos", sa.JSON(), nullable=False),
        sa.Column("beneficiario", sa.JSON(), nullable=False),
        sa.Column("calculado_por", sa.String(36), nullable=False),
        sa.Column("calculado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("aprobado_por", sa.String(36), nullable=True),
        sa.Column("aprobado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("aprobador_cargo_id", sa.String(36), nullable=True),
        sa.Column("aprobador_cargo_codigo", sa.String(40), nullable=True),
        sa.Column("aprobador_cargo_nombre", sa.String(200), nullable=True),
        sa.Column("aprobador_unidad", sa.String(200), nullable=True),
        sa.Column("aprobador_funcionario_id", sa.String(36), nullable=True),
        sa.Column("aprobador_funcionario_nombre", sa.String(200), nullable=True),
        sa.Column("aplicado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("anulado_por", sa.String(36), nullable=True),
        sa.Column("anulado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("motivo_anulacion", sa.String(500), nullable=True),
        sa.Column("huella", sa.String(64), nullable=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["payment_id"], ["gov_payments.id"]),
        sa.ForeignKeyConstraint(["policy_id"], ["gov_withholding_policies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(f"estado IN ({_en(*ESTADOS_LIQUIDACION_RETENCION)})", name="estado"),
        sa.CheckConstraint(f"moneda IN ({_en(*MONEDAS_LIMITE)})", name="moneda"),
        sa.CheckConstraint("bruto > 0", name="bruto"),
        sa.CheckConstraint("total_retenido >= 0", name="total_retenido"),
        sa.CheckConstraint("neto >= 0", name="neto"),
        sa.CheckConstraint("bruto = total_retenido + neto", name="cuadre"),
        sa.CheckConstraint("estado IN ('CALCULADA','ANULADA') OR (aprobado_por IS NOT NULL AND aprobado_en IS NOT NULL AND aprobador_cargo_id IS NOT NULL AND huella IS NOT NULL)", name="aprobacion"),
        sa.CheckConstraint("(estado = 'APLICADA') = (aplicado_en IS NOT NULL)", name="aplicacion"),
        sa.CheckConstraint("(estado = 'ANULADA') = (anulado_por IS NOT NULL AND anulado_en IS NOT NULL AND motivo_anulacion IS NOT NULL)", name="anulacion"),
    )
    op.create_index("ix_gov_withholding_settlements_company_id", "gov_withholding_settlements", ["company_id"])
    op.create_index(
        "uq_gov_withholding_settlements_activa",
        "gov_withholding_settlements",
        ["company_id", "payment_id"],
        unique=True,
        postgresql_where=sa.text("estado <> 'ANULADA'"),
        sqlite_where=sa.text("estado <> 'ANULADA'"),
    )
    op.create_index("ix_gov_withholding_settlements_payment_id", "gov_withholding_settlements", ["payment_id"])
    op.create_index("ix_gov_withholding_settlements_policy_id", "gov_withholding_settlements", ["policy_id"])

    op.create_table(
        "gov_withholding_settlement_lines",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("settlement_id", sa.String(36), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.Column("rule_snapshot", sa.JSON(), nullable=False),
        sa.Column("concept_id", sa.String(36), nullable=False),
        sa.Column("concepto_codigo", sa.String(20), nullable=False),
        sa.Column("concepto_nombre", sa.String(120), nullable=False),
        sa.Column("clase", sa.String(12), nullable=True),
        sa.Column("base", sa.Numeric(18, 2), nullable=False),
        sa.Column("tasa", sa.Numeric(9, 4), nullable=False),
        sa.Column("umbral", sa.Numeric(18, 2), nullable=True),
        sa.Column("tasa_referencia", sa.JSON(), nullable=True),
        sa.Column("aplica", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("motivo_no_aplica", sa.String(30), nullable=True),
        sa.Column("monto_calculado", sa.Numeric(18, 2), nullable=False),
        sa.Column("monto_aprobado", sa.Numeric(18, 2), nullable=False),
        sa.Column("motivo_ajuste", sa.String(500), nullable=True),
        sa.Column("ajustado_por", sa.String(36), nullable=True),
        sa.Column("ajustado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("exige_comprobante", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["settlement_id"], ["gov_withholding_settlements.id"]),
        sa.ForeignKeyConstraint(["concept_id"], ["gov_withholding_catalog.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("aplica OR (monto_calculado = 0 AND monto_aprobado = 0 AND motivo_no_aplica IS NOT NULL)", name="no_aplica"),
        sa.CheckConstraint("monto_aprobado >= 0", name="aprobado"),
        sa.CheckConstraint("monto_aprobado = monto_calculado OR motivo_ajuste IS NOT NULL", name="ajuste"),
        sa.CheckConstraint(f"motivo_no_aplica IS NULL OR motivo_no_aplica IN ({_en(*MOTIVOS_NO_APLICA_RETENCION)})", name="motivo_no_aplica"),
        sa.CheckConstraint("base >= 0", name="base"),
        sa.CheckConstraint("orden >= 1", name="orden"),
    )
    op.create_index("ix_gov_withholding_settlement_lines_company_id", "gov_withholding_settlement_lines", ["company_id"])
    op.create_index("ix_gov_withholding_settlement_lines_settlement_id", "gov_withholding_settlement_lines", ["settlement_id"])
    op.create_index("ix_gov_withholding_settlement_lines_concept_id", "gov_withholding_settlement_lines", ["concept_id"])

    op.create_table(
        "gov_withholding_receipts",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("settlement_id", sa.String(36), nullable=False),
        sa.Column("payment_id", sa.String(36), nullable=False),
        sa.Column("concept_id", sa.String(36), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("serie", sa.String(10), nullable=True),
        sa.Column("codigo", sa.String(60), nullable=False),
        sa.Column("estado", sa.String(10), nullable=False, server_default="EMITIDO"),
        sa.Column("sustituye_a_id", sa.String(36), nullable=True),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("huella", sa.String(64), nullable=False),
        sa.Column("document_id", sa.String(36), nullable=True),
        sa.Column("emitido_por", sa.String(36), nullable=False),
        sa.Column("emitido_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("anulado_por", sa.String(36), nullable=True),
        sa.Column("anulado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("motivo_anulacion", sa.String(500), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["settlement_id"], ["gov_withholding_settlements.id"]),
        sa.ForeignKeyConstraint(["payment_id"], ["gov_payments.id"]),
        sa.ForeignKeyConstraint(["concept_id"], ["gov_withholding_catalog.id"]),
        sa.ForeignKeyConstraint(["sustituye_a_id"], ["gov_withholding_receipts.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "codigo", name="uq_gov_withholding_receipts_company_codigo"),
        sa.CheckConstraint(f"estado IN ({_en(*ESTADOS_COMPROBANTE_RETENCION)})", name="estado"),
        sa.CheckConstraint("(estado = 'ANULADO') = (anulado_por IS NOT NULL AND anulado_en IS NOT NULL AND motivo_anulacion IS NOT NULL)", name="anulacion"),
        sa.CheckConstraint("numero >= 1", name="numero"),
    )
    op.create_index("ix_gov_withholding_receipts_company_id", "gov_withholding_receipts", ["company_id"])
    op.create_index("ix_gov_withholding_receipts_settlement_id", "gov_withholding_receipts", ["settlement_id"])
    op.create_index("ix_gov_withholding_receipts_payment_id", "gov_withholding_receipts", ["payment_id"])
    op.create_index("ix_gov_withholding_receipts_concept_id", "gov_withholding_receipts", ["concept_id"])
    op.create_index("ix_gov_withholding_receipts_sustituye_a_id", "gov_withholding_receipts", ["sustituye_a_id"])
    op.create_index("ix_gov_withholding_receipts_document_id", "gov_withholding_receipts", ["document_id"])

    op.create_table(
        "gov_withholding_history",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("recurso", sa.String(12), nullable=False),
        sa.Column("recurso_id", sa.String(36), nullable=False),
        sa.Column("evento", sa.String(40), nullable=False),
        sa.Column("actor_id", sa.String(36), nullable=True),
        sa.Column("instantanea", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(f"recurso IN ({_en(*RECURSOS_HISTORIA_RETENCION)})", name="recurso"),
    )
    op.create_index("ix_gov_withholding_history_company_id", "gov_withholding_history", ["company_id"])
    op.create_index("ix_gov_withholding_history_recurso_id", "gov_withholding_history", ["recurso_id"])

    if bind.dialect.name == "postgresql":
        op.execute("""
CREATE OR REPLACE FUNCTION kontrol_gov_withholding_settlement_guard() RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'TRUNCATE' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_WITHHOLDING_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_WITHHOLDING_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    IF OLD.estado IN ('APLICADA', 'ANULADA') THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_WITHHOLDING_IMMUTABLE', DETAIL = 'SETTLEMENT_APPLIED_OR_ANNULLED';
    END IF;
    IF OLD.company_id IS DISTINCT FROM NEW.company_id
        OR OLD.payment_id IS DISTINCT FROM NEW.payment_id
        OR OLD.policy_id IS DISTINCT FROM NEW.policy_id
        OR OLD.calculado_por IS DISTINCT FROM NEW.calculado_por THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_WITHHOLDING_IMMUTABLE', DETAIL = 'SETTLEMENT_KEY_CHANGE';
    END IF;
    IF OLD.estado = 'APROBADA' THEN
        IF OLD.bruto IS DISTINCT FROM NEW.bruto
            OR OLD.total_retenido IS DISTINCT FROM NEW.total_retenido
            OR OLD.neto IS DISTINCT FROM NEW.neto
            OR OLD.policy_snapshot::text IS DISTINCT FROM NEW.policy_snapshot::text
            OR OLD.beneficiario::text IS DISTINCT FROM NEW.beneficiario::text
            OR OLD.conceptos::text IS DISTINCT FROM NEW.conceptos::text
            OR OLD.huella IS DISTINCT FROM NEW.huella
            OR OLD.policy_numero_version IS DISTINCT FROM NEW.policy_numero_version THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_WITHHOLDING_IMMUTABLE', DETAIL = 'APPROVED_SETTLEMENT_CHANGE';
        END IF;
        IF NEW.estado NOT IN ('APLICADA', 'ANULADA') THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_WITHHOLDING_IMMUTABLE', DETAIL = 'APPROVED_SETTLEMENT_INVALID_TRANSITION';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
""")
        op.execute("""
CREATE OR REPLACE FUNCTION kontrol_gov_withholding_line_guard() RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'TRUNCATE' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_WITHHOLDING_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    IF TG_OP = 'DELETE' THEN
        IF (SELECT estado FROM gov_withholding_settlements WHERE id = OLD.settlement_id) <> 'CALCULADA' THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_WITHHOLDING_IMMUTABLE', DETAIL = 'LINE_DELETE_LOCKED';
        END IF;
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_WITHHOLDING_IMMUTABLE', DETAIL = 'LINE_DELETE';
    END IF;
    IF (SELECT estado FROM gov_withholding_settlements WHERE id = OLD.settlement_id) <> 'CALCULADA' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_WITHHOLDING_IMMUTABLE', DETAIL = 'LINE_UPDATE_LOCKED';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
""")
        op.execute("""
CREATE OR REPLACE FUNCTION kontrol_gov_withholding_receipt_guard() RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'TRUNCATE' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_WITHHOLDING_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_WITHHOLDING_IMMUTABLE', DETAIL = 'RECEIPT_DELETE';
    END IF;
    IF OLD.estado = 'ANULADO' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_WITHHOLDING_IMMUTABLE', DETAIL = 'RECEIPT_ANNULLED';
    END IF;
    IF NEW.estado NOT IN ('EMITIDO', 'ANULADO') THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_WITHHOLDING_IMMUTABLE', DETAIL = 'RECEIPT_INVALID_STATE';
    END IF;
    IF OLD.codigo IS DISTINCT FROM NEW.codigo
        OR OLD.numero IS DISTINCT FROM NEW.numero
        OR OLD.serie IS DISTINCT FROM NEW.serie
        OR OLD.snapshot::text IS DISTINCT FROM NEW.snapshot::text
        OR OLD.huella IS DISTINCT FROM NEW.huella
        OR OLD.settlement_id IS DISTINCT FROM NEW.settlement_id
        OR OLD.payment_id IS DISTINCT FROM NEW.payment_id
        OR OLD.concept_id IS DISTINCT FROM NEW.concept_id
        OR OLD.company_id IS DISTINCT FROM NEW.company_id THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_WITHHOLDING_IMMUTABLE', DETAIL = 'RECEIPT_KEY_CHANGE';
    END IF;
    IF OLD.document_id IS NOT NULL AND OLD.document_id IS DISTINCT FROM NEW.document_id THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_WITHHOLDING_IMMUTABLE', DETAIL = 'RECEIPT_DOCUMENT_CHANGE';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
""")
        op.execute("""
CREATE OR REPLACE FUNCTION kontrol_gov_withholding_policy_guard() RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'TRUNCATE' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_WITHHOLDING_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_WITHHOLDING_IMMUTABLE', DETAIL = 'POLICY_DELETE';
    END IF;
    IF OLD.estado = 'CERRADA' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_WITHHOLDING_IMMUTABLE', DETAIL = 'POLICY_CLOSED';
    END IF;
    IF OLD.estado = 'VIGENTE' THEN
        IF NEW.estado <> 'CERRADA' THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_WITHHOLDING_IMMUTABLE', DETAIL = 'POLICY_ACTIVE_TRANSITION';
        END IF;
        IF OLD.codigo IS DISTINCT FROM NEW.codigo
            OR OLD.numero_version IS DISTINCT FROM NEW.numero_version
            OR OLD.nombre IS DISTINCT FROM NEW.nombre
            OR OLD.moneda IS DISTINCT FROM NEW.moneda
            OR OLD.tipo_regla IS DISTINCT FROM NEW.tipo_regla
            OR OLD.estado_verificacion IS DISTINCT FROM NEW.estado_verificacion
            OR OLD.fuente_descripcion IS DISTINCT FROM NEW.fuente_descripcion
            OR OLD.fuente_referencia IS DISTINCT FROM NEW.fuente_referencia
            OR OLD.fuente_documento_id IS DISTINCT FROM NEW.fuente_documento_id
            OR OLD.act_id IS DISTINCT FROM NEW.act_id
            OR OLD.aprobador_competencia_accion IS DISTINCT FROM NEW.aprobador_competencia_accion
            OR OLD.aprobador_competencia_materia IS DISTINCT FROM NEW.aprobador_competencia_materia
            OR OLD.permite_ajuste IS DISTINCT FROM NEW.permite_ajuste
            OR OLD.redondeo_decimales IS DISTINCT FROM NEW.redondeo_decimales
            OR OLD.redondeo_modo IS DISTINCT FROM NEW.redondeo_modo
            OR OLD.vigente_desde IS DISTINCT FROM NEW.vigente_desde
            OR OLD.fundamento IS DISTINCT FROM NEW.fundamento THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_WITHHOLDING_IMMUTABLE', DETAIL = 'ACTIVE_POLICY_CHANGE';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
""")
        op.execute("""
CREATE OR REPLACE FUNCTION kontrol_gov_withholding_rule_guard() RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'TRUNCATE' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_WITHHOLDING_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    IF TG_OP = 'DELETE' THEN
        IF (SELECT estado FROM gov_withholding_policies WHERE id = OLD.policy_id) <> 'BORRADOR' THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_WITHHOLDING_IMMUTABLE', DETAIL = 'RULE_DELETE_LOCKED';
        END IF;
        RETURN OLD;
    END IF;
    IF (SELECT estado FROM gov_withholding_policies WHERE id = OLD.policy_id) <> 'BORRADOR' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_WITHHOLDING_IMMUTABLE', DETAIL = 'RULE_UPDATE_LOCKED';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
""")
        op.execute("""
CREATE TRIGGER trg_gov_withholding_settlements_guard
    BEFORE UPDATE OR DELETE ON gov_withholding_settlements
    FOR EACH ROW EXECUTE FUNCTION kontrol_gov_withholding_settlement_guard();
""")
        op.execute("""
CREATE TRIGGER trg_gov_withholding_settlements_no_truncate
    BEFORE TRUNCATE ON gov_withholding_settlements
    FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_withholding_settlement_guard();
""")
        op.execute("""
CREATE TRIGGER trg_gov_withholding_settlement_lines_guard
    BEFORE UPDATE OR DELETE ON gov_withholding_settlement_lines
    FOR EACH ROW EXECUTE FUNCTION kontrol_gov_withholding_line_guard();
""")
        op.execute("""
CREATE TRIGGER trg_gov_withholding_settlement_lines_no_truncate
    BEFORE TRUNCATE ON gov_withholding_settlement_lines
    FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_withholding_line_guard();
""")
        op.execute("""
CREATE TRIGGER trg_gov_withholding_receipts_guard
    BEFORE UPDATE OR DELETE ON gov_withholding_receipts
    FOR EACH ROW EXECUTE FUNCTION kontrol_gov_withholding_receipt_guard();
""")
        op.execute("""
CREATE TRIGGER trg_gov_withholding_receipts_no_truncate
    BEFORE TRUNCATE ON gov_withholding_receipts
    FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_withholding_receipt_guard();
""")
        op.execute("""
CREATE TRIGGER trg_gov_withholding_policies_guard
    BEFORE UPDATE OR DELETE ON gov_withholding_policies
    FOR EACH ROW EXECUTE FUNCTION kontrol_gov_withholding_policy_guard();
""")
        op.execute("""
CREATE TRIGGER trg_gov_withholding_policies_no_truncate
    BEFORE TRUNCATE ON gov_withholding_policies
    FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_withholding_policy_guard();
""")
        op.execute("""
CREATE TRIGGER trg_gov_withholding_policy_rules_guard
    BEFORE UPDATE OR DELETE ON gov_withholding_policy_rules
    FOR EACH ROW EXECUTE FUNCTION kontrol_gov_withholding_rule_guard();
""")
        op.execute("""
CREATE TRIGGER trg_gov_withholding_policy_rules_no_truncate
    BEFORE TRUNCATE ON gov_withholding_policy_rules
    FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_withholding_rule_guard();
""")
        op.execute("""
CREATE TRIGGER trg_gov_withholding_history_guard
    BEFORE UPDATE OR DELETE ON gov_withholding_history
    FOR EACH ROW EXECUTE FUNCTION kontrol_gov_presupuesto_historia_inmutable();
""")
        op.execute("""
CREATE TRIGGER trg_gov_withholding_history_no_truncate
    BEFORE TRUNCATE ON gov_withholding_history
    FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_presupuesto_historia_inmutable();
""")

    _conceder_permisos(bind)
    _proceso_sod(bind, *PROCESOS_SOD, "TRE-05")


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
        op.execute("DROP TRIGGER IF EXISTS trg_gov_withholding_history_guard ON gov_withholding_history")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_withholding_history_no_truncate ON gov_withholding_history")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_withholding_policy_rules_guard ON gov_withholding_policy_rules")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_withholding_policy_rules_no_truncate ON gov_withholding_policy_rules")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_withholding_policies_guard ON gov_withholding_policies")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_withholding_policies_no_truncate ON gov_withholding_policies")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_withholding_receipts_guard ON gov_withholding_receipts")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_withholding_receipts_no_truncate ON gov_withholding_receipts")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_withholding_settlement_lines_guard ON gov_withholding_settlement_lines")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_withholding_settlement_lines_no_truncate ON gov_withholding_settlement_lines")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_withholding_settlements_guard ON gov_withholding_settlements")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_withholding_settlements_no_truncate ON gov_withholding_settlements")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_withholding_rule_guard()")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_withholding_policy_guard()")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_withholding_receipt_guard()")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_withholding_line_guard()")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_withholding_settlement_guard()")

    op.drop_table("gov_withholding_history")
    op.drop_table("gov_withholding_receipts")
    op.drop_table("gov_withholding_settlement_lines")
    op.drop_table("gov_withholding_settlements")
    op.drop_table("gov_withholding_policy_rules")
    op.drop_table("gov_withholding_policies")
    op.drop_table("gov_withholding_catalog")
    op.drop_table("gov_withholding_settings")
