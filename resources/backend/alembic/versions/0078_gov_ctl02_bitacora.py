"""agrega institutional_context a audit_events"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0078_gov_ctl02_bitacora"
down_revision = "0077_gov_org06_identidad"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "audit_events",
        sa.Column("institutional_context", sa.JSON(none_as_null=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("audit_events", "institutional_context")
