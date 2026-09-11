"""Spec 028 · guardias del motor compartido de saldos monetarios.

`ADR-D0-001` nombra `KQA-100` —«`Decimal + float`»— como defecto CRÍTICO. Estas
guardias existen para que el dinero no vuelva a calcularse en coma flotante en
el motor que CxP, CxC, conciliación y tesorería comparten.

La invariante que defienden:

> **`MONETARY-BALANCE-INVARIANT`** — todo cálculo monetario canónico de saldos
> usa `Decimal`. Prohibido `float(monto)`, `round(float(...))` y cualquier
> aritmética intermedia binaria. La precisión la fija el maestro de monedas
> (`Currency.decimal_places`), no un número escrito a mano.
"""

from __future__ import annotations

import re
from pathlib import Path

from tests.spec_blocks import cuerpo_de_simbolo

RAIZ = Path(__file__).resolve().parents[1] / "app"
AP = (RAIZ / "modules" / "purchasing" / "service.py").read_text()
SALES = (RAIZ / "modules" / "sales" / "service.py").read_text()

#: Las funciones que son la autoridad del saldo y de su movimiento.
AUTORIDAD_DEL_SALDO = (
    "def open_item_balance(",
    "def _source_available(",
    "def _reduce_source(",
    "def apply_source(",
)


def test_el_saldo_no_se_calcula_en_coma_flotante():
    for nombre in AUTORIDAD_DEL_SALDO:
        cuerpo = cuerpo_de_simbolo(AP, nombre)
        assert "float(" not in cuerpo, f"{nombre} volvió a convertir dinero a float"
        assert "round(" not in cuerpo, f"{nombre} volvió a redondear a mano"


def test_el_saldo_devuelve_decimal():
    from decimal import Decimal

    from app.modules.purchasing import service as ap

    firma = cuerpo_de_simbolo(AP, "def open_item_balance(")
    assert "-> Decimal" in AP[AP.index("def open_item_balance("):][:120], \
        "la firma dejó de declarar Decimal"
    assert "_money(" in firma, "el saldo no pasa por el coercitivo monetario"
    assert ap._money("0.1") + ap._money("0.2") == Decimal("0.30"), \
        "el coercitivo monetario no es exacto"


def test_no_queda_margen_de_coma_flotante():
    """El `1e-6` era el disimulo del error binario. Con `Decimal` sobra."""
    for fuente, nombre in ((AP, "purchasing"), (SALES, "sales")):
        codigo = "\n".join(x for x in fuente.splitlines() if not x.strip().startswith("#"))
        assert "1e-6" not in codigo, f"{nombre}: volvió el margen de coma flotante"


def test_la_aplicacion_de_la_nota_de_credito_tampoco_usa_float():
    cuerpo = cuerpo_de_simbolo(SALES, "def apply_credit_note(")
    assert "float(" not in cuerpo, "la aplicación de la nota volvió a float"
    assert "round(" not in cuerpo


def test_la_precision_no_esta_escrita_a_mano():
    """El `6` de `round(..., 6)` no era política de nadie."""
    cuerpo = cuerpo_de_simbolo(AP, "def _money(")
    assert "_MONEY_PLACES" in cuerpo, "la escala volvió a ser un número suelto"
    assert "Currency" in AP[:AP.index("def _money(")], \
        "la escala no dice de dónde sale su autoridad"


def test_el_motor_de_saldos_tiene_un_solo_dueño():
    """CxC no puede tener su propia fórmula: consume la del motor compartido."""
    for nombre in ("def _aplicar_nota_a_cxc(", "def apply_credit_note("):
        cuerpo = cuerpo_de_simbolo(SALES, nombre)
        assert "ap_service.open_item_balance(" in cuerpo or "open_item_balance(" in cuerpo, \
            f"{nombre} dejó de usar la autoridad del saldo"
    # Y no existe una segunda función de saldo en ventas.
    assert not re.search(r"def \w*open_item_balance\w*\(", SALES), \
        "ventas creó su propio motor de saldos"
