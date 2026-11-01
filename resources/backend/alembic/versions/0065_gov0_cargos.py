"""gov0 cargos

Crea `gov_positions`, `gov_position_competencies` y `gov_position_versions` (ORG-03: cargos por ejercicio con competencias y límites de firma/aprobación e historia de cambios) y concede `gobierno_cargos:*` al rol protegido FUNCIONAL_COMPLETO de las instalaciones existentes. Sin relleno de datos de negocio.

Revision ID: 0065_gov0_cargos
Revises: 0064_gov0_estructuras
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa

from alembic import op

revision = "0065_gov0_cargos"
down_revision = "0064_gov0_estructuras"
branch_labels = None
depends_on = None

PERMISOS = {"gobierno_cargos": ("view", "edit", "publish")}


def _en(*valores: str) -> str:
    return ", ".join(f"'{v}'" for v in valores)


def _tiempos() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]


def upgrade() -> None:
    op.create_table(
        "gov_positions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("structure_id", sa.String(36), sa.ForeignKey("gov_structures.id"), nullable=False),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("unit_id", sa.String(36), nullable=False),
        sa.Column("code", sa.String(30), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="BORRADOR"),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_by", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        *_tiempos(),
        sa.UniqueConstraint("structure_id", "code", name="uq_gov_positions_structure_id_code"),

        sa.ForeignKeyConstraint(
            ["structure_id", "unit_id"],
            ["gov_units.structure_id", "gov_units.id"],
            name="fk_gov_positions_unidad_misma_estructura",
        ),
        sa.CheckConstraint(f"status IN ({_en('BORRADOR', 'VIGENTE', 'INACTIVO')})", name="status"),
        sa.CheckConstraint("valid_to IS NULL OR valid_to >= valid_from", name="vigencia"),
        sa.CheckConstraint(
            "(status = 'INACTIVO' AND valid_to IS NOT NULL) OR (status <> 'INACTIVO' AND valid_to IS NULL)",
            name="inactivo_fechado",
        ),
        sa.CheckConstraint("status = 'BORRADOR' OR activated_at IS NOT NULL", name="activado_fechado"),
        sa.CheckConstraint("version >= 1", name="version"),
    )
    op.create_index("ix_gov_positions_structure_id", "gov_positions", ["structure_id"])
    op.create_index("ix_gov_positions_company_id", "gov_positions", ["company_id"])
    op.create_index("ix_gov_positions_unit_id", "gov_positions", ["unit_id"])

    op.create_table(
        "gov_position_competencies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("position_id", sa.String(36), sa.ForeignKey("gov_positions.id"), nullable=False),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("subject", sa.String(16), nullable=False),
        sa.Column("limit_type", sa.String(16), nullable=False),
        sa.Column("limit_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("limit_currency", sa.String(3), nullable=True),
        sa.Column("basis", sa.String(255), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        *_tiempos(),
        sa.UniqueConstraint("position_id", "action", "subject", name="uq_gov_position_competencies_position_id_action_subject"),

        sa.CheckConstraint(
            f"action IN ({_en('SOLICITAR', 'COMPROMETER', 'CAUSAR', 'ORDENAR_PAGO', 'PAGAR', 'REGISTRAR', 'CUSTODIAR', 'APROBAR', 'AUDITAR', 'FIRMAR')})",
            name="action",
        ),
        sa.CheckConstraint(
            f"subject IN ({_en('PRESUPUESTO', 'CONTRATACIONES', 'TESORERIA', 'CONTABILIDAD', 'BIENES', 'EXPEDIENTE')})",
            name="subject",
        ),
        sa.CheckConstraint(f"limit_type IN ({_en('SIN_LIMITE', 'MONTO')})", name="limit_type"),
        sa.CheckConstraint(f"limit_currency IS NULL OR limit_currency IN ({_en('VES', 'USD', 'EUR')})", name="limit_currency"),
        sa.CheckConstraint(
            "(limit_type = 'SIN_LIMITE' AND limit_amount IS NULL AND limit_currency IS NULL) OR (limit_type = 'MONTO' AND limit_amount IS NOT NULL AND limit_amount > 0 AND limit_currency IS NOT NULL)",
            name="limite_coherente",
        ),
    )
    op.create_index("ix_gov_position_competencies_position_id", "gov_position_competencies", ["position_id"])
    op.create_index("ix_gov_position_competencies_company_id", "gov_position_competencies", ["company_id"])

    op.create_table(
        "gov_position_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("position_id", sa.String(36), sa.ForeignKey("gov_positions.id"), nullable=False),
        sa.Column("structure_id", sa.String(36), sa.ForeignKey("gov_structures.id"), nullable=False),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("reason", sa.String(255), nullable=True),
        sa.Column("actor_id", sa.String(36), nullable=True),
        *_tiempos(),
        sa.UniqueConstraint("position_id", "version", name="uq_gov_position_versions_position_id_version"),
        sa.CheckConstraint(f"status IN ({_en('BORRADOR', 'VIGENTE', 'INACTIVO')})", name="status"),
        sa.CheckConstraint("version >= 1", name="version"),
    )
    op.create_index("ix_gov_position_versions_position_id", "gov_position_versions", ["position_id"])
    op.create_index("ix_gov_position_versions_structure_id", "gov_position_versions", ["structure_id"])
    op.create_index("ix_gov_position_versions_company_id", "gov_position_versions", ["company_id"])

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
    op.drop_index("ix_gov_position_versions_company_id", table_name="gov_position_versions")
    op.drop_index("ix_gov_position_versions_structure_id", table_name="gov_position_versions")
    op.drop_index("ix_gov_position_versions_position_id", table_name="gov_position_versions")
    op.drop_index("ix_gov_position_competencies_company_id", table_name="gov_position_competencies")
    op.drop_index("ix_gov_position_competencies_position_id", table_name="gov_position_competencies")
    op.drop_index("ix_gov_positions_unit_id", table_name="gov_positions")
    op.drop_index("ix_gov_positions_company_id", table_name="gov_positions")
    op.drop_index("ix_gov_positions_structure_id", table_name="gov_positions")
    op.drop_table("gov_position_versions")
    op.drop_table("gov_position_competencies")
    op.drop_table("gov_positions")

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
