"""Tesorería (006).

Revision ID: 0006_tesoreria
Revises: 0005_ventas
Create Date: 2026-08-04
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0006_tesoreria"
down_revision = "0005_ventas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------------- Maestros financieros ----------------
    op.create_table(
        "financial_banks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("swift", sa.String(length=32), nullable=True),
        sa.Column("country", sa.String(length=4), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("policies", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_financial_banks_company_id", "financial_banks", ["company_id"])

    op.create_table(
        "financial_accounts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("bank_id", sa.String(length=36), sa.ForeignKey("financial_banks.id"), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="VED"),
        sa.Column("iban", sa.String(length=40), nullable=True),
        sa.Column("reference", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_financial_accounts_company_id", "financial_accounts", ["company_id"])
    op.create_index("ix_financial_accounts_bank_id", "financial_accounts", ["bank_id"])

    op.create_table(
        "cashboxes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="VED"),
        sa.Column("warehouse_id", sa.String(length=36), sa.ForeignKey("warehouses.id"), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("policies", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cashboxes_company_id", "cashboxes", ["company_id"])

    op.create_table(
        "payment_methods",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False, server_default="OTHER"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payment_methods_company_id", "payment_methods", ["company_id"])

    op.create_table(
        "treasury_instruments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("method_id", sa.String(length=36), sa.ForeignKey("payment_methods.id"), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("cashbox_id", sa.String(length=36), sa.ForeignKey("cashboxes.id"), nullable=True),
        sa.Column("account_id", sa.String(length=36), sa.ForeignKey("financial_accounts.id"), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_treasury_instruments_company_id", "treasury_instruments", ["company_id"])
    op.create_index("ix_treasury_instruments_method_id", "treasury_instruments", ["method_id"])

    op.create_table(
        "currencies",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=True),
        sa.Column("symbol", sa.String(length=8), nullable=True),
        sa.Column("decimal_places", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_currencies_company_id", "currencies", ["company_id"])

    op.create_table(
        "exchange_rates",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("currency_id", sa.String(length=36), sa.ForeignKey("currencies.id"), nullable=False),
        sa.Column("rate_date", sa.Date(), nullable=False),
        sa.Column("rate", sa.Float(), nullable=False),
        sa.Column("source", sa.String(length=120), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_exchange_rates_company_id", "exchange_rates", ["company_id"])
    op.create_index("ix_exchange_rates_currency_id", "exchange_rates", ["currency_id"])

    # ---------------- Cajas ----------------
    op.create_table(
        "cash_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("cashbox_id", sa.String(length=36), sa.ForeignKey("cashboxes.id"), nullable=False),
        sa.Column("opened_by", sa.String(length=36), nullable=True),
        sa.Column("opened_at", sa.Date(), nullable=True),
        sa.Column("closed_at", sa.Date(), nullable=True),
        sa.Column("opened_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("counted_amount", sa.Float(), nullable=True),
        sa.Column("expected_amount", sa.Float(), nullable=True),
        sa.Column("difference", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="OPEN"),
        sa.Column("approval_note", sa.Text(), nullable=True),
        sa.Column("audit", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cash_sessions_company_id", "cash_sessions", ["company_id"])
    op.create_index("ix_cash_sessions_cashbox_id", "cash_sessions", ["cashbox_id"])

    op.create_table(
        "cash_session_movements",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), sa.ForeignKey("cash_sessions.id"), nullable=False),
        sa.Column("movement_type", sa.String(length=16), nullable=False),
        sa.Column("payment_id", sa.String(length=36), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="PAYMENT"),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("instrument_id", sa.String(length=36), sa.ForeignKey("treasury_instruments.id"), nullable=True),
        sa.Column("reference", sa.String(length=120), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cash_session_movements_session_id", "cash_session_movements", ["session_id"])

    # ---------------- Bancos ----------------
    op.create_table(
        "bank_transactions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("account_id", sa.String(length=36), sa.ForeignKey("financial_accounts.id"), nullable=False),
        sa.Column("txn_date", sa.Date(), nullable=True),
        sa.Column("value_date", sa.Date(), nullable=True),
        sa.Column("direction", sa.String(length=8), nullable=False, server_default="OUT"),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="VED"),
        sa.Column("reference", sa.String(length=120), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="PAYMENT"),
        sa.Column("payment_id", sa.String(length=36), nullable=True),
        sa.Column("commission", sa.Float(), nullable=True),
        sa.Column("rate_snapshot", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bank_transactions_company_id", "bank_transactions", ["company_id"])
    op.create_index("ix_bank_transactions_account_id", "bank_transactions", ["account_id"])

    op.create_table(
        "treasury_transfers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("from_cashbox_id", sa.String(length=36), sa.ForeignKey("cashboxes.id"), nullable=True),
        sa.Column("from_account_id", sa.String(length=36), sa.ForeignKey("financial_accounts.id"), nullable=True),
        sa.Column("to_cashbox_id", sa.String(length=36), sa.ForeignKey("cashboxes.id"), nullable=True),
        sa.Column("to_account_id", sa.String(length=36), sa.ForeignKey("financial_accounts.id"), nullable=True),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="VED"),
        sa.Column("value_date", sa.Date(), nullable=True),
        sa.Column("reference", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_treasury_transfers_company_id", "treasury_transfers", ["company_id"])

    # ---------------- Conciliación ----------------
    op.create_table(
        "reconciliations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("account_id", sa.String(length=36), sa.ForeignKey("financial_accounts.id"), nullable=False),
        sa.Column("statement_date", sa.Date(), nullable=True),
        sa.Column("statement_ref", sa.String(length=120), nullable=True),
        sa.Column("opening_balance", sa.Float(), nullable=True),
        sa.Column("closing_balance", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="DRAFT"),
        sa.Column("approved_by", sa.String(length=36), nullable=True),
        sa.Column("approved_at", sa.Date(), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reconciliations_company_id", "reconciliations", ["company_id"])
    op.create_index("ix_reconciliations_account_id", "reconciliations", ["account_id"])

    op.create_table(
        "reconciliation_lines",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("reconciliation_id", sa.String(length=36), sa.ForeignKey("reconciliations.id"), nullable=False),
        sa.Column("bank_transaction_id", sa.String(length=36), sa.ForeignKey("bank_transactions.id"), nullable=True),
        sa.Column("system_movement_id", sa.String(length=36), nullable=True),
        sa.Column("system_movement_type", sa.String(length=16), nullable=True),
        sa.Column("match_score", sa.Float(), nullable=True),
        sa.Column("matched_by", sa.String(length=16), nullable=False, server_default="MANUAL"),
        sa.Column("rule_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="UNMATCHED"),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reconciliation_lines_reconciliation_id", "reconciliation_lines", ["reconciliation_id"])

    # ---------------- IGTF ----------------
    op.create_table(
        "fiscal_rules",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("rule_code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=True),
        sa.Column("rule_type", sa.String(length=24), nullable=False, server_default="IGTF"),
        sa.Column("version", sa.String(length=32), nullable=False, server_default="1.0"),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("params", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_fiscal_rules_company_id", "fiscal_rules", ["company_id"])

    op.create_table(
        "igft_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=24), nullable=False),
        sa.Column("source_document", sa.String(length=200), nullable=True),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="VED"),
        sa.Column("rate_snapshot", sa.Float(), nullable=True),
        sa.Column("igft_amount", sa.Float(), nullable=True),
        sa.Column("rule_id", sa.String(length=36), sa.ForeignKey("fiscal_rules.id"), nullable=True),
        sa.Column("evaluated_at", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="EVALUATED"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_igft_events_company_id", "igft_events", ["company_id"])


def downgrade() -> None:
    op.drop_table("igft_events")
    op.drop_table("fiscal_rules")
    op.drop_table("reconciliation_lines")
    op.drop_table("reconciliations")
    op.drop_table("treasury_transfers")
    op.drop_table("bank_transactions")
    op.drop_table("cash_session_movements")
    op.drop_table("cash_sessions")
    op.drop_table("exchange_rates")
    op.drop_table("currencies")
    op.drop_table("treasury_instruments")
    op.drop_table("payment_methods")
    op.drop_table("cashboxes")
    op.drop_table("financial_accounts")
    op.drop_table("financial_banks")
