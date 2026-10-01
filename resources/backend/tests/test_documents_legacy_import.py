"""Importación del legado documental (Spec 046, FR-046-112/113, T-046-143/148).

Los cinco casos del fixture legado, cada uno con su desenlace:

1. Binario localizable y verificable → se importa.
2. Referencia externa (URL) → no es un archivo nuestro; no se importa.
3. Ruta que no lleva a ningún archivo → `MISSING_FILE`, **reportado, no inventado**.
4. Binario localizado cuya huella no coincide → `MIGRATION_BLOCKER`, se detiene.
5. Hash sin binario → sigue sin ser un documento.

En los cinco, la fuente heredada queda intacta: nada se borra antes de
verificar, y nada se borra después tampoco (§144).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base, get_db, init_models
from app.core.errors import ConflictError
from app.modules.documents import service
from app.modules.documents.models import (
    Document,
    DocumentType,
    LegacyDocumentReference,
    StoredFile,
)
from app.modules.documents.storage import FilesystemStorageProvider, set_storage
from app.modules.setup.api import SetupRequest, initialize
from tests.conftest import make_engine

_CLIENT: TestClient
_FACTORY: sessionmaker
_ROOT: Path
_LEGACY: Path

CONTENT = b"%PDF-1.4\nfactura heredada\ntrailer\n%%EOF\n"
CHECKSUM = hashlib.sha256(CONTENT).hexdigest()


@pytest.fixture(scope="module", autouse=True)
def _app_client(tmp_path_factory):
    global _CLIENT, _FACTORY, _ROOT, _LEGACY
    engine = make_engine()
    init_models()
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    import app.core.database as dm

    dm._engine = engine  # type: ignore[attr-defined]
    dm._SessionLocal = factory  # type: ignore[attr-defined]

    _ROOT = tmp_path_factory.mktemp("kontrol-docs-legacy")
    set_storage(FilesystemStorageProvider(_ROOT))

    # Volumen heredado: archivos donde los dejó el sistema anterior.
    _LEGACY = tmp_path_factory.mktemp("volumen-legado")
    (_LEGACY / "facturas" / "2023").mkdir(parents=True)
    (_LEGACY / "facturas" / "2023" / "F-0001.pdf").write_bytes(CONTENT)
    (_LEGACY / "facturas" / "2023" / "F-0002.pdf").write_bytes(b"otro contenido")

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
    r = _CLIENT.post("/api/v1/auth/login", json={
        "tenant_code": "DEMO", "username": "admin", "password": "Kontrol2026Segura!"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _company_id() -> str:
    return _CLIENT.get("/api/v1/organization/companies", headers=_headers()).json()["items"][0]["id"]


def _actor():
    from app.modules.identity_access.models import User

    db = _FACTORY()
    try:
        return db.query(User).first()
    finally:
        db.close()


_N = {"i": 0}


def _doc_type(db: Session) -> DocumentType:
    _N["i"] += 1
    doc_type = DocumentType(
        company_id=_company_id(), code=f"LEG{_N['i']}", name="Legado",
        allowed_mime_types=["application/pdf"], scan_required=False, status="ACTIVE")
    db.add(doc_type)
    db.flush()
    return doc_type


def _reference(db: Session, raw_value: str | None, classification="UNVERIFIED_LEGACY"):
    _N["i"] += 1
    reference = LegacyDocumentReference(
        source_table="supplier_invoices", source_column="file_ref",
        source_row_id=f"row-{_N['i']}", company_id=_company_id(),
        raw_value=raw_value, classification=classification,
        notes="Sembrada por la prueba")
    db.add(reference)
    db.flush()
    return reference


# --------------------------------------------------------------- caso 1
def test_binario_localizable_y_verificable_se_importa():
    db = _FACTORY()
    try:
        doc_type = _doc_type(db)
        reference = _reference(db, "facturas/2023/F-0001.pdf")
        document = service.import_legacy_reference(
            db, reference=reference, search_roots=[_LEGACY], doc_type=doc_type,
            actor=_actor(), expected_sha256=CHECKSUM)
        db.commit()

        assert document is not None
        assert reference.classification == "VALID_MANAGED_FILE"
        assert reference.document_id == str(document.id)

        version = db.get(Document, str(document.id)).current_version_id
        assert version is not None
        stored = db.query(StoredFile).filter(
            StoredFile.sha256 == CHECKSUM).one()
        assert stored.size == len(CONTENT)
        # El legado no pasó por el analizador de hoy: se declara, no se supone.
        assert stored.security_status == "PENDING_SCAN"

        # La fuente heredada sigue en su sitio, byte por byte.
        assert (_LEGACY / "facturas" / "2023" / "F-0001.pdf").read_bytes() == CONTENT
    finally:
        db.close()


def test_lo_importado_no_se_entrega_hasta_verificarse():
    """`PENDING_SCAN` no es `CLEAN`: importar no es dar por bueno."""
    db = _FACTORY()
    try:
        doc_type = _doc_type(db)
        reference = _reference(db, "facturas/2023/F-0001.pdf")
        document = service.import_legacy_reference(
            db, reference=reference, search_roots=[_LEGACY], doc_type=doc_type,
            actor=_actor())
        db.commit()
        document_id = str(document.id)
    finally:
        db.close()

    r = _CLIENT.get(f"/api/v1/documentos/{document_id}/descargar", headers=_headers())
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "FILE_NOT_SCANNED"


# --------------------------------------------------------------- caso 2
def test_una_url_externa_no_se_importa_como_archivo_propio():
    db = _FACTORY()
    try:
        doc_type = _doc_type(db)
        reference = _reference(db, "https://proveedor.example/facturas/F-9.pdf")
        document = service.import_legacy_reference(
            db, reference=reference, search_roots=[_LEGACY], doc_type=doc_type,
            actor=_actor())
        db.commit()
        assert document is None
        assert reference.document_id is None
        assert reference.classification == "MISSING_FILE"
        # El texto original permanece: la pista no se pierde.
        assert reference.raw_value == "https://proveedor.example/facturas/F-9.pdf"
    finally:
        db.close()


# --------------------------------------------------------------- caso 3
def test_un_archivo_que_no_esta_se_reporta_no_se_inventa():
    db = _FACTORY()
    try:
        doc_type = _doc_type(db)
        reference = _reference(db, "facturas/2019/F-INEXISTENTE.pdf")
        document = service.import_legacy_reference(
            db, reference=reference, search_roots=[_LEGACY], doc_type=doc_type,
            actor=_actor())
        db.commit()

        assert document is None
        assert reference.classification == "MISSING_FILE"
        assert reference.document_id is None
        assert "no localizado" in (reference.notes or "")
        assert reference.raw_value == "facturas/2019/F-INEXISTENTE.pdf"
    finally:
        db.close()


# --------------------------------------------------------------- caso 4
def test_una_huella_que_no_coincide_detiene_la_importacion():
    db = _FACTORY()
    try:
        doc_type = _doc_type(db)
        reference = _reference(db, "facturas/2023/F-0002.pdf")
        with pytest.raises(ConflictError) as excinfo:
            service.import_legacy_reference(
                db, reference=reference, search_roots=[_LEGACY], doc_type=doc_type,
                actor=_actor(), expected_sha256=CHECKSUM)
        assert excinfo.value.code == "LEGACY_HASH_MISMATCH"
        db.commit()

        assert reference.classification == "MIGRATION_BLOCKER"
        assert reference.document_id is None
        # Y el binario que no era no quedó almacenado.
        assert (_LEGACY / "facturas" / "2023" / "F-0002.pdf").read_bytes() == b"otro contenido"
    finally:
        db.close()


# --------------------------------------------------------------- caso 5
def test_un_hash_suelto_sigue_sin_ser_un_documento():
    db = _FACTORY()
    try:
        doc_type = _doc_type(db)
        reference = _reference(db, "9f" * 32, classification="LEGACY_HASH_WITHOUT_FILE")
        document = service.import_legacy_reference(
            db, reference=reference, search_roots=[_LEGACY], doc_type=doc_type,
            actor=_actor())
        db.commit()
        assert document is None
        assert reference.document_id is None
    finally:
        db.close()


# --------------------------------------------------------------- contención
def test_una_ruta_heredada_no_autoriza_a_salir_del_volumen():
    """`../../etc/passwd` en el legado no saca nada de la raíz autorizada."""
    db = _FACTORY()
    try:
        doc_type = _doc_type(db)
        reference = _reference(db, "../../../../etc/passwd")
        document = service.import_legacy_reference(
            db, reference=reference, search_roots=[_LEGACY], doc_type=doc_type,
            actor=_actor())
        db.commit()
        assert document is None
        assert reference.classification == "MISSING_FILE"
    finally:
        db.close()


def test_ninguna_importacion_borra_la_fuente():
    """Nada se borra: ni antes de verificar, ni después (§144)."""
    remaining = sorted(p.name for p in (_LEGACY / "facturas" / "2023").iterdir())
    assert remaining == ["F-0001.pdf", "F-0002.pdf"]
