"""fusion backup org04

Une las dos ramas que salen de 0075: la política de copias (T052) y la ocupación de
cargos (ORG-04). No cambia el esquema: cada rama crea sus propias tablas.

Revision ID: 0077_fusion_backup_org04
Revises: 0076_backup_rpo, 0076_gov_org04_ocupacion
"""

from __future__ import annotations

revision = "0077_fusion_backup_org04"
down_revision = ("0076_backup_rpo", "0076_gov_org04_ocupacion")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
