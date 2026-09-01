"""N8 — se retiran las columnas de la transición.

Revision ID: 0038_n8_drop_legacy_scope
Revises: 0037_n7_tenant_company_fk

`legacy_scope_id` y `scope_backfill_class` se añadieron en N3 a 80 tablas como
red de seguridad para un backfill: guardarían el valor anterior y la
clasificación de cada fila mientras se reconstruía la empresa.

Ese backfill **nunca hizo falta**. No existe ninguna instalación desplegada, así
que la ventana se cerró antes de que hubiera nada que reconstruir, y las dos
columnas quedaron vacías desde el día que se crearon.

Nunca llegaron al modelo: ningún modelo las declaró, ningún servicio las leyó,
ninguna prueba las usó. Retirarlas es un `DROP` limpio, no una desconexión.

La capacidad de migrar una instalación heredada **no depende de ellas**: vive en
`app/core/mc`, que analiza el catálogo de la base destino y no estas columnas.
Esa capacidad se comprueba con el fixture hostil, que N8 convirtió en artefacto
reproducible precisamente para que no se pierda.

El `downgrade` las restituye vacías. Una instalación que revirtiera necesitaría
el esquema anterior completo, aunque su contenido nunca tuvo información.
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0038_n8_drop_legacy_scope"
down_revision = "0037_n7_tenant_company_fk"
branch_labels = None
depends_on = None

TABLAS = [
    "ap_advances",
    "ap_applications",
    "ap_open_items",
    "ap_payment_schedules",
    "ap_payments",
    "ap_withholdings",
    "approval_events",
    "attribute_definitions",
    "bank_transactions",
    "cash_sessions",
    "cashboxes",
    "catalog_items",
    "control_number_batches",
    "control_numbers",
    "cost_layers",
    "costing_profiles",
    "credit_debit_notes",
    "financial_accounts",
    "financial_banks",
    "fiscal_documents",
    "fiscal_number_series",
    "fiscal_periods",
    "fiscal_rules",
    "goods_receipts",
    "igft_events",
    "inventory_adjustments",
    "inventory_balances",
    "inventory_lots",
    "inventory_movements",
    "movement_types",
    "official_documents",
    "official_registrations",
    "parties",
    "payment_methods",
    "permit_instances",
    "permit_types",
    "pick_lists",
    "presentations",
    "print_events",
    "product_presentation_versions",
    "product_serials",
    "product_templates",
    "profile_versions",
    "purchase_orders",
    "purchase_requisitions",
    "purchase_returns",
    "reconciliations",
    "regulatory_approval_requests",
    "regulatory_authorities",
    "regulatory_contingencies",
    "regulatory_evaluations",
    "regulatory_profiles",
    "report_exports",
    "report_jobs",
    "reservations",
    "sales_credit_notes",
    "sales_debit_notes",
    "sales_invoices",
    "sales_orders",
    "sales_quotes",
    "sales_returns",
    "service_templates",
    "shipments",
    "stock_counts",
    "stored_files",
    "supplier_credit_notes",
    "supplier_invoices",
    "supplier_quotes",
    "tax_calculations",
    "tax_profiles",
    "tax_return_batches",
    "taxonomy_nodes",
    "transfers",
    "transport_drivers",
    "transport_vehicles",
    "treasury_instruments",
    "treasury_transfers",
    "triple_matches",
    "units_of_measure",
    "withholding_rules",
]


def upgrade() -> None:
    for tabla in TABLAS:
        op.drop_column(tabla, "legacy_scope_id")
        op.drop_column(tabla, "scope_backfill_class")


def downgrade() -> None:
    for tabla in TABLAS:
        op.add_column(tabla, sa.Column("legacy_scope_id", sa.String(36), nullable=True))
        op.add_column(tabla, sa.Column("scope_backfill_class", sa.String(32), nullable=True))
