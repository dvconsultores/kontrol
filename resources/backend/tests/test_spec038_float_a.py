"""Spec 038 · FLOAT-038-A — el importe del movimiento bancario es texto decimal exacto.

Decisiones del owner: `OQ-FLOAT-038-A-01` (texto al entrar y al salir, también la
comisión) y `OQ-FLOAT-038-A-02` (más decimales que la columna → 422, sin redondear).
La evidencia previa está en `specs/006-tesoreria/research.md` §5: un número JSON de
dieciocho dígitos llegaba a PostgreSQL como `…56.80` y salía como `…56.8`.

El fixture que separa una ruta `float` de una exacta es `1234567890123456.78`: cabe
en `numeric(18,2)` y un `double` no lo representa. `0.10` no serviría para eso,
porque `float` también lo lleva bien a la base; se prueba igualmente, como regla de
negocio, no como detector.
"""

from __future__ import annotations

import ast
import itertools
import re
import uuid
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import text

from app.core.errors import KontrolError
from app.modules.treasury import service as treasury_service
from app.modules.treasury.api import BankTransactionCreate, BankTransactionOut, BankTransactionPage, router
from app.shared.clock import hoy_de_negocio

pytest_plugins = ("tests.conftest_multicompany",)

EXACTO = "1234567890123456.78"
#: Lo que un `float` hace con `EXACTO` al llegar a `numeric(18,2)`.
CORROMPIDO = "1234567890123456.80"
RUTA = "/treasury/bank-transactions"
APP = Path(__file__).resolve().parents[1] / "app"

_serie = itertools.count(1)


def _cuenta(mundo, usuario: str = "ua", empresa: str | None = None) -> str:
    empresa = empresa or mundo.company_a
    n = f"{next(_serie)}{uuid.uuid4().hex[:4]}"
    banco = mundo.crear("/treasury/banks", usuario, empresa, {"code": f"FA-B{n}", "name": f"Banco FA {n}"})
    return mundo.crear("/treasury/accounts", usuario, empresa, {
        "bank_id": banco, "code": f"FA-C{n}", "name": f"Cuenta FA {n}",
        "currency": "VED", "account_number": f"0102FA{n}"})


def _mover(mundo, cuenta: str, importe: object, usuario: str = "ua", empresa: str | None = None, **extra):
    cuerpo = {"account_id": cuenta, "direction": "IN", "amount": importe, "currency": "VED", **extra}
    return mundo.post(RUTA, usuario, empresa or mundo.company_a, cuerpo)


def _escalar(mundo, sql: str, **parametros):
    db = mundo.factory()
    try:
        return db.execute(text(sql), parametros).scalar_one()
    finally:
        db.close()


def _filas(mundo, cuenta: str) -> int:
    return _escalar(mundo, "SELECT count(*) FROM bank_transactions WHERE account_id = :c", c=cuenta)


def _saldo(mundo, cuenta: str) -> str:
    return mundo.get(f"/treasury/accounts/{cuenta}/balance", "ua", mundo.company_a).json()["balance"]


def _rechazo(r, campo: str = "amount") -> None:
    assert r.status_code == 422, f"se esperaba 422 y llegó {r.status_code}: {r.text}"
    cuerpo = r.json()
    assert cuerpo["code"] == "VALIDATION_ERROR", cuerpo
    assert campo in cuerpo["field_errors"], cuerpo


# --------------------------------------------------------------- tipo en la frontera
def test_el_esquema_entrega_decimal_y_no_float():
    cuerpo = BankTransactionCreate.model_validate(
        {"account_id": "x", "direction": "IN", "amount": "123.45", "commission": "1.20"})
    assert type(cuerpo.amount) is Decimal and cuerpo.amount == Decimal("123.45")
    assert type(cuerpo.commission) is Decimal and cuerpo.commission == Decimal("1.20")


# --------------------------------------------------------------- exactitud de extremo a extremo
def test_un_importe_de_dieciocho_digitos_llega_exacto_a_la_base_y_vuelve_exacto(mundo):
    cuenta = _cuenta(mundo)
    r = _mover(mundo, cuenta, EXACTO)
    assert r.status_code == 200, r.text
    assert r.json()["amount"] == EXACTO, "la respuesta de creación degradó el importe"

    fila = r.json()["id"]
    en_base = _escalar(mundo, "SELECT amount::text FROM bank_transactions WHERE id = :i", i=fila)
    assert en_base == EXACTO, f"PostgreSQL guardó {en_base}: la frontera volvió a pasar por float"

    from app.modules.treasury.models import BankTransaction

    db = mundo.factory()
    try:
        leido = db.get(BankTransaction, fila).amount
    finally:
        db.close()
    assert type(leido) is Decimal and leido == Decimal(EXACTO)

    items = mundo.get(f"{RUTA}?account_id={cuenta}", "ua", mundo.company_a).json()["items"]
    assert [i["amount"] for i in items] == [EXACTO], "el listado degradó el importe"
    assert _saldo(mundo, cuenta) == EXACTO


@pytest.mark.parametrize(("enviado", "devuelto"), [
    ("10.50", "10.50"), ("10.5", "10.50"), ("10", "10.00"), ("10.0", "10.00"),
    ("0.01", "0.01"), ("1.10", "1.10"), ("1.00", "1.00"), ("001.20", "1.20"),
    ("9999999999999999.99", "9999999999999999.99"),
])
def test_la_respuesta_dice_el_importe_con_sus_dos_decimales(mundo, enviado, devuelto):
    cuenta = _cuenta(mundo)
    r = _mover(mundo, cuenta, enviado)
    assert r.status_code == 200, r.text
    assert r.json()["amount"] == devuelto
    items = mundo.get(f"{RUTA}?account_id={cuenta}", "ua", mundo.company_a).json()["items"]
    assert [i["amount"] for i in items] == [devuelto]
    assert _escalar(mundo, "SELECT amount::text FROM bank_transactions WHERE account_id = :c", c=cuenta) == devuelto


def test_diez_centimos_mas_veinte_son_treinta(mundo):
    cuenta = _cuenta(mundo)
    assert _mover(mundo, cuenta, "0.10").status_code == 200
    assert _mover(mundo, cuenta, "0.20").status_code == 200
    assert _saldo(mundo, cuenta) == "0.30"


# --------------------------------------------------------------- representación
@pytest.mark.parametrize("numero", [123.45, 100, 1234567890123456.78, True])
def test_un_numero_json_se_rechaza(mundo, numero):
    cuenta = _cuenta(mundo)
    _rechazo(_mover(mundo, cuenta, numero))
    assert _filas(mundo, cuenta) == 0


@pytest.mark.parametrize("malformado", [
    "1e3", "1E3", "NaN", "nan", "Infinity", "-Infinity", " 10", "10 ", "10.", ".5",
    "+10", "1,000.00", "1_000", "", "١٠",
])
def test_lo_que_no_es_texto_decimal_se_rechaza(mundo, malformado):
    cuenta = _cuenta(mundo)
    _rechazo(_mover(mundo, cuenta, malformado))
    assert _filas(mundo, cuenta) == 0


# --------------------------------------------------------------- escala, precisión y signo
@pytest.mark.parametrize("de_mas", ["0.001", "0.005", "10.000", "1234567890123456.785"])
def test_mas_decimales_que_la_columna_se_rechazan_sin_dejar_hecho_economico(mundo, de_mas):
    cuenta = _cuenta(mundo)
    assert _mover(mundo, cuenta, "5.00").status_code == 200
    filas, saldo = _filas(mundo, cuenta), _saldo(mundo, cuenta)

    r = _mover(mundo, cuenta, de_mas)
    _rechazo(r)
    assert "decimales" in " ".join(r.json()["field_errors"]["amount"])
    assert _filas(mundo, cuenta) == filas, "el rechazo dejó una fila"
    assert _saldo(mundo, cuenta) == saldo == "5.00", "el rechazo movió el saldo"


def test_mas_digitos_enteros_que_la_columna_es_un_422_y_no_un_500(mundo):
    cuenta = _cuenta(mundo)
    _rechazo(_mover(mundo, cuenta, "12345678901234567.00"))
    assert _filas(mundo, cuenta) == 0


@pytest.mark.parametrize("no_positivo", ["0.00", "0", "-1.00"])
def test_cero_y_negativo_siguen_rechazados(mundo, no_positivo):
    cuenta = _cuenta(mundo)
    _rechazo(_mover(mundo, cuenta, no_positivo))
    assert _filas(mundo, cuenta) == 0


def test_el_servicio_conserva_su_propia_regla_de_positivo(mundo):
    cuenta = _cuenta(mundo)
    db = mundo.factory()
    try:
        with pytest.raises(KontrolError) as error:
            treasury_service.create_bank_transaction(
                db, company_id=mundo.company_a, account_id=cuenta, direction="IN", amount=Decimal("0.00"))
    finally:
        db.rollback()
        db.close()
    assert error.value.code == "INVALID_AMOUNT" and error.value.status_code == 422


# --------------------------------------------------------------- comisión
def test_la_comision_sigue_la_misma_politica(mundo):
    cuenta = _cuenta(mundo)
    r = _mover(mundo, cuenta, "100.00", commission="12.35")
    assert r.status_code == 200, r.text
    assert r.json()["commission"] == "12.35"
    assert _escalar(mundo, "SELECT commission::text FROM bank_transactions WHERE id = :i", i=r.json()["id"]) == "12.35"

    _rechazo(_mover(mundo, cuenta, "100.00", commission=12.35), "commission")
    _rechazo(_mover(mundo, cuenta, "100.00", commission="0.001"), "commission")
    _rechazo(_mover(mundo, cuenta, "100.00", commission="1e1"), "commission")
    assert _filas(mundo, cuenta) == 1

    assert _mover(mundo, cuenta, "1.00", commission=None).json()["commission"] is None
    # La comisión no tenía regla de signo: este delta no inventa una.
    assert _mover(mundo, cuenta, "1.00", commission="-1.50").json()["commission"] == "-1.50"


def test_la_comision_de_dieciocho_digitos_vuelve_exacta(mundo):
    cuenta = _cuenta(mundo)
    r = _mover(mundo, cuenta, "1.00", commission=EXACTO)
    assert r.status_code == 200, r.text
    assert r.json()["commission"] == EXACTO


# --------------------------------------------------------------- contrato publicado
def test_openapi_declara_texto_y_la_respuesta_ya_no_es_un_objeto_vacio(mundo):
    esquema = mundo.client.app.openapi()
    componentes = esquema["components"]["schemas"]
    ruta = esquema["paths"][f"/api/v1{RUTA}"]

    entrada = componentes["BankTransactionCreate"]["properties"]
    assert entrada["amount"]["type"] == "string" and "number" not in str(entrada["amount"])
    assert {v.get("type") for v in entrada["commission"]["anyOf"]} == {"string", "null"}
    assert "number" not in str(entrada["commission"])

    assert ruta["post"]["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/BankTransactionOut"}
    assert ruta["get"]["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/BankTransactionPage"}
    salida = componentes["BankTransactionOut"]["properties"]
    assert salida["amount"]["type"] == "string"
    assert {v.get("type") for v in salida["commission"]["anyOf"]} == {"string", "null"}

    # Y lo publicado describe lo que de verdad responde.
    cuenta = _cuenta(mundo)
    respuesta = _mover(mundo, cuenta, EXACTO, commission="3.40").json()
    assert re.fullmatch(salida["amount"]["pattern"], respuesta["amount"])
    assert re.fullmatch(entrada["amount"]["pattern"], EXACTO)
    assert set(respuesta) == set(salida), "la respuesta y su modelo publicado no tienen los mismos campos"


# --------------------------------------------------------------- consumidores
def test_la_conciliacion_empareja_el_importe_exacto_y_no_el_degradado(mundo):
    from app.modules.master_data.models import Party
    from app.modules.purchasing.models import Payment

    cuenta = _cuenta(mundo)
    db = mundo.factory()
    try:
        codigo = f"FA-P{uuid.uuid4().hex[:6]}"
        parte = Party(company_id=mundo.company_a, code=codigo, name="Proveedor exacto", person_type="JURIDICA",
                      tax_id=f"J-{uuid.uuid4().int % 100000000:08d}-1", roles=["PROVEEDOR"], status="ACTIVE")
        db.add(parte)
        db.flush()
        # La regla empareja con puntuación ≥ 0,8: importe y fecha valor. Los dos pagos
        # tienen la fecha del movimiento; lo único que los distingue es el importe.
        exacto = Payment(company_id=mundo.company_a, party_id=str(parte.id), direction="IN", currency="VED",
                         amount=Decimal(EXACTO), applied=Decimal("0"), status="APPROVED", date=hoy_de_negocio())
        degradado = Payment(company_id=mundo.company_a, party_id=str(parte.id), direction="IN", currency="VED",
                            amount=Decimal(CORROMPIDO), applied=Decimal("0"), status="APPROVED", date=hoy_de_negocio())
        db.add_all([exacto, degradado])
        db.commit()
        pago_exacto, pago_degradado = str(exacto.id), str(degradado.id)
    finally:
        db.close()

    movimiento = _mover(mundo, cuenta, EXACTO).json()["id"]
    rec = mundo.crear("/treasury/reconciliations", "ua", mundo.company_a,
                      {"account_id": cuenta, "statement_ref": f"FA-EXT-{movimiento[:6]}"})
    r = mundo.post(f"/treasury/reconciliations/{rec}/lines", "ua", mundo.company_a, {"bank_transaction_id": movimiento})
    assert r.status_code == 200, r.text
    r = mundo.post(f"/treasury/reconciliations/{rec}/match", "ua", mundo.company_a, {})
    assert r.status_code == 200, r.text

    emparejado = _escalar(mundo, "SELECT system_movement_id FROM reconciliation_lines WHERE reconciliation_id = :r",
                          r=rec)
    assert emparejado == pago_exacto, (
        "la conciliación no emparejó el pago del mismo importe exacto"
        + (" sino el degradado por float" if emparejado == pago_degradado else ""))


def test_otra_empresa_no_ve_el_movimiento_exacto(mundo):
    cuenta = _cuenta(mundo)
    movimiento = _mover(mundo, cuenta, EXACTO).json()["id"]

    de_b = {t["id"] for t in mundo.get(RUTA, "ub", mundo.company_b).json()["items"]}
    assert movimiento not in de_b
    en_a = {t["id"]: t["amount"] for t in mundo.get(RUTA, "uab", mundo.company_a).json()["items"]}
    assert en_a[movimiento] == EXACTO
    assert movimiento not in {t["id"] for t in mundo.get(RUTA, "uab", mundo.company_b).json()["items"]}
    # El texto válido llega hasta la comprobación de empresa: el 404 es de la cuenta, no del formato.
    r = _mover(mundo, cuenta, EXACTO, usuario="ub", empresa=mundo.company_b)
    assert r.status_code == 404 and r.json()["code"] == "ACCOUNT_NOT_FOUND"


# --------------------------------------------------------------- guardas estáticas
def _arbol(relativo: str) -> ast.Module:
    return ast.parse((APP / relativo).read_text(encoding="utf-8"))


def _anotaciones_de_clase(arbol: ast.Module, clase: str) -> dict[str, str]:
    nodo = next(n for n in ast.walk(arbol) if isinstance(n, ast.ClassDef) and n.name == clase)
    return {n.target.id: ast.unparse(n.annotation) for n in nodo.body
            if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)}


def _funcion(arbol: ast.Module, nombre: str) -> ast.FunctionDef:
    return next(n for n in ast.walk(arbol) if isinstance(n, ast.FunctionDef) and n.name == nombre)


def test_guarda_ninguna_anotacion_float_en_el_camino_del_importe():
    entrada = _anotaciones_de_clase(_arbol("modules/treasury/api.py"), "BankTransactionCreate")
    assert "float" not in entrada["amount"] and "float" not in entrada["commission"], entrada

    modelo = _anotaciones_de_clase(_arbol("modules/treasury/models.py"), "BankTransaction")
    assert modelo["amount"] == "Mapped[Decimal]" and modelo["commission"] == "Mapped[Decimal | None]", modelo

    servicio = _funcion(_arbol("modules/treasury/service.py"), "create_bank_transaction")
    firma = {a.arg: ast.unparse(a.annotation) for a in servicio.args.kwonlyargs if a.annotation is not None}
    assert firma["amount"] == "Decimal" and firma["commission"] == "Decimal | None", firma


@pytest.mark.parametrize(("relativo", "funciones"), [
    ("modules/treasury/api.py", ("create_bank_transaction", "list_bank_transactions")),
    ("modules/treasury/service.py", ("create_bank_transaction", "bank_transaction_dict")),
])
def test_guarda_sin_float_ni_redondeo_en_la_ruta_ni_en_la_serializacion(relativo, funciones):
    arbol = _arbol(relativo)
    for nombre in funciones:
        llamadas = {n.func.id for n in ast.walk(_funcion(arbol, nombre))
                    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        assert not llamadas & {"float", "round"}, f"{relativo}:{nombre} llama a {llamadas & {'float', 'round'}}"


def test_guarda_las_rutas_del_movimiento_bancario_declaran_su_modelo():
    modelos = {(tuple(sorted(r.methods)), r.response_model) for r in router.routes if r.path == RUTA}
    assert modelos == {(("POST",), BankTransactionOut), (("GET",), BankTransactionPage)}
    assert BankTransactionOut.model_fields["amount"].annotation is str
