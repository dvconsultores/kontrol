"""OAS · El OpenAPI describe la autenticación REAL de KONTROL y nada más (OPENAPI-SIN-ESQUEMA-DE-SEGURIDAD;
FR-001-020/021; FR-001-042). La autoridad es el runtime: la matriz compara, operación por operación, si el
árbol de dependencias llega a `get_current_user` (protegida) con lo que el contrato declara, sin lista manual
de rutas. La seguridad documentada no cambia el runtime: los 401/403, el permiso y el contexto de empresa se
prueban aparte con peticiones reales. Mundo sintético (SQLite); nada real.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi import routing as fastapi_routing
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core import dependencies as dep
from app.core.config import get_settings
from app.core.database import Base, get_db, init_models
from app.main import create_app
from app.modules.organization.models import Company, Tenant
from app.modules.setup.api import SetupRequest, initialize
from tests.conftest import make_engine
from tests.test_system_access import PASSWORD, _usuario

ESQUEMA = dep.BEARER_SCHEME_NAME
METODOS = ("get", "post", "put", "patch", "delete")
#: Las operaciones que el runtime deja sin sesión (ninguna llega a `get_current_user`): health, bootstrap,
#: estado público de licencia, login/refresh/logout/recuperación y la raíz. Es una AFIRMACIÓN de contrato, no
#: la fuente del contrato: OAS-14 la deriva del árbol de dependencias y OAS-13 exige que coincidan.
PUBLICAS_POR_CONTRATO = {
    ("GET", "/api/v1/health/live"), ("GET", "/api/v1/health/ready"),
    ("GET", "/api/v1/setup/status"), ("POST", "/api/v1/setup/initialize"),
    ("GET", "/api/v1/license/status"),
    ("POST", "/api/v1/auth/login"), ("POST", "/api/v1/auth/refresh"), ("POST", "/api/v1/auth/logout"),
    ("POST", "/api/v1/auth/password-reset/request"), ("POST", "/api/v1/auth/password-reset/confirm"),
    ("GET", "/"),
}

_APP = None
_CLIENT: TestClient


def _llega_a(dependant, objetivo) -> bool:
    return dependant.call is objetivo or any(_llega_a(d, objetivo) for d in dependant.dependencies)


def _matriz_runtime(app) -> dict[tuple[str, str], bool]:
    """(MÉTODO, ruta) → ¿protegida en runtime? Leída del árbol de dependencias real de cada ruta.

    Con FastAPI 0.115, `app.routes` contiene las APIRoute ya planas con su prefijo.
    Con FastAPI 0.141, las inclusiones de routers aparecen como objetos internos; la API
    pública `fastapi.routing.iter_route_contexts` permite recorrerlas y obtener la ruta
    original, la ruta efectiva (con prefijo) y los métodos expuestos.
    """
    matriz: dict[tuple[str, str], bool] = {}

    iterar = getattr(fastapi_routing, "iter_route_contexts", None)

    if iterar is None:
        fuentes = ((r, r.path, r.methods, None) for r in app.routes)
    else:
        fuentes = (
            (rc.original_route, rc.path, rc.methods, rc)
            for rc in iterar(app.routes)
        )

    for original, path, methods, rc in fuentes:
        if not isinstance(original, APIRoute):
            continue

        if rc is not None:
            dependencias_inclusion = list(getattr(rc, "dependencies", original.dependencies))
            if dependencias_inclusion != list(original.dependencies):
                raise AssertionError(
                    f"la inclusión de {path} añade dependencias que esta matriz no mira"
                )

        for method in (methods or set()) - {"HEAD", "OPTIONS"}:
            clave = (method, path)
            assert clave not in matriz, f"operación duplicada en runtime: {clave}"
            matriz[clave] = _llega_a(original.dependant, dep.get_current_user)

    return matriz


def _operaciones(esquema: dict) -> dict[tuple[str, str], dict]:
    return {(m.upper(), ruta): op for ruta, item in esquema["paths"].items() for m, op in item.items() if m in METODOS}


@pytest.fixture(scope="module", autouse=True)
def _mundo() -> Iterator[None]:
    global _APP, _CLIENT
    import app.core.database as dm

    engine = make_engine()
    init_models()
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    dm._engine, dm._SessionLocal = engine, factory  # type: ignore[attr-defined]
    with factory() as db:
        initialize(db, SetupRequest(tenant_code="DEMO", tenant_name="Empresa Demo", company_code="D1", company_legal_name="Demo C.A.",
                                    company_rif="J-12345678-9", admin_username="admin", admin_password=PASSWORD))
        tenant = db.execute(select(Tenant).where(Tenant.code == "DEMO")).scalars().one()
        empresa = db.execute(select(Company).where(Company.tenant_id == tenant.id)).scalars().one()
        _usuario(db, str(tenant.id), str(empresa.id), "operador", sin={"license:view"})
        db.commit()
    _APP = create_app()

    def _db():
        d = factory()
        try:
            yield d
        finally:
            d.close()

    _APP.dependency_overrides[get_db] = _db
    _CLIENT = TestClient(_APP)
    yield


def _sesion(username: str = "admin") -> dict[str, str]:
    r = _CLIENT.post("/api/v1/auth/login", json={"tenant_code": "DEMO", "username": username, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ---------------------------------------------------------------- OAS-01/02 · el esquema existe y es el real
def test_oas_01_el_openapi_declara_exactamente_el_esquema_real_y_ninguno_global():
    s = _APP.openapi()
    assert s["openapi"].startswith("3.")
    assert ESQUEMA == "BearerAccessToken"  # el nombre es contrato: estable para los clientes generados
    assert list(s["components"]["securitySchemes"]) == ["BearerAccessToken"]
    assert "security" not in s  # sin seguridad global: cada operación declara la suya desde su dependencia


def test_oas_02_el_esquema_es_http_bearer_jwt_sin_oauth2_ni_api_key_ni_cookie():
    esquema = _APP.openapi()["components"]["securitySchemes"][ESQUEMA]
    assert esquema["type"] == "http" and esquema["scheme"] == "bearer" and esquema["bearerFormat"] == "JWT"
    assert "flows" not in esquema and "in" not in esquema and "openIdConnectUrl" not in esquema
    texto = json.dumps(_APP.openapi())
    assert "oauth2" not in texto.lower() and '"apiKey"' not in texto and "openIdConnect" not in texto
    assert get_settings().jwt_algorithm.startswith("HS")  # es un JWT de verdad, firmado por el backend


# ---------------------------------------------------------------- OAS-03..13 · públicas y protegidas por contrato
@pytest.mark.parametrize(("metodo", "ruta"), sorted(PUBLICAS_POR_CONTRATO))
def test_oas_03_13_las_operaciones_publicas_del_contrato_no_declaran_seguridad(metodo: str, ruta: str):
    op = _operaciones(_APP.openapi())[(metodo, ruta)]
    assert "security" not in op, (metodo, ruta, op.get("security"))


@pytest.mark.parametrize(("metodo", "ruta"), [
    ("GET", "/api/v1/system/diagnostics"), ("GET", "/api/v1/auth/me"), ("GET", "/api/v1/auth/sessions"),
    ("POST", "/api/v1/license/import"), ("POST", "/api/v1/licensing/sync"), ("GET", "/api/v1/license/detail"),
    ("GET", "/api/v1/users"), ("GET", "/api/v1/organization/companies"), ("GET", "/api/v1/notifications/counts"),
])
def test_oas_09_12_las_operaciones_protegidas_declaran_el_esquema_real(metodo: str, ruta: str):
    op = _operaciones(_APP.openapi())[(metodo, ruta)]
    assert op["security"] == [{ESQUEMA: []}], (metodo, ruta, op.get("security"))


# ---------------------------------------------------------------- OAS-14 · la matriz completa: runtime ↔ contrato, 0 desajustes
def test_oas_14_toda_operacion_coincide_runtime_con_contrato_y_las_publicas_son_exactamente_las_del_contrato():
    runtime = _matriz_runtime(_APP)
    contrato = _operaciones(_APP.openapi())
    assert set(runtime) == set(contrato), "el OpenAPI y las rutas no cuentan lo mismo"
    desajustes = [(m, r) for (m, r), protegida in runtime.items() if protegida != ("security" in contrato[(m, r)])]
    assert desajustes == []
    publicas = {k for k, protegida in runtime.items() if not protegida}
    assert publicas == PUBLICAS_POR_CONTRATO
    protegidas = [op for k, op in contrato.items() if runtime[k]]
    assert len(protegidas) >= 500 and all(op["security"] == [{ESQUEMA: []}] for op in protegidas)


# ---------------------------------------------------------------- OAS-15..18 · el runtime no cambió
def test_oas_15_anonimo_a_protegida_sigue_401_auth_required_sin_cuerpo_de_negocio():
    for ruta in ("/api/v1/system/diagnostics", "/api/v1/auth/me", "/api/v1/users"):
        r = _CLIENT.get(ruta)
        assert r.status_code == 401 and r.json()["code"] == "AUTH_REQUIRED", (ruta, r.text)


@pytest.mark.parametrize(("cabecera", "codigo"), [
    ("Basic YWRtaW46YWRtaW4=", "AUTH_REQUIRED"), ("Token abc", "AUTH_REQUIRED"),
    ("bearer abc", "AUTH_REQUIRED"),  # el esquema es literal `Bearer `; el HTTPBearer de serie lo habría aceptado
    ("Bearer", "AUTH_REQUIRED"),  # sin espacio no es el prefijo literal
    ("Bearer ", "AUTH_INVALID_TOKEN"),  # credencial vacía: se intenta decodificar y falla, como siempre
    ("Bearer no.es.un.token", "AUTH_INVALID_TOKEN"), ("Bearer eyJhbGciOiJub25lIn0.e30.", "AUTH_INVALID_TOKEN"),
])
def test_oas_15b_las_credenciales_ilegibles_conservan_codigo_y_401(cabecera: str, codigo: str):
    r = _CLIENT.get("/api/v1/auth/me", headers={"Authorization": cabecera})
    assert r.status_code == 401 and r.json()["code"] == codigo, (cabecera, r.text)


def test_oas_15c_un_token_caducado_firmado_con_la_clave_real_sigue_401():
    caducado = jwt.encode({"sub": "x", "type": "access", "exp": datetime.now(UTC) - timedelta(minutes=1)}, get_settings().secret_key,
                          algorithm=get_settings().jwt_algorithm)
    r = _CLIENT.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {caducado}"})
    assert r.status_code == 401 and r.json()["code"] == "AUTH_INVALID_TOKEN"
    refresh = jwt.encode({"sub": "x", "type": "refresh", "exp": datetime.now(UTC) + timedelta(minutes=5)}, get_settings().secret_key,
                         algorithm=get_settings().jwt_algorithm)
    assert _CLIENT.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {refresh}"}).json()["code"] == "AUTH_INVALID_TOKEN"  # tipo incorrecto


def test_oas_16_anonimo_a_publica_sigue_igual():
    assert _CLIENT.get("/api/v1/health/live").json() == {"status": "ok", "service": "kontrol-backend"}
    assert set(_CLIENT.get("/api/v1/health/ready").json()) == {"status", "service", "database"}
    assert set(_CLIENT.get("/api/v1/license/status").json()) == {"mode", "license_url"}
    assert _CLIENT.get("/").json() == {"service": get_settings().app_name, "status": "ok"}
    assert _CLIENT.get("/api/v1/setup/status").status_code == 200
    assert _CLIENT.post("/api/v1/auth/logout").json() == {"ok": True}  # sin sesión también responde: borra la cookie si la hubiera


def test_oas_17_con_sesion_y_sin_permiso_sigue_403_permission_denied():
    r = _CLIENT.get("/api/v1/system/diagnostics", headers=_sesion("operador"))
    assert r.status_code == 403 and r.json()["code"] == "PERMISSION_DENIED"
    assert _CLIENT.get("/api/v1/system/diagnostics", headers=_sesion("admin")).status_code == 200
    assert _CLIENT.get("/api/v1/auth/me", headers=_sesion("operador")).status_code == 200  # autenticado sí; autorizado, según permiso


def test_oas_18_el_contexto_de_empresa_sigue_siendo_del_backend():
    cabeceras = _sesion("admin")
    r = _CLIENT.get("/api/v1/notifications/counts", headers={**cabeceras, "X-Kontrol-Company": "00000000-0000-0000-0000-000000000000"})
    assert r.status_code == 404 and r.json()["code"] == "COMPANY_NOT_FOUND"  # política existente: inexistente, ajena o fuera de alcance → 404, sin filtrar
    assert _CLIENT.get("/api/v1/notifications/counts", headers=cabeceras).status_code == 200  # una sola empresa: se resuelve sola


# ---------------------------------------------------------------- OAS-19..22 · lo que NO se documenta como seguridad
def test_oas_19_la_cabecera_de_empresa_no_es_un_esquema_de_seguridad_pero_sigue_declarada_como_parametro():
    s = _APP.openapi()
    assert "X-Kontrol-Company" not in json.dumps(s["components"]["securitySchemes"])
    cabeceras = {p["name"] for op in _operaciones(s).values() for p in op.get("parameters", []) if p.get("in") == "header"}
    assert "X-Kontrol-Company" in cabeceras


def test_oas_20_los_permisos_internos_no_aparecen_como_scopes():
    s = _APP.openapi()
    for op in _operaciones(s).values():
        for req in op.get("security", []):
            assert req == {ESQUEMA: []}, req  # sin scopes: la autorización interna no es OAuth


def test_oas_21_la_cookie_de_refresh_es_un_parametro_de_refresh_y_no_un_esquema():
    s = _APP.openapi()
    op = _operaciones(s)[("POST", "/api/v1/auth/refresh")]
    assert any(p.get("in") == "cookie" and p["name"] == "kontrol_refresh" for p in op.get("parameters", []))
    assert all(e.get("type") == "http" and "in" not in e for e in s["components"]["securitySchemes"].values())  # ningún esquema apiKey/cookie


def test_oas_22_el_contrato_no_contiene_material_y_es_determinista():
    texto = json.dumps(_APP.openapi(), sort_keys=True)
    assert get_settings().secret_key not in texto and "eyJ" not in texto
    assert texto == json.dumps(create_app().openapi(), sort_keys=True)


def test_oas_23_un_solo_analizador_de_la_cabecera_y_docs_solo_fuera_de_prod():
    """`read_bearer_credentials` es la única lectura de `Authorization`; `/docs`, `/redoc` y `/openapi.json` se
    sirven fuera de `prod` y no en `prod` (contrato existente, sin cambio)."""
    import inspect

    from app.core import company_context

    assert "Authorization" in inspect.getsource(dep.read_bearer_credentials)
    assert 'headers.get("Authorization"' not in inspect.getsource(company_context)
    assert _CLIENT.get("/openapi.json").status_code == 200 and _CLIENT.get("/docs").status_code == 200
    assert create_app().docs_url == "/docs"  # entorno qa del mundo; en prod `create_app` deja `docs_url=None`
