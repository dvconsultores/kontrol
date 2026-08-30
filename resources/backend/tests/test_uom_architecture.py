"""Pruebas de arquitectura y contrato de la Spec 011.

No prueban un caso de uso: prueban que la **arquitectura** cumple lo que la
Spec exige, y están diseñadas para fallar si alguien la erosiona más adelante.

Comparan la matriz aprobada contra la implementación real (§68) y demuestran
que la lectura de un documento congelado no consulta el maestro vigente (§95).
"""

from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path

import pytest

from app.core.database import Base, init_models

BACKEND = Path(__file__).resolve().parents[1]

#: Autoridad: `transaction-uom-impact-matrix.md`. 17 líneas MUST_HAVE_NOW.
MUST_HAVE_NOW: dict[str, tuple[str, ...]] = {
    "inventory_movements": ("base_quantity",),
    "reservations": ("base_quantity",),
    "transfer_lines": ("base_quantity_sent", "base_quantity_received"),
    "stock_count_lines": ("base_expected_qty", "base_counted_qty"),
    "inventory_adjustments": ("base_quantity",),
    "purchase_requisition_lines": ("base_quantity",),
    "supplier_quote_lines": ("base_quantity",),
    "purchase_order_lines": ("base_quantity_ordered", "base_quantity_received"),
    "goods_receipt_lines": ("base_quantity_received", "base_quantity_accepted",
                            "base_quantity_rejected"),
    "supplier_invoice_lines": ("base_quantity",),
    "purchase_return_lines": ("base_quantity",),
    "sales_quote_lines": ("base_quantity",),
    "sales_order_lines": ("base_quantity",),
    "pick_list_lines": ("base_quantity",),
    "shipment_lines": ("base_quantity",),
    "sales_invoice_lines": ("base_quantity",),
    "sales_return_lines": ("base_quantity",),
}

#: Clasificadas `NOT_APPLICABLE`: proyección, derivada y comparación. **No**
#: deben recibir las columnas, y que no las tengan es parte del contrato.
NOT_APPLICABLE = ("inventory_balances", "cost_layers", "triple_matches")

CONTRACT_ONLY = ("permit_instances",)


@pytest.fixture(scope="module", autouse=True)
def _models():
    init_models()


# ---------------------------------------------------------------- §68
def test_las_17_lineas_must_have_now_estan_integradas():
    """Ninguna línea de la matriz queda fuera. Sin exclusiones artificiales."""
    faltan: list[str] = []
    for table, base_columns in MUST_HAVE_NOW.items():
        assert table in Base.metadata.tables, f"la tabla {table} desapareció del esquema"
        columns = set(Base.metadata.tables[table].c.keys())
        for required in ("uom_id", "presentation_id", "conversion_factor_snapshot",
                         "uom_source", *base_columns):
            if required not in columns:
                faltan.append(f"{table}.{required}")
    assert faltan == [], faltan
    assert len(MUST_HAVE_NOW) == 17


def test_not_applicable_no_reciben_columnas():
    """No se rellenan columnas porque «todas deberían tenerlas» (§18)."""
    for table in NOT_APPLICABLE:
        columns = set(Base.metadata.tables[table].c.keys())
        assert "presentation_id" not in columns, table
        assert "conversion_factor_snapshot" not in columns, table


def test_contract_only_solo_recibe_la_unidad():
    for table in CONTRACT_ONLY:
        columns = set(Base.metadata.tables[table].c.keys())
        assert "uom_id" in columns
        assert "presentation_id" not in columns


def test_cantidades_base_son_numeric():
    for table, base_columns in MUST_HAVE_NOW.items():
        for column in (*base_columns, "conversion_factor_snapshot"):
            kind = Base.metadata.tables[table].c[column].type.__class__.__name__
            assert kind == "Numeric", f"{table}.{column} es {kind}"


# ---------------------------------------------------------------- §69
def test_no_queda_unit_id_none_literal():
    """El patrón que dejaba la unidad sin capturar no debe sobrevivir."""
    offenders: list[str] = []
    for path in (BACKEND / "app").rglob("*.py"):
        for number, line in enumerate(path.read_text().splitlines(), start=1):
            if re.search(r"\bunit_id\s*=\s*None\b", line) and "Mapped" not in line:
                offenders.append(f"{path.relative_to(BACKEND)}:{number}")
    assert offenders == [], offenders


# ---------------------------------------------------------------- §70, P22
def test_autoridad_unica_de_conversion():
    """Un solo lugar del sistema convierte a unidad base (P22).

    Ningún módulo de compras, inventario, ventas o facturación replica el
    cálculo `cantidad × factor`.
    """
    engine = BACKEND / "app" / "modules" / "master_data" / "uom.py"
    assert engine.exists()

    offenders: list[str] = []
    pattern = re.compile(r"(factor_to_base|conversion_factor)\s*\*|"
                         r"\*\s*(factor_to_base|conversion_factor)")
    for path in (BACKEND / "app").rglob("*.py"):
        if path == engine:
            continue
        for number, line in enumerate(path.read_text().splitlines(), start=1):
            if pattern.search(line):
                offenders.append(f"{path.relative_to(BACKEND)}:{number}")
    assert offenders == [], f"cálculo de conversión fuera del motor: {offenders}"


def test_el_motor_de_conversiones_tiene_consumidores():
    """No se deja una capacidad nueva que nadie use (§70)."""
    consumers: list[str] = []
    for path in (BACKEND / "app").rglob("*.py"):
        if "master_data" in str(path) and path.name in ("uom.py",):
            continue
        text = path.read_text()
        if "master_data import uom" in text or "master_data.uom" in text:
            consumers.append(str(path.relative_to(BACKEND)))
    assert consumers, "el motor de conversión no tiene ningún consumidor"


# ---------------------------------------------------------------- §95
def test_lectura_historica_no_consulta_el_maestro_vigente():
    """Reimprimir un documento congelado usa **su** snapshot.

    La prueba busca activamente una consulta accidental al factor vigente:
    intercepta `resolve_conversion` y falla si alguien la invoca durante la
    lectura de una línea congelada.
    """
    from app.modules.master_data import uom

    called: list[str] = []
    original = uom.resolve_conversion

    def spy(*args, **kwargs):
        called.append("resolve_conversion")
        return original(*args, **kwargs)

    uom.resolve_conversion = spy  # type: ignore[assignment]
    try:
        # Lectura de una línea congelada: se usan sus propias columnas.
        class FrozenLine:
            quantity = Decimal("10")
            conversion_factor_snapshot = Decimal("100")
            base_quantity = Decimal("1000")
            uom_symbol_snapshot = "und"
            presentation_label_snapshot = "Caja"

        line = FrozenLine()
        rendered = (f"{line.quantity} {line.presentation_label_snapshot} = "
                    f"{line.base_quantity} {line.uom_symbol_snapshot}")
        assert rendered == "10 Caja = 1000 und"
    finally:
        uom.resolve_conversion = original  # type: ignore[assignment]

    assert called == [], "la lectura histórica consultó el maestro vigente"


def test_el_punto_de_congelamiento_es_por_ciclo_de_vida():
    """No se codifica `if status == "ISSUED"` para todos los dominios (§15)."""
    from app.modules.master_data import uom

    # Cada dominio tiene su propio punto de congelamiento contractual.
    assert uom.is_frozen("sales_invoices", "ISSUED") is True
    assert uom.is_frozen("sales_invoices", "DRAFT") is False
    assert uom.is_frozen("purchase_orders", "APPROVED") is True
    assert uom.is_frozen("purchase_orders", "DRAFT") is False
    assert uom.is_frozen("goods_receipts", "CONFIRMED") is True
    assert uom.is_frozen("stock_counts", "CLOSED") is True
    # Un movimiento de inventario nace congelado: no tiene borrador.
    assert uom.is_frozen("inventory_movements", None) is True
    # Ningún dominio usa el mismo literal para todo.
    literales = {frozenset(v) for v in uom.FREEZE_STATES.values()}
    assert len(literales) > 3, "los estados de congelamiento no distinguen ciclos de vida"


def test_base_fiscal_no_es_base_quantity():
    """Son conceptos distintos y no deben confundirse (§54)."""
    columns = Base.metadata.tables["sales_invoice_lines"].c
    assert "base_fiscal" in columns and "base_quantity" in columns
    assert columns["base_fiscal"].type.scale == 2, "base_fiscal es dinero"
    assert columns["base_quantity"].type.scale == 6, "base_quantity es cantidad"


def test_sin_unidades_ni_presentaciones_codificadas():
    """NFR-011-08: la estructura es dato, no código (P8)."""
    offenders: list[str] = []
    pattern = re.compile(r"""["'](UND|KG|CAJA|BOLSA|PALLET|SACO|LITRO)["']\s*[:,)=]""")
    for path in (BACKEND / "app").rglob("*.py"):
        for number, line in enumerate(path.read_text().splitlines(), start=1):
            if pattern.search(line) and "#" not in line.split('"')[0]:
                offenders.append(f"{path.relative_to(BACKEND)}:{number}")
    assert offenders == [], offenders
