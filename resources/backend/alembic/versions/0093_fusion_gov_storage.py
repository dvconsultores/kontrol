"""fusion gov proc07 evaluacion y storage classification

Une las dos ramas que salen de sus respectivas dependencias: la evaluacion
(PROC-07, Government) y la clasificacion de almacenamiento (Enterprise).
No cambia el esquema: cada rama crea sus propias tablas.

Revision ID: 0093_fusion_gov_storage
Revises: 0092_gov_proc07_evaluacion, 0092_storage_classification
"""

from __future__ import annotations

revision = "0093_fusion_gov_storage"
down_revision = ("0092_gov_proc07_evaluacion", "0092_storage_classification")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
