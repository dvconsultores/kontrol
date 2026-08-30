"""Semántica de unidad en las 17 líneas transaccionales (Spec 011, F4).

Añade `uom_id`, `presentation_id`, `conversion_factor_snapshot`, la cantidad
base por cada cantidad y `uom_source` a las 17 tablas clasificadas
`MUST_HAVE_NOW` en `transaction-uom-impact-matrix.md`.

Las columnas nacen **nullable**. Forzar `NOT NULL` antes de resolver el
histórico obligaría a inventar un valor, que es justo lo que la Spec prohíbe: el
endurecimiento va después del backfill y solo con reporte limpio (plan §9).

Migración de **esquema pura**: válida en modo offline.

`inventory_balances`, `cost_layers` y `triple_matches` **no** reciben estas
columnas por diseño: son proyección, derivada y comparación, no cantidad
transaccional original (§18, CL-011-18).

Revision ID: 0021_line_uom_columns
Revises: 0020_quantity_numeric
Create Date: 2026-08-30
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0021_line_uom_columns"
down_revision = "0020_quantity_numeric"
branch_labels = None
depends_on = None

#: tabla -> cantidades que reciben su propia cantidad base. La unidad y la
#: presentación se declaran **una vez por línea**: permitir una unidad por
#: cantidad dejaría aceptar en cajas lo recibido en unidades (CL-011-14).
MUST_HAVE_NOW: dict[str, tuple[str, ...]] = {
    "inventory_movements": ("quantity",),
    "reservations": ("quantity",),
    "transfer_lines": ("quantity_sent", "quantity_received"),
    "stock_count_lines": ("expected_qty", "counted_qty"),
    "inventory_adjustments": ("quantity",),
    "purchase_requisition_lines": ("quantity",),
    "supplier_quote_lines": ("quantity",),
    "purchase_order_lines": ("quantity_ordered", "quantity_received"),
    "goods_receipt_lines": ("quantity_received", "quantity_accepted", "quantity_rejected"),
    "supplier_invoice_lines": ("quantity",),
    "purchase_return_lines": ("quantity",),
    "sales_quote_lines": ("quantity",),
    "sales_order_lines": ("quantity",),
    "pick_list_lines": ("quantity",),
    "shipment_lines": ("quantity",),
    "sales_invoice_lines": ("quantity",),
    "sales_return_lines": ("quantity",),
}

#: Documentos emitidos: congelan además símbolo y etiqueta para que una
#: reimpresión sea fiel sin consultar el maestro vigente (CL-011-17).
WITH_LABELS = ("sales_invoice_lines", "supplier_invoice_lines",
               "sales_return_lines", "shipment_lines")

#: Solo el contrato mínimo: cantidad autorizada por un permiso regulatorio
#: necesita unidad, no presentación comercial (§17).
CONTRACT_ONLY = ("permit_instances",)


def base_name(column: str) -> str:
    if column == "quantity":
        return "base_quantity"
    if column.startswith("quantity_"):
        return "base_quantity_" + column[len("quantity_"):]
    return "base_" + column


def upgrade() -> None:
    for table, quantities in MUST_HAVE_NOW.items():
        op.add_column(table, sa.Column("uom_id", sa.String(36),
                                       sa.ForeignKey("units_of_measure.id"), nullable=True))
        op.add_column(table, sa.Column("presentation_id", sa.String(36),
                                       sa.ForeignKey("presentations.id"), nullable=True))
        op.add_column(table, sa.Column("conversion_factor_snapshot", sa.Numeric(18, 6), nullable=True))
        for quantity in quantities:
            op.add_column(table, sa.Column(base_name(quantity), sa.Numeric(18, 6), nullable=True))
        op.add_column(table, sa.Column("uom_source", sa.String(24), nullable=True))
        if table in WITH_LABELS:
            op.add_column(table, sa.Column("uom_symbol_snapshot", sa.String(16), nullable=True))
            op.add_column(table, sa.Column("presentation_label_snapshot", sa.String(120), nullable=True))
        op.create_index(f"ix_{table}_uom_id", table, ["uom_id"])

    for table in CONTRACT_ONLY:
        op.add_column(table, sa.Column("uom_id", sa.String(36),
                                       sa.ForeignKey("units_of_measure.id"), nullable=True))
        op.create_index(f"ix_{table}_uom_id", table, ["uom_id"])


def downgrade() -> None:
    for table in CONTRACT_ONLY:
        op.drop_index(f"ix_{table}_uom_id", table_name=table)
        op.drop_column(table, "uom_id")
    for table, quantities in MUST_HAVE_NOW.items():
        op.drop_index(f"ix_{table}_uom_id", table_name=table)
        if table in WITH_LABELS:
            op.drop_column(table, "presentation_label_snapshot")
            op.drop_column(table, "uom_symbol_snapshot")
        op.drop_column(table, "uom_source")
        for quantity in quantities:
            op.drop_column(table, base_name(quantity))
        op.drop_column(table, "conversion_factor_snapshot")
        op.drop_column(table, "presentation_id")
        op.drop_column(table, "uom_id")
