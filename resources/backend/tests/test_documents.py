"""Gestión documental (Spec 046).

Cubre lo que la Spec declara no negociable: que un archivo no se entregue si no
es recuperable y está limpio, que una versión histórica no se reinterprete, que
conocer un identificador no dé acceso, y que el nombre del usuario jamás toque
el sistema de archivos.

Sobre PostgreSQL y almacenamiento **real** cuando el entorno lo indica (P21).
"""

from __future__ import annotations

import hashlib
import io
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sesion_mfa import login_completo
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base, get_db, init_models
from app.core.errors import KontrolError
from app.modules.documents import scanning, service
from app.modules.documents.models import DocumentVersion, StoredFile
from app.modules.documents.storage import FilesystemStorageProvider, sanitize_filename, set_storage
from app.modules.setup.api import SetupRequest, initialize
from tests.conftest import make_engine

_CLIENT: TestClient
_FACTORY: sessionmaker
_ROOT: Path

#: Cadena EICAR: fixture de prueba reconocido por todo antivirus, **no** malware
#: real. Se construye por partes para que este archivo fuente no se marque.
EICAR = (b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE" b"!$H+H" b"*")

PDF = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n%%EOF\n"
PNG = bytes.fromhex("89504e470d0a1a0a0000000d49484452") + b"\x00" * 64
ELF = bytes.fromhex("7f454c4602010100") + b"\x00" * 128


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

    # Almacenamiento **real** en disco, no simulado (§70).
    _ROOT = tmp_path_factory.mktemp("kontrol-docs")
    set_storage(FilesystemStorageProvider(_ROOT))

    db = factory()
    initialize(db, SetupRequest(
        tenant_code="DEMO", tenant_name="Empresa Demo", company_code="D1",
        company_legal_name="Demo C.A.", company_rif="J-12345678-9",
        admin_username="admin", admin_password="Kontrol2026Segura!"))
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
        "tenant_code": "DEMO", "username": "admin", "password": "Kontrol2026Segura!"})
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
        "allowed_mime_types": ["application/pdf", "image/png"],
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
            mime: str = "application/pdf", extra_headers: dict | None = None, **kwargs):
    return _CLIENT.post(
        f"/api/v1/documentos/{document_id}/versiones",
        headers={**_headers(), **(extra_headers or {})},
        files={"file": (name, io.BytesIO(content), mime)}, **kwargs)


# ---------------------------------------------------------------- AC-046-01
def test_catalogos_nacen_vacios():
    """KONTROL no entrega tipos ni categorías documentales (P8)."""
    db = _FACTORY()
    try:
        from app.modules.documents.models import DocumentCategory, DocumentType

        # La instalación recién creada no trae ninguno; los de prueba se crean
        # explícitamente en cada caso.
        assert db.execute(select(DocumentCategory)).scalars().all() == []
        assert db.execute(select(DocumentType)).scalars().all() == []
    finally:
        db.close()


# ---------------------------------------------------------------- AC-046-02
def test_lista_blanca_vacia_significa_ninguno():
    doc_type = _doc_type(allowed_mime_types=[])
    document = _document(doc_type["id"])
    r = _upload(document["id"], PDF)
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "MIME_NOT_ALLOWED"


# ---------------------------------------------------------------- AC-046-03
def test_documento_logico_sin_archivo():
    document = _document(_doc_type()["id"])
    assert document["status"] == "DRAFT"
    assert document["current_version"] is None
    listed = _CLIENT.get("/api/v1/documentos", headers=_headers()).json()
    assert any(d["id"] == document["id"] for d in listed["items"])


# ---------------------------------------------------------------- AC-046-04
def test_subida_valida_calcula_hash_en_servidor():
    document = _document(_doc_type()["id"])
    r = _upload(document["id"], PDF, name="packing-list.pdf")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["version_number"] == 1
    assert body["sha256"] == hashlib.sha256(PDF).hexdigest()
    assert body["file"]["detected_mime"] == "application/pdf"
    # La respuesta **no** expone el almacenamiento.
    assert "storage_key" not in str(body)

    db = _FACTORY()
    try:
        stored = db.execute(select(StoredFile)).scalars().all()[-1]
        # La clave es opaca: no contiene el nombre, ni la empresa, ni el tercero.
        assert "packing-list" not in stored.storage_key
        assert _company_id() not in stored.storage_key
    finally:
        db.close()


# ---------------------------------------------------------------- AC-046-05
def test_el_nombre_del_usuario_nunca_es_ruta():
    """Ningún nombre escribe fuera de la raíz del proveedor."""
    for evil in ("../../../etc/passwd", "..\\win.ini", "/etc/shadow", "CON.pdf",
                 "a\rb\nc.pdf", "  ...  ", "x" * 400 + ".pdf", 'co"millas.pdf'):
        clean = sanitize_filename(evil)
        assert "/" not in clean and "\\" not in clean
        assert not clean.startswith("..")
        assert "\r" not in clean and "\n" not in clean
        assert '"' not in clean
        assert len(clean) <= 255

    document = _document(_doc_type()["id"])
    r = _upload(document["id"], PDF, name="../../../etc/passwd.pdf")
    assert r.status_code == 200, r.text
    # Nada se escribió fuera de la raíz.
    outside = Path("/etc/passwd.pdf")
    assert not outside.exists()
    files = [p for p in _ROOT.rglob("*") if p.is_file()]
    for path in files:
        assert str(path.resolve()).startswith(str(_ROOT.resolve()))


# ------------------------------------------------------ AC-046-06 / AC-046-07
def test_mime_por_contenido_no_por_extension():
    """Un ejecutable renombrado a PDF se rechaza y **no** queda almacenado."""
    document = _document(_doc_type()["id"])
    before = len([p for p in _ROOT.rglob("*") if p.is_file()])

    r = _upload(document["id"], ELF, name="factura.pdf", mime="application/pdf")
    assert r.status_code == 422, r.text
    assert r.json()["code"] in ("MIME_MISMATCH", "MIME_NOT_ALLOWED")

    after = len([p for p in _ROOT.rglob("*") if p.is_file()])
    assert after == before, "el archivo rechazado quedó almacenado"

    # Doble extensión.
    r2 = _upload(document["id"], ELF, name="factura.pdf.exe", mime="application/pdf")
    assert r2.status_code == 422


# ---------------------------------------------------------------- AC-046-08
def test_tamano_maximo():
    doc_type = _doc_type(max_size_bytes=1024)
    document = _document(doc_type["id"])
    big = PDF + b"\x00" * 4096
    r = _upload(document["id"], big)
    assert r.status_code == 413
    assert r.json()["code"] == "FILE_TOO_LARGE"


# ---------------------------------------------------------------- AC-046-10
def test_versionado_sin_sobrescritura():
    document = _document(_doc_type()["id"])
    first = _upload(document["id"], PDF).json()
    second_content = PDF + b"% v2\n"
    second = _upload(document["id"], second_content,
                     data={"replacement_reason": "Corrección"}).json()

    assert second["version_number"] == 2
    assert first["sha256"] != second["sha256"]

    versions = _CLIENT.get(f"/api/v1/documentos/{document['id']}/versiones",
                           headers=_headers()).json()
    assert len(versions) == 2
    assert [v["status"] for v in versions] == ["ACTIVE", "SUPERSEDED"]
    # El hash de la V1 **no cambió**.
    v1 = [v for v in versions if v["version_number"] == 1][0]
    assert v1["sha256"] == hashlib.sha256(PDF).hexdigest()

    # Y su binario sigue descargándose.
    r = _CLIENT.get(f"/api/v1/documentos/{document['id']}/versiones/{first['id']}/descargar",
                    headers=_headers())
    assert r.status_code == 200
    assert r.content == PDF


# ---------------------------------------------------------------- AC-046-13
def test_subida_idempotente():
    document = _document(_doc_type()["id"])
    key = {"Idempotency-Key": "abc-123"}
    first = _upload(document["id"], PDF, extra_headers=key)
    assert first.status_code == 200
    second = _CLIENT.post(f"/api/v1/documentos/{document['id']}/versiones",
                          headers={**_headers(), **key},
                          files={"file": ("a.pdf", io.BytesIO(PDF), "application/pdf")})
    assert second.status_code == 200
    assert second.json().get("idempotent_hit") is True

    versions = _CLIENT.get(f"/api/v1/documentos/{document['id']}/versiones",
                           headers=_headers()).json()
    assert len(versions) == 1, "la repetición creó una versión de más"


# ============================================================================
# Seguridad del archivo · analizador REAL (§23-28)
# ============================================================================

def _scanner_real() -> bool:
    return scanning.get_scanner().available() and isinstance(
        scanning.get_scanner(), scanning.ClamAVScanner)


# ---------------------------------------------------------------- AC-046-27
@pytest.mark.skipif(not os.environ.get("KONTROL_CLAMSCAN_PATH"),
                    reason="Sin analizador real: la Spec no se acepta con simulación")
def test_archivo_infectado_se_rechaza_y_no_se_almacena():
    """EICAR debe terminar rechazado. Ningún binario queda escrito."""
    doc_type = _doc_type(allowed_mime_types=["application/pdf", "text/plain"])
    document = _document(doc_type["id"])
    before = len([p for p in _ROOT.rglob("*") if p.is_file()])

    r = _upload(document["id"], EICAR, name="prueba.txt", mime="text/plain")
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "FILE_INFECTED"
    assert r.json()["details"]["scan_result"] == "INFECTED"
    assert "Eicar" in (r.json()["details"].get("signature") or "")

    after = len([p for p in _ROOT.rglob("*") if p.is_file()])
    assert after == before, "un archivo infectado quedó almacenado"

    versions = _CLIENT.get(f"/api/v1/documentos/{document['id']}/versiones",
                           headers=_headers()).json()
    assert versions == []


@pytest.mark.skipif(not os.environ.get("KONTROL_CLAMSCAN_PATH"),
                    reason="Sin analizador real")
def test_archivo_limpio_pasa_el_analisis():
    doc_type = _doc_type(allowed_mime_types=["application/pdf", "text/plain"])
    document = _document(doc_type["id"])
    r = _upload(document["id"], b"contenido inofensivo\n", name="nota.txt", mime="text/plain")
    assert r.status_code == 200, r.text
    assert r.json()["file"]["security_status"] == "CLEAN"


# ---------------------------------------------------------------- AC-046-28
def test_sin_analizador_falso_seguro():
    """Analizador ausente **no** es archivo limpio (§26)."""
    class Ausente(scanning.FileSecurityScanner):
        name = "ninguno"

        def available(self) -> bool:
            return False

        def scan(self, path: str):
            return scanning.ScanResult(scanning.SCAN_FAILED, self.name,
                                       details={"reason": "scanner_unavailable"})

    original = scanning.get_scanner()
    scanning.set_scanner(Ausente())
    try:
        document = _document(_doc_type()["id"])
        r = _upload(document["id"], PDF)
        assert r.status_code == 422, r.text
        assert r.json()["code"] == "SCAN_FAILED"
        assert r.json()["details"]["scan_result"] == "SCAN_FAILED"
    finally:
        scanning.set_scanner(original)


def test_analisis_desactivado_se_declara_no_se_disfraza():
    """`SKIPPED` viaja en la respuesta: nunca se afirma que se analizó."""
    original = scanning.get_scanner()
    scanning.set_scanner(scanning.DisabledScanner())
    try:
        doc_type = _doc_type(scan_required=False)
        document = _document(doc_type["id"])
        r = _upload(document["id"], PDF)
        assert r.status_code == 200, r.text
        assert r.json()["file"]["security_status"] == "SKIPPED"
        assert r.json()["file"]["security_status"] != "CLEAN"
    finally:
        scanning.set_scanner(original)


# ============================================================================
# Vinculación, autorización y congelación
# ============================================================================

def _approval_request() -> str:
    """Solicitud de aprobación real, para probar el contrato con la Spec 045."""
    from app.modules.approvals.models import ApprovalRequest

    db = _FACTORY()
    try:
        _N["i"] += 1
        request = ApprovalRequest(
            company_id=_company_id(), process_type="PURCHASE_ORDER",
            document_type="PURCHASE_ORDER", document_id=f"doc-{_N['i']}",
            status="PENDING", fingerprint=f"fp-{_N['i']}")
        db.add(request)
        db.commit()
        return str(request.id)
    finally:
        db.close()


# ---------------------------------------------------------------- AC-046-16
def test_tipo_de_recurso_desconocido_se_rechaza():
    document = _document(_doc_type()["id"])
    r = _CLIENT.post(f"/api/v1/documentos/{document['id']}/vinculos", headers=_headers(),
                     json={"resource_type": "Cualquiera", "resource_id": "x"})
    assert r.status_code == 422
    assert r.json()["code"] == "RESOURCE_TYPE_UNKNOWN"


def test_recurso_inexistente_se_rechaza():
    document = _document(_doc_type()["id"])
    r = _CLIENT.post(f"/api/v1/documentos/{document['id']}/vinculos", headers=_headers(),
                     json={"resource_type": "ApprovalRequest",
                           "resource_id": "00000000-0000-0000-0000-000000000000"})
    assert r.status_code == 404
    assert r.json()["code"] == "RESOURCE_NOT_FOUND"


# ------------------------------------------------------ AC-046-14 / AC-046-15
def test_vinculacion_y_documento_compartido():
    doc_type = _doc_type()
    document = _document(doc_type["id"])
    _upload(document["id"], PDF)
    first = _approval_request()
    second = _approval_request()

    for request_id in (first, second):
        r = _CLIENT.post(f"/api/v1/documentos/{document['id']}/vinculos", headers=_headers(),
                         json={"resource_type": "ApprovalRequest", "resource_id": request_id})
        assert r.status_code == 200, r.text

    for request_id in (first, second):
        listed = _CLIENT.get(
            f"/api/v1/documentos/por-recurso/ApprovalRequest/{request_id}",
            headers=_headers()).json()
        assert any(d["id"] == document["id"] for d in listed)

    # Un solo binario para los dos vínculos.
    db = _FACTORY()
    try:
        versions = db.execute(select(DocumentVersion).where(
            DocumentVersion.document_id == document["id"])).scalars().all()
        assert len({v.stored_file_id for v in versions}) == 1
    finally:
        db.close()


# ------------------------------------- AC-046-18 · CONTRATO CON LA SPEC 045
def test_version_congelada_el_historico_no_se_reinterpreta():
    """Una aprobación resuelta conserva la versión que usó.

    Es el contrato que la Spec 045 dejó declarado, y se satisface **sin cambiar
    su modelo**: el vínculo vive en la tabla de 046.
    """
    doc_type = _doc_type()
    document = _document(doc_type["id"])
    v1 = _upload(document["id"], PDF).json()
    request_id = _approval_request()

    link = _CLIENT.post(f"/api/v1/documentos/{document['id']}/vinculos", headers=_headers(),
                        json={"resource_type": "ApprovalRequest", "resource_id": request_id})
    assert link.status_code == 200, link.text

    # La entidad se vuelve inmutable: el consumidor congela.
    db = _FACTORY()
    try:
        frozen = service.freeze_links(db, resource_type="ApprovalRequest",
                                      resource_id=request_id)
        db.commit()
        assert len(frozen) == 1
        assert frozen[0].frozen_version_id == v1["id"]
    finally:
        db.close()

    # Después se crea la V2.
    v2 = _upload(document["id"], PDF + b"% v2\n").json()
    assert v2["version_number"] == 2

    # El histórico sigue apuntando a la V1, no a «la última».
    listed = _CLIENT.get(f"/api/v1/documentos/por-recurso/ApprovalRequest/{request_id}",
                         headers=_headers()).json()
    assert listed[0]["link"]["frozen_version_id"] == v1["id"]
    assert listed[0]["link"]["is_frozen"] is True

    # Y descargar esa versión devuelve **sus** bytes, no los de la V2.
    r = _CLIENT.get(f"/api/v1/documentos/{document['id']}/versiones/{v1['id']}/descargar",
                    headers=_headers())
    assert r.status_code == 200
    assert r.content == PDF
    assert hashlib.sha256(r.content).hexdigest() == v1["sha256"]

    # El modelo de 045 no se tocó.
    from app.modules.approvals.models import ApprovalRequest

    columns = set(ApprovalRequest.__table__.c.keys())
    assert "document_link_id" not in columns and "attachment_id" not in columns


# ---------------------------------------------------------------- AC-046-19
def test_vinculo_congelado_no_se_desvincula():
    doc_type = _doc_type()
    document = _document(doc_type["id"])
    _upload(document["id"], PDF)
    request_id = _approval_request()
    link = _CLIENT.post(f"/api/v1/documentos/{document['id']}/vinculos", headers=_headers(),
                        json={"resource_type": "ApprovalRequest",
                              "resource_id": request_id}).json()
    db = _FACTORY()
    try:
        service.freeze_links(db, resource_type="ApprovalRequest", resource_id=request_id)
        db.commit()
    finally:
        db.close()

    r = _CLIENT.delete(f"/api/v1/documentos/vinculos/{link['id']}", headers=_headers())
    assert r.status_code == 409
    assert r.json()["code"] == "LINK_FROZEN"


# ---------------------------------------------------------------- AC-046-31
def test_borrado_protegido_y_archivado_conserva_binario():
    doc_type = _doc_type()
    document = _document(doc_type["id"])
    version = _upload(document["id"], PDF).json()

    r = _CLIENT.delete(f"/api/v1/documentos/{document['id']}", headers=_headers())
    assert r.status_code == 409
    assert r.json()["code"] == "DOCUMENT_IN_USE"
    assert "archive" in r.json()["details"]["allowed_actions"]

    archived = _CLIENT.post(f"/api/v1/documentos/{document['id']}/archive", headers=_headers())
    assert archived.status_code == 200

    # El binario sobrevive al archivado.
    download = _CLIENT.get(
        f"/api/v1/documentos/{document['id']}/versiones/{version['id']}/descargar",
        headers=_headers())
    assert download.status_code == 200
    assert download.content == PDF


# ------------------------------------------------------- AC-046-46 / AC-046-47
def test_listar_miles_de_documentos_sin_abrir_un_solo_binario():
    """La biblioteca lista documentos, no archivos (NFR-046-01).

    Se siembran 5.000 documentos y se pagina. El proveedor de almacenamiento se
    envuelve en un contador: si la respuesta abriera un binario, aunque fuese
    uno, el contador lo delataría.
    """
    import time
    import uuid as _uuid

    from app.modules.documents.models import Document
    from app.modules.documents.storage import get_storage

    doc_type = _doc_type()
    company = _company_id()

    db = _FACTORY()
    try:
        db.bulk_save_objects([
            Document(id=str(_uuid.uuid4()), company_id=company,
                     document_type_id=doc_type["id"], title=f"Masivo {i:05d}",
                     status="ACTIVE", is_managed=True)
            for i in range(5000)])
        db.commit()
    finally:
        db.close()

    real = get_storage()
    opens = {"n": 0}

    class _CountingStorage(type(real)):  # type: ignore[misc]
        def open(self, key):            # noqa: D102
            opens["n"] += 1
            return real.open(key)

        def exists(self, key):          # noqa: D102
            opens["n"] += 1
            return real.exists(key)

    set_storage(_CountingStorage(_ROOT))
    try:
        started = time.monotonic()
        r = _CLIENT.get("/api/v1/documentos?limit=50", headers=_headers())
        elapsed = time.monotonic() - started
    finally:
        set_storage(real)

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] >= 5000
    assert len(body["items"]) == 50, "la paginación debe acotar la respuesta"
    assert opens["n"] == 0, f"la lista abrió el almacenamiento {opens['n']} veces"
    # Umbral holgado: lo que se afirma es que no crece con el total, no una marca.
    assert elapsed < 5.0, f"listar 50 de 5.000 tardó {elapsed:.2f}s"


# ---------------------------------------------------------------- AC-046-37
def test_metadata_se_valida_contra_el_esquema_del_tipo():
    """El esquema lo declara el tipo; el código no conoce ningún campo (P8)."""
    doc_type = _doc_type(metadata_schema={
        "required": ["numero_expediente"],
        "fields": {
            "numero_expediente": {"type": "string"},
            "monto": {"type": "number"},
            "organismo": {"type": "string", "options": ["SENIAT", "SENCAMER"]},
        },
    })

    # Falta el obligatorio.
    r = _CLIENT.post("/api/v1/documentos", headers=_headers(), json={
        "company_id": _company_id(), "document_type_id": doc_type["id"],
        "title": "Sin expediente", "doc_metadata": {"monto": 10}})
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "METADATA_INVALID"
    assert "numero_expediente" in r.json()["details"]["field_errors"]

    # Tipo equivocado.
    r = _CLIENT.post("/api/v1/documentos", headers=_headers(), json={
        "company_id": _company_id(), "document_type_id": doc_type["id"],
        "title": "Monto textual",
        "doc_metadata": {"numero_expediente": "E-1", "monto": "mucho"}})
    assert r.status_code == 422
    assert "monto" in r.json()["details"]["field_errors"]

    # Opción no admitida.
    r = _CLIENT.post("/api/v1/documentos", headers=_headers(), json={
        "company_id": _company_id(), "document_type_id": doc_type["id"],
        "title": "Organismo raro",
        "doc_metadata": {"numero_expediente": "E-1", "organismo": "OTRO"}})
    assert r.status_code == 422
    assert "organismo" in r.json()["details"]["field_errors"]

    # Y la metadata correcta pasa.
    r = _CLIENT.post("/api/v1/documentos", headers=_headers(), json={
        "company_id": _company_id(), "document_type_id": doc_type["id"],
        "title": "Correcto",
        "doc_metadata": {"numero_expediente": "E-1", "monto": 10,
                         "organismo": "SENIAT"}})
    assert r.status_code == 200, r.text


def test_un_tipo_sin_esquema_no_impone_nada():
    doc_type = _doc_type()
    r = _CLIENT.post("/api/v1/documentos", headers=_headers(), json={
        "company_id": _company_id(), "document_type_id": doc_type["id"],
        "title": "Libre", "doc_metadata": {"lo_que_sea": 1}})
    assert r.status_code == 200, r.text


# ---------------------------------------------------------------- AC-046-36
def test_el_mismo_archivo_dos_veces_no_se_deduplica_ni_se_bloquea():
    """La coincidencia de hash se registra; no unifica ni impide nada."""
    from app.modules.audit.models import AuditEvent

    doc_type = _doc_type()
    first = _document(doc_type["id"])
    second = _document(doc_type["id"])
    assert _upload(first["id"], PDF).status_code == 200
    r = _upload(second["id"], PDF)
    assert r.status_code == 200, r.text

    db = _FACTORY()
    try:
        files = db.execute(select(StoredFile).where(
            StoredFile.sha256 == hashlib.sha256(PDF).hexdigest())).scalars().all()
        # Dos archivos distintos con la misma huella: dos evidencias, no una.
        assert len(files) >= 2
        assert len({f.storage_key for f in files}) == len(files)

        coincidences = db.execute(select(AuditEvent).where(
            AuditEvent.action == "DOCUMENT_HASH_COINCIDENCE")).scalars().all()
        assert coincidences, "la coincidencia debe quedar registrada"
    finally:
        db.close()


# ------------------------------------------------- AC-046-33 · retención
def test_sin_plazo_declarado_nada_vence():
    """KONTROL no inventa plazos legales (ESC-046-03)."""
    doc_type = _doc_type()
    db = _FACTORY()
    try:
        from app.modules.documents.models import DocumentType

        row = db.get(DocumentType, doc_type["id"])
        assert service.retention_days(row) is None
    finally:
        db.close()


def test_una_version_referenciada_no_se_purga():
    doc_type = _doc_type()
    document = _document(doc_type["id"])
    _upload(document["id"], PDF, name="v1.pdf")
    _upload(document["id"], PNG, name="v2.png", mime="image/png")
    request_id = _approval_request()
    _CLIENT.post(f"/api/v1/documentos/{document['id']}/vinculos", headers=_headers(),
                 json={"resource_type": "ApprovalRequest", "resource_id": request_id})

    db = _FACTORY()
    try:
        service.freeze_links(db, resource_type="ApprovalRequest", resource_id=request_id)
        db.commit()

        versions = db.execute(select(DocumentVersion).where(
            DocumentVersion.document_id == document["id"])
            .order_by(DocumentVersion.version_number)).scalars().all()
        current, frozen = versions[0], versions[1]

        # La vigente no se purga por serlo.
        assert service.purge_blockers(db, frozen)
        with pytest.raises(KontrolError) as excinfo:
            service.purge_version(db, version=frozen, actor=None)
        assert excinfo.value.code == "VERSION_IN_USE"
        assert excinfo.value.details["blocked_by"], "debe decir por qué no se purga"

        # La v1, ni vigente ni congelada, sí puede purgarse: el binario se va,
        # el rastro se queda.
        assert service.purge_blockers(db, current) == []
        stored_key = db.get(StoredFile, current.stored_file_id).storage_key
        assert service.purge_version(db, version=current, actor=None) is True
        db.commit()

        stored = db.get(StoredFile, current.stored_file_id)
        assert stored.status == "PURGED"
        assert stored.sha256, "la huella se conserva aunque el binario no esté"
        assert not (_ROOT / stored_key).exists()
        # Y la versión sigue existiendo como registro histórico.
        assert db.get(DocumentVersion, str(current.id)) is not None
    finally:
        db.close()
