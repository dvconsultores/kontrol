"""PROC-08 × TRE-09: conversión de autoridad guardada en la decisión (columna nula, sin backfill)."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0115_gov_proc08_conversion"
down_revision = "0114_gov_tre09_tasas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("gov_procurement_decisions", sa.Column("conversion_autoridad", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("gov_procurement_decisions", "conversion_autoridad")
