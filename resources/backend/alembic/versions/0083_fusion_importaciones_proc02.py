"""fusion importaciones proc02

Une las dos ramas que salen de sus respectivas dependencias: las importaciones
(Enterprise) y las comisiones (CTL/PROC-02, Government). No cambia el
esquema: cada rama crea sus propias tablas.

Revision ID: 0083_fusion_importaciones_proc02
Revises: 0082_importaciones_seguimiento, 0079_gov_proc02_comisiones
"""

from __future__ import annotations

revision = "0083_fusion_importaciones_proc02"
down_revision = ("0082_importaciones_seguimiento", "0079_gov_proc02_comisiones")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
