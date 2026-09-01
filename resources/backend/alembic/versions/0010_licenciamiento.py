"""Licenciamiento central (010).

Revision ID: 0010_licenciamiento
Revises: 0009_reportes
Create Date: 2026-08-04
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0010_licenciamiento"
down_revision = "0009_reportes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "license_central_config",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("installation_id", sa.String(length=64), nullable=False),
        sa.Column("server_url", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("public_key", sa.Text(), nullable=True),
        sa.Column("sync_policy", sa.JSON(), nullable=True),
        sa.Column("grace_days", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="DISCONNECTED"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_license_central_config_installation_id", "license_central_config", ["installation_id"], unique=True)

    op.create_table(
        "license_sync_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("installation_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="FAILED"),
        sa.Column("request", sa.JSON(), nullable=True),
        sa.Column("response", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=64), nullable=True),
        sa.Column("ran_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_license_sync_runs_installation_id", "license_sync_runs", ["installation_id"])
    op.create_index("ix_license_sync_runs_idempotency_key", "license_sync_runs", ["idempotency_key"])

    op.create_table(
        "license_entitlement_snapshots",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("installation_id", sa.String(length=64), nullable=False),
        sa.Column("modules", sa.JSON(), nullable=True),
        sa.Column("version", sa.String(length=32), nullable=False, server_default="v1"),
        sa.Column("taken_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_license_entitlement_snapshots_installation_id", "license_entitlement_snapshots", ["installation_id"])


def downgrade() -> None:
    op.drop_table("license_entitlement_snapshots")
    op.drop_table("license_sync_runs")
    op.drop_table("license_central_config")
