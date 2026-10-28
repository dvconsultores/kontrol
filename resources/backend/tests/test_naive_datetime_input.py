"""Pruebas del contrato estricto de entrada de fechas INSTANT (ADR-020).

Toda entrada clasificada INSTANT debe incluir zona horaria explícita.
Hoy estas pruebas son ROJAS: los instantes sin zona se aceptan como UTC.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from mfa_mundo import API, alta_por_desafio, crear_usuario, login, mundo_mfa
from pydantic import BaseModel, TypeAdapter, ValidationError

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
def rol_tiempo(mundo):
    db = mundo.factory()
    try:
        rol = identity_service.create_role(
            db,
            tenant_id=mundo.tenant_id,
            code=f"ROL_TIEMPO_{uuid.uuid4().hex[:8]}",
            name="Rol tiempo",
            company_id=None,
            permissions=[
                "aprobaciones:view",
                "aprobaciones:delegate",
                "tesoreria:view",
                "audit:view",
                "fiscal:view",
            ],
            actor=mundo.admin_id,
        )
        db.commit()
        return rol["id"]
    finally:
        db.close()


def _actor(mundo, reloj, rol_tiempo):
    usuario = f"ndt{uuid.uuid4().hex[:12]}"
    user_id = crear_usuario(mundo, usuario)
    _dar(mundo, user_id, rol_tiempo, mundo.company_id)
    cabeceras = _entrar(mundo, reloj, usuario)
    cabeceras["X-Kontrol-Company"] = str(mundo.company_id)
    return cabeceras


MENSAJE_ZONA = "Indique la zona horaria (Z o ±HH:MM)."
MENSAJE_NAIVE = "La fecha y hora debe indicar su zona horaria."


def _assert_naive_simple(r, campo):
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "NAIVE_DATETIME", r.text
    assert r.json()["message"] == MENSAJE_NAIVE, r.text
    assert r.json()["field_errors"] == {campo: [MENSAJE_ZONA]}, r.text


def test_d01_cuerpo_sin_zona(mundo, reloj_mfa, rol_tiempo):
    """D-01: cuerpo INSTANT sin zona devuelve NAIVE_DATETIME."""

    cabeceras = _actor(mundo, reloj_mfa, rol_tiempo)
    r = mundo.client.post(
        f"{API}/approvals/delegations",
        headers=cabeceras,
        json={
            "grantor_id": str(uuid.uuid4()),
            "grantee_id": str(uuid.uuid4()),
            "valid_from": "2026-03-10T12:00:00",
        },
    )
    _assert_naive_simple(r, "valid_from")


def test_d02_consulta_sin_zona(mundo, reloj_mfa, rol_tiempo):
    """D-02: consulta INSTANT sin zona devuelve NAIVE_DATETIME."""

    cabeceras = _actor(mundo, reloj_mfa, rol_tiempo)
    r = mundo.client.get(
        f"{API}/notifications",
        headers=cabeceras,
        params={"created_from": "2026-03-10T12:00:00"},
    )
    _assert_naive_simple(r, "query.created_from")

    r = mundo.client.get(
        f"{API}/tasks",
        headers=cabeceras,
        params={"due_to": "2026-03-10T12:00:00"},
    )
    _assert_naive_simple(r, "query.due_to")


def test_d03_fecha_suelta_en_instante(mundo, reloj_mfa, rol_tiempo):
    """D-03: una fecha suelta en un campo INSTANT es NAIVE_DATETIME."""

    cabeceras = _actor(mundo, reloj_mfa, rol_tiempo)
    r = mundo.client.get(
        f"{API}/treasury/exchange-rates/resolve",
        headers=cabeceras,
        params={
            "base_currency": "USD",
            "quote_currency": "VED",
            "effective_at": "2026-03-10",
        },
    )
    _assert_naive_simple(r, "query.effective_at")


def test_d04_con_zona_aceptado(mundo, reloj_mfa, rol_tiempo):
    """D-04: los instantes con zona explícita se aceptan (CONTROL)."""

    cabeceras = _actor(mundo, reloj_mfa, rol_tiempo)
    for valor in (
        "2026-03-10T12:00:00Z",
        "2026-03-10T12:00:00+00:00",
        "2026-03-10T08:00:00-04:00",
    ):
        r = mundo.client.get(
            f"{API}/notifications",
            headers=cabeceras,
            params={"created_from": valor},
        )
        assert r.status_code == 200, r.text


def test_d05_cuerpo_con_zona_sin_error_de_zona(mundo, reloj_mfa, rol_tiempo):
    """D-05: cuerpo INSTANT con zona no produce error de zona (CONTROL)."""

    cabeceras = _actor(mundo, reloj_mfa, rol_tiempo)
    r = mundo.client.post(
        f"{API}/approvals/delegations",
        headers=cabeceras,
        json={
            "grantor_id": str(uuid.uuid4()),
            "grantee_id": str(uuid.uuid4()),
            "valid_from": "2026-03-10T08:00:00-04:00",
        },
    )
    assert r.json().get("code") != "NAIVE_DATETIME", r.text
    if isinstance(r.json().get("field_errors"), dict):
        assert "valid_from" not in r.json()["field_errors"], r.text


def test_d06_mixto_es_validation_error(mundo, reloj_mfa, rol_tiempo):
    """D-06: error de zona más otros errores produce VALIDATION_ERROR."""

    cabeceras = _actor(mundo, reloj_mfa, rol_tiempo)
    r = mundo.client.post(
        f"{API}/approvals/delegations",
        headers=cabeceras,
        json={
            "grantor_id": str(uuid.uuid4()),
            "valid_from": "2026-03-10T12:00:00",
        },
    )
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "VALIDATION_ERROR", r.text
    assert r.json()["field_errors"]["valid_from"] == [MENSAJE_ZONA], r.text
    assert "grantee_id" in r.json()["field_errors"], r.text


def test_d07_sin_eco_del_valor(mundo, reloj_mfa, rol_tiempo):
    """D-07: el valor rechazado nunca se repite en la respuesta."""

    cabeceras = _actor(mundo, reloj_mfa, rol_tiempo)
    valor = "2026-03-10T12:34:56"
    r = mundo.client.get(
        f"{API}/notifications",
        headers=cabeceras,
        params={"created_from": valor},
    )
    assert r.status_code == 422, r.text
    assert "12:34:56" not in r.text, r.text


def test_d08_sintaxis_invalida(mundo, reloj_mfa, rol_tiempo):
    """D-08: sintaxis inválida es VALIDATION_ERROR (CONTROL)."""

    cabeceras = _actor(mundo, reloj_mfa, rol_tiempo)
    r = mundo.client.get(
        f"{API}/notifications",
        headers=cabeceras,
        params={"created_from": "2026-13-40T99:00:00Z"},
    )
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "VALIDATION_ERROR", r.text


def test_d09_anidado_y_lista_sintetico():
    """D-09: la aplicación sintética valida anidados, listas y query."""

    from app.core.errors import register_exception_handlers
    from app.shared.clock import InstanteDeEntrada

    class Linea(BaseModel):
        momento: InstanteDeEntrada

    class Cuerpo(BaseModel):
        lineas: list[Linea]

    app = FastAPI()
    register_exception_handlers(app)

    @app.post("/api/v1/sintetica")
    def sintetica(body: Cuerpo, desde: InstanteDeEntrada | None = None):
        return {
            "momento": body.lineas[0].momento.isoformat(),
            "desde": desde.isoformat() if desde else None,
        }

    client = TestClient(app)

    r = client.post(
        "/api/v1/sintetica",
        json={
            "lineas": [
                {"momento": "2026-03-10T08:00:00-04:00"},
                {"momento": "2026-03-10T12:00:00"},
            ]
        },
    )
    _assert_naive_simple(r, "lineas.1.momento")

    r = client.post(
        "/api/v1/sintetica",
        json={"lineas": [{"momento": "2026-03-10T08:00:00-04:00"}]},
    )
    assert r.status_code == 200, r.text
    assert r.json()["momento"] == "2026-03-10T12:00:00+00:00", r.text

    r = client.post(
        "/api/v1/sintetica",
        json={"lineas": [{"momento": "2026-03-10T08:00:00-04:00"}]},
        params={"desde": "2026-03-10T12:00:00"},
    )
    _assert_naive_simple(r, "query.desde")


def test_d10_normaliza_a_utc():
    """D-10: InstanteDeEntrada normaliza a UTC y exige zona."""

    from app.shared.clock import InstanteDeEntrada

    valor = TypeAdapter(InstanteDeEntrada).validate_python(
        "2026-03-10T08:00:00-04:00"
    )
    assert valor == datetime(2026, 3, 10, 12, 0, tzinfo=UTC)
    assert valor.utcoffset() == timedelta(0)

    with pytest.raises(ValidationError) as exc:
        TypeAdapter(InstanteDeEntrada).validate_python(
            datetime(2026, 3, 10, 12, 0)
        )
    assert exc.value.errors()[0]["type"] == "timezone_aware"


def test_d11_fecha_de_negocio_intacta(mundo, reloj_mfa, rol_tiempo):
    """D-11: las fechas BUSINESS_DATE siguen intactas (CONTROL)."""

    cabeceras = _actor(mundo, reloj_mfa, rol_tiempo)
    r = mundo.client.get(
        f"{API}/audit/events",
        headers=cabeceras,
        params={"desde": "2026-10-28", "hasta": "2026-10-28"},
    )
    assert r.status_code == 200, r.text


def test_d12_periodo_intacto(mundo, reloj_mfa, rol_tiempo):
    """D-12: el parámetro PERIOD sigue intacto (CONTROL)."""

    cabeceras = _actor(mundo, reloj_mfa, rol_tiempo)
    r = mundo.client.get(
        f"{API}/fiscal/books/IGTF",
        headers=cabeceras,
        params={"period": "2026-10"},
    )
    assert r.status_code == 200, r.text


def test_guard_d01_ningun_datetime_desnudo():
    """GUARD-D-01: ninguna ruta usa datetime.datetime desnudo; AwareDatetime >= 16."""

    import datetime
    import types
    import typing

    from fastapi.dependencies.utils import get_flat_dependant
    from fastapi.routing import APIRoute
    from pydantic import AwareDatetime

    from app.main import create_app

    app = create_app()
    violaciones: list[str] = []
    instantes = 0
    visitados: set[type] = set()

    def _recorrer(tp, lugar):
        nonlocal instantes

        if tp is AwareDatetime:
            instantes += 1
            return

        if tp is datetime.datetime:
            violaciones.append(lugar)
            return

        origen = typing.get_origin(tp)
        args = typing.get_args(tp)

        if origen is typing.Annotated:
            _recorrer(args[0], lugar)
            return

        if origen in (
            typing.Union,
            types.UnionType,
            list,
            tuple,
            set,
            frozenset,
        ):
            for arg in args:
                if arg is type(None) or arg is Ellipsis:
                    continue
                _recorrer(arg, lugar)
            return

        if origen is dict:
            if len(args) == 2:
                _recorrer(args[1], lugar)
            return

        if isinstance(tp, type) and issubclass(tp, BaseModel):
            if tp in visitados:
                return
            visitados.add(tp)
            for nombre, campo in tp.model_fields.items():
                _recorrer(campo.annotation, f"{lugar}.{nombre}")
            return

    for ruta in app.routes:
        if not isinstance(ruta, APIRoute) or not ruta.path.startswith("/api/v1"):
            continue

        dependant = get_flat_dependant(ruta.dependant, skip_repeats=True)

        for p in (
            *dependant.query_params,
            *dependant.path_params,
            *dependant.header_params,
            *dependant.cookie_params,
        ):
            _recorrer(p.field_info.annotation, f"{ruta.path}:{p.name}")

        for p in dependant.body_params:
            _recorrer(p.field_info.annotation, f"{ruta.path}:body")

    assert not violaciones, violaciones
    assert instantes >= 16, instantes
