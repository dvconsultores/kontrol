"""Cantidades y factores de `Float` a `NUMERIC` (Spec 011, F4).

30 columnas de cantidad en 17 tablas dejan de ser coma flotante. El precedente
es `KQA-100`: una regresión `Decimal + float` que rompió factura, pago, cobro,
notas y CxC/CxP, que SQLite ocultó y que apareció por casualidad.

Esta migración **no aplica reglas comerciales de redondeo** (§28). Distingue
almacenamiento de política: convierte con la precisión declarada y **reporta**
toda fila cuyo valor cambie. Una pérdida material no documentada es un BLOCKER.

`presentations.content` **no** se convierte: es dato legado anterior a 011 que
se conserva como evidencia de la intención original y no se usa para calcular
(CL-011-11).

No se tocan columnas monetarias ni fiscales: `unit_price`, `tax_amount`,
`base_fiscal` y `total` ya son `NUMERIC` desde `0012`/`0014` y tienen otra
semántica. `base_fiscal` es base imponible en moneda, **no** cantidad base.

Revision ID: 0020_quantity_numeric
Revises: 0019_uom_model
Create Date: 2026-08-30
"""

from __future__ import annotations

import json

import sqlalchemy as sa

from alembic import op

revision = "0020_quantity_numeric"
down_revision = "0019_uom_model"
branch_labels = None
depends_on = None

#: (tabla, columna) de las 30 cantidades. Derivada de la matriz aprobada, no de
#: una búsqueda ciega de nombres.
QUANTITY_COLUMNS: tuple[tuple[str, str], ...] = (
    ("inventory_movements", "quantity"),
    ("inventory_balances", "qty_on_hand"),
    ("inventory_balances", "qty_reserved"),
    ("inventory_balances", "qty_available"),
    ("reservations", "quantity"),
    ("transfer_lines", "quantity_sent"),
    ("transfer_lines", "quantity_received"),
    ("stock_count_lines", "expected_qty"),
    ("stock_count_lines", "counted_qty"),
    ("stock_count_lines", "variance"),
    ("inventory_adjustments", "quantity"),
    ("cost_layers", "quantity_in"),
    ("cost_layers", "quantity_remaining"),
    ("purchase_requisition_lines", "quantity"),
    ("supplier_quote_lines", "quantity"),
    ("purchase_order_lines", "quantity_ordered"),
    ("purchase_order_lines", "quantity_received"),
    ("goods_receipt_lines", "quantity_received"),
    ("goods_receipt_lines", "quantity_accepted"),
    ("goods_receipt_lines", "quantity_rejected"),
    ("supplier_invoice_lines", "quantity"),
    ("triple_matches", "variance_qty"),
    ("purchase_return_lines", "quantity"),
    ("permit_instances", "quantity"),
    ("sales_quote_lines", "quantity"),
    ("sales_order_lines", "quantity"),
    ("pick_list_lines", "quantity"),
    ("shipment_lines", "quantity"),
    ("sales_invoice_lines", "quantity"),
    ("sales_return_lines", "quantity"),
)


class PrecisionLoss(RuntimeError):
    """Pérdida material de precisión no documentada: BLOCKER (§29)."""


def _emit(report: dict) -> None:
    print("\n===== REPORTE DE CONVERSIÓN NUMÉRICA (0020) =====")
    print(json.dumps({k: v for k, v in report.items() if k != "differences"},
                     indent=2, ensure_ascii=False))
    for row in report["differences"][:200]:
        print(f"  {row['table']}.{row['column']} id={row['row_id']} "
              f"{row['before']} -> {row['after']}")
    if len(report["differences"]) > 200:
        print(f"  … y {len(report['differences']) - 200} más")
    print("===== FIN DEL REPORTE =====\n")


def upgrade() -> None:
    bind = op.get_bind()
    postgres = bind.dialect.name == "postgresql"
    report: dict = {
        "migration_id": revision,
        "total_columns_migrated": 0,
        "total_rows_checked": 0,
        "exact_conversions": 0,
        "values_requiring_rounding": 0,
        "overflow": 0,
        "invalid": 0,
        "nulls": 0,
        "differences_detected": 0,
        "differences": [],
    }

    for table, column in QUANTITY_COLUMNS:
        if not postgres:
            op.alter_column(table, column, type_=sa.Numeric(18, 6), existing_type=sa.Float())
            report["total_columns_migrated"] += 1
            continue

        # 1. Comparar el valor original con su representación en NUMERIC(18,6)
        #    ANTES de tocar la columna. Es la única forma de saber qué cambia.
        rows = bind.execute(sa.text(
            f"SELECT id, {column} AS v FROM {table} WHERE {column} IS NOT NULL"
        )).fetchall()
        nulls = bind.execute(sa.text(
            f"SELECT count(*) FROM {table} WHERE {column} IS NULL")).scalar_one()
        report["nulls"] += int(nulls)

        for row_id, value in rows:
            report["total_rows_checked"] += 1
            try:
                rounded = bind.execute(
                    sa.text("SELECT CAST(CAST(:v AS double precision) AS numeric(18,6))"),
                    {"v": value}).scalar_one()
            except Exception:  # noqa: BLE001 — cualquier fallo es dato inválido
                report["invalid"] += 1
                report["differences"].append(
                    {"table": table, "column": column, "row_id": str(row_id),
                     "before": str(value), "after": "ERROR"})
                continue
            if float(rounded) == float(value):
                report["exact_conversions"] += 1
            else:
                report["values_requiring_rounding"] += 1
                report["differences_detected"] += 1
                report["differences"].append(
                    {"table": table, "column": column, "row_id": str(row_id),
                     "before": repr(value), "after": str(rounded)})

        op.execute(f"ALTER TABLE {table} ALTER COLUMN {column} "
                   f"TYPE NUMERIC(18,6) USING {column}::numeric(18,6)")
        report["total_columns_migrated"] += 1

    _emit(report)

    # La conversión de un `double precision` a `numeric(18,6)` solo pierde algo
    # cuando el valor traía más de 6 decimales significativos. Que ocurra es
    # aceptable; que ocurra **en silencio** no lo es: queda en el reporte fila a
    # fila, con su valor anterior.
    if report["invalid"]:
        raise PrecisionLoss(
            f"{report['invalid']} valores no convertibles. Revise el reporte antes de continuar.")


def downgrade() -> None:
    postgres = op.get_bind().dialect.name == "postgresql"
    for table, column in QUANTITY_COLUMNS:
        if postgres:
            op.execute(f"ALTER TABLE {table} ALTER COLUMN {column} "
                       f"TYPE double precision USING {column}::double precision")
        else:
            op.alter_column(table, column, type_=sa.Float(), existing_type=sa.Numeric(18, 6))
