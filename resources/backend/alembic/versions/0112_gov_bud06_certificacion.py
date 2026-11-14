"""BUD-06: certificaciones de disponibilidad presupuestaria y permiso gobierno_presupuesto:certify (LOPPM 242)."""

from __future__ import annotations

import uuid

import sqlalchemy as sa

from alembic import op

revision = "0112_gov_bud06_certificacion"
down_revision = "0111_gov_bud05_aprobado"
branch_labels = None
depends_on = None

PERMISOS = {"gobierno_presupuesto": ("certify",)}


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


def _en(*valores: str) -> str:
    return ", ".join(f"'{v}'" for v in valores)


TIPOS_HISTORIA_0111 = _en(
    'CREADO', 'NIVELES_CONFIGURADOS', 'CATEGORIA_CREADA', 'CATEGORIA_MODIFICADA',
    'CATEGORIA_ELIMINADA', 'CLASIFICADOR_REGISTRADO', 'PROCEDENCIA_MODIFICADA',
    'PARTIDA_CREADA', 'PARTIDA_ELIMINADA', 'PARTIDAS_IMPORTADAS', 'APROBADO',
    'RECONDUCIDO', 'CERRADO', 'PRECOMPROMISO_CAMBIADO',
    'PLAN_REGISTRADO', 'OBJETIVO_CREADO', 'OBJETIVO_MODIFICADO', 'OBJETIVO_ELIMINADO',
    'CATEGORIA_VINCULADA', 'META_CREADA', 'META_MODIFICADA', 'META_ELIMINADA', 'FUENTE_CREADA',
    'FUENTE_MODIFICADA', 'FUENTE_ELIMINADA', 'RESTRICCION_AGREGADA', 'RESTRICCION_ELIMINADA',
    'INGRESO_REGISTRADO', 'INGRESO_MODIFICADO', 'INGRESO_ELIMINADO',
    'CREDITO_REGISTRADO', 'CREDITO_MODIFICADO', 'CREDITO_ELIMINADO',
    'EXISTENCIAS_REGISTRADAS', 'EXISTENCIAS_ELIMINADAS',
)
TIPOS_HISTORIA = TIPOS_HISTORIA_0111 + ", " + _en('CERTIFICACION_EMITIDA', 'CERTIFICACION_ANULADA')


def upgrade() -> None:
    op.create_table(
        "gov_budget_certificates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("year_id", sa.String(36), sa.ForeignKey("gov_budget_years.id"), nullable=False),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("credit_id", sa.String(36), sa.ForeignKey("gov_budget_credits.id"), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("estado", sa.String(10), server_default="VIGENTE", nullable=False),
        sa.Column("monto", sa.Numeric(18, 2), nullable=False),
        sa.Column("saldo_antes", sa.Numeric(18, 2), nullable=False),
        sa.Column("saldo_despues", sa.Numeric(18, 2), nullable=False),
        sa.Column("moneda", sa.String(3), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("concepto", sa.String(500), nullable=False),
        sa.Column("expediente_referencia", sa.String(120), nullable=False),
        sa.Column("procurement_file_id", sa.String(36), sa.ForeignKey("gov_procurement_files.id"), nullable=True),
        sa.Column("firmante_cargo_id", sa.String(36), sa.ForeignKey("gov_positions.id"), nullable=False),
        sa.Column("firmante_cargo_codigo", sa.String(30), nullable=False),
        sa.Column("firmante_cargo_nombre", sa.String(200), nullable=False),
        sa.Column("firmante_unidad", sa.String(250), nullable=False),
        sa.Column("firmante_funcionario_id", sa.String(36), nullable=True),
        sa.Column("firmante_funcionario_nombre", sa.String(200), nullable=True),
        sa.Column("emitida_por", sa.String(36), nullable=False),
        sa.Column("emitida_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("huella", sa.String(64), nullable=False),
        sa.Column("documento_storage_key", sa.String(255), nullable=False),
        sa.Column("documento_sha256", sa.String(64), nullable=False),
        sa.Column("documento_tamano", sa.Integer(), nullable=False),
        sa.Column("documento_nombre", sa.String(200), nullable=False),
        sa.Column("anulada_por", sa.String(36), nullable=True),
        sa.Column("anulada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("motivo_anulacion", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.UniqueConstraint("year_id", "numero", name="uq_gov_budget_certificates_year_id_numero"),
        sa.UniqueConstraint("company_id", "codigo", name="uq_gov_budget_certificates_company_id_codigo"),
        sa.CheckConstraint("estado IN ('VIGENTE', 'ANULADA')", name="ck_gov_budget_certificates_estado"),
        sa.CheckConstraint("monto > 0", name="ck_gov_budget_certificates_monto"),
        sa.CheckConstraint("saldo_antes >= monto AND saldo_despues = saldo_antes - monto", name="ck_gov_budget_certificates_saldos"),
        sa.CheckConstraint(
            "(estado = 'VIGENTE' AND anulada_por IS NULL AND anulada_en IS NULL AND motivo_anulacion IS NULL) OR "
            "(estado = 'ANULADA' AND anulada_por IS NOT NULL AND anulada_en IS NOT NULL AND motivo_anulacion IS NOT NULL)",
            name="ck_gov_budget_certificates_anulacion",
        ),
        sa.Index("ix_gov_budget_certificates_year_id", "year_id"),
        sa.Index("ix_gov_budget_certificates_company_id", "company_id"),
        sa.Index("ix_gov_budget_certificates_credit_id", "credit_id"),
        sa.Index("ix_gov_budget_certificates_procurement_file_id", "procurement_file_id"),
        sa.Index("ix_gov_budget_certificates_firmante_cargo_id", "firmante_cargo_id"),
    )

    op.execute(
        "CREATE OR REPLACE FUNCTION kontrol_gov_certificado_inmutable() RETURNS TRIGGER AS $$ BEGIN IF TG_OP = 'DELETE' THEN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_BUDGET_CERTIFICATE_IMMUTABLE', DETAIL = TG_OP; END IF; IF OLD.estado <> 'VIGENTE' OR NEW.estado <> 'ANULADA' OR NEW.year_id IS DISTINCT FROM OLD.year_id OR NEW.company_id IS DISTINCT FROM OLD.company_id OR NEW.credit_id IS DISTINCT FROM OLD.credit_id OR NEW.numero IS DISTINCT FROM OLD.numero OR NEW.codigo IS DISTINCT FROM OLD.codigo OR NEW.monto IS DISTINCT FROM OLD.monto OR NEW.saldo_antes IS DISTINCT FROM OLD.saldo_antes OR NEW.saldo_despues IS DISTINCT FROM OLD.saldo_despues OR NEW.moneda IS DISTINCT FROM OLD.moneda OR NEW.fecha IS DISTINCT FROM OLD.fecha OR NEW.concepto IS DISTINCT FROM OLD.concepto OR NEW.expediente_referencia IS DISTINCT FROM OLD.expediente_referencia OR NEW.procurement_file_id IS DISTINCT FROM OLD.procurement_file_id OR NEW.firmante_cargo_id IS DISTINCT FROM OLD.firmante_cargo_id OR NEW.emitida_por IS DISTINCT FROM OLD.emitida_por OR NEW.emitida_en IS DISTINCT FROM OLD.emitida_en OR NEW.huella IS DISTINCT FROM OLD.huella OR NEW.documento_sha256 IS DISTINCT FROM OLD.documento_sha256 OR NEW.documento_storage_key IS DISTINCT FROM OLD.documento_storage_key THEN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_BUDGET_CERTIFICATE_IMMUTABLE', DETAIL = TG_OP; END IF; RETURN NEW; END; $$ LANGUAGE plpgsql"
    )
    op.execute(
        "CREATE TRIGGER trg_gov_budget_certificates_inmutable BEFORE UPDATE OR DELETE ON gov_budget_certificates FOR EACH ROW EXECUTE FUNCTION kontrol_gov_certificado_inmutable()"
    )
    op.execute(
        "CREATE TRIGGER trg_gov_budget_certificates_no_truncate BEFORE TRUNCATE ON gov_budget_certificates FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_presupuesto_historia_inmutable()"
    )

    op.drop_constraint("ck_gov_budget_year_history_tipo", "gov_budget_year_history", type_="check")
    op.create_check_constraint(
        "ck_gov_budget_year_history_tipo",
        "gov_budget_year_history",
        f"tipo IN ({TIPOS_HISTORIA})",
    )

    _conceder_permisos(op.get_bind())


def downgrade() -> None:
    bind = op.get_bind()

    for recurso, acciones in PERMISOS.items():
        for accion in acciones:
            fila = bind.execute(sa.text(
                "SELECT id FROM permissions WHERE resource = :r AND action = :a"),
                {"r": recurso, "a": accion}).fetchone()
            if fila:
                permiso = fila[0]
                bind.execute(sa.text("DELETE FROM role_permissions WHERE permission_id = :p"), {"p": permiso})
                bind.execute(sa.text("DELETE FROM permissions WHERE id = :p"), {"p": permiso})

    op.execute("DROP TRIGGER IF EXISTS trg_gov_budget_certificates_inmutable ON gov_budget_certificates")
    op.execute("DROP TRIGGER IF EXISTS trg_gov_budget_certificates_no_truncate ON gov_budget_certificates")
    op.execute("DROP FUNCTION IF EXISTS kontrol_gov_certificado_inmutable()")

    op.drop_constraint("ck_gov_budget_year_history_tipo", "gov_budget_year_history", type_="check")
    op.create_check_constraint(
        "ck_gov_budget_year_history_tipo",
        "gov_budget_year_history",
        f"tipo IN ({TIPOS_HISTORIA_0111})",
    )

    op.drop_table("gov_budget_certificates")
