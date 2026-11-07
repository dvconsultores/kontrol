"""Pruebas de regresión que protegen el catálogo de operaciones frente a inclusión perezosa de FastAPI 0.141.1."""

from pathlib import Path

import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from app.core.company_context import get_company_context
from app.core.operaciones import catalogo_de_operaciones
from app.core.route_contexts import contextos_de_api
from app.main import create_app

BACKEND = Path(__file__).resolve().parents[1]
REPOSITORIO = BACKEND.parents[1]


class _Dependencia:
    """Dependencia de prueba que declara las marcas que lee el catálogo."""

    def __init__(self, permiso: str, alcance: str | None = None) -> None:
        self.kontrol_permission = permiso
        self.kontrol_scope = alcance

    def __call__(self) -> None:
        return None


@pytest.fixture(scope="module")
def app_real() -> FastAPI:
    """Devuelve la aplicación FastAPI real."""
    return create_app()


@pytest.fixture(autouse=True)
def _cache_aislada(monkeypatch: pytest.MonkeyPatch) -> None:
    """Aísla la caché por `id(app)`: una app nueva podría reutilizar un id ya destruido."""
    monkeypatch.setattr("app.core.operaciones._CATALOGOS", {})


def test_catalogo_real_supera_el_umbral(app_real: FastAPI) -> None:
    """Comprueba que el catálogo contiene al menos 600 operaciones."""
    catalogo = catalogo_de_operaciones(app_real)
    assert len(catalogo) >= 600


def test_catalogo_coincide_con_openapi(app_real: FastAPI) -> None:
    """Comprueba que el catálogo coincide con las rutas declaradas en OpenAPI."""
    catalogo = catalogo_de_operaciones(app_real)
    catalogo_set = {(op["method"], op["path"]) for op in catalogo}
    openapi_set = set()
    for path, operaciones in app_real.openapi()["paths"].items():
        for method in ("get", "post", "put", "patch", "delete"):
            if method in operaciones:
                openapi_set.add((method.upper(), path))
    assert catalogo_set == openapi_set


@pytest.mark.parametrize(
    "operacion",
    [
        {"method": "GET", "path": "/api/v1/users", "capabilities": ["users:view"], "scope": "GLOBAL"},
        {"method": "POST", "path": "/api/v1/fiscal/legal-sources", "capabilities": ["fiscal:create"], "scope": "TENANT"},
        {"method": "GET", "path": "/api/v1/alerts", "capabilities": ["alertas:view"], "scope": "COMPANY"},
        {"method": "GET", "path": "/api/v1/authority/company", "capabilities": [], "scope": "COMPANY"},
        {"method": "GET", "path": "/api/v1/gobierno/cierres/bloqueos", "capabilities": ["gobierno_cierre:view"], "scope": "COMPANY"},
    ],
)
def test_operaciones_conocidas_conservan_contrato(app_real: FastAPI, operacion: dict[str, object]) -> None:
    """Comprueba que operaciones conocidas conservan su contrato."""
    catalogo = catalogo_de_operaciones(app_real)
    assert operacion in catalogo


def test_sin_head_ni_options(app_real: FastAPI) -> None:
    """Comprueba que el catálogo no contiene métodos HEAD ni OPTIONS."""
    catalogo = catalogo_de_operaciones(app_real)
    assert all(op["method"] not in ("HEAD", "OPTIONS") for op in catalogo)


def test_sin_operaciones_duplicadas(app_real: FastAPI) -> None:
    """Comprueba que no hay operaciones duplicadas en el catálogo."""
    catalogo = catalogo_de_operaciones(app_real)
    pares = {(op["method"], op["path"]) for op in catalogo}
    assert len(pares) == len(catalogo)


def test_catalogo_cacheado_por_aplicacion(app_real: FastAPI) -> None:
    """Comprueba que el catálogo se cachea por aplicación."""
    catalogo1 = catalogo_de_operaciones(app_real)
    catalogo2 = catalogo_de_operaciones(app_real)
    assert catalogo1 is catalogo2


def test_autorizacion_de_operaciones_exige_sesion(app_real: FastAPI) -> None:
    """Comprueba que el endpoint de operaciones exige sesión."""
    response = TestClient(app_real).get("/api/v1/auth/operations")
    assert response.status_code == 401


def _app_anidada() -> FastAPI:
    """Construye una mini aplicación con routers anidados."""
    permiso = _Dependencia("demo:view")
    alcance_tenant = _Dependencia("demo:create", "TENANT")

    interno = APIRouter(prefix="/interno")

    @interno.get("/global", dependencies=[Depends(permiso)])
    async def global_() -> dict[str, bool]:
        return {"ok": True}

    @interno.get("/empresa", dependencies=[Depends(permiso), Depends(get_company_context)])
    async def empresa_() -> dict[str, bool]:
        return {"ok": True}

    @interno.post("/tenant", dependencies=[Depends(alcance_tenant)])
    async def tenant_() -> dict[str, bool]:
        return {"ok": True}

    @interno.get("/ambos", dependencies=[Depends(alcance_tenant), Depends(get_company_context)])
    async def ambos_() -> dict[str, bool]:
        return {"ok": True}

    @interno.api_route("/varios", methods=["GET", "HEAD", "OPTIONS"])
    async def varios_() -> dict[str, bool]:
        return {"ok": True}

    externo = APIRouter(prefix="/externo")
    externo.include_router(interno)

    app = FastAPI()
    app.include_router(externo, prefix="/api/v1")

    @app.get("/directa")
    async def directa() -> dict[str, bool]:
        """Ruta directa."""
        return {"ok": True}

    async def plana(request: Request) -> PlainTextResponse:
        """Ruta plana que no es de API."""
        return PlainTextResponse("ok")

    app.add_route("/plana", plana)
    return app


def test_router_anidado_conserva_capacidad_y_alcance_global() -> None:
    """Comprueba que router anidado conserva capacidad y alcance global."""
    app = _app_anidada()
    catalogo = catalogo_de_operaciones(app)
    assert {"method": "GET", "path": "/api/v1/externo/interno/global",
            "capabilities": ["demo:view"], "scope": "GLOBAL"} in catalogo


def test_ruta_de_empresa_no_cae_a_global() -> None:
    """Comprueba que ruta de empresa conserva scope COMPANY."""
    app = _app_anidada()
    catalogo = catalogo_de_operaciones(app)
    assert {"method": "GET", "path": "/api/v1/externo/interno/empresa",
            "capabilities": ["demo:view"], "scope": "COMPANY"} in catalogo


def test_ruta_de_tenant_no_cae_a_global() -> None:
    """Comprueba que ruta de tenant conserva scope TENANT."""
    app = _app_anidada()
    catalogo = catalogo_de_operaciones(app)
    assert {"method": "POST", "path": "/api/v1/externo/interno/tenant",
            "capabilities": ["demo:create"], "scope": "TENANT"} in catalogo


def test_tenant_prevalece_sobre_empresa() -> None:
    """Comprueba que TENANT prevalece sobre COMPANY."""
    app = _app_anidada()
    catalogo = catalogo_de_operaciones(app)
    operacion = next(op for op in catalogo if op["path"] == "/api/v1/externo/interno/ambos")
    assert operacion["scope"] == "TENANT"


def test_metodos_explicitos_excluyen_head_y_options() -> None:
    """Comprueba que métodos explícitos excluyen HEAD y OPTIONS."""
    app = _app_anidada()
    catalogo = catalogo_de_operaciones(app)
    operaciones = [op for op in catalogo if op["path"] == "/api/v1/externo/interno/varios"]
    assert len(operaciones) == 1
    assert operaciones[0]["method"] == "GET"


def test_ruta_directa_y_anidada_conviven() -> None:
    """Comprueba que ruta directa y anidada conviven en el catálogo."""
    app = _app_anidada()
    catalogo = catalogo_de_operaciones(app)
    paths = {op["path"] for op in catalogo}
    assert "/directa" in paths
    assert "/api/v1/externo/interno/global" in paths


def test_contextos_de_api_excluye_rutas_que_no_son_de_api() -> None:
    """Comprueba que rutas planas quedan excluidas del contexto de API."""
    app = _app_anidada()
    contextos = list(contextos_de_api(app))
    assert all(contexto.path != "/plana" for contexto in contextos)
    catalogo = catalogo_de_operaciones(app)
    assert all(op["path"] != "/plana" for op in catalogo)


def test_dependencia_de_inclusion_aporta_capacidad() -> None:
    """Comprueba que la dependencia de inclusión aporta capacidad."""

    interno = APIRouter()

    @interno.get("/hija")
    async def hija() -> dict[str, bool]:
        return {"ok": True}

    app = FastAPI()
    app.include_router(
        interno,
        prefix="/api/v1",
        dependencies=[Depends(_Dependencia("demo:incluida"))],
    )
    catalogo = catalogo_de_operaciones(app)
    assert {
        "method": "GET",
        "path": "/api/v1/hija",
        "capabilities": ["demo:incluida"],
        "scope": "GLOBAL",
    } in catalogo


def test_ningun_consumidor_recorre_app_routes() -> None:
    """Comprueba que solo route_contexts recorre directamente app.routes."""
    ficheros_app = list((BACKEND / "app").rglob("*.py"))
    ficheros_qa = list((REPOSITORIO / "qa").glob("*.py"))
    for fichero in ficheros_app + ficheros_qa:
        if fichero.resolve() == (BACKEND / "app" / "core" / "route_contexts.py").resolve():
            continue
        contenido = fichero.read_text(encoding="utf-8")
        assert "app.routes" not in contenido, (
            f"{fichero} recorre app.routes directamente"
        )
