"""Fusión de cabezas: PROC-08 (gobierno) y planificación de abastecimiento (Spec 015)

Une las dos ramas que salen de sus respectivas dependencias: la decisión
(PROC-08, Government) y la planificación de abastecimiento (Enterprise).
No cambia el esquema: cada rama crea sus propias tablas.

Revision ID: 0095_fusion_gov_planning
Revises: 0094_gov_proc08_decision, 0094_supply_planning
"""

from __future__ import annotations

revision = "0095_fusion_gov_planning"
down_revision = ("0094_gov_proc08_decision", "0094_supply_planning")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
