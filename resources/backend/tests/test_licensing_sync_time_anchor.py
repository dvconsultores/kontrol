"""OBS-11 · la referencia temporal del sync de licenciamiento nace en la operación, no al importar (Spec 010, FR-010-003; 054).

`test_sync_success_records_run_snapshot_and_event` comparaba `last_reliable_date` con una constante de módulo evaluada al
importar (`SERVER_TIME = ahora + 5 min`). En cualquier suite que tarde más de cinco minutos en llegar al módulo la activación
de la licencia ya es posterior a esa referencia y el producto, correctamente monótono, conserva la activación: la prueba
fallaba sin defecto. Estas regresiones fijan la causa de forma determinista, sin sleep ni tolerancias.
"""

from __future__ import annotations

import ast
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.core import license_contract
from app.modules.licensing import service as licensing_service
from tests.test_licensing_central import (
    _activate_license,
    _configure_central,
    _fake_sync_client,
    _setup,
    select_installation,
    select_state,
)

_MODULO = Path(__file__).with_name("test_licensing_central.py")
_SERVICIO = Path(__file__).resolve().parents[1] / "app" / "modules" / "licensing" / "service.py"
_PROHIBIDOS = ("sleep(", "retry", "pytest.skip", "pytest.xfail", "flaky", "reruns", "pytest.approx", "utcnow(", "datetime.now()")


def _reloj_confiable(db) -> datetime:
    installation = db.execute(select_installation()).scalars().first()
    assert installation is not None
    state = db.execute(select_state(installation.installation_uuid)).scalars().first()
    assert state is not None
    return license_contract._as_utc(state.last_reliable_date)


def _respuesta(server_time: datetime) -> dict:
    return {"version": "1", "status": "NO_LICENSE", "server_time": server_time.isoformat(), "license": None}


def test_o11_01_el_servidor_posterior_a_la_activacion_se_adopta_exactamente(sesion_de_prueba) -> None:
    _setup(sesion_de_prueba)
    _activate_license(sesion_de_prueba)
    _configure_central(sesion_de_prueba)
    activacion = _reloj_confiable(sesion_de_prueba)

    transporte = _fake_sync_client()
    assert activacion < transporte.server_time  # orden causal: la referencia nace después de la activación
    assert transporte.server_time.tzinfo is not None and transporte.server_time.microsecond == 0

    resultado = licensing_service.sync_license(sesion_de_prueba, transport=transporte, actor="admin")

    assert resultado["status"] == "SUCCESS"
    assert _reloj_confiable(sesion_de_prueba) == transporte.server_time


def test_o11_02_la_referencia_envejecida_no_hace_retroceder_el_reloj_confiable(sesion_de_prueba) -> None:
    """Escenario envejecido determinista: el reloj del servidor queda detrás de la activación (como la constante de módulo
    tras más de cinco minutos). El producto conserva la activación; la prueba antigua lo etiquetaba como fallo."""
    _setup(sesion_de_prueba)
    _activate_license(sesion_de_prueba)
    _configure_central(sesion_de_prueba)
    activacion = _reloj_confiable(sesion_de_prueba)

    envejecido = (activacion - timedelta(minutes=1)).replace(microsecond=0)
    transporte = _fake_sync_client(response=_respuesta(envejecido))
    resultado = licensing_service.sync_license(sesion_de_prueba, transport=transporte, actor="admin")

    assert resultado["status"] == "SUCCESS"
    assert _reloj_confiable(sesion_de_prueba) == activacion
    assert _reloj_confiable(sesion_de_prueba) > envejecido


def test_o11_03_dos_syncs_sucesivos_mantienen_el_maximo(sesion_de_prueba) -> None:
    _setup(sesion_de_prueba)
    _activate_license(sesion_de_prueba)
    _configure_central(sesion_de_prueba)

    primero = _fake_sync_client()
    licensing_service.sync_license(sesion_de_prueba, transport=primero, actor="admin")
    assert _reloj_confiable(sesion_de_prueba) == primero.server_time

    anterior = (primero.server_time - timedelta(minutes=2)).replace(microsecond=0)
    segundo = _fake_sync_client(response=_respuesta(anterior))
    licensing_service.sync_license(sesion_de_prueba, transport=segundo, actor="admin")
    assert _reloj_confiable(sesion_de_prueba) == primero.server_time


def test_o11_04_el_transporte_falso_captura_su_reloj_en_la_operacion() -> None:
    antes = datetime.now(UTC)
    transporte = _fake_sync_client()
    despues = datetime.now(UTC)

    assert antes + timedelta(minutes=5) - timedelta(seconds=1) <= transporte.server_time <= despues + timedelta(minutes=5)
    assert transporte.response["server_time"] == transporte.server_time.isoformat()
    assert transporte.challenge("https://central.kontrol.example", "inst")["expires_at"] == transporte.server_time.isoformat()


def test_o11_05_contrato_estatico_del_modulo_objetivo() -> None:
    fuente = _MODULO.read_text(encoding="utf-8")
    arbol = ast.parse(fuente)

    # ninguna constante de módulo nace de un reloj: la referencia se captura en la operación
    for nodo in arbol.body:
        if isinstance(nodo, ast.Assign):
            llamadas = {n.func.attr for n in ast.walk(nodo.value) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
            assert not llamadas & {"now", "utcnow", "today"}, ast.unparse(nodo)
    assert "SERVER_TIME" not in fuente

    transporte = next(n for n in arbol.body if isinstance(n, ast.ClassDef) and n.name == "_TransporteFalso")
    init = next(n for n in transporte.body if isinstance(n, ast.FunctionDef) and n.name == "__init__")
    primera = init.body[0]
    assert isinstance(primera, ast.Assign) and ast.unparse(primera.targets[0]) == "self.server_time"
    assert "datetime.now(UTC)" in ast.unparse(primera.value) and "microsecond=0" in ast.unparse(primera.value)

    clase = next(n for n in arbol.body if isinstance(n, ast.ClassDef) and n.name == "TestSincronizacion")
    objetivo = next(n for n in clase.body if isinstance(n, ast.FunctionDef) and n.name == "test_sync_success_records_run_snapshot_and_event")
    aserciones = [ast.unparse(n.test) for n in ast.walk(objetivo) if isinstance(n, ast.Assert)]
    assert "state.last_reliable_date.replace(tzinfo=UTC) == transporte.server_time" in aserciones
    cuerpo = ast.unparse(objetivo)
    assert "approx" not in cuerpo and "abs(" not in cuerpo and "timedelta" not in cuerpo
    for prohibido in _PROHIBIDOS:
        assert prohibido not in fuente, prohibido

    # estas regresiones tampoco esperan ni toleran: cada marca aparece una sola vez, en la lista de prohibiciones
    propio = Path(__file__).read_text(encoding="utf-8")
    for prohibido in _PROHIBIDOS:
        assert propio.count(prohibido) == 1, prohibido

    # la regresión envejecida conserva sus dos aserciones: igualdad con la activación y posterioridad al servidor envejecido
    envejecida = next(n for n in ast.parse(propio).body if isinstance(n, ast.FunctionDef) and n.name == "test_o11_02_la_referencia_envejecida_no_hace_retroceder_el_reloj_confiable")
    aserciones_envejecida = [ast.unparse(n.test) for n in ast.walk(envejecida) if isinstance(n, ast.Assert)]
    assert "_reloj_confiable(sesion_de_prueba) == activacion" in aserciones_envejecida
    assert "_reloj_confiable(sesion_de_prueba) > envejecido" in aserciones_envejecida


def test_o11_06_centinela_del_reloj_canonico_del_producto() -> None:
    ahora = licensing_service._now()
    assert ahora.tzinfo is not None and ahora.utcoffset() == timedelta(0)

    fuente = _SERVICIO.read_text(encoding="utf-8")
    assert "state.last_reliable_date = _utc(recibido) if actual is None or license_contract._as_utc(actual) < license_contract._as_utc(recibido) else actual" in fuente
    assert "state.last_reliable_date = _utc(last_reliable or _now())" in fuente
