from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.scope import Scope
from app.shared.mixins import CodeMixin, CreatedByMixin, TimestampMixin, UUIDMixin, VersionMixin


class ImportFile(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, VersionMixin, Base):
    __tablename__ = "import_files"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    supplier_id: Mapped[str] = mapped_column(ForeignKey("parties.id"), nullable=False, index=True)
    order_id: Mapped[str | None] = mapped_column(ForeignKey("purchase_orders.id"), nullable=True, index=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="VED")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="NEGOTIATING")
    incoterm: Mapped[str | None] = mapped_column(String(8), nullable=True)
    incoterm_place: Mapped[str | None] = mapped_column(String(120), nullable=True)
    payment_conditions: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivery_conditions: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_dispatch_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expected_arrival_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    agent_party_id: Mapped[str | None] = mapped_column(ForeignKey("parties.id"), nullable=True, index=True)
    carrier_party_id: Mapped[str | None] = mapped_column(ForeignKey("parties.id"), nullable=True, index=True)
    transport_document: Mapped[str | None] = mapped_column(String(120), nullable=True)
    origin: Mapped[str | None] = mapped_column(String(120), nullable=True)
    destination: Mapped[str | None] = mapped_column(String(120), nullable=True)
    actual_departure_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    dispatched_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_import_files_company_code"),
        Index("ix_import_files_company_status", "company_id", "status"),
        CheckConstraint(
            "status IN ('NEGOTIATING','ORDERED','DOCUMENTS_COMPLETE','DISPATCHED','CANCELLED')",
            name="ck_import_files_status",
        ),
    )


class ImportTrackingEvent(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "import_tracking_events"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    file_id: Mapped[str] = mapped_column(ForeignKey("import_files.id"), nullable=False, index=True)
    milestone: Mapped[str] = mapped_column(String(32), nullable=False)
    occurred_on: Mapped[date] = mapped_column(Date, nullable=False)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "milestone IN ('BOOKED','DEPARTED','IN_TRANSIT','TRANSSHIPMENT','DELAYED','OTHER')",
            name="ck_import_tracking_events_milestone",
        ),
    )


class ImportFinancialLink(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "import_financial_links"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    file_id: Mapped[str] = mapped_column(ForeignKey("import_files.id"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)

    __table_args__ = (
        UniqueConstraint("company_id", "kind", "target_id", name="uq_import_financial_links_company_kind_target"),
        CheckConstraint("kind IN ('PAYMENT','ADVANCE')", name="ck_import_financial_links_kind"),
    )


class ImportCorrection(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    __tablename__ = "import_corrections"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    file_id: Mapped[str] = mapped_column(ForeignKey("import_files.id"), nullable=False, index=True)
    document_id: Mapped[str | None] = mapped_column(ForeignKey("import_documents.id"), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    action_required: Mapped[str | None] = mapped_column(Text, nullable=True)
    responsible: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN")
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    __table_args__ = (
        CheckConstraint("kind IN ('FALTANTE','CORRECCION_DOCUMENTAL')", name="ck_import_corrections_kind"),
        CheckConstraint("responsible IN ('PROVEEDOR','AGENTE','IMPORTACION')", name="ck_import_corrections_responsible"),
        CheckConstraint("status IN ('OPEN','RESOLVED','CANCELLED')", name="ck_import_corrections_status"),
    )


class ImportDocument(UUIDMixin, TimestampMixin, VersionMixin, Base):
    __tablename__ = "import_documents"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING','RECEIVED','VALIDATED','OBSERVED')",
            name="ck_import_documents_status",
        ),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    file_id: Mapped[str] = mapped_column(ForeignKey("import_files.id"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    required: Mapped[bool] = mapped_column(nullable=False, default=False)
    reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    observation: Mapped[str | None] = mapped_column(String(255), nullable=True)


class ImportExpense(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    __tablename__ = "import_expenses"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    file_id: Mapped[str] = mapped_column(ForeignKey("import_files.id"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    supplier_id: Mapped[str] = mapped_column(ForeignKey("parties.id"), nullable=False, index=True)
    supplier_invoice_id: Mapped[str | None] = mapped_column(ForeignKey("supplier_invoices.id"), nullable=True, index=True)
    reference: Mapped[str] = mapped_column(String(120), nullable=False)
    concept: Mapped[str] = mapped_column(String(200), nullable=False)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    functional_currency: Mapped[str] = mapped_column(String(8), nullable=False)
    functional_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    rate_snapshot_id: Mapped[str] = mapped_column(ForeignKey("treasury_rate_snapshots.id"), nullable=False)
    import_document_id: Mapped[str | None] = mapped_column(ForeignKey("import_documents.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="REGISTERED")
    void_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    voided_by: Mapped[str | None] = mapped_column(String(36), nullable=True)

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_import_expenses_amount_positive"),
        CheckConstraint("status IN ('REGISTERED','VOIDED')", name="ck_import_expenses_status"),
        CheckConstraint("kind IN ('DIRECT_IMPORT_EXPENSE','LINKED_SUPPLIER_INVOICE')", name="ck_import_expenses_kind"),
        CheckConstraint(
            "(kind = 'LINKED_SUPPLIER_INVOICE' AND supplier_invoice_id IS NOT NULL) OR "
            "(kind = 'DIRECT_IMPORT_EXPENSE' AND supplier_invoice_id IS NULL)",
            name="ck_import_expenses_invoice_kind",
        ),
        Index("ix_import_expenses_company_file", "company_id", "file_id"),
    )
