"""Terceros: versión optimista y validez bancaria."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0078_terceros_version"
down_revision = "0077_fusion_backup_org04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("parties", sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"))
    op.add_column("party_addresses", sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"))
    op.add_column("party_contacts", sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"))
    op.add_column("party_bank_accounts", sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"))
    op.add_column(
        "party_bank_accounts",
        sa.Column("validity", sa.String(length=32), nullable=False, server_default="ACTIVE"),
    )
    op.add_column("customers", sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"))
    op.add_column("suppliers", sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"))
    op.add_column("carriers", sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"))
    op.add_column("drivers", sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"))


def downgrade() -> None:
    op.drop_column("drivers", "version")
    op.drop_column("carriers", "version")
    op.drop_column("suppliers", "version")
    op.drop_column("customers", "version")
    op.drop_column("party_bank_accounts", "validity")
    op.drop_column("party_bank_accounts", "version")
    op.drop_column("party_contacts", "version")
    op.drop_column("party_addresses", "version")
    op.drop_column("parties", "version")
