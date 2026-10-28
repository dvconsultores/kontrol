"""El vencimiento documental se decide con el día de negocio de Caracas (Spec 001 · 046).

Sin base de datos: se congela el reloj en la única costura del núcleo temporal y
se comprueba que `is_expired` responde con el calendario de negocio, no con la
fecha UTC del proceso.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace

import app.shared.clock as reloj
from app.modules.documents.service import is_expired
from app.shared.clock import hoy_de_negocio


def test_hoy_de_negocio_sale_de_la_costura(monkeypatch) -> None:
    monkeypatch.setattr(reloj, "instante_actual", lambda: datetime(2026, 10, 28, 3, 30, tzinfo=UTC))
    assert hoy_de_negocio() == date(2026, 10, 27)


def test_un_documento_que_vence_hoy_no_esta_vencido_a_las_2330_de_caracas(monkeypatch) -> None:
    monkeypatch.setattr(reloj, "instante_actual", lambda: datetime(2026, 10, 28, 3, 30, tzinfo=UTC))
    documento = SimpleNamespace(expiration_date=date(2026, 10, 27))
    assert is_expired(documento) is False


def test_a_las_0030_de_caracas_del_dia_siguiente_ya_esta_vencido(monkeypatch) -> None:
    monkeypatch.setattr(reloj, "instante_actual", lambda: datetime(2026, 10, 28, 4, 30, tzinfo=UTC))
    documento = SimpleNamespace(expiration_date=date(2026, 10, 27))
    assert is_expired(documento) is True


def test_una_fecha_explicita_manda() -> None:
    documento = SimpleNamespace(expiration_date=date(2026, 10, 27))
    assert is_expired(documento, today=date(2026, 10, 27)) is False
    assert is_expired(documento, today=date(2026, 10, 28)) is True


def test_sin_vencimiento_nunca_vence() -> None:
    assert is_expired(SimpleNamespace(expiration_date=None)) is False
