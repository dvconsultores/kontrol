"""gov org06 identidad

Crea vínculos cuenta-funcionario, categorías de rol, política de identidad y sus historias (ORG-06), registra `gobierno_identidad` y añade ORG-06 a los procesos de SoD.

Revision ID: 0077_gov_org06_identidad
Revises: 0076_gov_org04_ocupacion
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa

from alembic import op

revision = "0077_gov_org06_identidad"
down_revision = "0076_gov_org04_ocupacion"
branch_labels = None
depends_on = None

PERMISOS = {"gobierno_identidad": ("view", "manage", "activate", "revoke")}


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
        "gov_user_official_links",
        sa.Column("id", sa.String(36), primary_key=True),
        *_tiempos(),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("version", sa.BigInteger, nullable=False, server_default="1"),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("official_id", sa.String(36), sa.ForeignKey("gov_officials.id"), nullable=False),
        sa.Column("desde", sa.Date, nullable=False),
        sa.Column("hasta", sa.Date, nullable=True),
        sa.Column("fin_efectivo", sa.Date, nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="BORRADOR"),
        sa.Column("motivo", sa.String(500), nullable=False),
        sa.Column("soporte", sa.String(200), nullable=True),
        sa.Column("motivo_fin", sa.String(500), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_by", sa.String(36), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_by", sa.String(36), nullable=True),
        sa.UniqueConstraint("company_id", "codigo", name="uq_gov_user_official_links_codigo"),
        sa.CheckConstraint("status IN ('BORRADOR', 'ACTIVO', 'CERRADO', 'REVOCADO', 'DESCARTADO')", name="ck_gov_user_official_links_status"),
        sa.CheckConstraint("version >= 1", name="ck_gov_user_official_links_version"),
        sa.CheckConstraint("hasta IS NULL OR hasta >= desde", name="ck_gov_user_official_links_vigencia"),
        sa.CheckConstraint("fin_efectivo IS NULL OR fin_efectivo >= desde", name="ck_gov_user_official_links_fin_tras_inicio"),
        sa.CheckConstraint("status NOT IN ('CERRADO','REVOCADO') OR (fin_efectivo IS NOT NULL AND motivo_fin IS NOT NULL)", name="ck_gov_user_official_links_fin_con_motivo"),
        sa.CheckConstraint("status IN ('BORRADOR','DESCARTADO') OR activated_at IS NOT NULL", name="ck_gov_user_official_links_activado_fechado"),
    )
    op.create_index("ix_gov_user_official_links_company_id", "gov_user_official_links", ["company_id"])
    op.create_index("ix_gov_user_official_links_user_id", "gov_user_official_links", ["user_id"])
    op.create_index("ix_gov_user_official_links_official_id", "gov_user_official_links", ["official_id"])

    op.create_table(
        "gov_user_official_link_history",
        sa.Column("id", sa.String(36), primary_key=True),
        *_tiempos(),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("link_id", sa.String(36), sa.ForeignKey("gov_user_official_links.id"), nullable=False),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("tipo", sa.String(16), nullable=False),
        sa.Column("detalle", sa.JSON, nullable=True),
        sa.CheckConstraint("tipo IN ('CREADO', 'EDITADO', 'ACTIVADO', 'DESCARTADO', 'CERRADO', 'REVOCADO')", name="ck_gov_user_official_link_history_tipo"),
    )
    op.create_index("ix_gov_user_official_link_history_link_id", "gov_user_official_link_history", ["link_id"])
    op.create_index("ix_gov_user_official_link_history_company_id", "gov_user_official_link_history", ["company_id"])

    op.create_table(
        "gov_role_categories",
        sa.Column("id", sa.String(36), primary_key=True),
        *_tiempos(),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("version", sa.BigInteger, nullable=False, server_default="1"),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("role_id", sa.String(36), sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("categoria", sa.String(32), nullable=False),
        sa.Column("desde", sa.Date, nullable=False),
        sa.Column("hasta", sa.Date, nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="ACTIVA"),
        sa.Column("motivo", sa.String(500), nullable=False),
        sa.CheckConstraint("categoria IN ('OPERATIVO', 'APROBADOR', 'CONTROL_INTERNO', 'AUDITORIA', 'ADMINISTRACION_TECNICA')", name="ck_gov_role_categories_categoria"),
        sa.CheckConstraint("status IN ('ACTIVA', 'RETIRADA')", name="ck_gov_role_categories_status"),
        sa.CheckConstraint("version >= 1", name="ck_gov_role_categories_version"),
        sa.CheckConstraint("hasta IS NULL OR hasta >= desde", name="ck_gov_role_categories_vigencia"),
        sa.CheckConstraint("status <> 'RETIRADA' OR hasta IS NOT NULL", name="ck_gov_role_categories_retirada_con_fin"),
    )
    op.create_index("ix_gov_role_categories_company_id", "gov_role_categories", ["company_id"])
    op.create_index("ix_gov_role_categories_role_id", "gov_role_categories", ["role_id"])

    op.create_table(
        "gov_role_category_history",
        sa.Column("id", sa.String(36), primary_key=True),
        *_tiempos(),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("category_id", sa.String(36), sa.ForeignKey("gov_role_categories.id"), nullable=False),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("tipo", sa.String(16), nullable=False),
        sa.Column("detalle", sa.JSON, nullable=True),
        sa.CheckConstraint("tipo IN ('AGREGADA', 'RETIRADA')", name="ck_gov_role_category_history_tipo"),
    )
    op.create_index("ix_gov_role_category_history_category_id", "gov_role_category_history", ["category_id"])
    op.create_index("ix_gov_role_category_history_company_id", "gov_role_category_history", ["company_id"])

    op.create_table(
        "gov_identity_policies",
        sa.Column("id", sa.String(36), primary_key=True),
        *_tiempos(),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("version", sa.BigInteger, nullable=False, server_default="1"),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("exige_identidad", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("motivo", sa.String(500), nullable=True),
        sa.UniqueConstraint("company_id", name="uq_gov_identity_policies_company_id"),
        sa.CheckConstraint("version >= 1", name="ck_gov_identity_policies_version"),
    )
    op.create_index("ix_gov_identity_policies_company_id", "gov_identity_policies", ["company_id"], unique=True)

    op.create_table(
        "gov_identity_policy_history",
        sa.Column("id", sa.String(36), primary_key=True),
        *_tiempos(),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("policy_id", sa.String(36), sa.ForeignKey("gov_identity_policies.id"), nullable=False),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("tipo", sa.String(16), nullable=False),
        sa.Column("detalle", sa.JSON, nullable=True),
        sa.CheckConstraint("tipo IN ('CAMBIADA')", name="ck_gov_identity_policy_history_tipo"),
    )
    op.create_index("ix_gov_identity_policy_history_policy_id", "gov_identity_policy_history", ["policy_id"])
    op.create_index("ix_gov_identity_policy_history_company_id", "gov_identity_policy_history", ["company_id"])

    if op.get_bind().dialect.name == "postgresql":
        op.execute("CREATE OR REPLACE FUNCTION kontrol_gov_vinculo_historia_inmutable() RETURNS TRIGGER AS $$ BEGIN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_LINK_HISTORY_IMMUTABLE', DETAIL = TG_OP; END; $$ LANGUAGE plpgsql")
        op.execute("CREATE TRIGGER trg_gov_link_history_no_update BEFORE UPDATE ON gov_user_official_link_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_vinculo_historia_inmutable()")
        op.execute("CREATE TRIGGER trg_gov_link_history_no_delete BEFORE DELETE ON gov_user_official_link_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_vinculo_historia_inmutable()")
        op.execute("CREATE TRIGGER trg_gov_link_history_no_truncate BEFORE TRUNCATE ON gov_user_official_link_history FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_vinculo_historia_inmutable()")

        op.execute("CREATE OR REPLACE FUNCTION kontrol_gov_categoria_historia_inmutable() RETURNS TRIGGER AS $$ BEGIN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_ROLE_CATEGORY_HISTORY_IMMUTABLE', DETAIL = TG_OP; END; $$ LANGUAGE plpgsql")
        op.execute("CREATE TRIGGER trg_gov_role_category_history_no_update BEFORE UPDATE ON gov_role_category_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_categoria_historia_inmutable()")
        op.execute("CREATE TRIGGER trg_gov_role_category_history_no_delete BEFORE DELETE ON gov_role_category_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_categoria_historia_inmutable()")
        op.execute("CREATE TRIGGER trg_gov_role_category_history_no_truncate BEFORE TRUNCATE ON gov_role_category_history FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_categoria_historia_inmutable()")

        op.execute("CREATE OR REPLACE FUNCTION kontrol_gov_politica_historia_inmutable() RETURNS TRIGGER AS $$ BEGIN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_POLICY_HISTORY_IMMUTABLE', DETAIL = TG_OP; END; $$ LANGUAGE plpgsql")
        op.execute("CREATE TRIGGER trg_gov_policy_history_no_update BEFORE UPDATE ON gov_identity_policy_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_politica_historia_inmutable()")
        op.execute("CREATE TRIGGER trg_gov_policy_history_no_delete BEFORE DELETE ON gov_identity_policy_history FOR EACH ROW EXECUTE FUNCTION kontrol_gov_politica_historia_inmutable()")
        op.execute("CREATE TRIGGER trg_gov_policy_history_no_truncate BEFORE TRUNCATE ON gov_identity_policy_history FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_politica_historia_inmutable()")

        op.execute("CREATE OR REPLACE FUNCTION kontrol_gov_vinculo_no_borrable() RETURNS TRIGGER AS $$ BEGIN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_LINK_NOT_DELETABLE', DETAIL = TG_OP; END; $$ LANGUAGE plpgsql")
        op.execute("CREATE TRIGGER trg_gov_links_no_delete BEFORE DELETE ON gov_user_official_links FOR EACH ROW EXECUTE FUNCTION kontrol_gov_vinculo_no_borrable()")
        op.execute("CREATE TRIGGER trg_gov_links_no_truncate BEFORE TRUNCATE ON gov_user_official_links FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_vinculo_no_borrable()")

        op.execute("CREATE OR REPLACE FUNCTION kontrol_gov_vinculo_no_editable() RETURNS TRIGGER AS $$ BEGIN IF OLD.status <> 'BORRADOR' AND (NEW.user_id IS DISTINCT FROM OLD.user_id OR NEW.official_id IS DISTINCT FROM OLD.official_id OR NEW.desde IS DISTINCT FROM OLD.desde OR NEW.codigo IS DISTINCT FROM OLD.codigo) THEN RAISE EXCEPTION USING ERRCODE = 'P0001', MESSAGE = 'GOV_LINK_NOT_EDITABLE'; END IF; RETURN NEW; END; $$ LANGUAGE plpgsql")
        op.execute("CREATE TRIGGER trg_gov_links_no_editable BEFORE UPDATE ON gov_user_official_links FOR EACH ROW EXECUTE FUNCTION kontrol_gov_vinculo_no_editable()")

        op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
        op.execute("ALTER TABLE gov_user_official_links ADD CONSTRAINT ex_gov_links_cuenta EXCLUDE USING gist (company_id WITH =, user_id WITH =, daterange(desde, COALESCE(fin_efectivo, hasta), '[]') WITH &&) WHERE (status = 'ACTIVO')")
        op.execute("ALTER TABLE gov_user_official_links ADD CONSTRAINT ex_gov_links_funcionario EXCLUDE USING gist (company_id WITH =, official_id WITH =, daterange(desde, COALESCE(fin_efectivo, hasta), '[]') WITH &&) WHERE (status = 'ACTIVO')")

        op.execute("ALTER TABLE gov_role_categories ADD CONSTRAINT ex_gov_role_categories EXCLUDE USING gist (company_id WITH =, role_id WITH =, categoria WITH =, daterange(desde, hasta, '[]') WITH &&) WHERE (status = 'ACTIVA')")

    _proceso_sod(op.get_bind(), "DOC-02", "CTL-06", "TRE-01", "TRE-02", "CTL-10", "ORG-04", "ORG-06")
    _conceder_permisos(op.get_bind())


def downgrade() -> None:
    _proceso_sod(op.get_bind(), "DOC-02", "CTL-06", "TRE-01", "TRE-02", "CTL-10", "ORG-04")

    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_gov_link_history_no_update ON gov_user_official_link_history")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_link_history_no_delete ON gov_user_official_link_history")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_link_history_no_truncate ON gov_user_official_link_history")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_role_category_history_no_update ON gov_role_category_history")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_role_category_history_no_delete ON gov_role_category_history")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_role_category_history_no_truncate ON gov_role_category_history")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_policy_history_no_update ON gov_identity_policy_history")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_policy_history_no_delete ON gov_identity_policy_history")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_policy_history_no_truncate ON gov_identity_policy_history")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_links_no_delete ON gov_user_official_links")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_links_no_truncate ON gov_user_official_links")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_links_no_editable ON gov_user_official_links")
        op.execute("ALTER TABLE gov_user_official_links DROP CONSTRAINT IF EXISTS ex_gov_links_cuenta")
        op.execute("ALTER TABLE gov_user_official_links DROP CONSTRAINT IF EXISTS ex_gov_links_funcionario")
        op.execute("ALTER TABLE gov_role_categories DROP CONSTRAINT IF EXISTS ex_gov_role_categories")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_vinculo_historia_inmutable()")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_categoria_historia_inmutable()")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_politica_historia_inmutable()")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_vinculo_no_borrable()")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_vinculo_no_editable()")

    bind = op.get_bind()
    permiso_ids = bind.execute(sa.text(
        "SELECT id FROM permissions WHERE resource = 'gobierno_identidad'")).fetchall()
    for fila in permiso_ids:
        bind.execute(sa.text(
            "DELETE FROM role_permissions WHERE permission_id = :p"),
            {"p": fila[0]})
    bind.execute(sa.text(
        "DELETE FROM permissions WHERE resource = 'gobierno_identidad'"))

    op.drop_table("gov_identity_policy_history")
    op.drop_table("gov_identity_policies")
    op.drop_table("gov_role_category_history")
    op.drop_table("gov_role_categories")
    op.drop_table("gov_user_official_link_history")
    op.drop_table("gov_user_official_links")
