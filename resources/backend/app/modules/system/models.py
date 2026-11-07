"""Modelos del módulo de sistema.

Incluye SystemSetting, FeatureFlag, IdempotencyRecord y OutboxEvent.

`FileMetadata` evolucionó a `StoredFile` en el módulo `documents` (Spec 046).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.scope import Scope
from app.shared.mixins import CreatedByMixin, TimestampMixin, UUIDMixin


class SystemSetting(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "system_settings"
    __scope__ = Scope.INSTALLATION

    #: Un ajuste puede ser de la instalación entera (tenant nulo) o de un tenant
    #: concreto. Que pueda faltar no lo exime de referenciar a alguien real.
    tenant_id: Mapped[str | None] = mapped_column(
        ForeignKey("tenants.id"), nullable=True, index=True)
    key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    value: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    updated_by: Mapped[str | None] = mapped_column(String(36), nullable=True)


class FeatureFlag(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "feature_flags"
    __scope__ = Scope.INSTALLATION

    key: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
    audience: Mapped[str | None] = mapped_column(String(64), nullable=True)


class IdempotencyRecord(UUIDMixin, TimestampMixin, Base):
    """Registro de idempotencia de la **instalación**.

    Se declaraba `TENANT` y nunca hubo por dónde llegar a uno: la clave es única
    en toda la instalación y quien escribe la fila guarda usuario y empresa, no
    tenant. `company_id` anulable acota la respuesta cacheada cuando la petición
    se hizo dentro de una empresa.
    """

    __tablename__ = "idempotency_records"
    __scope__ = Scope.INSTALLATION

    key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    method: Mapped[str] = mapped_column(String(8), nullable=False)
    path: Mapped[str] = mapped_column(String(255), nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    response_status: Mapped[int] = mapped_column(nullable=False)
    response_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    response_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OutboxEvent(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "outbox_events"
    __scope__ = Scope.TENANT

    aggregate_type: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(36), nullable=False)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    tenant_id: Mapped[str | None] = mapped_column(ForeignKey("tenants.id"), nullable=True)
    company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempts: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


# `FileMetadata` evolucionó a `StoredFile` en el módulo `documents` (Spec 046).
# La tabla `file_metadata` pasó a llamarse `stored_files` en la migración 0023;
# el modelo vive ahora donde vive su comportamiento, no aquí.

ESTADOS_COPIA = ("RUNNING", "CREATED", "VERIFIED_LOCAL", "VERIFIED_DESTINATION", "VERIFIED_DURABLE", "FAILED", "ABANDONED", "PURGED")
ORIGENES_COPIA = ("MANUAL", "SCHEDULED")
ETAPAS_CREACION = ("PENDING", "STARTED", "COMPLETED", "FAILED")
ETAPAS_VERIFICACION = ("PENDING", "STARTED", "SUCCEEDED", "FAILED")
ETAPAS_TRANSFERENCIA = ("NOT_APPLICABLE", "PENDING", "COMPLETED", "FAILED")
ETAPAS_RETENCION = ("NOT_APPLICABLE", "PENDING", "COMPLETED", "DEGRADED")


def _en(valores: tuple[str, ...]) -> str:
    """Lista SQL de literales para una restricción de valores permitidos."""
    return ", ".join(f"'{v}'" for v in valores)


class BackupSettings(UUIDMixin, TimestampMixin, Base):
    """Política de copias de seguridad de la instalación.

    Hay a lo sumo una fila, forzada por `singleton`. Los campos de política
    son NULL hasta que alguien los configure explícitamente.
    """

    __tablename__ = "backup_settings"
    __scope__ = Scope.INSTALLATION
    __table_args__ = (
        UniqueConstraint("singleton", name="uq_backup_settings_singleton"),
        CheckConstraint("singleton = 'INSTALLATION'", name="singleton"),
        CheckConstraint("configured_rpo_minutes IS NULL OR configured_rpo_minutes BETWEEN 1 AND 15", name="rpo_max"),
        CheckConstraint("schedule_interval_minutes IS NULL OR schedule_interval_minutes >= 1", name="interval_min"),
        CheckConstraint("safety_margin_minutes IS NULL OR safety_margin_minutes >= 0", name="margin_min"),
        CheckConstraint("retention_days IS NULL OR retention_days >= 1", name="retention_days_min"),
        CheckConstraint("retention_min_copies IS NULL OR retention_min_copies >= 1", name="retention_copies_min"),
        CheckConstraint("destination_type IS NULL OR destination_type = 'MOUNTED_FILESYSTEM'", name="destination_type"),
    )

    singleton: Mapped[str] = mapped_column(String(16), nullable=False, default="INSTALLATION", server_default="INSTALLATION")
    configured_rpo_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    schedule_interval_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    safety_margin_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retention_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retention_min_copies: Mapped[int | None] = mapped_column(Integer, nullable=True)
    destination_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    destination_label: Mapped[str | None] = mapped_column(String(63), nullable=True)
    scheduler_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    last_rpo_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    updated_by: Mapped[str | None] = mapped_column(String(36), nullable=True)


class BackupRun(UUIDMixin, TimestampMixin, Base):
    """Ledger de copias de la instalación.

    Solo puede existir una copia `RUNNING` a la vez y `origin` distingue la
    vía manual de la programada.
    """

    __tablename__ = "backup_runs"
    __scope__ = Scope.INSTALLATION
    __table_args__ = (
        UniqueConstraint("slot", name="uq_backup_runs_slot"),
        UniqueConstraint("backup_id", name="uq_backup_runs_backup_id"),
        CheckConstraint(f"status IN ({_en(ESTADOS_COPIA)})", name="status"),
        CheckConstraint(f"origin IN ({_en(ORIGENES_COPIA)})", name="origin"),
        CheckConstraint(f"create_state IN ({_en(ETAPAS_CREACION)})", name="create_state"),
        CheckConstraint(f"verify_state IN ({_en(ETAPAS_VERIFICACION)})", name="verify_state"),
        CheckConstraint(f"transfer_state IN ({_en(ETAPAS_TRANSFERENCIA)})", name="transfer_state"),
        CheckConstraint(f"retention_state IN ({_en(ETAPAS_RETENCION)})", name="retention_state"),
        CheckConstraint("duration_seconds IS NULL OR duration_seconds >= 0", name="duration"),
        CheckConstraint("package_size IS NULL OR package_size >= 0", name="package_size"),
        Index("uq_backup_runs_one_running", "status", unique=True,
              postgresql_where=text("status = 'RUNNING'"), sqlite_where=text("status = 'RUNNING'")),
    )

    origin: Mapped[str] = mapped_column(String(16), nullable=False)
    slot: Mapped[str | None] = mapped_column(String(64), nullable=True)
    backup_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    create_state: Mapped[str] = mapped_column(String(16), nullable=False)
    verify_state: Mapped[str] = mapped_column(String(16), nullable=False)
    transfer_state: Mapped[str] = mapped_column(String(16), nullable=False)
    retention_state: Mapped[str] = mapped_column(String(16), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    snapshot_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    package_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    destination_label: Mapped[str | None] = mapped_column(String(63), nullable=True)
    durable_off_host: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    retention_hold: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
