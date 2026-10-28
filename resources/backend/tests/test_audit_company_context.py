"""Contexto de empresa y tenant en los eventos de auditoría (C04-T04).

Cubre que los eventos de auditoría de documentos, tipos documentales,
unidades de medida y presentaciones lleven la empresa de la operación; que
los de tipo documental se rotulen con la entidad `DocumentType`; y que
`PASSWORD_RESET_FAILED` lleve el tenant cuando el usuario es conocido.
"""

from __future__ import annotations

import io
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sesion_mfa import login_completo
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base, get_db, init_models
from app.core.errors import KontrolError
from app.core.security import sha256_hex
from app.modules.audit.models import AuditEvent
from app.modules.documents import scanning
from app.modules.identity_access.models import PasswordReset, User
from app.modules.identity_access.service import confirm_password_reset
from app.modules.organization.models import Tenant
from app.modules.setup.api import SetupRequest, initialize
from tests.audit_world import PASSWORD
from tests.conftest import make_engine

_CLIENT: TestClient
_FACTORY: sessionmaker

PDF = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n%%EOF\n"


class _AnalizadorLimpio(scanning.FileSecurityScanner):
    name = "prueba"

    def available(self) -> bool:
        return True

    def scan(self, path: str) -> scanning.ScanResult:
        return scanning.ScanResult(scanning.CLEAN, self.name)


@pytest.fixture(scope="module", autouse=True)
def _app_client():
    global _CLIENT, _FACTORY
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
        admin_username="admin", admin_password=PASSWORD))
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
    scanning.set_scanner(_AnalizadorLimpio())
    yield _CLIENT
    scanning.set_scanner(None)


def _headers() -> dict:
    r = login_completo(_CLIENT, "/api/v1/auth/login", json={
        "tenant_code": "DEMO", "username": "admin", "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _tenant_id() -> str:
    db = _FACTORY()
    try:
        return str(db.execute(select(Tenant).where(Tenant.code == "DEMO")).scalars().first().id)
    finally:
        db.close()


def _company() -> tuple[str, str]:
    company = _CLIENT.get("/api/v1/organization/companies", headers=_headers()).json()["items"][0]
    return str(company["id"]), _tenant_id()


def _audit_events(action: str | None = None):
    db = _FACTORY()
    try:
        stmt = select(AuditEvent)
        if action is not None:
            stmt = stmt.where(AuditEvent.action == action)
        return db.execute(stmt).scalars().all()
    finally:
        db.close()


def test_ctx_01_tipo_documental_lleva_entidad_y_empresa():
    """CTX-01: DOCUMENT_TYPE_CREATED con entity_type=DocumentType y empresa."""
    company_id, _ = _company()
    code = "TAUD01"
    r = _CLIENT.post("/api/v1/documentos/tipos", headers=_headers(), json={
        "company_id": company_id,
        "code": code,
        "name": "Tipo auditado",
        "allowed_mime_types": ["application/pdf"],
        "scan_required": True,
    })
    assert r.status_code == 200, r.text
    document_type_id = r.json()["id"]

    events = [e for e in _audit_events("DOCUMENT_TYPE_CREATED")
              if getattr(e, "entity_id", None) == document_type_id]
    assert len(events) == 1
    assert events[0].entity_type == "DocumentType"
    assert events[0].company_id == company_id


def test_ctx_02_documento_lleva_empresa_y_tenant():
    """CTX-02: DOCUMENT_CREATED con empresa y tenant de la operación."""
    company_id, tenant_id = _company()
    type_r = _CLIENT.post("/api/v1/documentos/tipos", headers=_headers(), json={
        "company_id": company_id,
        "code": "TAUD02",
        "name": "Tipo auditado 2",
        "allowed_mime_types": ["application/pdf"],
        "scan_required": True,
    })
    assert type_r.status_code == 200, type_r.text
    document_type_id = type_r.json()["id"]

    r = _CLIENT.post("/api/v1/documentos", headers=_headers(), json={
        "company_id": company_id,
        "document_type_id": document_type_id,
        "title": "Documento auditado",
    })
    assert r.status_code == 200, r.text
    document_id = r.json()["id"]

    events = [e for e in _audit_events("DOCUMENT_CREATED")
              if getattr(e, "entity_id", None) == document_id]
    assert len(events) == 1
    assert events[0].company_id == company_id
    assert events[0].tenant_id == tenant_id


def test_ctx_03_carga_version_lleva_empresa():
    """CTX-03: DOCUMENT_FILE_UPLOADED con empresa de la operación."""
    company_id, _ = _company()
    type_r = _CLIENT.post("/api/v1/documentos/tipos", headers=_headers(), json={
        "company_id": company_id,
        "code": "TAUD03",
        "name": "Tipo auditado 3",
        "allowed_mime_types": ["application/pdf"],
        "scan_required": True,
    })
    assert type_r.status_code == 200, type_r.text
    document_type_id = type_r.json()["id"]

    doc_r = _CLIENT.post("/api/v1/documentos", headers=_headers(), json={
        "company_id": company_id,
        "document_type_id": document_type_id,
        "title": "Documento con versión auditada",
    })
    assert doc_r.status_code == 200, doc_r.text
    document_id = doc_r.json()["id"]

    upload_r = _CLIENT.post(
        f"/api/v1/documentos/{document_id}/versiones",
        headers=_headers(),
        files={"file": ("archivo.pdf", io.BytesIO(PDF), "application/pdf")},
    )
    assert upload_r.status_code == 200, upload_r.text

    events = [e for e in _audit_events("DOCUMENT_FILE_UPLOADED")
              if getattr(e, "entity_id", None) == document_id]
    assert len(events) == 1
    assert events[0].company_id == company_id


def test_ctx_04_unidad_lleva_empresa():
    """CTX-04: unit_of_measure CREATE con empresa de la petición."""
    company_id, _ = _company()
    r = _CLIENT.post("/api/v1/maestros/unidades", headers=_headers(), json={
        "code": "UAUD04",
        "name": "Unidad auditada",
        "symbol": "uaud04",
        "dimension": "CANTIDAD",
    })
    assert r.status_code == 200, r.text
    unit_id = r.json()["id"]

    events = [e for e in _audit_events() if getattr(e, "entity_id", None) == unit_id]
    assert len(events) == 1
    assert events[0].entity_type == "unit_of_measure"
    assert events[0].company_id == company_id


def test_ctx_05_password_reset_expired_tenant_e_invalid_sin_tenant():
    """CTX-05: PASSWORD_RESET_FAILED lleva tenant solo con usuario conocido."""
    db = _FACTORY()
    try:
        admin = db.execute(
            select(User).where(User.username == "admin")).scalars().first()
        assert admin is not None
        token = "token-sintetico-expirado"
        reset = PasswordReset(
            user_id=admin.id,
            token_hash=sha256_hex(token),
            expires_at=datetime.now(UTC) - timedelta(minutes=1),
            source="SELF",
        )
        db.add(reset)
        db.commit()

        with pytest.raises(KontrolError):
            confirm_password_reset(db, token=token, new_password=PASSWORD)

        events = db.execute(select(AuditEvent).where(
            AuditEvent.action == "PASSWORD_RESET_FAILED")).scalars().all()
        expired = [e for e in events if getattr(e, "reason", None) == "EXPIRED"]
        assert any(e.tenant_id == str(admin.tenant_id) and
                   e.entity_id == str(admin.id) for e in expired)

        with pytest.raises(KontrolError):
            confirm_password_reset(db, token="token-inexistente", new_password=PASSWORD)

        events = db.execute(select(AuditEvent).where(
            AuditEvent.action == "PASSWORD_RESET_FAILED")).scalars().all()
        invalid = [e for e in events if getattr(e, "reason", None) == "INVALID"]
        assert any(e.tenant_id is None for e in invalid)
    finally:
        db.close()


def test_ctx_06_ningun_evento_catalogado_sin_empresa():
    """CTX-06: los eventos de catálogo emitidos llevan siempre empresa."""
    entity_types = {
        "Document",
        "DocumentType",
        "unit_of_measure",
        "presentation",
        "unit_conversion",
        "product_presentation_version",
        "catalog_item",
    }
    events = _audit_events()
    relevant = [e for e in events if getattr(e, "entity_type", None) in entity_types]
    assert relevant, "se esperaban eventos de catálogo durante el módulo"
    assert all(getattr(e, "company_id", None) is not None for e in relevant)
