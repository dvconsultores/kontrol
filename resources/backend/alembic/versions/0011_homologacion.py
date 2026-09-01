"""Homologación y liberación (011).

Revision ID: 0011_homologacion
Revises: 0010_licenciamiento
Create Date: 2026-08-04
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0011_homologacion"
down_revision = "0010_licenciamiento"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "homologation_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("installation_id", sa.String(length=64), nullable=False),
        sa.Column("fiscal_version", sa.String(length=32), nullable=False),
        sa.Column("modality", sa.String(length=32), nullable=False, server_default="E_FACTURA"),
        sa.Column("formal_act_ref", sa.String(length=255), nullable=True),
        sa.Column("evidence_sha256", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="DRAFT"),
        sa.Column("evaluated_by", sa.String(length=36), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_homologation_records_installation_id", "homologation_records", ["installation_id"])

    op.create_table(
        "homologation_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("installation_id", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="HOMOLOGATION"),
        sa.Column("homologation_id", sa.String(length=36), nullable=True),
        sa.Column("entity_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("detail", sa.JSON(), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_homologation_events_installation_id", "homologation_events", ["installation_id"])
    op.create_index("ix_homologation_events_homologation_id", "homologation_events", ["homologation_id"])
    op.create_index("ix_homologation_events_entity_id", "homologation_events", ["entity_id"])

    op.create_table(
        "release_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("installation_id", sa.String(length=64), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("changelog", sa.JSON(), nullable=True),
        sa.Column("gates", sa.JSON(), nullable=True),
        sa.Column("homologation_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="DRAFT"),
        sa.Column("blocked_reasons", sa.JSON(), nullable=True),
        sa.Column("released_by", sa.String(length=36), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_release_versions_installation_id", "release_versions", ["installation_id"])
    op.create_index(
        "uq_release_versions_inst_version",
        "release_versions",
        ["installation_id", "version"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("release_versions")
    op.drop_table("homologation_events")
    op.drop_table("homologation_records")
