"""Pruebas del contrato estricto de parámetros de consulta (FR-001-268/269/273).

Fija el contrato que implementa `app.core.query_contract`: toda operación bajo
`/api/v1/` responde 422 ante nombres de parámetros de consulta no declarados por
la ruta resuelta (incluidas dependencias y subdependencias), conservando el
orden de autorización antes de la verificación y sin eco del valor enviado.
"""

from __future__ import annotations

import ast
import re
import uuid
from pathlib import Path

import pytest
from fastapi import Depends, FastAPI
from fastapi.routing import APIRoute, iter_route_contexts
from fastapi.testclient import TestClient
from mfa_mundo import API, alta_por_desafio, crear_usuario, login, mundo_mfa

from app.core.errors import register_exception_handlers
from app.modules.identity_access import service as identity_service
from app.modules.identity_access.models import UserRole

pytest_plugins = ("mfa_apoyo",)


@pytest.fixture(scope="module")
def mundo():
    with mundo_mfa() as m:
        yield m


def _dar(mundo, user_id, role_id, company_id):
    db = mundo.factory()
    try:
        db.add(UserRole(user_id=user_id, role_id=role_id, company_id=company_id))
        db.commit()
    finally:
        db.close()


def _entrar(mundo, reloj, nombre):
    r = login(mundo.client, nombre)
    assert r.status_code == 200, r.text
    if r.json().get("status") == "AUTHENTICATED":
        return {"Authorization": f"Bearer {r.json()['access_token']}"}
    return alta_por_desafio(mundo.client, reloj, nombre).cabeceras


@pytest.fixture(scope="module")
def rol_operador(mundo):
    db = mundo.factory()
    try:
        rol = identity_service.create_role(
            db,
            tenant_id=mundo.tenant_id,
            code=f"sqc{uuid.uuid4().hex[:12]}",
            name="SQC Operador",
            company_id=None,
            permissions=[
                "maestros:view",
                "maestros:create",
                "organization:view",
                "organization:edit",
                "organization:delete",
            ],
            actor=mundo.admin_id,
        )
        db.commit()
        return rol["id"]
    finally:
        db.close()


def _operador(mundo, reloj, rol):
    nombre = f"sqc{uuid.uuid4().hex[:12]}"
    user_id = crear_usuario(mundo, nombre)
    _dar(mundo, user_id, rol, mundo.company_id)
    cabeceras = _entrar(mundo, reloj, nombre)
    cabeceras["X-Kontrol-Company"] = str(mundo.company_id)
    return cabeceras


def _error_contracto(resp, *, code, nombres, message):
    assert resp.status_code == 422, resp.text
    cuerpo = resp.json()
    assert cuerpo["code"] == code, cuerpo
    assert cuerpo["message"] == message, cuerpo
    assert isinstance(cuerpo["request_id"], str), cuerpo
    assert cuerpo["request_id"], cuerpo
    assert cuerpo["details"] == {"unknown_query_parameters": nombres}, cuerpo
    assert cuerpo["field_errors"] == {
        f"query.{nombre}": ["Parámetro no admitido por esta operación."]
        for nombre in nombres
    }, cuerpo


def test_q01_desconocido_422(mundo, reloj_mfa, rol_operador):
    """Q-01: un nombre de consulta no declarado produce 422 con el contrato canónico."""
    cabeceras = _operador(mundo, reloj_mfa, rol_operador)
    resp = mundo.client.get(f"{API}/maestros/terceros?zz_no_declarado=1", headers=cabeceras)
    _error_contracto(
        resp,
        code="UNKNOWN_QUERY_PARAMETER",
        nombres=["zz_no_declarado"],
        message="La consulta incluye parámetros que esta operación no admite.",
    )


def test_q02_declarado_aceptado(mundo, reloj_mfa, rol_operador):
    """Q-02 (control verde hoy): parámetros declarados son aceptados."""
    cabeceras = _operador(mundo, reloj_mfa, rol_operador)
    resp = mundo.client.get(
        f"{API}/maestros/terceros?q=x&status=ACTIVE&page=1&page_size=5",
        headers=cabeceras,
    )
    assert resp.status_code == 200, resp.text


def test_q03_vacio_y_sin_igual(mundo, reloj_mfa, rol_operador):
    """Q-03: un desconocido vacío (`?zz=`) o sin igual (`?zz`) también es 422."""
    cabeceras = _operador(mundo, reloj_mfa, rol_operador)
    for url in (f"{API}/maestros/terceros?zz=", f"{API}/maestros/terceros?zz"):
        resp = mundo.client.get(url, headers=cabeceras)
        _error_contracto(
            resp,
            code="UNKNOWN_QUERY_PARAMETER",
            nombres=["zz"],
            message="La consulta incluye parámetros que esta operación no admite.",
        )


def test_q04_mayusculas_y_parecidos(mundo, reloj_mfa, rol_operador):
    """Q-04: la coincidencia es exacta y sensible a mayúsculas."""
    cabeceras = _operador(mundo, reloj_mfa, rol_operador)
    for nombre in ("Page_Size", "PAGE_SIZE", "pagesize", "Q"):
        resp = mundo.client.get(f"{API}/maestros/terceros?{nombre}=5", headers=cabeceras)
        _error_contracto(
            resp,
            code="UNKNOWN_QUERY_PARAMETER",
            nombres=[nombre],
            message="La consulta incluye parámetros que esta operación no admite.",
        )


def test_q05_varios_ordenados(mundo, reloj_mfa, rol_operador):
    """Q-05: los desconocidos se listan únicos y ordenados lexicográficamente."""
    cabeceras = _operador(mundo, reloj_mfa, rol_operador)
    resp = mundo.client.get(f"{API}/maestros/terceros?zz_b=1&zz_a=2&page=1", headers=cabeceras)
    _error_contracto(
        resp,
        code="UNKNOWN_QUERY_PARAMETER",
        nombres=["zz_a", "zz_b"],
        message="La consulta incluye parámetros que esta operación no admite.",
    )


def test_q06_sin_eco_de_valores(mundo, reloj_mfa, rol_operador):
    """Q-06: el valor enviado nunca aparece en la respuesta de error."""
    cabeceras = _operador(mundo, reloj_mfa, rol_operador)
    resp = mundo.client.get(
        f"{API}/maestros/terceros?zz=VALOR-SENSIBLE-123",
        headers=cabeceras,
    )
    _error_contracto(
        resp,
        code="UNKNOWN_QUERY_PARAMETER",
        nombres=["zz"],
        message="La consulta incluye parámetros que esta operación no admite.",
    )
    assert "VALOR-SENSIBLE-123" not in resp.text


def test_q07_repetido(mundo, reloj_mfa, rol_operador):
    """Q-07: un desconocido repetido aparece una sola vez."""
    cabeceras = _operador(mundo, reloj_mfa, rol_operador)
    resp = mundo.client.get(f"{API}/maestros/terceros?zz=1&zz=2", headers=cabeceras)
    _error_contracto(
        resp,
        code="UNKNOWN_QUERY_PARAMETER",
        nombres=["zz"],
        message="La consulta incluye parámetros que esta operación no admite.",
    )


def test_q08_declarado_repetido_conserva(mundo, reloj_mfa, rol_operador):
    """Q-08 (control): un declarado repetido conserva el comportamiento actual."""
    cabeceras = _operador(mundo, reloj_mfa, rol_operador)
    resp = mundo.client.get(f"{API}/maestros/terceros?page=1&page=2", headers=cabeceras)
    assert resp.status_code == 200, resp.text


def test_q09_post_patch_delete(mundo, reloj_mfa, rol_operador):
    """Q-09: POST, PATCH y DELETE bajo /api/v1 también aplican el contrato."""
    cabeceras = _operador(mundo, reloj_mfa, rol_operador)
    warehouse_id = str(uuid.uuid4())

    resp = mundo.client.post(f"{API}/maestros/terceros?zz=1", json={}, headers=cabeceras)
    _error_contracto(
        resp,
        code="UNKNOWN_QUERY_PARAMETER",
        nombres=["zz"],
        message="La consulta incluye parámetros que esta operación no admite.",
    )

    resp = mundo.client.patch(
        f"{API}/organization/warehouses/{warehouse_id}?zz=1",
        json={"name": "x"},
        headers=cabeceras,
    )
    _error_contracto(
        resp,
        code="UNKNOWN_QUERY_PARAMETER",
        nombres=["zz"],
        message="La consulta incluye parámetros que esta operación no admite.",
    )

    resp = mundo.client.delete(
        f"{API}/organization/warehouses/{warehouse_id}?zz=1",
        headers=cabeceras,
    )
    _error_contracto(
        resp,
        code="UNKNOWN_QUERY_PARAMETER",
        nombres=["zz"],
        message="La consulta incluye parámetros que esta operación no admite.",
    )


def test_q10_sin_token_401(mundo):
    """Q-10 (control): la autorización precede al verificador, sin token responde 401."""
    resp = mundo.client.get(f"{API}/maestros/terceros?zz=1")
    assert resp.status_code == 401, resp.text


def test_q11_precede_a_validacion_de_valor(mundo, reloj_mfa, rol_operador):
    """Q-11: el verificador va antes de la validación de valores declarados."""
    cabeceras = _operador(mundo, reloj_mfa, rol_operador)
    resp = mundo.client.get(
        f"{API}/maestros/terceros?page_size=abc&zz=1",
        headers=cabeceras,
    )
    _error_contracto(
        resp,
        code="UNKNOWN_QUERY_PARAMETER",
        nombres=["zz"],
        message="La consulta incluye parámetros que esta operación no admite.",
    )


def test_q12_cabecera_no_es_consulta(mundo, reloj_mfa, rol_operador):
    """Q-12 (control): las cabeceras no son parte de la consulta."""
    cabeceras = _operador(mundo, reloj_mfa, rol_operador)
    resp = mundo.client.get(f"{API}/maestros/terceros", headers=cabeceras)
    assert resp.status_code == 200, resp.text


def test_n02_selectores_de_alcance_desconocidos(mundo, reloj_mfa, rol_operador):
    """N-02: nombres de seguridad o alcance no declarados también se rechazan."""
    cabeceras = _operador(mundo, reloj_mfa, rol_operador)
    resp = mundo.client.get(
        f"{API}/maestros/terceros?tenant_id=x&company_id=y",
        headers=cabeceras,
    )
    _error_contracto(
        resp,
        code="UNKNOWN_QUERY_PARAMETER",
        nombres=["company_id", "tenant_id"],
        message="La consulta incluye parámetros que esta operación no admite.",
    )


def test_n01_nombre_de_seguridad(mundo, reloj_mfa, rol_operador):
    """N-01: nombres sensibles de seguridad no declarados son rechazados."""
    cabeceras = _operador(mundo, reloj_mfa, rol_operador)
    resp = mundo.client.get(
        f"{API}/maestros/terceros?include_deleted=true&as_user=admin",
        headers=cabeceras,
    )
    _error_contracto(
        resp,
        code="UNKNOWN_QUERY_PARAMETER",
        nombres=["as_user", "include_deleted"],
        message="La consulta incluye parámetros que esta operación no admite.",
    )


def test_q13_dependencias_y_subdependencias():
    """Q-13: se incluyen parámetros de dependencias y subdependencias; idempotente."""
    from app.core.query_contract import (
        VerificadorDeConsulta,
        instalar_contrato_de_consulta,
        parametros_de_consulta_declarados,
    )

    app = FastAPI()
    register_exception_handlers(app)

    def dep_anidada(filtro_anidado: str | None = None):
        return filtro_anidado

    def dep(filtro_dep: str | None = None, _=Depends(dep_anidada)):
        return filtro_dep

    @app.get("/api/v1/sintetica")
    def sintetica(propio: str | None = None, _=Depends(dep)):
        return {"ok": True}

    @app.get("/fuera")
    def fuera():
        return {"ok": True}

    instalar_contrato_de_consulta(app, "/api/v1")
    instalar_contrato_de_consulta(app, "/api/v1")

    client = TestClient(app)
    resp = client.get("/api/v1/sintetica?propio=1&filtro_dep=2&filtro_anidado=3")
    assert resp.status_code == 200, resp.text

    resp = client.get("/api/v1/sintetica?otro=1")
    _error_contracto(
        resp,
        code="UNKNOWN_QUERY_PARAMETER",
        nombres=["otro"],
        message="La consulta incluye parámetros que esta operación no admite.",
    )

    resp = client.get("/fuera?otro=1")
    assert resp.status_code == 200, resp.text

    ruta = next(
        r
        for r in app.routes
        if isinstance(r, APIRoute) and r.path == "/api/v1/sintetica"
    )
    verificadores = [
        d
        for d in ruta.dependant.dependencies
        if isinstance(d.call, VerificadorDeConsulta)
    ]
    assert len(verificadores) == 1
    assert ruta.dependant.dependencies[-1] is verificadores[0]
    assert parametros_de_consulta_declarados(ruta) == frozenset(
        {"propio", "filtro_dep", "filtro_anidado"}
    )


def test_guard_q01_estructural():
    """GUARD-Q-01: todas las rutas /api/v1 tienen exactamente un verificador final."""
    from app.core.query_contract import (
        VerificadorDeConsulta,
        parametros_de_consulta_declarados,
    )
    from app.main import create_app

    app = create_app()
    violaciones = []
    contadas = 0
    for ruta in iter_route_contexts(app.routes):
        if not isinstance(ruta.original_route, APIRoute):
            continue
        if not (ruta.path or "").startswith("/api/v1"):
            continue
        contadas += 1
        verificadores = [
            d
            for d in ruta.dependant.dependencies
            if isinstance(d.call, VerificadorDeConsulta)
        ]
        if len(verificadores) != 1:
            violaciones.append((ruta.path, "verificadores", len(verificadores)))
            continue
        if ruta.dependant.dependencies[-1] is not verificadores[0]:
            violaciones.append((ruta.path, "posicion", "no-final"))
        if verificadores[0].call.permitidos != parametros_de_consulta_declarados(ruta):
            violaciones.append((ruta.path, "permitidos", "desajuste"))
    assert not violaciones, violaciones
    assert contadas >= 400, contadas


def test_guard_q02_barrido(mundo, reloj_mfa):
    """GUARD-Q-02: toda operación /api/v1 rechaza `zz_no_declarado` salvo autorización previa."""
    nombre = f"sqc{uuid.uuid4().hex[:12]}"
    crear_usuario(mundo, nombre, admin=True, funcional=True)
    cabeceras = _entrar(mundo, reloj_mfa, nombre)
    cabeceras["X-Kontrol-Company"] = str(mundo.company_id)

    violaciones = []
    rechazadas = 0
    for ruta in iter_route_contexts(mundo.client.app.routes):
        if not isinstance(ruta.original_route, APIRoute):
            continue
        if not (ruta.path or "").startswith("/api/v1"):
            continue
        metodos = set(ruta.methods or set())
        for metodo in metodos - {"HEAD", "OPTIONS"}:
            url = re.sub(r"\{[^}]+\}", lambda _m: str(uuid.uuid4()), ruta.path)
            try:
                resp = mundo.client.request(
                    metodo, url, headers=cabeceras, params={"zz_no_declarado": "1"}
                )
            except Exception as exc:  # noqa: BLE001 - el barrido registra la violación.
                violaciones.append((metodo, ruta.path, "EXCEPCION", repr(exc)))
                continue
            cuerpo = {}
            try:
                cuerpo = resp.json()
            except ValueError:
                cuerpo = {}
            if resp.status_code == 422 and cuerpo.get("code") == "UNKNOWN_QUERY_PARAMETER":
                rechazadas += 1
                continue
            try:
                resp_sin = mundo.client.request(metodo, url, headers=cabeceras)
            except Exception as exc:  # noqa: BLE001
                violaciones.append((metodo, ruta.path, "EXCEPCION-SIN", repr(exc)))
                continue
            if resp.status_code in {401, 403, 423} and resp_sin.status_code == resp.status_code:
                continue
            violaciones.append((metodo, ruta.path, resp.status_code, cuerpo.get("code")))
    assert not violaciones, violaciones
    assert rechazadas >= 300, rechazadas


def test_guard_q03_sin_lectores_manuales():
    """GUARD-Q-03: solo query_contract.py lee `query_params` o `url.query`."""
    raiz = Path(__file__).resolve().parents[1] / "app"
    violaciones = []
    for archivo in raiz.rglob("*.py"):
        if archivo.name == "query_contract.py":
            continue
        arbol = ast.parse(archivo.read_text(encoding="utf-8"), filename=str(archivo))
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Attribute) and nodo.attr == "query_params":
                violaciones.append(f"{archivo}:{nodo.lineno}")
                break
            if (
                isinstance(nodo, ast.Attribute)
                and nodo.attr == "query"
                and isinstance(nodo.value, ast.Attribute)
                and nodo.value.attr == "url"
            ):
                violaciones.append(f"{archivo}:{nodo.lineno}")
                break
    assert not violaciones, violaciones
