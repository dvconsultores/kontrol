"""El escaneo de líneas contradictorias cuenta sin reparar (RCL-H)."""

from __future__ import annotations

import sys
from pathlib import Path

_QA = Path(__file__).resolve().parents[3] / "qa"
if str(_QA) not in sys.path:
    sys.path.insert(0, str(_QA))

from recepcion_lineas_contradictorias import contar  # noqa: E402

from app.modules.purchasing.models import GoodsReceiptLine  # noqa: E402
from tests.test_recepcion_linea_integridad import (  # noqa: E402
    db_session,  # noqa: F401
    mundo,  # noqa: F401
)


def test_sin_contradicciones_cuenta_cero(db_session, mundo):  # noqa: F811
    assert contar(db_session.connection()) == {}


def test_cuenta_la_fila_contradictoria_y_no_la_toca(db_session, mundo):  # noqa: F811
    fila = GoodsReceiptLine(
        receipt_id=str(mundo.recepcion.id),
        order_line_id=str(mundo.linea_a.id),
        product_id=str(mundo.producto_b.id),
        quantity_received=5,
        quantity_accepted=5,
        quantity_rejected=0,
        quality="PENDING",
    )
    db_session.add(fila)
    db_session.flush()

    assert contar(db_session.connection()) == {"DRAFT": 1}

    db_session.refresh(fila)
    assert fila.product_id == str(mundo.producto_b.id)


def test_una_fila_correcta_no_cuenta(db_session, mundo):  # noqa: F811
    fila = GoodsReceiptLine(
        receipt_id=str(mundo.recepcion.id),
        order_line_id=str(mundo.linea_a.id),
        product_id=str(mundo.producto_a.id),
        quantity_received=5,
        quantity_accepted=5,
        quantity_rejected=0,
        quality="PENDING",
    )
    db_session.add(fila)
    db_session.flush()

    assert contar(db_session.connection()) == {}
