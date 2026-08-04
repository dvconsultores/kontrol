"""Reportes y auditoría (009).

Revision ID: 0009_reportes
Revises: 0008_regulacion
Create Date: 2026-08-04
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0009_reportes"
down_revision = "0008_regulacion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "report_definitions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("report_key", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("enabled", sa.String(length=8), nullable=False, server_default="true"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_report_definitions_company_id", "report_definitions", ["company_id"])

    op.create_table(
        "report_exports",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("report_key", sa.String(length=64), nullable=False),
        sa.Column("format", sa.String(length=8), nullable=False, server_default="CSV"),
        sa.Column("filters", sa.Text(), nullable=True),
        sa.Column("file_ref", sa.String(length=255), nullable=True),
        sa.Column("exported_by", sa.String(length=36), nullable=True),
        sa.Column("exported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="DONE"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_report_exports_company_id", "report_exports", ["company_id"])
    op.create_index("ix_report_exports_report_key", "report_exports", ["report_key"])

    op.create_table(
        "report_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("report_key", sa.String(length=64), nullable=False),
        sa.Column("params", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="PENDING"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("result_ref", sa.String(length=255), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_report_jobs_company_id", "report_jobs", ["company_id"])


def downgrade() -> None:
    op.drop_table("report_jobs")
    op.drop_table("report_exports")
    op.drop_table("report_definitions")
