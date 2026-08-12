"""Segunda ola de dinero a NUMERIC (T-201 de la auditoría 012, KAUD-011).

Convierte las 18 columnas de dinero restantes de FLOAT a NUMERIC:
- Dinero: numeric(18,2)  (saldos abiertos, aplicados, descuentos, límites de
  crédito, bases de retención, comisiones, diferencias de caja, rounding).
- Tasa/margen: numeric(14,6)  (sales_orders.margin).

Las columnas de cantidad (quantity*, qty_*, capacity, factor, etc.) se
mantienen en FLOAT según la política de la Ola 2 (T-202, pendiente de ADR).

Revision ID: 0014_numeric_money_2
Revises: 0013_seed_business_permissions
Create Date: 2026-08-12
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0014_numeric_money_2"
down_revision = "0013_seed_business_permissions"
branch_labels = None
depends_on = None


def _alter(table: str, column: str, numeric: sa.Numeric) -> None:
    op.alter_column(table, column, existing_type=sa.Float(), type_=numeric,
                    postgresql_using=f'"{column}"::numeric')


def upgrade() -> None:
    # Dinero -> numeric(18,2)
    for t in ["ap_advances", "ap_payments", "sales_credit_notes", "supplier_credit_notes"]:
        _alter(t, "applied", sa.Numeric(18, 2))
    _alter("ap_advances", "available", sa.Numeric(18, 2))
    _alter("ap_open_items", "original", sa.Numeric(18, 2))
    _alter("ap_open_items", "applied", sa.Numeric(18, 2))
    _alter("bank_transactions", "commission", sa.Numeric(18, 2))
    _alter("cash_sessions", "difference", sa.Numeric(18, 2))
    _alter("customers", "credit_limit", sa.Numeric(18, 2))
    _alter("tax_calculations", "rounding", sa.Numeric(18, 2))
    _alter("withholding_rules", "minimum", sa.Numeric(18, 2))
    _alter("withholding_rules", "subtractor", sa.Numeric(18, 2))
    _alter("purchase_order_lines", "discount", sa.Numeric(18, 2))
    _alter("supplier_quote_lines", "discount", sa.Numeric(18, 2))
    _alter("sales_order_lines", "discount", sa.Numeric(18, 2))
    _alter("sales_quote_lines", "discount", sa.Numeric(18, 2))
    _alter("triple_matches", "variance_tax", sa.Numeric(18, 2))
    # Tasa/margen -> numeric(14,6)
    _alter("sales_orders", "margin", sa.Numeric(14, 6))


def downgrade() -> None:
    for t in ["ap_advances", "ap_payments", "sales_credit_notes", "supplier_credit_notes"]:
        op.alter_column(t, "applied", existing_type=sa.Numeric(18, 2), type_=sa.Float())
    op.alter_column("ap_advances", "available", existing_type=sa.Numeric(18, 2), type_=sa.Float())
    op.alter_column("ap_open_items", "original", existing_type=sa.Numeric(18, 2), type_=sa.Float())
    op.alter_column("ap_open_items", "applied", existing_type=sa.Numeric(18, 2), type_=sa.Float())
    op.alter_column("bank_transactions", "commission", existing_type=sa.Numeric(18, 2), type_=sa.Float())
    op.alter_column("cash_sessions", "difference", existing_type=sa.Numeric(18, 2), type_=sa.Float())
    op.alter_column("customers", "credit_limit", existing_type=sa.Numeric(18, 2), type_=sa.Float())
    op.alter_column("tax_calculations", "rounding", existing_type=sa.Numeric(18, 2), type_=sa.Float())
    op.alter_column("withholding_rules", "minimum", existing_type=sa.Numeric(18, 2), type_=sa.Float())
    op.alter_column("withholding_rules", "subtractor", existing_type=sa.Numeric(18, 2), type_=sa.Float())
    op.alter_column("purchase_order_lines", "discount", existing_type=sa.Numeric(18, 2), type_=sa.Float())
    op.alter_column("supplier_quote_lines", "discount", existing_type=sa.Numeric(18, 2), type_=sa.Float())
    op.alter_column("sales_order_lines", "discount", existing_type=sa.Numeric(18, 2), type_=sa.Float())
    op.alter_column("sales_quote_lines", "discount", existing_type=sa.Numeric(18, 2), type_=sa.Float())
    op.alter_column("triple_matches", "variance_tax", existing_type=sa.Numeric(18, 2), type_=sa.Float())
    op.alter_column("sales_orders", "margin", existing_type=sa.Numeric(14, 6), type_=sa.Float())
