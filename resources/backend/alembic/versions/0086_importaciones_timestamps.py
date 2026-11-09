"""Importaciones timestamps

Revision ID: 0086_importaciones_timestamps
Revises: 0084_fusion_importaciones_proc03
Create Date: 2024-01-01 00:00:00.000000
"""
import sqlalchemy as sa

from alembic import op

revision = "0086_importaciones_timestamps"
down_revision = "0084_fusion_importaciones_proc03"
branch_labels = None
depends_on = None

TABLAS = [
    "import_files",
    "import_documents",
    "import_tracking_events",
    "import_financial_links",
    "import_corrections",
]


def upgrade() -> None:
    for tabla in TABLAS:
        op.alter_column(
            tabla,
            "created_at",
            server_default=sa.func.now(),
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=False,
        )
        op.alter_column(
            tabla,
            "updated_at",
            server_default=sa.func.now(),
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=False,
        )


def downgrade() -> None:
    for tabla in TABLAS:
        op.alter_column(
            tabla,
            "created_at",
            server_default=None,
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=False,
        )
        op.alter_column(
            tabla,
            "updated_at",
            server_default=None,
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=False,
        )
