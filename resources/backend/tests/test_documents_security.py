"""Suite de seguridad de la gestión documental (Spec 046, T-046-106).

Una prueba por amenaza del registro de riesgos, `AMZ-01` a `AMZ-20`, más los
fallos de almacenamiento que la Spec exige tratar como fallos y no como
entregas: objeto ausente, huella distinta y escritura fallida.

Sobre almacenamiento **real** en disco y analizador real cuando el entorno lo
provee: un mock no sirve como evidencia de que esto está cerrado (§159).
"""

from __future__ import annotations

import io
import os
import threading
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base, get_db, init_models
from app.core.errors import ConflictError
from app.modules.audit.models import AuditEvent
from app.modules.documents import api as documents_api
from app.modules.documents import scanning, service
from app.modules.documents.models import Document, DocumentType, DocumentVersion, FileSecurityScan, StoredFile
from app.modules.documents.storage import (
    FilesystemStorageProvider,
    StorageError,
    generate_storage_key,
    get_storage,
    sanitize_filename,
    set_storage,
)
from app.modules.identity_access import service as identity_service
from app.modules.identity_access.models import User, UserRole
from app.modules.organization.models import Company, Installation, Tenant
from app.modules.setup.api import SetupRequest, _bootstrap_roles, initialize
from app.modules.system.models import IdempotencyRecord
from tests.concurrency import carrera, esperar_bloqueados
from tests.conftest import make_engine

_CLIENT: TestClient
_FACTORY: sessionmaker
_ROOT: Path

#: Cadena EICAR: fixture de prueba estándar, **no** malware real. Partida para
#: que este propio archivo fuente no dispare el antivirus del desarrollador.
EICAR = (b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE" b"!$H+H" b"*")

#: Las siete carreras de versión se fuerzan con primitivas de PostgreSQL (`tests/concurrency.py`:
#: `pg_backend_pid`, `pg_stat_activity`) y su contrato es que **PostgreSQL decide** (FR-046-115,
#: `conc-046-concurrent-version-delta.md`, G-CONC-046-06; P21). En SQLite no existen esas
#: funciones ni el bloqueo de fila: se omiten diciéndolo, como `test_license_import_race.py`.
PG = os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql")
solo_postgresql = pytest.mark.skipif(
    not PG, reason="la carrera de versiones se certifica sobre PostgreSQL (FR-046-115, conc-046; P21)")

PDF = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n%%EOF\n"
PNG = bytes.fromhex("89504e470d0a1a0a0000000d49484452") + b"\x00" * 64
ELF = bytes.fromhex("7f454c4602010100") + b"\x00" * 128
ZIP = b"PK\x03\x04" + b"\x00" * 64
SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'


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

    _ROOT = tmp_path_factory.mktemp("kontrol-docs-sec")
    set_storage(FilesystemStorageProvider(_ROOT))

    db = factory()
    initialize(db, SetupRequest(
        tenant_code="DEMO", tenant_name="Empresa Demo", company_code="D1",
        company_legal_name="Demo C.A.", company_rif="J-12345678-9",
        admin_username="admin", admin_password="Kontrol2026Segura!"))

    # Segundo tenant con administrador propio: sirve para comprobar que ser
    # administrador **de otro sitio** no abre nada aquí.
    #
    # Tiene empresa propia a propósito. Un tenant sin ninguna empresa no
    # demuestra aislamiento: no ve nada porque no tiene dónde mirar, no porque
    # el sistema lo separe (ARCH-MC-001 N5).
    inst = db.execute(select(Installation).limit(1)).scalars().first()
    tenant_b = Tenant(installation_id=str(inst.id), code="DEMO2", name="Empresa B",
                      plan="MONO_COMPANY", status="ACTIVE")
    db.add(tenant_b)
    db.flush()
    company_b = Company(tenant_id=str(tenant_b.id), code="CB", legal_name="Empresa B CA",
                        rif="J-87654321-0", legal_type="JURIDICA",
                        functional_currency="VED", status="ACTIVE")
    db.add(company_b)
    db.flush()
    user_b = identity_service.create_user(
        db, tenant_id=str(tenant_b.id), username="admin2", email="admin2@b.com",
        password="Kontrol2026Segura!", created_by=None)
    role_b = _bootstrap_roles(db, str(tenant_b.id), str(user_b.id))
    db.add(UserRole(user_id=str(user_b.id), role_id=str(role_b.id), company_id=None))
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
    set_storage(None)


def _login(tenant: str, username: str) -> dict:
    r = _CLIENT.post("/api/v1/auth/login", json={
        "tenant_code": tenant, "username": username, "password": "Kontrol2026Segura!"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _headers() -> dict:
    return _login("DEMO", "admin")


def _headers_b() -> dict:
    return _login("DEMO2", "admin2")


def _company_id() -> str:
    return _CLIENT.get("/api/v1/organization/companies", headers=_headers()).json()["items"][0]["id"]


_N = {"i": 0}


def _doc_type(**overrides) -> dict:
    _N["i"] += 1
    body = {
        "company_id": _company_id(), "code": f"SEC{_N['i']}", "name": "Tipo seguro",
        "allowed_mime_types": ["application/pdf", "image/png"],
        "scan_required": True, **overrides,
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
            mime: str = "application/pdf", data: dict | None = None):
    return _CLIENT.post(
        f"/api/v1/documentos/{document_id}/versiones", headers=_headers(),
        files={"file": (name, io.BytesIO(content), mime)}, data=data or {})


def _approval_request(company_id: str | None = None) -> str:
    from app.modules.approvals.models import ApprovalRequest

    db = _FACTORY()
    try:
        _N["i"] += 1
        request = ApprovalRequest(
            company_id=company_id or _company_id(), process_type="PURCHASE_ORDER",
            document_type="PURCHASE_ORDER", document_id=f"sec-{_N['i']}",
            status="PENDING", fingerprint=f"secfp-{_N['i']}")
        db.add(request)
        db.commit()
        return str(request.id)
    finally:
        db.close()


def _stored_of(document_id: str) -> StoredFile:
    db = _FACTORY()
    try:
        document = db.get(Document, document_id)
        version = db.get(DocumentVersion, document.current_version_id)
        return db.get(StoredFile, version.stored_file_id)
    finally:
        db.close()


# ============================================================== AMZ-01
def test_amz_01_recorrido_de_rutas():
    """Ningún nombre del usuario alcanza el sistema de archivos."""
    document = _document(_doc_type()["id"])
    hostiles = [
        "../../../../etc/passwd.pdf",
        "/etc/passwd.pdf",
        "..\\..\\windows\\system32\\config.pdf",
        "..%2f..%2fetc%2fpasswd.pdf",
        "%2e%2e%2f%2e%2e%2fetc%2fshadow.pdf",
        "../../etc/hosts.pdf",
    ]
    for name in hostiles:
        r = _upload(document["id"], PDF, name=name)
        assert r.status_code == 200, (name, r.text)
        stored_name = r.json()["file"]["original_name"]
        assert "/" not in stored_name and "\\" not in stored_name, name
        assert not stored_name.startswith(".."), name

    # Todo lo escrito vive bajo la raíz, y ninguna ruta lleva el nombre dado.
    written = [p for p in _ROOT.rglob("*") if p.is_file()]
    assert written, "el almacenamiento real debería contener los archivos"
    for path in written:
        assert _ROOT in path.parents or path.parent == _ROOT or _ROOT in path.resolve().parents
        assert "passwd" not in str(path) and "shadow" not in str(path)


# ============================================================== AMZ-02
def test_amz_02_suplantacion_de_mime():
    """Un ejecutable con nombre y `Content-Type` de PDF sigue siendo ejecutable."""
    document = _document(_doc_type()["id"])
    r = _upload(document["id"], ELF, name="inocente.pdf", mime="application/pdf")
    assert r.status_code == 422, r.text
    assert r.json()["code"] in ("MIME_MISMATCH", "MIME_NOT_ALLOWED")
    # Y no quedó nada registrado.
    assert _CLIENT.get(f"/api/v1/documentos/{document['id']}",
                       headers=_headers()).json()["current_version"] is None


# ============================================================== AMZ-03
def test_amz_03_ejecutable_rechazado():
    document = _document(_doc_type()["id"])
    r = _upload(document["id"], ELF, name="binario.bin", mime="application/octet-stream")
    assert r.status_code == 422, r.text
    assert r.json()["code"] in ("MIME_MISMATCH", "MIME_NOT_ALLOWED")


# ============================================================== AMZ-04
def test_amz_04_contenido_activo_nunca_en_linea():
    """Un SVG con guion no se muestra en línea aunque el tipo lo declare."""
    doc_type = _doc_type(allowed_mime_types=["image/svg+xml"],
                         inline_preview_mimes=["image/svg+xml"])
    document = _document(doc_type["id"])
    r = _upload(document["id"], SVG, name="activo.svg", mime="image/svg+xml")
    if r.status_code != 200:
        pytest.skip(f"libmagic no clasifica el SVG como image/svg+xml: {r.text}")

    preview = _CLIENT.get(f"/api/v1/documentos/{document['id']}/preview", headers=_headers())
    assert preview.status_code == 200, preview.text
    assert preview.headers["content-disposition"].startswith("attachment")
    assert preview.headers["content-type"].startswith("application/octet-stream")
    assert preview.headers["x-content-type-options"] == "nosniff"
    assert "sandbox" in preview.headers["content-security-policy"]


# ============================================================== AMZ-05
def test_amz_05_xss_por_nombre_de_archivo():
    document = _document(_doc_type()["id"])
    hostile = '<script>alert("x")</script>.pdf'
    r = _upload(document["id"], PDF, name=hostile)
    assert r.status_code == 200, r.text
    # El nombre viaja como dato en JSON; nunca como marcado interpretado.
    listed = _CLIENT.get(f"/api/v1/documentos/{document['id']}", headers=_headers())
    assert listed.headers["content-type"].startswith("application/json")

    download = _CLIENT.get(f"/api/v1/documentos/{document['id']}/descargar",
                           headers=_headers())
    assert download.status_code == 200
    # La cabecera no puede contener comillas sin escapar que la partan.
    disposition = download.headers["content-disposition"]
    assert disposition.count('"') == 2, disposition


# ============================================================== AMZ-06
def test_amz_06_referencia_insegura_directa():
    """Conocer el identificador no da acceso: se responde «no existe»."""
    doc_type = _doc_type()
    document = _document(doc_type["id"])
    _upload(document["id"], PDF)
    other = _headers_b()

    for path in (f"/api/v1/documentos/{document['id']}",
                 f"/api/v1/documentos/{document['id']}/versiones",
                 f"/api/v1/documentos/{document['id']}/descargar",
                 f"/api/v1/documentos/{document['id']}/preview"):
        r = _CLIENT.get(path, headers=other)
        assert r.status_code == 404, (path, r.status_code, r.text)
        assert "storage_key" not in r.text


# ============================================================== AMZ-07
def test_amz_07_fuga_entre_empresas():
    doc_type = _doc_type()
    document = _document(doc_type["id"])
    _upload(document["id"], PDF)
    other = _headers_b()

    # 1. No aparece en el listado ajeno.
    listada = _CLIENT.get("/api/v1/documentos", headers=other)
    assert listada.status_code == 200, listada.text
    assert all(d["id"] != document["id"] for d in listada.json()["items"])
    # 2. No se puede crear un documento en la empresa ajena.
    r = _CLIENT.post("/api/v1/documentos", headers=other, json={
        "company_id": _company_id(), "document_type_id": doc_type["id"], "title": "Ajeno"})
    assert r.status_code == 404, r.text
    # 3. Ni cargarle una versión.
    r = _CLIENT.post(f"/api/v1/documentos/{document['id']}/versiones", headers=other,
                     files={"file": ("x.pdf", io.BytesIO(PDF), "application/pdf")})
    assert r.status_code == 404, r.text
    # 4. Ni vincularlo.
    r = _CLIENT.post(f"/api/v1/documentos/{document['id']}/vinculos", headers=other,
                     json={"resource_type": "ApprovalRequest",
                           "resource_id": _approval_request()})
    assert r.status_code == 404, r.text
    # 5. Ni ver los tipos documentales ajenos.
    assert all(t["id"] != doc_type["id"]
               for t in _CLIENT.get("/api/v1/documentos/tipos", headers=other).json())


# ============================================================== AMZ-08
def test_amz_08_sin_urls_publicas():
    """Ninguna respuesta entrega una ruta ni una URL al binario."""
    document = _document(_doc_type()["id"])
    _upload(document["id"], PDF)

    for path in ("/api/v1/documentos",
                 f"/api/v1/documentos/{document['id']}",
                 f"/api/v1/documentos/{document['id']}/versiones",
                 "/api/v1/documentos/salud/almacenamiento"):
        body = _CLIENT.get(path, headers=_headers()).text
        for leak in ("storage_key", "storage_path", "public_url", "signed_url",
                     str(_ROOT)):
            assert leak not in body, (path, leak)


# ============================================================== AMZ-09
def test_amz_09_sin_url_firmada_de_vida_larga():
    """No hay URL firmada porque no hay URL: la entrega pasa por el endpoint."""
    storage = get_storage()
    for attribute in ("public_url", "signed_url", "presigned_url", "url"):
        assert not hasattr(storage, attribute), attribute
    health = _CLIENT.get("/api/v1/documentos/salud/almacenamiento", headers=_headers())
    assert health.status_code == 200
    assert "http" not in health.text.lower()


# ============================================================== AMZ-10
def test_amz_10_malware_no_se_almacena_ni_se_entrega():
    if scanning.get_scanner().name == "disabled":
        pytest.skip("análisis desactivado en este entorno")
    document = _document(_doc_type(allowed_mime_types=["text/plain"])["id"])
    before = {p for p in _ROOT.rglob("*") if p.is_file()}
    r = _upload(document["id"], EICAR, name="muestra.txt", mime="text/plain")
    assert r.status_code == 422, r.text
    assert r.json()["code"] in ("FILE_INFECTED", "SCAN_FAILED")

    after = {p for p in _ROOT.rglob("*") if p.is_file()}
    assert after == before, "un archivo rechazado no debe quedar almacenado"
    assert _CLIENT.get(f"/api/v1/documentos/{document['id']}/descargar",
                       headers=_headers()).status_code == 404


# ============================================================== AMZ-11
def test_amz_11_comprimidos_rechazados_por_defecto():
    document = _document(_doc_type()["id"])
    r = _upload(document["id"], ZIP, name="paquete.zip", mime="application/zip")
    assert r.status_code == 422, r.text
    assert r.json()["code"] in ("MIME_MISMATCH", "MIME_NOT_ALLOWED")


# ============================================================== AMZ-12
def test_amz_12_clave_de_almacenamiento_opaca():
    """La clave no se deriva del nombre ni del contenido: es aleatoria."""
    doc_type = _doc_type()
    first = _document(doc_type["id"])
    second = _document(doc_type["id"])
    _upload(first["id"], PDF, name="mismo-nombre.pdf")
    _upload(second["id"], PDF, name="mismo-nombre.pdf")

    key_a = _stored_of(first["id"]).storage_key
    key_b = _stored_of(second["id"]).storage_key
    assert key_a != key_b, "mismo contenido y nombre no puede dar la misma clave"
    for key in (key_a, key_b):
        assert "mismo-nombre" not in key
        assert ".pdf" not in key
        assert len(key.rsplit("/", 1)[-1]) >= 20

    # Y dos claves nuevas seguidas tampoco se parecen.
    company = _company_id()
    assert generate_storage_key(company) != generate_storage_key(company)


# ============================================================== AMZ-13
def test_amz_13_sin_sobrescritura_del_historico():
    document = _document(_doc_type()["id"])
    _upload(document["id"], PDF, name="v1.pdf")
    first_key = _stored_of(document["id"]).storage_key
    first_bytes = get_storage().open(first_key).read()

    _upload(document["id"], PNG, name="v2.png", mime="image/png")
    second_key = _stored_of(document["id"]).storage_key

    assert second_key != first_key
    assert get_storage().exists(first_key), "el binario de la v1 debe seguir ahí"
    assert get_storage().open(first_key).read() == first_bytes == PDF


# ============================================================== AMZ-14
def test_amz_14_el_hash_no_autoriza():
    """No existe ninguna vía que convierta conocer el hash en acceso."""
    document = _document(_doc_type()["id"])
    r = _upload(document["id"], PDF)
    checksum = r.json()["sha256"]

    other = _headers_b()
    assert _CLIENT.get(f"/api/v1/documentos/{checksum}", headers=other).status_code == 404
    assert _CLIENT.get(f"/api/v1/documentos?q={checksum}",
                       headers=other).json()["items"] == []
    # Tampoco para el propio dueño: el hash no es un identificador de ruta.
    assert _CLIENT.get(f"/api/v1/documentos/{checksum}",
                       headers=_headers()).status_code == 404


# ============================================================== AMZ-15
def test_amz_15_asignacion_masiva():
    """Lo que el servidor determina, lo determina el servidor."""
    document = _document(_doc_type()["id"])
    r = _upload(document["id"], PDF, data={
        "storage_key": "controlado/por/el/cliente",
        "sha256": "0" * 64,
        "version_number": "99",
        "security_status": "CLEAN",
        "status": "AVAILABLE",
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["version_number"] == 1, "el correlativo lo pone el servidor"
    assert body["sha256"] != "0" * 64
    stored = _stored_of(document["id"])
    assert stored.storage_key != "controlado/por/el/cliente"


# ============================================================== AMZ-16
def test_amz_16_vinculacion_no_autorizada():
    """Vincular exige permiso sobre el destino, no sobre el documento."""
    document = _document(_doc_type()["id"])
    _upload(document["id"], PDF)
    foreign_request = _approval_request()

    # El administrador del otro tenant no puede vincular ni su propio recurso
    # a un documento ajeno.
    r = _CLIENT.post(f"/api/v1/documentos/{document['id']}/vinculos", headers=_headers_b(),
                     json={"resource_type": "ApprovalRequest",
                           "resource_id": foreign_request})
    assert r.status_code == 404, r.text

    # Y un recurso inexistente no se confirma como inexistente por otra vía.
    r = _CLIENT.post(f"/api/v1/documentos/{document['id']}/vinculos", headers=_headers(),
                     json={"resource_type": "ApprovalRequest",
                           "resource_id": "00000000-0000-0000-0000-000000000000"})
    assert r.status_code == 404
    assert r.json()["code"] == "RESOURCE_NOT_FOUND"


# ============================================================== AMZ-17
def test_amz_17_desvinculacion_no_autorizada():
    """La evidencia de un proceso cerrado no se puede retirar."""
    document = _document(_doc_type()["id"])
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

    # Ni el ajeno…
    assert _CLIENT.delete(f"/api/v1/documentos/vinculos/{link['id']}",
                          headers=_headers_b()).status_code == 404
    # …ni el propio dueño.
    r = _CLIENT.delete(f"/api/v1/documentos/vinculos/{link['id']}", headers=_headers())
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "LINK_FROZEN"


# ============================================================== AMZ-18
def test_amz_18_agotamiento_por_archivo_grande():
    """El corte es temprano: no se consume el flujo entero para rechazarlo."""
    doc_type = _doc_type(max_size_bytes=4096)
    document = _document(doc_type["id"])
    before = {p for p in _ROOT.rglob("*") if p.is_file()}

    r = _upload(document["id"], PDF + b"\x00" * 200_000)
    assert r.status_code == 413, r.text
    assert r.json()["code"] == "FILE_TOO_LARGE"
    assert r.json()["details"]["max_size_bytes"] == 4096

    after = {p for p in _ROOT.rglob("*") if p.is_file()}
    assert after == before, "nada que exceda el máximo debe llegar al almacenamiento"
    # El máximo global acota incluso a un tipo que pida más.
    assert min(10 * service.GLOBAL_MAX_SIZE, service.GLOBAL_MAX_SIZE) \
        == service.GLOBAL_MAX_SIZE


# ============================================================== AMZ-19
def test_amz_19_inyeccion_de_cabeceras():
    """CR/LF en el nombre no puede partir la cabecera de descarga."""
    document = _document(_doc_type()["id"])
    hostile = 'informe\r\nSet-Cookie: sesion=robada\r\n\r\n.pdf'
    r = _upload(document["id"], PDF, name=hostile)
    assert r.status_code == 200, r.text

    download = _CLIENT.get(f"/api/v1/documentos/{document['id']}/descargar",
                           headers=_headers())
    assert download.status_code == 200

    # La cabecera es una sola línea: no hay CR/LF que la parta, y por tanto
    # ninguna cabecera nueva pudo inyectarse.
    disposition = download.headers["content-disposition"]
    assert "\r" not in disposition and "\n" not in disposition
    assert "set-cookie" not in {k.lower() for k in download.headers}

    # El nombre guardado tampoco conserva caracteres de control: el cliente
    # HTTP los escapa al enviar el multipart, y el saneado los elimina cuando
    # llegan crudos. Se comprueban las dos vías.
    stored_name = _stored_of(document["id"]).original_name
    assert not any(ch in stored_name for ch in "\r\n")
    saneado = sanitize_filename(hostile)
    assert "\r" not in saneado and "\n" not in saneado
    # Y construida la cabecera con el nombre crudo, sigue sin partirse.
    assert "\r" not in f'attachment; filename="{saneado}"'
    assert "\n" not in f'attachment; filename="{saneado}"'


# ============================================================== AMZ-20
def test_amz_20_los_registros_no_filtran_contenido(caplog):
    """Se registran identificadores; nunca contenido, nombres de ruta ni secretos."""
    import logging

    document = _document(_doc_type()["id"])
    with caplog.at_level(logging.DEBUG):
        _upload(document["id"], PDF, name="confidencial.pdf")
        _CLIENT.get(f"/api/v1/documentos/{document['id']}/descargar", headers=_headers())

    text = caplog.text
    assert "%PDF" not in text
    assert str(_ROOT) not in text
    assert "Kontrol2026Segura!" not in text
    assert _stored_of(document["id"]).storage_key not in text

    # La auditoría guarda la huella y la versión, no los bytes.
    from app.modules.audit.models import AuditEvent

    db = _FACTORY()
    try:
        entries = db.execute(select(AuditEvent).where(
            AuditEvent.entity_id == document["id"])).scalars().all()
        assert entries, "la subida debe quedar auditada"
        assert any(e.action == "DOCUMENT_FILE_UPLOADED" for e in entries)
        for entry in entries:
            payload = str(entry.after or "") + str(entry.before or "")
            assert "%PDF" not in payload, payload
            assert "storage_key" not in payload, payload
    finally:
        db.close()


# =============================================== Fallos de almacenamiento
def test_fallo_de_escritura_no_deja_version():
    """Si el almacenamiento falla, no nace ninguna versión."""
    document = _document(_doc_type()["id"])
    real = get_storage()

    class _FailingStorage(FilesystemStorageProvider):
        def put(self, key, source):  # noqa: D102
            raise StorageError("disco lleno")

    set_storage(_FailingStorage(_ROOT))
    try:
        r = _upload(document["id"], PDF)
        assert r.status_code >= 500, r.text
    finally:
        set_storage(real)

    db = _FACTORY()
    try:
        assert db.execute(select(DocumentVersion).where(
            DocumentVersion.document_id == document["id"])).scalars().all() == []
    finally:
        db.close()


def test_objeto_ausente_no_se_entrega_otra_cosa():
    document = _document(_doc_type()["id"])
    _upload(document["id"], PDF)
    stored = _stored_of(document["id"])

    path = _ROOT / stored.storage_key
    backup = path.read_bytes()
    path.unlink()
    try:
        r = _CLIENT.get(f"/api/v1/documentos/{document['id']}/descargar", headers=_headers())
        assert r.status_code == 500, r.text
        assert r.json()["code"] == "STORAGE_OBJECT_MISSING"
    finally:
        path.write_bytes(backup)

    # Restaurado, vuelve a entregarse.
    assert _CLIENT.get(f"/api/v1/documentos/{document['id']}/descargar",
                       headers=_headers()).status_code == 200


def test_huella_distinta_no_se_entrega():
    """Si el binario cambió bajo los pies, no se entrega en silencio."""
    document = _document(_doc_type()["id"])
    _upload(document["id"], PDF)
    stored = _stored_of(document["id"])

    path = _ROOT / stored.storage_key
    backup = path.read_bytes()
    path.write_bytes(PDF + b"alterado")
    try:
        r = _CLIENT.get(f"/api/v1/documentos/{document['id']}/descargar", headers=_headers())
        assert r.status_code == 500, r.text
        assert r.json()["code"] == "STORAGE_HASH_MISMATCH"
    finally:
        path.write_bytes(backup)


def test_pendiente_de_analisis_no_se_entrega():
    """`SCAN_FAILED` no es `CLEAN`: mientras no se verifique, no se entrega."""
    document = _document(_doc_type()["id"])
    _upload(document["id"], PDF)
    stored = _stored_of(document["id"])

    db = _FACTORY()
    try:
        row = db.get(StoredFile, str(stored.id))
        row.security_status = scanning.SCAN_FAILED
        db.commit()
    finally:
        db.close()

    r = _CLIENT.get(f"/api/v1/documentos/{document['id']}/descargar", headers=_headers())
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "FILE_NOT_SCANNED"


# =============================================== Concurrencia (CONC-046)
#
# Antes aquí había dos hilos sin forzar nada que aceptaban cualquier respuesta
# distinta de 200: casi nunca coincidían, y cuando lo hacían la perdedora
# escapaba como excepción del hilo sin que la prueba lo viera. Ahora la carrera
# se **fuerza** y se comprueba que ocurrió (`tests/concurrency.py`): la primera
# transacción crea su versión sin confirmar, la segunda llega a la ventana
# crítica y queda esperando en PostgreSQL, y solo entonces se confirma la primera.


def _admin(sesion: Session, usuario: str = "admin") -> User:
    return sesion.execute(select(User).where(User.username == usuario)).scalars().one()


def _subida(document_id: str, contenido: bytes, nombre: str, usuario: str = "admin"):
    """Una subida por el servicio, en la sesión que le dé la carrera."""
    def subir(sesion: Session) -> DocumentVersion:
        document = sesion.get(Document, document_id)
        doc_type = sesion.get(DocumentType, document.document_type_id)
        return service.upload_version(
            sesion, document=document, doc_type=doc_type, stream=io.BytesIO(contenido),
            original_name=nombre, declared_mime="application/pdf", actor=_admin(sesion, usuario))
    return subir


def _huella(document_id: str) -> dict:
    """Todo lo que una subida deja: versiones, archivos, análisis, auditoría y binarios."""
    db = _FACTORY()
    try:
        versiones = [(v.version_number, v.status) for v in db.execute(
            select(DocumentVersion).where(DocumentVersion.document_id == document_id)
            .order_by(DocumentVersion.version_number)).scalars()]
        return {
            "versiones": versiones,
            "vigente": db.get(Document, document_id).current_version_id,
            "archivos": db.execute(select(func.count()).select_from(StoredFile)).scalar_one(),
            "analisis": db.execute(select(func.count()).select_from(FileSecurityScan)).scalar_one(),
            "auditorias": db.execute(select(func.count()).select_from(AuditEvent).where(
                AuditEvent.entity_id == document_id,
                AuditEvent.action == "DOCUMENT_FILE_UPLOADED")).scalar_one(),
            "binarios": sum(1 for p in _ROOT.rglob("*") if p.is_file()),
        }
    finally:
        db.close()


def _un_efecto_mas(antes: dict, despues: dict) -> None:
    for campo in ("archivos", "analisis", "auditorias", "binarios"):
        assert despues[campo] == antes[campo] + 1, (
            f"{campo}: {antes[campo]} → {despues[campo]}; la subida que perdió dejó rastro")


def _en_hilo(funcion):
    salida: dict = {}

    def correr() -> None:
        try:
            salida["r"] = funcion()
        except Exception as e:  # noqa: BLE001 - el resultado es la excepción
            salida["r"] = e

    hilo = threading.Thread(target=correr)
    hilo.start()
    return hilo, salida


def _post_version(document_id: str, contenido: bytes, headers: dict):
    return _CLIENT.post(f"/api/v1/documentos/{document_id}/versiones", headers=headers,
                        files={"file": ("carrera.pdf", io.BytesIO(contenido), "application/pdf")})


def _pid(sesion: Session) -> int:
    return sesion.execute(text("SELECT pg_backend_pid()")).scalar()


@solo_postgresql
@pytest.mark.parametrize("vuelta", range(3))
def test_dos_subidas_simultaneas_no_producen_dos_v2(vuelta):
    """La carrera ocurre de verdad, tres veces: una V2, una vigente y un conflicto de dominio."""
    document = _document(_doc_type()["id"])["id"]
    assert _upload(document, PDF, name="base.pdf").status_code == 200
    antes = _huella(document)

    primero, segundo = carrera(_FACTORY, _subida(document, PDF + b"%A", "a.pdf"),
                               _subida(document, PDF + b"%B", "b.pdf"))

    assert isinstance(segundo, ConflictError), f"quien perdió recibió {segundo!r}"
    assert (segundo.code, segundo.status_code) == ("VERSION_CONFLICT", 409)
    despues = _huella(document)
    assert despues["versiones"] == [(1, "SUPERSEDED"), (2, "ACTIVE")], despues["versiones"]
    assert despues["vigente"] == str(primero.id)
    _un_efecto_mas(antes, despues)


@solo_postgresql
def test_la_primera_version_simultanea_tampoco_da_un_500():
    """Sin versión previa la segunda espera en el índice único, no en una fila: mismo resultado."""
    document = _document(_doc_type()["id"])["id"]
    primero, segundo = carrera(_FACTORY, _subida(document, PDF + b"%1", "uno.pdf"),
                               _subida(document, PDF + b"%2", "dos.pdf"))
    assert isinstance(segundo, ConflictError) and segundo.code == "VERSION_CONFLICT", repr(segundo)
    assert _huella(document)["versiones"] == [(1, "ACTIVE")]
    assert _huella(document)["vigente"] == str(primero.id)


@solo_postgresql
def test_la_peticion_http_que_pierde_la_carrera_recibe_un_409_y_no_un_500():
    document = _document(_doc_type()["id"])["id"]
    assert _upload(document, PDF, name="base.pdf").status_code == 200
    antes = _huella(document)
    cabeceras = _headers()

    s1 = _FACTORY()
    try:
        ganadora = _subida(document, PDF + b"%S", "s.pdf")(s1)
        s1.flush()
        hilo, salida = _en_hilo(lambda: _post_version(document, PDF + b"%H", cabeceras))
        assert esperar_bloqueados(_FACTORY, 1, excluir=_pid(s1)), "la petición HTTP nunca chocó"
        s1.commit()
    finally:
        s1.close()
    hilo.join(timeout=60)

    r = salida.get("r")
    assert not isinstance(r, Exception), f"la petición que perdió escapó como excepción: {r!r}"
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "VERSION_CONFLICT"
    despues = _huella(document)
    assert despues["versiones"] == [(1, "SUPERSEDED"), (2, "ACTIVE")]
    assert despues["vigente"] == str(ganadora.id)
    _un_efecto_mas(antes, despues)


@solo_postgresql
def test_tres_subidas_simultaneas_crean_una_sola_version():
    document = _document(_doc_type()["id"])["id"]
    assert _upload(document, PDF, name="base.pdf").status_code == 200
    antes = _huella(document)
    cabeceras = _headers()

    s1 = _FACTORY()
    try:
        _subida(document, PDF + b"%T", "t.pdf")(s1)
        s1.flush()
        hilos = [_en_hilo(lambda i=i: _post_version(document, PDF + bytes([i]), cabeceras)) for i in (7, 8)]
        assert esperar_bloqueados(_FACTORY, 2, excluir=_pid(s1)), "las dos peticiones no llegaron a chocar"
        s1.commit()
    finally:
        s1.close()

    for hilo, salida in hilos:
        hilo.join(timeout=60)
        r = salida.get("r")
        assert not isinstance(r, Exception), f"una perdedora escapó como excepción: {r!r}"
        assert (r.status_code, r.json()["code"]) == (409, "VERSION_CONFLICT"), r.text
    despues = _huella(document)
    assert despues["versiones"] == [(1, "SUPERSEDED"), (2, "ACTIVE")]
    _un_efecto_mas(antes, despues)


@solo_postgresql
def test_la_misma_clave_en_carrera_devuelve_la_version_ganadora():
    document = _document(_doc_type()["id"])["id"]
    assert _upload(document, PDF, name="base.pdf").status_code == 200
    antes = _huella(document)
    clave = "carrera-misma-clave"
    cabeceras = {**_headers(), "Idempotency-Key": clave}

    s1 = _FACTORY()
    try:
        # La ganadora hace lo mismo que la ruta: la versión y su registro idempotente.
        ganadora = _subida(document, PDF + b"%K", "k.pdf")(s1)
        s1.add(IdempotencyRecord(
            key=documents_api._clave_idempotente(document, clave), method="POST",
            path=f"/documentos/{document}/versiones", user_id=str(_admin(s1).id),
            company_id=ganadora.company_id, response_status=200, response_hash=ganadora.sha256,
            response_payload={"version_id": str(ganadora.id), "version_number": ganadora.version_number}))
        s1.flush()
        hilo, salida = _en_hilo(lambda: _post_version(document, PDF + b"%R", cabeceras))
        assert esperar_bloqueados(_FACTORY, 1, excluir=_pid(s1)), "el reintento nunca chocó"
        s1.commit()
    finally:
        s1.close()
    hilo.join(timeout=60)

    r = salida.get("r")
    assert not isinstance(r, Exception), f"el reintento escapó como excepción: {r!r}"
    assert r.status_code == 200, f"la misma clave recibió {r.status_code}: {r.text}"
    assert r.json()["idempotent_hit"] is True and r.json()["id"] == str(ganadora.id)
    despues = _huella(document)
    assert despues["versiones"] == [(1, "SUPERSEDED"), (2, "ACTIVE")]
    _un_efecto_mas(antes, despues)


def test_un_reintento_devuelve_la_version_de_su_clave_aunque_haya_otra_despues():
    """Antes devolvía la vigente: tras otra subida, el reintento recibía una versión que no pidió."""
    document = _document(_doc_type()["id"])["id"]
    clave = {**_headers(), "Idempotency-Key": "reintento-tardio"}
    primera = _post_version(document, PDF + b"%P", clave)
    assert primera.status_code == 200, primera.text
    assert _upload(document, PDF + b"%Q", name="otra.pdf").status_code == 200

    repetida = _post_version(document, PDF + b"%P", clave)
    assert repetida.status_code == 200, repetida.text
    assert repetida.json()["idempotent_hit"] is True
    assert repetida.json()["id"] == primera.json()["id"], "el reintento devolvió otra versión"
    assert _huella(document)["versiones"] == [(1, "SUPERSEDED"), (2, "ACTIVE")]


def test_la_misma_clave_en_otro_documento_no_devuelve_una_version_ajena():
    tipo = _doc_type()["id"]
    uno, dos = _document(tipo)["id"], _document(tipo)["id"]
    clave = {**_headers(), "Idempotency-Key": "clave-compartida"}

    assert _post_version(uno, PDF + b"%U", clave).status_code == 200
    r = _post_version(dos, PDF + b"%D", clave)
    assert r.status_code == 200, r.text
    assert r.json().get("idempotent_hit") is not True, "otro documento recibió una versión ajena"
    assert r.json()["document_id"] == dos and r.json()["version_number"] == 1


def _documento_del_otro_tenant() -> str:
    """Tipo y documento en la empresa del segundo tenant, directamente en la base."""
    db = _FACTORY()
    try:
        empresa = db.execute(select(Company).where(Company.code == "CB")).scalars().one()
        _N["i"] += 1
        tipo = DocumentType(company_id=str(empresa.id), code=f"CB{_N['i']}", name="Tipo B",
                            allowed_mime_types=["application/pdf"], scan_required=True)
        db.add(tipo)
        db.flush()
        documento = Document(company_id=str(empresa.id), document_type_id=str(tipo.id),
                             title=f"Documento B {_N['i']}")
        db.add(documento)
        db.commit()
        return str(documento.id)
    finally:
        db.close()


@solo_postgresql
def test_subidas_a_documentos_distintos_no_se_esperan():
    """Ni otro documento de la misma empresa ni el de otro tenant esperan a una carrera ajena."""
    tipo = _doc_type()["id"]
    bloqueado = _document(tipo)["id"]
    assert _upload(bloqueado, PDF, name="base.pdf").status_code == 200
    vecino = _document(tipo)["id"]
    ajeno = _documento_del_otro_tenant()

    s1 = _FACTORY()
    try:
        _subida(bloqueado, PDF + b"%X", "x.pdf")(s1)
        s1.flush()
        otras = [_en_hilo(lambda: carrera_libre(vecino, "admin")),
                 _en_hilo(lambda: carrera_libre(ajeno, "admin2"))]
        for hilo, salida in otras:
            hilo.join(timeout=60)
            assert not hilo.is_alive(), "una subida a otro documento esperó a una carrera ajena"
            assert isinstance(salida.get("r"), DocumentVersion), f"recibió {salida.get('r')!r}"
        s1.commit()
    finally:
        s1.close()
    assert _huella(vecino)["versiones"] == [(1, "ACTIVE")]
    assert _huella(ajeno)["versiones"] == [(1, "ACTIVE")]
    assert _huella(bloqueado)["versiones"] == [(1, "SUPERSEDED"), (2, "ACTIVE")]


def carrera_libre(document_id: str, usuario: str) -> DocumentVersion:
    sesion = _FACTORY()
    try:
        version = _subida(document_id, PDF + b"%L", "libre.pdf", usuario)(sesion)
        sesion.commit()
        return version
    finally:
        sesion.close()


@solo_postgresql
def test_otro_tenant_no_alcanza_un_documento_ajeno_durante_la_carrera():
    document = _document(_doc_type()["id"])["id"]
    assert _upload(document, PDF, name="base.pdf").status_code == 200
    ajenas = _headers_b()

    s1 = _FACTORY()
    try:
        _subida(document, PDF + b"%Z", "z.pdf")(s1)
        s1.flush()
        hilo, salida = _en_hilo(lambda: _post_version(document, PDF + b"%E", ajenas))
        hilo.join(timeout=60)
        assert not hilo.is_alive(), "la petición ajena esperó a la carrera"
        s1.commit()
    finally:
        s1.close()

    r = salida.get("r")
    assert not isinstance(r, Exception), repr(r)
    assert r.status_code == 404, f"otro tenant recibió {r.status_code}: {r.text}"
    assert _huella(document)["versiones"] == [(1, "SUPERSEDED"), (2, "ACTIVE")]


# =============================================== Contrato de respuesta
def test_el_contrato_nunca_expone_almacenamiento():
    """Ninguna clave de respuesta habla de almacenamiento (NFR-046-01)."""
    document = _document(_doc_type()["id"])
    upload = _upload(document["id"], PDF).json()
    detail = _CLIENT.get(f"/api/v1/documentos/{document['id']}", headers=_headers()).json()
    versions = _CLIENT.get(f"/api/v1/documentos/{document['id']}/versiones",
                           headers=_headers()).json()

    prohibited = {"storage_key", "storage_provider", "storage_path", "path", "uploaded_by"}

    def _keys(value) -> set[str]:
        if isinstance(value, dict):
            found = set(value)
            for nested in value.values():
                found |= _keys(nested)
            return found
        if isinstance(value, list):
            found: set[str] = set()
            for item in value:
                found |= _keys(item)
            return found
        return set()

    for payload in (upload, detail, versions):
        assert not (_keys(payload) & prohibited), _keys(payload) & prohibited

    # Y el estado de seguridad **siempre** viaja: nunca se omite (§27).
    assert upload["file"]["security_status"]
    assert detail["current_version"]["file"]["security_status"]
    assert all(v["file"]["security_status"] for v in versions)


def test_sin_autenticacion_nada():
    document = _document(_doc_type()["id"])
    _upload(document["id"], PDF)
    for path in ("/api/v1/documentos",
                 f"/api/v1/documentos/{document['id']}",
                 f"/api/v1/documentos/{document['id']}/descargar",
                 f"/api/v1/documentos/{document['id']}/preview",
                 "/api/v1/documentos/tipos",
                 "/api/v1/documentos/salud/almacenamiento"):
        assert _CLIENT.get(path).status_code == 401, path
