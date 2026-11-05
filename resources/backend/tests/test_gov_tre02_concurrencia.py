import itertools
import os
import threading

import pytest

from tests.test_gov_ctl06_hallazgos import ANIO
from tests.test_gov_tre01_cuentas import cuenta_vigente
from tests.tre02_ayudantes import (
    MOTIVO,
    activar_programa,
    crear_programa,
    crear_rubro,
    declarar,
    linea,
    programa_vigente,
    reprogramar,
    ver,
)

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos")

pytestmark = pytest.mark.skipif(
    not os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql"),
    reason="la carrera con bloqueo de fila se mide en PostgreSQL",
)

_ejercicios = itertools.count(ANIO)


def _cabeceras(mundo, usuario, empresa, version):
    cabeceras = mundo.como(usuario, empresa)
    cabeceras["If-Match"] = str(version)
    return cabeceras


def _siguiente_ejercicio() -> int:
    ejercicio = next(_ejercicios)
    assert ejercicio <= ANIO + 40
    return ejercicio


def _correr_dos_hilos(
    mundo, url_a, url_b, cabeceras_a, cabeceras_b, cuerpo_a=None, cuerpo_b=None
):
    resultados = {}
    barrera = threading.Barrier(2, timeout=30)

    def hilo(nombre, url, cabeceras, cuerpo=None):
        barrera.wait()
        resultados[nombre] = mundo.client.post(url, headers=cabeceras, json=cuerpo)

    hilos = [
        threading.Thread(target=hilo, args=("h1", url_a, cabeceras_a, cuerpo_a)),
        threading.Thread(target=hilo, args=("h2", url_b, cabeceras_b, cuerpo_b)),
    ]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=60)
        assert not h.is_alive()
    return resultados


def test_cc01_dos_reprogramar(mundo, siembra, gobierno):
    """CC-01 dos reprogramar con la misma versión: un 201 y un 409 STALE o DRAFT_OPEN; un solo borrador."""
    ejercicio = _siguiente_ejercicio()
    cargo = siembra["cargo_vigente"]
    cuenta = cuenta_vigente(mundo, cargo)
    programa = crear_programa(mundo, ejercicio)
    rubro = crear_rubro(mundo, "INGRESO")
    programa = declarar(mundo, programa, cuenta, "1000.00")
    programa = linea(mundo, programa, rubro, 1, "500.00")
    programa = activar_programa(mundo, programa)

    url = f"/api/v1/gobierno/tesoreria/programas/{programa['id']}/reprogramar"
    cabeceras = _cabeceras(mundo, "ua", mundo.company_a, programa["version"])
    cuerpo = {"motivo": MOTIVO}
    resultados = _correr_dos_hilos(mundo, url, url, cabeceras, cabeceras, cuerpo, cuerpo)

    codigos = sorted(r.status_code for r in resultados.values())
    assert codigos == [201, 409]

    error_409 = next(r for r in resultados.values() if r.status_code == 409)
    assert error_409.json()["code"] in (
        "GOV_CASH_PROGRAM_STALE",
        "GOV_CASH_PROGRAM_DRAFT_OPEN",
    )

    detalle = ver(mundo, programa)
    borradores = [v for v in detalle["versiones"] if v["estado"] == "BORRADOR"]
    assert len(borradores) == 1


def test_cc02_activar_contra_linea(mundo, siembra, gobierno):
    """CC-02 activar contra añadir línea, misma versión: exactamente un éxito y un 409 STALE."""
    ejercicio = _siguiente_ejercicio()
    cargo = siembra["cargo_vigente"]
    cuenta = cuenta_vigente(mundo, cargo)
    programa = crear_programa(mundo, ejercicio)
    rubro_ingreso = crear_rubro(mundo, "INGRESO")
    rubro_desembolso = crear_rubro(mundo, "DESEMBOLSO")
    programa = declarar(mundo, programa, cuenta, "1000.00")
    programa = linea(mundo, programa, rubro_ingreso, 1, "500.00")

    url_activar = f"/api/v1/gobierno/tesoreria/programas/{programa['id']}/activar"
    url_linea = f"/api/v1/gobierno/tesoreria/programas/{programa['id']}/lineas"
    cabeceras = _cabeceras(mundo, "ua", mundo.company_a, programa["version"])
    cuerpo_linea = {"rubro_id": rubro_desembolso["id"], "mes": 2, "monto": "100.00"}

    resultados = {}
    barrera = threading.Barrier(2, timeout=30)

    def hilo(nombre, url, cabeceras, cuerpo=None):
        barrera.wait()
        if cuerpo is None:
            resultados[nombre] = mundo.client.post(url, headers=cabeceras)
        else:
            resultados[nombre] = mundo.client.post(url, headers=cabeceras, json=cuerpo)

    hilos = [
        threading.Thread(target=hilo, args=("activar", url_activar, cabeceras)),
        threading.Thread(target=hilo, args=("linea", url_linea, cabeceras, cuerpo_linea)),
    ]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=60)
        assert not h.is_alive()

    codigos = sorted(r.status_code for r in resultados.values())
    assert codigos in ([200, 409], [201, 409])

    error_409 = next(r for r in resultados.values() if r.status_code == 409)
    assert error_409.json()["code"] == "GOV_CASH_PROGRAM_STALE"

    detalle = ver(mundo, programa)
    if resultados["activar"].status_code == 200:
        assert detalle["estado"] == "VIGENTE"
        assert len(detalle["lineas"]) == 1
    else:
        assert resultados["linea"].status_code == 201
        assert detalle["estado"] == "BORRADOR"
        assert len(detalle["lineas"]) == 2


def test_cc03_misma_linea_a_la_vez(mundo, siembra, gobierno):
    """CC-03 misma línea (rubro y mes) a la vez: un 201 y un 409 STALE o LINE_DUPLICATE; una sola línea."""
    ejercicio = _siguiente_ejercicio()
    cargo = siembra["cargo_vigente"]
    cuenta = cuenta_vigente(mundo, cargo)
    programa = crear_programa(mundo, ejercicio)
    rubro = crear_rubro(mundo, "INGRESO")
    programa = declarar(mundo, programa, cuenta, "1000.00")

    url = f"/api/v1/gobierno/tesoreria/programas/{programa['id']}/lineas"
    cabeceras = _cabeceras(mundo, "ua", mundo.company_a, programa["version"])
    cuerpo = {"rubro_id": rubro["id"], "mes": 1, "monto": "500.00"}

    resultados = {}
    barrera = threading.Barrier(2, timeout=30)

    def hilo(nombre):
        barrera.wait()
        resultados[nombre] = mundo.client.post(url, headers=cabeceras, json=cuerpo)

    hilos = [
        threading.Thread(target=hilo, args=("h1",)),
        threading.Thread(target=hilo, args=("h2",)),
    ]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=60)
        assert not h.is_alive()

    codigos = sorted(r.status_code for r in resultados.values())
    assert codigos == [201, 409]

    error_409 = next(r for r in resultados.values() if r.status_code == 409)
    assert error_409.json()["code"] in (
        "GOV_CASH_PROGRAM_STALE",
        "GOV_CASH_LINE_DUPLICATE",
    )

    detalle = ver(mundo, programa)
    lineas_rubro_mes = [
        linea_detalle
        for linea_detalle in detalle["lineas"]
        if linea_detalle["rubro_id"] == rubro["id"] and linea_detalle["mes"] == 1
    ]
    assert len(lineas_rubro_mes) == 1


def test_cc04_cerrar_contra_reprogramar(mundo, siembra, gobierno):
    """CC-04 cerrar contra reprogramar: un éxito y un 409; el estado final es coherente con el ganador."""
    ejercicio = _siguiente_ejercicio()
    cargo = siembra["cargo_vigente"]
    cuenta = cuenta_vigente(mundo, cargo)
    programa = crear_programa(mundo, ejercicio)
    rubro = crear_rubro(mundo, "INGRESO")
    programa = declarar(mundo, programa, cuenta, "1000.00")
    programa = linea(mundo, programa, rubro, 1, "500.00")
    programa = activar_programa(mundo, programa)

    base_url = f"/api/v1/gobierno/tesoreria/programas/{programa['id']}"
    url_cerrar = f"{base_url}/cerrar"
    url_reprogramar = f"{base_url}/reprogramar"
    cabeceras_cerrar = _cabeceras(mundo, "ua", mundo.company_a, programa["version"])
    cabeceras_reprogramar = _cabeceras(
        mundo, "ua", mundo.company_a, programa["version"]
    )

    resultados = {}
    barrera = threading.Barrier(2, timeout=30)

    def hilo_cerrar():
        barrera.wait()
        resultados["cerrar"] = mundo.client.post(
            url_cerrar, headers=cabeceras_cerrar, json={"motivo": MOTIVO}
        )

    def hilo_reprogramar():
        barrera.wait()
        resultados["reprogramar"] = mundo.client.post(
            url_reprogramar, headers=cabeceras_reprogramar, json={"motivo": MOTIVO}
        )

    hilos = [
        threading.Thread(target=hilo_cerrar),
        threading.Thread(target=hilo_reprogramar),
    ]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=60)
        assert not h.is_alive()

    codigos = sorted(r.status_code for r in resultados.values())
    assert codigos in ([200, 409], [201, 409])

    detalle = ver(mundo, programa)
    if resultados["cerrar"].status_code == 200:
        assert detalle["estado"] == "CERRADO"
        assert all(v["estado"] != "BORRADOR" for v in detalle["versiones"])
    else:
        assert resultados["reprogramar"].status_code == 201
        assert detalle["estado"] == "VIGENTE"
        assert any(v["estado"] == "BORRADOR" for v in detalle["versiones"])


def test_cc05_dos_activaciones_de_reprogramacion(mundo, siembra, gobierno):
    """CC-05 dos activaciones de la reprogramación: un 200 y un 409; una sola versión vigente, y la anterior superada una sola vez."""
    ejercicio = _siguiente_ejercicio()
    cargo = siembra["cargo_vigente"]
    programa = programa_vigente(mundo, cargo, ejercicio)
    programa = reprogramar(mundo, programa)

    url = f"/api/v1/gobierno/tesoreria/programas/{programa['id']}/activar"
    cabeceras = _cabeceras(mundo, "ua", mundo.company_a, programa["version"])
    resultados = _correr_dos_hilos(mundo, url, url, cabeceras, cabeceras, {}, {})

    codigos = sorted(r.status_code for r in resultados.values())
    assert codigos == [200, 409]

    detalle = ver(mundo, programa)
    vigentes = [v for v in detalle["versiones"] if v["estado"] == "VIGENTE"]
    superadas = [v for v in detalle["versiones"] if v["estado"] == "SUPERADA"]
    assert len(vigentes) == 1
    assert len(superadas) == 1


def test_cc06_dos_altas_del_mismo_programa(mundo, gobierno):
    """CC-06 dos altas del mismo programa: un 201 y un 409 GOV_CASH_PROGRAM_DUPLICATE."""
    ejercicio = _siguiente_ejercicio()
    url = "/api/v1/gobierno/tesoreria/programas"
    cabeceras = mundo.como("ua", mundo.company_a)
    cuerpo = {"ejercicio": ejercicio, "moneda": "VES", "mes_inicial": 1}

    resultados = {}
    barrera = threading.Barrier(2, timeout=30)

    def hilo(nombre):
        barrera.wait()
        resultados[nombre] = mundo.client.post(url, headers=cabeceras, json=cuerpo)

    hilos = [
        threading.Thread(target=hilo, args=("h1",)),
        threading.Thread(target=hilo, args=("h2",)),
    ]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=60)
        assert not h.is_alive()

    codigos = sorted(r.status_code for r in resultados.values())
    assert codigos == [201, 409]

    error_409 = next(r for r in resultados.values() if r.status_code == 409)
    assert error_409.json()["code"] == "GOV_CASH_PROGRAM_DUPLICATE"


@pytest.mark.parametrize("_iteracion", range(5))
def test_cc07_repeticion_dos_activaciones_de_reprogramacion(mundo, siembra, gobierno, _iteracion):
    """CC-07 repite CC-05 cinco veces."""
    ejercicio = _siguiente_ejercicio()
    cargo = siembra["cargo_vigente"]
    programa = programa_vigente(mundo, cargo, ejercicio)
    programa = reprogramar(mundo, programa)

    url = f"/api/v1/gobierno/tesoreria/programas/{programa['id']}/activar"
    cabeceras = _cabeceras(mundo, "ua", mundo.company_a, programa["version"])
    resultados = _correr_dos_hilos(mundo, url, url, cabeceras, cabeceras, {}, {})

    codigos = sorted(r.status_code for r in resultados.values())
    assert codigos == [200, 409]

    detalle = ver(mundo, programa)
    vigentes = [v for v in detalle["versiones"] if v["estado"] == "VIGENTE"]
    superadas = [v for v in detalle["versiones"] if v["estado"] == "SUPERADA"]
    assert len(vigentes) == 1
    assert len(superadas) == 1
