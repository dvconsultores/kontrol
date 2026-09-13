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

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.scope import Scope
from app.shared.mixins import CodeMixin, CreatedByMixin, NameMixin, TimestampMixin, UUIDMixin


# --------------------------------------------------------------------------- #
# Maestros financieros (prerequisito — DOC-02 §3)
# --------------------------------------------------------------------------- #
class FinancialBank(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, NameMixin, Base):
    __tablename__ = "financial_banks"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    swift: Mapped[str | None] = mapped_column(String(32), nullable=True)
    country: Mapped[str | None] = mapped_column(String(4), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    policies: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON


class FinancialAccount(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, NameMixin, Base):
    __tablename__ = "financial_accounts"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    bank_id: Mapped[str] = mapped_column(ForeignKey("financial_banks.id"), nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="VED")
    iban: Mapped[str | None] = mapped_column(String(40), nullable=True)
    reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


class Cashbox(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, NameMixin, Base):
    __tablename__ = "cashboxes"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="VED")
    warehouse_id: Mapped[str | None] = mapped_column(ForeignKey("warehouses.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    policies: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON


class PaymentMethod(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, NameMixin, Base):
    __tablename__ = "payment_methods"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False, default="OTHER")  # CASH / BANK / OTHER
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


class TreasuryInstrument(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, NameMixin, Base):
    __tablename__ = "treasury_instruments"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    method_id: Mapped[str] = mapped_column(ForeignKey("payment_methods.id"), nullable=False, index=True)
    cashbox_id: Mapped[str | None] = mapped_column(ForeignKey("cashboxes.id"), nullable=True)
    account_id: Mapped[str | None] = mapped_column(ForeignKey("financial_accounts.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


class Currency(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, Base):
    __tablename__ = "currencies"
    #: Una sola moneda **activa** por código en cada empresa (Spec 013). Sin
    #: esto, dos «USD» convivían y la resolución elegía una al azar. Es parcial
    #: para que desactivar una moneda no impida volver a darla de alta.
    #:
    #: Declarado aquí y no solo en la migración `0056`: si vive únicamente en la
    #: migración, la base que las pruebas construyen desde los modelos no lo
    #: tiene, y ninguna prueba ejerce la unicidad.
    __table_args__ = (
        Index("uq_currencies_company_code_active", "company_id", "code", unique=True,
              postgresql_where=sql_text("status = 'ACTIVE'")).ddl_if(dialect="postgresql"),
    )
    #: De empresa, no de tenant. La matriz canónica las clasificó como de
    #: tenant por su naturaleza —moneda, tasa, informe— pero el código exige
    #: empresa al crearlas, lista por empresa y N5 probó su aislamiento A/B.
    #: La declaración era lo que no coincidía con el comportamiento.
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    symbol: Mapped[str | None] = mapped_column(String(8), nullable=True)
    decimal_places: Mapped[int] = mapped_column(default=2, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


# --------------------------------------------------------------------------- #
# Spec 013 · maestros financieros
#
# La 038 dejó de inventar tasas y destapó que nadie las registra. Lo que aquí
# se añade es la autoridad de la tasa: de qué fuente viene, qué par expresa,
# desde cuándo rige y cómo se resuelve —incluida la respuesta «no la hay»—.
#
# Ninguna regla legal venezolana se escribe en el código. La moneda funcional
# la declara la empresa; la fuente y su autoridad, el maestro.
# --------------------------------------------------------------------------- #
class ExchangeRateSource(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, NameMixin, Base):
    """De dónde viene una tasa.

    `source_type` es texto del maestro y no un `enum` del código: la lista de
    fuentes de un país no la decide el programa. `provider_code` enlaza con el
    adaptador externo de la Spec 048 cuando exista; sin él, la fuente sigue
    siendo utilizable a mano.
    """

    __tablename__ = "exchange_rate_sources"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_rate_sources_company_code"),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default="MANUAL")
    authority_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    provider_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    allows_manual: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    #: Salud de la sincronización. No son observaciones de tasa: son el estado
    #: del canal, y confundirlos haría pasar un error de red por una cotización.
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(1000), nullable=True)


class ExchangeRatePolicy(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Cómo se **resuelve** una tasa.

    Distinta de `TreasuryFxPolicy`, que es la política de operación y es de la
    Spec 038: aquélla decide si se puede convertir; ésta, de dónde sale el
    número. Nace denegando inversión y triangulación porque derivar una tasa es
    tomar una decisión económica, y el código no la toma solo.
    """

    __tablename__ = "exchange_rate_policies"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("company_id", "policy_code", "version",
                         name="uq_rate_policies_company_code_version"),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    policy_code: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    allow_inversion: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allow_triangulation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    triangulation_currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    #: Nulo = sin tope, que es el comportamiento heredado. Declarado en vez de
    #: implícito: sin política, una tasa de 2020 valora una operación de 2026.
    max_age_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    carry_forward: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    require_rate_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    #: La escala de la tasa es del maestro. 6 es lo que la columna venía
    #: aplicando; queda declarado, no cableado en el servicio.
    rate_scale: Mapped[int] = mapped_column(Integer, nullable=False, default=6)
    authority_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)


class ExchangeRateImportBatch(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Un fichero de tasas. El hash es lo que hace idempotente reimportarlo."""

    __tablename__ = "exchange_rate_import_batches"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("company_id", "content_hash", name="uq_rate_import_company_hash"),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("exchange_rate_sources.id"), nullable=False)
    rate_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    filename: Mapped[str | None] = mapped_column(String(300), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    imported_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rejected_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="COMPLETED")


class ExchangeRate(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Una observación de tasa, con su par explícito y su procedencia.

    **1 unidad de `base` = `rate` unidades de `quote`.** Con `base = USD`,
    `quote = VES` y `rate = 100`: un dólar son cien bolívares. Antes el par lo
    suponía el código, con la moneda funcional escrita dentro del dominio.

    `currency_id` y `rate_date` se conservan: son la clave foránea viva de la
    instantánea de la 038 y el camino de lectura de lo ya escrito.
    """

    __tablename__ = "exchange_rates"
    #: Una observación por coordenadas, salvo las sustituidas: la corrección
    #: crea la versión siguiente y la anterior queda fuera del índice.
    __table_args__ = (
        CheckConstraint("rate > 0", name="ck_exchange_rates_rate_positive"),
        Index("uq_exchange_rates_observation", "company_id", "base_currency_id",
              "quote_currency_id", "source_id", "rate_type", "effective_at", "version",
              unique=True,
              postgresql_where=sql_text("status <> 'SUPERSEDED'")).ddl_if(dialect="postgresql"),
    )
    #: De empresa, no de tenant. La matriz canónica las clasificó como de
    #: tenant por su naturaleza —moneda, tasa, informe— pero el código exige
    #: empresa al crearlas, lista por empresa y N5 probó su aislamiento A/B.
    #: La declaración era lo que no coincidía con el comportamiento.
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    currency_id: Mapped[str] = mapped_column(ForeignKey("currencies.id"), nullable=False, index=True)
    rate_date: Mapped[date] = mapped_column(Date, nullable=False)
    #: `Decimal`, no `float`. La columna siempre fue exacta; la anotación era
    #: la que mentía, y es la familia de `KQA-100`.
    rate: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    source: Mapped[str | None] = mapped_column(String(120), nullable=True)

    base_currency_id: Mapped[str | None] = mapped_column(ForeignKey("currencies.id"), nullable=True)
    quote_currency_id: Mapped[str | None] = mapped_column(ForeignKey("currencies.id"), nullable=True)
    source_id: Mapped[str | None] = mapped_column(ForeignKey("exchange_rate_sources.id"), nullable=True)
    rate_type: Mapped[str] = mapped_column(String(32), nullable=False, default="REFERENCE")
    effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True,
                                                          index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    #: Una corrección no reescribe: sucede. La original queda `SUPERSEDED` y la
    #: instantánea que la usó sigue apuntando a ella.
    supersedes_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    provider_observation_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    import_batch_id: Mapped[str | None] = mapped_column(
        ForeignKey("exchange_rate_import_batches.id"), nullable=True)
    source_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    authority_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    entered_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)


# --------------------------------------------------------------------------- #
# Cajas — sesiones y movimientos (DOC-03 §9 / DOC-02 §10)
# --------------------------------------------------------------------------- #
class CashSession(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "cash_sessions"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    cashbox_id: Mapped[str] = mapped_column(ForeignKey("cashboxes.id"), nullable=False, index=True)
    opened_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    opened_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    closed_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    opened_amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0.0)
    counted_amount: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    expected_amount: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    difference: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN")
    # OPEN -> ARCHED (arqueo) -> PRE_CLOSED -> CLOSED / REJECTED
    approval_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    audit: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON


class CashSessionMovement(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "cash_session_movements"
    __scope__ = Scope.COMPANY
    __scope_authority__ = "session_id → cash_sessions"

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
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("financial_accounts.id"), nullable=False, index=True)
    txn_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    value_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    direction: Mapped[str] = mapped_column(String(8), nullable=False, default="OUT")  # IN / OUT
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="VED")
    reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="PAYMENT")  # PAYMENT/COLLECTION/TRANSFER/DEPOSIT/ADJUSTMENT
    payment_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    commission: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    rate_snapshot: Mapped[float | None] = mapped_column(Numeric(14, 6), nullable=True)
    #: La instantánea completa que gobernó la conversión, con su procedencia. La
    #: columna anterior guardaba un número suelto: no decía de dónde salía.
    rate_snapshot_id: Mapped[str | None] = mapped_column(
        ForeignKey("treasury_rate_snapshots.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")


class TreasuryTransfer(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "treasury_transfers"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
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
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
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
    __scope__ = Scope.COMPANY
    __scope_authority__ = "reconciliation_id → reconciliations"

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
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
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
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(24), nullable=False)  # PAYMENT / COLLECTION / TRANSFER
    source_document: Mapped[str | None] = mapped_column(String(200), nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="VED")
    rate_snapshot: Mapped[float | None] = mapped_column(Numeric(14, 6), nullable=True)
    igft_amount: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    rule_id: Mapped[str | None] = mapped_column(ForeignKey("fiscal_rules.id"), nullable=True)
    evaluated_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="EVALUATED")


# --------------------------------------------------------------------------- #
# Spec 038 · política cambiaria, conversión explícita y reembolso
#
# La arquitectura funcional §9 dejaba el hueco a propósito: «las diferencias
# cambiarias se calculan al aplicar o valorar **según política**». No había
# política. Lo que había era `_rate_snapshot` devolviendo **1,0** cuando no
# encontraba la moneda o no había tasa cargada, así que un pago en divisa se
# registraba al cambio uno y nadie se enteraba.
#
# Nada de esto escribe una regla legal venezolana en el código: la política se
# configura, se versiona y guarda de qué autoridad viene. `D0-07` sigue abierto.
# --------------------------------------------------------------------------- #
class TreasuryFxPolicy(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """La política cambiaria de una empresa, con vigencia y versión.

    Se guarda **qué versión** gobernó cada operación, para que cambiarla mañana
    no reescriba lo de ayer.
    """

    __tablename__ = "treasury_fx_policies"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        CheckConstraint("effective_date_basis IN ('TRANSACTION', 'SETTLEMENT')",
                        name="ck_treasury_fx_policies_basis"),
        CheckConstraint("status IN ('DRAFT', 'ACTIVE', 'SUPERSEDED')",
                        name="ck_treasury_fx_policies_status"),
        Index("uq_treasury_fx_policies_active", "company_id", "policy_code", unique=True,
              postgresql_where=sql_text("status = 'ACTIVE'")).ddl_if(dialect="postgresql"),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    policy_code: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default=sql_text("1"))
    functional_currency: Mapped[str] = mapped_column(String(8), nullable=False)
    #: `TRANSACTION` o `SETTLEMENT`. Cuál rige no se escribe: se configura.
    effective_date_basis: Mapped[str] = mapped_column(String(32), nullable=False,
                                                      default="SETTLEMENT",
                                                      server_default="SETTLEMENT")
    rate_source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    rate_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    allow_cross_currency: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False,
                                                       server_default=sql_text("false"))
    allow_manual_rate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False,
                                                    server_default=sql_text("false"))
    manual_rate_requires_approval: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=sql_text("true"))
    allow_refund: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False,
                                               server_default=sql_text("false"))
    refund_requires_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True,
                                                           server_default=sql_text("true"))
    #: Qué norma la respalda. Vacía mientras no exista: el mecanismo es
    #: parametrizable y la validación legal sigue en `D0-07`.
    authority_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT",
                                        server_default="DRAFT")
    approved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TreasuryRateSnapshot(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """La procedencia entera de una tasa, congelada en la operación.

    Una tasa futura no cambia una operación pasada porque la operación no vuelve
    a preguntar: guarda la que usó, de dónde salió y con qué política.
    """

    __tablename__ = "treasury_rate_snapshots"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        CheckConstraint("rate > 0", name="ck_treasury_rate_snapshots_positive"),
        CheckConstraint("origin IN ('REGISTERED', 'MANUAL')",
                        name="ck_treasury_rate_snapshots_origin"),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    source_currency: Mapped[str] = mapped_column(String(8), nullable=False)
    target_currency: Mapped[str] = mapped_column(String(8), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    rate_source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    rate_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rate_date: Mapped[date] = mapped_column(Date, nullable=False)
    exchange_rate_id: Mapped[str | None] = mapped_column(ForeignKey("exchange_rates.id"),
                                                         nullable=True)
    #: `INVERSE` o `TRIANGULATION` cuando la tasa no salió de una fila tal cual.
    #: Nulo es lo normal: la Spec 013 deniega derivar salvo política expresa.
    derivation: Mapped[str | None] = mapped_column(String(32), nullable=True)
    derived_from: Mapped[str | None] = mapped_column(String(500), nullable=True)
    policy_id: Mapped[str | None] = mapped_column(ForeignKey("treasury_fx_policies.id"),
                                                   nullable=True)
    policy_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    #: `REGISTERED` si viene del maestro, `MANUAL` si la escribió una persona.
    #: No hay una tercera: no existe tasa por defecto.
    origin: Mapped[str] = mapped_column(String(16), nullable=False, default="REGISTERED",
                                        server_default="REGISTERED")
    manual_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class TreasuryFxConversion(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Cambiar de moneda es un hecho, no un número escondido en otro."""

    __tablename__ = "treasury_fx_conversions"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        CheckConstraint("source_amount > 0 AND target_amount > 0",
                        name="ck_treasury_fx_conversions_positive"),
        Index("uq_treasury_fx_conversions_idem", "company_id", "idempotency_key", unique=True,
              postgresql_where=sql_text("idempotency_key IS NOT NULL")).ddl_if(dialect="postgresql"),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    source_account_id: Mapped[str] = mapped_column(ForeignKey("financial_accounts.id"), nullable=False)
    target_account_id: Mapped[str] = mapped_column(ForeignKey("financial_accounts.id"), nullable=False)
    source_currency: Mapped[str] = mapped_column(String(8), nullable=False)
    target_currency: Mapped[str] = mapped_column(String(8), nullable=False)
    source_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    target_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    rate_snapshot_id: Mapped[str] = mapped_column(ForeignKey("treasury_rate_snapshots.id"),
                                                   nullable=False)
    source_movement_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    target_movement_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    #: Su propio hecho. No reescribe ningún documento fiscal: «no alteran el IVA
    #: original por sí solas».
    exchange_difference: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    difference_currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="SETTLED",
                                        server_default="SETTLED")
    reversal_of: Mapped[str | None] = mapped_column(String(36), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(120), nullable=True)


class TreasuryRefund(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """La devolución en dinero de un crédito a favor del cliente.

    `OWNER-DECISION-038-01`: se soporta, no es automática, exige solicitud,
    validación del crédito, aprobación y ejecución desde tesorería.

    El **saldo económico** del crédito sigue viviendo en su nota, que es de la
    Spec 037. Aquí vive la solicitud y su ejecución: duplicar el saldo dentro de
    tesorería sería tener dos verdades sobre el mismo dinero.
    """

    __tablename__ = "treasury_refunds"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_treasury_refunds_positive"),
        CheckConstraint(
            "status IN ('REQUESTED', 'APPROVED', 'REJECTED', 'SETTLED', 'CANCELLED', 'REVERSED')",
            name="ck_treasury_refunds_status"),
        Index("uq_treasury_refunds_idem", "company_id", "idempotency_key", unique=True,
              postgresql_where=sql_text("idempotency_key IS NOT NULL")).ddl_if(dialect="postgresql"),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("parties.id"), nullable=False)
    credit_note_id: Mapped[str] = mapped_column(ForeignKey("sales_credit_notes.id"),
                                                 nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    account_id: Mapped[str | None] = mapped_column(ForeignKey("financial_accounts.id"), nullable=True)
    payment_method_id: Mapped[str | None] = mapped_column(ForeignKey("payment_methods.id"),
                                                           nullable=True)
    beneficiary_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="REQUESTED",
                                        server_default="REQUESTED")
    status_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    movement_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    reversal_of: Mapped[str | None] = mapped_column(String(36), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    requested_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    settled_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
