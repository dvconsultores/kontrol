"""Modelos del módulo de sistema.

Incluye SystemSetting, FeatureFlag, IdempotencyRecord y OutboxEvent.

`FileMetadata` evolucionó a `StoredFile` en el módulo `documents` (Spec 046).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, String, Text
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
