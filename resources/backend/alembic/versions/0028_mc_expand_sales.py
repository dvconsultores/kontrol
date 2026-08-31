"""Expansión de alcance multiempresa — ventas (ARCH-MC-001, fase N3).

Solo esquema. **No toca un solo dato.** Añade dos columnas vacías por tabla:

- `legacy_scope_id` guardará el valor original de `company_id` —que hoy contiene
  el `tenant_id`— cuando el backfill lo sustituya por la empresa real. Se crea
  ahora, vacía, para que la evidencia tenga dónde ir antes de que haga falta.
- `scope_backfill_class` registrará la clase `MC-A`..`MC-E` con la que cada fila
  se clasificó, de modo que la decisión quede en el dato y no en un informe suelto.

Ninguna de las dos se rellena aquí. Reinterpretar `company_id` antes de haber
demostrado la reconstrucción sería destruir la única evidencia que queda de a
quién pertenecía la fila.

Revision ID: 0028_mc_expand_sales
Revises: 0027_mc_expand_inventory
Create Date: 2026-08-31
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0028_mc_expand_sales"
down_revision = "0027_mc_expand_inventory"
branch_labels = None
depends_on = None

#: Tablas de alcance de empresa cuyo `company_id` todavía guarda el tenant.
TABLAS = (
    "pick_lists",
    "sales_credit_notes",
    "sales_debit_notes",
    "sales_invoices",
    "sales_orders",
    "sales_quotes",
    "sales_returns",
    "shipments",
)


def upgrade() -> None:
    for tabla in TABLAS:
        op.add_column(tabla, sa.Column("legacy_scope_id", sa.String(36), nullable=True))
        op.add_column(tabla, sa.Column("scope_backfill_class", sa.String(8), nullable=True))


def downgrade() -> None:
    for tabla in TABLAS:
        op.drop_column(tabla, "scope_backfill_class")
        op.drop_column(tabla, "legacy_scope_id")
