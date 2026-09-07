"""Spec 035 — el despacho aprende a decir con qué factura sale y quién se la lleva.

`validate_shipment` prometía en su docstring bloquear el despacho cuando faltara
un requisito, y su cuerpo aprobaba siempre. La evaluación regulatoria que sí
sabe decidir —`regulatory.evaluate_shipment`— existía y nadie la llamaba desde
el despacho. Esta migración añade lo que hacía falta para que la compuerta pueda
guardar de qué se pronunció.

El ¶106 dice que «la mercancía sale del almacén **con su factura**»: por eso el
despacho guarda cuál. Las columnas nacen anulables porque los despachos
anteriores no la tienen y una migración no inventa historia.

Revision ID: 0053_spec035_dispatch
Revises: 0052_spec034_billing
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0053_spec035_dispatch"
down_revision = "0052_spec034_billing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("shipments", sa.Column("invoice_id", sa.String(36), nullable=True))
    op.add_column("shipments", sa.Column("vehicle_id", sa.String(36), nullable=True))
    op.add_column("shipments", sa.Column("driver_id", sa.String(36), nullable=True))
    op.add_column("shipments", sa.Column("regulatory_status", sa.String(32), nullable=True))
    op.add_column("shipments", sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("shipments", sa.Column("validated_by", sa.String(36), nullable=True))
    op.add_column("shipments", sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("shipments", sa.Column("dispatched_by", sa.String(36), nullable=True))
    op.create_foreign_key("fk_shipments_invoice", "shipments", "sales_invoices",
                          ["invoice_id"], ["id"])
    op.create_foreign_key("fk_shipments_vehicle", "shipments", "transport_vehicles",
                          ["vehicle_id"], ["id"])
    op.create_foreign_key("fk_shipments_driver", "shipments", "transport_drivers",
                          ["driver_id"], ["id"])
    op.create_index("ix_shipments_invoice_id", "shipments", ["invoice_id"])
    # Un pedido no sale dos veces. Cancelar un despacho libera el pedido; haberlo
    # despachado, no: deshacer una salida física es una devolución, y su dueña
    # es la Spec 036.
    op.execute("CREATE UNIQUE INDEX uq_shipments_live_order ON shipments (order_id) "
               "WHERE status <> 'CANCELLED'")
    op.create_check_constraint(
        "shipment_regulatory_status", "shipments",
        "regulatory_status IS NULL OR regulatory_status IN ('CLEARED', 'BLOCKED')")


def downgrade() -> None:
    op.drop_constraint("shipment_regulatory_status", "shipments", type_="check")
    op.execute("DROP INDEX IF EXISTS uq_shipments_live_order")
    op.drop_index("ix_shipments_invoice_id", table_name="shipments")
    for fk in ("fk_shipments_driver", "fk_shipments_vehicle", "fk_shipments_invoice"):
        op.drop_constraint(fk, "shipments", type_="foreignkey")
    for col in ("dispatched_by", "dispatched_at", "validated_by", "validated_at",
                "regulatory_status", "driver_id", "vehicle_id", "invoice_id"):
        op.drop_column("shipments", col)
