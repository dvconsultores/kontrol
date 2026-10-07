"""Modelo de datos de la Autoridad Central (PostgreSQL propio; tablas `cla_*`).

`Base` propia: nada de aquí comparte metadatos con el cliente. El libro (`cla_issuances`) y la
auditoría (`cla_audit_events`) son de solo anexar; el único dato mutable es `last_revision` del
linaje, que solo crece bajo el bloqueo de la fila de la instalación.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Installation(Base):
    """Registro de instalaciones: la identidad que el cliente genera y envía en su solicitud de activación."""

    __tablename__ = "cla_installations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    installation_uuid: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    public_key_pem: Mapped[str] = mapped_column(Text, nullable=False)
    customer_id: Mapped[str] = mapped_column(String(64), nullable=False)
    contract_id: Mapped[str] = mapped_column(String(64), nullable=False)
    company_tax_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    registered_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class PeriodLineage(Base):
    """Linaje de `revision` de una instalación en un período: la autoridad persistente del contador."""

    __tablename__ = "cla_period_lineages"
    __table_args__ = (
        UniqueConstraint("installation_id", "period_start", "period_end", name="uq_cla_lineage_installation_period"),
        Index("ix_cla_lineage_installation", "installation_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    installation_id: Mapped[str] = mapped_column(String(36), ForeignKey("cla_installations.id"), nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)


class Issuance(Base):
    """Libro de emisiones, de solo anexar: el artefacto exacto que se firmó y entregó."""

    __tablename__ = "cla_issuances"
    __table_args__ = (
        UniqueConstraint("lineage_id", "revision", name="uq_cla_issuance_lineage_revision"),
        Index("ix_cla_issuance_installation", "installation_id"),
        Index("ix_cla_issuance_lineage", "lineage_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    installation_id: Mapped[str] = mapped_column(String(36), ForeignKey("cla_installations.id"), nullable=False)
    lineage_id: Mapped[str] = mapped_column(String(36), ForeignKey("cla_period_lineages.id"), nullable=False)
    license_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    kid: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    signature_hex: Mapped[str] = mapped_column(Text, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    issued_by: Mapped[str] = mapped_column(String(128), nullable=False)


class AuditEvent(Base):
    """Auditoría de operaciones del propietario, de solo anexar; nunca lleva material de clave ni firmas."""

    __tablename__ = "cla_audit_events"
    __table_args__ = (Index("ix_cla_audit_installation", "installation_uuid"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    operation: Mapped[str] = mapped_column(String(64), nullable=False)
    operator: Mapped[str] = mapped_column(String(128), nullable=False)
    installation_uuid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    issuance_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    outcome: Mapped[str] = mapped_column(String(64), nullable=False)
    detail: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
