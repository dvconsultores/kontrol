"""Autoridad Central · Fase 1: registro de instalaciones, linajes de revisión, libro de emisiones y auditoría.

Revision ID: 0001_cla_fase1
Revises:
Create Date: 2026-10-06
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0001_cla_fase1"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cla_installations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("installation_uuid", sa.String(64), nullable=False),
        sa.Column("public_key_pem", sa.Text(), nullable=False),
        sa.Column("customer_id", sa.String(64), nullable=False),
        sa.Column("contract_id", sa.String(64), nullable=False),
        sa.Column("company_tax_id", sa.String(32), nullable=True),
        sa.Column("registered_by", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_cla_installations_installation_uuid", "cla_installations", ["installation_uuid"], unique=True)

    op.create_table(
        "cla_period_lineages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("installation_id", sa.String(36), sa.ForeignKey("cla_installations.id"), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_revision", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("installation_id", "period_start", "period_end", name="uq_cla_lineage_installation_period"),
    )
    op.create_index("ix_cla_lineage_installation", "cla_period_lineages", ["installation_id"])

    op.create_table(
        "cla_issuances",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("installation_id", sa.String(36), sa.ForeignKey("cla_installations.id"), nullable=False),
        sa.Column("lineage_id", sa.String(36), sa.ForeignKey("cla_period_lineages.id"), nullable=False),
        sa.Column("license_id", sa.String(64), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("kid", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("signature_hex", sa.Text(), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("issued_by", sa.String(128), nullable=False),
        sa.UniqueConstraint("lineage_id", "revision", name="uq_cla_issuance_lineage_revision"),
        sa.UniqueConstraint("license_id", name="uq_cla_issuances_license_id"),
    )
    op.create_index("ix_cla_issuance_installation", "cla_issuances", ["installation_id"])
    op.create_index("ix_cla_issuance_lineage", "cla_issuances", ["lineage_id"])

    op.create_table(
        "cla_audit_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("operation", sa.String(64), nullable=False),
        sa.Column("operator", sa.String(128), nullable=False),
        sa.Column("installation_uuid", sa.String(64), nullable=True),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=True),
        sa.Column("issuance_id", sa.String(36), nullable=True),
        sa.Column("outcome", sa.String(64), nullable=False),
        sa.Column("detail", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_cla_audit_installation", "cla_audit_events", ["installation_uuid"])


def downgrade() -> None:
    op.drop_index("ix_cla_audit_installation", table_name="cla_audit_events")
    op.drop_table("cla_audit_events")
    op.drop_index("ix_cla_issuance_lineage", table_name="cla_issuances")
    op.drop_index("ix_cla_issuance_installation", table_name="cla_issuances")
    op.drop_table("cla_issuances")
    op.drop_index("ix_cla_lineage_installation", table_name="cla_period_lineages")
    op.drop_table("cla_period_lineages")
    op.drop_index("ix_cla_installations_installation_uuid", table_name="cla_installations")
    op.drop_table("cla_installations")
