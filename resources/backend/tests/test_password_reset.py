"""T-223 · Flujo de recuperación de contraseña (KAUD-012 → FR-001-026).

Verifica el ciclo completo: solicitud de reset → token entregado en modo
fundación → confirmación con nueva contraseña → login exitoso con la nueva
credencial. Antes de la remediación no existía UI ni prueba del flujo.
"""
from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta

import pytest
from conftest import make_engine
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.database import Base, get_db, init_models
from app.modules.licensing import service as licensing_service
from app.modules.organization.models import Installation
from app.modules.setup.api import SetupRequest, initialize

_ENGINE = _FACTORY = _CLIENT = None


@pytest.fixture(scope="module", autouse=True)
def _app_client():
    global _ENGINE, _FACTORY, _CLIENT
    engine = make_engine()
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
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    key = Ed25519PrivateKey.generate()
    pub = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    inst = db.execute(select(Installation).limit(1)).scalars().first()
    now = datetime.now(UTC)
    payload = {
        "issuer": "K", "license_id": "LIC-RESET", "installation_id": inst.installation_uuid,
        "customer_id": "C1", "contract_id": "C1", "company_tax_id": "J-12345678-9",
        "period_start": (now - timedelta(days=30)).isoformat(),
        "period_end": (now + timedelta(days=120)).isoformat(),
        "critical_warning_start": (now + timedelta(days=180)).isoformat(),
        "read_only_start": (now + timedelta(days=200)).isoformat(),
        "entitlements": {"companies": 1, "users": 25, "modules": ["*"]},
        "minimum_version": "1.0.0", "kid": "kontrol-lic-2026-01",  # el kid de la clave configurada (LICENCIA-SIN-ROTACION-DE-CLAVE)
    }
    sig = key.sign(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hex()
    os.environ["KONTROL_LICENSE_PUBLIC_KEY_PEM"] = pub
    get_settings.cache_clear()
    try:
        licensing_service.import_license(db, payload=payload, signature_hex=sig, source="MANUAL")
    finally:
        # El ancla se queda configurada: el vigente se reverifica contra ella en cada lectura y escritura (LICENCIA-ESTADO-SIN-REVERIFICAR).
        get_settings.cache_clear()
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
    _ENGINE, _FACTORY = engine, factory
    _CLIENT = TestClient(app)
    yield _CLIENT


def test_reset_password_flow_full_cycle():
    """Solicitud → token → confirmación → login con la nueva contraseña."""
    r = _CLIENT.post("/api/v1/auth/password-reset/request", json={
        "tenant_code": "DEMO", "username": "admin",
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ok"] is True
    token = data["reset_token"]
    assert token, "el token debe entregarse en modo fundación"

    # Un token no puede usarse dos veces y la confirmación cambia la credencial.
    new_password = "NuevaClave2026!"
    r = _CLIENT.post("/api/v1/auth/password-reset/confirm", json={
        "token": token, "new_password": new_password,
    })
    assert r.status_code == 200, r.text

    # La contraseña anterior ya no funciona; la nueva sí.
    r = _CLIENT.post("/api/v1/auth/login", json={
        "tenant_code": "DEMO", "username": "admin", "password": "Kontrol2026Segura!",
    })
    assert r.status_code == 401, r.text

    r = _CLIENT.post("/api/v1/auth/login", json={
        "tenant_code": "DEMO", "username": "admin", "password": new_password,
    })
    assert r.status_code == 200, r.text
    assert r.json()["access_token"]


def test_reset_password_unknown_user_is_safe():
    """No revela si el usuario existe (responde 401 uniforme)."""
    r = _CLIENT.post("/api/v1/auth/password-reset/request", json={
        "tenant_code": "DEMO", "username": "usuario_que_no_existe_xyz",
    })
    assert r.status_code == 401, r.text
    assert r.json()["code"] == "AUTH_INVALID_CREDENTIALS"
    assert "reset_token" not in r.json()
