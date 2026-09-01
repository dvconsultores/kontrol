"""Módulo fiscal (PREPARACIÓN - sin emisión en 001, Constitución P4).

Estructura versionada del núcleo fiscal: LegalSource, TaxRuleVersion,
FiscalNumberSeries y ControlNumberBatch (data-model.md §2.6).
La emisión real y la homologación corresponden a Specs posteriores.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.scope import Scope
from app.shared.mixins import CreatedByMixin, TimestampMixin, UUIDMixin, VersionMixin


class LegalSource(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Norma con fuente: ley, decreto, providencia, resolución, Gaceta."""

    __tablename__ = "legal_sources"
    __scope__ = Scope.INSTALLATION

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
    __scope__ = Scope.GLOBAL

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
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    establishment_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    document_type: Mapped[str] = mapped_column(String(32), nullable=False)
    prefix: Mapped[str | None] = mapped_column(String(16), nullable=True)
    next_number: Mapped[int] = mapped_column(BigInteger, default=1, nullable=False)
    lock_version: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    validity: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)


class ControlNumberBatch(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Lote de números de control de imprenta autorizada (preparación)."""

    __tablename__ = "control_number_batches"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    establishment_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    printer: Mapped[str | None] = mapped_column(String(120), nullable=True)
    range_from: Mapped[str] = mapped_column(String(32), nullable=False)
    range_to: Mapped[str] = mapped_column(String(32), nullable=False)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="AVAILABLE")
    counts: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)


# --------------------------------------------------------------------------- #
# Números de control individuales (007)
# --------------------------------------------------------------------------- #
class ControlNumber(UUIDMixin, TimestampMixin, Base):
    """Número de control individual de un lote (DOC-03 §7/§12)."""

    __tablename__ = "control_numbers"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    batch_id: Mapped[str] = mapped_column(ForeignKey("control_number_batches.id"), nullable=False, index=True)
    value: Mapped[str] = mapped_column(String(32), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="AVAILABLE")
    # AVAILABLE / RESERVED / USED / VOID / LOST / DAMAGED
    document_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# --------------------------------------------------------------------------- #
# Cálculo fiscal y perfiles (007, DOC-03 §10)
# --------------------------------------------------------------------------- #
class TaxCalculation(UUIDMixin, TimestampMixin, Base):
    """Cálculo fiscal por documento/línea con snapshot (FR-007-004)."""

    __tablename__ = "tax_calculations"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    document_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    line_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    rule_version_id: Mapped[str | None] = mapped_column(ForeignKey("tax_rule_versions.id"), nullable=True)
    base: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0.0)
    rate: Mapped[float] = mapped_column(Numeric(14, 6), nullable=False, default=0.0)
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0.0)
    rounding: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=2.0)
    snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)


class TaxProfile(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Perfil fiscal por empresa/tercero/rubro (FR-007-003)."""

    __tablename__ = "tax_profiles"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    scope: Mapped[str] = mapped_column(String(16), nullable=False)  # COMPANY / PARTY / ITEM
    party_id: Mapped[str | None] = mapped_column(ForeignKey("parties.id"), nullable=True)
    item_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    classifications: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)
    validity_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    validity_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


# --------------------------------------------------------------------------- #
# Emisión, impresión y notas (007, DOC-03 §7)
# --------------------------------------------------------------------------- #
class FiscalDocument(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Documento fiscal emitido: envuelve un documento de 004/005 (FR-007-021)."""

    __tablename__ = "fiscal_documents"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    business_document: Mapped[str] = mapped_column(String(200), nullable=False, index=True)  # INVOICE:{id}
    document_type: Mapped[str] = mapped_column(String(32), nullable=False)  # INVOICE / CREDIT_NOTE / DEBIT_NOTE
    fiscal_mode: Mapped[str] = mapped_column(String(24), nullable=False, default="DIGITAL")
    series: Mapped[str | None] = mapped_column(String(16), nullable=True)
    invoice_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    control_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fiscal_currency: Mapped[str] = mapped_column(String(8), nullable=False, default="VED")
    exchange_rate_snapshot: Mapped[float | None] = mapped_column(Numeric(14, 6), nullable=True)
    emitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="EMITTED")


class PrintEvent(UUIDMixin, TimestampMixin, Base):
    """Impresión/reimpresión de un documento fiscal (FR-007-022)."""

    __tablename__ = "print_events"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    fiscal_document_id: Mapped[str] = mapped_column(ForeignKey("fiscal_documents.id"), nullable=False, index=True)
    copy_type: Mapped[str] = mapped_column(String(16), nullable=False, default="ORIGINAL")
    printer: Mapped[str | None] = mapped_column(String(120), nullable=True)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    printed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hash: Mapped[str | None] = mapped_column(String(64), nullable=True)


class CreditDebitNote(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Nota de crédito/débito con referencia y límites al saldo ajustable (FR-007-030)."""

    __tablename__ = "credit_debit_notes"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    fiscal_document_id: Mapped[str | None] = mapped_column(ForeignKey("fiscal_documents.id"), nullable=True)
    original_document: Mapped[str] = mapped_column(String(200), nullable=False)  # INVOICE:{id}
    note_type: Mapped[str] = mapped_column(String(16), nullable=False)  # CREDIT / DEBIT
    cause: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    base_amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0.0)
    tax_amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0.0)
    limits: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)
    inventory_effect: Mapped[str | None] = mapped_column(String(64), nullable=True)
    financial_effect: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="EMITTED")


# --------------------------------------------------------------------------- #
# Reglas de retención (007) — las instancias reutilizan 004 `ap_withholdings`
# --------------------------------------------------------------------------- #
class WithholdingRule(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Regla de retención IVA/ISLR versionada (FR-007-040)."""

    __tablename__ = "withholding_rules"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    tax_type: Mapped[str] = mapped_column(String(16), nullable=False)  # IVA / ISLR
    concept: Mapped[str | None] = mapped_column(String(120), nullable=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    conditions: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)
    base: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0.0)
    rate: Mapped[float] = mapped_column(Numeric(14, 6), nullable=False, default=0.0)
    minimum: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    subtractor: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    validity: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


# --------------------------------------------------------------------------- #
# Períodos y declaraciones (007) — libros como vista reconstruible
# --------------------------------------------------------------------------- #
class FiscalPeriod(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Período fiscal con cierre/reapertura aprobados (FR-007-051)."""

    __tablename__ = "fiscal_periods"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    tax_type: Mapped[str] = mapped_column(String(24), nullable=False)  # IVA / ISLR / IGTF / RETENCION
    period_key: Mapped[str] = mapped_column(String(12), nullable=False)  # 2026-01
    start: Mapped[date | None] = mapped_column(Date, nullable=True)
    end: Mapped[date | None] = mapped_column(Date, nullable=True)
    deadlines: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN")
    approvals: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)


class TaxReturnBatch(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Lote de declaración fiscal (FR-007-052)."""

    __tablename__ = "tax_return_batches"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    tax_type: Mapped[str] = mapped_column(String(24), nullable=False)
    period: Mapped[str] = mapped_column(String(12), nullable=False)
    files: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)
    totals: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)
    submission: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)
    payment: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)
    reconciliation: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")

