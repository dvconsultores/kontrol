"""fusion gov proc06 landed cost

Une las dos ramas que salen de sus respectivas dependencias: las importaciones
(Enterprise) y las ofertas de contratación (PROC-06, Government). No cambia el
esquema: cada rama crea sus propias tablas.

Revision ID: 0089_fusion_gov_landed
Revises: 0088_gov_proc06_ofertas, 0088_importaciones_landed_cost
"""

from __future__ import annotations

revision = "0089_fusion_gov_landed"
down_revision = ("0088_gov_proc06_ofertas", "0088_importaciones_landed_cost")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
