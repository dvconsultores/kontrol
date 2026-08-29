"""Pruebas de contrato del motor de aprobaciones por API (Spec 045, F4/F7).

Verifican lo que las pruebas de servicio no pueden: permisos, códigos de error
del contrato, `allowed_actions` calculado en backend y aislamiento por empresa.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.database import Base, get_db, init_models
from app.modules.identity_access import service as identity_service
from app.modules.identity_access.models import Role, UserRole
from app.modules.licensing import service as licensing_service
from app.modules.organization.models import Company, Installation
from app.modules.setup.api import SetupRequest, initialize

_CLIENT: TestClient | None = None
_FACTORY = None
COMPANY_ID = ""


def _import_license(db: Session) -> None:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    key = Ed25519PrivateKey.generate()
    pub = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    inst = db.execute(select(Installation).limit(1)).scalars().first()
    now = datetime.now(UTC)
    payload = {
        "issuer": "K", "license_id": "LIC-SEC", "installation_id": inst.installation_uuid,
        "customer_id": "C1", "contract_id": "C1", "company_tax_id": "J-12345678-9",
        "period_start": (now - timedelta(days=30)).isoformat(),
        "period_end": (now + timedelta(days=120)).isoformat(),
        "critical_warning_start": (now + timedelta(days=180)).isoformat(),
        "read_only_start": (now + timedelta(days=200)).isoformat(),
        "entitlements": {"companies": 1, "users": 25, "modules": ["*"]},
        "minimum_version": "1.0.0", "kid": "kontrol-lic-2026-01",
    }
    sig = key.sign(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hex()
    os.environ["KONTROL_LICENSE_PUBLIC_KEY_PEM"] = pub
    get_settings.cache_clear()
    try:
        licensing_service.import_license(db, payload=payload, signature_hex=sig, source="MANUAL")
    finally:
        os.environ.pop("KONTROL_LICENSE_PUBLIC_KEY_PEM", None)
        get_settings.cache_clear()


@pytest.fixture(scope="module", autouse=True)
def _app_client():
    global _CLIENT, _FACTORY, COMPANY_ID
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True,
                           connect_args={"check_same_thread": False}, poolclass=StaticPool)
    init_models()
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    import app.core.database as dm

    dm._engine = engine  # type: ignore[attr-defined]
    dm._SessionLocal = factory  # type: ignore[attr-defined]

    db = factory()
    initialize(db, SetupRequest(
        tenant_code="DEMO", tenant_name="Empresa Demo", company_code="D1",
        company_legal_name="Demo C.A.", company_rif="J-12345678-9",
        admin_username="admin", admin_password="Kontrol2026Segura!"))
    _import_license(db)
    COMPANY_ID = str(db.execute(select(Company).limit(1)).scalars().first().id)

    # Aprobador sin permisos de configuración: sólo `aprobaciones:approve|view`
    admin_role = db.execute(select(Role).where(Role.code == "ADMIN")).scalars().first()
    approver = identity_service.create_user(
        db, tenant_id=admin_role.created_by or "t", username="aprobador",
        email="apr@demo.com", password="Kontrol2026Segura!", created_by=None)
    db.add(UserRole(user_id=str(approver.id), role_id=str(admin_role.id), company_id=None))
    db.commit()
    db.close()

    from app.main import create_app

    app = create_app()

    def _override_get_db():
        d = factory()
        try:
            yield d
        finally:
            d.close()

    app.dependency_overrides[get_db] = _override_get_db
    _FACTORY = factory
    _CLIENT = TestClient(app)
    yield _CLIENT


def _auth(username: str = "admin") -> dict:
    r = _CLIENT.post("/api/v1/auth/login",
                     json={"tenant_code": "DEMO", "username": username,
                           "password": "Kontrol2026Segura!"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _make_policy(h: dict, process_type: str, *, segregation: bool = False,
                 threshold: float = 1000.0) -> str:
    r = _CLIENT.post("/api/v1/approvals/policies", headers=h, json={
        "company_id": COMPANY_ID, "process_type": process_type,
        "code": "P", "name": "Política", "requires_segregation": segregation})
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    rr = _CLIENT.post(f"/api/v1/approvals/policies/{pid}/rules", headers=h, json={
        "name": "Sobre umbral",
        "conditions": [{"field": "amount_base", "operator": "gt", "value": threshold}],
        "condition_fields": ["amount_base", "amount", "currency"]})
    assert rr.status_code == 201, rr.text
    rl = _CLIENT.post(f"/api/v1/approvals/policies/{pid}/rules/{rr.json()['id']}/levels",
                      headers=h, json={"level_order": 1, "resolver_type": "ROLE",
                                       "resolver_ref": "ADMIN", "quorum_type": "ANY"})
    assert rl.status_code == 201, rl.text
    act = _CLIENT.post(f"/api/v1/approvals/policies/{pid}/activate", headers=h)
    assert act.status_code == 200, act.text
    return pid


def test_requires_authentication():
    r = _CLIENT.get(f"/api/v1/approvals/policies?company_id={COMPANY_ID}")
    assert r.status_code == 401


def test_policy_lifecycle_by_api():
    h = _auth()
    pid = _make_policy(h, "API_PROCESS_1")
    got = _CLIENT.get(f"/api/v1/approvals/policies/{pid}", headers=h)
    assert got.status_code == 200
    body = got.json()
    assert body["status"] == "ACTIVE"
    assert body["allowed_actions"] == ["close"]
    assert len(body["rules"]) == 1 and len(body["rules"][0]["levels"]) == 1


def test_active_policy_rejects_edition():
    h = _auth()
    pid = _make_policy(h, "API_PROCESS_2")
    r = _CLIENT.patch(f"/api/v1/approvals/policies/{pid}", headers=h, json={"name": "otro"})
    assert r.status_code == 409
    assert r.json()["code"] == "APPROVAL_POLICY_NOT_EDITABLE"


def test_evaluate_does_not_create_request():
    h = _auth()
    _make_policy(h, "API_PROCESS_3")
    r = _CLIENT.post("/api/v1/approvals/evaluate", headers=h, json={
        "company_id": COMPANY_ID, "process_type": "API_PROCESS_3",
        "context": {"amount": 5000, "currency": "VED"}})
    assert r.status_code == 200 and r.json()["requires_approval"] is True
    lst = _CLIENT.get(f"/api/v1/approvals/requests?company_id={COMPANY_ID}"
                      "&process_type=API_PROCESS_3", headers=h)
    assert lst.json()["items"] == []


def test_full_cycle_and_allowed_actions():
    h = _auth()
    _make_policy(h, "API_PROCESS_4")
    created = _CLIENT.post("/api/v1/approvals/requests", headers=h, json={
        "company_id": COMPANY_ID, "process_type": "API_PROCESS_4",
        "document_type": "Doc", "document_id": "d-4",
        "context": {"amount": 5000, "currency": "VED"}})
    assert created.status_code == 201, created.text
    assert created.json()["requires_approval"] is True

    # Idempotencia por API (FR-045-053)
    again = _CLIENT.post("/api/v1/approvals/requests", headers=h, json={
        "company_id": COMPANY_ID, "process_type": "API_PROCESS_4",
        "document_type": "Doc", "document_id": "d-4",
        "context": {"amount": 5000, "currency": "VED"}})
    assert again.json()["idempotent_hit"] is True
    assert again.json()["request_id"] == created.json()["request_id"]

    inbox = _CLIENT.get(f"/api/v1/approvals/inbox?company_id={COMPANY_ID}", headers=h)
    assert inbox.status_code == 200
    item = next(i for i in inbox.json()["items"] if i["document_id"] == "d-4")
    assert item["allowed_actions"] == ["approve", "reject", "return"]

    ok = _CLIENT.post(f"/api/v1/approvals/steps/{item['step_id']}/approve", headers=h,
                      json={"reason": None})
    assert ok.status_code == 200, ok.text
    assert ok.json()["status"] == "APPROVED"

    doc = _CLIENT.get(f"/api/v1/approvals/requests/by-document?company_id={COMPANY_ID}"
                      "&document_type=Doc&document_id=d-4", headers=h)
    assert doc.json()["is_approved"] is True and doc.json()["blocks_advance"] is False


def test_reason_required_returns_422():
    h = _auth()
    _make_policy(h, "API_PROCESS_5")
    _CLIENT.post("/api/v1/approvals/requests", headers=h, json={
        "company_id": COMPANY_ID, "process_type": "API_PROCESS_5",
        "document_type": "Doc", "document_id": "d-5",
        "context": {"amount": 5000, "currency": "VED"}})
    inbox = _CLIENT.get(f"/api/v1/approvals/inbox?company_id={COMPANY_ID}", headers=h)
    item = next(i for i in inbox.json()["items"] if i["document_id"] == "d-5")
    r = _CLIENT.post(f"/api/v1/approvals/steps/{item['step_id']}/reject", headers=h,
                     json={"reason": "  "})
    assert r.status_code == 422
    assert r.json()["code"] == "APPROVAL_REASON_REQUIRED"


def test_if_match_version_conflict_returns_409():
    h = _auth()
    _make_policy(h, "API_PROCESS_6")
    _CLIENT.post("/api/v1/approvals/requests", headers=h, json={
        "company_id": COMPANY_ID, "process_type": "API_PROCESS_6",
        "document_type": "Doc", "document_id": "d-6",
        "context": {"amount": 5000, "currency": "VED"}})
    inbox = _CLIENT.get(f"/api/v1/approvals/inbox?company_id={COMPANY_ID}", headers=h)
    item = next(i for i in inbox.json()["items"] if i["document_id"] == "d-6")
    r = _CLIENT.post(f"/api/v1/approvals/steps/{item['step_id']}/approve",
                     headers={**h, "If-Match": "999"}, json={"reason": None})
    assert r.status_code == 409
    assert r.json()["code"] == "APPROVAL_STEP_VERSION_CONFLICT"


def test_segregation_denied_by_api():
    h = _auth()
    _make_policy(h, "API_PROCESS_7", segregation=True)
    created = _CLIENT.post("/api/v1/approvals/requests", headers=h, json={
        "company_id": COMPANY_ID, "process_type": "API_PROCESS_7",
        "document_type": "Doc", "document_id": "d-7",
        "context": {"amount": 5000, "currency": "VED"}})
    assert created.status_code == 201
    rid = created.json()["request_id"]
    detail = _CLIENT.get(f"/api/v1/approvals/requests/{rid}", headers=h).json()
    # El creador no puede resolver: allowed_actions vacío (P6)
    assert detail["allowed_actions"] == []
    step_id = next(s["id"] for s in detail["steps"] if s["status"] == "IN_REVIEW")
    r = _CLIENT.post(f"/api/v1/approvals/steps/{step_id}/approve", headers=h, json={})
    assert r.status_code == 403
    assert r.json()["code"] == "APPROVAL_SEGREGATION_VIOLATION"


def test_delegation_lifecycle_by_api():
    h = _auth()
    r = _CLIENT.post("/api/v1/approvals/delegations", headers=h, json={
        "company_id": COMPANY_ID, "grantor_id": "u-1", "grantee_id": "u-2",
        "scope_process_type": "API_PROCESS_1", "reason": "vacaciones"})
    assert r.status_code == 201
    did = r.json()["id"]
    lst = _CLIENT.get(f"/api/v1/approvals/delegations?company_id={COMPANY_ID}", headers=h)
    assert any(d["id"] == did and d["status"] == "ACTIVE" for d in lst.json()["items"])
    rev = _CLIENT.post(f"/api/v1/approvals/delegations/{did}/revoke", headers=h)
    assert rev.status_code == 200 and rev.json()["status"] == "REVOKED"


def test_self_delegation_returns_422():
    h = _auth()
    r = _CLIENT.post("/api/v1/approvals/delegations", headers=h, json={
        "company_id": COMPANY_ID, "grantor_id": "u-9", "grantee_id": "u-9"})
    assert r.status_code == 422
    assert r.json()["code"] == "APPROVAL_DELEGATION_SELF"


def test_inbox_isolated_by_company():
    h = _auth()
    r = _CLIENT.get("/api/v1/approvals/inbox?company_id=otra-empresa", headers=h)
    assert r.status_code == 200 and r.json()["total"] == 0
