"""gov doc04 notificaciones

Crea `gov_notifications`, `gov_notification_attempts` y `gov_notification_versions` (DOC-04: notificaciones administrativas con tipos de persona, estados, medios e intentos, e historia de cambios) y concede `gobierno_notificaciones:*` al rol protegido FUNCIONAL_COMPLETO de las instalaciones existentes. Sin relleno de datos de negocio.

Revision ID: 0067_gov_doc04_notificaciones
Revises: 0066_gov_doc02_actos
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa

from alembic import op

revision = "0067_gov_doc04_notificaciones"
down_revision = "0066_gov_doc02_actos"
branch_labels = None
depends_on = None

PERMISOS = {"gobierno_notificaciones": ("view", "edit", "record")}


def _en(*valores: str) -> str:
    return ", ".join(f"'{v}'" for v in valores)


def _tiempos() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]


def upgrade() -> None:
    bind = op.get_bind()

    op.create_table(
        "gov_notifications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("act_id", sa.String(36), sa.ForeignKey("gov_acts.id"), nullable=False),
        sa.Column("tipo_persona", sa.String(8), nullable=False),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("identificacion", sa.String(20), nullable=False),
        sa.Column("identificacion_clave", sa.String(20), nullable=False),
        sa.Column("domicilio", sa.String(500), nullable=False),
        sa.Column("apoderado_nombre", sa.String(200), nullable=True),
        sa.Column("apoderado_identificacion", sa.String(20), nullable=True),
        sa.Column("recursos", sa.Text(), nullable=False),
        sa.Column("documento_oficio_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="PENDIENTE"),
        sa.Column("fecha_notificacion", sa.Date(), nullable=True),
        sa.Column("medio_notificacion", sa.String(8), nullable=True),
        sa.Column("motivo_anulacion", sa.String(255), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        *_tiempos(),
        sa.CheckConstraint(f"tipo_persona IN ({_en('NATURAL', 'JURIDICA')})", name="tipo_persona"),
        sa.CheckConstraint(f"status IN ({_en('PENDIENTE', 'NOTIFICADA', 'ANULADA')})", name="status"),
        sa.CheckConstraint(
            f"medio_notificacion IS NULL OR medio_notificacion IN ({_en('PERSONAL', 'PRENSA')})",
            name="medio",
        ),
        sa.CheckConstraint(
            "(status = 'NOTIFICADA') = (fecha_notificacion IS NOT NULL AND medio_notificacion IS NOT NULL)",
            name="notificada_fechada",
        ),
        sa.CheckConstraint("(status = 'ANULADA') = (motivo_anulacion IS NOT NULL)", name="anulada_motivada"),
        sa.CheckConstraint(
            "(apoderado_nombre IS NULL) = (apoderado_identificacion IS NULL)",
            name="apoderado_completo",
        ),
        sa.CheckConstraint("version >= 1", name="version"),
    )
    op.create_index("ix_gov_notifications_company_id", "gov_notifications", ["company_id"])
    op.create_index("ix_gov_notifications_act_id", "gov_notifications", ["act_id"])
    op.create_index("ix_gov_notifications_company_status", "gov_notifications", ["company_id", "status"])
    if bind.dialect.name == "postgresql":
        op.create_index(
            "uq_gov_notifications_act_destinatario",
            "gov_notifications",
            ["act_id", "identificacion_clave"],
            unique=True,
            postgresql_where=sa.text("status <> 'ANULADA'"),
        )

    op.create_table(
        "gov_notification_attempts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("notification_id", sa.String(36), sa.ForeignKey("gov_notifications.id"), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("medio", sa.String(8), nullable=False),
        sa.Column("resultado", sa.String(10), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("receptor_nombre", sa.String(200), nullable=True),
        sa.Column("receptor_identificacion", sa.String(20), nullable=True),
        sa.Column("motivo_fallo", sa.String(500), nullable=True),
        sa.Column("diario", sa.String(120), nullable=True),
        sa.Column("referencia", sa.String(120), nullable=True),
        sa.Column("documento_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("registrado_por", sa.String(36), nullable=True),
        *_tiempos(),
        sa.UniqueConstraint("notification_id", "numero", name="uq_gov_notification_attempts_numero"),
        sa.CheckConstraint(f"medio IN ({_en('PERSONAL', 'PRENSA')})", name="medio"),
        sa.CheckConstraint(f"resultado IN ({_en('ENTREGADA', 'FALLIDA', 'PUBLICADA')})", name="resultado"),
        sa.CheckConstraint("numero >= 1", name="numero"),
        sa.CheckConstraint(
            "(medio = 'PERSONAL' AND resultado IN ('ENTREGADA', 'FALLIDA')) OR (medio = 'PRENSA' AND resultado = 'PUBLICADA')",
            name="medio_resultado",
        ),
        sa.CheckConstraint(
            "(resultado = 'ENTREGADA') = (receptor_nombre IS NOT NULL AND receptor_identificacion IS NOT NULL)",
            name="entregada_receptor",
        ),
        sa.CheckConstraint("(resultado = 'FALLIDA') = (motivo_fallo IS NOT NULL)", name="fallida_motivo"),
        sa.CheckConstraint(
            "(resultado = 'PUBLICADA') = (diario IS NOT NULL AND referencia IS NOT NULL)",
            name="publicada_diario",
        ),
    )
    op.create_index("ix_gov_notification_attempts_company_id", "gov_notification_attempts", ["company_id"])
    op.create_index("ix_gov_notification_attempts_notification_id", "gov_notification_attempts", ["notification_id"])

    op.create_table(
        "gov_notification_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("notification_id", sa.String(36), sa.ForeignKey("gov_notifications.id"), nullable=False),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("reason", sa.String(255), nullable=True),
        sa.Column("actor_id", sa.String(36), nullable=True),
        *_tiempos(),
        sa.UniqueConstraint("notification_id", "version", name="uq_gov_notification_versions_notification_id_version"),
        sa.CheckConstraint(f"status IN ({_en('PENDIENTE', 'NOTIFICADA', 'ANULADA')})", name="status"),
        sa.CheckConstraint("version >= 1", name="version"),
    )
    op.create_index("ix_gov_notification_versions_notification_id", "gov_notification_versions", ["notification_id"])
    op.create_index("ix_gov_notification_versions_company_id", "gov_notification_versions", ["company_id"])

    _conceder_permisos(bind)


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

    op.drop_index("ix_gov_notification_versions_company_id", table_name="gov_notification_versions")
    op.drop_index("ix_gov_notification_versions_notification_id", table_name="gov_notification_versions")
    op.drop_table("gov_notification_versions")

    op.drop_index("ix_gov_notification_attempts_notification_id", table_name="gov_notification_attempts")
    op.drop_index("ix_gov_notification_attempts_company_id", table_name="gov_notification_attempts")
    op.drop_table("gov_notification_attempts")

    if bind.dialect.name == "postgresql":
        op.drop_index("uq_gov_notifications_act_destinatario", table_name="gov_notifications")
    op.drop_index("ix_gov_notifications_company_status", table_name="gov_notifications")
    op.drop_index("ix_gov_notifications_act_id", table_name="gov_notifications")
    op.drop_index("ix_gov_notifications_company_id", table_name="gov_notifications")
    op.drop_table("gov_notifications")
