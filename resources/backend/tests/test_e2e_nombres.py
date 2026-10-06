"""E2ENOM · Los nombres de las bases efímeras del E2E (FR-054-E2EDB-002, 003).

El nombre de una base de una corrida es lo primero que mira la compuerta antes de
crear o eliminar cualquier cosa. Por eso aquí se prueba qué se acepta y, sobre todo,
qué no: el patrón se cumple entero o el nombre no es de una base de corrida.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "qa"))

import e2e_nombres as n  # noqa: E402

RUN = "r20261001t213355p4242n3fa9c1"
BASE = "kontrol_e2e_test_" + RUN
AHORA = datetime(2026, 10, 1, 21, 33, 55, tzinfo=UTC)
BUENA = (
    "kontrol-e2e run="
    + RUN
    + " pid=4242 maquina=h creado=2026-10-01T21:33:55+00:00"
)


def test_e2enom_01_el_run_id_sale_de_la_fecha_el_proceso_y_el_nonce():
    assert n.nuevo_run_id(AHORA, 4242, "3fa9c1") == RUN


def test_e2enom_02_el_run_id_se_escribe_en_utc():
    caracas = timezone(timedelta(hours=-4))
    assert (
        n.nuevo_run_id(datetime(2026, 10, 1, 17, 33, 55, tzinfo=caracas), 4242, "3fa9c1")
        == RUN
    )


@pytest.mark.parametrize(
    "ahora, pid, nonce",
    [
        (datetime(2026, 10, 1, 21, 33, 55), 4242, "3fa9c1"),
        (AHORA, 0, "3fa9c1"),
        (AHORA, -1, "3fa9c1"),
        (AHORA, 10_000_000, "3fa9c1"),
        (AHORA, True, "3fa9c1"),
        (AHORA, "4242", "3fa9c1"),
        (AHORA, 4242, "3FA9C1"),
        (AHORA, 4242, "3fa9c"),
        (AHORA, 4242, "3fa9c1a"),
        (AHORA, 4242, "zzzzzz"),
        (AHORA, 4242, None),
    ],
)
def test_e2enom_03_un_run_id_no_se_fabrica_con_datos_invalidos(ahora, pid, nonce):
    with pytest.raises(ValueError):
        n.nuevo_run_id(ahora, pid, nonce)


def test_e2enom_04_el_nombre_lleva_los_dos_marcadores_y_cabe_en_postgresql():
    assert n.nombre_de_base(RUN) == BASE
    assert "e2e" in BASE and "test" in BASE
    largo = n.nombre_de_base(n.nuevo_run_id(AHORA, 9_999_999, "ffffff"))
    assert len(largo) == 48 and len(largo) <= 63


def test_e2enom_05_ida_y_vuelta():
    assert n.run_de_base(n.nombre_de_base(RUN)) == RUN
    assert n.es_base_e2e(BASE) is True


@pytest.mark.parametrize(
    "nombre",
    [
        "kaud",
        "ktest",
        "postgres",
        "template0",
        "template1",
        "kontrol",
        "kontrol_e2e",
        "kontrol_e2e_test_",
        "kontrol_test_" + RUN,
        "kontrol_e2e_" + RUN,
        "e2e_test_" + RUN,
        BASE + "x",
        BASE + "\n",
        " " + BASE,
        BASE + " ",
        "x" + BASE,
        BASE.upper(),
        BASE + "; drop database kaud",
        BASE + '"',
        "kontrol_e2e_test_r20261001t213355p4242n3FA9C1",
        "kontrol_e2e_test_r2026100t213355p4242n3fa9c1",
        "kontrol_e2e_test_r20261001t213355p12345678n3fa9c1",
        "kontrol_e2e_test_r20261001t213355pn3fa9c1",
        "kontrol_e2e_test_proto_173514",
        "",
        None,
        7,
        b"kontrol_e2e_test_r20261001t213355p4242n3fa9c1",
    ],
)
def test_e2enom_06_lo_que_no_cumple_el_patron_entero_no_es_una_base_e2e(nombre):
    assert n.run_de_base(nombre) is None
    assert n.es_base_e2e(nombre) is False


@pytest.mark.parametrize(
    "run", ["", "r20261001", RUN + "x", RUN.upper(), "x" + RUN, RUN + "\n", None, 7]
)
def test_e2enom_07_ni_el_nombre_ni_la_aplicacion_se_construyen_con_un_run_invalido(run):
    with pytest.raises(ValueError):
        n.nombre_de_base(run)
    with pytest.raises(ValueError):
        n.aplicacion(run)


def test_e2enom_08_la_aplicacion_identifica_las_conexiones_de_la_corrida():
    assert n.aplicacion(RUN) == "kontrol-e2e:" + RUN
    assert len(n.aplicacion(n.nuevo_run_id(AHORA, 9_999_999, "ffffff"))) <= 63


def test_e2enom_09_la_marca_dice_quien_creo_la_base_y_cuando():
    texto = n.marca(RUN, 4242, "qa-host.local", AHORA)
    assert (
        texto
        == "kontrol-e2e run=" + RUN + " pid=4242 maquina=qa-host.local creado=2026-10-01T21:33:55+00:00"
    )
    assert texto.startswith(n.PREFIJO_DE_MARCA)
    assert n.leer_marca(texto) == {
        "run": RUN,
        "pid": "4242",
        "maquina": "qa-host.local",
        "creado": "2026-10-01T21:33:55+00:00",
    }


def test_e2enom_10_la_marca_tambien_se_escribe_en_utc():
    caracas = timezone(timedelta(hours=-4))
    assert n.marca(
        RUN, 4242, "h", datetime(2026, 10, 1, 17, 33, 55, tzinfo=caracas)
    ).endswith("creado=2026-10-01T21:33:55+00:00")


@pytest.mark.parametrize(
    "run, pid, maquina, creado",
    [
        ("malo", 4242, "h", AHORA),
        (RUN, 0, "h", AHORA),
        (RUN, True, "h", AHORA),
        (RUN, 4242, "", AHORA),
        (RUN, 4242, "con espacio", AHORA),
        (RUN, 4242, "h' ; --", AHORA),
        (RUN, 4242, "h" * 65, AHORA),
        (RUN, 4242, None, AHORA),
        (RUN, 4242, "h", datetime(2026, 10, 1, 21, 33, 55)),
    ],
)
def test_e2enom_11_una_marca_no_se_escribe_con_datos_invalidos(run, pid, maquina, creado):
    with pytest.raises(ValueError):
        n.marca(run, pid, maquina, creado)


@pytest.mark.parametrize(
    "texto",
    [
        "",
        "kontrol-e2e prototipo",
        "kontrol-test pid=1 creado=2026-10-01T21:33:55+00:00",
        BUENA + " ",
        BUENA + "\n",
        " " + BUENA,
        BUENA.replace("run=", "run=x"),
        BUENA.replace("pid=4242", "pid="),
        BUENA.replace("+00:00", "-04:00"),
        BUENA.replace("maquina=h", "maquina=h h"),
        None,
        7,
    ],
)
def test_e2enom_12_lo_que_no_es_exactamente_una_marca_no_se_lee_como_marca(texto):
    assert n.leer_marca(texto) is None


def test_e2enom_12_la_marca_buena_si_se_lee():
    assert n.leer_marca(BUENA) is not None
