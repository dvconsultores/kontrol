"""gov doc08 paquetes

Crea las tablas de paquetes de auditoría exportables y de sus verificaciones (DOC-08, GOV-DOC-010),
registra `gobierno_paquetes:view` y `gobierno_paquetes:generate` y los concede al rol protegido
FUNCIONAL_COMPLETO de las instalaciones existentes.

Revision ID: 0071_gov_doc08_paquetes
Revises: 0070_gov_ctl06_hallazgos
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa

from alembic import op

revision = "0071_gov_doc08_paquetes"
down_revision = "0070_gov_ctl06_hallazgos"
branch_labels = None
depends_on = None

PERMISOS = {"gobierno_paquetes": ("view", "generate")}


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
        "gov_audit_packages",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("sample_id", sa.String(36), nullable=False),
        sa.Column("numero_generacion", sa.Integer(), nullable=False),
        sa.Column("titulo", sa.String(200), nullable=False),
        sa.Column("proposito", sa.Text(), nullable=False),
        sa.Column("version_manifiesto", sa.Integer(), nullable=False),
        sa.Column("huella_manifiesto", sa.String(64), nullable=False),
        sa.Column("huella_paquete", sa.String(64), nullable=False),
        sa.Column("bytes", sa.BigInteger(), nullable=False),
        sa.Column("clave_almacenamiento", sa.String(255), nullable=False),
        sa.Column("nombre_archivo", sa.String(80), nullable=False),
        sa.Column("eventos", sa.Integer(), nullable=False),
        sa.Column("documentos_incluidos", sa.Integer(), nullable=False),
        sa.Column("documentos_excluidos", sa.Integer(), nullable=False),
        sa.Column("hallazgos", sa.Integer(), nullable=False),
        sa.Column("archivos", sa.Integer(), nullable=False),
        sa.Column("manifiesto", sa.JSON(), nullable=False),
        sa.Column("idempotency_key", sa.String(100), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["sample_id"], ["gov_audit_samples.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "codigo", name="uq_gov_audit_packages_company_id_codigo"),
        sa.UniqueConstraint("sample_id", "numero_generacion", name="uq_gov_audit_packages_sample_id_numero_generacion"),
        sa.UniqueConstraint("company_id", "idempotency_key", name="uq_gov_audit_packages_company_id_idempotency_key"),
        sa.UniqueConstraint("clave_almacenamiento", name="uq_gov_audit_packages_clave_almacenamiento"),
        sa.CheckConstraint("length(huella_manifiesto) = 64 AND length(huella_paquete) = 64", name="huellas"),
        sa.CheckConstraint("bytes > 0", name="bytes"),
        sa.CheckConstraint("eventos >= 0 AND documentos_incluidos >= 0 AND documentos_excluidos >= 0 AND hallazgos >= 0 AND archivos >= 0", name="contadores"),
        sa.CheckConstraint("numero_generacion >= 1", name="numero_generacion"),
        sa.CheckConstraint("version_manifiesto = 1", name="version_manifiesto"),
    )
    op.create_index("ix_gov_audit_packages_tenant_id", "gov_audit_packages", ["tenant_id"])
    op.create_index("ix_gov_audit_packages_company_id", "gov_audit_packages", ["company_id"])
    op.create_index("ix_gov_audit_packages_sample_id", "gov_audit_packages", ["sample_id"])

    if bind.dialect.name == "postgresql":
        op.execute("""
            CREATE OR REPLACE FUNCTION kontrol_gov_audit_package_inmutable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'GOV_AUDIT_PACKAGE_IMMUTABLE' USING ERRCODE = 'P0001', DETAIL = TG_OP; END; $$
        """)
        op.execute("CREATE TRIGGER trg_gov_audit_packages_no_update BEFORE UPDATE ON gov_audit_packages FOR EACH ROW EXECUTE FUNCTION kontrol_gov_audit_package_inmutable()")
        op.execute("CREATE TRIGGER trg_gov_audit_packages_no_delete BEFORE DELETE ON gov_audit_packages FOR EACH ROW EXECUTE FUNCTION kontrol_gov_audit_package_inmutable()")
        op.execute("CREATE TRIGGER trg_gov_audit_packages_no_truncate BEFORE TRUNCATE ON gov_audit_packages FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_audit_package_inmutable()")

    op.create_table(
        "gov_audit_package_verifications",
        sa.Column("id", sa.String(36), nullable=False),
        *_tiempos(),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("package_id", sa.String(36), nullable=False),
        sa.Column("resultado", sa.String(20), nullable=False),
        sa.Column("motivos", sa.JSON(), nullable=False),
        sa.Column("huella_archivo", sa.String(64), nullable=False),
        sa.Column("bytes_archivo", sa.BigInteger(), nullable=False),
        sa.Column("identico", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["package_id"], ["gov_audit_packages.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(f"resultado IN ({_en(*('VALIDO', 'INVALIDO', 'INCOMPLETO', 'VERSION_NO_SOPORTADA'))})", name="resultado"),
        sa.CheckConstraint("length(huella_archivo) = 64", name="huella_archivo"),
        sa.CheckConstraint("bytes_archivo >= 0", name="bytes_archivo"),
    )
    op.create_index("ix_gov_audit_package_verifications_company_id", "gov_audit_package_verifications", ["company_id"])
    op.create_index("ix_gov_audit_package_verifications_package_id", "gov_audit_package_verifications", ["package_id"])

    if bind.dialect.name == "postgresql":
        op.execute("""
            CREATE OR REPLACE FUNCTION kontrol_gov_audit_package_inmutable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'GOV_AUDIT_PACKAGE_IMMUTABLE' USING ERRCODE = 'P0001', DETAIL = TG_OP; END; $$
        """)
        op.execute("CREATE TRIGGER trg_gov_audit_package_verifications_no_update BEFORE UPDATE ON gov_audit_package_verifications FOR EACH ROW EXECUTE FUNCTION kontrol_gov_audit_package_inmutable()")
        op.execute("CREATE TRIGGER trg_gov_audit_package_verifications_no_delete BEFORE DELETE ON gov_audit_package_verifications FOR EACH ROW EXECUTE FUNCTION kontrol_gov_audit_package_inmutable()")
        op.execute("CREATE TRIGGER trg_gov_audit_package_verifications_no_truncate BEFORE TRUNCATE ON gov_audit_package_verifications FOR EACH STATEMENT EXECUTE FUNCTION kontrol_gov_audit_package_inmutable()")

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
        op.execute("DROP TRIGGER IF EXISTS trg_gov_audit_package_verifications_no_update ON gov_audit_package_verifications")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_audit_package_verifications_no_delete ON gov_audit_package_verifications")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_audit_package_verifications_no_truncate ON gov_audit_package_verifications")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_audit_packages_no_update ON gov_audit_packages")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_audit_packages_no_delete ON gov_audit_packages")
        op.execute("DROP TRIGGER IF EXISTS trg_gov_audit_packages_no_truncate ON gov_audit_packages")
        op.execute("DROP FUNCTION IF EXISTS kontrol_gov_audit_package_inmutable()")

    op.drop_index("ix_gov_audit_package_verifications_package_id", table_name="gov_audit_package_verifications")
    op.drop_index("ix_gov_audit_package_verifications_company_id", table_name="gov_audit_package_verifications")
    op.drop_table("gov_audit_package_verifications")

    op.drop_index("ix_gov_audit_packages_sample_id", table_name="gov_audit_packages")
    op.drop_index("ix_gov_audit_packages_company_id", table_name="gov_audit_packages")
    op.drop_index("ix_gov_audit_packages_tenant_id", table_name="gov_audit_packages")
    op.drop_table("gov_audit_packages")
