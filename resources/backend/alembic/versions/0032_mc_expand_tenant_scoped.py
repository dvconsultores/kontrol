"""Alcance de tenant: la columna pasa a llamarse lo que guarda (ARCH-MC-001, N3).

Estas tablas **sí** son del tenant. Su problema no es de pertenencia sino de
nombre: llevan una columna `company_id` que contiene un `tenant_id`. Aquí se
añade `tenant_id` con clave foránea real y vacía; el traslado del valor y la
retirada de la columna falsa llegan en el backfill y en la contracción.

No se convierten en entidades de empresa: compartirlas entre las empresas de un
tenant es una decisión funcional, no un descuido.

Revision ID: 0032_mc_expand_tenant_scoped
Revises: 0031_mc_expand_regulatory
Create Date: 2026-08-31
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0032_mc_expand_tenant_scoped"
down_revision = "0031_mc_expand_regulatory"
branch_labels = None
depends_on = None

#: `outbox_events` queda fuera: ya tiene `tenant_id` propio. Su `company_id`
#: guarda el tenant y se retirará en la contracción, no aquí.
TABLAS = (
    "currencies",
    "exchange_rates",
    "idempotency_records",
    "legacy_document_references",
    "report_definitions",
)


def upgrade() -> None:
    for tabla in TABLAS:
        op.add_column(tabla, sa.Column("tenant_id", sa.String(36), nullable=True))
        op.create_foreign_key(f"fk_{tabla}_tenant_id", tabla, "tenants", ["tenant_id"], ["id"])


def downgrade() -> None:
    for tabla in TABLAS:
        op.drop_constraint(f"fk_{tabla}_tenant_id", tabla, type_="foreignkey")
        op.drop_column(tabla, "tenant_id")
