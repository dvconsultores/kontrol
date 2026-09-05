"""Spec 032 — el plan aprende a distinguir lo que se planificó de lo que se recogió.

Un plan decía cuánto había que recoger de cada ubicación. No tenía dónde anotar
cuánto se recogió **de verdad**, y sobrescribir la cantidad planificada habría
borrado la intención: sin las dos cifras no hay diferencia que registrar, y el
proceso fuente es explícito en que la diferencia debe registrarse (¶47) y que el
pedido «no debería simplemente modificarse sin dejar evidencia» (¶53).

Los cinco motivos de diferencia no se inventan: son los del ¶48-52 del proceso.

`reservations.picked_base_quantity` es el delta dirigido sobre la Spec 030. El
contador `qty_reserved` significa, según el vocabulario que fijó `D0-03` §0,
«unidades comprometidas **y aún no extraídas**». Extraer lo baja; el despacho no
puede volver a restar lo ya extraído, o al despachar el primer pedido borraría
del contador el compromiso del segundo.

Revision ID: 0050_spec032_pick
Revises: 0049_spec031_picking
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0050_spec032_pick"
down_revision = "0049_spec031_picking"
branch_labels = None
depends_on = None

MOTIVOS = ("PRODUCTO_NO_LOCALIZADO", "CANTIDAD_INSUFICIENTE", "UBICACION_INCORRECTA",
           "DIFERENCIA_SISTEMA_FISICO", "MERCANCIA_DANADA")


def upgrade() -> None:
    # --- el hecho físico, separado de la intención ---
    op.add_column("pick_list_lines", sa.Column("picked_base_quantity", sa.Numeric(18, 6), nullable=True))
    op.add_column("pick_list_lines", sa.Column("picked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("pick_list_lines", sa.Column("picked_by", sa.String(36), nullable=True))
    op.add_column("pick_list_lines", sa.Column("discrepancy_kind", sa.String(32), nullable=True))
    op.add_column("pick_list_lines", sa.Column("discrepancy_note", sa.Text(), nullable=True))
    op.create_check_constraint(
        "pick_list_line_discrepancy_kind", "pick_list_lines",
        "discrepancy_kind IS NULL OR discrepancy_kind IN "
        "('" + "', '".join(MOTIVOS) + "')")
    # Recoger de menos exige motivo: es la evidencia que pide el ¶53.
    op.create_check_constraint(
        "pick_list_line_shortfall_reason", "pick_list_lines",
        "picked_base_quantity IS NULL OR base_quantity IS NULL "
        "OR picked_base_quantity >= base_quantity OR discrepancy_kind IS NOT NULL")
    op.create_check_constraint(
        "pick_list_line_picked_not_negative", "pick_list_lines",
        "picked_base_quantity IS NULL OR picked_base_quantity >= 0")

    # --- consolidación: el pedido concentrado y trasladado ---
    op.add_column("pick_lists", sa.Column("consolidated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("pick_lists", sa.Column("consolidated_by", sa.String(36), nullable=True))
    op.add_column("pick_lists", sa.Column("consolidation_location_id", sa.String(36), nullable=True))
    op.create_foreign_key("fk_pick_lists_consolidation_location", "pick_lists", "warehouse_locations",
                          ["consolidation_location_id"], ["id"])

    # --- delta dirigido Spec 030: lo ya extraído de cada reserva ---
    op.add_column("reservations", sa.Column("picked_base_quantity", sa.Numeric(18, 6),
                                            nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("reservations", "picked_base_quantity")
    op.drop_constraint("fk_pick_lists_consolidation_location", "pick_lists", type_="foreignkey")
    for col in ("consolidation_location_id", "consolidated_by", "consolidated_at"):
        op.drop_column("pick_lists", col)
    for c in ("pick_list_line_picked_not_negative", "pick_list_line_shortfall_reason",
              "pick_list_line_discrepancy_kind"):
        op.drop_constraint(c, "pick_list_lines", type_="check")
    for col in ("discrepancy_note", "discrepancy_kind", "picked_by", "picked_at",
                "picked_base_quantity"):
        op.drop_column("pick_list_lines", col)
