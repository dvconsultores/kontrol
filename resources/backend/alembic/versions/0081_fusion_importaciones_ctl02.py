"""fusion importaciones ctl02

Une las dos ramas que salen de sus respectivas dependencias: las importaciones
(Enterprise) y la bitácora institucional (CTL-02, Government). No cambia el
esquema: cada rama crea sus propias tablas.

Revision ID: 0081_fusion_importaciones_ctl02
Revises: 0080_importaciones, 0078_gov_ctl02_bitacora
"""

from __future__ import annotations

revision = "0081_fusion_importaciones_ctl02"
down_revision = ("0080_importaciones", "0078_gov_ctl02_bitacora")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
