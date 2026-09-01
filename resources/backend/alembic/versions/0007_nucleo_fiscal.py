"""Núcleo fiscal (007).

Revision ID: 0007_nucleo_fiscal
Revises: 0006_tesoreria
Create Date: 2026-08-04
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0007_nucleo_fiscal"
down_revision = "0006_tesoreria"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------------- Números de control individuales ----------------
    op.create_table(
        "control_numbers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("batch_id", sa.String(length=36), sa.ForeignKey("control_number_batches.id"), nullable=False),
        sa.Column("value", sa.String(length=32), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False, server_default="AVAILABLE"),
        sa.Column("document_ref", sa.String(length=200), nullable=True),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_control_numbers_company_id", "control_numbers", ["company_id"])
    op.create_index("ix_control_numbers_batch_id", "control_numbers", ["batch_id"])

    # ---------------- Cálculo fiscal y perfiles ----------------
    op.create_table(
        "tax_calculations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("document_ref", sa.String(length=200), nullable=True),
        sa.Column("line_ref", sa.String(length=200), nullable=True),
        sa.Column("rule_version_id", sa.String(length=36), sa.ForeignKey("tax_rule_versions.id"), nullable=True),
        sa.Column("base", sa.Float(), nullable=False, server_default="0"),
        sa.Column("rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("rounding", sa.Float(), nullable=False, server_default="2"),
        sa.Column("snapshot", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tax_calculations_company_id", "tax_calculations", ["company_id"])

    op.create_table(
        "tax_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("party_id", sa.String(length=36), sa.ForeignKey("parties.id"), nullable=True),
        sa.Column("item_id", sa.String(length=36), nullable=True),
        sa.Column("classifications", sa.JSON(), nullable=True),
        sa.Column("validity_from", sa.Date(), nullable=True),
        sa.Column("validity_to", sa.Date(), nullable=True),
        sa.Column("source", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tax_profiles_company_id", "tax_profiles", ["company_id"])

    # ---------------- Documentos fiscales e impresión ----------------
    op.create_table(
        "fiscal_documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("business_document", sa.String(length=200), nullable=False),
        sa.Column("document_type", sa.String(length=32), nullable=False),
        sa.Column("fiscal_mode", sa.String(length=24), nullable=False, server_default="DIGITAL"),
        sa.Column("series", sa.String(length=16), nullable=True),
        sa.Column("invoice_number", sa.String(length=64), nullable=True),
        sa.Column("control_number", sa.String(length=64), nullable=True),
        sa.Column("fiscal_currency", sa.String(length=8), nullable=False, server_default="VED"),
        sa.Column("exchange_rate_snapshot", sa.Float(), nullable=True),
        sa.Column("emitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("hash", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="EMITTED"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_fiscal_documents_company_id", "fiscal_documents", ["company_id"])
    op.create_index("ix_fiscal_documents_business_document", "fiscal_documents", ["business_document"])

    op.create_table(
        "print_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("fiscal_document_id", sa.String(length=36), sa.ForeignKey("fiscal_documents.id"), nullable=False),
        sa.Column("copy_type", sa.String(length=16), nullable=False, server_default="ORIGINAL"),
        sa.Column("printer", sa.String(length=120), nullable=True),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("printed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("hash", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_print_events_company_id", "print_events", ["company_id"])
    op.create_index("ix_print_events_fiscal_document_id", "print_events", ["fiscal_document_id"])

    op.create_table(
        "credit_debit_notes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("fiscal_document_id", sa.String(length=36), sa.ForeignKey("fiscal_documents.id"), nullable=True),
        sa.Column("original_document", sa.String(length=200), nullable=False),
        sa.Column("note_type", sa.String(length=16), nullable=False),
        sa.Column("cause", sa.String(length=255), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("base_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("tax_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("limits", sa.JSON(), nullable=True),
        sa.Column("inventory_effect", sa.String(length=64), nullable=True),
        sa.Column("financial_effect", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="EMITTED"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_credit_debit_notes_company_id", "credit_debit_notes", ["company_id"])

    # ---------------- Reglas de retención ----------------
    op.create_table(
        "withholding_rules",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("tax_type", sa.String(length=16), nullable=False),
        sa.Column("concept", sa.String(length=120), nullable=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("conditions", sa.JSON(), nullable=True),
        sa.Column("base", sa.Float(), nullable=False, server_default="0"),
        sa.Column("rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("minimum", sa.Float(), nullable=True),
        sa.Column("subtractor", sa.Float(), nullable=True),
        sa.Column("validity", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_withholding_rules_company_id", "withholding_rules", ["company_id"])
    op.create_index("ix_withholding_rules_code", "withholding_rules", ["code"])

    # ---------------- Períodos y declaraciones ----------------
    op.create_table(
        "fiscal_periods",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("tax_type", sa.String(length=24), nullable=False),
        sa.Column("period_key", sa.String(length=12), nullable=False),
        sa.Column("start", sa.Date(), nullable=True),
        sa.Column("end", sa.Date(), nullable=True),
        sa.Column("deadlines", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="OPEN"),
        sa.Column("approvals", sa.JSON(), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_fiscal_periods_company_id", "fiscal_periods", ["company_id"])

    op.create_table(
        "tax_return_batches",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("tax_type", sa.String(length=24), nullable=False),
        sa.Column("period", sa.String(length=12), nullable=False),
        sa.Column("files", sa.JSON(), nullable=True),
        sa.Column("totals", sa.JSON(), nullable=True),
        sa.Column("submission", sa.JSON(), nullable=True),
        sa.Column("payment", sa.JSON(), nullable=True),
        sa.Column("reconciliation", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="DRAFT"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tax_return_batches_company_id", "tax_return_batches", ["company_id"])


def downgrade() -> None:
    op.drop_table("tax_return_batches")
    op.drop_table("fiscal_periods")
    op.drop_table("withholding_rules")
    op.drop_table("credit_debit_notes")
    op.drop_table("print_events")
    op.drop_table("fiscal_documents")
    op.drop_table("tax_profiles")
    op.drop_table("tax_calculations")
    op.drop_table("control_numbers")
