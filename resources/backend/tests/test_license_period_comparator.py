"""CMP Â· El comparador de perÃ­odos ordena solo por perÃ­odo (Fase A de LICENCIA-DOWNGRADE-FIRMADO,
FR-010-201..203). Igual inicio e igual fin: mismo perÃ­odo; ambos posteriores: mÃ¡s nuevo; ambos
anteriores: mÃ¡s viejo; cualquier otra forma no es un perÃ­odo del contrato y no se ordena. Ni el
`kid`, ni el identificador, ni los derechos, ni el reloj local participan. Fechas sintÃ©ticas."""

from __future__ import annotations

import inspect
from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.core.license import (
    INCOMPARABLE_PERIOD,
    NEWER_PERIOD,
    OLDER_PERIOD,
    SAME_PERIOD,
    compare_period,
)

CARACAS = timezone(timedelta(hours=-4))


def periodo(anio: int) -> tuple[datetime, datetime]:
    return (
        datetime(anio, 4, 1, 0, 0, 0, tzinfo=CARACAS),
        datetime(anio + 1, 3, 31, 23, 59, 59, tzinfo=CARACAS),
    )


def test_cmp_01_mismo_periodo() -> None:
    assert compare_period(*periodo(2027), *periodo(2027)) == SAME_PERIOD


def test_cmp_02_periodo_posterior_es_newer() -> None:
    assert compare_period(*periodo(2026), *periodo(2027)) == NEWER_PERIOD
    assert compare_period(*periodo(2026), *periodo(2030)) == NEWER_PERIOD


def test_cmp_03_periodo_anterior_es_older() -> None:
    assert compare_period(*periodo(2027), *periodo(2026)) == OLDER_PERIOD
    assert compare_period(*periodo(2027), *periodo(2020)) == OLDER_PERIOD


@pytest.mark.parametrize("a, b", [(2026, 2027), (2024, 2028), (2027, 2028)])
def test_cmp_04_el_orden_es_antisimetrico(a: int, b: int) -> None:
    assert compare_period(*periodo(a), *periodo(b)) == NEWER_PERIOD
    assert compare_period(*periodo(b), *periodo(a)) == OLDER_PERIOD


def test_cmp_05_las_zonas_horarias_no_cambian_el_orden() -> None:
    inicio_caracas, fin_caracas = periodo(2027)
    inicio_utc = inicio_caracas.astimezone(UTC)
    fin_utc = fin_caracas.astimezone(UTC)
    assert compare_period(inicio_caracas, fin_caracas, inicio_utc, fin_utc) == SAME_PERIOD

    inicio_naive = datetime(2027, 4, 1, 4, 0, 0)
    fin_naive = datetime(2028, 4, 1, 3, 59, 59)
    assert compare_period(inicio_caracas, fin_caracas, inicio_naive, fin_naive) == SAME_PERIOD

    assert inicio_utc.hour == 4


def test_cmp_06_mismo_inicio_distinto_fin_es_incomparable() -> None:
    inicio, fin = periodo(2027)
    assert compare_period(inicio, fin, inicio, fin + timedelta(days=30)) == INCOMPARABLE_PERIOD
    assert compare_period(inicio, fin, inicio, fin - timedelta(days=30)) == INCOMPARABLE_PERIOD


def test_cmp_07_mismo_fin_distinto_inicio_es_incomparable() -> None:
    inicio, fin = periodo(2027)
    assert compare_period(inicio, fin, inicio - timedelta(days=30), fin) == INCOMPARABLE_PERIOD
    assert compare_period(inicio, fin, inicio + timedelta(days=30), fin) == INCOMPARABLE_PERIOD


def test_cmp_08_periodos_cruzados_son_incomparables() -> None:
    inicio, fin = periodo(2027)
    assert compare_period(inicio, fin, inicio + timedelta(days=30), fin - timedelta(days=30)) == INCOMPARABLE_PERIOD
    assert compare_period(inicio, fin, inicio - timedelta(days=30), fin + timedelta(days=30)) == INCOMPARABLE_PERIOD


def test_cmp_09_un_segundo_basta_para_ordenar() -> None:
    inicio, fin = periodo(2027)
    un_segundo = timedelta(seconds=1)
    assert compare_period(inicio, fin, inicio + un_segundo, fin + un_segundo) == NEWER_PERIOD
    assert compare_period(inicio, fin, inicio - un_segundo, fin - un_segundo) == OLDER_PERIOD


def test_cmp_10_nada_mas_participa() -> None:
    assert tuple(inspect.signature(compare_period).parameters) == (
        "current_start",
        "current_end",
        "incoming_start",
        "incoming_end",
    )

    constantes = {SAME_PERIOD, NEWER_PERIOD, OLDER_PERIOD, INCOMPARABLE_PERIOD}
    assert len(constantes) == 4

    inicio, fin = periodo(2027)
    resultados = (
        compare_period(inicio, fin, *periodo(2027)),
        compare_period(inicio, fin, *periodo(2028)),
        compare_period(inicio, fin, *periodo(2026)),
        compare_period(inicio, fin, inicio, fin + timedelta(days=1)),
    )
    for resultado in resultados:
        assert resultado in constantes
