"""Auditoría del rechazo del análisis documental (OD-AUD-07/08/09).

El contenido subido nunca es malicioso: los dobles de analizador deciden el
resultado. La firma usada por los dobles es sintética.
"""

from __future__ import annotations

import hashlib
import io
import socket
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sesion_mfa import login_completo
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base, get_db, init_models
from app.core.errors import KontrolError
from app.modules.audit.models import AuditEvent
from app.modules.documents import scanning, service
from app.modules.documents.models import (
    Document,
    DocumentCategory,
    DocumentType,
    DocumentVersion,
    StoredFile,
)
from app.modules.documents.storage import FilesystemStorageProvider, set_storage
from app.modules.identity_access.models import User
from app.modules.organization.models import Company
from app.modules.setup.api import SetupRequest, initialize
from tests.audit_world import PASSWORD
from tests.conftest import make_engine

_CLIENT: TestClient
_FACTORY: sessionmaker
_ROOT: Path

PDF = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n%%EOF\n"
FIRMA_SINTETICA = "Firma-Sintetica-De-Prueba"


@pytest.fixture(scope="module", autouse=True)
def _app_client(tmp_path_factory):
    global _CLIENT, _FACTORY, _ROOT
    engine = make_engine()
    init_models()
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    import app.core.database as dm

    dm._engine = engine  # type: ignore[attr-defined]
    dm._SessionLocal = factory  # type: ignore[attr-defined]
    _ROOT = tmp_path_factory.mktemp("kontrol-docs")
    set_storage(FilesystemStorageProvider(_ROOT))
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
    yield _CLIENT
    set_storage(None)


def _headers() -> dict:
    r = login_completo(_CLIENT, "/api/v1/auth/login", json={
        "tenant_code": "DEMO", "username": "admin", "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _company_id() -> str:
    return _CLIENT.get("/api/v1/organization/companies", headers=_headers()).json()["items"][0]["id"]


_N = {"i": 0}


def _doc_type(code: str | None = None, **overrides) -> dict:
    _N["i"] += 1
    body = {
        "company_id": _company_id(),
        "code": code or f"TIPO{_N['i']}",
        "name": "Tipo de prueba",
        "allowed_mime_types": ["application/pdf"],
        "scan_required": True,
        **overrides,
    }
    r = _CLIENT.post("/api/v1/documentos/tipos", headers=_headers(), json=body)
    assert r.status_code == 200, r.text
    return r.json()


def _document(type_id: str, **overrides) -> dict:
    _N["i"] += 1
    body = {"company_id": _company_id(), "document_type_id": type_id,
            "title": f"Documento {_N['i']}", **overrides}
    r = _CLIENT.post("/api/v1/documentos", headers=_headers(), json=body)
    assert r.status_code == 200, r.text
    return r.json()


def _upload(document_id: str, content: bytes, name: str = "archivo.pdf",
            mime: str = "application/pdf"):
    return _CLIENT.post(
        f"/api/v1/documentos/{document_id}/versiones",
        headers=_headers(),
        files={"file": (name, io.BytesIO(content), mime)})


class _DobleInfectado(scanning.FileSecurityScanner):
    name = "doble-infectado"

    def available(self) -> bool:
        return True

    def scan(self, path: str) -> scanning.ScanResult:
        del path
        return scanning.ScanResult(scanning.INFECTED, self.name,
                                   signature=FIRMA_SINTETICA)

    def engine_version(self) -> str | None:
        return "motor-prueba 1.0"


class _DobleFallido(scanning.FileSecurityScanner):
    name = "doble-fallido"

    def __init__(self, reason: str):
        self.reason = reason

    def available(self) -> bool:
        return True

    def scan(self, path: str) -> scanning.ScanResult:
        del path
        return scanning.ScanResult(scanning.SCAN_FAILED, self.name,
                                   signature=FIRMA_SINTETICA,
                                   details={"reason": self.reason})


class _DobleSaltado(scanning.FileSecurityScanner):
    name = "doble-saltado"

    def available(self) -> bool:
        return True

    def scan(self, path: str) -> scanning.ScanResult:
        del path
        return scanning.ScanResult(scanning.SKIPPED, self.name,
                                   signature=FIRMA_SINTETICA,
                                   details={"reason": "scanning_disabled"})


@pytest.fixture
def _scanner_restaurado():
    yield
    scanning.set_scanner(None)


# ------------------------------------------------------------------ SCAN-01
def test_rechazo_infectado_audita_evidencia_minima(_scanner_restaurado):
    doc_type = _doc_type()
    document = _document(doc_type["id"])
    contenido = PDF
    nombre = "informe-confidencial.pdf"
    scanning.set_scanner(_DobleInfectado())
    try:
        r = _upload(document["id"], contenido, name=nombre)
    finally:
        scanning.set_scanner(None)

    assert r.status_code == 422, r.text
    cuerpo = r.json()
    assert cuerpo["code"] == "FILE_INFECTED"
    assert cuerpo["details"] == {"scan_result": "INFECTED",
                                 "category": "MALWARE_DETECTED"}

    db = _FACTORY()
    try:
        eventos = db.execute(
            select(AuditEvent).where(
                AuditEvent.action == "DOCUMENT_SCAN_REJECTED",
                AuditEvent.entity_id == document["id"])
        ).scalars().all()
        assert len(eventos) == 1
        ev = eventos[0]
        empresa = db.execute(
            select(Company).where(Company.code == "D1")
        ).scalars().first()
        assert ev.company_id == empresa.id
        assert ev.tenant_id == empresa.tenant_id
        assert ev.user_id is not None
        assert ev.request_id == r.headers["X-Request-ID"]
        assert ev.reason == "MALWARE_DETECTED"
        assert set(ev.evidence) == {
            "category", "reason_code", "engine", "engine_version", "sha256",
            "size_bytes", "detected_mime", "document_type_id"}
        assert ev.evidence["sha256"] == hashlib.sha256(contenido).hexdigest()
        assert ev.evidence["size_bytes"] == len(contenido)
        assert ev.evidence["engine_version"] == "motor-prueba 1.0"
        representacion = repr((ev.before, ev.after, ev.evidence, ev.reason))
        assert FIRMA_SINTETICA not in representacion
        assert nombre not in representacion
    finally:
        db.close()
    assert FIRMA_SINTETICA not in r.text
    assert nombre not in r.text


# ------------------------------------------------------------------ SCAN-02
@pytest.mark.parametrize(
    "reason, categoria, codigo",
    [
        ("scanner_unavailable", "SCANNER_UNAVAILABLE", "scanner_unavailable"),
        ("connection_refused", "SCANNER_UNAVAILABLE", "connection_refused"),
        ("timeout", "SCAN_TIMEOUT", "timeout"),
        ("scanner_error", "SCAN_ERROR", "scanner_error"),
        ("PermissionError", "SCAN_ERROR", "os_error"),
    ],
)
def test_rechazo_scan_failed_normalizado(reason, categoria, codigo,
                                         _scanner_restaurado):
    doc_type = _doc_type()
    document = _document(doc_type["id"])
    scanning.set_scanner(_DobleFallido(reason))
    try:
        r = _upload(document["id"], PDF)
    finally:
        scanning.set_scanner(None)

    assert r.status_code == 422, r.text
    cuerpo = r.json()
    assert cuerpo["code"] == "SCAN_FAILED"
    assert cuerpo["details"]["category"] == categoria

    db = _FACTORY()
    try:
        eventos = db.execute(
            select(AuditEvent).where(
                AuditEvent.action == "DOCUMENT_SCAN_REJECTED",
                AuditEvent.entity_id == document["id"])
        ).scalars().all()
        assert len(eventos) == 1
        assert eventos[0].evidence["category"] == categoria
        assert eventos[0].evidence["reason_code"] == codigo
        assert eventos[0].evidence["engine_version"] == "unknown"
    finally:
        db.close()


def test_rechazo_skipped_normalizado(_scanner_restaurado):
    doc_type = _doc_type()
    document = _document(doc_type["id"])
    scanning.set_scanner(_DobleSaltado())
    try:
        r = _upload(document["id"], PDF)
    finally:
        scanning.set_scanner(None)

    assert r.status_code == 422, r.text
    assert r.json()["code"] == "SCAN_FAILED"
    assert r.json()["details"]["category"] == "SCANNER_UNAVAILABLE"

    db = _FACTORY()
    try:
        eventos = db.execute(
            select(AuditEvent).where(
                AuditEvent.action == "DOCUMENT_SCAN_REJECTED",
                AuditEvent.entity_id == document["id"])
        ).scalars().all()
        assert len(eventos) == 1
        assert eventos[0].evidence["category"] == "SCANNER_UNAVAILABLE"
        assert eventos[0].evidence["reason_code"] == "scanning_disabled"
    finally:
        db.close()


# ------------------------------------------------------------------ SCAN-03
def test_rechazo_sobrevive_al_rollback_y_deshace_la_carga(
        _scanner_restaurado):
    doc_type = _doc_type()
    document = _document(doc_type["id"])
    db = _FACTORY()
    try:
        empresa = db.execute(
            select(Company).where(Company.code == "D1")
        ).scalars().first()
        actor = db.execute(
            select(User).where(User.username == "admin")
        ).scalars().first()

        pendiente = DocumentCategory(
            company_id=empresa.id, code="CAT-PENDIENTE",
            name="Categoria pendiente")
        db.add(pendiente)
        db.flush()
        categoria_id = pendiente.id

        documento = db.get(Document, document["id"])
        tipo = db.get(DocumentType, doc_type["id"])
        scanning.set_scanner(_DobleInfectado())
        try:
            with pytest.raises(KontrolError) as error:
                service.upload_version(
                    db, document=documento, doc_type=tipo,
                    stream=io.BytesIO(PDF), original_name="archivo.pdf",
                    declared_mime="application/pdf", actor=actor)
        finally:
            scanning.set_scanner(None)
    finally:
        db.close()

    assert error.value.code == "FILE_INFECTED", error.value
    db = _FACTORY()
    try:
        eventos = db.execute(
            select(AuditEvent).where(
                AuditEvent.action == "DOCUMENT_SCAN_REJECTED",
                AuditEvent.entity_id == document["id"])
        ).scalars().all()
        assert len(eventos) == 1
        pendientes = db.execute(
            select(DocumentCategory).where(DocumentCategory.id == categoria_id)
        ).scalars().all()
        assert pendientes == []
    finally:
        db.close()


# ------------------------------------------------------------------ SCAN-04
def test_rechazo_no_crea_stored_file_ni_version(_scanner_restaurado):
    doc_type = _doc_type()
    document = _document(doc_type["id"])
    db = _FACTORY()
    try:
        empresa = db.execute(
            select(Company).where(Company.code == "D1")
        ).scalars().first()
        stored_before = db.execute(
            select(StoredFile).where(StoredFile.company_id == empresa.id)
        ).scalars().all()
        version_before = db.execute(
            select(DocumentVersion).where(
                DocumentVersion.document_id == document["id"])
        ).scalars().all()
    finally:
        db.close()

    scanning.set_scanner(_DobleInfectado())
    try:
        r = _upload(document["id"], PDF)
    finally:
        scanning.set_scanner(None)
    assert r.status_code == 422, r.text

    db = _FACTORY()
    try:
        stored_after = db.execute(
            select(StoredFile).where(StoredFile.company_id == empresa.id)
        ).scalars().all()
        version_after = db.execute(
            select(DocumentVersion).where(
                DocumentVersion.document_id == document["id"])
        ).scalars().all()
        assert len(stored_after) == len(stored_before)
        assert len(version_after) == len(version_before)
    finally:
        db.close()


# ------------------------------------------------------------------ SCAN-05
@pytest.mark.parametrize(
    "resultado, detalle, categoria, codigo",
    [
        (scanning.INFECTED, None, "MALWARE_DETECTED", "threat_detected"),
        (scanning.SKIPPED, None, "SCANNER_UNAVAILABLE", "scanning_disabled"),
        (scanning.SCAN_FAILED, {"reason": "scanner_unavailable"},
         "SCANNER_UNAVAILABLE", "scanner_unavailable"),
        (scanning.SCAN_FAILED, {"reason": "connection_refused"},
         "SCANNER_UNAVAILABLE", "connection_refused"),
        (scanning.SCAN_FAILED, {"reason": "timeout"},
         "SCAN_TIMEOUT", "timeout"),
        (scanning.SCAN_FAILED, {"reason": "TimeoutExpired"},
         "SCAN_TIMEOUT", "timeout"),
        (scanning.SCAN_FAILED, {"reason": "stream_interrupted"},
         "SCAN_ERROR", "stream_interrupted"),
        (scanning.SCAN_FAILED, {"reason": "truncated_response"},
         "SCAN_ERROR", "truncated_response"),
        (scanning.SCAN_FAILED, {"reason": "scanner_error"},
         "SCAN_ERROR", "scanner_error"),
        (scanning.SCAN_FAILED, {"reason": "protocol_error"},
         "SCAN_ERROR", "protocol_error"),
        (scanning.SCAN_FAILED, {"reason": "PermissionError"},
         "SCAN_ERROR", "os_error"),
        (scanning.SCAN_FAILED, {}, "SCAN_ERROR", "scanner_error"),
        (scanning.PENDING_SCAN, None, "SCAN_ERROR", "scanner_error"),
    ],
)
def test_clasificar_rechazo(resultado, detalle, categoria, codigo):
    scan = scanning.ScanResult(resultado, "doble", signature=FIRMA_SINTETICA,
                               details=detalle)
    assert scanning.clasificar_rechazo(scan) == (categoria, codigo)


def test_clamav_engine_version_no_existe():
    assert scanning.ClamAVScanner(binary="/no/existe").engine_version() is None


def test_disabled_engine_version():
    assert scanning.DisabledScanner().engine_version() == "disabled"


def test_clamd_engine_version_sin_demonio():
    puerto = _puerto_cerrado()
    assert scanning.ClamdScanner(host="127.0.0.1", port=puerto,
                                 timeout=1).engine_version() is None


def _puerto_cerrado() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
