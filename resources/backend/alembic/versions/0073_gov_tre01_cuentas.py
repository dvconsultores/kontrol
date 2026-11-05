"""gov tre01 cuentas

Crea el catálogo de bancos, las cuentas bancarias públicas, sus autorizaciones por cargo y su historia
(TRE-01, GOV-TRE-001), amplía el proceso de las reglas SoD y registra `gobierno_cuentas:view`, `:manage` y `:activate`
y los concede al rol protegido FUNCIONAL_COMPLETO de las instalaciones existentes.

Revision ID: 0073_gov_tre01_cuentas
Revises: 0072_gov_ctl01_sod
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa

from alembic import op

revision = "0073_gov_tre01_cuentas"
down_revision = "0072_gov_ctl01_sod"
branch_labels = None
depends_on = None

PERMISOS = {"gobierno_cuentas": ("view", "manage", "activate")}


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
        "gov_banks",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("codigo", sa.String(4), nullable=False),
        sa.Column("nombre", sa.String(120), nullable=False),
        sa.Column("estado", sa.String(10), nullable=False, server_default="ACTIVO"),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "codigo", name="uq_gov_banks_company_id_codigo"),
        sa.CheckConstraint(f"estado IN ({_en('ACTIVO', 'INACTIVO')})", name="estado"),
        sa.CheckConstraint("version >= 1", name="version"),
    )
    op.create_index("ix_gov_banks_tenant_id", "gov_banks", ["tenant_id"])
    op.create_index("ix_gov_banks_company_id", "gov_banks", ["company_id"])

    op.create_table(
        "gov_bank_accounts",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("denominacion", sa.String(200), nullable=False),
        sa.Column("bank_id", sa.String(36), nullable=False),
        sa.Column("tipo", sa.String(10), nullable=False),
        sa.Column("numero", sa.String(20), nullable=False),
        sa.Column("moneda", sa.String(3), nullable=False),
        sa.Column("vigente_desde", sa.Date(), nullable=False),
        sa.Column("vigente_hasta", sa.Date(), nullable=True),
        sa.Column("estado", sa.String(10), nullable=False, server_default="BORRADOR"),
        sa.Column("acto_id", sa.String(36), nullable=True),
        sa.Column("activada_por", sa.String(36), nullable=True),
        sa.Column("activada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cerrada_por", sa.String(36), nullable=True),
        sa.Column("cerrada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fecha_cierre", sa.Date(), nullable=True),
        sa.Column("motivo_cierre", sa.String(500), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["bank_id"], ["gov_banks.id"]),
        sa.ForeignKeyConstraint(["acto_id"], ["gov_acts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "codigo", name="uq_gov_bank_accounts_company_id_codigo"),
        sa.UniqueConstraint("company_id", "bank_id", "numero", name="uq_gov_bank_accounts_numero"),
        sa.CheckConstraint(f"estado IN ({_en('BORRADOR', 'VIGENTE', 'INACTIVA', 'CERRADA')})", name="estado"),
        sa.CheckConstraint(f"tipo IN ({_en('CORRIENTE', 'AHORRO')})", name="tipo"),
        sa.CheckConstraint(f"moneda IN ({_en('VES', 'USD', 'EUR')})", name="moneda"),
        sa.CheckConstraint("length(numero) = 20", name="numero_largo"),
        sa.CheckConstraint("vigente_hasta IS NULL OR vigente_hasta >= vigente_desde", name="vigencia"),
        sa.CheckConstraint(
            "estado = 'BORRADOR' OR (acto_id IS NOT NULL AND activada_en IS NOT NULL)",
            name="activada_con_acto",
        ),
        sa.CheckConstraint(
            "(estado = 'CERRADA') = (cerrada_en IS NOT NULL AND fecha_cierre IS NOT NULL AND motivo_cierre IS NOT NULL)",
            name="cierre_completo",
        ),
        sa.CheckConstraint("version >= 1", name="version"),
    )
    op.create_index("ix_gov_bank_accounts_tenant_id", "gov_bank_accounts", ["tenant_id"])
    op.create_index("ix_gov_bank_accounts_company_id", "gov_bank_accounts", ["company_id"])
    op.create_index("ix_gov_bank_accounts_bank_id", "gov_bank_accounts", ["bank_id"])
    op.create_index("ix_gov_bank_accounts_acto_id", "gov_bank_accounts", ["acto_id"])
    op.create_index("ix_gov_bank_accounts_company_estado", "gov_bank_accounts", ["company_id", "estado"])

    op.create_table(
        "gov_bank_account_authorizations",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("account_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("position_id", sa.String(36), nullable=False),
        sa.Column("cargo_codigo", sa.String(30), nullable=False),
        sa.Column("cargo_denominacion", sa.String(200), nullable=False),
        sa.Column("cargo_unidad", sa.String(200), nullable=False),
        sa.Column("acto_alta_id", sa.String(36), nullable=False),
        sa.Column("vigente_desde", sa.Date(), nullable=False),
        sa.Column("vigente_hasta", sa.Date(), nullable=True),
        sa.Column("acto_fin_id", sa.String(36), nullable=True),
        sa.Column("motivo_fin", sa.String(500), nullable=True),
        sa.Column("terminada_por", sa.String(36), nullable=True),
        sa.Column("terminada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["gov_bank_accounts.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["position_id"], ["gov_positions.id"]),
        sa.ForeignKeyConstraint(["acto_alta_id"], ["gov_acts.id"]),
        sa.ForeignKeyConstraint(["acto_fin_id"], ["gov_acts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("vigente_hasta IS NULL OR vigente_hasta >= vigente_desde", name="vigencia"),
        sa.CheckConstraint(
            "(vigente_hasta IS NULL) = (motivo_fin IS NULL AND terminada_en IS NULL)",
            name="fin_completo",
        ),
        sa.CheckConstraint("acto_fin_id IS NULL OR vigente_hasta IS NOT NULL", name="acto_fin_terminada"),
    )
    op.create_index("ix_gov_bank_account_authorizations_account_id", "gov_bank_account_authorizations", ["account_id"])
    op.create_index("ix_gov_bank_account_authorizations_company_id", "gov_bank_account_authorizations", ["company_id"])
    op.create_index("ix_gov_bank_account_authorizations_position_id", "gov_bank_account_authorizations", ["position_id"])
    op.create_index("ix_gov_bank_account_authorizations_acto_alta_id", "gov_bank_account_authorizations", ["acto_alta_id"])
    op.create_index(
        "uq_gov_bank_account_authorizations_en_vigor",
        "gov_bank_account_authorizations",
        ["account_id", "position_id"],
        unique=True,
        postgresql_where=sa.text("vigente_hasta IS NULL"),
        sqlite_where=sa.text("vigente_hasta IS NULL"),
    )

    op.create_table(
        "gov_bank_account_history",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("account_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("tipo", sa.String(16), nullable=False),
        sa.Column("detalle", sa.JSON(), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["gov_bank_accounts.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            f"tipo IN ({_en('CREADA', 'EDITADA', 'ACTO_VINCULADO', 'ACTIVADA', 'INACTIVADA', 'REACTIVADA', 'CERRADA', 'AUTORIZADO_ALTA', 'AUTORIZADO_FIN')})",
            name="tipo",
        ),
    )
    op.create_index("ix_gov_bank_account_history_account_id", "gov_bank_account_history", ["account_id"])
    op.create_index("ix_gov_bank_account_history_company_id", "gov_bank_account_history", ["company_id"])

    if bind.dialect.name == "postgresql":
        op.execute("""
            CREATE OR REPLACE FUNCTION kontrol_gov_cuenta_no_borrable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'GOV_BANK_ACCOUNT_NOT_DELETABLE' USING ERRCODE = 'P0001', DETAIL = TG_OP; END; $$
        """)
        op.execute("""
            CREATE TRIGGER trg_gov_bank_accounts_no_delete BEFORE DELETE ON gov_bank_accounts FOR EACH ROW EXECUTE FUNCTION kontrol_gov_cuenta_no_borrable()
        """)
        op.execute("""
            CREATE TRIGGER trg_gov_bank_accounts_no_truncate BEFORE TRUNCATE ON gov_bank_accounts FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_cuenta_no_borrable()
        """)
        op.execute("""
            CREATE TRIGGER trg_gov_bank_account_authorizations_no_delete BEFORE DELETE ON gov_bank_account_authorizations FOR EACH ROW EXECUTE FUNCTION kontrol_gov_cuenta_no_borrable()
        """)
        op.execute("""
            CREATE TRIGGER trg_gov_bank_account_authorizations_no_truncate BEFORE TRUNCATE ON gov_bank_account_authorizations FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_cuenta_no_borrable()
        """)
        op.execute("""
            CREATE OR REPLACE FUNCTION kontrol_gov_cuenta_historia_inmutable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'GOV_BANK_ACCOUNT_HISTORY_IMMUTABLE' USING ERRCODE = 'P0001', DETAIL = TG_OP; END; $$
        """)
        op.execute("""
            CREATE TRIGGER trg_gov_bank_account_history_no_update BEFORE UPDATE ON gov_bank_account_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_cuenta_historia_inmutable()
        """)
        op.execute("""
            CREATE TRIGGER trg_gov_bank_account_history_no_delete BEFORE DELETE ON gov_bank_account_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_cuenta_historia_inmutable()
        """)
        op.execute("""
            CREATE TRIGGER trg_gov_bank_account_history_no_truncate BEFORE TRUNCATE ON gov_bank_account_history FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_cuenta_historia_inmutable()
        """)

    _proceso_sod(bind, "DOC-02", "CTL-06", "TRE-01")

    _conceder_permisos(bind)


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

    _proceso_sod(bind, "DOC-02", "CTL-06")

    if bind.dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_gov_bank_account_history_no_truncate ON gov_bank_account_history")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_bank_account_history_no_delete ON gov_bank_account_history")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_bank_account_history_no_update ON gov_bank_account_history")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_bank_account_authorizations_no_truncate ON gov_bank_account_authorizations")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_bank_account_authorizations_no_delete ON gov_bank_account_authorizations")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_bank_accounts_no_truncate ON gov_bank_accounts")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_bank_accounts_no_delete ON gov_bank_accounts")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_cuenta_historia_inmutable()")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_cuenta_no_borrable()")

    op.drop_index("ix_gov_bank_account_history_company_id", table_name="gov_bank_account_history")
    op.drop_index("ix_gov_bank_account_history_account_id", table_name="gov_bank_account_history")
    op.drop_table("gov_bank_account_history")

    op.drop_index("uq_gov_bank_account_authorizations_en_vigor", table_name="gov_bank_account_authorizations")
    op.drop_index("ix_gov_bank_account_authorizations_acto_alta_id", table_name="gov_bank_account_authorizations")
    op.drop_index("ix_gov_bank_account_authorizations_position_id", table_name="gov_bank_account_authorizations")
    op.drop_index("ix_gov_bank_account_authorizations_company_id", table_name="gov_bank_account_authorizations")
    op.drop_index("ix_gov_bank_account_authorizations_account_id", table_name="gov_bank_account_authorizations")
    op.drop_table("gov_bank_account_authorizations")

    op.drop_index("ix_gov_bank_accounts_company_estado", table_name="gov_bank_accounts")
    op.drop_index("ix_gov_bank_accounts_acto_id", table_name="gov_bank_accounts")
    op.drop_index("ix_gov_bank_accounts_bank_id", table_name="gov_bank_accounts")
    op.drop_index("ix_gov_bank_accounts_company_id", table_name="gov_bank_accounts")
    op.drop_index("ix_gov_bank_accounts_tenant_id", table_name="gov_bank_accounts")
    op.drop_table("gov_bank_accounts")

    op.drop_index("ix_gov_banks_company_id", table_name="gov_banks")
    op.drop_index("ix_gov_banks_tenant_id", table_name="gov_banks")
    op.drop_table("gov_banks")
