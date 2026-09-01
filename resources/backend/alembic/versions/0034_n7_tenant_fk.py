"""N7 — el tenant también deja de ser una cadena suelta.

Revision ID: 0034_n7_tenant_fk
Revises: 0033_n7_company_fk

Tres tablas de alcance tenant guardan `tenant_id` sin referencia: `users`,
`audit_events` y `outbox_events`. Las tres son infraestructura —quién entra, qué
hizo y qué se publicó—, y precisamente por eso importan: un rastro que apunta a
un tenant inexistente es un rastro ilegible.

`audit_events` y `outbox_events` admiten nulo porque hay acciones anteriores a
conocer el tenant (el arranque de la instalación); la referencia se añade
igualmente, porque un tenant nulo es distinto de un tenant inventado.
"""
from __future__ import annotations

from alembic import op

revision = "0034_n7_tenant_fk"
down_revision = "0033_n7_company_fk"
branch_labels = None
depends_on = None

#: `system_settings` entra aquí porque un ajuste puede ser de la instalación
#: entera o de un tenant concreto, y en el segundo caso ese tenant debe existir.
TABLAS = ["users", "audit_events", "outbox_events", "system_settings"]


def upgrade() -> None:
    for tabla in TABLAS:
        op.create_foreign_key(
            f"fk_{tabla}_tenant", tabla, "tenants", ["tenant_id"], ["id"],
        )
    # La auditoría guarda tenant y empresa a la vez, deliberadamente: debe poder
    # responder «en qué instalación» y «en qué empresa». Desde N5 el tenant se
    # deduce de la empresa al registrarlo, así que no pueden contradecirse.
    op.create_foreign_key(
        "fk_audit_events_company", "audit_events", "companies", ["company_id"], ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_audit_events_company", "audit_events", type_="foreignkey")
    for tabla in TABLAS:
        op.drop_constraint(f"fk_{tabla}_tenant", tabla, type_="foreignkey")
