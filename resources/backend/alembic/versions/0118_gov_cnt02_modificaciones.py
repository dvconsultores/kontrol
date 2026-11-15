"""CNT-02: adendas, prórrogas, modificaciones y variaciones versionadas del contrato (GOV-CNT-002)."""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0118_gov_cnt02_modificaciones"
down_revision = "0117_gov_cnt04_supervisor"
branch_labels = None
depends_on = None

TIPOS = ("ADENDA", "PRORROGA", "MODIFICACION", "VARIACION")
ESTADOS = ("BORRADOR", "FORMALIZADA")

COMPLETITUD = (
    "(estado = 'BORRADOR' AND numero IS NULL AND codigo IS NULL AND monto_anterior IS NULL AND monto_nuevo IS NULL AND fecha_fin_anterior IS NULL AND fecha_fin_nueva IS NULL AND fecha_formalizacion IS NULL AND formalizado_en IS NULL AND formalizado_por IS NULL AND snapshot IS NULL AND huella IS NULL) OR (estado = 'FORMALIZADA' AND numero IS NOT NULL AND codigo IS NOT NULL AND motivo IS NOT NULL AND fecha_instrumento IS NOT NULL AND vigente_desde IS NOT NULL AND referencia_instrumento IS NOT NULL AND document_id IS NOT NULL AND document_version_id IS NOT NULL AND documento_sha256 IS NOT NULL AND monto_anterior IS NOT NULL AND monto_nuevo IS NOT NULL AND fecha_fin_anterior IS NOT NULL AND fecha_fin_nueva IS NOT NULL AND firmante_cargo_id IS NOT NULL AND fecha_formalizacion IS NOT NULL AND formalizado_en IS NOT NULL AND formalizado_por IS NOT NULL AND snapshot IS NOT NULL AND huella IS NOT NULL)"
)


def _en(*valores: str) -> str:
    return ", ".join(f"'{v}'" for v in valores)


def _tiempos() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]


def upgrade() -> None:
    op.create_table(
        "gov_contract_amendments",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("contract_id", sa.String(36), nullable=False),
        sa.Column("file_id", sa.String(36), nullable=False),
        sa.Column("estado", sa.String(12), nullable=False, server_default="BORRADOR"),
        sa.Column("tipo", sa.String(14), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=True),
        sa.Column("codigo", sa.String(40), nullable=True),
        sa.Column("previous_amendment_id", sa.String(36), nullable=True),
        sa.Column("base_numero", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("motivo", sa.String(2000), nullable=True),
        sa.Column("fecha_instrumento", sa.Date(), nullable=True),
        sa.Column("vigente_desde", sa.Date(), nullable=True),
        sa.Column("nueva_fecha_fin", sa.Date(), nullable=True),
        sa.Column("delta_monto", sa.Numeric(18, 2), nullable=True),
        sa.Column("condiciones", sa.String(4000), nullable=True),
        sa.Column("referencia_instrumento", sa.String(120), nullable=True),
        sa.Column("document_id", sa.String(36), nullable=True),
        sa.Column("document_version_id", sa.String(36), nullable=True),
        sa.Column("documento_version_numero", sa.BigInteger(), nullable=True),
        sa.Column("documento_sha256", sa.String(64), nullable=True),
        sa.Column("documento_titulo", sa.String(300), nullable=True),
        sa.Column("moneda", sa.String(3), nullable=False),
        sa.Column("monto_anterior", sa.Numeric(18, 2), nullable=True),
        sa.Column("monto_nuevo", sa.Numeric(18, 2), nullable=True),
        sa.Column("fecha_fin_anterior", sa.Date(), nullable=True),
        sa.Column("fecha_fin_nueva", sa.Date(), nullable=True),
        sa.Column("firmante_cargo_id", sa.String(36), nullable=True),
        sa.Column("firmante_cargo_nombre", sa.String(200), nullable=True),
        sa.Column("firmante_funcionario_nombre", sa.String(200), nullable=True),
        sa.Column("fecha_formalizacion", sa.Date(), nullable=True),
        sa.Column("formalizado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("formalizado_por", sa.String(36), nullable=True),
        sa.Column("snapshot", sa.JSON(), nullable=True),
        sa.Column("huella", sa.String(64), nullable=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["contract_id"], ["gov_contracts.id"]),
        sa.ForeignKeyConstraint(["file_id"], ["gov_procurement_files.id"]),
        sa.ForeignKeyConstraint(["previous_amendment_id"], ["gov_contract_amendments.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["document_version_id"], ["document_versions.id"]),
        sa.ForeignKeyConstraint(["firmante_cargo_id"], ["gov_positions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("contract_id", "numero", name="uq_gov_contract_amendments_numero"),
        sa.UniqueConstraint("company_id", "codigo", name="uq_gov_contract_amendments_codigo"),
        sa.UniqueConstraint("previous_amendment_id", name="uq_gov_contract_amendments_previa"),
        sa.CheckConstraint(f"estado IN ({_en(*ESTADOS)})", name="estado"),
        sa.CheckConstraint(f"tipo IN ({_en(*TIPOS)})", name="tipo"),
        sa.CheckConstraint("numero IS NULL OR numero >= 1", name="numero"),
        sa.CheckConstraint("base_numero >= 0", name="base"),
        sa.CheckConstraint("delta_monto IS NULL OR delta_monto <> 0", name="delta"),
        sa.CheckConstraint("length(moneda) = 3", name="moneda"),
        sa.CheckConstraint("vigente_desde IS NULL OR fecha_instrumento IS NULL OR vigente_desde >= fecha_instrumento", name="fechas"),
        sa.CheckConstraint("monto_nuevo IS NULL OR (monto_nuevo > 0 AND monto_nuevo = monto_anterior + COALESCE(delta_monto, 0))", name="montos"),
        sa.CheckConstraint("fecha_fin_nueva IS NULL OR (nueva_fecha_fin IS NULL AND fecha_fin_nueva = fecha_fin_anterior) OR (nueva_fecha_fin IS NOT NULL AND nueva_fecha_fin > fecha_fin_anterior AND fecha_fin_nueva = nueva_fecha_fin)", name="plazo"),
        sa.CheckConstraint(COMPLETITUD, name="completitud"),
    )
    op.create_index("ix_gov_contract_amendments_company_id", "gov_contract_amendments", ["company_id"])
    op.create_index("ix_gov_contract_amendments_contract_id", "gov_contract_amendments", ["contract_id"])
    op.create_index("ix_gov_contract_amendments_file_id", "gov_contract_amendments", ["file_id"])
    op.create_index(
        "uq_gov_contract_amendments_borrador",
        "gov_contract_amendments",
        ["contract_id"],
        unique=True,
        postgresql_where=sa.text("estado = 'BORRADOR'"),
        sqlite_where=sa.text("estado = 'BORRADOR'"),
    )

    op.create_table(
        "gov_contract_amendment_allocations",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("amendment_id", sa.String(36), nullable=False),
        sa.Column("contract_id", sa.String(36), nullable=False),
        sa.Column("certificate_id", sa.String(36), nullable=False),
        sa.Column("year_id", sa.String(36), nullable=False),
        sa.Column("certificado_codigo", sa.String(20), nullable=False),
        sa.Column("monto", sa.Numeric(18, 2), nullable=False),
        sa.Column("moneda", sa.String(3), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["amendment_id"], ["gov_contract_amendments.id"]),
        sa.ForeignKeyConstraint(["contract_id"], ["gov_contracts.id"]),
        sa.ForeignKeyConstraint(["certificate_id"], ["gov_budget_certificates.id"]),
        sa.ForeignKeyConstraint(["year_id"], ["gov_budget_years.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("amendment_id", "certificate_id", name="uq_gov_contract_amendment_allocations_certificado"),
        sa.CheckConstraint("monto > 0", name="monto"),
    )
    op.create_index("ix_gov_contract_amendment_allocations_company_id", "gov_contract_amendment_allocations", ["company_id"])
    op.create_index("ix_gov_contract_amendment_allocations_amendment_id", "gov_contract_amendment_allocations", ["amendment_id"])
    op.create_index("ix_gov_contract_amendment_allocations_contract_id", "gov_contract_amendment_allocations", ["contract_id"])
    op.create_index("ix_gov_contract_amendment_allocations_certificate_id", "gov_contract_amendment_allocations", ["certificate_id"])

    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            """
CREATE OR REPLACE FUNCTION kontrol_gov_contract_amendment_guard() RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'TRUNCATE' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CONTRACT_AMENDMENT_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    IF TG_OP = 'DELETE' THEN
        IF OLD.estado <> 'BORRADOR' THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CONTRACT_AMENDMENT_IMMUTABLE', DETAIL = TG_OP;
        END IF;
        RETURN OLD;
    END IF;
    IF OLD.estado = 'FORMALIZADA'
        OR NEW.company_id IS DISTINCT FROM OLD.company_id
        OR NEW.contract_id IS DISTINCT FROM OLD.contract_id
        OR NEW.file_id IS DISTINCT FROM OLD.file_id
        OR NEW.moneda IS DISTINCT FROM OLD.moneda
        OR NEW.created_by IS DISTINCT FROM OLD.created_by THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CONTRACT_AMENDMENT_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    RETURN NEW;
END; $$ LANGUAGE plpgsql
"""
        )
        op.execute("CREATE TRIGGER trg_gov_contract_amendments_guard BEFORE UPDATE OR DELETE ON gov_contract_amendments FOR EACH ROW EXECUTE FUNCTION kontrol_gov_contract_amendment_guard()")
        op.execute("CREATE TRIGGER trg_gov_contract_amendments_no_truncate BEFORE TRUNCATE ON gov_contract_amendments FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_contract_amendment_guard()")
        op.execute(
            """
CREATE OR REPLACE FUNCTION kontrol_gov_contract_amendment_link_guard() RETURNS TRIGGER AS $$
DECLARE
    v_estado text;
BEGIN
    IF TG_OP = 'TRUNCATE' OR TG_OP = 'UPDATE' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CONTRACT_AMENDMENT_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    SELECT estado INTO v_estado FROM gov_contract_amendments WHERE id = (CASE WHEN TG_OP = 'DELETE' THEN OLD.amendment_id ELSE NEW.amendment_id END);
    IF v_estado = 'FORMALIZADA' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CONTRACT_AMENDMENT_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END; $$ LANGUAGE plpgsql
"""
        )
        op.execute("CREATE TRIGGER trg_gov_contract_amendment_allocations_guard BEFORE INSERT OR UPDATE OR DELETE ON gov_contract_amendment_allocations FOR EACH ROW EXECUTE FUNCTION kontrol_gov_contract_amendment_link_guard()")
        op.execute("CREATE TRIGGER trg_gov_contract_amendment_allocations_no_truncate BEFORE TRUNCATE ON gov_contract_amendment_allocations FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_contract_amendment_link_guard()")


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_gov_contract_amendments_guard ON gov_contract_amendments")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_contract_amendments_no_truncate ON gov_contract_amendments")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_contract_amendment_allocations_guard ON gov_contract_amendment_allocations")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_contract_amendment_allocations_no_truncate ON gov_contract_amendment_allocations")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_contract_amendment_guard()")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_contract_amendment_link_guard()")

    op.drop_index("ix_gov_contract_amendment_allocations_certificate_id", table_name="gov_contract_amendment_allocations")
    op.drop_index("ix_gov_contract_amendment_allocations_contract_id", table_name="gov_contract_amendment_allocations")
    op.drop_index("ix_gov_contract_amendment_allocations_amendment_id", table_name="gov_contract_amendment_allocations")
    op.drop_index("ix_gov_contract_amendment_allocations_company_id", table_name="gov_contract_amendment_allocations")
    op.drop_table("gov_contract_amendment_allocations")

    op.drop_index("uq_gov_contract_amendments_borrador", table_name="gov_contract_amendments")
    op.drop_index("ix_gov_contract_amendments_file_id", table_name="gov_contract_amendments")
    op.drop_index("ix_gov_contract_amendments_contract_id", table_name="gov_contract_amendments")
    op.drop_index("ix_gov_contract_amendments_company_id", table_name="gov_contract_amendments")
    op.drop_table("gov_contract_amendments")
