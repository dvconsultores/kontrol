"""Módulo de licenciamiento local: LicenseState, LicenseArtifact,
LicenseEvent y LicenseRenewalRequest (data-model.md §2.3)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.mixins import TimestampMixin, UUIDMixin


class LicenseState(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "license_states"

    installation_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    license_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    mode: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    critical_warning_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    read_only_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    entitlements: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    minimum_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    kid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_reliable_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LicenseArtifact(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "license_artifacts"

    license_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    signature_hex: Mapped[str] = mapped_column(Text, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    kid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    replaced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LicenseEvent(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "license_events"

    installation_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    detail: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="LOCAL")


class LicenseRenewalRequest(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "license_renewal_requests"

    installation_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payment_proof_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="REPORTED")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)


class LicenseCentralConfig(UUIDMixin, TimestampMixin, Base):
    """Configuración del licenciamiento central (010, FR-010-001).

    Guarda el endpoint del servidor central, la clave pública, la política de
    sincronización y la gracia offline. Se persiste una única fila por
    instalación.
    """

    __tablename__ = "license_central_config"

    installation_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    server_url: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    public_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    sync_policy: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    grace_days: Mapped[int] = mapped_column(nullable=False, default=7)
    enabled: Mapped[bool] = mapped_column(nullable=False, default=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DISCONNECTED")


class LicenseSyncRun(UUIDMixin, TimestampMixin, Base):
    """Ejecución de sincronización contra el servidor central (FR-010-002/004).

    Cada intento (éxito o error) queda registrado con su request/response y
    una clave de idempotencia por día para evitar duplicados.
    """

    __tablename__ = "license_sync_runs"

    installation_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="FAILED")
    request: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)
    response: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    ran_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LicenseEntitlementSnapshot(UUIDMixin, TimestampMixin, Base):
    """Snapshot de la matriz de entitlements por módulo (FR-010-010/012).

    La matriz sincronizada (002-009) se versiona en cada sincronización.
    """

    __tablename__ = "license_entitlement_snapshots"

    installation_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    modules: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")
    taken_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
