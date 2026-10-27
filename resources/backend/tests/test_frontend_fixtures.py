"""La UI proyecta la autoridad del backend (Spec 003, ADR-018); estas instantáneas le dan a sus pruebas la verdad del backend, y esta prueba impide que deriven."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_QA = Path(__file__).resolve().parents[3] / "qa"
if str(_QA) not in sys.path:
    sys.path.insert(0, str(_QA))

from fixtures_de_frontend import (  # noqa: E402
    DIRECTORIO_FIXTURES,
    instantaneas,
)

from app.main import create_app  # noqa: E402

_MENSAJE = (
    "instantánea desactualizada: regenere con `qa/fixtures_de_frontend.py`, "
    "ejecutado con el intérprete del backend y `PYTHONPATH=resources/backend`"
)


@pytest.mark.parametrize("nombre", ["openapi-routes.json", "operaciones.json"])
def test_instantanea_coincide_con_backend(nombre: str) -> None:
    app = create_app()
    esperado = instantaneas(app)[nombre]
    guardado = json.loads((DIRECTORIO_FIXTURES / nombre).read_text(encoding="utf-8"))
    assert guardado == esperado, _MENSAJE
