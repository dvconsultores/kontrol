"""Dinero y tasas a NUMERIC (T-05 de la auditoría 012).

Convierte las 58 columnas de dinero/tasas de FLOAT a NUMERIC para precisión
fiscal (dinero: numeric(18,2); tasas: numeric(14,6)).

Revision ID: 0012_numeric_money
Revises: 0011_homologacion
Create Date: 2026-08-10
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0012_numeric_money"
down_revision = "0011_homologacion"
branch_labels = None
depends_on = None


def _alter(table: str, column: str, numeric: sa.Numeric) -> None:
    op.alter_column(table, column, existing_type=sa.Float(), type_=numeric,
                    postgresql_using=f'"{column}"::numeric')


def upgrade() -> None:
    # Dinero -> numeric(18,2)
    # Corregido (validación sobre PostgreSQL real, 2026-08-29): la lista original
    # incluía seis tablas SIN columna `amount` — purchase_order_lines,
    # reconciliations, sales_invoices, supplier_invoices, supplier_quote_lines y
    # triple_matches. El ALTER fallaba con UndefinedColumn y detenía toda la
    # cadena en PostgreSQL. Sus columnas monetarias reales (unit_price, discount,
    # opening/closing_balance, base_fiscal, tax_total, total, variance_price,
    # variance_tax) ya se convierten en los `_alter` explícitos de más abajo.
    for t in ["ap_advances", "ap_applications", "ap_payment_instruments", "ap_payment_schedules",
              "ap_payments", "approval_requests", "bank_transactions", "cash_session_movements",
              "credit_debit_notes", "igft_events",
              "sales_credit_notes", "sales_debit_notes", "supplier_credit_notes",
              "treasury_transfers"]:
        _alter(t, "amount", sa.Numeric(18, 2))
    _alter("ap_withholdings", "amount", sa.Numeric(18, 2))
    _alter("ap_withholdings", "base", sa.Numeric(18, 2))
    _alter("cash_sessions", "opened_amount", sa.Numeric(18, 2))
    _alter("cash_sessions", "counted_amount", sa.Numeric(18, 2))
    _alter("cash_sessions", "expected_amount", sa.Numeric(18, 2))
    _alter("cost_layers", "unit_cost", sa.Numeric(18, 2))
    _alter("cost_layers", "landed_cost", sa.Numeric(18, 2))
    _alter("credit_debit_notes", "base_amount", sa.Numeric(18, 2))
    _alter("credit_debit_notes", "tax_amount", sa.Numeric(18, 2))
    _alter("igft_events", "igft_amount", sa.Numeric(18, 2))
    _alter("inventory_adjustments", "unit_cost", sa.Numeric(18, 2))
    _alter("inventory_movements", "unit_cost", sa.Numeric(18, 2))
    _alter("reconciliations", "opening_balance", sa.Numeric(18, 2))
    _alter("reconciliations", "closing_balance", sa.Numeric(18, 2))
    _alter("sales_invoice_lines", "unit_price", sa.Numeric(18, 2))
    _alter("sales_invoice_lines", "tax_amount", sa.Numeric(18, 2))
    _alter("sales_invoice_lines", "base_fiscal", sa.Numeric(18, 2))
    _alter("sales_invoice_lines", "total", sa.Numeric(18, 2))
    _alter("sales_invoices", "base_fiscal", sa.Numeric(18, 2))
    _alter("sales_invoices", "tax_total", sa.Numeric(18, 2))
    _alter("sales_invoices", "total", sa.Numeric(18, 2))
    _alter("purchase_order_lines", "unit_price", sa.Numeric(18, 2))
    _alter("sales_order_lines", "unit_price", sa.Numeric(18, 2))
    _alter("supplier_quote_lines", "unit_price", sa.Numeric(18, 2))
    _alter("triple_matches", "variance_price", sa.Numeric(18, 2))
    _alter("triple_matches", "variance_tax", sa.Numeric(18, 2))
    _alter("sales_quote_lines", "unit_price", sa.Numeric(18, 2))
    _alter("supplier_invoice_lines", "unit_price", sa.Numeric(18, 2))
    _alter("supplier_invoice_lines", "tax_amount", sa.Numeric(18, 2))
    _alter("supplier_invoice_lines", "total", sa.Numeric(18, 2))
    _alter("supplier_invoices", "tax_total", sa.Numeric(18, 2))
    _alter("supplier_invoices", "total", sa.Numeric(18, 2))
    _alter("tax_calculations", "base", sa.Numeric(18, 2))
    _alter("tax_calculations", "amount", sa.Numeric(18, 2))
    _alter("withholding_rules", "base", sa.Numeric(18, 2))

    # Tasas -> numeric(14,6)
    _alter("ap_applications", "rate", sa.Numeric(14, 6))
    _alter("ap_payment_instruments", "rate", sa.Numeric(14, 6))
    _alter("bank_transactions", "rate_snapshot", sa.Numeric(14, 6))
    _alter("cost_layers", "fiscal_rate", sa.Numeric(14, 6))
    _alter("exchange_rates", "rate", sa.Numeric(14, 6))
    _alter("fiscal_documents", "exchange_rate_snapshot", sa.Numeric(14, 6))
    _alter("igft_events", "rate_snapshot", sa.Numeric(14, 6))
    _alter("inventory_movements", "fiscal_rate", sa.Numeric(14, 6))
    _alter("tax_calculations", "rate", sa.Numeric(14, 6))
    _alter("withholding_rules", "rate", sa.Numeric(14, 6))


def downgrade() -> None:
    # Revertir a FLOAT (solo para ambientes no productivos / rollback controlado).
    for table, column in [
        ("ap_advances", "amount"), ("ap_applications", "amount"), ("ap_applications", "rate"),
        ("ap_payment_instruments", "amount"), ("ap_payment_instruments", "rate"),
        ("ap_payment_schedules", "amount"), ("ap_payments", "amount"),
        ("ap_withholdings", "base"), ("ap_withholdings", "amount"),
        ("approval_requests", "amount"), ("bank_transactions", "amount"), ("bank_transactions", "rate_snapshot"),
        ("cash_session_movements", "amount"), ("cash_sessions", "opened_amount"),
        ("cash_sessions", "counted_amount"), ("cash_sessions", "expected_amount"),
        ("cost_layers", "unit_cost"), ("cost_layers", "fiscal_rate"), ("cost_layers", "landed_cost"),
        ("credit_debit_notes", "amount"), ("credit_debit_notes", "base_amount"), ("credit_debit_notes", "tax_amount"),
        ("exchange_rates", "rate"), ("fiscal_documents", "exchange_rate_snapshot"),
        ("igft_events", "amount"), ("igft_events", "rate_snapshot"), ("igft_events", "igft_amount"),
        ("inventory_adjustments", "unit_cost"), ("inventory_movements", "unit_cost"),
        ("inventory_movements", "fiscal_rate"), ("purchase_order_lines", "unit_price"),
        ("reconciliations", "opening_balance"), ("reconciliations", "closing_balance"),
        ("sales_credit_notes", "amount"), ("sales_debit_notes", "amount"),
        ("sales_invoice_lines", "unit_price"), ("sales_invoice_lines", "tax_amount"),
        ("sales_invoice_lines", "base_fiscal"), ("sales_invoice_lines", "total"),
        ("sales_invoices", "base_fiscal"), ("sales_invoices", "tax_total"), ("sales_invoices", "total"),
        ("sales_order_lines", "unit_price"), ("sales_quote_lines", "unit_price"),
        ("supplier_credit_notes", "amount"), ("supplier_invoice_lines", "unit_price"),
        ("supplier_invoice_lines", "tax_amount"), ("supplier_invoice_lines", "total"),
        ("supplier_invoices", "tax_total"), ("supplier_invoices", "total"),
        ("supplier_quote_lines", "unit_price"), ("tax_calculations", "base"),
        ("tax_calculations", "rate"), ("tax_calculations", "amount"),
        ("treasury_transfers", "amount"), ("triple_matches", "variance_price"),
        ("withholding_rules", "base"), ("withholding_rules", "rate"),
    ]:
        op.alter_column(table, column, existing_type=sa.text("numeric"), type_=sa.Float(),
                        postgresql_using=f'"{column}"::double precision')
