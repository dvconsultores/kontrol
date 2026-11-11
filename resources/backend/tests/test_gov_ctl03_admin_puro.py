import os
import pathlib
import re
from uuid import uuid4

import pytest
from fastapi.routing import APIRoute

from app.modules.identity_access.authority import TECHNICAL_CAPABILITIES
from tests.test_delegation_ceiling import (
    _actor,
    _asignar,
    _filas,
    _id_rol,
    _negaciones,
    _nombre,
)

pytestmark = pytest.mark.skipif(
    not os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql"),
    reason="Requiere PostgreSQL",
)

pytest_plugins = ("mfa_apoyo",)

from mfa_mundo import API, mundo_mfa  # noqa: E402


@pytest.fixture(scope="module")
def mundo():
    with mundo_mfa() as m:
        yield m


def _crear_rol(mundo, code: str, permissions: list[str], headers: dict):
    return mundo.client.post(
        f"{API}/roles",
        json={
            "code": code,
            "name": code,
            "permissions": permissions,
            "company_id": None,
        },
        headers=headers,
    )


def _crear_usuario(mundo, username: str, headers: dict):
    return mundo.client.post(
        f"{API}/users",
        json={
            "username": username,
            "email": None,
            "password": "Kontrol!Prueba-2026",
            "must_change_password": False,
        },
        headers=headers,
    )


def test_ap01_admin_puro_no_se_autoescala(mundo, reloj_mfa):
    """AP-01 ADMIN puro se asigna FUNCIONAL_COMPLETO y es denegado."""
    actor_id, cab = _actor(mundo, reloj_mfa, admin=True)
    antes = len(_negaciones(mundo, actor_id))
    resp = _asignar(mundo, cab, actor_id, _id_rol(mundo, "FUNCIONAL_COMPLETO"))
    assert resp.status_code == 403
    assert resp.json().get("code") == "SELF_ESCALATION_FORBIDDEN"
    assert _filas(mundo, actor_id, _id_rol(mundo, "FUNCIONAL_COMPLETO")) == 0
    nuevas = _negaciones(mundo, actor_id)[antes:]
    assert len(nuevas) == 1
    evidence = nuevas[0].evidence or {}
    assert evidence.get("capabilities_excedidas")
    assert not (set(evidence.get("capabilities_excedidas", [])) & TECHNICAL_CAPABILITIES)


def test_ap02_rol_sombra_denegado(mundo, reloj_mfa):
    """AP-02 Rol sombra con permiso de gobierno es denegado."""
    actor_id, cab = _actor(mundo, reloj_mfa, admin=True)
    code = f"ROOT{_nombre()}"
    resp = _crear_rol(mundo, code, ["gobierno_decision:decide"], cab)
    assert resp.status_code == 403
    assert resp.json().get("code") == "AUTHORITY_CEILING_EXCEEDED"
    db = mundo.factory()
    try:
        from app.modules.identity_access.models import Role

        assert db.query(Role).filter(Role.code == code).count() == 0
    finally:
        db.close()


def test_ap03_tarea_tecnica_legitima(mundo, reloj_mfa):
    """AP-03 ADMIN puro crea rol tecnico y usuario."""
    actor_id, cab = _actor(mundo, reloj_mfa, admin=True)
    code = f"ADMIN2{_nombre()}"
    resp = _crear_rol(mundo, code, ["users:view", "roles:view"], cab)
    assert resp.status_code == 201
    username = f"user_{uuid4().hex[:6]}"
    resp = _crear_usuario(mundo, username, cab)
    assert resp.status_code < 300


def test_ap04_gobierno_y_aprobaciones_denegados(mundo, reloj_mfa):
    """AP-04 ADMIN puro no accede a gobierno ni aprobaciones."""
    actor_id, cab = _actor(mundo, reloj_mfa, admin=True)
    for ruta in [
        f"{API}/gobierno/actos",
        f"{API}/gobierno/identidad/politica",
        f"{API}/gobierno/identidad/vinculos",
        f"{API}/approvals/policies",
    ]:
        resp = mundo.client.post(ruta, json={}, headers=cab)
        assert resp.status_code == 403, ruta


def _permisos_de_dependencia(dep) -> set[str]:
    permisos: set[str] = set()
    permiso = getattr(dep.call, "kontrol_permission", None)
    if permiso:
        permisos.add(permiso)
    for sub in getattr(dep, "dependencies", []) or []:
        permisos |= _permisos_de_dependencia(sub)
    return permisos


def test_ap05_invariante_de_rutas():
    """AP-05 Las rutas de gobierno/aprobaciones no usan permisos tecnicos."""
    from app.main import create_app

    app = create_app()
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if not route.path.startswith(("/api/v1/gobierno", "/api/v1/approvals")):
            continue
        metodos = route.methods or set()
        if not (metodos & {"POST", "PUT", "PATCH", "DELETE"}):
            continue
        permisos: set[str] = set()
        for dep in route.dependant.dependencies:
            permisos |= _permisos_de_dependencia(dep)
        assert permisos, f"Sin permisos: {route.path}"
        tecnicos = permisos & TECHNICAL_CAPABILITIES
        assert not tecnicos, f"Permisos tecnicos en {route.path}: {tecnicos}"


def test_ap06_migraciones_sin_concesion_admin():
    """AP-06 Ninguna migracion posterior a 60 concede el rol ADMIN."""
    versions = pathlib.Path(__file__).resolve().parents[1] / "alembic" / "versions"
    for fichero in versions.glob("*.py"):
        try:
            prefijo = int(fichero.name[:4])
        except ValueError:
            continue
        if prefijo <= 60:
            continue
        texto = fichero.read_text(encoding="utf-8")
        assert re.search(r"code\s*=\s*'ADMIN'", texto) is None, fichero.name
