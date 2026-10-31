"""gov0 estructuras

Crea `gov_structures`, `gov_units` y `gov_unit_versions` (ORG-02: estructura
organizativa por ejercicio, unidades con jerarquía dentro de la misma
estructura e historia de cambios) y concede `gobierno_estructura:*` al rol
protegido FUNCIONAL_COMPLETO de las instalaciones existentes. Sin relleno de
datos de negocio.

Revision ID: 0064_gov0_estructuras
Revises: 0063_gov0_entes
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa

from alembic import op

revision = "0064_gov0_estructuras"
down_revision = "0063_gov0_entes"
branch_labels = None
depends_on = None

PERMISOS = {"gobierno_estructura": ("view", "edit", "publish", "close")}


def _en(*valores: str) -> str:
    return ", ".join(f"'{v}'" for v in valores)


def _tiempos() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]


def upgrade() -> None:
    op.create_table(
        "gov_structures",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("entity_id", sa.String(36), sa.ForeignKey("gov_entities.id"), nullable=False),
        sa.Column("exercise", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="BORRADOR"),
        sa.Column("copied_from_exercise", sa.Integer(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_by", sa.String(36), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_by", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        *_tiempos(),
        sa.UniqueConstraint("company_id", "exercise", name="uq_gov_structures_company_id_exercise"),
        sa.CheckConstraint(f"status IN ({_en('BORRADOR', 'VIGENTE', 'CERRADA')})", name="status"),
        sa.CheckConstraint("exercise BETWEEN 2000 AND 2100", name="exercise"),
        sa.CheckConstraint("version >= 1", name="version"),
        sa.CheckConstraint("status = 'BORRADOR' OR published_at IS NOT NULL", name="publicada_fechada"),
        sa.CheckConstraint("status <> 'CERRADA' OR closed_at IS NOT NULL", name="cerrada_fechada"),
    )

    op.create_table(
        "gov_units",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("structure_id", sa.String(36), sa.ForeignKey("gov_structures.id"), nullable=False),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("code", sa.String(30), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("unit_type", sa.String(32), nullable=False),
        sa.Column("parent_id", sa.String(36), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="ACTIVA"),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        *_tiempos(),
        sa.UniqueConstraint("structure_id", "code", name="uq_gov_units_structure_id_code"),
        sa.UniqueConstraint("structure_id", "id", name="uq_gov_units_structure_id_id"),
        sa.ForeignKeyConstraint(
            ["structure_id", "parent_id"],
            ["gov_units.structure_id", "gov_units.id"],
            name="fk_gov_units_parent_misma_estructura",
        ),
        sa.CheckConstraint(
            f"unit_type IN ({_en('ORGANO', 'UNIDAD_ADMINISTRATIVA', 'UNIDAD_EJECUTORA_LOCAL', 'DEPENDENCIA', 'SEDE', 'CENTRO_GESTOR')})",
            name="unit_type",
        ),
        sa.CheckConstraint(f"status IN ({_en('ACTIVA', 'INACTIVA')})", name="status"),
        sa.CheckConstraint("parent_id IS NULL OR parent_id <> id", name="sin_autorreferencia"),
        sa.CheckConstraint("valid_to IS NULL OR valid_to >= valid_from", name="vigencia"),
        sa.CheckConstraint(
            "(status = 'ACTIVA' AND valid_to IS NULL) OR (status = 'INACTIVA' AND valid_to IS NOT NULL)",
            name="inactiva_fechada",
        ),
        sa.CheckConstraint("version >= 1", name="version"),
    )
    op.create_index("ix_gov_units_structure_id", "gov_units", ["structure_id"])
    op.create_index("ix_gov_units_company_id", "gov_units", ["company_id"])

    op.create_table(
        "gov_unit_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("unit_id", sa.String(36), sa.ForeignKey("gov_units.id"), nullable=False),
        sa.Column("structure_id", sa.String(36), sa.ForeignKey("gov_structures.id"), nullable=False),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("reason", sa.String(255), nullable=True),
        sa.Column("actor_id", sa.String(36), nullable=True),
        *_tiempos(),
        sa.UniqueConstraint("unit_id", "version", name="uq_gov_unit_versions_unit_id_version"),
        sa.CheckConstraint(f"status IN ({_en('ACTIVA', 'INACTIVA')})", name="status"),
        sa.CheckConstraint("version >= 1", name="version"),
    )
    op.create_index("ix_gov_unit_versions_unit_id", "gov_unit_versions", ["unit_id"])
    op.create_index("ix_gov_unit_versions_structure_id", "gov_unit_versions", ["structure_id"])
    op.create_index("ix_gov_unit_versions_company_id", "gov_unit_versions", ["company_id"])

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
    op.drop_index("ix_gov_unit_versions_company_id", table_name="gov_unit_versions")
    op.drop_index("ix_gov_unit_versions_structure_id", table_name="gov_unit_versions")
    op.drop_index("ix_gov_unit_versions_unit_id", table_name="gov_unit_versions")
    op.drop_index("ix_gov_units_company_id", table_name="gov_units")
    op.drop_index("ix_gov_units_structure_id", table_name="gov_units")
    op.drop_table("gov_unit_versions")
    op.drop_table("gov_units")
    op.drop_table("gov_structures")

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
