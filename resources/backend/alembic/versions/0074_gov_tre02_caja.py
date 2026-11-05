"""gov tre02 caja

Crea los rubros de caja, los programas de caja, sus versiones, declaraciones, líneas e historia
(TRE-02, GOV-TRE-002), amplía el proceso de las reglas SoD y registra `gobierno_caja:view`, `:manage` y `:activate`
y los concede al rol protegido FUNCIONAL_COMPLETO de las instalaciones existentes.

Revision ID: 0074_gov_tre02_caja
Revises: 0073_gov_tre01_cuentas
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa

from alembic import op

revision = "0074_gov_tre02_caja"
down_revision = "0073_gov_tre01_cuentas"
branch_labels = None
depends_on = None

PERMISOS = {"gobierno_caja": ("view", "manage", "activate")}


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
        "gov_cash_items",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("nombre", sa.String(120), nullable=False),
        sa.Column("tipo", sa.String(11), nullable=False),
        sa.Column("estado", sa.String(10), nullable=False, server_default="ACTIVO"),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "codigo", name="uq_gov_cash_items_company_id_codigo"),
        sa.CheckConstraint(f"tipo IN ({_en('INGRESO', 'DESEMBOLSO')})", name="tipo"),
        sa.CheckConstraint(f"estado IN ({_en('ACTIVO', 'INACTIVO')})", name="estado"),
        sa.CheckConstraint("version >= 1", name="version"),
    )
    op.create_index("ix_gov_cash_items_tenant_id", "gov_cash_items", ["tenant_id"])
    op.create_index("ix_gov_cash_items_company_id", "gov_cash_items", ["company_id"])

    op.create_table(
        "gov_cash_programs",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("ejercicio", sa.SmallInteger(), nullable=False),
        sa.Column("moneda", sa.String(3), nullable=False),
        sa.Column("mes_inicial", sa.SmallInteger(), nullable=False),
        sa.Column("estado", sa.String(11), nullable=False, server_default="BORRADOR"),
        sa.Column("cerrado_por", sa.String(36), nullable=True),
        sa.Column("cerrado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("motivo_cierre", sa.String(500), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(f"moneda IN ({_en('VES', 'USD', 'EUR')})", name="moneda"),
        sa.CheckConstraint(f"estado IN ({_en('BORRADOR', 'VIGENTE', 'CERRADO', 'DESCARTADO')})", name="estado"),
        sa.CheckConstraint("mes_inicial BETWEEN 1 AND 12", name="mes_inicial"),
        sa.CheckConstraint(
            "(estado = 'CERRADO') = (cerrado_en IS NOT NULL AND motivo_cierre IS NOT NULL)",
            name="cierre_completo",
        ),
        sa.CheckConstraint("version >= 1", name="version"),
    )
    op.create_index("ix_gov_cash_programs_tenant_id", "gov_cash_programs", ["tenant_id"])
    op.create_index("ix_gov_cash_programs_company_id", "gov_cash_programs", ["company_id"])
    op.create_index("ix_gov_cash_programs_company_estado", "gov_cash_programs", ["company_id", "estado"])
    op.create_index(
        "uq_gov_cash_programs_company_ejercicio_moneda_activos",
        "gov_cash_programs",
        ["company_id", "ejercicio", "moneda"],
        unique=True,
        postgresql_where=sa.text("estado <> 'DESCARTADO'"),
        sqlite_where=sa.text("estado <> 'DESCARTADO'"),
    )

    op.create_table(
        "gov_cash_program_versions",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("program_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("numero", sa.SmallInteger(), nullable=False),
        sa.Column("estado", sa.String(11), nullable=False),
        sa.Column("motivo", sa.String(500), nullable=True),
        sa.Column("activada_por", sa.String(36), nullable=True),
        sa.Column("activada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["program_id"], ["gov_cash_programs.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("program_id", "numero", name="uq_gov_cash_program_versions_program_id_numero"),
        sa.CheckConstraint(f"estado IN ({_en('BORRADOR', 'VIGENTE', 'SUPERADA', 'DESCARTADA', 'CERRADA')})", name="estado"),
        sa.CheckConstraint("numero >= 1", name="numero"),
        sa.CheckConstraint(
            "(estado IN ('BORRADOR', 'DESCARTADA')) = (activada_por IS NULL AND activada_en IS NULL) AND "
            "(estado IN ('VIGENTE', 'SUPERADA', 'CERRADA')) = (activada_por IS NOT NULL AND activada_en IS NOT NULL)",
            name="activacion_completa",
        ),
    )
    op.create_index("ix_gov_cash_program_versions_program_id", "gov_cash_program_versions", ["program_id"])
    op.create_index("ix_gov_cash_program_versions_company_id", "gov_cash_program_versions", ["company_id"])
    op.create_index(
        "uq_gov_cash_program_versions_borrador_por_programa",
        "gov_cash_program_versions",
        ["program_id"],
        unique=True,
        postgresql_where=sa.text("estado = 'BORRADOR'"),
        sqlite_where=sa.text("estado = 'BORRADOR'"),
    )
    op.create_index(
        "uq_gov_cash_program_versions_vigente_por_programa",
        "gov_cash_program_versions",
        ["program_id"],
        unique=True,
        postgresql_where=sa.text("estado = 'VIGENTE'"),
        sqlite_where=sa.text("estado = 'VIGENTE'"),
    )

    op.create_table(
        "gov_cash_program_declarations",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("program_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("account_id", sa.String(36), nullable=False),
        sa.Column("monto", sa.Numeric(18, 2), nullable=False),
        sa.Column("fecha_corte", sa.Date(), nullable=False),
        sa.Column("fundamento", sa.String(500), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["program_id"], ["gov_cash_programs.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["account_id"], ["gov_bank_accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("program_id", "account_id", name="uq_gov_cash_program_declarations_programa_cuenta"),
        sa.CheckConstraint("monto >= 0", name="monto"),
        sa.CheckConstraint("length(fundamento) BETWEEN 10 AND 500", name="fundamento"),
    )
    op.create_index("ix_gov_cash_program_declarations_program_id", "gov_cash_program_declarations", ["program_id"])
    op.create_index("ix_gov_cash_program_declarations_company_id", "gov_cash_program_declarations", ["company_id"])
    op.create_index("ix_gov_cash_program_declarations_account_id", "gov_cash_program_declarations", ["account_id"])

    op.create_table(
        "gov_cash_program_lines",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("version_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("item_id", sa.String(36), nullable=False),
        sa.Column("mes", sa.SmallInteger(), nullable=False),
        sa.Column("monto", sa.Numeric(18, 2), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["version_id"], ["gov_cash_program_versions.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["item_id"], ["gov_cash_items.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version_id", "item_id", "mes", name="uq_gov_cash_program_lines_version_rubro_mes"),
        sa.CheckConstraint("mes BETWEEN 1 AND 12", name="mes"),
        sa.CheckConstraint("monto > 0", name="monto"),
    )
    op.create_index("ix_gov_cash_program_lines_version_id", "gov_cash_program_lines", ["version_id"])
    op.create_index("ix_gov_cash_program_lines_company_id", "gov_cash_program_lines", ["company_id"])
    op.create_index("ix_gov_cash_program_lines_item_id", "gov_cash_program_lines", ["item_id"])

    op.create_table(
        "gov_cash_program_history",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("program_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("version_numero", sa.SmallInteger(), nullable=False),
        sa.Column("tipo", sa.String(14), nullable=False),
        sa.Column("detalle", sa.JSON(), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["program_id"], ["gov_cash_programs.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            f"tipo IN ({_en('CREADO', 'DECLARACION', 'LINEA', 'ACTIVADO', 'REPROGRAMADO', 'DESCARTADO', 'CERRADO')})",
            name="tipo",
        ),
    )
    op.create_index("ix_gov_cash_program_history_program_id", "gov_cash_program_history", ["program_id"])
    op.create_index("ix_gov_cash_program_history_company_id", "gov_cash_program_history", ["company_id"])

    if bind.dialect.name == "postgresql":
        op.execute("""
            CREATE OR REPLACE FUNCTION kontrol_gov_cash_program_no_borrable() RETURNS TRIGGER AS $$ BEGIN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CASH_PROGRAM_NOT_DELETABLE', DETAIL = TG_OP; END; $$ LANGUAGE plpgsql
        """)
        op.execute("""
            CREATE TRIGGER trg_gov_cash_programs_no_delete BEFORE DELETE ON gov_cash_programs FOR EACH ROW EXECUTE FUNCTION kontrol_gov_cash_program_no_borrable()
        """)
        op.execute("""
            CREATE TRIGGER trg_gov_cash_programs_no_truncate BEFORE TRUNCATE ON gov_cash_programs FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_cash_program_no_borrable()
        """)
        op.execute("""
            CREATE TRIGGER trg_gov_cash_program_versions_no_delete BEFORE DELETE ON gov_cash_program_versions FOR EACH ROW EXECUTE FUNCTION kontrol_gov_cash_program_no_borrable()
        """)
        op.execute("""
            CREATE TRIGGER trg_gov_cash_program_versions_no_truncate BEFORE TRUNCATE ON gov_cash_program_versions FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_cash_program_no_borrable()
        """)
        op.execute("""
            CREATE OR REPLACE FUNCTION kontrol_gov_cash_program_historia_inmutable() RETURNS TRIGGER AS $$ BEGIN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CASH_PROGRAM_HISTORY_IMMUTABLE', DETAIL = TG_OP; END; $$ LANGUAGE plpgsql
        """)
        op.execute("""
            CREATE TRIGGER trg_gov_cash_program_history_no_update BEFORE UPDATE ON gov_cash_program_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_cash_program_historia_inmutable()
        """)
        op.execute("""
            CREATE TRIGGER trg_gov_cash_program_history_no_delete BEFORE DELETE ON gov_cash_program_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_cash_program_historia_inmutable()
        """)
        op.execute("""
            CREATE TRIGGER trg_gov_cash_program_history_no_truncate BEFORE TRUNCATE ON gov_cash_program_history FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_cash_program_historia_inmutable()
        """)
        op.execute("""
            CREATE OR REPLACE FUNCTION kontrol_gov_cash_line_solo_borrador() RETURNS TRIGGER AS $$ DECLARE version_estado TEXT; BEGIN IF TG_OP = 'DELETE' THEN SELECT estado INTO version_estado FROM gov_cash_program_versions WHERE id = OLD.version_id; ELSE SELECT estado INTO version_estado FROM gov_cash_program_versions WHERE id = NEW.version_id; END IF; IF version_estado IS DISTINCT FROM 'BORRADOR' THEN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CASH_LINE_VERSION_NOT_BORRADOR', DETAIL = TG_OP; END IF; IF TG_OP = 'DELETE' THEN RETURN OLD; END IF; RETURN NEW; END; $$ LANGUAGE plpgsql
        """)
        op.execute("""
            CREATE TRIGGER trg_gov_cash_program_lines_only_borrador BEFORE INSERT OR UPDATE OR DELETE ON gov_cash_program_lines FOR EACH ROW EXECUTE FUNCTION kontrol_gov_cash_line_solo_borrador()
        """)
        op.execute("""
            CREATE OR REPLACE FUNCTION kontrol_gov_cash_declaracion_solo_borrador() RETURNS TRIGGER AS $$ DECLARE programa_estado TEXT; BEGIN IF TG_OP = 'DELETE' THEN SELECT p.estado INTO programa_estado FROM gov_cash_programs p WHERE p.id = OLD.program_id; ELSE SELECT p.estado INTO programa_estado FROM gov_cash_programs p WHERE p.id = NEW.program_id; END IF; IF programa_estado IS DISTINCT FROM 'BORRADOR' THEN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_CASH_DECLARATION_PROGRAM_NOT_BORRADOR', DETAIL = TG_OP; END IF; IF TG_OP = 'DELETE' THEN RETURN OLD; END IF; RETURN NEW; END; $$ LANGUAGE plpgsql
        """)
        op.execute("""
            CREATE TRIGGER trg_gov_cash_program_declarations_only_borrador BEFORE INSERT OR UPDATE OR DELETE ON gov_cash_program_declarations FOR EACH ROW EXECUTE FUNCTION kontrol_gov_cash_declaracion_solo_borrador()
        """)

    _proceso_sod(bind, "DOC-02", "CTL-06", "TRE-01", "TRE-02")

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

    _proceso_sod(bind, "DOC-02", "CTL-06", "TRE-01")

    if bind.dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_gov_cash_program_declarations_only_borrador ON gov_cash_program_declarations")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_cash_declaracion_solo_borrador()")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_cash_program_lines_only_borrador ON gov_cash_program_lines")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_cash_line_solo_borrador()")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_cash_program_history_no_truncate ON gov_cash_program_history")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_cash_program_history_no_delete ON gov_cash_program_history")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_cash_program_history_no_update ON gov_cash_program_history")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_cash_program_historia_inmutable()")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_cash_program_versions_no_truncate ON gov_cash_program_versions")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_cash_program_versions_no_delete ON gov_cash_program_versions")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_cash_programs_no_truncate ON gov_cash_programs")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_cash_programs_no_delete ON gov_cash_programs")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_cash_program_no_borrable()")

    op.drop_index("ix_gov_cash_program_history_company_id", table_name="gov_cash_program_history")
    op.drop_index("ix_gov_cash_program_history_program_id", table_name="gov_cash_program_history")
    op.drop_table("gov_cash_program_history")

    op.drop_index("ix_gov_cash_program_lines_item_id", table_name="gov_cash_program_lines")
    op.drop_index("ix_gov_cash_program_lines_company_id", table_name="gov_cash_program_lines")
    op.drop_index("ix_gov_cash_program_lines_version_id", table_name="gov_cash_program_lines")
    op.drop_table("gov_cash_program_lines")

    op.drop_index("ix_gov_cash_program_declarations_account_id", table_name="gov_cash_program_declarations")
    op.drop_index("ix_gov_cash_program_declarations_company_id", table_name="gov_cash_program_declarations")
    op.drop_index("ix_gov_cash_program_declarations_program_id", table_name="gov_cash_program_declarations")
    op.drop_table("gov_cash_program_declarations")

    op.drop_index(
        "uq_gov_cash_program_versions_vigente_por_programa",
        table_name="gov_cash_program_versions",
    )
    op.drop_index(
        "uq_gov_cash_program_versions_borrador_por_programa",
        table_name="gov_cash_program_versions",
    )
    op.drop_index("ix_gov_cash_program_versions_company_id", table_name="gov_cash_program_versions")
    op.drop_index("ix_gov_cash_program_versions_program_id", table_name="gov_cash_program_versions")
    op.drop_table("gov_cash_program_versions")

    op.drop_index(
        "uq_gov_cash_programs_company_ejercicio_moneda_activos",
        table_name="gov_cash_programs",
    )
    op.drop_index("ix_gov_cash_programs_company_estado", table_name="gov_cash_programs")
    op.drop_index("ix_gov_cash_programs_company_id", table_name="gov_cash_programs")
    op.drop_index("ix_gov_cash_programs_tenant_id", table_name="gov_cash_programs")
    op.drop_table("gov_cash_programs")

    op.drop_index("ix_gov_cash_items_company_id", table_name="gov_cash_items")
    op.drop_index("ix_gov_cash_items_tenant_id", table_name="gov_cash_items")
    op.drop_table("gov_cash_items")
