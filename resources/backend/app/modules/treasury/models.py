"""Modelos de tesorería (006, data-model.md).

Alcance: cajas (sesiones, movimientos, arqueo, pre-cierre, cierre y diferencias),
bancos/cuentas (transacciones con fecha valor y comisión), ingresos/egresos,
transferencias y depósitos, conciliación asistida con resolución manual auditada,
e IGTF por regla y evento (reglas versionadas; motor fiscal completo en 007).

Invariantes (Constitución P4/P5/P8, DOC-01 §5, DOC-02 §10, DOC-03 §12):
- Los saldos de caja/banco se calculan desde movimientos/cierres; nunca se editan.
- Una caja no se cierra con diferencia sin aprobación/justificación.
- Cobros/pagos se ejecutan separados de la factura y de la obligación.
- IGTF evaluado por regla y evento; no confundir con IVA adicional.
- Comisiones y diferencias cambiarias no alteran el IVA original.
- 006 consume los pagos de 004 y cobros de 005; no duplica su lógica.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.mixins import CodeMixin, CreatedByMixin, NameMixin, TimestampMixin, UUIDMixin


# --------------------------------------------------------------------------- #
# Maestros financieros (prerequisito — DOC-02 §3)
# --------------------------------------------------------------------------- #
class FinancialBank(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, NameMixin, Base):
    __tablename__ = "financial_banks"

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    swift: Mapped[str | None] = mapped_column(String(32), nullable=True)
    country: Mapped[str | None] = mapped_column(String(4), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    policies: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON


class FinancialAccount(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, NameMixin, Base):
    __tablename__ = "financial_accounts"

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    bank_id: Mapped[str] = mapped_column(ForeignKey("financial_banks.id"), nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="VED")
    iban: Mapped[str | None] = mapped_column(String(40), nullable=True)
    reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


class Cashbox(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, NameMixin, Base):
    __tablename__ = "cashboxes"

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="VED")
    warehouse_id: Mapped[str | None] = mapped_column(ForeignKey("warehouses.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    policies: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON


class PaymentMethod(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, NameMixin, Base):
    __tablename__ = "payment_methods"

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="OTHER")  # CASH / BANK / OTHER
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


class TreasuryInstrument(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, NameMixin, Base):
    __tablename__ = "treasury_instruments"

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    method_id: Mapped[str] = mapped_column(ForeignKey("payment_methods.id"), nullable=False, index=True)
    cashbox_id: Mapped[str | None] = mapped_column(ForeignKey("cashboxes.id"), nullable=True)
    account_id: Mapped[str | None] = mapped_column(ForeignKey("financial_accounts.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


class Currency(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, Base):
    __tablename__ = "currencies"

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    symbol: Mapped[str | None] = mapped_column(String(8), nullable=True)
    decimal_places: Mapped[int] = mapped_column(default=2, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


class ExchangeRate(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "exchange_rates"

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    currency_id: Mapped[str] = mapped_column(ForeignKey("currencies.id"), nullable=False, index=True)
    rate_date: Mapped[date] = mapped_column(Date, nullable=False)
    rate: Mapped[float] = mapped_column(Numeric(14, 6), nullable=False)
    source: Mapped[str | None] = mapped_column(String(120), nullable=True)


# --------------------------------------------------------------------------- #
# Cajas — sesiones y movimientos (DOC-03 §9 / DOC-02 §10)
# --------------------------------------------------------------------------- #
class CashSession(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "cash_sessions"

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    cashbox_id: Mapped[str] = mapped_column(ForeignKey("cashboxes.id"), nullable=False, index=True)
    opened_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    opened_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    closed_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    opened_amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0.0)
    counted_amount: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    expected_amount: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    difference: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN")
    # OPEN -> ARCHED (arqueo) -> PRE_CLOSED -> CLOSED / REJECTED
    approval_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    audit: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON


class CashSessionMovement(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "cash_session_movements"

    session_id: Mapped[str] = mapped_column(ForeignKey("cash_sessions.id"), nullable=False, index=True)
    movement_type: Mapped[str] = mapped_column(String(16), nullable=False)  # IN / OUT / ADJUST
    payment_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="PAYMENT")
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    instrument_id: Mapped[str | None] = mapped_column(ForeignKey("treasury_instruments.id"), nullable=True)
    reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


# --------------------------------------------------------------------------- #
# Bancos — transacciones y transferencias (DOC-03 §9)
# --------------------------------------------------------------------------- #
class BankTransaction(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "bank_transactions"

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("financial_accounts.id"), nullable=False, index=True)
    txn_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    value_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    direction: Mapped[str] = mapped_column(String(8), nullable=False, default="OUT")  # IN / OUT
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="VED")
    reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="PAYMENT")  # PAYMENT/COLLECTION/TRANSFER/DEPOSIT/ADJUSTMENT
    payment_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    commission: Mapped[float | None] = mapped_column(Float, nullable=True)
    rate_snapshot: Mapped[float | None] = mapped_column(Numeric(14, 6), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")


class TreasuryTransfer(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "treasury_transfers"

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    from_cashbox_id: Mapped[str | None] = mapped_column(ForeignKey("cashboxes.id"), nullable=True)
    from_account_id: Mapped[str | None] = mapped_column(ForeignKey("financial_accounts.id"), nullable=True)
    to_cashbox_id: Mapped[str | None] = mapped_column(ForeignKey("cashboxes.id"), nullable=True)
    to_account_id: Mapped[str | None] = mapped_column(ForeignKey("financial_accounts.id"), nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="VED")
    value_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")


# --------------------------------------------------------------------------- #
# Conciliación (DOC-03 §9 / DOC-02 §10)
# --------------------------------------------------------------------------- #
class Reconciliation(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "reconciliations"

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("financial_accounts.id"), nullable=False, index=True)
    statement_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    statement_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    opening_balance: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    closing_balance: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    # DRAFT -> IN_PROGRESS -> REVIEW -> APPROVED / REJECTED
    approved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    approved_at: Mapped[date | None] = mapped_column(Date, nullable=True)


class ReconciliationLine(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "reconciliation_lines"

    reconciliation_id: Mapped[str] = mapped_column(ForeignKey("reconciliations.id"), nullable=False, index=True)
    bank_transaction_id: Mapped[str | None] = mapped_column(ForeignKey("bank_transactions.id"), nullable=True)
    system_movement_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    system_movement_type: Mapped[str | None] = mapped_column(String(16), nullable=True)  # PAYMENT / ADVANCE / CREDIT
    match_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    matched_by: Mapped[str] = mapped_column(String(16), nullable=False, default="MANUAL")  # RULE / MANUAL
    rule_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="UNMATCHED")  # UNMATCHED / MATCHED / RESOLVED
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON: type MATCHED/DIFFERENCE/COMMISSION/FX + amount
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


# --------------------------------------------------------------------------- #
# IGTF por regla y evento (DOC-02 §10 / FR-006-040/041)
# --------------------------------------------------------------------------- #
class FiscalRule(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "fiscal_rules"

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    rule_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    rule_type: Mapped[str] = mapped_column(String(24), nullable=False, default="IGTF")  # IGTF / WITHHOLDING
    version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0")
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    params: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON: {"rate": 0.03}
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


class IgftEvent(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "igft_events"

    company_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(24), nullable=False)  # PAYMENT / COLLECTION / TRANSFER
    source_document: Mapped[str | None] = mapped_column(String(200), nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="VED")
    rate_snapshot: Mapped[float | None] = mapped_column(Numeric(14, 6), nullable=True)
    igft_amount: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    rule_id: Mapped[str | None] = mapped_column(ForeignKey("fiscal_rules.id"), nullable=True)
    evaluated_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="EVALUATED")
