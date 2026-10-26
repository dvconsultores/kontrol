"""E2E de procesos críticos por API (T-10 de la auditoría 012).

Recorre cadenas completas (no pantallas aisladas):
  1. Organización: setup → login → empresa → sucursal → establecimiento → almacén → ubicación.
  2. Seguridad: roles → crear usuario → asignar rol → verificar → quitar.
  3. Licencia: modo READ_ONLY bloquea escrituras de negocio (423).

Usa SQLite en memoria con StaticPool (el middleware de licencia abre su propia
sesión) y una licencia firmada FULL_ACCESS.
"""
from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sesion_mfa import login_completo
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.database import Base, get_db, init_models
from app.modules.licensing import service as licensing_service
from app.modules.licensing.models import LicenseState
from app.modules.organization.models import Installation
from app.modules.setup.api import SetupRequest, initialize

_ENGINE = None
_FACTORY = None
_APP = None
_CLIENT = None


def _import_license(db: Session) -> str:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    key = Ed25519PrivateKey.generate()
    pub = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    inst = db.execute(select(Installation).limit(1)).scalars().first()
    now = datetime.now(UTC)
    period_end = (now + timedelta(days=120)).isoformat()
    critical = (now + timedelta(days=180)).isoformat()
    read_only = (now + timedelta(days=200)).isoformat()
    payload = {
        "issuer": "K", "license_id": "LIC-E2E", "installation_id": inst.installation_uuid,
        "customer_id": "C1", "contract_id": "C1", "company_tax_id": "J-12345678-9",
        "period_start": (now - timedelta(days=30)).isoformat(),
        "period_end": period_end,
        "critical_warning_start": critical, "read_only_start": read_only,
        "entitlements": {"companies": 1, "users": 25, "modules": ["*"]},
        "minimum_version": "1.0.0", "kid": "kontrol-lic-2026-01",
    }
    sig = key.sign(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hex()
    os.environ["KONTROL_LICENSE_PUBLIC_KEY_PEM"] = pub
    get_settings.cache_clear()
    try:
        st = licensing_service.import_license(db, payload=payload, signature_hex=sig, source="MANUAL")
        return st.mode
    finally:
        # El ancla se queda configurada: el vigente se reverifica contra ella en cada lectura y escritura (LICENCIA-ESTADO-SIN-REVERIFICAR).
        get_settings.cache_clear()


def _activate_full_access(db: Session) -> None:
    _import_license(db)


def _simular_licencia_vencida(db: Session) -> str:
    """El tiempo pasa sobre la licencia vigente: su período queda atrás y el 1 de mayo ya ocurrió.

    Antes se simulaba importando otra licencia con fechas pasadas; desde la Fase A de
    LICENCIA-DOWNGRADE-FIRMADO un período anterior o incoherente no sustituye al vigente, así que
    la expiración se simula como ocurre de verdad: con las fechas del estado, coherentes entre sí.
    """
    estado = db.execute(select(LicenseState)).scalars().one()
    now = datetime.now(UTC)
    estado.period_start = now - timedelta(days=400)
    estado.period_end = now - timedelta(days=1)
    estado.critical_warning_start = now - timedelta(days=3)
    estado.read_only_start = now - timedelta(days=2)
    db.commit()
    return licensing_service.current_mode(db)


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
    _activate_full_access(db)
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


def _auth_headers() -> dict:
    r = login_completo(_CLIENT, "/api/v1/auth/login", json={
        "tenant_code": "DEMO", "username": "admin", "password": "Kontrol2026Segura!",
    })
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_org_chain_complete():
    H = _auth_headers()
    companies = _CLIENT.get("/api/v1/organization/companies", headers=H)
    assert companies.status_code == 200
    company_id = companies.json()["items"][0]["id"]

    branch = _CLIENT.post("/api/v1/organization/branches", headers=H,
                          json={"company_id": company_id, "code": "SUC-01", "name": "Sucursal Centro"})
    assert branch.status_code == 200, branch.text
    branch_id = branch.json()["id"]

    est = _CLIENT.post("/api/v1/organization/establishments", headers=H,
                       json={"branch_id": branch_id, "code": "EST-01", "name": "Establecimiento A"})
    assert est.status_code == 200, est.text

    wh = _CLIENT.post("/api/v1/organization/warehouses", headers=H,
                      json={"company_id": company_id, "branch_id": branch_id, "code": "ALM-01", "name": "Almacén Central"})
    assert wh.status_code == 200, wh.text
    wh_id = wh.json()["id"]

    loc = _CLIENT.post("/api/v1/organization/locations", headers=H,
                       json={"warehouse_id": wh_id, "code": "A-01"})
    assert loc.status_code == 200, loc.text

    # verificación: cada lista los contiene
    assert any(b["code"] == "SUC-01" for b in _CLIENT.get(f"/api/v1/organization/branches?company_id={company_id}", headers=H).json())
    assert any(e["code"] == "EST-01" for e in _CLIENT.get(f"/api/v1/organization/establishments?branch_id={branch_id}", headers=H).json())
    # Desde la Spec 008 ambas listas son paginadas: {total, limit, offset, items}.
    assert any(w["code"] == "ALM-01" for w in _CLIENT.get(f"/api/v1/organization/warehouses?company_id={company_id}", headers=H).json()["items"])
    assert any(loc["code"] == "A-01" for loc in _CLIENT.get(f"/api/v1/organization/locations?warehouse_id={wh_id}", headers=H).json()["items"])


def test_security_chain_roles():
    H = _auth_headers()
    roles = _CLIENT.get("/api/v1/roles", headers=H)
    assert roles.status_code == 200
    admin = next((r for r in roles.json()["items"] if r["code"] == "ADMIN"), None)
    assert admin is not None

    created = _CLIENT.post("/api/v1/users", headers=H, json={
        "username": "jperez", "email": "j@x.com", "password": "Clave2026Segura!",
        "must_change_password": True,
    })
    assert created.status_code == 200, created.text
    uid = created.json()["id"]

    assign = _CLIENT.post(f"/api/v1/users/{uid}/roles", headers=H, json={"role_id": admin["id"]})
    assert assign.status_code == 200, assign.text

    users = _CLIENT.get("/api/v1/users", headers=H).json()
    me = next(u for u in users if u["id"] == uid)
    assert any(r["id"] == admin["id"] for r in me["roles"])

    remove = _CLIENT.delete(f"/api/v1/users/{uid}/roles/{admin['id']}", headers=H)
    assert remove.status_code == 200, remove.text
    users = _CLIENT.get("/api/v1/users", headers=H).json()
    me = next(u for u in users if u["id"] == uid)
    assert all(r["id"] != admin["id"] for r in me["roles"])


def test_read_only_blocks_business_writes():
    H = _auth_headers()
    companies = _CLIENT.get("/api/v1/organization/companies", headers=H).json()["items"]
    company_id = companies[0]["id"]

    # la licencia vigente envejece hasta pasado el 1 de mayo → modo READ_ONLY (enforcement real)
    db = _FACTORY()
    try:
        mode = _simular_licencia_vencida(db)
    finally:
        db.close()
    assert mode == "READ_ONLY"

    blocked = _CLIENT.post("/api/v1/organization/branches", headers=H,
                           json={"company_id": company_id, "code": "SUC-RO", "name": "No debe crearse"})
    assert blocked.status_code == 423
    assert blocked.json().get("code") == "LICENSE_READ_ONLY"

    # restaurar FULL_ACCESS y confirmar que escribe
    db = _FACTORY()
    try:
        _activate_full_access(db)
    finally:
        db.close()
    ok = _CLIENT.post("/api/v1/organization/branches", headers=H,
                      json={"company_id": company_id, "code": "SUC-OK", "name": "Sí debe crearse"})
    assert ok.status_code == 200, ok.text
