from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
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
    capitalization: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="UNDETERMINED", default="UNDETERMINED"
    )
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
        CheckConstraint(
            "capitalization IN ('CAPITALIZABLE','NOT_CAPITALIZABLE','UNDETERMINED')",
            name="ck_import_expenses_capitalization",
        ),
        Index("ix_import_expenses_company_file", "company_id", "file_id"),
    )


class ImportCostApplication(UUIDMixin, TimestampMixin, CreatedByMixin, VersionMixin, Base):
    __tablename__ = "import_cost_applications"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    file_id: Mapped[str] = mapped_column(ForeignKey("import_files.id"), nullable=False, index=True)
    expense_id: Mapped[str] = mapped_column(ForeignKey("import_expenses.id"), nullable=False, index=True)
    criterion: Mapped[str] = mapped_column(String(16), nullable=False)
    criterion_source: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="APPLIED")
    origin_currency: Mapped[str] = mapped_column(String(8), nullable=False)
    origin_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    origin_rate_snapshot_id: Mapped[str] = mapped_column(ForeignKey("treasury_rate_snapshots.id"), nullable=False)
    origin_rate_value: Mapped[Decimal] = mapped_column(Numeric(24, 12), nullable=False)
    valuation_currency: Mapped[str] = mapped_column(String(8), nullable=False)
    valuation_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    valuation_rate_snapshot_id: Mapped[str | None] = mapped_column(
        ForeignKey("treasury_rate_snapshots.id"), nullable=True
    )
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    applied_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    reversed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reversed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    reversal_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "criterion IN ('VALUE','QUANTITY','MANUAL')",
            name="ck_import_cost_applications_criterion",
        ),
        CheckConstraint(
            "status IN ('APPLIED','REVERSED')",
            name="ck_import_cost_applications_status",
        ),
        Index(
            "uq_import_cost_applications_applied",
            "expense_id",
            unique=True,
            postgresql_where=text("status = 'APPLIED'"),
            sqlite_where=text("status = 'APPLIED'"),
        ),
        Index("ix_import_cost_applications_company", "company_id"),
        Index("ix_import_cost_applications_expense", "expense_id"),
    )


class ImportCostAllocation(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "import_cost_allocations"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    application_id: Mapped[str] = mapped_column(
        ForeignKey("import_cost_applications.id"), nullable=False, index=True
    )
    layer_id: Mapped[str] = mapped_column(ForeignKey("cost_layers.id"), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False, index=True)
    allocation_base: Mapped[Decimal] = mapped_column(Numeric(24, 6), nullable=False)
    participation: Mapped[Decimal] = mapped_column(Numeric(12, 8), nullable=False)
    exact_share: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    rounded_share: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    residual_adjustment: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    allocated_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    before_landed_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    after_landed_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    before_unit_cost: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    after_unit_cost: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "application_id",
            "layer_id",
            name="uq_import_cost_allocations_application_layer",
        ),
        Index("ix_import_cost_allocations_company", "company_id"),
        Index("ix_import_cost_allocations_application", "application_id"),
    )


class ImportDifferenceReport(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "import_difference_reports"
    __scope__ = Scope.COMPANY

    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    import_file_id: Mapped[str] = mapped_column(ForeignKey("import_files.id"), nullable=False, index=True)
    receipt_id: Mapped[str] = mapped_column(ForeignKey("goods_receipts.id"), nullable=False, index=True)
    chain_number: Mapped[int] = mapped_column(Integer, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    reference: Mapped[str] = mapped_column(String(32), nullable=False)
    supersedes_id: Mapped[str | None] = mapped_column(
        ForeignKey("import_difference_reports.id"), nullable=True
    )
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    issued_by: Mapped[str] = mapped_column(String(36), nullable=False)
    issued_by_name: Mapped[str] = mapped_column(String(64), nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_code: Mapped[str] = mapped_column(String(64), nullable=False)
    order_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    supplier_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    receipt_code: Mapped[str] = mapped_column(String(64), nullable=False)
    warehouse_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    line_count: Mapped[int] = mapped_column(Integer, nullable=False)
    incident_count: Mapped[int] = mapped_column(Integer, nullable=False)
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    file_name: Mapped[str] = mapped_column(String(120), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "reference",
            name="uq_import_difference_reports_company_reference",
        ),
        UniqueConstraint(
            "company_id",
            "chain_number",
            "revision",
            name="uq_import_difference_reports_chain_revision",
        ),
        UniqueConstraint(
            "receipt_id",
            "revision",
            name="uq_import_difference_reports_receipt_revision",
        ),
        CheckConstraint("revision >= 1", name="revision_positive"),
        CheckConstraint("chain_number >= 1", name="chain_positive"),
        Index("ix_import_difference_reports_receipt", "receipt_id"),
        Index("ix_import_difference_reports_file", "import_file_id"),
    )


class ImportDifferenceReportLine(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "import_difference_report_lines"
    __scope__ = Scope.COMPANY

    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    report_id: Mapped[str] = mapped_column(
        ForeignKey("import_difference_reports.id"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    receipt_line_id: Mapped[str] = mapped_column(String(36), nullable=False)
    product_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    product_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    presentation_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    base_uom: Mapped[str | None] = mapped_column(String(16), nullable=True)
    conversion_factor: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    ordered_base: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    received_base: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    counted_base: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    accepted_base: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    rejected_base: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    damaged_base: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    overage_base: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    difference_kinds: Mapped[str | None] = mapped_column(String(200), nullable=True)
    physical_condition: Mapped[str | None] = mapped_column(String(24), nullable=True)
    observation: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("report_id", "position", name="uq_import_difference_report_lines_position"),
    )


class ImportDifferenceReportIncident(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "import_difference_report_incidents"
    __scope__ = Scope.COMPANY

    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    report_id: Mapped[str] = mapped_column(
        ForeignKey("import_difference_reports.id"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    incident_id: Mapped[str] = mapped_column(String(36), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    incident_type: Mapped[str] = mapped_column(String(32), nullable=False)
    receipt_line_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    product_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    affected_base_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    escalated_by_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    escalation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution: Mapped[str | None] = mapped_column(String(32), nullable=True)
    resolution_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    authorization_status: Mapped[str] = mapped_column(String(32), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    registered_by_name: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (
        UniqueConstraint("report_id", "position", name="uq_import_difference_report_incidents_position"),
    )


class ImportDifferenceReportEvidence(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "import_difference_report_evidence"
    __scope__ = Scope.COMPANY

    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    report_id: Mapped[str] = mapped_column(
        ForeignKey("import_difference_reports.id"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_code: Mapped[str] = mapped_column(String(64), nullable=False)
    document_title: Mapped[str] = mapped_column(String(200), nullable=False)
    version_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)

    __table_args__ = (
        UniqueConstraint("report_id", "position", name="uq_import_difference_report_evidence_position"),
    )
