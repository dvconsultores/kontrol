"""Migración Spec 002: sello de credencial en usuarios, sesiones y desafíos MFA,
y estado del token de reset de contraseña.

El sello de credencial permite invalidar sesiones y desafíos emitidos antes de
un cambio de contraseña. En esta migración se introduce la columna, se rellena
de forma única para cada usuario y se propaga a las sesiones y desafíos MFA
existentes para que ninguno quede inválido. Además, el token de reset incorpora
la marca de invalidación y el origen del reinicio.

Revision ID: 0059_spec002_password_reset
Revises: 0058_spec002_mfa
"""
from __future__ import annotations

import secrets

import sqlalchemy as sa

from alembic import op

revision = "0059_spec002_password_reset"
down_revision = "0058_spec002_mfa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("credential_stamp", sa.String(length=32), nullable=True))

    filas = bind.execute(sa.text("SELECT id FROM users")).mappings()
    for fila in filas:
        bind.execute(
            sa.text("UPDATE users SET credential_stamp = :sello WHERE id = :id"),
            {"sello": secrets.token_hex(16), "id": fila["id"]},
        )

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("credential_stamp", nullable=False)

    with op.batch_alter_table("sessions") as batch_op:
        batch_op.add_column(sa.Column("credential_stamp", sa.String(length=32), nullable=True))

    bind.execute(
        sa.text(
            "UPDATE sessions SET credential_stamp = ("
            "SELECT u.credential_stamp FROM users u WHERE u.id = sessions.user_id"
            ")"
        )
    )

    with op.batch_alter_table("mfa_challenges") as batch_op:
        batch_op.add_column(sa.Column("credential_stamp", sa.String(length=32), nullable=True))

    bind.execute(
        sa.text(
            "UPDATE mfa_challenges SET credential_stamp = ("
            "SELECT u.credential_stamp FROM users u WHERE u.id = mfa_challenges.user_id"
            ")"
        )
    )

    with op.batch_alter_table("password_resets") as batch_op:
        batch_op.add_column(
            sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "source",
                sa.String(length=16),
                nullable=False,
                server_default="SELF",
            )
        )
        batch_op.drop_index("ix_password_resets_token_hash")
        batch_op.create_unique_constraint(
            "uq_password_resets_token_hash", ["token_hash"]
        )


def downgrade() -> None:
    with op.batch_alter_table("password_resets") as batch_op:
        batch_op.drop_constraint("uq_password_resets_token_hash", type_="unique")
        batch_op.create_index(
            "ix_password_resets_token_hash", ["token_hash"], unique=False
        )
        batch_op.drop_column("source")
        batch_op.drop_column("invalidated_at")

    with op.batch_alter_table("mfa_challenges") as batch_op:
        batch_op.drop_column("credential_stamp")

    with op.batch_alter_table("sessions") as batch_op:
        batch_op.drop_column("credential_stamp")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("credential_stamp")
