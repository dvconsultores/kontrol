"""Autoridad Central · sync autenticado: huella única de la clave pública de la instalación y desafíos de un solo uso.

Las filas ya registradas se conservan: su huella se calcula desde el PEM guardado (no se genera ninguna
clave ni se enrola nada en silencio). Si dos filas previas compartieran clave, el índice único no se
crea y la migración se detiene: eso lo resuelve el vendor, no la migración.

Revision ID: 0002_cla_sync_auth
Revises: 0001_cla_fase1
Create Date: 2026-10-07
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op
from app.core.sync_auth_contract import public_key_fingerprint

revision = "0002_cla_sync_auth"
down_revision = "0001_cla_fase1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cla_installations", sa.Column("public_key_fingerprint", sa.String(64), nullable=True))
    conexion = op.get_bind()
    filas = conexion.execute(sa.text("select id, public_key_pem from cla_installations")).all()
    for id_, pem in filas:
        conexion.execute(sa.text("update cla_installations set public_key_fingerprint = :h where id = :i"),
                         {"h": public_key_fingerprint(pem), "i": id_})
    with op.batch_alter_table("cla_installations") as lote:
        lote.alter_column("public_key_fingerprint", existing_type=sa.String(64), nullable=False)
    op.create_index("uq_cla_installations_public_key_fingerprint", "cla_installations", ["public_key_fingerprint"], unique=True)

    op.create_table(
        "cla_sync_challenges",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("installation_id", sa.String(36), sa.ForeignKey("cla_installations.id"), nullable=True),
        sa.Column("nonce_sha256", sa.String(64), nullable=False),
        sa.Column("protocol_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_cla_sync_challenges_installation", "cla_sync_challenges", ["installation_id"])
    op.create_index("ix_cla_sync_challenges_expires_at", "cla_sync_challenges", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_cla_sync_challenges_expires_at", table_name="cla_sync_challenges")
    op.drop_index("ix_cla_sync_challenges_installation", table_name="cla_sync_challenges")
    op.drop_table("cla_sync_challenges")
    op.drop_index("uq_cla_installations_public_key_fingerprint", table_name="cla_installations")
    with op.batch_alter_table("cla_installations") as lote:
        lote.drop_column("public_key_fingerprint")
