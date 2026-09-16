"""Spec 038 · FLOAT-038-C — las seis fronteras monetarias que A y B dejaron abiertas.

Mismo contrato que sus dos predecesores: el dinero público viaja como texto decimal,
se convierte una sola vez a `Decimal`, y lo que no cabe en la escala de su columna se
rechaza en vez de redondearse. Lo que cambia aquí es sólo el conjunto de campos.

Cada campo conserva **su** regla de signo, que no es la misma para todos: el fondo de
apertura y los saldos de conciliación siempre admitieron cualquier signo, y los tres
importes con `gt=0` siguen exigiendo un valor positivo. Decimalizar no es ocasión para
homogeneizar reglas de negocio.

El detector de exactitud vuelve a ser `1234567890123456.78`: cabe en `numeric(18,2)`
y un `double` no lo representa. Si alguien reintroduce un `float` en el camino, ese
número vuelve como `...56.80` y la prueba lo dice.
"""

from __future__ import annotations

import itertools
import json
import uuid
from datetime import date
from decimal import Decimal

import pytest

pytest_plugins = ("tests.conftest_multicompany",)

EXACTO = "1234567890123456.78"
_serie = itertools.count(1)


def _n() -> str:
    return f"{next(_serie)}{uuid.uuid4().hex[:4]}"


def _caja(mundo, empresa: str | None = None) -> str:
    n = _n()
    return mundo.crear("/treasury/cashboxes", "ua", empresa or mundo.company_a,
                       {"code": f"FC-C{n}", "name": f"Caja FC {n}", "currency": "VED"})


def _cuenta(mundo) -> str:
    n = _n()
    banco = mundo.crear("/treasury/banks", "ua", mundo.company_a,
                        {"code": f"FC-B{n}", "name": f"Banco FC {n}"})
    return mundo.crear("/treasury/accounts", "ua", mundo.company_a,
                       {"bank_id": banco, "code": f"FC-A{n}", "name": f"Cuenta FC {n}",
                        "currency": "VED", "account_number": f"0102{n}"})


def _sesion(mundo, fondo: str = "100.00") -> str:
    return mundo.crear("/treasury/cash-sessions", "ua", mundo.company_a,
                       {"cashbox_id": _caja(mundo), "opened_amount": fondo})


def _regla_igtf(mundo) -> None:
    mundo.post("/treasury/fiscal-rules", "ua", mundo.company_a, {
        "rule_code": f"IGTF-{_n()}", "name": "IGTF", "rule_type": "IGTF", "version": "1.0",
        "effective_from": date.today().isoformat(), "params": json.dumps({"rate": 0.03})})


# --------------------------------------------------------------------------- #
# Los seis caminos, cada uno con su forma de llamarse
# --------------------------------------------------------------------------- #
def _abrir(mundo, valor: object):
    return mundo.post("/treasury/cash-sessions", "ua", mundo.company_a,
                      {"cashbox_id": _caja(mundo), "opened_amount": valor})


def _mover(mundo, valor: object, sesion: str | None = None):
    sesion = sesion or _sesion(mundo)
    return mundo.post(f"/treasury/cash-sessions/{sesion}/movements", "ua", mundo.company_a,
                      {"movement_type": "IN", "amount": valor, "source": "ADJUSTMENT"})


def _transferir(mundo, valor: object):
    # Entre cuentas: transferir entre cajas exige sesión abierta en ambas, que es
    # regla de caja y no de este delta.
    return mundo.post("/treasury/transfers", "ua", mundo.company_a,
                      {"amount": valor, "currency": "VED",
                       "from_account_id": _cuenta(mundo), "to_account_id": _cuenta(mundo)})


def _conciliar(mundo, apertura: object, cierre: object = None):
    return mundo.post("/treasury/reconciliations", "ua", mundo.company_a,
                      {"account_id": _cuenta(mundo), "opening_balance": apertura,
                       "closing_balance": cierre})


def _igtf(mundo, valor: object):
    _regla_igtf(mundo)
    return mundo.post("/treasury/igft-events/evaluate", "ua", mundo.company_a,
                      {"event_type": "PAYMENT", "amount": valor, "currency": "VED"})


#: (nombre, invocación, ¿admite signo?, ¿admite cero?)
CAMPOS = [
    ("opened_amount", _abrir, True, True),
    ("movement.amount", _mover, False, False),
    ("transfer.amount", _transferir, False, False),
    ("reconciliation.opening_balance", _conciliar, True, True),
    ("igtf.amount", _igtf, False, False),
]


def _campo(nombre: str):
    return next(c for c in CAMPOS if c[0] == nombre)[1]


# --------------------------------------------------------------------------- #
# A · el texto decimal se acepta · B · el número JSON no
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("nombre", [c[0] for c in CAMPOS])
def test_el_texto_decimal_se_acepta(mundo, nombre):
    r = _campo(nombre)(mundo, "125.50")
    assert r.status_code == 200, r.text


@pytest.mark.parametrize("nombre", [c[0] for c in CAMPOS])
def test_un_numero_json_no_es_dinero(mundo, nombre):
    """Cuando el número llega, `json.loads` ya lo convirtió en `float`: es tarde."""
    r = _campo(nombre)(mundo, 125.50)
    assert r.status_code == 422, r.text
    assert "texto decimal" in r.text


@pytest.mark.parametrize("nombre", [c[0] for c in CAMPOS])
def test_un_entero_json_tampoco(mundo, nombre):
    r = _campo(nombre)(mundo, 125)
    assert r.status_code == 422, r.text


# --------------------------------------------------------------------------- #
# C · escala · D · efecto cero
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("nombre", [c[0] for c in CAMPOS])
def test_mas_decimales_de_los_que_caben_se_rechazan_sin_redondear(mundo, nombre):
    r = _campo(nombre)(mundo, "100.005")
    assert r.status_code == 422, r.text
    assert "2 decimales" in r.text


def test_lo_rechazado_no_deja_rastro(mundo):
    """Una entrada inválida no crea filas, no mueve saldos y no registra nada."""
    antes = len(mundo.get("/treasury/transfers", "ua", mundo.company_a).json()["items"])
    for malo in (100.005, "100.005", "1e3", "abc", "", "100,00"):
        assert _transferir(mundo, malo).status_code == 422
    despues = len(mundo.get("/treasury/transfers", "ua", mundo.company_a).json()["items"])
    assert antes == despues


# --------------------------------------------------------------------------- #
# E/F · persistencia y respuesta exactas
# --------------------------------------------------------------------------- #
def test_el_fondo_de_apertura_vuelve_exacto(mundo):
    r = _abrir(mundo, EXACTO)
    assert r.status_code == 200, r.text
    assert r.json()["opened_amount"] == EXACTO


def test_el_movimiento_de_caja_vuelve_exacto(mundo):
    sesion = _sesion(mundo, "0.00")
    assert _mover(mundo, EXACTO, sesion).status_code == 200
    detalle = mundo.get(f"/treasury/cash-sessions/{sesion}", "ua", mundo.company_a).json()
    assert [m["amount"] for m in detalle["movements"]] == [EXACTO]


def test_la_transferencia_vuelve_exacta(mundo):
    r = _transferir(mundo, EXACTO)
    assert r.status_code == 200, r.text
    assert r.json()["amount"] == EXACTO


def test_los_saldos_de_conciliacion_vuelven_exactos(mundo):
    r = _conciliar(mundo, EXACTO, "-0.01")
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert (cuerpo["opening_balance"], cuerpo["closing_balance"]) == (EXACTO, "-0.01")


def test_la_base_del_igtf_vuelve_exacta(mundo):
    r = _igtf(mundo, EXACTO)
    assert r.status_code == 200, r.text
    assert r.json()["amount"] == EXACTO


def test_el_igtf_calculado_sale_como_texto_y_no_como_numero(mundo):
    """El impuesto no cambia; cambia que su importe deja de viajar en `float`."""
    r = _igtf(mundo, "100.00")
    assert r.status_code == 200, r.text
    calculado = r.json()["igft_amount"]
    assert isinstance(calculado, str), f"el IGTF volvió como {type(calculado).__name__}"
    assert calculado == "3.00"  # 100.00 × 0.03, la misma regla de siempre


# --------------------------------------------------------------------------- #
# I · cada campo conserva su regla de signo y de cero
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("nombre,admite_signo", [(c[0], c[2]) for c in CAMPOS])
def test_la_regla_de_signo_de_cada_campo_se_conserva(mundo, nombre, admite_signo):
    r = _campo(nombre)(mundo, "-0.01")
    if admite_signo:
        assert r.status_code == 200, r.text
    else:
        assert r.status_code == 422, r.text


@pytest.mark.parametrize("nombre,admite_cero", [(c[0], c[3]) for c in CAMPOS])
def test_la_regla_del_cero_de_cada_campo_se_conserva(mundo, nombre, admite_cero):
    r = _campo(nombre)(mundo, "0.00")
    if admite_cero:
        assert r.status_code == 200, r.text
    else:
        assert r.status_code == 422, r.text


# --------------------------------------------------------------------------- #
# El tipo interno, no sólo el texto que sale
# --------------------------------------------------------------------------- #
def test_lo_que_se_guarda_es_decimal_y_no_float(mundo):
    """Si el camino vuelve a pasar por `float`, esto lo ve aunque la respuesta cuadre."""
    from app.modules.treasury.models import CashSession, IgftEvent, Reconciliation, TreasuryTransfer

    _abrir(mundo, EXACTO)
    _transferir(mundo, EXACTO)
    _conciliar(mundo, EXACTO, "-0.01")
    _igtf(mundo, "100.00")

    db = mundo.factory()
    try:
        for modelo, campo, esperado in (
            (CashSession, "opened_amount", Decimal(EXACTO)),
            (TreasuryTransfer, "amount", Decimal(EXACTO)),
            (Reconciliation, "opening_balance", Decimal(EXACTO)),
            (IgftEvent, "igft_amount", Decimal("3.00")),
        ):
            fila = db.query(modelo).order_by(modelo.created_at.desc()).first()
            valor = getattr(fila, campo)
            assert isinstance(valor, Decimal), f"{modelo.__name__}.{campo} es {type(valor).__name__}"
            assert valor == esperado, f"{modelo.__name__}.{campo} = {valor}"
    finally:
        db.close()


def test_ninguna_de_las_seis_fronteras_declara_float(mundo):
    """Guarda estática dirigida: sólo sobre los seis símbolos, no sobre el módulo."""
    import inspect

    from app.modules.treasury import api

    fuente = inspect.getsource(api)
    for modelo, campo in (("SessionOpen", "opened_amount"), ("SessionMovementCreate", "amount"),
                          ("TransferCreate", "amount"), ("ReconciliationCreate", "opening_balance"),
                          ("ReconciliationCreate", "closing_balance"), ("IgftEvaluateBody", "amount")):
        bloque = fuente.split(f"class {modelo}(")[1].split("\nclass ")[0]
        linea = next(ln for ln in bloque.splitlines() if ln.strip().startswith(f"{campo}:"))
        assert "float" not in linea, f"{modelo}.{campo} volvió a declarar float: {linea.strip()}"
