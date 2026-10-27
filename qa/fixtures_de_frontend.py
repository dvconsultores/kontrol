"""Regenera las instantáneas del frontend a partir de la aplicación real.

Uso (desde la raíz del repositorio):

    PYTHONPATH=resources/backend resources/backend/.venv/bin/python qa/fixtures_de_frontend.py

No toca la base: construye la aplicación y lee sus rutas.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("KONTROL_ENVIRONMENT", "local")
os.environ.setdefault("KONTROL_LOG_JSON", "false")
os.environ.setdefault("KONTROL_SECRET_KEY", "0" * 64)
os.environ.setdefault("KONTROL_DB_URL", "sqlite+pysqlite:///:memory:")

from fastapi.routing import APIRoute  # noqa: E402

from app.core.operaciones import catalogo_de_operaciones  # noqa: E402
from app.main import create_app  # noqa: E402
from app.modules.setup.api import CATALOGO_DE_PERMISOS  # noqa: E402

RAIZ_REPOSITORIO = Path(__file__).resolve().parents[1]
DIRECTORIO_FIXTURES = (
    RAIZ_REPOSITORIO / "resources" / "frontend" / "src" / "tests" / "fixtures"
)
PREFIJO_API = "/api/v1"


def _rutas_openapi(app) -> dict[str, list[dict[str, str]]]:
    rutas: list[dict[str, str]] = []
    for ruta in app.routes:
        if not isinstance(ruta, APIRoute):
            continue
        metodos = getattr(ruta, "methods", None) or set()
        for metodo in metodos:
            if metodo in {"HEAD", "OPTIONS"}:
                continue
            camino = ruta.path
            if camino == PREFIJO_API:
                camino = "/"
            elif camino.startswith(PREFIJO_API + "/"):
                camino = camino[len(PREFIJO_API):]
            rutas.append({"method": metodo, "path": camino})
    rutas.sort(key=lambda item: (item["path"], item["method"]))
    return {"routes": rutas}


def _operaciones(app) -> dict[str, list]:
    return {
        "operations": list(catalogo_de_operaciones(app)),
        "permissions": [
            f"{recurso}:{accion}"
            for recurso, acciones in CATALOGO_DE_PERMISOS.items()
            for accion in acciones
        ],
    }


def instantaneas(app) -> dict[str, dict]:
    """Devuelve las instantáneas (nombre de fichero → datos) para ``app``."""
    return {
        "openapi-routes.json": _rutas_openapi(app),
        "operaciones.json": _operaciones(app),
    }


def _escribir(datos: dict[str, dict]) -> None:
    DIRECTORIO_FIXTURES.mkdir(parents=True, exist_ok=True)
    for nombre, contenido in datos.items():
        destino = DIRECTORIO_FIXTURES / nombre
        destino.write_text(
            json.dumps(contenido, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )


def main() -> None:
    app = create_app()
    _escribir(instantaneas(app))


if __name__ == "__main__":
    main()
