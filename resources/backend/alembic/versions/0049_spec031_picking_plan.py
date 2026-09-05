"""Spec 031 — el plan de picking aprende a decir de dónde se recoge y en qué orden.

`pick_list_lines` tenía producto y cantidad y nada más: no podía expresar «recoge
esto de aquí, y de aquí antes que de allí», que es el objeto entero de la Spec
031. Se le añaden la línea de pedido que satisface, la ubicación de origen, el
estado de mercancía —para parear con la identidad exacta del saldo— y el puesto
en el recorrido.

`pick_lists` gana el ciclo de vida que `D0-15` decidió: cinco estados con `CHECK`,
sellos de confirmación, cancelación e invalidación, y motivo.

**No hay backfill.** Las columnas nacen anulables porque el esqueleto anterior
pudo crear líneas sin ubicación y una migración no inventa historia: no existe
dato del que deducir de qué ubicación salió una línea que nunca la tuvo. La
restricción `pick_list_line_allocation_shape` no exige que estén; exige que, si
están, estén las cuatro. El servicio no crea asignaciones a medias.

El índice único parcial impide que un pedido tenga dos planes vivos: dos
almacenistas asignando la misma demanda por separado la comprometerían dos veces.

Revision ID: 0049_spec031_picking
Revises: 0048_spec022_location
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0049_spec031_picking"
down_revision = "0048_spec022_location"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- ciclo de vida del plan ---
    op.add_column("pick_lists", sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("pick_lists", sa.Column("confirmed_by", sa.String(36), nullable=True))
    op.add_column("pick_lists", sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("pick_lists", sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("pick_lists", sa.Column("status_reason", sa.Text(), nullable=True))
    op.create_check_constraint(
        "pick_list_status", "pick_lists",
        "status IN ('DRAFT', 'CONFIRMED', 'CLOSED', 'CANCELLED', 'INVALIDATED')")
    op.execute(
        "CREATE UNIQUE INDEX uq_pick_lists_active_order ON pick_lists (order_id) "
        "WHERE status IN ('DRAFT', 'CONFIRMED')")

    # --- asignación por ubicación ---
    op.add_column("pick_list_lines", sa.Column("order_line_id", sa.String(36), nullable=True))
    op.add_column("pick_list_lines", sa.Column("location_id", sa.String(36), nullable=True))
    op.add_column("pick_list_lines", sa.Column("state", sa.String(32), nullable=True))
    op.add_column("pick_list_lines", sa.Column("sequence", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_pick_list_lines_order_line", "pick_list_lines", "sales_order_lines",
                          ["order_line_id"], ["id"])
    op.create_foreign_key("fk_pick_list_lines_location", "pick_list_lines", "warehouse_locations",
                          ["location_id"], ["id"])
    op.create_index("ix_pick_list_lines_location_id", "pick_list_lines", ["location_id"])
    op.create_index("ix_pick_list_lines_order_line_id", "pick_list_lines", ["order_line_id"])
    op.create_check_constraint(
        "pick_list_line_allocation_shape", "pick_list_lines",
        "(location_id IS NULL AND sequence IS NULL AND state IS NULL) OR "
        "(location_id IS NOT NULL AND sequence IS NOT NULL AND state IS NOT NULL "
        " AND base_quantity IS NOT NULL)")


def downgrade() -> None:
    op.drop_constraint("pick_list_line_allocation_shape", "pick_list_lines", type_="check")
    op.drop_index("ix_pick_list_lines_order_line_id", table_name="pick_list_lines")
    op.drop_index("ix_pick_list_lines_location_id", table_name="pick_list_lines")
    op.drop_constraint("fk_pick_list_lines_location", "pick_list_lines", type_="foreignkey")
    op.drop_constraint("fk_pick_list_lines_order_line", "pick_list_lines", type_="foreignkey")
    for col in ("sequence", "state", "location_id", "order_line_id"):
        op.drop_column("pick_list_lines", col)
    op.execute("DROP INDEX IF EXISTS uq_pick_lists_active_order")
    op.drop_constraint("pick_list_status", "pick_lists", type_="check")
    for col in ("status_reason", "invalidated_at", "cancelled_at", "confirmed_by", "confirmed_at"):
        op.drop_column("pick_lists", col)
