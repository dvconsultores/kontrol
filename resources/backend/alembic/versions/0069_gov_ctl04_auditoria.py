"""gov ctl04 auditoria

Crea las tablas `gov_audit_samples` y `gov_audit_sample_items` (muestras de auditoría de solo inserción y el permiso gobierno_auditoria).
Registra el permiso `gobierno_auditoria:view` y `gobierno_auditoria:sample` y lo concede al rol protegido
FUNCIONAL_COMPLETO de las instalaciones existentes.

Revision ID: 0069_gov_ctl04_auditoria
Revises: 0068_gov_org07_autoridad
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa

from alembic import op

revision = "0069_gov_ctl04_auditoria"
down_revision = "0068_gov_org07_autoridad"
branch_labels = None
depends_on = None

PERMISOS = {"gobierno_auditoria": ("view", "sample")}


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
        "gov_audit_samples",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("titulo", sa.String(200), nullable=False),
        sa.Column("criterio", sa.Text(), nullable=False),
        sa.Column("justificacion", sa.Text(), nullable=False),
        sa.Column("metodo", sa.String(12), nullable=False),
        sa.Column("semilla", sa.BigInteger(), nullable=True),
        sa.Column("tamano", sa.Integer(), nullable=False),
        sa.Column("poblacion", sa.Integer(), nullable=False),
        sa.Column("filtros", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "codigo", name="uq_gov_audit_samples_company_id_codigo"),
        sa.CheckConstraint(f"metodo IN ({_en(*('TODAS', 'ESPECIFICA', 'ALEATORIA'))})", name="metodo"),
        sa.CheckConstraint("(metodo = 'ALEATORIA') = (semilla IS NOT NULL)", name="semilla_solo_aleatoria"),
        sa.CheckConstraint("tamano >= 1 AND tamano <= poblacion", name="tamano"),
    )
    op.create_index("ix_gov_audit_samples_tenant_id", "gov_audit_samples", ["tenant_id"])
    op.create_index("ix_gov_audit_samples_company_id", "gov_audit_samples", ["company_id"])

    op.create_table(
        "gov_audit_sample_items",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("sample_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("audit_event_id", sa.String(36), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["sample_id"], ["gov_audit_samples.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["audit_event_id"], ["audit_events.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sample_id", "audit_event_id", name="uq_gov_audit_sample_items_sample_id_audit_event_id"),
        sa.UniqueConstraint("sample_id", "orden", name="uq_gov_audit_sample_items_sample_id_orden"),
        sa.CheckConstraint("orden >= 1", name="orden"),
    )
    op.create_index("ix_gov_audit_sample_items_sample_id", "gov_audit_sample_items", ["sample_id"])
    op.create_index("ix_gov_audit_sample_items_company_id", "gov_audit_sample_items", ["company_id"])
    op.create_index("ix_gov_audit_sample_items_audit_event_id", "gov_audit_sample_items", ["audit_event_id"])

    if bind.dialect.name == "postgresql":
        op.execute("""
            CREATE OR REPLACE FUNCTION kontrol_gov_audit_samples_inmutable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'GOV_AUDIT_SAMPLE_IMMUTABLE' USING ERRCODE = 'P0001', DETAIL = TG_OP; END; $$
        """)
        op.execute("CREATE TRIGGER trg_gov_audit_samples_no_update BEFORE UPDATE ON gov_audit_samples FOR EACH ROW EXECUTE FUNCTION kontrol_gov_audit_samples_inmutable()")
        op.execute("CREATE TRIGGER trg_gov_audit_samples_no_delete BEFORE DELETE ON gov_audit_samples FOR EACH ROW EXECUTE FUNCTION kontrol_gov_audit_samples_inmutable()")
        op.execute("CREATE TRIGGER trg_gov_audit_samples_no_truncate BEFORE TRUNCATE ON gov_audit_samples FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_audit_samples_inmutable()")
        op.execute("CREATE TRIGGER trg_gov_audit_sample_items_no_update BEFORE UPDATE ON gov_audit_sample_items FOR EACH ROW EXECUTE FUNCTION kontrol_gov_audit_samples_inmutable()")
        op.execute("CREATE TRIGGER trg_gov_audit_sample_items_no_delete BEFORE DELETE ON gov_audit_sample_items FOR EACH ROW EXECUTE FUNCTION kontrol_gov_audit_samples_inmutable()")
        op.execute("CREATE TRIGGER trg_gov_audit_sample_items_no_truncate BEFORE TRUNCATE ON gov_audit_sample_items FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_audit_samples_inmutable()")

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
        op.execute("DROP TRIGGER IF EXISTS trg_gov_audit_sample_items_no_update ON gov_audit_sample_items")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_audit_sample_items_no_delete ON gov_audit_sample_items")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_audit_sample_items_no_truncate ON gov_audit_sample_items")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_audit_samples_no_update ON gov_audit_samples")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_audit_samples_no_delete ON gov_audit_samples")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_audit_samples_no_truncate ON gov_audit_samples")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_audit_samples_inmutable()")

    op.drop_index("ix_gov_audit_sample_items_audit_event_id", table_name="gov_audit_sample_items")
    op.drop_index("ix_gov_audit_sample_items_company_id", table_name="gov_audit_sample_items")
    op.drop_index("ix_gov_audit_sample_items_sample_id", table_name="gov_audit_sample_items")
    op.drop_table("gov_audit_sample_items")
    op.drop_index("ix_gov_audit_samples_company_id", table_name="gov_audit_samples")
    op.drop_index("ix_gov_audit_samples_tenant_id", table_name="gov_audit_samples")
    op.drop_table("gov_audit_samples")
