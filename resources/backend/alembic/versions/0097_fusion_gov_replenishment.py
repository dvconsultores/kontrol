"""Fusión de cabezas: PROC-10 (gobierno) y detección automática de reposición (Spec 015)

Une las dos ramas que salen de sus respectivas dependencias: la garantía
(PROC-10, Government) y la detección de reposición (Enterprise).
No cambia el esquema: cada rama crea sus propias tablas.

Revision ID: 0097_fusion_gov_replenishment
Revises: 0096_gov_proc10_garantias, 0096_replenishment_detection
"""

from __future__ import annotations

revision = "0097_fusion_gov_replenishment"
down_revision = ("0096_gov_proc10_garantias", "0096_replenishment_detection")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
