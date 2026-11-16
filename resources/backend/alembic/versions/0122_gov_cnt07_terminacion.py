"""CNT-07: terminación, resolución o rescisión del contrato (GOV-CNT-008)."""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "0122_gov_cnt07_terminacion"
down_revision = "0121_gov_cnt09_alertas"
branch_labels = None
depends_on = None

PERMISOS = {"gobierno_contratos": ("terminate",)}

FIGURAS = ("RESCISION_NO_IMPUTABLE", "RESOLUCION_MUTUO_ACUERDO", "RESCISION_IMPUTABLE")
CAUSALES = (
    "INTERES_DEL_CONTRATANTE",
    "CIRCUNSTANCIAS_ACONSEJABLES",
    "LCP_155_1",
    "LCP_155_2",
    "LCP_155_3",
    "LCP_155_4",
    "LCP_155_5",
    "LCP_155_6",
    "LCP_155_7",
    "LCP_155_8",
    "LCP_155_9",
    "CLAUSULA_CONTRATO",
)
ESTADOS = ("BORRADOR", "FORMALIZADA")


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
    op.create_table(
        "gov_contract_terminations",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("contract_id", sa.String(36), nullable=False),
        sa.Column("file_id", sa.String(36), nullable=False),
        sa.Column("estado", sa.String(12), nullable=False, server_default="BORRADOR"),
        sa.Column("figura", sa.String(32), nullable=False),
        sa.Column("causal", sa.String(32), nullable=True),
        sa.Column("causal_referencia", sa.String(200), nullable=True),
        sa.Column("hechos", sa.String(4000), nullable=True),
        sa.Column("fundamento", sa.String(4000), nullable=True),
        sa.Column("act_id", sa.String(36), nullable=True),
        sa.Column("apertura_act_id", sa.String(36), nullable=True),
        sa.Column("document_id", sa.String(36), nullable=True),
        sa.Column("document_version_id", sa.String(36), nullable=True),
        sa.Column("documento_sha256", sa.String(64), nullable=True),
        sa.Column("documento_titulo", sa.String(300), nullable=True),
        sa.Column("conclusion_alcance", sa.String(1000), nullable=True),
        sa.Column("conclusion_hasta", sa.Date(), nullable=True),
        sa.Column("fecha_acto", sa.Date(), nullable=True),
        sa.Column("fecha_eficacia", sa.Date(), nullable=True),
        sa.Column("codigo", sa.String(20), nullable=True),
        sa.Column("snapshot", sa.JSON(), nullable=True),
        sa.Column("huella", sa.String(64), nullable=True),
        sa.Column("formalizado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("formalizado_por", sa.String(36), nullable=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["contract_id"], ["gov_contracts.id"]),
        sa.ForeignKeyConstraint(["file_id"], ["gov_procurement_files.id"]),
        sa.ForeignKeyConstraint(["act_id"], ["gov_acts.id"]),
        sa.ForeignKeyConstraint(["apertura_act_id"], ["gov_acts.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["document_version_id"], ["document_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "codigo", name="uq_gov_contract_terminations_codigo"),
        sa.CheckConstraint(f"estado IN ({_en(*ESTADOS)})", name="estado"),
        sa.CheckConstraint(f"figura IN ({_en(*FIGURAS)})", name="figura"),
        sa.CheckConstraint(f"causal IS NULL OR causal IN ({_en(*CAUSALES)})", name="causal"),
        sa.CheckConstraint("(conclusion_hasta IS NULL) = (conclusion_alcance IS NULL)", name="conclusion"),
        sa.CheckConstraint(
            "estado <> 'FORMALIZADA' OR (causal IS NOT NULL AND hechos IS NOT NULL AND fundamento IS NOT NULL AND act_id IS NOT NULL AND fecha_acto IS NOT NULL AND fecha_eficacia IS NOT NULL AND codigo IS NOT NULL AND huella IS NOT NULL AND formalizado_en IS NOT NULL)",
            name="completitud",
        ),
        sa.CheckConstraint("conclusion_hasta IS NULL OR fecha_eficacia IS NULL OR conclusion_hasta > fecha_eficacia", name="conclusion_fecha"),
    )
    op.create_index("ix_gov_contract_terminations_company_id", "gov_contract_terminations", ["company_id"])
    op.create_index("ix_gov_contract_terminations_contract_id", "gov_contract_terminations", ["contract_id"])
    op.create_index("ix_gov_contract_terminations_file_id", "gov_contract_terminations", ["file_id"])
    op.create_index(
        "uq_gov_contract_terminations_borrador",
        "gov_contract_terminations",
        ["contract_id"],
        unique=True,
        postgresql_where=sa.text("estado = 'BORRADOR'"),
        sqlite_where=sa.text("estado = 'BORRADOR'"),
    )
    op.create_index(
        "uq_gov_contract_terminations_formalizada",
        "gov_contract_terminations",
        ["contract_id"],
        unique=True,
        postgresql_where=sa.text("estado = 'FORMALIZADA'"),
        sqlite_where=sa.text("estado = 'FORMALIZADA'"),
    )

    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            """
CREATE OR REPLACE FUNCTION kontrol_gov_contract_termination_guard() RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'TRUNCATE' THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CONTRACT_TERMINATION_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    IF TG_OP = 'DELETE' THEN
        IF OLD.estado <> 'BORRADOR' THEN
            RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CONTRACT_TERMINATION_IMMUTABLE', DETAIL = TG_OP;
        END IF;
        RETURN OLD;
    END IF;
    IF OLD.estado = 'FORMALIZADA'
        OR NEW.company_id IS DISTINCT FROM OLD.company_id
        OR NEW.contract_id IS DISTINCT FROM OLD.contract_id
        OR NEW.file_id IS DISTINCT FROM OLD.file_id
        OR NEW.created_by IS DISTINCT FROM OLD.created_by THEN
        RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CONTRACT_TERMINATION_IMMUTABLE', DETAIL = TG_OP;
    END IF;
    RETURN NEW;
END; $$ LANGUAGE plpgsql
"""
        )
        op.execute("CREATE TRIGGER trg_gov_contract_terminations_guard BEFORE UPDATE OR DELETE ON gov_contract_terminations FOR EACH ROW EXECUTE FUNCTION kontrol_gov_contract_termination_guard()")
        op.execute("CREATE TRIGGER trg_gov_contract_terminations_no_truncate BEFORE TRUNCATE ON gov_contract_terminations FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_contract_termination_guard()")

    _conceder_permisos(op.get_bind())


def downgrade() -> None:
    bind = op.get_bind()
    permisos = bind.execute(
        sa.text("SELECT id FROM permissions WHERE resource = :r AND action = :a"),
        {"r": "gobierno_contratos", "a": "terminate"},
    ).fetchall()
    for permiso in permisos:
        bind.execute(sa.text("DELETE FROM role_permissions WHERE permission_id = :p"), {"p": permiso[0]})
        bind.execute(sa.text("DELETE FROM permissions WHERE id = :p"), {"p": permiso[0]})

    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_gov_contract_terminations_guard ON gov_contract_terminations")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_contract_terminations_no_truncate ON gov_contract_terminations")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_contract_termination_guard()")

    op.drop_index("uq_gov_contract_terminations_borrador", table_name="gov_contract_terminations")
    op.drop_index("uq_gov_contract_terminations_formalizada", table_name="gov_contract_terminations")
    op.drop_index("ix_gov_contract_terminations_file_id", table_name="gov_contract_terminations")
    op.drop_index("ix_gov_contract_terminations_contract_id", table_name="gov_contract_terminations")
    op.drop_index("ix_gov_contract_terminations_company_id", table_name="gov_contract_terminations")
    op.drop_table("gov_contract_terminations")
