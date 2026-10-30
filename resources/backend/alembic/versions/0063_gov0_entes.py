"""gov0 entes

Crea `gov_entities` y `gov_entity_versions` (GOV-0-01, OD-GOV0-03: un ente por
contenedor de empresa) y concede `gobierno_ente:*` al rol protegido
FUNCIONAL_COMPLETO de las instalaciones existentes (PDD-GOV0-01: capacidades
funcionales, no técnicas; ADMIN no las recibe). Sin relleno de datos de
negocio.

Revision ID: 0063_gov0_entes
Revises: 0062_spec001_roles_tenant
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa

from alembic import op

revision = "0063_gov0_entes"
down_revision = "0062_spec001_roles_tenant"
branch_labels = None
depends_on = None

PERMISOS = {"gobierno_ente": ("view", "create", "edit", "activate")}


def _en(*valores: str) -> str:
    return ", ".join(f"'{v}'" for v in valores)


def _tiempos() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]


def upgrade() -> None:
    op.create_table(
        "gov_entities",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("denominacion", sa.String(200), nullable=False),
        sa.Column("siglas", sa.String(20), nullable=True),
        sa.Column("rif", sa.String(12), nullable=True),
        sa.Column("nivel_territorial", sa.String(16), nullable=True),
        sa.Column("forma_organizativa", sa.String(32), nullable=True),
        sa.Column("organo_adscripcion", sa.String(200), nullable=True),
        sa.Column("entidad_federal", sa.String(120), nullable=True),
        sa.Column("municipio", sa.String(120), nullable=True),
        sa.Column("acto_tipo", sa.String(16), nullable=True),
        sa.Column("acto_numero", sa.String(60), nullable=True),
        sa.Column("acto_fecha", sa.Date(), nullable=True),
        sa.Column("acto_publicacion", sa.String(200), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="BORRADOR"),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_by", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        *_tiempos(),
        sa.UniqueConstraint("company_id", name="uq_gov_entities_company_id"),
        sa.CheckConstraint(
            f"status IN ({_en('BORRADOR', 'ACTIVO')})",
            name="status",
        ),
        sa.CheckConstraint(
            f"nivel_territorial IS NULL OR nivel_territorial IN ({_en('NACIONAL', 'ESTADAL', 'MUNICIPAL')})",
            name="nivel_territorial",
        ),
        sa.CheckConstraint(
            "forma_organizativa IS NULL OR forma_organizativa IN "
            f"({_en('ADMINISTRACION_CENTRAL', 'INSTITUTO_PUBLICO', 'SERVICIO_DESCONCENTRADO', 'ENTE_DESCENTRALIZADO')})",
            name="forma_organizativa",
        ),
        sa.CheckConstraint(
            f"acto_tipo IS NULL OR acto_tipo IN ({_en('LEY', 'DECRETO', 'ORDENANZA', 'RESOLUCION', 'OTRO')})",
            name="acto_tipo",
        ),
        sa.CheckConstraint("version >= 1", name="version"),
        sa.CheckConstraint("status <> 'ACTIVO' OR activated_at IS NOT NULL", name="activo_fechado"),
    )

    op.create_table(
        "gov_entity_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("entity_id", sa.String(36), sa.ForeignKey("gov_entities.id"), nullable=False),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("reason", sa.String(255), nullable=True),
        sa.Column("actor_id", sa.String(36), nullable=True),
        *_tiempos(),
        sa.UniqueConstraint("entity_id", "version", name="uq_gov_entity_versions_entity_id_version"),
        sa.CheckConstraint(f"status IN ({_en('BORRADOR', 'ACTIVO')})", name="status"),
        sa.CheckConstraint("version >= 1", name="version"),
    )
    op.create_index("ix_gov_entity_versions_entity_id", "gov_entity_versions", ["entity_id"])
    op.create_index("ix_gov_entity_versions_company_id", "gov_entity_versions", ["company_id"])

    _conceder_permisos(op.get_bind())


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


def downgrade() -> None:
    op.drop_index("ix_gov_entity_versions_company_id", table_name="gov_entity_versions")
    op.drop_index("ix_gov_entity_versions_entity_id", table_name="gov_entity_versions")
    op.drop_table("gov_entity_versions")
    op.drop_table("gov_entities")

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
