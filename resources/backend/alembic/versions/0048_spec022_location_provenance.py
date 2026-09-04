"""Spec 022 — el movimiento deja de suponer de qué ubicación salió la mercancía.

Un traslado físico necesita origen y destino. `inventory_movements` tenía una
sola `location_id`, que bastaba mientras nada se ubicaba: con el put-away deja de
bastar, y `recompute_balances` volvería a suponer, que es justo lo que la Spec
023 cerró para el estado de mercancía. Misma forma, misma razón.

Backfill: **no se inventa dirección.** La `location_id` histórica es la ubicación
sobre la que el motor escribió el saldo, y el signo de la cantidad dice si la
mercancía entró o salió de ella —es la convención del motor desde la Spec 003—.
Entradas y ceros: esa ubicación fue el destino. Salidas: fue el origen. Las filas
sin ubicación no se tocan: nunca tuvieron una.

Revision ID: 0048_spec022_location
Revises: 0047_spec021_confirm
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0048_spec022_location"
down_revision = "0047_spec021_confirm"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("inventory_movements",
                  sa.Column("source_location_id", sa.String(36), nullable=True))
    op.add_column("inventory_movements",
                  sa.Column("target_location_id", sa.String(36), nullable=True))
    op.create_foreign_key("fk_inventory_movements_source_location", "inventory_movements",
                          "warehouse_locations", ["source_location_id"], ["id"])
    op.create_foreign_key("fk_inventory_movements_target_location", "inventory_movements",
                          "warehouse_locations", ["target_location_id"], ["id"])

    conn = op.get_bind()
    con_ubicacion = conn.execute(sa.text(
        "SELECT count(*) FROM inventory_movements WHERE location_id IS NOT NULL")).scalar() or 0
    entradas = conn.execute(sa.text(
        "UPDATE inventory_movements SET target_location_id = location_id "
        "WHERE location_id IS NOT NULL AND quantity >= 0")).rowcount
    salidas = conn.execute(sa.text(
        "UPDATE inventory_movements SET source_location_id = location_id "
        "WHERE location_id IS NOT NULL AND quantity < 0")).rowcount

    print(f"[0048 spec022] movimientos con ubicación: {con_ubicacion}; "
          f"entradas: {entradas}; salidas: {salidas}")
    print("[0048 spec022] la dirección no se supone: la da el signo de la cantidad, que es la "
          "convención del motor desde la Spec 003. Las filas sin ubicación no se tocan")

    # Un traslado que no diga ni de dónde ni a dónde no es reconstruible. Se
    # admite que ambas sean nulas —el movimiento no toca ubicación— pero no que
    # haya `location_id` y ninguna de las dos.
    op.execute(
        "ALTER TABLE inventory_movements ADD CONSTRAINT "
        "ck_inventory_movements_location_provenance CHECK ("
        "location_id IS NULL "
        "OR source_location_id IS NOT NULL OR target_location_id IS NOT NULL)")


def downgrade() -> None:
    op.execute("ALTER TABLE inventory_movements "
               "DROP CONSTRAINT IF EXISTS ck_inventory_movements_location_provenance")
    op.drop_constraint("fk_inventory_movements_target_location", "inventory_movements",
                       type_="foreignkey")
    op.drop_constraint("fk_inventory_movements_source_location", "inventory_movements",
                       type_="foreignkey")
    op.drop_column("inventory_movements", "target_location_id")
    op.drop_column("inventory_movements", "source_location_id")
