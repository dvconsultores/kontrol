"""fusion terceros org06

Une la versión de terceros (Enterprise) con la identidad institucional (ORG-06,
Government). No cambia el esquema: cada rama crea sus propias tablas.

Revision ID: 0079_fusion_terceros_org06
Revises: 0078_terceros_version, 0077_gov_org06_identidad
"""

from __future__ import annotations

revision = "0079_fusion_terceros_org06"
down_revision = ("0078_terceros_version", "0077_gov_org06_identidad")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
