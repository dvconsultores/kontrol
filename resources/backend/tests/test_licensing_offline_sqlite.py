"""OFF · La tolerancia offline decide lo mismo en SQLite y en PostgreSQL (OFFLINE-NAIVE-EN-SQLITE; FR-010-003).

`last_reliable_date` es un instante: lo escribe `_now()` (UTC) o el `server_time` del sync autenticado.
SQLite guarda `DateTime(timezone=True)` como hora de pared sin zona y lo devuelve **naive**; PostgreSQL
(`timestamptz`) conserva el instante. `verify_offline` sumaba la gracia al valor crudo y lo comparaba con
`now` aware: `TypeError` y 500 en `/licensing/overview` y `/licensing/offline-status` solo sobre SQLite.
Todas las pruebas recargan el estado desde la base en una sesión nueva (la de cada petición HTTP o una
abierta aquí): el objeto recién escrito en memoria conserva la zona y esconde el defecto. Reloj fijo.
"""
from __future__ import annotations

import os
import time
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.modules.licensing import service as licensing_service
from app.modules.licensing.models import LicenseState
from tests.test_license_access import _mundo, _sesion
from tests.test_licensing_central import _configure_central

PG = os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql")
#: Reloj fijo de la tolerancia offline: ninguna prueba cruza una frontera por el paso del tiempo real.
AHORA = datetime(2026, 10, 13, 12, 0, 0, tzinfo=UTC)
GRACIA = 7
_FACTORY: sessionmaker


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[None]:
    global _CLIENTE, _FACTORY
    _CLIENTE, _FACTORY = _mundo(con_licencia=True)
    with _FACTORY() as db:
        _configure_central(db)
        db.commit()
    yield


@pytest.fixture(autouse=True)
def _reloj_fijo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(licensing_service, "_now", lambda: AHORA)


def _fijar_fecha_confiable(valor: datetime | None) -> None:
    """Escribe el instante, confirma y cierra: lo que venga después se lee de la base, no de la memoria."""
    with _FACTORY() as db:
        estado = db.execute(select(LicenseState)).scalars().one()
        estado.last_reliable_date = valor
        db.commit()


def _leida_de_la_base() -> datetime | None:
    with _FACTORY() as db:
        return db.execute(select(LicenseState)).scalars().one().last_reliable_date


def _pedir(ruta: str, usuario: str = "admin"):
    return _CLIENTE.get(f"/api/v1/licensing/{ruta}", headers=_sesion(usuario, _CLIENTE))


# ----------------------------------------------------------------------------- OFF-01 · lo que devuelve cada motor
def test_off_01_la_base_devuelve_el_instante_con_o_sin_zona_segun_el_motor():
    _fijar_fecha_confiable(AHORA - timedelta(days=2))
    leido = _leida_de_la_base()
    assert leido is not None
    if PG:
        assert leido.tzinfo is not None and leido == AHORA - timedelta(days=2)
    else:
        # SQLite: la misma hora de pared, sin zona. Etiquetarla UTC devuelve el instante persistido.
        assert leido.tzinfo is None and leido.replace(tzinfo=UTC) == AHORA - timedelta(days=2)


# ----------------------------------------------------------------------------- OFF-02/03/04/05/08 · dentro de la gracia
def test_off_02_03_dentro_de_la_gracia_los_dos_endpoints_responden_200_con_la_misma_decision():
    _fijar_fecha_confiable(AHORA - timedelta(days=2))
    estado = _pedir("offline-status")
    assert estado.status_code == 200, estado.text
    cuerpo = estado.json()
    assert cuerpo == {
        "offline_valid": True, "reason": "WITHIN_GRACE", "grace_days": GRACIA, "grace_days_left": 5,
        "grace_end": (AHORA + timedelta(days=5)).isoformat(), "last_reliable_date": (AHORA - timedelta(days=2)).isoformat(),
    }
    vista = _pedir("overview")
    assert vista.status_code == 200, vista.text
    assert vista.json()["offline"] == cuerpo


# ----------------------------------------------------------------------------- OFF-09 · frontera exacta
def test_off_09_en_la_frontera_exacta_de_la_gracia_sigue_dentro():
    # El contrato vigente rechaza solo cuando `now` SUPERA el fin de gracia: en el instante justo quedan 0 días y sigue válido.
    _fijar_fecha_confiable(AHORA - timedelta(days=GRACIA))
    cuerpo = _pedir("offline-status").json()
    assert cuerpo["offline_valid"] is True and cuerpo["reason"] == "WITHIN_GRACE" and cuerpo["grace_days_left"] == 0
    assert cuerpo["grace_end"] == AHORA.isoformat()
    _fijar_fecha_confiable(AHORA - timedelta(days=GRACIA, seconds=1))
    cuerpo = _pedir("offline-status").json()
    assert cuerpo["offline_valid"] is False and cuerpo["reason"] == "GRACE_EXPIRED"


# ----------------------------------------------------------------------------- OFF-10 · fuera de la ventana
def test_off_10_fuera_de_la_ventana_la_gracia_esta_vencida_en_los_dos_motores():
    _fijar_fecha_confiable(AHORA - timedelta(days=30))
    estado = _pedir("offline-status")
    assert estado.status_code == 200, estado.text
    assert estado.json() == {
        "offline_valid": False, "reason": "GRACE_EXPIRED", "grace_days": GRACIA, "grace_days_left": 0,
        "grace_end": (AHORA - timedelta(days=23)).isoformat(), "last_reliable_date": (AHORA - timedelta(days=30)).isoformat(),
    }
    assert _pedir("overview").status_code == 200


# ----------------------------------------------------------------------------- OFF-07 · sin fecha confiable
def test_off_07_sin_fecha_confiable_se_conserva_el_comportamiento():
    _fijar_fecha_confiable(None)
    assert _pedir("offline-status").json() == {"offline_valid": False, "reason": "NO_RELIABLE_DATE", "grace_days": GRACIA, "grace_days_left": 0}
    assert _pedir("overview").status_code == 200


# ----------------------------------------------------------------------------- OFF-11 · la zona del equipo no decide nada
@pytest.mark.parametrize("zona", ["UTC", "America/Caracas", "Asia/Tokyo"])
def test_off_11_la_zona_horaria_del_proceso_no_cambia_la_decision(zona: str, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TZ", zona)
    time.tzset()
    try:
        _fijar_fecha_confiable(AHORA - timedelta(days=2))
        cuerpo = _pedir("offline-status").json()
        assert cuerpo["offline_valid"] is True and cuerpo["grace_days_left"] == 5
        assert cuerpo["last_reliable_date"] == (AHORA - timedelta(days=2)).isoformat()
    finally:
        monkeypatch.delenv("TZ", raising=False)
        time.tzset()


# ----------------------------------------------------------------------------- OFF-12 · el objeto en memoria esconde el defecto
@pytest.mark.skipif(PG, reason="documenta la conducta de SQLite: en PostgreSQL la zona nunca se pierde")
def test_off_12_sin_recargar_desde_la_base_el_valor_conserva_la_zona_y_no_demuestra_nada():
    with _FACTORY() as db:
        estado = db.execute(select(LicenseState)).scalars().one()
        estado.last_reliable_date = AHORA - timedelta(days=2)
        db.commit()
        assert estado.last_reliable_date.tzinfo is not None, "en la misma sesión el objeto sigue con zona"
    assert _leida_de_la_base().tzinfo is None, "recargado, SQLite lo devuelve sin zona: esto es lo que hay que probar"


# ----------------------------------------------------------------------------- OFF-14 · precedencia
def test_off_14_sin_permiso_sigue_siendo_403_antes_que_cualquier_decision_offline():
    _fijar_fecha_confiable(AHORA - timedelta(days=2))
    r = _pedir("offline-status", "operador")
    assert r.status_code == 403 and r.json()["code"] == "PERMISSION_DENIED"
    assert _CLIENTE.get("/api/v1/licensing/overview").status_code == 401
