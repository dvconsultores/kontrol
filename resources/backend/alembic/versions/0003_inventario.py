"""Inventario y logística (003-inventario-logistica).

Revision ID: 0003_inventario
Revises: 0002_maestros
Create Date: 2026-08-04
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0003_inventario"
down_revision = "0002_maestros"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # NOTA: `warehouses` y `locations` (custodia) ya se crean en 0001_fundacion
    # (módulo organization). Este módulo los reutiliza (CL-003-02).

    # ---------------- Tipos de movimiento (versionados, P8) ----------------
    op.create_table(
        "movement_types",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("affects_balance", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "code", name="uq_movement_types_company_code"),
    )
    op.create_index("ix_movement_types_company_id", "movement_types", ["company_id"])

    # ---------------- Movimientos (inmutables) ----------------
    op.create_table(
        "inventory_movements",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("warehouse_id", sa.String(length=36), sa.ForeignKey("warehouses.id"), nullable=False),
        sa.Column("location_id", sa.String(length=36), sa.ForeignKey("locations.id"), nullable=True),
        sa.Column("product_id", sa.String(length=36), sa.ForeignKey("catalog_items.id"), nullable=False),
        sa.Column("movement_type_id", sa.String(length=36), sa.ForeignKey("movement_types.id"), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("unit_id", sa.String(length=36), sa.ForeignKey("units_of_measure.id"), nullable=True),
        sa.Column("unit_cost", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="VED"),
        sa.Column("fiscal_rate", sa.Float(), nullable=True),
        sa.Column("document_ref", sa.String(length=200), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reversed_by_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="POSTED"),
        sa.Column("idempotency_key", sa.String(length=120), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inventory_movements_company_id", "inventory_movements", ["company_id"])
    op.create_index("ix_inventory_movements_warehouse_id", "inventory_movements", ["warehouse_id"])
    op.create_index("ix_inventory_movements_product_id", "inventory_movements", ["product_id"])
    op.create_index("ix_inventory_movements_idempotency_key", "inventory_movements", ["idempotency_key"])
    op.create_index("ix_inventory_movements_company_product", "inventory_movements", ["company_id", "product_id", "warehouse_id"])

    # ---------------- Lotes y seriales ----------------
    op.create_table(
        "inventory_lots",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("product_id", sa.String(length=36), sa.ForeignKey("catalog_items.id"), nullable=False),
        sa.Column("lot_number", sa.String(length=120), nullable=False),
        sa.Column("manufacture_date", sa.Date(), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("supplier_id", sa.String(length=36), nullable=True),
        sa.Column("receipt_ref", sa.String(length=200), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="DISPONIBLE"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "product_id", "lot_number", name="uq_inventory_lots_company_product_lot"),
    )
    op.create_index("ix_inventory_lots_company_id", "inventory_lots", ["company_id"])
    op.create_index("ix_inventory_lots_product_id", "inventory_lots", ["product_id"])
    op.create_index("ix_inventory_lots_expiry_date", "inventory_lots", ["expiry_date"])

    op.create_table(
        "product_serials",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("product_id", sa.String(length=36), sa.ForeignKey("catalog_items.id"), nullable=False),
        sa.Column("serial", sa.String(length=120), nullable=False),
        sa.Column("imei1", sa.String(length=40), nullable=True),
        sa.Column("imei2", sa.String(length=40), nullable=True),
        sa.Column("mac", sa.String(length=40), nullable=True),
        sa.Column("lot_id", sa.String(length=36), sa.ForeignKey("inventory_lots.id"), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="DISPONIBLE"),
        sa.Column("warehouse_id", sa.String(length=36), sa.ForeignKey("warehouses.id"), nullable=True),
        sa.Column("purchase_line_id", sa.String(length=36), nullable=True),
        sa.Column("sale_line_id", sa.String(length=36), nullable=True),
        sa.Column("warranty_until", sa.Date(), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "serial", name="uq_product_serials_company_serial"),
    )
    op.create_index("ix_product_serials_company_id", "product_serials", ["company_id"])
    op.create_index("ix_product_serials_product_id", "product_serials", ["product_id"])

    # ---------------- Balance (cache reconstruible) ----------------
    op.create_table(
        "inventory_balances",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("warehouse_id", sa.String(length=36), sa.ForeignKey("warehouses.id"), nullable=False),
        sa.Column("location_id", sa.String(length=36), nullable=True),
        sa.Column("product_id", sa.String(length=36), sa.ForeignKey("catalog_items.id"), nullable=False),
        sa.Column("lot_id", sa.String(length=36), nullable=True),
        sa.Column("serial_id", sa.String(length=36), nullable=True),
        sa.Column("state", sa.String(length=32), nullable=False, server_default="DISPONIBLE"),
        sa.Column("qty_on_hand", sa.Float(), nullable=False, server_default="0"),
        sa.Column("qty_reserved", sa.Float(), nullable=False, server_default="0"),
        sa.Column("qty_available", sa.Float(), nullable=False, server_default="0"),
        sa.Column("last_rebuilt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inventory_balances_company_id", "inventory_balances", ["company_id"])
    op.create_index("ix_inventory_balances_warehouse_id", "inventory_balances", ["warehouse_id"])
    op.create_index("ix_inventory_balances_product_id", "inventory_balances", ["product_id"])
    op.create_index("ix_inventory_balances_company_product_wh", "inventory_balances", ["company_id", "product_id", "warehouse_id", "state"])

    # ---------------- Reservas ----------------
    op.create_table(
        "reservations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("source_document", sa.String(length=200), nullable=True),
        sa.Column("product_id", sa.String(length=36), sa.ForeignKey("catalog_items.id"), nullable=False),
        sa.Column("warehouse_id", sa.String(length=36), sa.ForeignKey("warehouses.id"), nullable=False),
        sa.Column("lot_id", sa.String(length=36), nullable=True),
        sa.Column("serial_id", sa.String(length=36), nullable=True),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reservations_company_id", "reservations", ["company_id"])
    op.create_index("ix_reservations_product_id", "reservations", ["product_id"])
    op.create_index("ix_reservations_warehouse_id", "reservations", ["warehouse_id"])

    # ---------------- Transferencias ----------------
    op.create_table(
        "transfers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("origin_warehouse_id", sa.String(length=36), sa.ForeignKey("warehouses.id"), nullable=False),
        sa.Column("destination_warehouse_id", sa.String(length=36), sa.ForeignKey("warehouses.id"), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("request_ref", sa.String(length=200), nullable=True),
        sa.Column("shipment_ref", sa.String(length=200), nullable=True),
        sa.Column("receipt_ref", sa.String(length=200), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="DRAFT"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transfers_company_id", "transfers", ["company_id"])

    op.create_table(
        "transfer_lines",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("transfer_id", sa.String(length=36), sa.ForeignKey("transfers.id"), nullable=False),
        sa.Column("product_id", sa.String(length=36), sa.ForeignKey("catalog_items.id"), nullable=False),
        sa.Column("lot_id", sa.String(length=36), nullable=True),
        sa.Column("serial_id", sa.String(length=36), nullable=True),
        sa.Column("quantity_sent", sa.Float(), nullable=False),
        sa.Column("quantity_received", sa.Float(), nullable=True),
        sa.Column("difference", sa.Float(), nullable=True),
        sa.Column("destination_state", sa.String(length=32), nullable=False, server_default="DISPONIBLE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transfer_lines_transfer_id", "transfer_lines", ["transfer_id"])

    # ---------------- Conteos ----------------
    op.create_table(
        "stock_counts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("warehouse_id", sa.String(length=36), sa.ForeignKey("warehouses.id"), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("plan_ref", sa.String(length=200), nullable=True),
        sa.Column("scope", sa.JSON(), nullable=False),
        sa.Column("freeze_policy", sa.String(length=32), nullable=False, server_default="PER_PRODUCT"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="DRAFT"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_stock_counts_company_id", "stock_counts", ["company_id"])

    op.create_table(
        "stock_count_lines",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("count_id", sa.String(length=36), sa.ForeignKey("stock_counts.id"), nullable=False),
        sa.Column("product_id", sa.String(length=36), sa.ForeignKey("catalog_items.id"), nullable=False),
        sa.Column("location_id", sa.String(length=36), nullable=True),
        sa.Column("lot_id", sa.String(length=36), nullable=True),
        sa.Column("expected_qty", sa.Float(), nullable=False, server_default="0"),
        sa.Column("counted_qty", sa.Float(), nullable=True),
        sa.Column("variance", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_stock_count_lines_count_id", "stock_count_lines", ["count_id"])

    # ---------------- Ajustes ----------------
    op.create_table(
        "inventory_adjustments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("warehouse_id", sa.String(length=36), sa.ForeignKey("warehouses.id"), nullable=False),
        sa.Column("product_id", sa.String(length=36), sa.ForeignKey("catalog_items.id"), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("evidence_ref", sa.String(length=255), nullable=True),
        sa.Column("unit_cost", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="VED"),
        sa.Column("approver_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="DRAFT"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inventory_adjustments_company_id", "inventory_adjustments", ["company_id"])

    # ---------------- Costos ----------------
    op.create_table(
        "cost_layers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=False),
        sa.Column("product_id", sa.String(length=36), sa.ForeignKey("catalog_items.id"), nullable=False),
        sa.Column("warehouse_id", sa.String(length=36), sa.ForeignKey("warehouses.id"), nullable=False),
        sa.Column("receipt_ref", sa.String(length=200), nullable=True),
        sa.Column("quantity_in", sa.Float(), nullable=False),
        sa.Column("quantity_remaining", sa.Float(), nullable=False),
        sa.Column("unit_cost", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="VED"),
        sa.Column("fiscal_rate", sa.Float(), nullable=True),
        sa.Column("landed_cost", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="OPEN"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cost_layers_company_id", "cost_layers", ["company_id"])
    op.create_index("ix_cost_layers_product_id", "cost_layers", ["product_id"])
    op.create_index("ix_cost_layers_warehouse_id", "cost_layers", ["warehouse_id"])

    op.create_table(
        "costing_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.String(length=36), nullable=True),
        sa.Column("product_id", sa.String(length=36), sa.ForeignKey("catalog_items.id"), nullable=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("method", sa.String(length=16), nullable=False, server_default="AVERAGE"),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="VED"),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_costing_profiles_company_id", "costing_profiles", ["company_id"])


def downgrade() -> None:
    op.drop_table("costing_profiles")
    op.drop_table("cost_layers")
    op.drop_table("inventory_adjustments")
    op.drop_table("stock_count_lines")
    op.drop_table("stock_counts")
    op.drop_table("transfer_lines")
    op.drop_table("transfers")
    op.drop_table("reservations")
    op.drop_table("inventory_balances")
    op.drop_table("product_serials")
    op.drop_table("inventory_lots")
    op.drop_table("inventory_movements")
    op.drop_table("movement_types")
