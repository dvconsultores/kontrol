"""Módulo fiscal (PREPARACIÓN - sin emisión en 001, Constitución P4).

Estructura versionada del núcleo fiscal: LegalSource, TaxRuleVersion,
FiscalNumberSeries y ControlNumberBatch (data-model.md §2.6).
La emisión real y la homologación corresponden a Specs posteriores.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.mixins import CreatedByMixin, TimestampMixin, UUIDMixin, VersionMixin


class LegalSource(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Norma con fuente: ley, decreto, providencia, resolución, Gaceta."""

    __tablename__ = "legal_sources"

    authority: Mapped[str] = mapped_column(String(64), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    gazette: Mapped[str | None] = mapped_column(String(64), nullable=True)
    publication_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    file_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="LEGAL_VALIDATION_REQUIRED")


class TaxRuleVersion(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    """Regla tributaria versionada con fuente y vigencia (FR-001-091)."""

    __tablename__ = "tax_rule_versions"

    tax_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    legal_source_id: Mapped[str | None] = mapped_column(ForeignKey("legal_sources.id"), nullable=True)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rate: Mapped[Any | None] = mapped_column(JSON, nullable=True)  # fórmula/porcentaje estructurado
    conditions: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)
    approval: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)
    fiscal_release: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")


class FiscalNumberSeries(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Serie de numeración fiscal con asignación atómica (preparación)."""

    __tablename__ = "fiscal_number_series"

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    establishment_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    document_type: Mapped[str] = mapped_column(String(32), nullable=False)
    prefix: Mapped[str | None] = mapped_column(String(16), nullable=True)
    next_number: Mapped[int] = mapped_column(BigInteger, default=1, nullable=False)
    lock_version: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    validity: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)


class ControlNumberBatch(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Lote de números de control de imprenta autorizada (preparación)."""

    __tablename__ = "control_number_batches"

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    establishment_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    printer: Mapped[str | None] = mapped_column(String(120), nullable=True)
    range_from: Mapped[str] = mapped_column(String(32), nullable=False)
    range_to: Mapped[str] = mapped_column(String(32), nullable=False)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="AVAILABLE")
    counts: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)
