"""RLR · Matriz PURA del límite de tasa de desafíos de la Autoridad Central (`CENTRAL-SYNC-SIN-LIMITE-DE-TASA`):
`decide`/`window_start` de `central_authority/rate_limit.py` y la validación de los tres ajustes
`sync_challenge_rate_limit_*` de `central_authority/config.py`. Sin red, sin base, sin reloj real, sin
azar: `now` fijo en UTC y `Settings(_env_file=None, environment=…, db_url=…)` sin leer el entorno.
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime, timedelta

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from central_authority.config import Settings
from central_authority.rate_limit import CAPACITY_EXCEEDED, DISABLED, OK, RateLimitDecision, RateLimitPolicy, decide, window_start
from tests.central.conftest import pem_privada

NOW = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)
BASE = {"_env_file": None, "db_url": "sqlite+pysqlite:///:memory:"}


def _politica(capacity: int = 3, window_seconds: int = 60, enabled: bool = True) -> RateLimitPolicy:
    return RateLimitPolicy(enabled=enabled, capacity=capacity, window_seconds=window_seconds)


def test_rlr_01_la_politica_apagada_admite_siempre() -> None:
    politica = _politica(capacity=1, enabled=False)
    assert decide(policy=politica, now=NOW, issued_in_window=0, oldest_in_window=None) == RateLimitDecision(True, DISABLED, None)
    assert decide(policy=politica, now=NOW, issued_in_window=9999, oldest_in_window=NOW - timedelta(seconds=5)) == RateLimitDecision(True, DISABLED, None)


@pytest.mark.parametrize("ventana", [1, 60, 3600])
def test_rlr_02_window_start_retrocede_exactamente_la_ventana(ventana: int) -> None:
    assert window_start(_politica(window_seconds=ventana), NOW) == NOW - timedelta(seconds=ventana)


@pytest.mark.parametrize(("capacity", "issued"), [(1, 0), (3, 0), (3, 1), (3, 2), (120, 0), (120, 119)])
def test_rlr_03_por_debajo_de_la_capacidad_se_admite(capacity: int, issued: int) -> None:
    assert decide(policy=_politica(capacity), now=NOW, issued_in_window=issued, oldest_in_window=NOW - timedelta(seconds=1)) == RateLimitDecision(True, OK, None)


@pytest.mark.parametrize("capacity", [1, 3, 120])
@pytest.mark.parametrize("exceso", [0, 1, 1000])
def test_rlr_04_en_la_capacidad_o_por_encima_se_rechaza(capacity: int, exceso: int) -> None:
    decision = decide(policy=_politica(capacity), now=NOW, issued_in_window=capacity + exceso, oldest_in_window=NOW)
    assert decision == RateLimitDecision(False, CAPACITY_EXCEEDED, 60)


@pytest.mark.parametrize(("antiguedad", "esperado"), [(0, 60), (0.4, 60), (50, 10), (59.2, 1), (59.9, 1), (60, 1), (70, 1)])
def test_rlr_05_retry_after_es_el_tiempo_hasta_que_el_mas_antiguo_salga_acotado_a_la_ventana(antiguedad: float, esperado: int) -> None:
    decision = decide(policy=_politica(capacity=1), now=NOW, issued_in_window=1, oldest_in_window=NOW - timedelta(seconds=antiguedad))
    assert decision == RateLimitDecision(False, CAPACITY_EXCEEDED, esperado)


def test_rlr_06_sin_instante_del_mas_antiguo_la_espera_es_la_ventana_entera() -> None:
    assert decide(policy=_politica(capacity=1, window_seconds=7), now=NOW, issued_in_window=1, oldest_in_window=None) == RateLimitDecision(False, CAPACITY_EXCEEDED, 7)


@pytest.mark.parametrize("issued", [-1, -100])
def test_rlr_07_un_recuento_negativo_es_un_error(issued: int) -> None:
    with pytest.raises(ValueError):
        decide(policy=_politica(), now=NOW, issued_in_window=issued, oldest_in_window=None)


@pytest.mark.parametrize(("capacity", "window"), [(0, 60), (-1, 60), (120, 0), (120, -1)])
def test_rlr_08_una_politica_invalida_no_se_construye(capacity: int, window: int) -> None:
    with pytest.raises(ValueError):
        RateLimitPolicy(enabled=True, capacity=capacity, window_seconds=window)


def test_rlr_09_los_ajustes_por_defecto_activan_el_limite_con_120_por_60_s() -> None:
    ajustes = Settings(environment="qa", **BASE)
    assert (ajustes.sync_challenge_rate_limit_enabled, ajustes.sync_challenge_rate_limit_capacity, ajustes.sync_challenge_rate_limit_window_seconds) == (True, 120, 60)


@pytest.mark.parametrize(("capacity", "window"), [(0, 60), (100_001, 60), (120, 0), (120, 3601)])
def test_rlr_10_los_ajustes_fuera_de_rango_no_cargan(capacity: int, window: int) -> None:
    with pytest.raises(ValueError):
        Settings(environment="qa", sync_challenge_rate_limit_capacity=capacity, sync_challenge_rate_limit_window_seconds=window, **BASE)


@pytest.mark.parametrize(("capacity", "window"), [(1, 1), (100_000, 1), (1, 3600), (100_000, 3600)])
def test_rlr_10b_los_extremos_validos_cargan(capacity: int, window: int) -> None:
    ajustes = Settings(environment="qa", sync_challenge_rate_limit_capacity=capacity, sync_challenge_rate_limit_window_seconds=window, **BASE)
    assert (ajustes.sync_challenge_rate_limit_capacity, ajustes.sync_challenge_rate_limit_window_seconds) == (capacity, window)


def test_rlr_11_en_prod_el_limite_no_se_apaga_y_en_qa_si() -> None:
    clave = pem_privada(Ed25519PrivateKey.generate())
    with pytest.raises(ValueError, match="RATE_LIMIT_ENABLED"):
        Settings(environment="prod", signing_private_key_pem=clave, sync_challenge_rate_limit_enabled=False, **BASE)
    assert Settings(environment="prod", signing_private_key_pem=clave, **BASE).sync_challenge_rate_limit_enabled is True
    assert Settings(environment="qa", sync_challenge_rate_limit_enabled=False, **BASE).sync_challenge_rate_limit_enabled is False


def test_rlr_12_decide_es_determinista_y_las_estructuras_son_inmutables() -> None:
    politica = _politica(capacity=1)
    resultados = {decide(policy=politica, now=NOW, issued_in_window=1, oldest_in_window=NOW - timedelta(seconds=30)) for _ in range(5)}
    assert resultados == {RateLimitDecision(False, CAPACITY_EXCEEDED, 30)}
    with pytest.raises(dataclasses.FrozenInstanceError):
        politica.capacity = 99  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        RateLimitDecision(True, OK, None).allowed = False  # type: ignore[misc]
