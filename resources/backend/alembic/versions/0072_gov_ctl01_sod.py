"""gov ctl01 sod

Crea las reglas de segregación de funciones y su historia (CTL-01, GOV-CTL-001),
registra `gobierno_sod:view`, `gobierno_sod:manage` y `gobierno_sod:activate` y los concede al rol protegido
FUNCIONAL_COMPLETO de las instalaciones existentes.

Revision ID: 0072_gov_ctl01_sod
Revises: 0071_gov_doc08_paquetes
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa

from alembic import op

revision = "0072_gov_ctl01_sod"
down_revision = "0071_gov_doc08_paquetes"
branch_labels = None
depends_on = None

PERMISOS = {"gobierno_sod": ("view", "manage", "activate")}


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
        "gov_sod_rules",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("proceso", sa.String(10), nullable=False),
        sa.Column("accion_a", sa.String(32), nullable=False),
        sa.Column("accion_b", sa.String(32), nullable=False),
        sa.Column("bidireccional", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("alcance", sa.String(16), nullable=False, server_default="MISMO_OBJETO"),
        sa.Column("modo", sa.String(10), nullable=False, server_default="BLOQUEAR"),
        sa.Column("vigente_desde", sa.Date(), nullable=False),
        sa.Column("vigente_hasta", sa.Date(), nullable=True),
        sa.Column("estado", sa.String(10), nullable=False, server_default="BORRADOR"),
        sa.Column("activada_por", sa.String(36), nullable=True),
        sa.Column("activada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cerrada_por", sa.String(36), nullable=True),
        sa.Column("cerrada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("motivo_cierre", sa.String(500), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "codigo", name="uq_gov_sod_rules_company_id_codigo"),
        sa.CheckConstraint(f"estado IN ({_en('BORRADOR', 'VIGENTE', 'CERRADA')})", name="estado"),
        sa.CheckConstraint(f"alcance IN ({_en('MISMO_OBJETO')})", name="alcance"),
        sa.CheckConstraint(f"modo IN ({_en('BLOQUEAR')})", name="modo"),
        sa.CheckConstraint(f"proceso IN ({_en('DOC-02', 'CTL-06')})", name="proceso"),
        sa.CheckConstraint("accion_a <> accion_b", name="acciones_distintas"),
        sa.CheckConstraint("vigente_hasta IS NULL OR vigente_hasta >= vigente_desde", name="vigencia"),
    )
    op.create_index("ix_gov_sod_rules_tenant_id", "gov_sod_rules", ["tenant_id"])
    op.create_index("ix_gov_sod_rules_company_id", "gov_sod_rules", ["company_id"])

    if bind.dialect.name == "postgresql":
        op.execute("""
            CREATE OR REPLACE FUNCTION kontrol_gov_sod_no_borrable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'GOV_SOD_RULE_NOT_DELETABLE' USING ERRCODE = 'P0001', DETAIL = TG_OP; END; $$
        """)
        op.execute("CREATE TRIGGER trg_gov_sod_rules_no_delete BEFORE DELETE ON gov_sod_rules FOR EACH ROW EXECUTE FUNCTION kontrol_gov_sod_no_borrable()")
        op.execute("CREATE TRIGGER trg_gov_sod_rules_no_truncate BEFORE TRUNCATE ON gov_sod_rules FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_sod_no_borrable()")

    op.create_table(
        "gov_sod_rule_history",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("rule_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("tipo", sa.String(10), nullable=False),
        sa.Column("detalle", sa.JSON(), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["rule_id"], ["gov_sod_rules.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(f"tipo IN ({_en('CREADA', 'EDITADA', 'ACTIVADA', 'CERRADA')})", name="tipo"),
    )
    op.create_index("ix_gov_sod_rule_history_rule_id", "gov_sod_rule_history", ["rule_id"])
    op.create_index("ix_gov_sod_rule_history_company_id", "gov_sod_rule_history", ["company_id"])

    if bind.dialect.name == "postgresql":
        op.execute("""
            CREATE OR REPLACE FUNCTION kontrol_gov_sod_historia_inmutable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE 'GOV_SOD_HISTORY_IMMUTABLE'; END; $$
        """)
        op.execute("CREATE TRIGGER trg_gov_sod_rule_history_no_update BEFORE UPDATE ON gov_sod_rule_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_sod_historia_inmutable()")
        op.execute("CREATE TRIGGER trg_gov_sod_rule_history_no_delete BEFORE DELETE ON gov_sod_rule_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_sod_historia_inmutable()")
        op.execute("CREATE TRIGGER trg_gov_sod_rule_history_no_truncate BEFORE TRUNCATE ON gov_sod_rule_history FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_sod_historia_inmutable()")

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
        op.execute("DROP TRIGGER IF EXISTS trg_gov_sod_rule_history_no_update ON gov_sod_rule_history")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_sod_rule_history_no_delete ON gov_sod_rule_history")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_sod_rule_history_no_truncate ON gov_sod_rule_history")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_sod_rules_no_delete ON gov_sod_rules")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_sod_rules_no_truncate ON gov_sod_rules")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_sod_historia_inmutable()")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_sod_no_borrable()")

    op.drop_index("ix_gov_sod_rule_history_company_id", table_name="gov_sod_rule_history")
    op.drop_index("ix_gov_sod_rule_history_rule_id", table_name="gov_sod_rule_history")
    op.drop_table("gov_sod_rule_history")

    op.drop_index("ix_gov_sod_rules_company_id", table_name="gov_sod_rules")
    op.drop_index("ix_gov_sod_rules_tenant_id", table_name="gov_sod_rules")
    op.drop_table("gov_sod_rules")
