"""Spec 034 — la factura aprende de qué pedido viene, y un pedido no se factura dos veces.

`B-007` del backlog maestro lo pedía en estos términos: «factura trazable a su
pedido; migración **aditiva con FK nullable**; nueva factura exige orden; **no se
puede facturar dos veces la misma orden**». Las facturas históricas no tienen
pedido y no se les inventa uno: por eso la columna nace anulable. Lo que impide
la doble facturación es el índice único parcial, no la buena voluntad del
servicio.

`B-060` pedía la compuerta: «solo se factura un pedido `CONFIRMED`; solicitud de
facturación explícita». La solicitud es el estado `READY_FOR_BILLING` que declara
`ADR-D0-012`; sus sellos —quién la pidió y cuándo— van en el pedido, que es donde
se puede auditar quién autorizó qué.

Revision ID: 0052_spec034_billing
Revises: 0051_spec033_confirm
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0052_spec034_billing"
down_revision = "0051_spec033_confirm"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- la factura, atada a su origen ---
    op.add_column("sales_invoices", sa.Column("order_id", sa.String(36), nullable=True))
    op.add_column("sales_invoices", sa.Column("confirmation_id", sa.String(36), nullable=True))
    op.add_column("sales_invoices", sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("sales_invoices", sa.Column("fiscal_document_id", sa.String(36), nullable=True))
    op.add_column("sales_invoices", sa.Column("control_number", sa.String(64), nullable=True))
    op.create_foreign_key("fk_sales_invoices_order", "sales_invoices", "sales_orders",
                          ["order_id"], ["id"])
    op.create_foreign_key("fk_sales_invoices_confirmation", "sales_invoices", "order_confirmations",
                          ["confirmation_id"], ["id"])
    op.create_index("ix_sales_invoices_order_id", "sales_invoices", ["order_id"])
    # Un pedido, una factura viva. Cancelar un borrador libera el pedido; anular
    # una factura ya emitida **no**, porque eso es una corrección fiscal y su
    # dueña es la Spec 036.
    op.execute("CREATE UNIQUE INDEX uq_sales_invoices_order ON sales_invoices (order_id) "
               "WHERE order_id IS NOT NULL AND status <> 'CANCELLED'")

    # --- la solicitud de facturación, auditable ---
    op.add_column("sales_orders", sa.Column("billing_requested_at", sa.DateTime(timezone=True),
                                            nullable=True))
    op.add_column("sales_orders", sa.Column("billing_requested_by", sa.String(36), nullable=True))
    op.add_column("sales_orders", sa.Column("invoiced_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    for col in ("invoiced_at", "billing_requested_by", "billing_requested_at"):
        op.drop_column("sales_orders", col)
    op.execute("DROP INDEX IF EXISTS uq_sales_invoices_order")
    op.drop_index("ix_sales_invoices_order_id", table_name="sales_invoices")
    op.drop_constraint("fk_sales_invoices_confirmation", "sales_invoices", type_="foreignkey")
    op.drop_constraint("fk_sales_invoices_order", "sales_invoices", type_="foreignkey")
    for col in ("control_number", "fiscal_document_id", "issued_at", "confirmation_id", "order_id"):
        op.drop_column("sales_invoices", col)
