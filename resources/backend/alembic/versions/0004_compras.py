"""Compras y cuentas por pagar (004).

Revision ID: 0004_compras
Revises: 0003_inventario
Create Date: 2026-08-04
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0004_compras"
down_revision = "0003_inventario"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------------- Requisición ----------------
    op.create_table(
        "purchase_requisitions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("requester_id", sa.String(length=36), nullable=True),
        sa.Column("cost_center_id", sa.String(length=36), nullable=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("need_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="DRAFT"),
        sa.Column("approval_ref", sa.String(length=200), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_purchase_requisitions_company_id", "purchase_requisitions", ["company_id"])

    op.create_table(
        "purchase_requisition_lines",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("requisition_id", sa.String(length=36), sa.ForeignKey("purchase_requisitions.id"), nullable=False),
        sa.Column("product_id", sa.String(length=36), sa.ForeignKey("catalog_items.id"), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("unit_id", sa.String(length=36), sa.ForeignKey("units_of_measure.id"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_purchase_requisition_lines_requisition_id", "purchase_requisition_lines", ["requisition_id"])

    # ---------------- Cotización ----------------
    op.create_table(
        "supplier_quotes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("supplier_id", sa.String(length=36), sa.ForeignKey("parties.id"), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("validity_until", sa.Date(), nullable=True),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="VED"),
        sa.Column("terms", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_supplier_quotes_company_id", "supplier_quotes", ["company_id"])
    op.create_index("ix_supplier_quotes_supplier_id", "supplier_quotes", ["supplier_id"])

    op.create_table(
        "supplier_quote_lines",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("quote_id", sa.String(length=36), sa.ForeignKey("supplier_quotes.id"), nullable=False),
        sa.Column("product_id", sa.String(length=36), sa.ForeignKey("catalog_items.id"), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("unit_price", sa.Float(), nullable=False),
        sa.Column("discount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("delivery_days", sa.Integer(), nullable=True),
        sa.Column("tax_ref", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_supplier_quote_lines_quote_id", "supplier_quote_lines", ["quote_id"])

    # ---------------- Orden de compra ----------------
    op.create_table(
        "purchase_orders",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("supplier_id", sa.String(length=36), sa.ForeignKey("parties.id"), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("terms", sa.Text(), nullable=True),
        sa.Column("expected_date", sa.Date(), nullable=True),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="VED"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="DRAFT"),
        sa.Column("approval_ref", sa.String(length=200), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_purchase_orders_company_id", "purchase_orders", ["company_id"])
    op.create_index("ix_purchase_orders_supplier_id", "purchase_orders", ["supplier_id"])

    op.create_table(
        "purchase_order_lines",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("order_id", sa.String(length=36), sa.ForeignKey("purchase_orders.id"), nullable=False),
        sa.Column("product_id", sa.String(length=36), sa.ForeignKey("catalog_items.id"), nullable=False),
        sa.Column("quantity_ordered", sa.Float(), nullable=False),
        sa.Column("quantity_received", sa.Float(), nullable=False, server_default="0"),
        sa.Column("unit_price", sa.Float(), nullable=False),
        sa.Column("discount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("tax_ref", sa.String(length=120), nullable=True),
        sa.Column("needs_inventory", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("snapshot", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_purchase_order_lines_order_id", "purchase_order_lines", ["order_id"])

    # ---------------- Recepción ----------------
    op.create_table(
        "goods_receipts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("order_id", sa.String(length=36), sa.ForeignKey("purchase_orders.id"), nullable=False),
        sa.Column("warehouse_id", sa.String(length=36), sa.ForeignKey("warehouses.id"), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="DRAFT"),
        sa.Column("quality_status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_goods_receipts_company_id", "goods_receipts", ["company_id"])
    op.create_index("ix_goods_receipts_order_id", "goods_receipts", ["order_id"])

    op.create_table(
        "goods_receipt_lines",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("receipt_id", sa.String(length=36), sa.ForeignKey("goods_receipts.id"), nullable=False),
        sa.Column("order_line_id", sa.String(length=36), sa.ForeignKey("purchase_order_lines.id"), nullable=False),
        sa.Column("product_id", sa.String(length=36), sa.ForeignKey("catalog_items.id"), nullable=False),
        sa.Column("quantity_received", sa.Float(), nullable=False),
        sa.Column("quantity_accepted", sa.Float(), nullable=False, server_default="0"),
        sa.Column("quantity_rejected", sa.Float(), nullable=False, server_default="0"),
        sa.Column("lot_id", sa.String(length=36), sa.ForeignKey("inventory_lots.id"), nullable=True),
        sa.Column("lot_number", sa.String(length=120), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("serials", sa.Text(), nullable=True),
        sa.Column("quality", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_goods_receipt_lines_receipt_id", "goods_receipt_lines", ["receipt_id"])

    # ---------------- Factura del proveedor y conciliación triple ----------------
    op.create_table(
        "supplier_invoices",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("supplier_id", sa.String(length=36), sa.ForeignKey("parties.id"), nullable=False),
        sa.Column("invoice_number", sa.String(length=120), nullable=False),
        sa.Column("control_number", sa.String(length=120), nullable=True),
        sa.Column("issue_date", sa.Date(), nullable=True),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="VED"),
        sa.Column("tax_total", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="DRAFT"),
        sa.Column("reversed_by_id", sa.String(length=36), nullable=True),
        sa.Column("idempotency_key", sa.String(length=120), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "supplier_id", "invoice_number", "control_number",
                            name="uq_supplier_invoices_company_supplier_invoice_control"),
    )
    op.create_index("ix_supplier_invoices_company_id", "supplier_invoices", ["company_id"])
    op.create_index("ix_supplier_invoices_supplier_id", "supplier_invoices", ["supplier_id"])
    op.create_index("ix_supplier_invoices_idempotency_key", "supplier_invoices", ["idempotency_key"])

    op.create_table(
        "supplier_invoice_lines",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("invoice_id", sa.String(length=36), sa.ForeignKey("supplier_invoices.id"), nullable=False),
        sa.Column("order_line_id", sa.String(length=36), sa.ForeignKey("purchase_order_lines.id"), nullable=True),
        sa.Column("receipt_line_id", sa.String(length=36), sa.ForeignKey("goods_receipt_lines.id"), nullable=True),
        sa.Column("product_id", sa.String(length=36), sa.ForeignKey("catalog_items.id"), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("unit_price", sa.Float(), nullable=False),
        sa.Column("tax_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total", sa.Float(), nullable=False, server_default="0"),
        sa.Column("snapshot", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_supplier_invoice_lines_invoice_id", "supplier_invoice_lines", ["invoice_id"])

    op.create_table(
        "triple_matches",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("invoice_id", sa.String(length=36), sa.ForeignKey("supplier_invoices.id"), nullable=False),
        sa.Column("order_line_id", sa.String(length=36), sa.ForeignKey("purchase_order_lines.id"), nullable=True),
        sa.Column("receipt_line_id", sa.String(length=36), sa.ForeignKey("goods_receipt_lines.id"), nullable=True),
        sa.Column("invoice_line_id", sa.String(length=36), sa.ForeignKey("supplier_invoice_lines.id"), nullable=True),
        sa.Column("variance_qty", sa.Float(), nullable=False, server_default="0"),
        sa.Column("variance_price", sa.Float(), nullable=False, server_default="0"),
        sa.Column("variance_tax", sa.Float(), nullable=False, server_default="0"),
        sa.Column("resolution", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("approved_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_triple_matches_company_id", "triple_matches", ["company_id"])
    op.create_index("ix_triple_matches_invoice_id", "triple_matches", ["invoice_id"])

    # ---------------- Devoluciones y notas de crédito ----------------
    op.create_table(
        "purchase_returns",
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
    op.create_index("ix_purchase_returns_company_id", "purchase_returns", ["company_id"])

    op.create_table(
        "purchase_return_lines",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("return_id", sa.String(length=36), sa.ForeignKey("purchase_returns.id"), nullable=False),
        sa.Column("product_id", sa.String(length=36), sa.ForeignKey("catalog_items.id"), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("condition", sa.String(length=32), nullable=False, server_default="DEFECTUOSO"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_purchase_return_lines_return_id", "purchase_return_lines", ["return_id"])

    op.create_table(
        "supplier_credit_notes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("supplier_id", sa.String(length=36), sa.ForeignKey("parties.id"), nullable=False),
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
    op.create_index("ix_supplier_credit_notes_company_id", "supplier_credit_notes", ["company_id"])
    op.create_index("ix_supplier_credit_notes_supplier_id", "supplier_credit_notes", ["supplier_id"])

    # ---------------- CxP ----------------
    op.create_table(
        "ap_open_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("party_id", sa.String(length=36), sa.ForeignKey("parties.id"), nullable=False),
        sa.Column("source_document", sa.String(length=200), nullable=True),
        sa.Column("item_type", sa.String(length=16), nullable=False, server_default="PAYABLE"),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="VED"),
        sa.Column("original", sa.Float(), nullable=False),
        sa.Column("applied", sa.Float(), nullable=False, server_default="0"),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="OPEN"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ap_open_items_company_id", "ap_open_items", ["company_id"])
    op.create_index("ix_ap_open_items_party_id", "ap_open_items", ["party_id"])

    op.create_table(
        "ap_payments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("party_id", sa.String(length=36), sa.ForeignKey("parties.id"), nullable=False),
        sa.Column("direction", sa.String(length=8), nullable=False, server_default="OUT"),
        sa.Column("date", sa.Date(), nullable=True),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="VED"),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("applied", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="DRAFT"),
        sa.Column("approver_id", sa.String(length=36), nullable=True),
        sa.Column("idempotency_key", sa.String(length=120), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ap_payments_company_id", "ap_payments", ["company_id"])
    op.create_index("ix_ap_payments_party_id", "ap_payments", ["party_id"])
    op.create_index("ix_ap_payments_idempotency_key", "ap_payments", ["idempotency_key"])

    op.create_table(
        "ap_payment_instruments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("payment_id", sa.String(length=36), sa.ForeignKey("ap_payments.id"), nullable=False),
        sa.Column("method", sa.String(length=32), nullable=False),
        sa.Column("account", sa.String(length=120), nullable=True),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="VED"),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("rate", sa.Float(), nullable=True),
        sa.Column("reference", sa.String(length=120), nullable=True),
        sa.Column("value_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ap_payment_instruments_payment_id", "ap_payment_instruments", ["payment_id"])

    op.create_table(
        "ap_applications",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_id", sa.String(length=36), nullable=False),
        sa.Column("target_open_item_id", sa.String(length=36), sa.ForeignKey("ap_open_items.id"), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="VED"),
        sa.Column("rate", sa.Float(), nullable=True),
        sa.Column("date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="APPLIED"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ap_applications_company_id", "ap_applications", ["company_id"])
    op.create_index("ix_ap_applications_target_open_item_id", "ap_applications", ["target_open_item_id"])

    op.create_table(
        "ap_advances",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("party_id", sa.String(length=36), sa.ForeignKey("parties.id"), nullable=False),
        sa.Column("direction", sa.String(length=8), nullable=False, server_default="OUT"),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="VED"),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("available", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ap_advances_company_id", "ap_advances", ["company_id"])
    op.create_index("ix_ap_advances_party_id", "ap_advances", ["party_id"])

    op.create_table(
        "ap_payment_schedules",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("party_id", sa.String(length=36), sa.ForeignKey("parties.id"), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ap_payment_schedules_company_id", "ap_payment_schedules", ["company_id"])
    op.create_index("ix_ap_payment_schedules_party_id", "ap_payment_schedules", ["party_id"])

    op.create_table(
        "ap_withholdings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("party_id", sa.String(length=36), sa.ForeignKey("parties.id"), nullable=False),
        sa.Column("source_event", sa.String(length=200), nullable=True),
        sa.Column("tax_type", sa.String(length=16), nullable=False),
        sa.Column("rule_ref", sa.String(length=120), nullable=True),
        sa.Column("base", sa.Float(), nullable=False, server_default="0"),
        sa.Column("rate_ref", sa.String(length=120), nullable=True),
        sa.Column("amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("period", sa.String(length=20), nullable=True),
        sa.Column("certificate", sa.String(length=200), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="CALCULADA"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ap_withholdings_company_id", "ap_withholdings", ["company_id"])
    op.create_index("ix_ap_withholdings_party_id", "ap_withholdings", ["party_id"])


def downgrade() -> None:
    op.drop_table("ap_withholdings")
    op.drop_table("ap_payment_schedules")
    op.drop_table("ap_advances")
    op.drop_table("ap_applications")
    op.drop_table("ap_payment_instruments")
    op.drop_table("ap_payments")
    op.drop_table("ap_open_items")
    op.drop_table("supplier_credit_notes")
    op.drop_table("purchase_return_lines")
    op.drop_table("purchase_returns")
    op.drop_table("triple_matches")
    op.drop_table("supplier_invoice_lines")
    op.drop_table("supplier_invoices")
    op.drop_table("goods_receipt_lines")
    op.drop_table("goods_receipts")
    op.drop_table("purchase_order_lines")
    op.drop_table("purchase_orders")
    op.drop_table("supplier_quote_lines")
    op.drop_table("supplier_quotes")
    op.drop_table("purchase_requisition_lines")
    op.drop_table("purchase_requisitions")
