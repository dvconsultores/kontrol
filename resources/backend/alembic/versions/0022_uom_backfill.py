"""Backfill clasificado de la semántica de unidad (Spec 011, F5).

Gobernada por `legacy-uom-migration-matrix.md`, que es normativa. Es la
migración de mayor riesgo del proyecto hasta la fecha: en la Spec 008 se imponía
integridad sobre referencias que **existían**; aquí se asigna significado a un
dato que **nunca se capturó**.

Orden obligatorio, diseñado para poder abortar sin daño:

  1. Clasificar cada línea. Sin escribir.
  2. Si hay críticas fiscales por encima del umbral: reportar y **abortar**.
  3. Escribir las clases A y B.
  4. Marcar las clases C y D sin tocar sus cantidades.
  5. Emitir el reporte.

Reglas no negociables:

- La `quantity` original **nunca** se modifica (FR-011-077).
- `factor = 1` solo cuando puede demostrarse que la cantidad ya está en unidad
  base. Nunca como valor por defecto técnico (R-011-4).
- Una línea ambigua queda **nula y marcada**; no se le asigna la unidad más
  probable (FR-011-073).
- Una línea de documento fiscal emitido irreconstruible **no se toca**
  (FR-011-074).

Esta migración lee datos: **no** es válida en modo offline (`--sql`).

Revision ID: 0022_uom_backfill
Revises: 0021_line_uom_columns
Create Date: 2026-08-30
"""

from __future__ import annotations

import json
import os

import sqlalchemy as sa

from alembic import op

revision = "0022_uom_backfill"
down_revision = "0021_line_uom_columns"
branch_labels = None
depends_on = None

CLASS_A = "DETERMINISTIC_BACKFILL"
CLASS_B = "RECONSTRUCTIBLE_WITH_EVIDENCE"
CLASS_C = "AMBIGUOUS"
CLASS_D = "NON_RECONSTRUCTIBLE_FISCAL"

SOURCE_A = "LEGACY_ASSUMED_BASE"
SOURCE_B = "LEGACY_RECONSTRUCTED"
SOURCE_C = "LEGACY_UNRESOLVED"
SOURCE_D = "LEGACY_UNVERSIONED"

#: ESC-011-01 — semántica explícita y sin ambigüedad matemática.
#:
#: `KONTROL_UOM_BACKFILL_MAX_CRITICAL` es el número **máximo tolerado** de líneas
#: fiscales emitidas irreconstruibles. El valor por defecto es **0**: tolerancia
#: cero. Con el default, encontrar 1 o más aborta la migración.
#:
#:     critical_count > MAX_CRITICAL  ->  BLOCK MIGRATION
#:     con MAX_CRITICAL = 0, esto es  critical_count >= 1  ->  BLOCK
#:
#: No existe default permisivo. Cambiarlo en una instalación real es una acción
#: deliberada, explícita y auditable en el reporte (§21, §22).
MAX_CRITICAL_ENV = "KONTROL_UOM_BACKFILL_MAX_CRITICAL"
DEFAULT_MAX_CRITICAL = 0

#: tabla -> (cantidades, columna de producto, tabla de cabecera, FK a cabecera)
LINES: dict[str, tuple[tuple[str, ...], str, str | None, str | None]] = {
    "inventory_movements": (("quantity",), "product_id", None, None),
    "reservations": (("quantity",), "product_id", None, None),
    "transfer_lines": (("quantity_sent", "quantity_received"), "product_id", None, None),
    "stock_count_lines": (("expected_qty", "counted_qty"), "product_id", "stock_counts", "count_id"),
    "inventory_adjustments": (("quantity",), "product_id", None, None),
    "purchase_requisition_lines": (("quantity",), "product_id", None, None),
    "supplier_quote_lines": (("quantity",), "product_id", None, None),
    "purchase_order_lines": (("quantity_ordered", "quantity_received"), "product_id", None, None),
    "goods_receipt_lines": (("quantity_received", "quantity_accepted", "quantity_rejected"),
                            "product_id", None, None),
    "supplier_invoice_lines": (("quantity",), "product_id", None, None),
    "purchase_return_lines": (("quantity",), "product_id", None, None),
    "sales_quote_lines": (("quantity",), "product_id", None, None),
    "sales_order_lines": (("quantity",), "product_id", None, None),
    "pick_list_lines": (("quantity",), "product_id", None, None),
    "shipment_lines": (("quantity",), "product_id", None, None),
    "sales_invoice_lines": (("quantity",), "product_id", None, None),
    "sales_return_lines": (("quantity",), "product_id", None, None),
}

#: Documentos con efecto fiscal: su histórico es una declaración ante la
#: administración tributaria. La clase C degrada a D aquí.
FISCAL_LINES = frozenset({"sales_invoice_lines", "supplier_invoice_lines", "sales_return_lines"})


def base_name(column: str) -> str:
    if column == "quantity":
        return "base_quantity"
    if column.startswith("quantity_"):
        return "base_quantity_" + column[len("quantity_"):]
    return "base_" + column


class BackfillBlocked(RuntimeError):
    """Líneas fiscales irreconstruibles por encima del umbral (ESC-011-01)."""


def _emit(report: dict) -> None:
    print("\n===== REPORTE DE BACKFILL DE UNIDADES (0022) =====")
    print(json.dumps({k: v for k, v in report.items() if k != "details"},
                     indent=2, ensure_ascii=False))
    for row in report["details"][:300]:
        print(f"  [{row['classification']}] {row['table']} id={row['row_id']} "
              f"producto={row['product_id']} accion={row['action']} · {row['justification']}")
    if len(report["details"]) > 300:
        print(f"  … y {len(report['details']) - 300} más")
    print("===== FIN DEL REPORTE =====\n")


def upgrade() -> None:
    bind = op.get_bind()
    max_critical = int(os.environ.get(MAX_CRITICAL_ENV, DEFAULT_MAX_CRITICAL))

    report: dict = {
        "migration_id": revision,
        "max_critical_allowed": max_critical,
        "threshold_source": ("ENV:" + MAX_CRITICAL_ENV
                             if MAX_CRITICAL_ENV in os.environ else "DEFAULT"),
        "total_lines_checked": 0,
        "deterministic": 0,
        "reconstructed": 0,
        "ambiguous": 0,
        "non_reconstructible": 0,
        "fiscal_critical": 0,
        "assigned_base_unit": 0,
        "assigned_presentation": 0,
        "assigned_factor_snapshot": 0,
        "manual_review": 0,
        "migration_blocked": False,
        "details": [],
    }

    # Unidad base declarada por producto. Es la evidencia de la clase A.
    base_units = dict(bind.execute(sa.text(
        "SELECT id, base_unit_id FROM catalog_items WHERE base_unit_id IS NOT NULL")).fetchall())

    # Evidencia para la clase B: unidades observadas por producto en las dos
    # tablas que llegaron a tener columna de unidad. Más de una candidata
    # degrada la línea; no se elige la más frecuente (FR-011-072).
    evidence: dict[str, set[str]] = {}
    for table, column in (("inventory_movements", "unit_id"),
                          ("purchase_requisition_lines", "unit_id")):
        try:
            rows = bind.execute(sa.text(
                f"SELECT DISTINCT product_id, {column} FROM {table} WHERE {column} IS NOT NULL"
            )).fetchall()
        except Exception:  # noqa: BLE001 — la columna puede no existir en esta versión
            continue
        for product_id, unit_id in rows:
            evidence.setdefault(product_id, set()).add(unit_id)

    # Unidad de facturación de los servicios. Vive en `services`, no en
    # `catalog_items`, y se enlaza por `item_id`: es la vía legítima de la clase
    # B para servicios (CL-011-09).
    billing_units = dict(bind.execute(sa.text(
        "SELECT item_id, billing_unit_id FROM services WHERE billing_unit_id IS NOT NULL"
    )).fetchall())

    writes: list[tuple[str, str, str, str, str]] = []   # tabla, id, uom, source, quantities-json
    marks: list[tuple[str, str, str]] = []              # tabla, id, source

    # ---- 1. Clasificar. Nada se escribe todavía. ----
    for table, (quantities, product_col, _head, _fk) in LINES.items():
        rows = bind.execute(sa.text(
            f"SELECT id, {product_col} FROM {table}")).fetchall()
        for row_id, product_id in rows:
            report["total_lines_checked"] += 1

            unit_id = base_units.get(product_id)
            if unit_id:
                report["deterministic"] += 1
                writes.append((table, str(row_id), unit_id, SOURCE_A, json.dumps(list(quantities))))
                continue

            candidates = evidence.get(product_id, set())
            if len(candidates) == 1:
                report["reconstructed"] += 1
                resolved = next(iter(candidates))
                report["details"].append({
                    "table": table, "row_id": str(row_id), "product_id": str(product_id),
                    "classification": CLASS_B, "action": "RECONSTRUCTED",
                    "justification": "Candidata única observada en movimientos o requisiciones"})
                writes.append((table, str(row_id), resolved, SOURCE_B, json.dumps(list(quantities))))
                continue
            if not candidates and product_id in billing_units:
                report["reconstructed"] += 1
                report["details"].append({
                    "table": table, "row_id": str(row_id), "product_id": str(product_id),
                    "classification": CLASS_B, "action": "RECONSTRUCTED",
                    "justification": "Unidad de facturación única del producto"})
                writes.append((table, str(row_id), billing_units[product_id], SOURCE_B,
                               json.dumps(list(quantities))))
                continue

            # Sin unidad base y sin candidata única.
            if table in FISCAL_LINES:
                report["non_reconstructible"] += 1
                report["fiscal_critical"] += 1
                report["manual_review"] += 1
                report["details"].append({
                    "table": table, "row_id": str(row_id), "product_id": str(product_id),
                    "classification": CLASS_D, "action": "BLOCKED",
                    "justification": ("Documento fiscal emitido sin unidad reconstruible: "
                                      f"{len(candidates)} candidatas")})
                marks.append((table, str(row_id), SOURCE_D))
                continue

            report["ambiguous"] += 1
            report["manual_review"] += 1
            report["details"].append({
                "table": table, "row_id": str(row_id), "product_id": str(product_id),
                "classification": CLASS_C, "action": "MARKED_UNRESOLVED",
                "justification": f"{len(candidates)} candidatas: no se elige la más probable"})
            marks.append((table, str(row_id), SOURCE_C))

    # ---- 2. Evaluar el bloqueo ANTES de cualquier escritura ----
    if report["fiscal_critical"] > max_critical:
        report["migration_blocked"] = True
        _emit(report)
        raise BackfillBlocked(
            f"{report['fiscal_critical']} líneas fiscales emitidas sin unidad reconstruible "
            f"(máximo tolerado: {max_critical}). La migración se detiene sin escribir nada. "
            "Resuelva la unidad base de esos productos y vuelva a ejecutar "
            "(legacy-uom-migration-matrix.md §3, clase D).")

    # ---- 3. Escribir clases A y B ----
    for table, row_id, unit_id, source, quantities_json in writes:
        quantities = json.loads(quantities_json)
        # `factor = 1` es aquí una conclusión demostrada: no existió ni pudo
        # existir presentación alguna, luego la cantidad ya está en la unidad
        # asignada (R-011-4, matriz §1).
        sets = ["uom_id = :uom", "presentation_id = NULL",
                "conversion_factor_snapshot = 1", "uom_source = :src"]
        for quantity in quantities:
            sets.append(f"{base_name(quantity)} = {quantity}")
        bind.execute(sa.text(f"UPDATE {table} SET {', '.join(sets)} WHERE id = :id"),
                     {"uom": unit_id, "src": source, "id": row_id})
        report["assigned_base_unit"] += 1
        report["assigned_factor_snapshot"] += 1

    # ---- 4. Marcar clases C y D sin tocar sus cantidades ----
    for table, row_id, source in marks:
        bind.execute(sa.text(f"UPDATE {table} SET uom_source = :src WHERE id = :id"),
                     {"src": source, "id": row_id})

    _emit(report)


def downgrade() -> None:
    # Retira solo la semántica añadida. Las cantidades originales nunca se
    # tocaron, así que no hay nada que restaurar.
    for table, (quantities, _p, _h, _f) in LINES.items():
        sets = ["uom_id = NULL", "presentation_id = NULL",
                "conversion_factor_snapshot = NULL", "uom_source = NULL"]
        for quantity in quantities:
            sets.append(f"{base_name(quantity)} = NULL")
        op.execute(f"UPDATE {table} SET {', '.join(sets)}")
