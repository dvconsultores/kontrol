from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from mfa_mundo import API, alta_por_desafio, crear_usuario, mundo_mfa

from app.core.errors import PermissionDeniedError
from app.modules.approvals import service as approvals_service
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
            code="CSS-D2",
            legal_name="Company Scope Surface D2",
            rif="J-33333333-3",
            legal_type="JURIDICA",
            functional_currency="VED",
            status="ACTIVE",
        )
        db.add(d2)
        db.flush()

        roles = {}
        definiciones = {
            "R_CSS_AUD": ["audit:view"],
            "R_CSS_FIS": ["fiscal:create"],
            "R_CSS_ORG": ["organization:create"],
            "R_CSS_APR": ["aprobaciones:view", "aprobaciones:approve"],
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

    return f"css{uuid.uuid4().hex[:12]}"


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


def _audit_events(mundo, escenario, marca):
    # Filas insertadas directamente: la prueba es de lectura sobre historia simulada;
    # `record_audit` solo admite pares del catálogo cerrado (OD-AUD-04).
    db = mundo.factory()
    try:
        db.add(
            AuditEvent(
                action="qa.css.created",
                entity_type="QA_CSS",
                entity_id=f"{marca}-d1",
                tenant_id=mundo.tenant_id,
                company_id=escenario.d1,
                user_id=mundo.admin_id,
                event_time=datetime.now(UTC),
            )
        )
        db.add(
            AuditEvent(
                action="qa.css.created",
                entity_type="QA_CSS",
                entity_id=f"{marca}-d2",
                tenant_id=mundo.tenant_id,
                company_id=escenario.d2,
                user_id=mundo.admin_id,
                event_time=datetime.now(UTC),
            )
        )
        db.add(
            AuditEvent(
                action="qa.css.created",
                entity_type="QA_CSS",
                entity_id=f"{marca}-t",
                tenant_id=mundo.tenant_id,
                company_id=None,
                user_id=mundo.admin_id,
                event_time=datetime.now(UTC),
            )
        )
        db.commit()
    finally:
        db.close()


def test_css_a01_auditoria_solo_empresa_d1(mundo, escenario, reloj_mfa):
    """CSS-A01: auditor con alcance D1 solo ve eventos de D1."""
    marca = _nombre()
    _audit_events(mundo, escenario, marca)

    _, cabeceras = _actor(mundo, reloj_mfa, escenario.roles["R_CSS_AUD"], escenario.d1)

    r = mundo.client.get(
        f"{API}/audit/events",
        params={"entity_type": "QA_CSS"},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text
    payload = r.json()
    items = payload["items"]
    marca_items = [item for item in items if item.get("entity_id") == f"{marca}-d1"]
    assert len(marca_items) == 1, r.text
    assert all(
        item.get("entity_id") != f"{marca}-d2" and item.get("entity_id") != f"{marca}-t"
        for item in items
    ), r.text
    assert payload["total"] == len(items), r.text


def test_css_a02_auditoria_todo_tenant_ve_tres(mundo, escenario, reloj_mfa):
    """CSS-A02: auditor de todo el tenant ve D1, D2 y evento sin empresa."""
    marca = _nombre()
    _audit_events(mundo, escenario, marca)

    _, cabeceras = _actor(mundo, reloj_mfa, escenario.roles["R_CSS_AUD"], None)

    r = mundo.client.get(
        f"{API}/audit/events",
        params={"entity_type": "QA_CSS", "page_size": 100},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text
    payload = r.json()
    ids = {item.get("entity_id") for item in payload["items"]}
    assert {f"{marca}-d1", f"{marca}-d2", f"{marca}-t"} <= ids, r.text
    assert payload["total"] == len(payload["items"]), r.text


def test_css_t01_legal_sources_exige_todo_tenant(mundo, escenario, reloj_mfa):
    """CSS-T01: fiscal:create en D1 no permite legal-sources; en todo el tenant sí."""
    payload = {"authority": "SENIAT", "source_type": "PROVIDENCIA"}

    _, cabeceras_d1 = _actor(mundo, reloj_mfa, escenario.roles["R_CSS_FIS"], escenario.d1)
    r_d1 = mundo.client.post(
        f"{API}/fiscal/legal-sources",
        json=payload,
        headers=cabeceras_d1,
    )
    assert r_d1.status_code == 403, r_d1.text
    assert r_d1.json().get("code") == "COMPANY_SCOPE_FORBIDDEN", r_d1.text

    _, cabeceras_todo = _actor(mundo, reloj_mfa, escenario.roles["R_CSS_FIS"], None)
    r_todo = mundo.client.post(
        f"{API}/fiscal/legal-sources",
        json=payload,
        headers=cabeceras_todo,
    )
    assert r_todo.status_code != 403, r_todo.text


def test_css_t02_organizacion_companies_exige_todo_tenant(mundo, escenario, reloj_mfa):
    """CSS-T02: organization:create en D1 no permite companies; en todo el tenant sí."""
    codigo = f"CSS-{_nombre().upper()}"

    payload = {"code": codigo, "legal_name": "Company Scope Test", "rif": "J-22222222-2"}

    _, cabeceras_d1 = _actor(mundo, reloj_mfa, escenario.roles["R_CSS_ORG"], escenario.d1)
    r_d1 = mundo.client.post(
        f"{API}/organization/companies",
        json=payload,
        headers=cabeceras_d1,
    )
    assert r_d1.status_code == 403, r_d1.text
    assert r_d1.json().get("code") == "COMPANY_SCOPE_FORBIDDEN", r_d1.text

    _, cabeceras_todo = _actor(mundo, reloj_mfa, escenario.roles["R_CSS_ORG"], None)
    r_todo = mundo.client.post(
        f"{API}/organization/companies",
        json=payload,
        headers=cabeceras_todo,
    )
    assert r_todo.status_code != 403, r_todo.text


def test_css_p01_resolve_actors_por_empresa(mundo, escenario):
    """CSS-P01: resolve_actors solo incluye asignaciones nulas o de la empresa pedida."""
    u1 = crear_usuario(mundo, _nombre())
    u2 = crear_usuario(mundo, _nombre())
    _dar(mundo, u1, escenario.roles["R_CSS_APR"], escenario.d1)
    _dar(mundo, u2, escenario.roles["R_CSS_APR"], None)

    policy = SimpleNamespace(
        requires_segregation=False,
        allow_self_approval=True,
        distinct_actors_across_levels=False,
    )

    db = mundo.factory()
    try:
        resultado_d2 = approvals_service.resolve_actors(
            db,
            company_id=escenario.d2,
            level={"resolver_type": "ROLE", "resolver_ref": "R_CSS_APR"},
            policy=policy,
            requested_by=None,
            used_actors=None,
        )
        assert u2 in resultado_d2, resultado_d2
        assert u1 not in resultado_d2, resultado_d2

        resultado_d1 = approvals_service.resolve_actors(
            db,
            company_id=escenario.d1,
            level={"resolver_type": "ROLE", "resolver_ref": "R_CSS_APR"},
            policy=policy,
            requested_by=None,
            used_actors=None,
        )
        assert u1 in resultado_d1, resultado_d1
        assert u2 in resultado_d1, resultado_d1
    finally:
        db.close()


def test_css_p02_assert_can_decide_por_empresa(mundo, escenario):
    """CSS-P02: _assert_can_decide solo permite decidir en empresas donde el actor puede aprobar."""
    u1 = crear_usuario(mundo, _nombre())
    _dar(mundo, u1, escenario.roles["R_CSS_APR"], escenario.d1)

    request_d2 = SimpleNamespace(
        status="IN_REVIEW",
        policy_snapshot={},
        requested_by=None,
        company_id=escenario.d2,
        process_type="QA",
    )
    step = SimpleNamespace(
        id=_nombre(),
        status="IN_REVIEW",
        eligible_actors=[u1],
    )

    db = mundo.factory()
    try:
        with pytest.raises(PermissionDeniedError) as excinfo:
            approvals_service._assert_can_decide(
                db,
                request=request_d2,
                step=step,
                actor_id=u1,
            )
        assert excinfo.value.code == "COMPANY_SCOPE_FORBIDDEN"

        request_d1 = SimpleNamespace(
            status="IN_REVIEW",
            policy_snapshot={},
            requested_by=None,
            company_id=escenario.d1,
            process_type="QA",
        )
        assert (
            approvals_service._assert_can_decide(
                db,
                request=request_d1,
                step=step,
                actor_id=u1,
            )
            is None
        )
    finally:
        db.close()
