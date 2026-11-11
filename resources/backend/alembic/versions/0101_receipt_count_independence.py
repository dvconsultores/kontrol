"""Receipt count independence

Revision ID: 0101_receipt_count_independence
Revises: 0100_gov_ctl05_rendicion
Create Date: 2024-01-01 00:00:00.000000
"""
import sqlalchemy as sa

from alembic import op

revision = "0101_receipt_count_independence"
down_revision = "0100_gov_ctl05_rendicion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "companies",
        sa.Column(
            "receipt_count_same_user_allowed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("companies", "receipt_count_same_user_allowed")
