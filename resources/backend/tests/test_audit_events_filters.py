"""AF-01..11 · Muestreo y filtrado de la bitácora; proyección segura y filtros.

El alcance de lectura no se amplía: un auditor de empresa no ve eventos de
tenant ni de otras empresas (OD-AUD-01). El orden es estable por sellado e id.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from mfa_mundo import API, alta_por_desafio, crear_usuario, mundo_mfa

from app.modules.audit.models import AuditEvent
from app.modules.identity_access import service as identity_service
from app.modules.identity_access.models import UserRole
from app.modules.organization.models import Company

pytest_plugins = ("mfa_apoyo",)


@pytest.fixture(scope="module")
def mundo():
    with mundo_mfa() as m:
        yield m


@pytest.fixture(scope="module")
def escenario(mundo):
    db = mundo.factory()
    try:
        d2 = Company(
            tenant_id=mundo.tenant_id,
            code="AF-D2",
            legal_name="Audit Filters D2",
            rif="J-44444444-4",
            legal_type="JURIDICA",
            functional_currency="VED",
            status="ACTIVE",
        )
        db.add(d2)
        db.flush()

        roles = {}
        definiciones = {
            "R_AF_AUD": ["audit:view"],
            "R_AF_FIS": ["fiscal:create"],
        }
        for code, permissions in definiciones.items():
            roles[code] = identity_service.create_role(
                db,
                tenant_id=mundo.tenant_id,
                code=code,
                name=code,
                company_id=None,
                permissions=permissions,
                actor=mundo.admin_id,
            )["id"]

        db.commit()
        return SimpleNamespace(
            roles=roles,
            d1=mundo.company_id,
            d2=d2.id,
        )
    finally:
        db.close()


def _nombre():
    import uuid

    return f"af{uuid.uuid4().hex[:12]}"


def _dar(mundo, user_id, role_id, company_id):
    db = mundo.factory()
    try:
        db.add(
            UserRole(
                user_id=user_id,
                role_id=role_id,
                company_id=company_id,
            )
        )
        db.commit()
    finally:
        db.close()


def _actor(mundo, reloj, role_id, company_id):
    nombre = _nombre()
    user_id = crear_usuario(mundo, nombre)
    _dar(mundo, user_id, role_id, company_id)
    cabeceras = alta_por_desafio(mundo.client, reloj, nombre).cabeceras
    return user_id, cabeceras


def _evento(
    mundo,
    *,
    marca,
    user_id=None,
    company_id=None,
    event_time=None,
    action="DOCUMENT_CREATED",
    entity_type="Document",
    request_id=None,
    after=None,
    evidence=None,
):
    db = mundo.factory()
    try:
        evento = AuditEvent(
            action=action,
            entity_type=entity_type,
            entity_id=marca,
            tenant_id=mundo.tenant_id,
            company_id=company_id,
            user_id=user_id,
            request_id=request_id,
            source="QA",
            event_time=event_time or datetime.now(UTC),
            after=after,
            evidence=evidence,
        )
        db.add(evento)
        db.commit()
        db.refresh(evento)
        return evento
    finally:
        db.close()


def _listar(client, cabeceras, **params):
    r = client.get(f"{API}/audit/events", headers=cabeceras, params=params)
    return r


def test_af_01_bordes_del_dia_de_caracas(mundo, escenario, reloj_mfa):
    """AF-01: desde/hasta se interpretan como día civil de Caracas (ADR-020)."""
    marca = _nombre()
    e_0359 = _evento(
        mundo,
        marca=marca,
        company_id=escenario.d1,
        event_time=datetime(2026, 3, 10, 3, 59, 59, tzinfo=UTC),
    )
    e_0400 = _evento(
        mundo,
        marca=marca,
        company_id=escenario.d1,
        event_time=datetime(2026, 3, 10, 4, 0, 0, tzinfo=UTC),
    )

    _, cabeceras = _actor(mundo, reloj_mfa, escenario.roles["R_AF_AUD"], None)

    r = _listar(
        mundo.client,
        cabeceras,
        desde="2026-03-10",
        hasta="2026-03-10",
        entity_id=marca,
    )
    assert r.status_code == 200, r.text
    assert r.json()["total"] == 1
    assert [i["id"] for i in r.json()["items"]] == [str(e_0400.id)]

    r = _listar(
        mundo.client,
        cabeceras,
        hasta="2026-03-09",
        entity_id=marca,
    )
    assert r.status_code == 200, r.text
    assert r.json()["total"] == 1
    assert [i["id"] for i in r.json()["items"]] == [str(e_0359.id)]


def test_af_02_rango_de_fechas_invalido(mundo, escenario, reloj_mfa):
    """AF-02: desde posterior a hasta es 422 INVALID_DATE_RANGE."""
    _, cabeceras = _actor(mundo, reloj_mfa, escenario.roles["R_AF_AUD"], None)
    r = _listar(
        mundo.client,
        cabeceras,
        desde="2026-03-11",
        hasta="2026-03-10",
    )
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "INVALID_DATE_RANGE"


def test_af_03_filtro_por_usuario(mundo, escenario, reloj_mfa):
    """AF-03: username filtra por el id del usuario dentro del tenant."""
    _, cabeceras = _actor(mundo, reloj_mfa, escenario.roles["R_AF_AUD"], None)

    nombre = _nombre()
    user_id = crear_usuario(mundo, nombre)
    otro = crear_usuario(mundo, _nombre())
    marca = _nombre()
    evento_del_usuario = _evento(
        mundo, marca=marca, user_id=user_id, company_id=escenario.d1
    )
    _evento(mundo, marca=marca, user_id=otro, company_id=escenario.d1)

    r = _listar(mundo.client, cabeceras, username=nombre, entity_id=marca)
    assert r.status_code == 200, r.text
    ids = {i["id"] for i in r.json()["items"]}
    assert ids == {str(evento_del_usuario.id)}


def test_af_04_company_id_suma_al_alcance(mundo, escenario, reloj_mfa):
    """AF-04: company_id se suma a la condición de alcance; no revela existencia."""
    marca = _nombre()
    _evento(mundo, marca=marca, company_id=escenario.d2)

    _, cabeceras_d1 = _actor(mundo, reloj_mfa, escenario.roles["R_AF_AUD"], escenario.d1)
    r = _listar(mundo.client, cabeceras_d1, company_id=escenario.d2)
    assert r.status_code == 200, r.text
    assert r.json()["total"] == 0

    _, cabeceras_todo = _actor(mundo, reloj_mfa, escenario.roles["R_AF_AUD"], None)
    r = _listar(mundo.client, cabeceras_todo, company_id=escenario.d2, entity_id=marca)
    assert r.status_code == 200, r.text
    assert r.json()["total"] == 1


def test_af_05_scope_tenant_y_company(mundo, escenario, reloj_mfa):
    """AF-05: evento de tenant solo lo ve el auditor de todo el tenant (OD-AUD-01)."""
    marca = _nombre()
    _evento(mundo, marca=marca, company_id=None, action="USER_CREATED", entity_type="User")

    _, cabeceras_todo = _actor(mundo, reloj_mfa, escenario.roles["R_AF_AUD"], None)
    r = _listar(mundo.client, cabeceras_todo, scope="TENANT", entity_id=marca)
    assert r.status_code == 200, r.text
    assert r.json()["total"] == 1
    item = next(i for i in r.json()["items"] if i["entity_id"] == marca)
    assert item["scope"] == "TENANT"
    assert item["company_id"] is None

    _, cabeceras_d1 = _actor(mundo, reloj_mfa, escenario.roles["R_AF_AUD"], escenario.d1)
    r = _listar(mundo.client, cabeceras_d1, scope="TENANT", entity_id=marca)
    assert r.status_code == 200, r.text
    assert r.json()["total"] == 0

    r = _listar(mundo.client, cabeceras_todo, scope="COMPANY", entity_id=marca)
    assert r.status_code == 200, r.text
    assert r.json()["total"] == 0


def test_af_06_request_id(mundo, escenario, reloj_mfa):
    """AF-06: request_id filtra por correlación."""
    marca = _nombre()
    _evento(mundo, marca=marca, company_id=escenario.d1, request_id="af-06-unico")

    _, cabeceras = _actor(mundo, reloj_mfa, escenario.roles["R_AF_AUD"], None)
    r = _listar(mundo.client, cabeceras, request_id="af-06-unico", entity_id=marca)
    assert r.status_code == 200, r.text
    assert r.json()["total"] == 1


def test_af_07_proyeccion_segura_y_contexto(mundo, escenario, reloj_mfa):
    """AF-07: details seguros, company_name y etiqueta; sin campos crudos."""
    _, cabeceras = _actor(mundo, reloj_mfa, escenario.roles["R_AF_AUD"], None)

    marca = _nombre()
    _evento(
        mundo,
        marca=marca,
        company_id=escenario.d1,
        action="DOCUMENT_CREATED",
        entity_type="Document",
        after={"title": "x", "otra": 1},
        evidence={"title": {"token": "s"}},
    )
    r = _listar(mundo.client, cabeceras, entity_id=marca)
    assert r.status_code == 200, r.text
    assert r.json()["total"] == 1
    item = r.json()["items"][0]
    assert item["details"] == {
        "after": {"title": "x"},
        "evidence": {"title": {}},
    }
    assert item["company_name"] is not None
    assert item["action_label"] != "DOCUMENT_CREATED"
    assert item["scope"] == "COMPANY"
    for clave in ("ip", "session_id", "before", "after", "evidence"):
        assert clave not in item

    marca_hist = _nombre()
    _evento(
        mundo,
        marca=marca_hist,
        company_id=escenario.d1,
        action="ACCION_HISTORICA_X",
        entity_type="Antigua",
    )
    r = _listar(mundo.client, cabeceras, entity_id=marca_hist)
    assert r.status_code == 200, r.text
    item = r.json()["items"][0]
    assert item["scope"] == "UNCATALOGUED"
    assert item["details"] == {}
    assert item["action_label"] == "ACCION_HISTORICA_X"


def test_af_08_evento_historico_sin_empresa(mundo, escenario, reloj_mfa):
    """AF-08: evento COMPANY sin empresa: no lo ve D1; sí el auditor de todo el tenant."""
    marca = _nombre()
    _evento(mundo, marca=marca, company_id=None)

    _, cabeceras_d1 = _actor(mundo, reloj_mfa, escenario.roles["R_AF_AUD"], escenario.d1)
    r = _listar(mundo.client, cabeceras_d1, entity_id=marca)
    assert r.status_code == 200, r.text
    assert r.json()["total"] == 0

    _, cabeceras_todo = _actor(mundo, reloj_mfa, escenario.roles["R_AF_AUD"], None)
    r = _listar(mundo.client, cabeceras_todo, entity_id=marca)
    assert r.status_code == 200, r.text
    assert r.json()["total"] == 1
    item = r.json()["items"][0]
    assert item["scope"] == "COMPANY"
    assert item["company_id"] is None


def test_af_09_orden_estable_por_id_descendente(mundo, escenario, reloj_mfa):
    """AF-09: el desempate entre sellos iguales es por id descendente."""
    _, cabeceras = _actor(mundo, reloj_mfa, escenario.roles["R_AF_AUD"], None)

    marca = _nombre()
    sello = datetime(2026, 3, 11, 12, 0, 0, tzinfo=UTC)
    e1 = _evento(mundo, marca=marca, company_id=escenario.d1, event_time=sello)
    e2 = _evento(mundo, marca=marca, company_id=escenario.d1, event_time=sello)

    r = _listar(mundo.client, cabeceras, entity_id=marca)
    assert r.status_code == 200, r.text
    ids = [item["id"] for item in r.json()["items"]]
    assert ids == sorted([str(e1.id), str(e2.id)], reverse=True)


def test_af_10_filters(mundo, escenario, reloj_mfa):
    """AF-10: /audit/filters refleja el alcance y catálogo público."""
    _, cabeceras_d1 = _actor(mundo, reloj_mfa, escenario.roles["R_AF_AUD"], escenario.d1)
    r = mundo.client.get(f"{API}/audit/filters", headers=cabeceras_d1)
    assert r.status_code == 200, r.text
    payload = r.json()
    assert payload["tenant_wide"] is False
    assert [c["id"] for c in payload["companies"]] == [str(escenario.d1)]

    _, cabeceras_todo = _actor(mundo, reloj_mfa, escenario.roles["R_AF_AUD"], None)
    r = mundo.client.get(f"{API}/audit/filters", headers=cabeceras_todo)
    assert r.status_code == 200, r.text
    payload = r.json()
    assert payload["tenant_wide"] is True
    assert {c["id"] for c in payload["companies"]} == {str(escenario.d1), str(escenario.d2)}

    acciones = payload["actions"]
    for accion in acciones:
        assert set(accion) == {"code", "entity_type", "label", "scope", "lifecycle"}
    assert any(
        accion["code"] == "DOCUMENT_SCAN_REJECTED"
        and accion["entity_type"] == "Document"
        for accion in acciones
    )
    assert payload["catalog_version"] != ""


def test_af_11_validacion_y_permisos(mundo, escenario, reloj_mfa):
    """AF-11: page_size 101 es 422; sin audit:view es 403 en events y filters."""
    _, cabeceras = _actor(mundo, reloj_mfa, escenario.roles["R_AF_AUD"], None)
    r = _listar(mundo.client, cabeceras, page_size=101)
    assert r.status_code == 422, r.text

    _, cabeceras_fis = _actor(mundo, reloj_mfa, escenario.roles["R_AF_FIS"], escenario.d1)
    r = mundo.client.get(f"{API}/audit/events", headers=cabeceras_fis)
    assert r.status_code == 403, r.text
    r = mundo.client.get(f"{API}/audit/filters", headers=cabeceras_fis)
    assert r.status_code == 403, r.text
