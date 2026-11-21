"""TRE-05 · Retención de Tesorería — pruebas backend en su propio mundo (casos 14 y 15)."""

from __future__ import annotations

import pytest

from tests.tre05_ayudantes import (
    aislar_caches,
    beneficiario,
    calcular,
    concepto,
    condicion,
    cuentas_t05,
    pago_listo,
    politica_ret,
    regla,
)

pytest_plugins = (
    "tests.conftest_multicompany",
    "tests.test_gov_ctl06_hallazgos",
    "tests.org04_ayudantes",
)


@pytest.fixture(scope="module", autouse=True)
def _aislar_caches_tre05c():
    aislar_caches()
    yield
    aislar_caches()


def test_t05_14_exclusiones_y_condiciones(mundo, gobierno, ocupacion):
    cuentas_t05(mundo)
    cond_excl = condicion(mundo)
    cond = condicion(mundo)
    concepto_a = concepto(mundo)
    concepto_b = concepto(mundo)

    politica = politica_ret(
        mundo,
        "VES",
        [
            regla(concepto_a, orden=1, exclusiones=[cond_excl["codigo"]]),
            regla(concepto_b, orden=2, condiciones_exigidas=[cond["codigo"]]),
        ],
    )

    datos = pago_listo(mundo, ocupacion, monto="10.00")
    r = calcular(
        mundo,
        datos["pago"],
        politica,
        [concepto_a["codigo"], concepto_b["codigo"]],
        beneficiario(tipo="JURIDICA", condiciones=[cond_excl["codigo"]]),
    )
    assert r.status_code == 201, r.text
    lineas = r.json()["lineas"]
    linea_a = next(linea for linea in lineas if linea["concepto_codigo"] == concepto_a["codigo"])
    linea_b = next(linea for linea in lineas if linea["concepto_codigo"] == concepto_b["codigo"])
    assert linea_a["motivo_no_aplica"] == "EXCLUSION"
    assert linea_b["motivo_no_aplica"] == "CONDICION_FALTANTE"

    datos2 = pago_listo(mundo, ocupacion, monto="10.00")
    r = calcular(
        mundo,
        datos2["pago"],
        politica,
        [concepto_b["codigo"]],
        beneficiario(tipo="JURIDICA", condiciones=[cond["codigo"]]),
    )
    assert r.status_code == 201, r.text
    lineas2 = r.json()["lineas"]
    linea_b2 = next(linea for linea in lineas2 if linea["concepto_codigo"] == concepto_b["codigo"])
    assert linea_b2["aplica"] is True


def test_t05_15_varias_reglas(mundo, gobierno, ocupacion):
    cuentas_t05(mundo)
    concepto_a = concepto(mundo)
    concepto_b = concepto(mundo)
    concepto_c = concepto(mundo)
    politica = politica_ret(
        mundo,
        "VES",
        [
            regla(concepto_a, orden=1, tasa="5"),
            regla(concepto_b, orden=2, tasa="2"),
            regla(concepto_c, orden=3, tasa="1"),
        ],
    )
    datos = pago_listo(mundo, ocupacion, monto="100.00")
    r = calcular(
        mundo,
        datos["pago"],
        politica,
        [concepto_a["codigo"], concepto_b["codigo"], concepto_c["codigo"]],
        beneficiario(),
    )
    assert r.status_code == 201, r.text
    liq = r.json()
    assert len(liq["lineas"]) == 3
    assert liq["total_retenido"] == "8.00"
    assert liq["neto"] == "92.00"
    assert all(linea["aplica"] for linea in liq["lineas"])
