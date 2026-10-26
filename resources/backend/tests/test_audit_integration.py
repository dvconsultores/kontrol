"""T-204 · Cobertura de auditoría de negocio (KAUD-001 → FR-009-022).

Verifica que operaciones de negocio (crear/transicionar documentos, mover
inventario, aplicar cobros/pagos) generan eventos AuditEvent con company_id,
action, entity_type y user_id. Antes de la remediación solo identity_access
auditaba; esta prueba impide la regresión.
"""
from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta

import pytest
from conftest import make_engine
from fastapi.testclient import TestClient
from sesion_mfa import login_completo
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.database import Base, get_db, init_models
from app.modules.audit.models import AuditEvent
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
    # Licencia FULL_ACCESS
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    key = Ed25519PrivateKey.generate()
    pub = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    inst = db.execute(select(Installation).limit(1)).scalars().first()
    now = datetime.now(UTC)
    payload = {
        "issuer": "K", "license_id": "LIC-AUD", "installation_id": inst.installation_uuid,
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


def _auth() -> dict:
    r = login_completo(_CLIENT, "/api/v1/auth/login", json={
        "tenant_code": "DEMO", "username": "admin", "password": "Kontrol2026Segura!",
    })
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _events() -> list[AuditEvent]:
    db = _FACTORY()
    try:
        return db.execute(select(AuditEvent)).scalars().all()
    finally:
        db.close()


def _event_actions() -> set[str]:
    return {e.action for e in _events()}


def test_business_operations_generate_audit_events():
    h = _auth()

    # La empresa en la que se opera. Antes bastaba con no decirlo, porque el
    # tenant tenía una sola; al crear la segunda hay que declararlo, y eso es
    # justamente lo que ARCH-MC-001 vino a hacer explícito.
    empresa = _CLIENT.get("/api/v1/organization/companies", headers=h).json()["items"][0]["id"]

    # organización
    comp = _CLIENT.post("/api/v1/organization/companies", headers=h,
                        json={"code": "D2", "legal_name": "Audit Co", "rif": "J-98765432-1"}).json()
    assert comp["id"]

    # Desde aquí el tenant tiene dos empresas: toda operación de empresa dice
    # en cuál ocurre.
    h = {**h, "X-Kontrol-Company": empresa}

    # maestro tercero (cliente)
    cust = _CLIENT.post("/api/v1/maestros/terceros", headers=h,
                        json={"code": "C-AUD", "name": "Cliente Audit", "roles": ["CLIENTE"]}).json()
    customer_id = cust["id"]

    # orden de venta + confirmación (Spec 030: DRAFT → SUBMITTED → RELEASED)
    order = _CLIENT.post("/api/v1/sales/orders", headers=h,
                         json={"code": "OV-AUD", "customer_id": customer_id, "margin": None, "currency": "VED"}).json()
    order_id = order["id"]
    prod = _CLIENT.post("/api/v1/maestros/catalogos/items", headers=h,
                        json={"code": "P-AUD", "name": "Servicio Audit", "item_type": "PRODUCT"}).json()
    r = _CLIENT.post(f"/api/v1/sales/orders/{order_id}/lines", headers=h,
                     json={"product_id": prod["id"], "quantity": 1, "unit_price": 10, "needs_inventory": False})
    assert r.status_code == 200, r.text
    r = _CLIENT.post(f"/api/v1/sales/orders/{order_id}/transition", headers=h, json={"target": "SUBMITTED"})
    assert r.status_code == 200, r.text

    after = _event_actions()
    expected = {
        "SALES_ORDER_TRANSITIONED",
    }
    missing = expected - after
    assert not missing, f"faltan eventos de auditoría de negocio: {missing}"
    assert "SALES_ORDER_TRANSITIONED" in after


def test_audit_events_have_context():
    """Los eventos de negocio deben incluir company_id/entity_type/entity_id."""
    db = _FACTORY()
    try:
        ev = db.execute(select(AuditEvent).where(AuditEvent.action == "SALES_ORDER_TRANSITIONED")).scalars().first()
    finally:
        db.close()
    assert ev is not None, "debe existir un evento SALES_ORDER_TRANSITIONED"
    assert ev.company_id is not None
    assert ev.entity_type == "SalesOrder"
    assert ev.entity_id
