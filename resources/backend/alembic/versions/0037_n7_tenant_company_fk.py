"""N7 — la empresa también referencia donde es opcional.

Revision ID: 0037_n7_tenant_company_fk
Revises: 0036_n7_consistency

Nueve tablas de alcance tenant llevan `company_id` como **estrechamiento
opcional**: un rol puede valer en todo el tenant o solo en una empresa, una
moneda puede ser nacional o propia, un registro de idempotencia puede acotarse.

Que la columna admita nulo no la exime de referenciar a alguien real. Una
empresa nula significa «todas»; una empresa inventada no significa nada, y hasta
ahora las nueve la admitían.

Es la misma regla que 0033 aplicó a las tablas de empresa, en el sitio donde no
llegó porque se clasificó por alcance del modelo y estas son de tenant.
"""
from __future__ import annotations

from alembic import op

revision = "0037_n7_tenant_company_fk"
down_revision = "0036_n7_consistency"
branch_labels = None
depends_on = None

TABLAS = [
    "currencies",
    "exchange_rates",
    "idempotency_records",
    "legacy_document_references",
    "outbox_events",
    "report_definitions",
    "roles",
    "user_roles",
    "user_scopes",
]


def upgrade() -> None:
    for tabla in TABLAS:
        op.create_foreign_key(
            f"fk_{tabla}_company", tabla, "companies", ["company_id"], ["id"],
        )


def downgrade() -> None:
    for tabla in TABLAS:
        op.drop_constraint(f"fk_{tabla}_company", tabla, type_="foreignkey")
