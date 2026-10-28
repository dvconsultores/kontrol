"""C05-T11: Búsqueda asíncrona de taxonomía para AsyncCombobox (PDD-API-12)."""

import uuid
from types import SimpleNamespace

import pytest
from mfa_mundo import API, alta_por_desafio, crear_usuario, login, mundo_mfa

from app.modules.identity_access import service as identity_service
from app.modules.identity_access.models import UserRole
from app.modules.master_data.models import TaxonomyNode
from app.modules.organization.models import Company

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
def escenario(mundo):
    s = uuid.uuid4().hex[:8]
    db = mundo.factory()
    try:
        nodo_a = TaxonomyNode(
            company_id=mundo.company_id,
            code=f"TXS-A-{s}",
            name=f"Ferretería {s}",
            level="RUBRO",
            applies_to=["PRODUCT"],
            status="ACTIVE",
        )
        nodo_b = TaxonomyNode(
            company_id=mundo.company_id,
            code=f"TXS-B-{s}",
            name=f"Pinturas {s}",
            level="RUBRO",
            applies_to=["PRODUCT"],
            status="ACTIVE",
        )
        nodo_i = TaxonomyNode(
            company_id=mundo.company_id,
            code=f"TXS-I-{s}",
            name=f"Ferretería inactiva {s}",
            level="RUBRO",
            applies_to=["PRODUCT"],
            status="INACTIVE",
        )
        db.add_all([nodo_a, nodo_b, nodo_i])
        db.flush()

        company = Company(
            tenant_id=mundo.tenant_id,
            code=f"D2-{uuid.uuid4().hex[:12]}",
            legal_name=f"Empresa D2 {s}",
            rif="J-66666666-6",
            legal_type="JURIDICA",
            functional_currency="VED",
            status="ACTIVE",
        )
        db.add(company)
        db.flush()

        nodo_c = TaxonomyNode(
            company_id=company.id,
            code=f"TXS-C-{s}",
            name=f"Ferretería {s}",
            level="RUBRO",
            applies_to=["PRODUCT"],
            status="ACTIVE",
        )
        db.add(nodo_c)
        db.flush()

        role = identity_service.create_role(
            db,
            tenant_id=mundo.tenant_id,
            code=f"TXS-ROLE-{s}",
            name=f"TXS Role {s}",
            company_id=None,
            permissions=["maestros:view"],
            actor=mundo.admin_id,
        )
        db.commit()

        return SimpleNamespace(
            s=s,
            a_id=str(nodo_a.id),
            a_code=nodo_a.code,
            a_name=nodo_a.name,
            a_level=nodo_a.level,
            b_id=str(nodo_b.id),
            b_code=nodo_b.code,
            b_name=nodo_b.name,
            role_id=role["id"],
        )
    finally:
        db.close()


def _actor(mundo, reloj, role_id):
    nombre = f"txs{uuid.uuid4().hex[:12]}"
    user_id = crear_usuario(mundo, nombre)
    _dar(mundo, user_id, role_id, mundo.company_id)
    cabeceras = _entrar(mundo, reloj, nombre)
    cabeceras["X-Kontrol-Company"] = str(mundo.company_id)
    return cabeceras


def test_t01_busqueda_por_nombre_encuentra_solo_nodo_activo(mundo, escenario, reloj_mfa):
    """T-01: q=nombre encuentra solo el nodo activo de la empresa actual."""
    cabeceras = _actor(mundo, reloj_mfa, escenario.role_id)
    r = mundo.client.get(
        f"{API}/maestros/catalogos/taxonomia/search",
        params={"q": f"ferretería {escenario.s}"},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 1, body
    assert body["items"][0]["id"] == escenario.a_id, body
    assert body["items"][0]["code"] == escenario.a_code, body
    assert body["items"][0]["name"] == escenario.a_name, body
    assert body["items"][0]["level"] == escenario.a_level, body


def test_t02_busqueda_por_code_encuentra_nodo_b(mundo, escenario, reloj_mfa):
    """T-02: q=code encuentra el nodo B."""
    cabeceras = _actor(mundo, reloj_mfa, escenario.role_id)
    r = mundo.client.get(
        f"{API}/maestros/catalogos/taxonomia/search",
        params={"q": f"txs-b-{escenario.s}"},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 1, body
    assert body["items"][0]["id"] == escenario.b_id, body
    assert body["items"][0]["name"] == escenario.b_name, body
    assert body["items"][0]["code"] == escenario.b_code, body


def test_t03_busqueda_por_s_ordenada_por_nombre(mundo, escenario, reloj_mfa):
    """T-03: q=s devuelve A y B ordenados por nombre."""
    cabeceras = _actor(mundo, reloj_mfa, escenario.role_id)
    r = mundo.client.get(
        f"{API}/maestros/catalogos/taxonomia/search",
        params={"q": escenario.s},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 2, body
    ids = [item["id"] for item in body["items"]]
    assert set(ids) == {escenario.a_id, escenario.b_id}, body
    assert ids == [escenario.a_id, escenario.b_id], body


def test_t04_paginacion_pagina_dos(mundo, escenario, reloj_mfa):
    """T-04: página 2 devuelve solo el nodo B."""
    cabeceras = _actor(mundo, reloj_mfa, escenario.role_id)
    r = mundo.client.get(
        f"{API}/maestros/catalogos/taxonomia/search",
        params={"q": escenario.s, "page_size": 1, "page": 2},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 2, body
    assert len(body["items"]) == 1, body
    assert body["items"][0]["id"] == escenario.b_id, body


def test_t05_sobre_respuesta_exacto(mundo, escenario, reloj_mfa):
    """T-05: el sobre de respuesta contiene exactamente las claves esperadas."""
    cabeceras = _actor(mundo, reloj_mfa, escenario.role_id)
    r = mundo.client.get(
        f"{API}/maestros/catalogos/taxonomia/search",
        params={"q": escenario.s},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body.keys()) == {"items", "total", "page", "page_size"}, body


def test_t06_listado_original_sigue_siendo_lista(mundo, escenario, reloj_mfa):
    """T-06: el listado original sigue devolviendo una lista."""
    cabeceras = _actor(mundo, reloj_mfa, escenario.role_id)
    r = mundo.client.get(
        f"{API}/maestros/catalogos/taxonomia",
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text
    assert isinstance(r.json(), list), r.text


def test_t07_query_parametro_desconocido_devuelve_422(mundo, escenario, reloj_mfa):
    """T-07: un query parameter desconocido produce 422 UNKNOWN_QUERY_PARAMETER."""
    cabeceras = _actor(mundo, reloj_mfa, escenario.role_id)
    r = mundo.client.get(
        f"{API}/maestros/catalogos/taxonomia/search",
        params={"zz": 1},
        headers=cabeceras,
    )
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "UNKNOWN_QUERY_PARAMETER", r.text
