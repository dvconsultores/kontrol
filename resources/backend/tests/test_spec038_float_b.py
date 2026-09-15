"""Spec 038 · FLOAT-038-B — arqueo y cierre de caja exactos.

La resta del arqueo ya era exacta: `_money(contado) - _money(esperado)` en `Decimal`
(errata §14 de `spec038-convergence.md`) y no se toca. Lo que este delta corrige es
lo que la rodeaba: el conteo entraba como `float`, el cierre decidía con un épsilon
y la auditoría guardaba `float(...)`. Hereda las decisiones de FLOAT-038-A: texto
decimal en el contrato, 422 para lo que no cabe, cero exacto.

El detector de exactitud es `1234567890123456.78`, que cabe en `numeric(18,2)` y un
`double` no representa. El detector del cero es un céntimo: con dinero de escala 2
el `1e-6` antiguo no cambiaba ningún resultado, así que la prueba fija la regla y
no el literal.
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

from app.modules.treasury import service as treasury_service
from app.modules.treasury.api import ArqueoBody, CashSessionOut, CashSessionPage, router

pytest_plugins = ("tests.conftest_multicompany",)

EXACTO = "1234567890123456.78"
BASE = "/treasury/cash-sessions"
APP = Path(__file__).resolve().parents[1] / "app"

_serie = itertools.count(1)


def _sesion(mundo, fondo: float = 100, usuario: str = "ua", empresa: str | None = None) -> str:
    """Abre una sesión. El fondo viaja como número: esa entrada es otro contrato, fuera de este delta."""
    empresa = empresa or mundo.company_a
    n = f"{next(_serie)}{uuid.uuid4().hex[:4]}"
    caja = mundo.crear("/treasury/cashboxes", usuario, empresa,
                       {"code": f"FB-C{n}", "name": f"Caja FB {n}", "currency": "VED"})
    return mundo.crear(BASE, usuario, empresa, {"cashbox_id": caja, "opened_amount": fondo})


def _arquear(mundo, sesion: str, contado: object, usuario: str = "ua", empresa: str | None = None):
    return mundo.post(f"{BASE}/{sesion}/arqueo", usuario, empresa or mundo.company_a, {"counted_amount": contado})


def _precerrar(mundo, sesion: str) -> None:
    r = mundo.post(f"{BASE}/{sesion}/pre-close", "ua", mundo.company_a, {})
    assert r.status_code == 200, r.text


def _cerrar(mundo, sesion: str, aprobada: bool = False):
    return mundo.post(f"{BASE}/{sesion}/close", "ua", mundo.company_a,
                      {"difference_approved": aprobada, "approval_note": "aprobada" if aprobada else None})


def _fila(mundo, sesion: str):
    db = mundo.factory()
    try:
        return db.execute(text(
            "SELECT status, counted_amount::text AS counted, expected_amount::text AS expected, "
            "difference::text AS difference FROM cash_sessions WHERE id = :i"), {"i": sesion}).one()
    finally:
        db.close()


def _auditorias(mundo, sesion: str, accion: str) -> list[dict]:
    db = mundo.factory()
    try:
        return list(db.execute(text(
            "SELECT after FROM audit_events WHERE entity_id = :i AND action = :a ORDER BY event_time"),
            {"i": sesion, "a": accion}).scalars())
    finally:
        db.close()


def _rechazo(r, campo: str = "counted_amount") -> None:
    assert r.status_code == 422, f"se esperaba 422 y llegó {r.status_code}: {r.text}"
    cuerpo = r.json()
    assert cuerpo["code"] == "VALIDATION_ERROR", cuerpo
    assert campo in cuerpo["field_errors"], cuerpo


def _intacta(mundo, sesion: str) -> None:
    fila = _fila(mundo, sesion)
    assert fila.status == "OPEN", "un conteo rechazado cambió el estado de la sesión"
    assert fila.counted is None and fila.difference is None, "un conteo rechazado dejó cifras"
    assert _auditorias(mundo, sesion, "CASH_SESSION_ARCHED") == [], "un conteo rechazado se auditó como arqueo"


# --------------------------------------------------------------- tipo en la frontera
def test_el_esquema_entrega_decimal_y_no_float():
    cuerpo = ArqueoBody.model_validate({"counted_amount": "100.00"})
    assert type(cuerpo.counted_amount) is Decimal and cuerpo.counted_amount == Decimal("100.00")
    assert ArqueoBody.model_validate({"counted_amount": "0.00"}).counted_amount == Decimal("0")


def test_un_conteo_en_texto_llega_exacto(mundo):
    sesion = _sesion(mundo, fondo=100)
    r = _arquear(mundo, sesion, "100.00")
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert (cuerpo["counted_amount"], cuerpo["expected_amount"], cuerpo["difference"], cuerpo["status"]) == \
        ("100.00", "100.00", "0.00", "ARCHED")
    assert _fila(mundo, sesion).counted == "100.00"


def test_un_importe_de_dieciocho_digitos_llega_exacto_a_base_respuesta_y_auditoria(mundo):
    sesion = _sesion(mundo, fondo=0)
    r = _arquear(mundo, sesion, EXACTO)
    assert r.status_code == 200, r.text
    assert r.json()["counted_amount"] == EXACTO, "la respuesta degradó el conteo"
    assert r.json()["difference"] == EXACTO, "la diferencia degradó el conteo"

    fila = _fila(mundo, sesion)
    assert (fila.counted, fila.difference) == (EXACTO, EXACTO), f"PostgreSQL guardó {fila.counted}"
    assert _auditorias(mundo, sesion, "CASH_SESSION_ARCHED") == [
        {"expected": "0.00", "counted": EXACTO, "difference": EXACTO}], "la auditoría degradó el conteo"


# --------------------------------------------------------------- representación y escala
@pytest.mark.parametrize("numero", [100.00, 100, 0, True])
def test_un_numero_json_se_rechaza_sin_tocar_la_sesion(mundo, numero):
    sesion = _sesion(mundo)
    _rechazo(_arquear(mundo, sesion, numero))
    _intacta(mundo, sesion)


@pytest.mark.parametrize("de_mas", ["100.001", "100.005", "0.005", "100.000"])
def test_mas_decimales_que_la_columna_se_rechazan_sin_tocar_la_sesion(mundo, de_mas):
    sesion = _sesion(mundo)
    r = _arquear(mundo, sesion, de_mas)
    _rechazo(r)
    assert "decimales" in " ".join(r.json()["field_errors"]["counted_amount"])
    _intacta(mundo, sesion)


@pytest.mark.parametrize("malformado", [
    "1e2", "NaN", "Infinity", "-1.00", "+1", "", " 100", "100,00", "12345678901234567.00",
])
def test_lo_que_no_es_un_conteo_valido_se_rechaza(mundo, malformado):
    sesion = _sesion(mundo)
    _rechazo(_arquear(mundo, sesion, malformado))
    _intacta(mundo, sesion)


def test_cero_sigue_siendo_un_conteo_valido(mundo):
    sesion = _sesion(mundo, fondo=0)
    r = _arquear(mundo, sesion, "0.00")
    assert r.status_code == 200, r.text
    assert r.json()["difference"] == "0.00"


# --------------------------------------------------------------- diferencia y cero exacto
def test_la_diferencia_es_decimal_y_conserva_formula_y_signo(mundo):
    db = mundo.factory()
    try:
        caja = treasury_service.create_cashbox(db, company_id=mundo.company_a,
                                               code=f"FB-S{uuid.uuid4().hex[:6]}", name="Caja de servicio")
        db.flush()
        sesion = treasury_service.open_session(db, company_id=mundo.company_a, cashbox_id=str(caja.id),
                                               opened_amount=Decimal("100.00"))
        db.flush()
        treasury_service.arqueo_session(db, session_id=str(sesion.id), counted_amount=Decimal("99.99"))
        assert type(sesion.difference) is Decimal
        assert sesion.difference == Decimal("-0.01"), "la diferencia cambió de fórmula o de signo"
    finally:
        db.rollback()
        db.close()


def test_si_cuadra_exacto_cierra_sin_aprobacion(mundo):
    sesion = _sesion(mundo, fondo=100)
    assert _arquear(mundo, sesion, "100.00").status_code == 200
    _precerrar(mundo, sesion)
    r = _cerrar(mundo, sesion)
    assert r.status_code == 200, r.text
    assert (r.json()["status"], r.json()["difference"]) == ("CLOSED", "0.00")
    assert _auditorias(mundo, sesion, "CASH_SESSION_CLOSED") == [{"difference": "0.00", "approved": False}]


def test_un_centimo_de_menos_es_diferencia_y_exige_aprobacion(mundo):
    sesion = _sesion(mundo, fondo=100)
    r = _arquear(mundo, sesion, "99.99")
    assert r.json()["difference"] == "-0.01", "el faltante perdió su signo"
    _precerrar(mundo, sesion)

    r = _cerrar(mundo, sesion)
    assert r.status_code == 409, f"cerró con un céntimo de diferencia sin aprobación: {r.text}"
    assert r.json()["code"] == "DIFFERENCE_NOT_APPROVED"
    assert _fila(mundo, sesion).status == "PRE_CLOSED"
    assert _auditorias(mundo, sesion, "CASH_SESSION_CLOSED") == []

    r = _cerrar(mundo, sesion, aprobada=True)
    assert r.status_code == 200 and r.json()["status"] == "CLOSED", r.text


def test_un_centimo_de_mas_es_diferencia_con_su_signo(mundo):
    sesion = _sesion(mundo, fondo=100)
    assert _arquear(mundo, sesion, "100.01").json()["difference"] == "0.01", "el sobrante perdió su signo"
    _precerrar(mundo, sesion)
    r = _cerrar(mundo, sesion)
    assert r.status_code == 409 and r.json()["code"] == "DIFFERENCE_NOT_APPROVED", r.text


def test_cerrar_dos_veces_no_cierra_dos_veces(mundo):
    sesion = _sesion(mundo, fondo=100)
    _arquear(mundo, sesion, "100.00")
    _precerrar(mundo, sesion)
    assert _cerrar(mundo, sesion).status_code == 200
    assert _cerrar(mundo, sesion).status_code == 409
    assert len(_auditorias(mundo, sesion, "CASH_SESSION_CLOSED")) == 1


# --------------------------------------------------------------- auditoría y respuesta
def test_la_auditoria_guarda_texto_exacto_con_signo(mundo):
    sesion = _sesion(mundo, fondo=100)
    _arquear(mundo, sesion, "99.99")
    _precerrar(mundo, sesion)
    _cerrar(mundo, sesion, aprobada=True)

    [arqueo] = _auditorias(mundo, sesion, "CASH_SESSION_ARCHED")
    assert arqueo == {"expected": "100.00", "counted": "99.99", "difference": "-0.01"}
    assert all(isinstance(v, str) for v in arqueo.values()), "la auditoría volvió a guardar números"
    [cierre] = _auditorias(mundo, sesion, "CASH_SESSION_CLOSED")
    assert cierre == {"difference": "-0.01", "approved": True}


def test_la_sesion_dice_todos_sus_importes_en_texto(mundo):
    sesion = _sesion(mundo, fondo=100)
    r = mundo.post(f"{BASE}/{sesion}/movements", "ua", mundo.company_a, {"movement_type": "IN", "amount": 25.5})
    assert r.status_code == 200, r.text

    detalle = mundo.get(f"{BASE}/{sesion}", "ua", mundo.company_a).json()
    assert (detalle["opened_amount"], detalle["expected_amount"]) == ("100.00", "125.50")
    assert (detalle["counted_amount"], detalle["difference"]) == (None, None)
    assert [m["amount"] for m in detalle["movements"]] == ["25.50"]

    arqueada = _arquear(mundo, sesion, "125.50").json()
    assert (arqueada["counted_amount"], arqueada["difference"]) == ("125.50", "0.00")
    listado = {s["id"]: s for s in mundo.get(BASE, "ua", mundo.company_a).json()["items"]}
    assert listado[sesion]["expected_amount"] == "125.50"


def test_openapi_declara_texto_en_el_arqueo_y_en_la_sesion(mundo):
    esquema = mundo.client.app.openapi()
    componentes = esquema["components"]["schemas"]
    entrada = componentes["ArqueoBody"]["properties"]["counted_amount"]
    assert entrada["type"] == "string" and "number" not in str(entrada)

    rutas = esquema["paths"]
    for ruta, metodo in ((f"/api/v1{BASE}", "post"), (f"/api/v1{BASE}/{{session_id}}", "get"),
                         (f"/api/v1{BASE}/{{session_id}}/arqueo", "post"),
                         (f"/api/v1{BASE}/{{session_id}}/pre-close", "post"),
                         (f"/api/v1{BASE}/{{session_id}}/close", "post"),
                         (f"/api/v1{BASE}/{{session_id}}/reject", "post")):
        assert rutas[ruta][metodo]["responses"]["200"]["content"]["application/json"]["schema"] == {
            "$ref": "#/components/schemas/CashSessionOut"}, ruta
    assert rutas[f"/api/v1{BASE}"]["get"]["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/CashSessionPage"}

    salida = componentes["CashSessionOut"]["properties"]
    for campo in ("opened_amount", "expected_amount"):
        assert salida[campo]["type"] == "string", campo
    for campo in ("counted_amount", "difference"):
        assert {v.get("type") for v in salida[campo]["anyOf"]} == {"string", "null"}, campo

    sesion = _sesion(mundo, fondo=0)
    respuesta = _arquear(mundo, sesion, EXACTO).json()
    patron = salida["expected_amount"]["pattern"]
    assert all(re.fullmatch(patron, respuesta[c]) for c in ("opened_amount", "expected_amount", "difference"))
    assert re.fullmatch(entrada["pattern"], EXACTO)
    assert set(respuesta) == set(salida), "la respuesta y su modelo publicado no tienen los mismos campos"


# --------------------------------------------------------------- empresa
def test_otra_empresa_no_arquea_ni_con_un_conteo_valido(mundo):
    sesion = _sesion(mundo)
    r = _arquear(mundo, sesion, "100.00", usuario="ub", empresa=mundo.company_b)
    assert r.status_code == 404 and r.json()["code"] == "CASH_SESSION_NOT_FOUND", r.text
    _intacta(mundo, sesion)


# --------------------------------------------------------------- guardas estáticas
def _arbol(relativo: str) -> ast.Module:
    return ast.parse((APP / relativo).read_text(encoding="utf-8"))


def _anotaciones_de_clase(arbol: ast.Module, clase: str) -> dict[str, str]:
    nodo = next(n for n in ast.walk(arbol) if isinstance(n, ast.ClassDef) and n.name == clase)
    return {n.target.id: ast.unparse(n.annotation) for n in nodo.body
            if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)}


def _funcion(arbol: ast.Module, nombre: str) -> ast.FunctionDef:
    return next(n for n in ast.walk(arbol) if isinstance(n, ast.FunctionDef) and n.name == nombre)


def test_guarda_ninguna_anotacion_float_en_el_arqueo():
    assert "float" not in _anotaciones_de_clase(_arbol("modules/treasury/api.py"), "ArqueoBody")["counted_amount"]

    modelo = _anotaciones_de_clase(_arbol("modules/treasury/models.py"), "CashSession")
    for campo in ("opened_amount", "counted_amount", "expected_amount", "difference"):
        assert "Decimal" in modelo[campo] and "float" not in modelo[campo], (campo, modelo[campo])

    servicio = _arbol("modules/treasury/service.py")
    arqueo = _funcion(servicio, "arqueo_session")
    firma = {a.arg: ast.unparse(a.annotation) for a in arqueo.args.kwonlyargs if a.annotation is not None}
    assert firma["counted_amount"] == "Decimal", firma
    assert ast.unparse(_funcion(servicio, "_session_expected").returns) == "Decimal"


def test_guarda_sin_float_redondeo_ni_epsilon_en_arqueo_cierre_y_sesion():
    servicio = _arbol("modules/treasury/service.py")
    for nombre in ("arqueo_session", "close_session", "session_dict"):
        funcion = _funcion(servicio, nombre)
        llamadas = {n.func.id for n in ast.walk(funcion) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        assert not llamadas & {"float", "round"}, f"{nombre} llama a {llamadas & {'float', 'round'}}"
        tolerancias = [n.value for n in ast.walk(funcion) if isinstance(n, ast.Constant) and isinstance(n.value, float)]
        assert not tolerancias, f"{nombre} compara dinero con una constante en coma flotante: {tolerancias}"
        assert "isclose" not in ast.unparse(funcion), f"{nombre} usa isclose"


def test_guarda_las_rutas_de_la_sesion_declaran_su_modelo():
    modelos = {(r.path, tuple(sorted(r.methods))): r.response_model for r in router.routes if r.path.startswith(BASE)}
    assert modelos[(BASE, ("GET",))] is CashSessionPage
    for clave in ((BASE, ("POST",)), (f"{BASE}/{{session_id}}", ("GET",)),
                  (f"{BASE}/{{session_id}}/arqueo", ("POST",)), (f"{BASE}/{{session_id}}/pre-close", ("POST",)),
                  (f"{BASE}/{{session_id}}/close", ("POST",)), (f"{BASE}/{{session_id}}/reject", ("POST",))):
        assert modelos[clave] is CashSessionOut, clave
