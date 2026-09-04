"""Spec 023 — el movimiento deja de suponer el estado de la mercancía.

`ADR-D0-010` v2 R-D0-10-5 exige que el saldo se reconstruya desde el ledger. Con
saldos en varios estados eso era imposible: `inventory_movements` no guardaba
ninguno, y `recompute_balances` fijaba `DISPONIBLE` para todos porque era lo
único coherente que podía hacer con lo que tenía.

Backfill: **no se inventa historia.** Hasta esta migración `record_movement`
escribía el saldo con `state="DISPONIBLE"` fijo —es comprobable en el código de
todas las versiones anteriores—, así que la procedencia histórica no se deduce:
se conoce. Las entradas tuvieron `DISPONIBLE` por destino y las salidas por
origen. Ninguna fila queda ambigua y ninguna se reinterpreta.

Revision ID: 0046_spec023_state
Revises: 0045_spec020_incidents
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0046_spec023_state"
down_revision = "0045_spec020_incidents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("inventory_movements", sa.Column("source_state", sa.String(32), nullable=True))
    op.add_column("inventory_movements", sa.Column("target_state", sa.String(32), nullable=True))

    conn = op.get_bind()
    total = conn.execute(sa.text("SELECT count(*) FROM inventory_movements")).scalar() or 0

    # Entradas y salidas por el signo de la cantidad, que es la convención del
    # motor desde la Spec 003. El cero cuenta como entrada: `record_movement` no
    # lo emite, pero el histórico tiene filas en cero —conversiones de tipo,
    # correcciones— y todas tocaron la fila `DISPONIBLE` como destino, sumándole
    # cero. Dejarlas fuera las volvería inclasificables y abortaría la migración.
    entradas = conn.execute(sa.text(
        "UPDATE inventory_movements SET target_state = 'DISPONIBLE' WHERE quantity >= 0")).rowcount
    salidas = conn.execute(sa.text(
        "UPDATE inventory_movements SET source_state = 'DISPONIBLE' WHERE quantity < 0")).rowcount

    print(f"[0046 spec023] movimientos existentes: {total}; "
          f"entradas clasificadas: {entradas}; salidas clasificadas: {salidas}")
    print("[0046 spec023] la clasificación no es una suposición: hasta esta migración el motor "
          "escribía el saldo con state='DISPONIBLE' fijo, sin excepción ni parámetro")

    ambiguas = conn.execute(sa.text(
        "SELECT count(*) FROM inventory_movements "
        "WHERE source_state IS NULL AND target_state IS NULL")).scalar() or 0
    if ambiguas:
        raise RuntimeError(
            f"{ambiguas} movimientos quedarían sin procedencia de estado. La restricción los "
            "rechazaría y clasificarlos a ciegas sería falsificar historia: revisar antes de migrar.")

    op.execute(
        "ALTER TABLE inventory_movements ADD CONSTRAINT ck_inventory_movements_state_provenance "
        "CHECK (source_state IS NOT NULL OR target_state IS NOT NULL)")


def downgrade() -> None:
    op.execute("ALTER TABLE inventory_movements "
               "DROP CONSTRAINT IF EXISTS ck_inventory_movements_state_provenance")
    op.execute("ALTER TABLE inventory_movements "
               "DROP CONSTRAINT IF EXISTS ck_inventory_movements_ck_inventory_movements_state_provenance")
    op.drop_column("inventory_movements", "target_state")
    op.drop_column("inventory_movements", "source_state")
