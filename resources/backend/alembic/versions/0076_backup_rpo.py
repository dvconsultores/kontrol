"""Backup: política de RPO y ledger de copias de la instalación."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0076_backup_rpo"
down_revision = "0075_gov_ctl10_cierres"
branch_labels = None
depends_on = None


def _en(valores: tuple[str, ...]) -> str:
    """Lista SQL de literales para una restricción de valores permitidos."""
    return ", ".join(f"'{v}'" for v in valores)


def upgrade() -> None:
    op.create_table(
        "backup_settings",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("singleton", sa.String(16), nullable=False, server_default="INSTALLATION"),
        sa.Column("configured_rpo_minutes", sa.Integer(), nullable=True),
        sa.Column("schedule_interval_minutes", sa.Integer(), nullable=True),
        sa.Column("safety_margin_minutes", sa.Integer(), nullable=True),
        sa.Column("retention_days", sa.Integer(), nullable=True),
        sa.Column("retention_min_copies", sa.Integer(), nullable=True),
        sa.Column("destination_type", sa.String(32), nullable=True),
        sa.Column("destination_label", sa.String(63), nullable=True),
        sa.Column("scheduler_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("last_rpo_state", sa.String(32), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("singleton", name="uq_backup_settings_singleton"),
        sa.CheckConstraint("singleton = 'INSTALLATION'", name="singleton"),
        sa.CheckConstraint("configured_rpo_minutes IS NULL OR configured_rpo_minutes BETWEEN 1 AND 15", name="rpo_max"),
        sa.CheckConstraint("schedule_interval_minutes IS NULL OR schedule_interval_minutes >= 1", name="interval_min"),
        sa.CheckConstraint("safety_margin_minutes IS NULL OR safety_margin_minutes >= 0", name="margin_min"),
        sa.CheckConstraint("retention_days IS NULL OR retention_days >= 1", name="retention_days_min"),
        sa.CheckConstraint("retention_min_copies IS NULL OR retention_min_copies >= 1", name="retention_copies_min"),
        sa.CheckConstraint("destination_type IS NULL OR destination_type = 'MOUNTED_FILESYSTEM'", name="destination_type"),
    )

    op.create_table(
        "backup_runs",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("origin", sa.String(16), nullable=False),
        sa.Column("slot", sa.String(64), nullable=True),
        sa.Column("backup_id", sa.String(64), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("create_state", sa.String(16), nullable=False),
        sa.Column("verify_state", sa.String(16), nullable=False),
        sa.Column("transfer_state", sa.String(16), nullable=False),
        sa.Column("retention_state", sa.String(16), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("package_size", sa.BigInteger(), nullable=True),
        sa.Column("sha256", sa.String(64), nullable=True),
        sa.Column("destination_label", sa.String(63), nullable=True),
        sa.Column("durable_off_host", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("retention_hold", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("correlation_id", sa.String(36), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slot", name="uq_backup_runs_slot"),
        sa.UniqueConstraint("backup_id", name="uq_backup_runs_backup_id"),
        sa.CheckConstraint("status IN ('RUNNING', 'CREATED', 'VERIFIED_LOCAL', 'VERIFIED_DESTINATION', 'VERIFIED_DURABLE', 'FAILED', 'ABANDONED', 'PURGED')", name="status"),
        sa.CheckConstraint("origin IN ('MANUAL', 'SCHEDULED')", name="origin"),
        sa.CheckConstraint("create_state IN ('PENDING', 'STARTED', 'COMPLETED', 'FAILED')", name="create_state"),
        sa.CheckConstraint("verify_state IN ('PENDING', 'STARTED', 'SUCCEEDED', 'FAILED')", name="verify_state"),
        sa.CheckConstraint("transfer_state IN ('NOT_APPLICABLE', 'PENDING', 'COMPLETED', 'FAILED')", name="transfer_state"),
        sa.CheckConstraint("retention_state IN ('NOT_APPLICABLE', 'PENDING', 'COMPLETED', 'DEGRADED')", name="retention_state"),
        sa.CheckConstraint("duration_seconds IS NULL OR duration_seconds >= 0", name="duration"),
        sa.CheckConstraint("package_size IS NULL OR package_size >= 0", name="package_size"),
    )

    op.create_index("ix_backup_runs_status", "backup_runs", ["status"])
    op.create_index(
        "uq_backup_runs_one_running",
        "backup_runs",
        ["status"],
        unique=True,
        postgresql_where=sa.text("status = 'RUNNING'"),
        sqlite_where=sa.text("status = 'RUNNING'"),
    )


def downgrade() -> None:
    op.drop_index("uq_backup_runs_one_running", table_name="backup_runs")
    op.drop_index("ix_backup_runs_status", table_name="backup_runs")
    op.drop_table("backup_runs")
    op.drop_table("backup_settings")
