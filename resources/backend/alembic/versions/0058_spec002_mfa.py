"""Spec 002 — MFA: factores, códigos de recuperación, desafíos y seguridad de sesión.

Aditiva: tres tablas nuevas para el modelo de datos de MFA y las columnas de
seguridad de sesión en `sessions`. `family_id` se rellena con `id` en las filas
existentes. Concede `users:mfa_reset` al rol ADMIN con el patrón idempotente.

En `sessions`, las columnas nuevas son las únicas tablas existentes que se
tocan. `auth_method` se añade NOT NULL con server_default 'PASSWORD'.

Revision ID: 0058_spec002_mfa
Revises: 0057_spec047_notifications
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa

from alembic import op

revision = "0058_spec002_mfa"
down_revision = "0057_spec047_notifications"
branch_labels = None
depends_on = None

PERMISOS = {"users": ("mfa_reset",)}


def _en(*valores: str) -> str:
    return ", ".join(f"'{v}'" for v in valores)


def _tiempos() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]


def upgrade() -> None:
    op.create_table(
        "mfa_factors",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="PENDING"),
        sa.Column("secret_ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("key_id", sa.String(32), nullable=True),
        sa.Column("digits", sa.Integer(), nullable=False, server_default="6"),
        sa.Column("period", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("algorithm", sa.String(8), nullable=False, server_default="SHA1"),
        sa.Column("last_used_step", sa.BigInteger(), nullable=True),
        sa.Column("failed_confirmations", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pending_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        *_tiempos(),
        sa.CheckConstraint("status IN ('PENDING','ACTIVE','REVOKED')", name="status"),
    )
    op.create_index("ix_mfa_factors_tenant_id", "mfa_factors", ["tenant_id"])
    op.create_index("ix_mfa_factors_user_id", "mfa_factors", ["user_id"])
    op.create_index(
        "uq_mfa_factor_active",
        "mfa_factors",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
        sqlite_where=sa.text("status = 'ACTIVE'"),
    )
    op.create_index(
        "uq_mfa_factor_pending",
        "mfa_factors",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'PENDING'"),
        sqlite_where=sa.text("status = 'PENDING'"),
    )

    op.create_table(
        "mfa_recovery_codes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("factor_id", sa.String(36), sa.ForeignKey("mfa_factors.id"), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        *_tiempos(),
        sa.UniqueConstraint("code_hash", name="uq_mfa_recovery_codes_code_hash"),
    )
    op.create_index("ix_mfa_recovery_codes_user_id", "mfa_recovery_codes", ["user_id"])
    op.create_index("ix_mfa_recovery_codes_factor_id", "mfa_recovery_codes", ["factor_id"])

    op.create_table(
        "mfa_challenges",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("purpose", sa.String(16), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ip", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(255), nullable=True),
        *_tiempos(),
        sa.CheckConstraint("purpose IN ('LOGIN','ENROLL')", name="purpose"),
        sa.UniqueConstraint("token_hash", name="uq_mfa_challenges_token_hash"),
    )
    op.create_index("ix_mfa_challenges_tenant_id", "mfa_challenges", ["tenant_id"])
    op.create_index("ix_mfa_challenges_user_id", "mfa_challenges", ["user_id"])

    op.add_column(
        "sessions",
        sa.Column("family_id", sa.String(36), nullable=True),
    )
    op.add_column(
        "sessions",
        sa.Column("auth_method", sa.String(24), nullable=False, server_default="PASSWORD"),
    )
    op.add_column(
        "sessions",
        sa.Column("mfa_verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "sessions",
        sa.Column("reauth_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.execute("UPDATE sessions SET family_id = id WHERE family_id IS NULL")

    with op.batch_alter_table("sessions") as batch_op:
        batch_op.alter_column("family_id", nullable=False)
        batch_op.create_index("ix_sessions_family_id", ["family_id"])
        batch_op.create_check_constraint(
            "auth_method",
            "auth_method IN ('PASSWORD','PASSWORD_TOTP','PASSWORD_RECOVERY')",
        )

    _conceder_permisos(op.get_bind())


def _conceder_permisos(bind) -> None:
    admin = bind.execute(sa.text(
        "SELECT id FROM roles WHERE code = 'ADMIN' AND company_id IS NULL LIMIT 1")).fetchone()
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
            if not admin:
                continue
            ya = bind.execute(sa.text(
                "SELECT 1 FROM role_permissions WHERE role_id = :rol AND permission_id = :p"),
                {"rol": admin[0], "p": permiso}).fetchone()
            if not ya:
                bind.execute(sa.text(
                    "INSERT INTO role_permissions (id, role_id, permission_id) VALUES (:id, :rol, :p)"),
                    {"id": str(uuid.uuid4()), "rol": admin[0], "p": permiso})


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text(
        "DELETE FROM role_permissions WHERE permission_id IN "
        "(SELECT id FROM permissions WHERE resource = 'users' AND action = 'mfa_reset')"))
    bind.execute(sa.text(
        "DELETE FROM permissions WHERE resource = 'users' AND action = 'mfa_reset'"))

    with op.batch_alter_table("sessions") as batch_op:
        batch_op.drop_constraint("auth_method", type_="check")
        batch_op.drop_index("ix_sessions_family_id")
        batch_op.drop_column("reauth_at")
        batch_op.drop_column("mfa_verified_at")
        batch_op.drop_column("auth_method")
        batch_op.drop_column("family_id")

    op.drop_table("mfa_challenges")
    op.drop_table("mfa_recovery_codes")
    op.drop_table("mfa_factors")
