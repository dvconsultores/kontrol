"""Pruebas de contrato estricto de consulta con el runtime bloqueado.

Verifica que el arranque de la aplicación no dependa de ayudantes internos
de FastAPI eliminados en la versión fijada por los locks y que el contrato
estricto de consulta siga funcionando a cualquier profundidad de dependencias.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query
from fastapi.routing import APIRoute, iter_route_contexts
from fastapi.testclient import TestClient

from app.core.errors import register_exception_handlers
from app.core.query_contract import (
    CODIGO,
    VerificadorDeConsulta,
    instalar_contrato_de_consulta,
    parametros_de_consulta_declarados,
)

BACKEND = Path(__file__).resolve().parents[1]


def _app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    def nieta(profunda: str | None = None) -> None:
        return None

    def hija(media: str | None = None, _n: None = Depends(nieta)) -> None:
        return None

    def con_alias(valor: Annotated[str | None, Query(alias="otro-nombre")] = None) -> None:
        return None

    @app.get("/api/v1/raiz")
    def raiz(directa: str | None = None) -> dict[str, bool]:
        return {"ok": True}

    @app.get("/api/v1/dep")
    def dep(_d: None = Depends(hija)) -> dict[str, bool]:
        return {"ok": True}

    @app.get("/api/v1/repetida")
    def repetida(
        _primera: None = Depends(hija),
        _segunda: None = Depends(hija),
    ) -> dict[str, bool]:
        return {"ok": True}

    @app.get("/api/v1/alias")
    def alias(_d: None = Depends(con_alias)) -> dict[str, bool]:
        return {"ok": True}

    @app.get("/api/v1/vacia")
    def vacia() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/fuera/abierta")
    def fuera(x: str | None = None) -> dict[str, bool]:
        return {"ok": True}

    instalar_contrato_de_consulta(app, "/api/v1")
    return app


def test_arranque_con_runtime_lock() -> None:
    env = os.environ.copy()
    resultado = subprocess.run(
        [sys.executable, "-c", "import app.main"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        env=env,
    )
    assert resultado.returncode == 0, resultado.stderr


def test_parametro_directo_aceptado() -> None:
    with TestClient(_app()) as cliente:
        respuesta = cliente.get("/api/v1/raiz", params={"directa": "1"})
    assert respuesta.status_code == 200


def test_parametro_de_dependencia_aceptado() -> None:
    with TestClient(_app()) as cliente:
        respuesta = cliente.get("/api/v1/dep", params={"media": "1"})
    assert respuesta.status_code == 200


def test_parametro_anidado_aceptado() -> None:
    with TestClient(_app()) as cliente:
        respuesta = cliente.get("/api/v1/dep", params={"profunda": "1"})
    assert respuesta.status_code == 200


def test_alias_aceptado_y_nombre_interno_rechazado() -> None:
    with TestClient(_app()) as cliente:
        respuesta_alias = cliente.get("/api/v1/alias", params={"otro-nombre": "1"})
        respuesta_interna = cliente.get("/api/v1/alias", params={"valor": "1"})
    assert respuesta_alias.status_code == 200
    assert respuesta_interna.status_code == 422


def test_dependencia_repetida_y_conjunto_declarado() -> None:
    app = _app()
    ruta = next(
        r for r in app.routes if isinstance(r, APIRoute) and r.path == "/api/v1/repetida"
    )
    assert parametros_de_consulta_declarados(ruta) == frozenset({"media", "profunda"})
    with TestClient(app) as cliente:
        respuesta = cliente.get("/api/v1/repetida", params={"media": "1"})
    assert respuesta.status_code == 200


def test_ruta_sin_query_rechaza_cualquier_parametro() -> None:
    with TestClient(_app()) as cliente:
        respuesta_sin = cliente.get("/api/v1/vacia")
        respuesta_con = cliente.get("/api/v1/vacia", params={"x": "1"})
    assert respuesta_sin.status_code == 200
    assert respuesta_con.status_code == 422
    assert respuesta_con.json()["code"] == CODIGO


def test_multiple_desconocido_ordenado_en_details() -> None:
    with TestClient(_app()) as cliente:
        respuesta = cliente.get("/api/v1/vacia", params={"b": "1", "a": "2"})
    assert respuesta.status_code == 422
    cuerpo = respuesta.json()
    assert cuerpo["details"]["unknown_query_parameters"] == ["a", "b"]


def test_valor_desconocido_no_aparece_en_respuesta() -> None:
    with TestClient(_app(), raise_server_exceptions=False) as cliente:
        respuesta = cliente.get("/api/v1/vacia", params={"zz": "valor-secreto"})
    assert "valor-secreto" not in respuesta.text


def test_instalacion_idempotente() -> None:
    app = _app()
    instalar_contrato_de_consulta(app, "/api/v1")
    for ruta in app.routes:
        if not isinstance(ruta, APIRoute):
            continue
        if ruta.path == "/api/v1" or ruta.path.startswith("/api/v1/"):
            verificadores = [
                dep for dep in ruta.dependant.dependencies
                if isinstance(dep.call, VerificadorDeConsulta)
            ]
            assert len(verificadores) == 1


def test_fuera_del_prefijo_no_recibe_verificador() -> None:
    with TestClient(_app()) as cliente:
        respuesta = cliente.get("/fuera/abierta", params={"otro": "1"})
    assert respuesta.status_code == 200


def test_router_incluido_aplica_contrato() -> None:
    app = FastAPI()
    register_exception_handlers(app)

    router = APIRouter(prefix="/sub")

    def filtro(q: str | None = None) -> None:
        return None

    @router.get("/item", dependencies=[Depends(filtro)])
    def item() -> dict[str, str]:
        return {"ok": "item"}

    app.include_router(router, prefix="/api/v1")
    instalar_contrato_de_consulta(app, "/api/v1")

    with TestClient(app) as cliente:
        assert cliente.get("/api/v1/sub/item", params={"q": "1"}).status_code == 200

        respuesta = cliente.get("/api/v1/sub/item", params={"zz": "1"})
    assert respuesta.status_code == 422
    assert respuesta.json()["code"] == CODIGO

    instalar_contrato_de_consulta(app, "/api/v1")
    verificadores = []
    for contexto in iter_route_contexts(app.routes):
        if contexto.path == "/api/v1/sub/item":
            verificadores = [
                dependencia
                for dependencia in contexto.dependant.dependencies
                if isinstance(dependencia.call, VerificadorDeConsulta)
            ]
            break

    assert len(verificadores) == 1
    assert contexto.dependant.dependencies[-1] is verificadores[0]


def test_router_incluido_autoriza_antes_de_verificar() -> None:
    app = FastAPI()
    register_exception_handlers(app)

    router = APIRouter()

    def exige() -> None:
        raise HTTPException(status_code=401, detail="no autorizado")

    @router.get("/privada", dependencies=[Depends(exige)])
    def privada() -> dict[str, str]:
        return {"ok": "privada"}

    app.include_router(router, prefix="/api/v1")
    instalar_contrato_de_consulta(app, "/api/v1")

    with TestClient(app) as cliente:
        respuesta = cliente.get("/api/v1/privada", params={"zz": "1"})
    assert respuesta.status_code == 401


def test_app_real_aplica_contrato() -> None:
    from app.main import create_app

    cliente = TestClient(create_app())

    assert cliente.get("/api/v1/health/live").status_code == 200

    respuesta = cliente.get("/api/v1/health/live", params={"zz": "1"})
    assert respuesta.status_code == 422
    assert respuesta.json()["code"] == CODIGO
