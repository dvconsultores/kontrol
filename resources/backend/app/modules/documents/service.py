"""Servicio de gestión documental (Spec 046, F3-F5).

Aquí vive el valor de la Spec: el flujo de subida con sus controles, el
versionado, la vinculación autorizada y la congelación histórica.

El orden del flujo de subida no es casual (§13, §14): se escribe a un temporal,
se detecta el MIME real, se analiza, se calcula el hash y **solo entonces** se
confirma. Nunca se declara disponible algo que no puede recuperarse.
"""

from __future__ import annotations

import contextlib
import hashlib
import os
import tempfile
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, BinaryIO

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.core.integrity import es_violacion_unica
from app.modules.documents import resources as resource_registry
from app.modules.documents import scanning
from app.modules.documents.models import (
    Document,
    DocumentLink,
    DocumentType,
    DocumentVersion,
    FileSecurityScan,
    StoredFile,
)
from app.modules.documents.storage import (
    CHUNK,
    StorageError,
    generate_storage_key,
    get_storage,
    safe_extension,
    sanitize_filename,
)
from app.shared.audit import record_audit, record_audit_after_rollback
from app.shared.clock import hoy_de_negocio

#: Tamaño máximo global. Un tipo puede bajarlo, nunca subirlo por encima.
GLOBAL_MAX_SIZE = 50 * 1024 * 1024

#: MIME que **jamás** se muestran en línea, aunque un tipo los declare: pueden
#: llevar guion activo y se ejecutarían en contexto autenticado (§21, §84).
NEVER_INLINE = frozenset({
    "image/svg+xml", "text/html", "application/xhtml+xml", "application/xml",
    "text/xml", "application/x-shockwave-flash",
})

#: Familias siempre rechazadas salvo declaración explícita del tipo: ejecutables
#: y comprimidos (§50, §51).
DANGEROUS_MIME_PREFIXES = ("application/x-dosexec", "application/x-executable",
                           "application/x-mach-binary", "application/x-sharedlib")
DANGEROUS_MIME = frozenset({
    "application/x-msdownload", "application/vnd.microsoft.portable-executable",
    "application/x-elf", "application/octet-stream",
    "application/zip", "application/x-rar", "application/x-7z-compressed",
    "application/gzip", "application/x-tar", "application/java-archive",
})


def _now() -> datetime:
    return datetime.now(UTC)


def _audit(db: Session, actor: Any, action: str, entity_id: str,
           before: dict | None = None, after: dict | None = None, *,
           company_id: str) -> None:
    record_audit(db, action=action, entity_type="Document", entity_id=entity_id,
                 tenant_id=getattr(actor, "tenant_id", None),
                 user_id=str(getattr(actor, "id", "")) or None,
                 before=before, after=after, company_id=company_id)


# --------------------------------------------------------------------------
# Detección de MIME — no se cree al cliente (§19)
# --------------------------------------------------------------------------

def detect_mime(path: str) -> str:
    """MIME por contenido. Es lo único que decide, no la extensión."""
    try:
        import magic

        return magic.from_file(path, mime=True) or "application/octet-stream"
    except Exception:  # noqa: BLE001 — sin libmagic no se adivina: se rechaza
        return "application/octet-stream"


def _mime_allowed(doc_type: DocumentType, mime: str) -> bool:
    """Lista blanca del tipo. **Vacía significa ninguno**, no todos."""
    allowed = doc_type.allowed_mime_types or []
    return mime in allowed


def _extension_allowed(doc_type: DocumentType, extension: str | None) -> bool:
    allowed = doc_type.allowed_extensions or []
    if not allowed:
        return True          # sin restricción de extensión; el MIME manda
    return (extension or "") in allowed


def can_preview_inline(doc_type: DocumentType, mime: str) -> bool:
    """Solo en línea si el tipo lo declara **y** no es de los que nunca."""
    if mime in NEVER_INLINE:
        return False
    return mime in (doc_type.inline_preview_mimes or [])


# --------------------------------------------------------------------------
# Subida — el flujo con sus controles, en orden (§13)
# --------------------------------------------------------------------------

def upload_version(
    db: Session,
    *,
    document: Document,
    doc_type: DocumentType,
    stream: BinaryIO,
    original_name: str,
    declared_mime: str | None,
    actor: Any,
    replacement_reason: str | None = None,
) -> DocumentVersion:
    """Crea una versión a partir de un archivo.

    Orden obligatorio: temporal → tamaño → MIME real → política → análisis →
    hash → almacenamiento → verificación → confirmación. Un archivo solo llega
    a `AVAILABLE` cuando ha pasado **todos** los controles (§14).
    """
    if not document.is_managed:
        raise KontrolError(code="EXTERNAL_DOCUMENT_NO_FILE",
                           message="Un documento de referencia externa no admite archivos",
                           status_code=422)

    validate_metadata(doc_type, document.doc_metadata)

    max_size = min(doc_type.max_size_bytes or GLOBAL_MAX_SIZE, GLOBAL_MAX_SIZE)
    safe_name = sanitize_filename(original_name)
    extension = safe_extension(original_name)

    # 1. Temporal: nada se registra hasta pasar los controles.
    temp_dir = Path(tempfile.mkdtemp(prefix="kontrol-doc-"))
    temp_path = temp_dir / "upload.bin"
    digest = hashlib.sha256()
    size = 0
    try:
        with open(temp_path, "wb") as out:
            while True:
                chunk = stream.read(CHUNK)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_size:
                    # Corte temprano: no se consume el flujo completo (§30).
                    raise KontrolError(
                        code="FILE_TOO_LARGE",
                        message=f"El archivo supera el máximo permitido ({max_size} bytes)",
                        status_code=413,
                        details={"max_size_bytes": max_size})
                digest.update(chunk)
                out.write(chunk)
        if size == 0:
            raise KontrolError(code="FILE_EMPTY", message="El archivo está vacío",
                               status_code=422)

        # 2. MIME real, por contenido.
        detected = detect_mime(str(temp_path))

        # 3. Política del tipo.
        if not _mime_allowed(doc_type, detected):
            if declared_mime and declared_mime != detected and _mime_allowed(doc_type, declared_mime):
                # Dijo una cosa y es otra: suplantación (§20).
                raise KontrolError(
                    code="MIME_MISMATCH",
                    message="El contenido del archivo no corresponde con el tipo declarado",
                    status_code=422,
                    details={"declared": declared_mime, "detected": detected})
            raise KontrolError(
                code="MIME_NOT_ALLOWED",
                message=f"El tipo documental no admite archivos «{detected}»",
                status_code=422,
                details={"detected": detected,
                         "allowed": doc_type.allowed_mime_types or []})
        if not _extension_allowed(doc_type, extension):
            raise KontrolError(code="MIME_NOT_ALLOWED",
                               message="Extensión no admitida por el tipo documental",
                               status_code=422)
        if (detected in DANGEROUS_MIME or detected.startswith(DANGEROUS_MIME_PREFIXES)) \
                and detected not in (doc_type.allowed_mime_types or []):
            raise KontrolError(code="MIME_NOT_ALLOWED",
                               message="Tipo de archivo peligroso no admitido",
                               status_code=422, details={"detected": detected})

        # 4. Análisis. Falso seguro: sin analizador no hay limpieza (§26).
        scanner = scanning.get_scanner()
        scan = scanner.scan(str(temp_path))
        if doc_type.scan_required and scan.result != scanning.CLEAN:
            category, reason_code = scanning.clasificar_rechazo(scan)
            code = "FILE_INFECTED" if scan.result == scanning.INFECTED else "SCAN_FAILED"
            message = ("El archivo fue rechazado por seguridad: el análisis lo identificó como malicioso"
                       if scan.result == scanning.INFECTED
                       else "No se pudo verificar la seguridad del archivo")
            # OD-AUD-07: la carga rechazada se deshace y el rechazo se confirma
            # aparte, así sobrevive. OD-AUD-08/09: evidencia mínima, sin firma
            # ni contenido ni nombre original.
            evidencia = {
                "category": category,
                "reason_code": reason_code,
                "engine": scan.scanner,
                "engine_version": scanner.engine_version() or "unknown",
                "sha256": digest.hexdigest(),
                "size_bytes": size,
                "detected_mime": detected,
                "document_type_id": str(doc_type.id),
            }
            document_id = str(document.id)
            company_id = document.company_id
            tenant_id = getattr(actor, "tenant_id", None)
            user_id = str(getattr(actor, "id", "")) or None
            record_audit_after_rollback(
                db, action="DOCUMENT_SCAN_REJECTED", entity_type="Document",
                entity_id=document_id, company_id=company_id, tenant_id=tenant_id,
                user_id=user_id, reason=category, evidence=evidencia)
            raise KontrolError(code=code, message=message, status_code=422,
                               details={"scan_result": scan.result,
                                        "category": category})

        checksum = digest.hexdigest()

        # 5. Almacenamiento, con clave opaca del servidor.
        storage = get_storage()
        key = generate_storage_key(document.company_id)
        with open(temp_path, "rb") as source:
            stored_size, stored_hash = storage.put(key, source)

        # 6. Verificación: «escribí» no es «está y es el que era».
        if stored_hash != checksum or stored_size != size:
            storage.delete(key)
            raise KontrolError(code="STORAGE_FAILURE",
                               message="La verificación de integridad falló tras escribir",
                               status_code=503)
        if not storage.verify(key, checksum):
            storage.delete(key)
            raise KontrolError(code="STORAGE_FAILURE",
                               message="El archivo no pudo verificarse en el almacenamiento",
                               status_code=503)
    finally:
        temp_path.unlink(missing_ok=True)
        temp_dir.rmdir()

    # 7. Confirmación en base. Si algo falla aquí, la transacción revierte y
    #    queda un binario huérfano: basura recuperable, no evidencia perdida.
    stored = StoredFile(
        company_id=document.company_id, original_name=safe_name,
        mime_type=detected, declared_mime=declared_mime, detected_mime=detected,
        extension=extension, size=size, sha256=checksum, storage_key=key,
        storage_provider=storage.name,
        security_status=scan.result, status="AVAILABLE",
        uploaded_by=str(getattr(actor, "id", "")) or None, uploaded_at=_now())
    db.add(stored)
    db.flush()

    db.add(FileSecurityScan(stored_file_id=str(stored.id), scanner=scan.scanner,
                            result=scan.result, signature=scan.signature,
                            details=scan.details, scanned_at=_now()))

    # Otro archivo con la misma huella: se **registra**, no se bloquea ni se
    # deduplica. Dos procesos distintos pueden legítimamente adjuntar el mismo
    # PDF, y unificarlos convertiría una evidencia en dos referencias a una
    # sola (FR-046-049, AC-046-36).
    twins = db.execute(select(func.count()).select_from(StoredFile).where(
        StoredFile.sha256 == checksum, StoredFile.company_id == document.company_id,
        StoredFile.id != str(stored.id))).scalar_one()
    if twins:
        _audit(db, actor, "DOCUMENT_HASH_COINCIDENCE", str(document.id),
               after={"sha256": checksum, "existing_files": int(twins)},
               company_id=document.company_id)

    try:
        version = _create_version(db, document, doc_type, stored, replacement_reason, actor)
    except ConflictError as conflicto:
        # CONC-046: quien pierde la carrera ya escribió su binario. Se borra; si el
        # borrado falla, queda la basura recuperable que este flujo ya admitía.
        if conflicto.code == "VERSION_CONFLICT":
            with contextlib.suppress(StorageError):
                storage.delete(key)
        raise
    _audit(db, actor, "DOCUMENT_FILE_UPLOADED", str(document.id),
           after={"version": version.version_number, "sha256": checksum,
                  "scan": scan.result},
           company_id=document.company_id)
    return version


#: Las dos restricciones que deciden una carrera de versiones: el correlativo y la
#: vigente. Cuál salta primero depende del orden en que PostgreSQL comprueba los
#: índices, y las dos significan lo mismo (CONC-046).
_RESTRICCIONES_DE_VERSION = ("uq_document_versions_number", "uq_document_versions_active")


def _create_version(db: Session, document: Document, doc_type: DocumentType,
                    stored: StoredFile, reason: str | None, actor: Any) -> DocumentVersion:
    """Crea la versión y supera la anterior.

    El correlativo lo asigna el **servidor** y la restricción única impide que
    dos peticiones simultáneas produzcan dos V2 (§32, §33). Quien pierde esa
    carrera recibe `VERSION_CONFLICT`, no la violación única en crudo (CONC-046):
    las dos leyeron el mismo máximo, y la segunda solo llega a insertar cuando la
    primera ya confirmó.
    """
    current = db.execute(
        select(DocumentVersion).where(DocumentVersion.document_id == document.id,
                                      DocumentVersion.status == "ACTIVE")
    ).scalars().first()

    if current is not None and doc_type.versioning_policy == "SINGLE":
        raise ConflictError(code="VERSION_NOT_ALLOWED",
                            message="Este tipo documental no admite versiones adicionales")

    highest = db.execute(
        select(func.max(DocumentVersion.version_number))
        .where(DocumentVersion.document_id == document.id)
    ).scalar_one_or_none() or 0

    try:
        with db.begin_nested():
            if current is not None:
                current.status = "SUPERSEDED"
                db.flush()

            version = DocumentVersion(
                document_id=str(document.id), company_id=document.company_id,
                version_number=int(highest) + 1, stored_file_id=str(stored.id),
                replacement_reason=reason, sha256=stored.sha256,
                metadata_snapshot=document.doc_metadata, status="ACTIVE",
                created_by=str(getattr(actor, "id", "")) or None)
            db.add(version)
            db.flush()
    except IntegrityError as error:
        if not any(es_violacion_unica(error, r) for r in _RESTRICCIONES_DE_VERSION):
            raise
        raise ConflictError(
            code="VERSION_CONFLICT",
            message="Otra operación creó una versión de este documento al mismo tiempo. "
                    "Recargue y vuelva a intentarlo.",
            details={"reason": "Otra subida simultánea creó la versión",
                     "dependencies": {"document_id": str(document.id)},
                     "allowed_actions": ["retry"]}) from None
    document.current_version_id = str(version.id)
    if document.status == "DRAFT":
        document.status = "ACTIVE"
    db.flush()
    return version


# --------------------------------------------------------------------------
# Vinculación y congelación (§34, §37-42)
# --------------------------------------------------------------------------

def attach(db: Session, *, document: Document, resource_type: str, resource_id: str,
           actor: Any, role: str = "ATTACHMENT",
           document_type_id: str | None = None) -> DocumentLink:
    """Vincula un documento a una entidad.

    Comprueba que el tipo está registrado, que la entidad existe y que pertenece
    a la misma empresa. El permiso sobre la entidad lo verifica la capa de API,
    que es quien conoce al usuario.
    """
    _entity, resource_company = resource_registry.resolve_resource(db, resource_type, resource_id)
    if resource_company is not None and resource_company != document.company_id:
        raise KontrolError(code="RESOURCE_ACCESS_DENIED",
                           message="El recurso pertenece a otra empresa", status_code=403)

    existing = db.execute(
        select(DocumentLink).where(DocumentLink.document_id == document.id,
                                   DocumentLink.resource_type == resource_type,
                                   DocumentLink.resource_id == resource_id,
                                   DocumentLink.role == role)).scalars().first()
    if existing is not None:
        return existing

    link = DocumentLink(document_id=str(document.id), company_id=document.company_id,
                        resource_type=resource_type, resource_id=resource_id, role=role,
                        document_type_id=document_type_id or document.document_type_id,
                        created_by=str(getattr(actor, "id", "")) or None)
    db.add(link)
    db.flush()
    _audit(db, actor, "DOCUMENT_LINKED", str(document.id),
           after={"resource_type": resource_type, "resource_id": resource_id, "role": role},
           company_id=document.company_id)
    return link


def detach(db: Session, *, link: DocumentLink, actor: Any) -> None:
    """Desvincula. Un vínculo congelado no se toca (R-D0-08-8)."""
    if link.is_frozen:
        raise ConflictError(
            code="LINK_FROZEN",
            message="El vínculo está congelado: el proceso que lo usó no se reinterpreta")
    _audit(db, actor, "DOCUMENT_UNLINKED", link.document_id,
           before={"resource_type": link.resource_type, "resource_id": link.resource_id},
           company_id=link.company_id)
    db.delete(link)
    db.flush()


def freeze_links(db: Session, *, resource_type: str, resource_id: str,
                 actor: Any = None) -> list[DocumentLink]:
    """Congela los vínculos de una entidad que acaba de volverse inmutable.

    Es el contrato que satisface la Spec 045: al resolverse una aprobación, sus
    documentos quedan atados a la versión **usada**. Crear una versión nueva
    después no altera la decisión de ayer (FR-046-100).
    """
    links = db.execute(
        select(DocumentLink).where(DocumentLink.resource_type == resource_type,
                                   DocumentLink.resource_id == resource_id)).scalars().all()
    frozen: list[DocumentLink] = []
    for link in links:
        if link.is_frozen:
            continue
        document = db.get(Document, link.document_id)
        if document is None or document.current_version_id is None:
            continue
        link.frozen_version_id = document.current_version_id
        link.is_frozen = True
        frozen.append(link)
        if actor is not None:
            _audit(db, actor, "DOCUMENT_LINK_FROZEN", link.document_id,
                   after={"frozen_version_id": link.frozen_version_id},
                   company_id=link.company_id)
    db.flush()
    return frozen


def documents_for(db: Session, *, resource_type: str, resource_id: str,
                  company_ids: list[str]) -> list[tuple[Document, DocumentLink]]:
    """Documentos de una entidad. La consulta que usan todos los consumidores."""
    resource_registry.get_kind(resource_type)
    rows = db.execute(
        select(Document, DocumentLink)
        .join(DocumentLink, DocumentLink.document_id == Document.id)
        .where(DocumentLink.resource_type == resource_type,
               DocumentLink.resource_id == resource_id,
               Document.company_id.in_(company_ids))
        .order_by(DocumentLink.created_at)).all()
    return [(d, link) for d, link in rows]


def puede_leer_archivo(db: Session, document: Document, company_id: str, permissions: set[str]) -> bool:
    """Para leer un archivo hay que poder ver **alguna** entidad vinculada (R-D0-08-6).

    Un documento sin vínculos solo lo lee quien tiene permiso documental: es el
    caso del documento suelto, todavía no adjuntado a nada; ese permiso lo exige
    el llamador. Un documento de otra empresa nunca es legible desde esta. Es la
    regla única que usan la descarga de documentos y el paquete de auditoría
    (DOC-08), para que exportar no sea un atajo alrededor del control documental.
    """
    if document.company_id != company_id:
        return False
    links = db.execute(select(DocumentLink).where(
        DocumentLink.document_id == document.id)).scalars().all()
    if not links:
        return True
    for link in links:
        try:
            _entity, company = resource_registry.resolve_resource(
                db, link.resource_type, link.resource_id)
        except KontrolError:
            continue
        if company is not None and company != company_id:
            continue
        if resource_registry.required_permission(link.resource_type) in permissions:
            return True
    return False


# --------------------------------------------------------------------------
# Estados, borrado y entrega
# --------------------------------------------------------------------------

def is_expired(document: Document, today: date | None = None) -> bool:
    """`EXPIRED` es **derivado**, no un estado persistido (FR-046-061).

    El «hoy» es el día de negocio de Caracas (FR-001-248).
    """
    if document.expiration_date is None:
        return False
    return document.expiration_date < (today or hoy_de_negocio())


def dependencies_of(db: Session, document: Document) -> dict[str, Any]:
    """Qué impide borrar. Se enumera, no se resume en un booleano."""
    links = db.execute(select(func.count()).select_from(DocumentLink)
                       .where(DocumentLink.document_id == document.id)).scalar_one()
    frozen = db.execute(select(func.count()).select_from(DocumentLink)
                        .where(DocumentLink.document_id == document.id,
                               DocumentLink.is_frozen.is_(True))).scalar_one()
    versions = db.execute(select(func.count()).select_from(DocumentVersion)
                          .where(DocumentVersion.document_id == document.id)).scalar_one()
    blocking: dict[str, Any] = {}
    if links:
        blocking["links"] = int(links)
    if frozen:
        blocking["frozen_links"] = int(frozen)
    if versions:
        blocking["versions"] = int(versions)
    if document.status == "ARCHIVED":
        blocking["archived"] = True
    return blocking


def can_delete(db: Session, document: Document) -> tuple[bool, dict[str, Any]]:
    blocking = dependencies_of(db, document)
    return (not blocking), blocking


def assert_deliverable(db: Session, version: DocumentVersion) -> StoredFile:
    """Un archivo solo se entrega si es recuperable y está limpio.

    Comprueba, en este orden: que el binario exista, que su hash coincida y que
    el análisis lo haya declarado limpio. Nunca se entrega otro contenido en
    lugar del esperado (§119, §120).
    """
    stored = db.get(StoredFile, version.stored_file_id)
    if stored is None:
        raise NotFoundError(code="DOCUMENT_NOT_FOUND", message="Documento no encontrado")
    if stored.security_status == scanning.INFECTED:
        raise KontrolError(code="FILE_INFECTED",
                           message="El archivo fue identificado como malicioso", status_code=422)
    if stored.security_status in (scanning.PENDING_SCAN, scanning.SCAN_FAILED):
        raise ConflictError(code="FILE_NOT_SCANNED",
                            message="El archivo aún no superó la verificación de seguridad")
    storage = get_storage()
    if not storage.exists(stored.storage_key):
        raise KontrolError(code="STORAGE_OBJECT_MISSING",
                           message="El archivo no está disponible en el almacenamiento",
                           status_code=500)
    if not storage.verify(stored.storage_key, stored.sha256):
        raise KontrolError(code="STORAGE_HASH_MISMATCH",
                           message="El archivo almacenado no coincide con su huella registrada",
                           status_code=500)
    return stored


# --------------------------------------------------------------------------
# Metadata declarada por el tipo (FR-046-014)
# --------------------------------------------------------------------------

#: Tipos admitidos en un esquema de metadata. Deliberadamente pocos: el
#: esquema describe datos de negocio, no estructuras arbitrarias.
_METADATA_TYPES: dict[str, tuple[type, ...]] = {
    "string": (str,), "number": (int, float), "integer": (int,),
    "boolean": (bool,), "date": (str,), "array": (list,), "object": (dict,),
}


def validate_metadata(doc_type: DocumentType, metadata: dict | None) -> None:
    """Valida la metadata contra el esquema **del tipo**, no contra uno fijo.

    Un tipo sin esquema no impone nada: la validación es una capacidad que cada
    tipo declara, no una regla escrita en el código (P8).
    """
    schema = doc_type.metadata_schema or {}
    if not schema:
        return

    values = metadata or {}
    fields = schema.get("fields") or {}
    errors: dict[str, str] = {}

    for name in schema.get("required", []):
        if values.get(name) in (None, ""):
            errors[name] = "Campo obligatorio para este tipo documental"

    for name, declared in fields.items():
        if name not in values or values[name] is None:
            continue
        expected = _METADATA_TYPES.get(str(declared.get("type", "string")))
        if expected and not isinstance(values[name], expected):
            errors[name] = f"Se esperaba un valor de tipo «{declared.get('type')}»"
        options = declared.get("options")
        if options and values[name] not in options:
            errors[name] = f"Valor no admitido; opciones: {', '.join(map(str, options))}"

    unknown = set(values) - set(fields)
    if unknown and not schema.get("allow_extra", True):
        for name in sorted(unknown):
            errors[name] = "Campo no declarado por el tipo documental"

    if errors:
        raise KontrolError(code="METADATA_INVALID",
                           message="La metadata no cumple el esquema del tipo documental",
                           status_code=422, details={"field_errors": errors})


# --------------------------------------------------------------------------
# Retención y purga (FR-046-065, 066, 067)
# --------------------------------------------------------------------------

def retention_days(doc_type: DocumentType) -> int | None:
    """Plazo declarado por el tipo, o `None`.

    **No hay valor por defecto.** KONTROL no inventa plazos legales: si nadie
    lo declaró, nada vence (ESC-046-03).
    """
    policy = doc_type.retention_policy or {}
    value = policy.get("retain_days")
    return int(value) if value is not None else None


def purge_blockers(db: Session, version: DocumentVersion) -> list[str]:
    """Razones por las que una versión **no** puede purgarse.

    Lista vacía significa que puede purgarse. Se devuelven todas, no la
    primera: quien opera merece ver el cuadro completo.
    """
    blockers: list[str] = []
    document = db.get(Document, version.document_id)
    if document is not None and document.current_version_id == str(version.id):
        blockers.append("Es la versión vigente del documento")
    frozen = db.execute(select(func.count()).select_from(DocumentLink).where(
        DocumentLink.frozen_version_id == str(version.id))).scalar_one()
    if frozen:
        blockers.append(f"{frozen} proceso(s) congelaron esta versión como evidencia")
    return blockers


def purge_version(db: Session, *, version: DocumentVersion, actor: Any) -> bool:
    """Purga el **binario** de una versión, conservando su rastro.

    La fila y su hash permanecen: purgar por retención no es borrar la prueba de
    que el archivo existió. Si algo la referencia, no se purga y se dice por qué
    (AC-046-33).

    No hay planificador aquí: esta operación la invoca el trabajador común de la
    plataforma. 046 aporta la operación, no un calendario propio (FR-046-066).
    """
    blockers = purge_blockers(db, version)
    if blockers:
        # `ConflictError` no lleva detalle; se usa la clase base para poder
        # decir **por qué** no se purga, que es lo que necesita quien opera.
        raise KontrolError(code="VERSION_IN_USE",
                           message="La versión está referenciada y no puede purgarse",
                           status_code=409, details={"blocked_by": blockers})

    stored = db.get(StoredFile, version.stored_file_id)
    if stored is None or stored.status == "PURGED":
        return False

    get_storage().delete(stored.storage_key)
    stored.status = "PURGED"
    db.flush()
    _audit(db, actor, "DOCUMENT_FILE_PURGED", str(version.document_id),
           after={"version": version.version_number, "sha256": stored.sha256},
           company_id=version.company_id)
    return True


# --------------------------------------------------------------------------
# Legado: importar solo lo que se puede localizar y verificar (FR-046-112)
# --------------------------------------------------------------------------

def import_legacy_reference(
    db: Session,
    *,
    reference: Any,
    search_roots: list[Path],
    doc_type: DocumentType,
    actor: Any,
    expected_sha256: str | None = None,
) -> Document | None:
    """Convierte una anotación heredada en documento **solo si hay binario**.

    Devuelve `None` cuando el archivo no se localiza: eso no es un fallo, es el
    resultado. La anotación se reclasifica como `MISSING_FILE` y se conserva —
    un archivo que no está no se inventa, y perder la pista de que existió sería
    peor que no encontrarlo (FR-046-113, R-046-5).

    La fuente heredada **no se toca**: ni se modifica ni se borra. Copiar antes
    de verificar y borrar después no es esta función; aquí no se borra nada
    (§144).
    """
    raw = (reference.raw_value or "").strip()
    if not raw:
        reference.classification = "MISSING_FILE"
        db.flush()
        return None

    # Se busca por el último segmento: la ruta heredada puede ser de otra
    # máquina, pero el nombre del archivo suele sobrevivir a la mudanza.
    candidate = _locate_legacy_file(raw, search_roots)
    if candidate is None:
        reference.classification = "MISSING_FILE"
        reference.notes = ((reference.notes or "") +
                           " · Binario no localizado en las raíces indicadas").strip()
        db.flush()
        return None

    digest = hashlib.sha256()
    size = 0
    with open(candidate, "rb") as source:
        for chunk in iter(lambda: source.read(CHUNK), b""):
            digest.update(chunk)
            size += len(chunk)
    checksum = digest.hexdigest()

    # Si el legado declaraba una huella, tiene que coincidir. Un binario que no
    # es el que se registró no se importa disfrazado del que era.
    if expected_sha256 and expected_sha256 != checksum:
        reference.classification = "MIGRATION_BLOCKER"
        reference.notes = ((reference.notes or "") +
                           " · La huella del binario no coincide con la registrada").strip()
        db.flush()
        raise ConflictError(
            code="LEGACY_HASH_MISMATCH",
            message="El binario localizado no coincide con la huella registrada")

    storage = get_storage()
    key = generate_storage_key(reference.company_id)
    with open(candidate, "rb") as source:
        stored_size, stored_hash = storage.put(key, source)
    if stored_hash != checksum or stored_size != size:
        storage.delete(key)
        raise KontrolError(code="STORAGE_FAILURE",
                           message="La verificación de integridad falló tras importar",
                           status_code=503)

    stored = StoredFile(
        company_id=reference.company_id,
        original_name=sanitize_filename(candidate.name),
        mime_type=detect_mime(str(candidate)),
        declared_mime=None, detected_mime=detect_mime(str(candidate)),
        extension=safe_extension(candidate.name), size=size, sha256=checksum,
        storage_key=key, storage_provider=storage.name,
        # El legado no pasó por el analizador de hoy: se dice, no se supone.
        security_status=scanning.PENDING_SCAN, status="AVAILABLE",
        uploaded_by=str(getattr(actor, "id", "")) or None, uploaded_at=_now())
    db.add(stored)
    db.flush()

    document = Document(
        company_id=reference.company_id, document_type_id=str(doc_type.id),
        title=sanitize_filename(candidate.name), status="DRAFT", is_managed=True,
        created_by=str(getattr(actor, "id", "")) or None)
    db.add(document)
    db.flush()
    _create_version(db, document, doc_type, stored, "Importación de legado", actor)

    reference.classification = "VALID_MANAGED_FILE"
    reference.document_id = str(document.id)
    db.flush()
    _audit(db, actor, "LEGACY_DOCUMENT_IMPORTED", str(document.id),
           after={"source_table": reference.source_table,
                  "source_column": reference.source_column,
                  "source_row_id": reference.source_row_id, "sha256": checksum},
           company_id=reference.company_id)
    return document


def _locate_legacy_file(raw: str, search_roots: list[Path]) -> Path | None:
    """Localiza el binario heredado sin salir de las raíces autorizadas."""
    if raw.lower().startswith(("http://", "https://")):
        return None                      # referencia externa: no es archivo nuestro
    name = sanitize_filename(raw.replace("\\", "/").split("/")[-1])
    for root in search_roots:
        base = Path(root).resolve()
        for candidate in (base / raw.lstrip("/"), base / name):
            try:
                resolved = candidate.resolve()
            except OSError:
                continue
            if not str(resolved).startswith(str(base) + os.sep):
                continue                 # una ruta heredada no autoriza a salir
            if resolved.is_file():
                return resolved
    return None


def allowed_actions(db: Session, document: Document, permissions: set[str]) -> list[str]:
    """Acciones que **este** usuario puede ejecutar sobre **este** documento."""
    actions: list[str] = []
    if "documentos:view" in permissions:
        actions.append("view")
    if "documentos:edit" in permissions and document.status not in ("ARCHIVED", "REVOKED"):
        actions.append("edit")
    if "documentos:upload" in permissions and document.is_managed \
            and document.status not in ("ARCHIVED", "REVOKED"):
        actions.append("upload")
    if "documentos:download" in permissions and document.current_version_id:
        actions.append("download")
    if "documentos:link" in permissions and document.status not in ("ARCHIVED", "REVOKED"):
        actions.append("link")
    if "documentos:edit" in permissions and document.status != "ARCHIVED":
        actions.append("archive")
    deletable, _ = can_delete(db, document)
    if deletable and "documentos:delete" in permissions:
        actions.append("delete")
    return actions
