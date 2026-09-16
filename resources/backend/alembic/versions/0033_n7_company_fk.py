"""N7 — la empresa deja de ser una cadena y pasa a ser una referencia.

Revision ID: 0033_n7_company_fk
Revises: 0032_mc_expand_tenant_scoped

`company_id` existe en 101 tablas desde N3, y en 80 de ellas es una
columna de texto que la base no contrasta con nada. Hoy nada impide escribir ahí
el identificador de un tenant, el de una empresa de otro tenant, o uno que no
corresponda a nada.

N5 hizo que el código escriba siempre la empresa correcta y N6 que el frontend
opere sobre ella. Las dos protecciones viven en la aplicación: una consulta
nueva, un trabajo de fondo o un `INSERT` a mano las esquivan enteras. Esta
migración se lo pide a PostgreSQL, que no se puede olvidar de comprobarlo.

Sin cascada a propósito. Borrar una empresa con datos debe fallar: es una
persona jurídica con histórico fiscal, y que su borrado arrastre asientos,
documentos y libros sería lo contrario de lo que la ley obliga a conservar (P5).
"""
from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0033_n7_company_fk"
down_revision = "0032_mc_expand_tenant_scoped"
branch_labels = None
depends_on = None

#: Tablas de alcance empresa cuyo `company_id` todavía no referencia a nadie.
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
        _clave_de_empresa(tabla)


def _clave_de_empresa(tabla: str) -> None:
    """Crea la clave foránea sin condenar al histórico que otra migración preservó.

    La `0016` dejó a propósito en `regulatory_approval_requests` una solicitud
    legada cuya empresa ya no existe, y lo hizo apoyándose en una premisa que
    escribió: que esa tabla guardaba `company_id` «como texto SIN clave foránea».
    Esta migración invalidaba esa premisa y abortaba entero el upgrade de cualquier
    instalación con histórico —el `ALTER TABLE` fallaba con `ForeignKeyViolation`—.

    `NOT VALID` atiende las dos cosas a la vez: PostgreSQL no revisa las filas que
    ya estaban, pero **sí exige la referencia en toda inserción o actualización
    posterior**. Donde no cuelga nada —toda instalación limpia y toda base sana— la
    restricción se valida acto seguido y el resultado es idéntico al de antes.
    Donde cuelga algo, se anota y se sigue, que es lo que la matriz de
    reconstrucción de ARCH-MC-001 manda para la clase MC-D `NON_RECONSTRUCTIBLE`:
    anotar, no rellenar. No se inventa empresa y no se reasigna nada.
    """
    nombre = f"fk_{tabla}_company"
    op.execute(
        f"ALTER TABLE {tabla} ADD CONSTRAINT {nombre} "
        f"FOREIGN KEY (company_id) REFERENCES companies (id) NOT VALID"
    )
    # `TABLAS` es una lista literal de este mismo fichero: no hay entrada externa.
    colgantes = op.get_bind().execute(sa.text(
        f"SELECT t.company_id, count(*) FROM {tabla} t "
        f"LEFT JOIN companies c ON c.id = t.company_id "
        f"WHERE t.company_id IS NOT NULL AND c.id IS NULL "
        f"GROUP BY t.company_id ORDER BY t.company_id"
    )).fetchall()

    if not colgantes:
        op.execute(f"ALTER TABLE {tabla} VALIDATE CONSTRAINT {nombre}")
        return

    total = sum(fila[1] for fila in colgantes)
    detalle = ", ".join(f"{fila[0]!r}×{fila[1]}" for fila in colgantes)
    print(f"[0033] {tabla}: {total} fila(s) apuntan a una empresa que ya no existe "
          f"({detalle}). Se conservan intactas y {nombre} queda NOT VALID: toda "
          f"escritura nueva sigue exigiendo una empresa real.")


def downgrade() -> None:
    for tabla in TABLAS:
        op.drop_constraint(f"fk_{tabla}_company", tabla, type_="foreignkey")
