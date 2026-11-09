"""fusion importaciones proc03

Une las dos ramas que salen de sus respectivas dependencias: las importaciones
(Enterprise) y los expedientes de contratación (CTL/PROC-03, Government). No
cambia el esquema: cada rama crea sus propias tablas.

Revision ID: 0084_fusion_importaciones_proc03
Revises: 0083_fusion_importaciones_proc02, 0080_gov_proc03_expedientes
"""

from __future__ import annotations

revision = "0084_fusion_importaciones_proc03"
down_revision = ("0083_fusion_importaciones_proc02", "0080_gov_proc03_expedientes")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
