"""API de gestión documental (Spec 046, F6).

Prefijo `/api/v1/documentos`. **Ninguna respuesta expone `storage_key`,
proveedor ni ruta** (R-D0-08-2): el cliente conoce documentos, no
almacenamiento.

La autorización de descarga y previsualización se resuelve sobre la **entidad
vinculada**, no sobre el conocimiento del identificador; sin acceso se responde
404, porque confirmar la existencia ya sería una filtración (§44).
"""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, File, Form, Header, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.responses import StreamingResponse

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_permission, require_write_allowed
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.documents import resources as resource_registry
from app.modules.documents import service
from app.modules.documents.models import (
    Document,
    DocumentCategory,
    DocumentLink,
    DocumentType,
    DocumentVersion,
    StoredFile,
)
from app.modules.documents.storage import get_storage, sanitize_filename
from app.modules.identity_access.models import User
from app.shared.audit import record_audit

router = APIRouter(prefix="/documentos", tags=["documentos"])


# --------------------------------------------------------------------------
# Alcance y control
# --------------------------------------------------------------------------

def _alcance(ctx: CompanyContext) -> list[str]:
    """La empresa en la que se está operando, y solo esa.

    Antes esto devolvía todas las empresas del tenant, así que un documento de
    la empresa B se leía, se listaba y se descargaba desde la empresa A. Era
    coherente cuando la Spec 046 se escribió —tenant y empresa eran lo mismo— y
    dejó de serlo en cuanto hubo dos. El comentario de `_get_document` ya decía
    la intención correcta; la implementación se había quedado atrás.
    """
    return [ctx.company_id]


def _permissions(db: Session, user: User) -> set[str]:
    from app.modules.identity_access import service as identity_service

    return set(identity_service.get_user_permissions(db, user))


def _get_document(db: Session, ctx: CompanyContext, document_id: str) -> Document:
    """Un documento de otra empresa se responde como inexistente (§44)."""
    document = db.get(Document, document_id)
    if document is None or document.company_id not in _alcance(ctx):
        raise NotFoundError(code="DOCUMENT_NOT_FOUND", message="Documento no encontrado")
    return document


def _get_type(db: Session, ctx: CompanyContext, type_id: str) -> DocumentType:
    doc_type = db.get(DocumentType, type_id)
    if doc_type is None or doc_type.company_id not in _alcance(ctx):
        raise NotFoundError(code="DOCUMENT_TYPE_NOT_FOUND", message="Tipo documental no encontrado")
    return doc_type


def _assert_resource_access(db: Session, user: User, ctx: CompanyContext,
                            resource_type: str, resource_id: str) -> None:
    """Permiso sobre la **entidad**, no sobre el documento (R-D0-08-6)."""
    _entity, company = resource_registry.resolve_resource(db, resource_type, resource_id)
    if company is not None and company not in _alcance(ctx):
        # No se confirma que exista.
        raise NotFoundError(code="RESOURCE_NOT_FOUND", message="Recurso no encontrado")
    needed = resource_registry.required_permission(resource_type)
    if needed not in _permissions(db, user):
        raise KontrolError(code="RESOURCE_ACCESS_DENIED",
                           message="No tiene permiso sobre el recurso vinculado",
                           status_code=403,
                           details={"required_permission": needed})


def _assert_can_read_file(db: Session, user: User, ctx: CompanyContext,
                          document: Document) -> None:
    """Para leer un archivo hay que poder ver **alguna** entidad vinculada.

    Un documento sin vínculos solo lo lee quien tiene permiso documental: es el
    caso del documento suelto, todavía no adjuntado a nada.
    """
    links = db.execute(select(DocumentLink).where(
        DocumentLink.document_id == document.id)).scalars().all()
    if not links:
        return
    companies = _alcance(ctx)
    permissions = _permissions(db, user)
    for link in links:
        try:
            _entity, company = resource_registry.resolve_resource(
                db, link.resource_type, link.resource_id)
        except KontrolError:
            continue
        if company is not None and company not in companies:
            continue
        if resource_registry.required_permission(link.resource_type) in permissions:
            return
    raise NotFoundError(code="DOCUMENT_NOT_FOUND", message="Documento no encontrado")


def _check_version(entity: Any, if_match: str | None) -> None:
    if if_match is None:
        return
    expected = if_match.strip('"')
    if not expected.isdigit() or int(expected) != int(entity.version):
        raise ConflictError(code="VERSION_CONFLICT",
                            message="El registro fue modificado por otra operación")


def _audit(db: Session, user: User, action: str, entity_id: str,
           before: dict | None = None, after: dict | None = None) -> None:
    record_audit(db, action=action, entity_type="Document", entity_id=entity_id,
                 tenant_id=user.tenant_id, user_id=str(user.id), before=before, after=after)


# --------------------------------------------------------------------------
# Catálogo
# --------------------------------------------------------------------------

class CategoryIn(BaseModel):
    #: Se conserva por compatibilidad; la empresa la decide el contexto.
    company_id: str | None = None
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None


class TypeIn(BaseModel):
    #: Se conserva por compatibilidad; la empresa la decide el contexto.
    company_id: str | None = None
    category_id: str | None = None
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=120)
    #: Vacío significa **ninguno**, no todos.
    allowed_mime_types: list[str] = Field(default_factory=list)
    allowed_extensions: list[str] = Field(default_factory=list)
    max_size_bytes: int | None = None
    versioning_policy: str = "VERSIONED"
    requires_expiration: bool = False
    metadata_schema: dict[str, Any] | None = None
    retention_policy: dict[str, Any] | None = None
    audit_downloads: bool = False
    scan_required: bool = True
    inline_preview_mimes: list[str] = Field(default_factory=list)


@router.get("/categorias")
def list_categories(db: Session = Depends(get_db),
                    user: User = Depends(require_permission("documentos", "view")),
    ctx: CompanyContext = Depends(get_company_context)):
    rows = db.execute(select(DocumentCategory).where(
        DocumentCategory.company_id.in_(_alcance(ctx)))
        .order_by(DocumentCategory.code)).scalars().all()
    return [{"id": str(c.id), "company_id": c.company_id, "code": c.code,
             "name": c.name, "description": c.description, "status": c.status} for c in rows]


@router.post("/categorias", dependencies=[Depends(require_write_allowed)])
def create_category(body: CategoryIn, db: Session = Depends(get_db),
                    actor: User = Depends(require_permission("documentos", "create")),
    ctx: CompanyContext = Depends(get_company_context)):
    if body.company_id is not None and body.company_id != ctx.company_id:
        raise NotFoundError(code="COMPANY_NOT_FOUND", message="Empresa no encontrada")
    category = DocumentCategory(**{**body.model_dump(), "company_id": ctx.company_id},
                                status="ACTIVE", created_by=str(actor.id))
    db.add(category)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(code="CATEGORY_CODE_DUPLICATE",
                            message="Ya existe una categoría con ese código") from exc
    db.refresh(category)
    return {"id": str(category.id), "code": category.code, "name": category.name}


def _type_dict(doc_type: DocumentType) -> dict[str, Any]:
    return {
        "id": str(doc_type.id), "company_id": doc_type.company_id,
        "category_id": doc_type.category_id, "code": doc_type.code, "name": doc_type.name,
        "allowed_mime_types": doc_type.allowed_mime_types or [],
        "allowed_extensions": doc_type.allowed_extensions or [],
        "max_size_bytes": doc_type.max_size_bytes,
        "versioning_policy": doc_type.versioning_policy,
        "requires_expiration": doc_type.requires_expiration,
        "retention_policy": doc_type.retention_policy,
        "audit_downloads": doc_type.audit_downloads,
        "scan_required": doc_type.scan_required,
        "inline_preview_mimes": doc_type.inline_preview_mimes or [],
        "status": doc_type.status, "version": int(doc_type.version),
    }


@router.get("/tipos")
def list_types(db: Session = Depends(get_db),
               user: User = Depends(require_permission("documentos", "view")),
    ctx: CompanyContext = Depends(get_company_context)):
    rows = db.execute(select(DocumentType).where(
        DocumentType.company_id.in_(_alcance(ctx)))
        .order_by(DocumentType.code)).scalars().all()
    return [_type_dict(t) for t in rows]


@router.post("/tipos", dependencies=[Depends(require_write_allowed)])
def create_type(body: TypeIn, db: Session = Depends(get_db),
                actor: User = Depends(require_permission("documentos", "manage_types")),
    ctx: CompanyContext = Depends(get_company_context)):
    if body.company_id is not None and body.company_id != ctx.company_id:
        raise NotFoundError(code="COMPANY_NOT_FOUND", message="Empresa no encontrada")
    doc_type = DocumentType(**{**body.model_dump(), "company_id": ctx.company_id},
                            status="ACTIVE", created_by=str(actor.id))
    db.add(doc_type)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(code="DOCUMENT_TYPE_CODE_DUPLICATE",
                            message="Ya existe un tipo con ese código") from exc
    db.refresh(doc_type)
    _audit(db, actor, "DOCUMENT_TYPE_CREATED", str(doc_type.id), after={"code": doc_type.code})
    db.commit()
    return _type_dict(doc_type)


@router.patch("/tipos/{type_id}", dependencies=[Depends(require_write_allowed)])
def update_type(type_id: str, body: dict[str, Any], db: Session = Depends(get_db),
                actor: User = Depends(require_permission("documentos", "manage_types")),
    ctx: CompanyContext = Depends(get_company_context)):
    doc_type = _get_type(db, ctx, type_id)
    for field in ("name", "allowed_mime_types", "allowed_extensions", "max_size_bytes",
                  "versioning_policy", "requires_expiration", "metadata_schema",
                  "retention_policy", "audit_downloads", "scan_required",
                  "inline_preview_mimes", "status"):
        if field in body:
            setattr(doc_type, field, body[field])
    doc_type.version = int(doc_type.version) + 1
    _audit(db, actor, "DOCUMENT_TYPE_UPDATED", str(doc_type.id))
    db.commit()
    db.refresh(doc_type)
    return _type_dict(doc_type)


# --------------------------------------------------------------------------
# Documentos
# --------------------------------------------------------------------------

class DocumentIn(BaseModel):
    #: Se conserva por compatibilidad; la empresa la decide el contexto.
    company_id: str | None = None
    document_type_id: str
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    document_number: str | None = None
    issuer: str | None = None
    issued_at: date | None = None
    effective_from: date | None = None
    expiration_date: date | None = None
    doc_metadata: dict[str, Any] | None = None
    #: Referencia externa: sin archivo administrado (§64).
    external_url: str | None = None


class DocumentPatch(BaseModel):
    title: str | None = None
    description: str | None = None
    document_number: str | None = None
    issuer: str | None = None
    issued_at: date | None = None
    effective_from: date | None = None
    expiration_date: date | None = None
    doc_metadata: dict[str, Any] | None = None


def _document_dict(db: Session, document: Document, permissions: set[str],
                   *, full: bool = False) -> dict[str, Any]:
    version = (db.get(DocumentVersion, document.current_version_id)
               if document.current_version_id else None)
    stored = (db.get(StoredFile, version.stored_file_id)
              if version is not None else None)
    deletable, blocking = service.can_delete(db, document)
    data: dict[str, Any] = {
        "id": str(document.id), "company_id": document.company_id,
        "document_type_id": document.document_type_id, "title": document.title,
        "document_number": document.document_number, "issuer": document.issuer,
        "issued_at": document.issued_at.isoformat() if document.issued_at else None,
        "expiration_date": (document.expiration_date.isoformat()
                            if document.expiration_date else None),
        # `EXPIRED` es derivado, no un estado persistido.
        "is_expired": service.is_expired(document),
        "status": document.status, "is_managed": document.is_managed,
        "external_url": document.external_url, "version": int(document.version),
        "current_version": (
            {"id": str(version.id), "version_number": version.version_number,
             "sha256": version.sha256,
             "file": ({"original_name": stored.original_name,
                       "mime_type": stored.mime_type, "size": stored.size,
                       # El estado de seguridad **siempre** viaja: si es
                       # `SKIPPED`, el cliente sabe que no se analizó.
                       "security_status": stored.security_status}
                      if stored is not None else None)}
            if version is not None else None),
        "can_delete": deletable,
        "delete_blocked_by": blocking or None,
        "allowed_actions": service.allowed_actions(db, document, permissions),
    }
    if not full:
        return data
    data["description"] = document.description
    data["effective_from"] = (document.effective_from.isoformat()
                              if document.effective_from else None)
    data["metadata"] = document.doc_metadata
    links = db.execute(select(DocumentLink).where(
        DocumentLink.document_id == document.id)).scalars().all()
    data["links"] = [{"id": str(link.id), "resource_type": link.resource_type,
                      "resource_id": link.resource_id, "role": link.role,
                      "is_frozen": link.is_frozen,
                      "frozen_version_id": link.frozen_version_id} for link in links]
    return data


@router.get("")
def list_documents(q: str | None = None, document_type_id: str | None = None,
                   status: str | None = None, expiring_before: date | None = None,
                   resource_type: str | None = None, resource_id: str | None = None,
                   limit: int = 50, offset: int = 0, db: Session = Depends(get_db),
                   user: User = Depends(require_permission("documentos", "view")),
    ctx: CompanyContext = Depends(get_company_context)):
    """Biblioteca paginada. **No abre ningún binario** (NFR-046-01)."""
    companies = _alcance(ctx)
    query = select(Document).where(Document.company_id.in_(companies))
    if document_type_id:
        query = query.where(Document.document_type_id == document_type_id)
    if status:
        query = query.where(Document.status == status)
    if expiring_before:
        query = query.where(Document.expiration_date.is_not(None),
                            Document.expiration_date <= expiring_before)
    if resource_type and resource_id:
        resource_registry.get_kind(resource_type)
        query = query.join(DocumentLink, DocumentLink.document_id == Document.id).where(
            DocumentLink.resource_type == resource_type,
            DocumentLink.resource_id == resource_id)
    if q:
        pattern = f"%{q}%"
        query = query.where(Document.title.ilike(pattern)
                            | Document.document_number.ilike(pattern))
    total = int(db.execute(select(func.count()).select_from(query.subquery())).scalar_one())
    rows = db.execute(query.order_by(Document.created_at.desc())
                      .limit(limit).offset(offset)).scalars().all()
    permissions = _permissions(db, user)
    return {"total": total, "limit": limit, "offset": offset,
            "items": [_document_dict(db, d, permissions) for d in rows]}


@router.post("", dependencies=[Depends(require_write_allowed)])
def create_document(body: DocumentIn, db: Session = Depends(get_db),
                    actor: User = Depends(require_permission("documentos", "create")),
    ctx: CompanyContext = Depends(get_company_context)):
    if body.company_id is not None and body.company_id != ctx.company_id:
        raise NotFoundError(code="COMPANY_NOT_FOUND", message="Empresa no encontrada")
    doc_type = _get_type(db, ctx, body.document_type_id)
    if doc_type.requires_expiration and body.expiration_date is None:
        raise KontrolError(code="EXPIRATION_REQUIRED",
                           message="Este tipo documental exige fecha de vencimiento",
                           status_code=422)
    # La metadata se valida contra el esquema **del tipo** (FR-046-014).
    service.validate_metadata(doc_type, body.doc_metadata)
    data = body.model_dump()
    data["company_id"] = ctx.company_id
    external = data.pop("external_url")
    document = Document(**data, external_url=external, is_managed=external is None,
                        status="DRAFT", created_by=str(actor.id))
    db.add(document)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(code="DOCUMENT_NUMBER_DUPLICATE",
                            message="Ya existe un documento con ese número para este tipo") from exc
    db.refresh(document)
    _audit(db, actor, "DOCUMENT_CREATED", str(document.id), after={"title": document.title})
    db.commit()
    return _document_dict(db, document, _permissions(db, actor), full=True)


@router.get("/{document_id}")
def get_document(document_id: str, db: Session = Depends(get_db),
                 user: User = Depends(require_permission("documentos", "view")),
    ctx: CompanyContext = Depends(get_company_context)):
    document = _get_document(db, ctx, document_id)
    return _document_dict(db, document, _permissions(db, user), full=True)


@router.patch("/{document_id}", dependencies=[Depends(require_write_allowed)])
def update_document(document_id: str, body: DocumentPatch,
                    if_match: str | None = Header(default=None, alias="If-Match"),
                    db: Session = Depends(get_db),
                    actor: User = Depends(require_permission("documentos", "edit")),
    ctx: CompanyContext = Depends(get_company_context)):
    document = _get_document(db, ctx, document_id)
    _check_version(document, if_match)
    if document.status in ("ARCHIVED", "REVOKED"):
        raise ConflictError(code="DOCUMENT_IMMUTABLE",
                            message="Un documento archivado no se edita")
    changes = body.model_dump(exclude_unset=True)
    if "doc_metadata" in changes:
        service.validate_metadata(_get_type(db, ctx, document.document_type_id),
                                  changes["doc_metadata"])
    before = {"title": document.title}
    for field, value in changes.items():
        setattr(document, field, value)
    document.version = int(document.version) + 1
    _audit(db, actor, "DOCUMENT_METADATA_UPDATED", str(document.id), before=before,
           after={"title": document.title})
    db.commit()
    db.refresh(document)
    return _document_dict(db, document, _permissions(db, actor), full=True)


@router.post("/{document_id}/archive", dependencies=[Depends(require_write_allowed)])
def archive_document(document_id: str, db: Session = Depends(get_db),
                     actor: User = Depends(require_permission("documentos", "edit")),
    ctx: CompanyContext = Depends(get_company_context)):
    """Archivar es lógico: el binario **no** se destruye (FR-046-064)."""
    document = _get_document(db, ctx, document_id)
    document.status = "ARCHIVED"
    document.version = int(document.version) + 1
    _audit(db, actor, "DOCUMENT_ARCHIVED", str(document.id))
    db.commit()
    return {"id": str(document.id), "status": document.status}


@router.delete("/{document_id}", dependencies=[Depends(require_write_allowed)])
def delete_document(document_id: str, db: Session = Depends(get_db),
                    actor: User = Depends(require_permission("documentos", "delete")),
    ctx: CompanyContext = Depends(get_company_context)):
    document = _get_document(db, ctx, document_id)
    deletable, blocking = service.can_delete(db, document)
    if not deletable:
        _audit(db, actor, "DOCUMENT_DELETE_BLOCKED", str(document.id), after=blocking)
        db.commit()
        raise KontrolError(
            code="DOCUMENT_IN_USE",
            message="El documento tiene dependencias y no puede borrarse", status_code=409,
            details={"reason": "Existen vínculos o versiones asociados",
                     "dependencies": blocking, "allowed_actions": ["archive"]})
    _audit(db, actor, "DOCUMENT_DELETED", str(document.id), before={"title": document.title})
    db.delete(document)
    db.commit()
    return {"deleted": True}


# --------------------------------------------------------------------------
# Subida y versiones
# --------------------------------------------------------------------------

@router.get("/{document_id}/versiones")
def list_versions(document_id: str, db: Session = Depends(get_db),
                  user: User = Depends(require_permission("documentos", "view")),
    ctx: CompanyContext = Depends(get_company_context)):
    document = _get_document(db, ctx, document_id)
    rows = db.execute(
        select(DocumentVersion).where(DocumentVersion.document_id == document.id)
        .order_by(DocumentVersion.version_number.desc())).scalars().all()
    result = []
    for version in rows:
        stored = db.get(StoredFile, version.stored_file_id)
        result.append({
            "id": str(version.id), "version_number": version.version_number,
            "sha256": version.sha256, "status": version.status,
            "replacement_reason": version.replacement_reason,
            "created_at": version.created_at.isoformat() if version.created_at else None,
            "file": ({"original_name": stored.original_name, "mime_type": stored.mime_type,
                      "size": stored.size, "security_status": stored.security_status}
                     if stored is not None else None),
        })
    return result


def _clave_idempotente(document_id: str, idempotency_key: str) -> str:
    return f"documents:upload:{document_id}:{idempotency_key}"[:64]


def _acierto_idempotente(db: Session, document: Document, idempotency_key: str) -> dict | None:
    """La versión que creó **esta** clave en **este** documento, si existe.

    Se lee del registro, no de la versión vigente: después pudo subirse otra, y un
    reintento no debe recibir una versión que no pidió (AC-046-13, AC-046-54).
    """
    from app.modules.system.models import IdempotencyRecord

    registro = db.execute(select(IdempotencyRecord).where(
        IdempotencyRecord.key == _clave_idempotente(str(document.id), idempotency_key))).scalars().first()
    if registro is None:
        return None
    version_id = (registro.response_payload or {}).get("version_id")
    version = db.get(DocumentVersion, version_id) if version_id else None
    if version is None or str(version.document_id) != str(document.id):
        return None
    return {"id": str(version.id), "version_number": version.version_number,
            "sha256": version.sha256, "idempotent_hit": True}


@router.post("/{document_id}/versiones", dependencies=[Depends(require_write_allowed)])
def upload_version(document_id: str,
                   file: UploadFile = File(...),
                   replacement_reason: str | None = Form(default=None),
                   idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
                   db: Session = Depends(get_db),
                   actor: User = Depends(require_permission("documentos", "upload")),
    ctx: CompanyContext = Depends(get_company_context)):
    """Sube un archivo y crea una versión.

    El cliente envía el archivo y, como mucho, el motivo. **No** envía hash,
    tamaño, `storage_key` ni número de versión: los determina el servidor
    (§113). Un archivo solo llega a estar disponible tras pasar todos los
    controles.
    """
    document = _get_document(db, ctx, document_id)
    doc_type = _get_type(db, ctx, document.document_type_id)

    # Idempotencia: doble clic o reintento devuelven la misma versión (§101).
    if idempotency_key:
        acierto = _acierto_idempotente(db, document, idempotency_key)
        if acierto is not None:
            return acierto

    try:
        version = service.upload_version(
            db, document=document, doc_type=doc_type, stream=file.file,
            original_name=file.filename or "archivo", declared_mime=file.content_type,
            actor=actor, replacement_reason=replacement_reason)
    except ConflictError as conflicto:
        # CONC-046: con la misma clave, quien pierde la carrera no recibe un
        # conflicto sino la versión que ganó (AC-046-53). La ganadora ya confirmó
        # —por eso esta transacción chocó—, así que su registro es legible.
        if not (idempotency_key and conflicto.code == "VERSION_CONFLICT"):
            raise
        db.rollback()
        acierto = _acierto_idempotente(db, document, idempotency_key)
        if acierto is None:
            raise
        return acierto

    if idempotency_key:
        from app.modules.system.models import IdempotencyRecord

        db.add(IdempotencyRecord(
            key=_clave_idempotente(str(document.id), idempotency_key),
            method="POST", path=f"/documentos/{document_id}/versiones",
            user_id=str(actor.id), company_id=document.company_id,
            response_status=200, response_hash=version.sha256,
            response_payload={"version_id": str(version.id),
                              "version_number": version.version_number}))
    db.commit()
    db.refresh(version)
    stored = db.get(StoredFile, version.stored_file_id)
    return {
        "id": str(version.id), "document_id": str(document.id),
        "version_number": version.version_number, "sha256": version.sha256,
        "replacement_reason": version.replacement_reason,
        "file": {"original_name": stored.original_name, "mime_type": stored.mime_type,
                 "declared_mime": stored.declared_mime, "detected_mime": stored.detected_mime,
                 "size": stored.size, "sha256": stored.sha256,
                 "security_status": stored.security_status},
    }


# --------------------------------------------------------------------------
# Descarga y previsualización
# --------------------------------------------------------------------------

def _deliver(db: Session, user: User, document: Document, version: DocumentVersion,
             *, inline: bool) -> StreamingResponse:
    """Entrega un archivo, tras comprobar que puede entregarse."""
    doc_type = db.get(DocumentType, document.document_type_id)
    stored = service.assert_deliverable(db, version)

    disposition = "attachment"
    media_type = "application/octet-stream"
    if inline:
        if doc_type is None or not service.can_preview_inline(doc_type, stored.mime_type):
            # Contenido no declarado seguro: se descarga, no se muestra (§21).
            disposition = "attachment"
        else:
            disposition = "inline"
            media_type = stored.mime_type

    filename = sanitize_filename(stored.original_name)
    handle = get_storage().open(stored.storage_key)

    if doc_type is not None and doc_type.audit_downloads:
        # Según política del tipo, no siempre (§80).
        _audit(db, user, "DOCUMENT_DOWNLOADED", str(document.id),
               after={"version": version.version_number})
        db.commit()

    return StreamingResponse(
        handle, media_type=media_type,
        headers={
            "Content-Disposition": f'{disposition}; filename="{filename}"',
            "Content-Length": str(stored.size),
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; sandbox",
        })


def _resolve_version(db: Session, document: Document, version_id: str | None) -> DocumentVersion:
    if version_id:
        version = db.get(DocumentVersion, version_id)
        if version is None or version.document_id != str(document.id):
            raise NotFoundError(code="DOCUMENT_NOT_FOUND", message="Versión no encontrada")
        return version
    if not document.current_version_id:
        raise NotFoundError(code="DOCUMENT_NOT_FOUND", message="El documento no tiene archivo")
    version = db.get(DocumentVersion, document.current_version_id)
    if version is None:
        raise NotFoundError(code="DOCUMENT_NOT_FOUND", message="El documento no tiene archivo")
    return version


@router.get("/{document_id}/descargar")
def download_document(document_id: str, db: Session = Depends(get_db),
                      user: User = Depends(require_permission("documentos", "download")),
    ctx: CompanyContext = Depends(get_company_context)):
    document = _get_document(db, ctx, document_id)
    _assert_can_read_file(db, user, ctx, document)
    return _deliver(db, user, document, _resolve_version(db, document, None), inline=False)


@router.get("/{document_id}/versiones/{version_id}/descargar")
def download_version(document_id: str, version_id: str, db: Session = Depends(get_db),
                     user: User = Depends(require_permission("documentos", "download")),
    ctx: CompanyContext = Depends(get_company_context)):
    """Descarga una versión concreta. Es lo que permite que un histórico
    congelado devuelva **sus** bytes, no los de la versión vigente (§35)."""
    document = _get_document(db, ctx, document_id)
    _assert_can_read_file(db, user, ctx, document)
    return _deliver(db, user, document, _resolve_version(db, document, version_id), inline=False)


@router.get("/{document_id}/preview")
def preview_document(document_id: str, db: Session = Depends(get_db),
                     user: User = Depends(require_permission("documentos", "download")),
    ctx: CompanyContext = Depends(get_company_context)):
    """Previsualización. **Mismo permiso** que la descarga, no uno menor (§50)."""
    document = _get_document(db, ctx, document_id)
    _assert_can_read_file(db, user, ctx, document)
    return _deliver(db, user, document, _resolve_version(db, document, None), inline=True)


# --------------------------------------------------------------------------
# Vinculación
# --------------------------------------------------------------------------

class LinkIn(BaseModel):
    resource_type: str
    resource_id: str
    role: str = "ATTACHMENT"


@router.post("/{document_id}/vinculos", dependencies=[Depends(require_write_allowed)])
def create_link(document_id: str, body: LinkIn, db: Session = Depends(get_db),
                actor: User = Depends(require_permission("documentos", "link")),
    ctx: CompanyContext = Depends(get_company_context)):
    """Vincula. Exige permiso sobre la **entidad de destino** (§39)."""
    document = _get_document(db, ctx, document_id)
    _assert_resource_access(db, actor, ctx, body.resource_type, body.resource_id)
    link = service.attach(db, document=document, resource_type=body.resource_type,
                          resource_id=body.resource_id, actor=actor, role=body.role)
    db.commit()
    db.refresh(link)
    return {"id": str(link.id), "document_id": str(document.id),
            "resource_type": link.resource_type, "resource_id": link.resource_id,
            "role": link.role, "is_frozen": link.is_frozen}


@router.delete("/vinculos/{link_id}", dependencies=[Depends(require_write_allowed)])
def delete_link(link_id: str, db: Session = Depends(get_db),
                actor: User = Depends(require_permission("documentos", "link")),
    ctx: CompanyContext = Depends(get_company_context)):
    link = db.get(DocumentLink, link_id)
    if link is None or link.company_id not in _alcance(ctx):
        raise NotFoundError(code="DOCUMENT_NOT_FOUND", message="Vínculo no encontrado")
    _assert_resource_access(db, actor, ctx, link.resource_type, link.resource_id)
    try:
        service.detach(db, link=link, actor=actor)
    except ConflictError:
        db.commit()
        raise
    db.commit()
    return {"deleted": True}


@router.get("/por-recurso/{resource_type}/{resource_id}")
def documents_by_resource(resource_type: str, resource_id: str, db: Session = Depends(get_db),
                          user: User = Depends(require_permission("documentos", "view")),
    ctx: CompanyContext = Depends(get_company_context)):
    """La consulta que usan todos los consumidores."""
    _assert_resource_access(db, user, ctx, resource_type, resource_id)
    permissions = _permissions(db, user)
    pairs = service.documents_for(db, resource_type=resource_type, resource_id=resource_id,
                                  company_ids=_alcance(ctx))
    return [{**_document_dict(db, document, permissions),
             "link": {"id": str(link.id), "role": link.role, "is_frozen": link.is_frozen,
                      "frozen_version_id": link.frozen_version_id}}
            for document, link in pairs]


@router.get("/salud/almacenamiento")
def storage_health(db: Session = Depends(get_db),
                   user: User = Depends(require_permission("documentos", "view"))):
    """Estado del almacenamiento. **No expone rutas ni credenciales** (§121)."""
    del db, user
    return get_storage().health()
