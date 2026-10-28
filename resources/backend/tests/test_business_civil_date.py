"""Spec 001 · business-civil-date — límites civiles y período en la zona de negocio.

La zona de negocio es constante `America/Caracas` y los límites de día y de
período son semiabiertos: [inicio, fin). Estas pruebas verifican los vectores del
contrato, las transiciones históricas de la hora legal venezolana y la validación
del período «AAAA-MM».
"""

from __future__ import annotations

import os
import time
from datetime import UTC, date, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.errors import KontrolError
from app.shared.clock import (
    ZONA_DE_NEGOCIO,
    hoy_de_negocio,
    inicio_del_dia_de_negocio,
    limites_del_dia_utc,
    limites_del_periodo_utc,
    periodo_valido,
    zona_de_negocio,
)


def _bajo(zona: str, funcion):
    """Ejecuta `funcion` con el proceso en `zona` y restituye la del entorno."""
    original = os.environ.get("TZ")
    try:
        os.environ["TZ"] = zona
        time.tzset()
        return funcion()
    finally:
        if original is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = original
        time.tzset()


def test_vector_01_dia_de_negocio_antes_de_medianoche_caracas():
    """2026-10-28T03:30Z (23:30 del 27 en Caracas) sigue en el día 27."""
    assert hoy_de_negocio(datetime(2026, 10, 28, 3, 30, tzinfo=UTC)) == date(2026, 10, 27)


def test_vector_02_dia_de_negocio_despues_de_medianoche_caracas():
    """2026-10-28T04:30Z (00:30 del 28 en Caracas) ya es el día 28."""
    assert hoy_de_negocio(datetime(2026, 10, 28, 4, 30, tzinfo=UTC)) == date(2026, 10, 28)


def test_vector_03_instante_fin_de_periodo_es_excluido():
    """El límite superior del período semiabierto coincide con fin y está excluido."""
    inicio, fin = limites_del_periodo_utc("2026-10")
    x = datetime(2026, 11, 1, 3, 59, 59, tzinfo=UTC)
    assert inicio <= x < fin
    medianoche = datetime(2026, 11, 1, 4, 0, tzinfo=UTC)  # 00:00 del 1-nov en Caracas
    assert fin == medianoche and not (inicio <= medianoche < fin)


def test_vector_04_ano_nuevo_en_utc_sigue_del_ano_anterior_en_caracas():
    """2027-01-01T02:00Z (22:00 del 31-dic-2026 en Caracas) sigue en 2026."""
    assert hoy_de_negocio(datetime(2027, 1, 1, 2, 0, tzinfo=UTC)) == date(2026, 12, 31)


def test_vector_05_ano_nuevo_en_caracas():
    """2027-01-01T04:00Z (00:00 del 1-ene-2027 en Caracas) ya es 2027."""
    assert hoy_de_negocio(datetime(2027, 1, 1, 4, 0, tzinfo=UTC)) == date(2027, 1, 1)


def test_limites_del_periodo_utc_octubre_2026():
    """Los límites de octubre 2026 en Caracas equivalen a las 04:00 UTC."""
    assert limites_del_periodo_utc("2026-10") == (
        datetime(2026, 10, 1, 4, 0, tzinfo=UTC),
        datetime(2026, 11, 1, 4, 0, tzinfo=UTC),
    )


def test_limites_del_periodo_utc_diciembre_2026():
    """Diciembre abarca hasta el 1 de enero del año siguiente."""
    assert limites_del_periodo_utc("2026-12") == (
        datetime(2026, 12, 1, 4, 0, tzinfo=UTC),
        datetime(2027, 1, 1, 4, 0, tzinfo=UTC),
    )


def test_limites_del_dia_utc():
    """El día civil 2026-10-27 va de las 04:00 a las 04:00 UTC."""
    assert limites_del_dia_utc(date(2026, 10, 27)) == (
        datetime(2026, 10, 27, 4, 0, tzinfo=UTC),
        datetime(2026, 10, 28, 4, 0, tzinfo=UTC),
    )


def test_transicion_historica_decreto_2301():
    """El 1 de mayo de 2016 duró 23 h 30 min por el Decreto 2.301."""
    assert limites_del_dia_utc(date(2016, 5, 1)) == (
        datetime(2016, 5, 1, 4, 30, tzinfo=UTC),
        datetime(2016, 5, 2, 4, 0, tzinfo=UTC),
    )
    assert inicio_del_dia_de_negocio(date(2016, 4, 30)).utcoffset() == timedelta(
        hours=-4, minutes=-30
    )


@pytest.mark.parametrize(
    "zona", ["UTC", "America/Caracas", "Asia/Tokyo", "Pacific/Kiritimati"]
)
def test_limites_del_dia_no_cambian_con_la_zona_del_proceso(zona):
    """La zona del proceso no afecta a los límites calculados con ZoneInfo."""
    esperado = (
        datetime(2026, 10, 27, 4, 0, tzinfo=UTC),
        datetime(2026, 10, 28, 4, 0, tzinfo=UTC),
    )
    assert _bajo(zona, lambda: limites_del_dia_utc(date(2026, 10, 27))) == esperado


def test_periodo_valido():
    """Un período «AAAA-MM» se descompone en año y mes."""
    assert periodo_valido("2026-10") == (2026, 10)


@pytest.mark.parametrize(
    "invalido",
    ["", "0", "2026-13", "2026-00", "2026-1", "26-10", "2026-10-01", "2026/10"],
)
def test_periodo_invalido_lanza_kontrol_error(invalido):
    """Formatos fuera de «AAAA-MM» producen KontrolError 422."""
    with pytest.raises(KontrolError) as exc_info:
        periodo_valido(invalido)
    assert exc_info.value.code == "INVALID_PERIOD"
    assert exc_info.value.status_code == 422


def test_zona_de_negocio_es_constante():
    """La zona devuelta es exactamente la constante del módulo."""
    assert zona_de_negocio() is ZONA_DE_NEGOCIO
    assert str(ZONA_DE_NEGOCIO) == "America/Caracas"


def test_config_business_timezone_puede_ser_solo_caracas():
    """La configuración rechaza cualquier zona distinta de America/Caracas."""
    with pytest.raises(ValidationError):
        Settings(business_timezone="UTC")
    assert Settings(business_timezone="America/Caracas").business_timezone == "America/Caracas"
