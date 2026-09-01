"""Ventas y cuentas por cobrar (005).

Revision ID: 0005_ventas
Revises: 0004_compras
Create Date: 2026-08-04
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0005_ventas"
down_revision = "0004_compras"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------------- Cotización ----------------
    op.create_table(
        "sales_quotes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("customer_id", sa.String(length=36), sa.ForeignKey("parties.id"), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("price_list", sa.String(length=120), nullable=True),
        sa.Column("validity_until", sa.Date(), nullable=True),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="VED"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sales_quotes_company_id", "sales_quotes", ["company_id"])
    op.create_index("ix_sales_quotes_customer_id", "sales_quotes", ["customer_id"])

    op.create_table(
        "sales_quote_lines",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("quote_id", sa.String(length=36), sa.ForeignKey("sales_quotes.id"), nullable=False),
        sa.Column("product_id", sa.String(length=36), sa.ForeignKey("catalog_items.id"), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("unit_price", sa.Float(), nullable=False),
        sa.Column("discount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("tax_ref", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sales_quote_lines_quote_id", "sales_quote_lines", ["quote_id"])

    # ---------------- Orden de venta ----------------
    op.create_table(
        "sales_orders",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("customer_id", sa.String(length=36), sa.ForeignKey("parties.id"), nullable=False),
        sa.Column("warehouse_id", sa.String(length=36), sa.ForeignKey("warehouses.id"), nullable=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("credit_decision", sa.Text(), nullable=True),
        sa.Column("margin", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="VED"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="DRAFT"),
        sa.Column("approval_ref", sa.String(length=200), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sales_orders_company_id", "sales_orders", ["company_id"])
    op.create_index("ix_sales_orders_customer_id", "sales_orders", ["customer_id"])

    op.create_table(
        "sales_order_lines",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("order_id", sa.String(length=36), sa.ForeignKey("sales_orders.id"), nullable=False),
        sa.Column("product_id", sa.String(length=36), sa.ForeignKey("catalog_items.id"), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("unit_price", sa.Float(), nullable=False),
        sa.Column("discount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("tax_ref", sa.String(length=120), nullable=True),
        sa.Column("needs_inventory", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("snapshot", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sales_order_lines_order_id", "sales_order_lines", ["order_id"])

    # ---------------- Picking y despacho ----------------
    op.create_table(
        "pick_lists",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("order_id", sa.String(length=36), sa.ForeignKey("sales_orders.id"), nullable=False),
        sa.Column("warehouse_id", sa.String(length=36), sa.ForeignKey("warehouses.id"), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="DRAFT"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pick_lists_company_id", "pick_lists", ["company_id"])
    op.create_index("ix_pick_lists_order_id", "pick_lists", ["order_id"])

    op.create_table(
        "pick_list_lines",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("picklist_id", sa.String(length=36), sa.ForeignKey("pick_lists.id"), nullable=False),
        sa.Column("product_id", sa.String(length=36), sa.ForeignKey("catalog_items.id"), nullable=False),
        sa.Column("lot_id", sa.String(length=36), nullable=True),
        sa.Column("serial_id", sa.String(length=36), nullable=True),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pick_list_lines_picklist_id", "pick_list_lines", ["picklist_id"])

    op.create_table(
        "shipments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("order_id", sa.String(length=36), sa.ForeignKey("sales_orders.id"), nullable=False),
        sa.Column("origin_warehouse_id", sa.String(length=36), sa.ForeignKey("warehouses.id"), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("destination", sa.String(length=255), nullable=True),
        sa.Column("transport", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="DRAFT"),
        sa.Column("validation_status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_shipments_company_id", "shipments", ["company_id"])
    op.create_index("ix_shipments_order_id", "shipments", ["order_id"])

    op.create_table(
        "shipment_lines",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("shipment_id", sa.String(length=36), sa.ForeignKey("shipments.id"), nullable=False),
        sa.Column("product_id", sa.String(length=36), sa.ForeignKey("catalog_items.id"), nullable=False),
        sa.Column("lot_id", sa.String(length=36), nullable=True),
        sa.Column("serial_id", sa.String(length=36), nullable=True),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_shipment_lines_shipment_id", "shipment_lines", ["shipment_id"])

    # ---------------- Factura de venta ----------------
    op.create_table(
        "sales_invoices",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("customer_id", sa.String(length=36), sa.ForeignKey("parties.id"), nullable=False),
        sa.Column("invoice_number", sa.String(length=120), nullable=True),
        sa.Column("base_fiscal_currency", sa.String(length=8), nullable=False, server_default="VED"),
        sa.Column("base_fiscal", sa.Float(), nullable=False, server_default="0"),
        sa.Column("tax_total", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="DRAFT"),
        sa.Column("reversed_by_id", sa.String(length=36), nullable=True),
        sa.Column("idempotency_key", sa.String(length=120), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sales_invoices_company_id", "sales_invoices", ["company_id"])
    op.create_index("ix_sales_invoices_customer_id", "sales_invoices", ["customer_id"])
    op.create_index("ix_sales_invoices_idempotency_key", "sales_invoices", ["idempotency_key"])

    op.create_table(
        "sales_invoice_lines",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("invoice_id", sa.String(length=36), sa.ForeignKey("sales_invoices.id"), nullable=False),
        sa.Column("product_id", sa.String(length=36), sa.ForeignKey("catalog_items.id"), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("unit_price", sa.Float(), nullable=False),
        sa.Column("tax_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("base_fiscal", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total", sa.Float(), nullable=False, server_default="0"),
        sa.Column("snapshot", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sales_invoice_lines_invoice_id", "sales_invoice_lines", ["invoice_id"])

    # ---------------- Notas y devoluciones ----------------
    op.create_table(
        "sales_credit_notes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("customer_id", sa.String(length=36), sa.ForeignKey("parties.id"), nullable=False),
        sa.Column("invoice_ref", sa.String(length=200), nullable=True),
        sa.Column("number", sa.String(length=120), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("applied", sa.Float(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="VED"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="DRAFT"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sales_credit_notes_company_id", "sales_credit_notes", ["company_id"])
    op.create_index("ix_sales_credit_notes_customer_id", "sales_credit_notes", ["customer_id"])

    op.create_table(
        "sales_debit_notes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("customer_id", sa.String(length=36), sa.ForeignKey("parties.id"), nullable=False),
        sa.Column("invoice_ref", sa.String(length=200), nullable=True),
        sa.Column("number", sa.String(length=120), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="VED"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="DRAFT"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sales_debit_notes_company_id", "sales_debit_notes", ["company_id"])
    op.create_index("ix_sales_debit_notes_customer_id", "sales_debit_notes", ["customer_id"])

    op.create_table(
        "sales_returns",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("source_document", sa.String(length=200), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("condition", sa.String(length=32), nullable=False, server_default="DEFECTUOSO"),
        sa.Column("inventory_destination", sa.String(length=32), nullable=False, server_default="CUARENTENA"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="DRAFT"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sales_returns_company_id", "sales_returns", ["company_id"])

    op.create_table(
        "sales_return_lines",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("return_id", sa.String(length=36), sa.ForeignKey("sales_returns.id"), nullable=False),
        sa.Column("product_id", sa.String(length=36), sa.ForeignKey("catalog_items.id"), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("condition", sa.String(length=32), nullable=False, server_default="DEFECTUOSO"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sales_return_lines_return_id", "sales_return_lines", ["return_id"])


def downgrade() -> None:
    op.drop_table("sales_return_lines")
    op.drop_table("sales_returns")
    op.drop_table("sales_debit_notes")
    op.drop_table("sales_credit_notes")
    op.drop_table("sales_invoice_lines")
    op.drop_table("sales_invoices")
    op.drop_table("shipment_lines")
    op.drop_table("shipments")
    op.drop_table("pick_list_lines")
    op.drop_table("pick_lists")
    op.drop_table("sales_order_lines")
    op.drop_table("sales_orders")
    op.drop_table("sales_quote_lines")
    op.drop_table("sales_quotes")
