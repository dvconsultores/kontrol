"""CNT-01: contrato u orden derivada de la adjudicación y permiso gobierno_contratos (GOV-CNT-001)."""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "0114_gov_cnt01_contratos"
down_revision = "0113_gov_bud08_compromiso"
branch_labels = None
depends_on = None

PERMISOS = {"gobierno_contratos": ("view", "manage", "formalize")}
TIPOS = ("CONTRATO", "ORDEN_COMPRA", "ORDEN_SERVICIO")
ESTADOS = ("BORRADOR", "FORMALIZADO")
CLASES_ANTES = ("APERTURA", "DATOS", "RESPONSABLE", "COMISION", "ACTUACION", "DECISION", "DOCUMENTO", "ACTO", "HITO", "CIERRE", "DESCARTE", "OFERTA", "APERTURA_OFERTA", "EVALUACION", "RECOMENDACION", "RECHAZO_OFERTA", "ADJUDICACION", "DESIERTA", "TERMINACION", "NULIDAD", "GARANTIA")
CLASES_DESPUES = CLASES_ANTES + ("CONTRATO",)
CK_CLASE = "ck_gov_procurement_file_events_ck_gov_procurement_file__de56"


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


def upgrade() -> None:
    bind = op.get_bind()

    op.create_table(
        "gov_contracts",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("file_id", sa.String(36), nullable=False),
        sa.Column("decision_id", sa.String(36), nullable=False),
        sa.Column("offer_id", sa.String(36), nullable=False),
        sa.Column("act_id", sa.String(36), nullable=False),
        sa.Column("amount_id", sa.String(36), nullable=False),
        sa.Column("estado", sa.String(12), nullable=False, server_default="BORRADOR"),
        sa.Column("tipo", sa.String(16), nullable=True),
        sa.Column("codigo", sa.String(20), nullable=True),
        sa.Column("numero", sa.Integer(), nullable=True),
        sa.Column("anio", sa.SmallInteger(), nullable=True),
        sa.Column("expediente_numero", sa.String(40), nullable=False),
        sa.Column("objeto", sa.String(1000), nullable=False),
        sa.Column("descripcion_complementaria", sa.String(2000), nullable=True),
        sa.Column("decision_referencia", sa.String(10), nullable=False),
        sa.Column("decision_fecha", sa.Date(), nullable=False),
        sa.Column("acto_etiqueta", sa.String(400), nullable=False),
        sa.Column("oferta_referencia", sa.String(12), nullable=False),
        sa.Column("contratista_nombre", sa.String(300), nullable=False),
        sa.Column("contratista_documento", sa.String(40), nullable=False),
        sa.Column("contratista_representante", sa.String(200), nullable=True),
        sa.Column("monto", sa.Numeric(18, 2), nullable=False),
        sa.Column("moneda", sa.String(3), nullable=False),
        sa.Column("fecha_inicio", sa.Date(), nullable=True),
        sa.Column("fecha_fin", sa.Date(), nullable=True),
        sa.Column("referencia_instrumento", sa.String(120), nullable=True),
        sa.Column("document_id", sa.String(36), nullable=True),
        sa.Column("document_version_id", sa.String(36), nullable=True),
        sa.Column("documento_version_numero", sa.BigInteger(), nullable=True),
        sa.Column("documento_sha256", sa.String(64), nullable=True),
        sa.Column("documento_titulo", sa.String(300), nullable=True),
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
        sa.ForeignKeyConstraint(["file_id"], ["gov_procurement_files.id"]),
        sa.ForeignKeyConstraint(["decision_id"], ["gov_procurement_decisions.id"]),
        sa.ForeignKeyConstraint(["offer_id"], ["gov_procurement_offers.id"]),
        sa.ForeignKeyConstraint(["act_id"], ["gov_acts.id"]),
        sa.ForeignKeyConstraint(["amount_id"], ["gov_procurement_offer_amounts.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["document_version_id"], ["document_versions.id"]),
        sa.ForeignKeyConstraint(["firmante_cargo_id"], ["gov_positions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "codigo", name="uq_gov_contracts_company_codigo"),
        sa.UniqueConstraint("decision_id", name="uq_gov_contracts_decision"),
        sa.CheckConstraint(f"estado IN ({_en(*ESTADOS)})", name="estado"),
        sa.CheckConstraint(f"tipo IS NULL OR tipo IN ({_en(*TIPOS)})", name="tipo"),
        sa.CheckConstraint("monto > 0", name="monto"),
        sa.CheckConstraint("length(moneda) = 3", name="moneda"),
        sa.CheckConstraint("numero IS NULL OR numero >= 1", name="numero"),
        sa.CheckConstraint("fecha_fin IS NULL OR fecha_inicio IS NULL OR fecha_fin >= fecha_inicio", name="plazo"),
        sa.CheckConstraint(
            "(estado = 'BORRADOR' AND codigo IS NULL AND numero IS NULL AND anio IS NULL AND fecha_formalizacion IS NULL AND formalizado_en IS NULL AND formalizado_por IS NULL AND snapshot IS NULL AND huella IS NULL) OR (estado = 'FORMALIZADO' AND tipo IS NOT NULL AND codigo IS NOT NULL AND numero IS NOT NULL AND anio IS NOT NULL AND fecha_inicio IS NOT NULL AND fecha_fin IS NOT NULL AND referencia_instrumento IS NOT NULL AND document_id IS NOT NULL AND document_version_id IS NOT NULL AND documento_sha256 IS NOT NULL AND firmante_cargo_id IS NOT NULL AND fecha_formalizacion IS NOT NULL AND formalizado_en IS NOT NULL AND formalizado_por IS NOT NULL AND snapshot IS NOT NULL AND huella IS NOT NULL)",
            name="completitud",
        ),
    )
    op.create_index("ix_gov_contracts_company_id", "gov_contracts", ["company_id"])
    op.create_index("ix_gov_contracts_file_id", "gov_contracts", ["file_id"])
    op.create_index("ix_gov_contracts_offer_id", "gov_contracts", ["offer_id"])

    op.create_table(
        "gov_contract_budget_allocations",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("contract_id", sa.String(36), nullable=False),
        sa.Column("certificate_id", sa.String(36), nullable=False),
        sa.Column("year_id", sa.String(36), nullable=False),
        sa.Column("certificado_codigo", sa.String(20), nullable=False),
        sa.Column("monto", sa.Numeric(18, 2), nullable=False),
        sa.Column("moneda", sa.String(3), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["contract_id"], ["gov_contracts.id"]),
        sa.ForeignKeyConstraint(["certificate_id"], ["gov_budget_certificates.id"]),
        sa.ForeignKeyConstraint(["year_id"], ["gov_budget_years.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("contract_id", "certificate_id", name="uq_gov_contract_budget_allocations_certificado"),
        sa.CheckConstraint("monto > 0", name="monto"),
    )
    op.create_index("ix_gov_contract_budget_allocations_company_id", "gov_contract_budget_allocations", ["company_id"])
    op.create_index("ix_gov_contract_budget_allocations_contract_id", "gov_contract_budget_allocations", ["contract_id"])
    op.create_index("ix_gov_contract_budget_allocations_certificate_id", "gov_contract_budget_allocations", ["certificate_id"])

    op.create_table(
        "gov_contract_guarantees",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("contract_id", sa.String(36), nullable=False),
        sa.Column("instrument_id", sa.String(36), nullable=False),
        sa.Column("garantia_referencia", sa.String(20), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["contract_id"], ["gov_contracts.id"]),
        sa.ForeignKeyConstraint(["instrument_id"], ["gov_guarantee_instruments.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("contract_id", "instrument_id", name="uq_gov_contract_guarantees_instrumento"),
    )
    op.create_index("ix_gov_contract_guarantees_company_id", "gov_contract_guarantees", ["company_id"])
    op.create_index("ix_gov_contract_guarantees_contract_id", "gov_contract_guarantees", ["contract_id"])
    op.create_index("ix_gov_contract_guarantees_instrument_id", "gov_contract_guarantees", ["instrument_id"])

    if bind.dialect.name == "postgresql":
        op.execute(f"ALTER TABLE gov_procurement_file_events DROP CONSTRAINT IF EXISTS {CK_CLASE}")
        op.execute(
            f"ALTER TABLE gov_procurement_file_events ADD CONSTRAINT {CK_CLASE} CHECK (clase IN ({_en(*CLASES_DESPUES)}))"
        )

        op.execute("""CREATE OR REPLACE FUNCTION kontrol_gov_contract_guard() RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' OR TG_OP = 'TRUNCATE' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CONTRACT_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    IF OLD.estado = 'FORMALIZADO' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CONTRACT_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    IF NEW.company_id IS DISTINCT FROM OLD.company_id
        OR NEW.file_id IS DISTINCT FROM OLD.file_id
        OR NEW.decision_id IS DISTINCT FROM OLD.decision_id
        OR NEW.offer_id IS DISTINCT FROM OLD.offer_id
        OR NEW.act_id IS DISTINCT FROM OLD.act_id
        OR NEW.amount_id IS DISTINCT FROM OLD.amount_id
        OR NEW.expediente_numero IS DISTINCT FROM OLD.expediente_numero
        OR NEW.objeto IS DISTINCT FROM OLD.objeto
        OR NEW.decision_referencia IS DISTINCT FROM OLD.decision_referencia
        OR NEW.oferta_referencia IS DISTINCT FROM OLD.oferta_referencia
        OR NEW.contratista_nombre IS DISTINCT FROM OLD.contratista_nombre
        OR NEW.contratista_documento IS DISTINCT FROM OLD.contratista_documento
        OR NEW.monto IS DISTINCT FROM OLD.monto
        OR NEW.moneda IS DISTINCT FROM OLD.moneda THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CONTRACT_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    RETURN NEW;
END; $$ LANGUAGE plpgsql""")
        op.execute("CREATE TRIGGER trg_gov_contracts_guard BEFORE UPDATE OR DELETE ON gov_contracts FOR EACH ROW EXECUTE FUNCTION kontrol_gov_contract_guard()")
        op.execute("CREATE TRIGGER trg_gov_contracts_no_truncate BEFORE TRUNCATE ON gov_contracts FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_contract_guard()")

        op.execute("""CREATE OR REPLACE FUNCTION kontrol_gov_contract_link_guard() RETURNS TRIGGER AS $$
DECLARE
    v_estado text;
BEGIN
    IF TG_OP = 'TRUNCATE' OR TG_OP = 'UPDATE' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CONTRACT_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    SELECT estado INTO v_estado FROM gov_contracts WHERE id = (CASE WHEN TG_OP = 'DELETE' THEN OLD.contract_id ELSE NEW.contract_id END);
    IF v_estado = 'FORMALIZADO' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CONTRACT_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END; $$ LANGUAGE plpgsql""")
        op.execute("CREATE TRIGGER trg_gov_contract_budget_allocations_guard BEFORE INSERT OR UPDATE OR DELETE ON gov_contract_budget_allocations FOR EACH ROW EXECUTE FUNCTION kontrol_gov_contract_link_guard()")
        op.execute("CREATE TRIGGER trg_gov_contract_budget_allocations_no_truncate BEFORE TRUNCATE ON gov_contract_budget_allocations FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_contract_link_guard()")
        op.execute("CREATE TRIGGER trg_gov_contract_guarantees_guard BEFORE INSERT OR UPDATE OR DELETE ON gov_contract_guarantees FOR EACH ROW EXECUTE FUNCTION kontrol_gov_contract_link_guard()")
        op.execute("CREATE TRIGGER trg_gov_contract_guarantees_no_truncate BEFORE TRUNCATE ON gov_contract_guarantees FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_contract_link_guard()")

    _conceder_permisos(bind)


def downgrade() -> None:
    bind = op.get_bind()

    for recurso, acciones in PERMISOS.items():
        for accion in acciones:
            fila = bind.execute(
                sa.text("SELECT id FROM permissions WHERE resource = :r AND action = :a"),
                {"r": recurso, "a": accion},
            ).fetchone()
            if not fila:
                continue
            permiso = fila[0]
            bind.execute(sa.text("DELETE FROM role_permissions WHERE permission_id = :p"), {"p": permiso})
            bind.execute(sa.text("DELETE FROM permissions WHERE id = :id"), {"id": permiso})

    if bind.dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_gov_contracts_guard ON gov_contracts")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_contracts_no_truncate ON gov_contracts")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_contract_budget_allocations_guard ON gov_contract_budget_allocations")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_contract_budget_allocations_no_truncate ON gov_contract_budget_allocations")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_contract_guarantees_guard ON gov_contract_guarantees")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_contract_guarantees_no_truncate ON gov_contract_guarantees")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_contract_link_guard()")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_contract_guard()")

        op.execute(f"ALTER TABLE gov_procurement_file_events DROP CONSTRAINT IF EXISTS {CK_CLASE}")
        op.execute(
            f"ALTER TABLE gov_procurement_file_events ADD CONSTRAINT {CK_CLASE} CHECK (clase IN ({_en(*CLASES_ANTES)}))"
        )

    op.drop_index("ix_gov_contract_guarantees_instrument_id", table_name="gov_contract_guarantees")
    op.drop_index("ix_gov_contract_guarantees_contract_id", table_name="gov_contract_guarantees")
    op.drop_index("ix_gov_contract_guarantees_company_id", table_name="gov_contract_guarantees")
    op.drop_table("gov_contract_guarantees")

    op.drop_index("ix_gov_contract_budget_allocations_certificate_id", table_name="gov_contract_budget_allocations")
    op.drop_index("ix_gov_contract_budget_allocations_contract_id", table_name="gov_contract_budget_allocations")
    op.drop_index("ix_gov_contract_budget_allocations_company_id", table_name="gov_contract_budget_allocations")
    op.drop_table("gov_contract_budget_allocations")

    op.drop_index("ix_gov_contracts_offer_id", table_name="gov_contracts")
    op.drop_index("ix_gov_contracts_file_id", table_name="gov_contracts")
    op.drop_index("ix_gov_contracts_company_id", table_name="gov_contracts")
    op.drop_table("gov_contracts")
