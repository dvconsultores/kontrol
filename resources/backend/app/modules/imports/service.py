from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.documents.models import DocumentLink
from app.modules.imports.models import ImportDocument, ImportFile
from app.modules.master_data import party_service
from app.modules.master_data import service as master_service
from app.modules.master_data.models import Party
from app.modules.purchasing.models import PurchaseOrder
from app.shared.audit import record_audit

INCOTERMS = ("EXW", "FCA", "CPT", "CIP", "DAP", "DPU", "DDP", "FAS", "FOB", "CFR", "CIF")
DOCUMENTOS_OBLIGATORIOS = (
    ("PROFORMA_INVOICE", "Factura proforma"),
    ("PACKING_LIST", "Packing list"),
    ("SHIPPING_DOCUMENT", "Documento de embarque"),
)


def _audit(
    db: Session,
    *,
    action: str,
    file: ImportFile,
    actor_id: str,
    tenant_id: str,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    reason: str | None = None,
):
    record_audit(
        db,
        action=action,
        entity_type="ImportFile",
        entity_id=str(file.id),
        tenant_id=tenant_id,
        company_id=file.company_id,
        user_id=actor_id,
        before=before,
        after=after,
        reason=reason,
    )


def _file_key(file: ImportFile, keys: tuple[str, ...]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in keys:
        value = getattr(file, key, None)
        if isinstance(value, date):
            value = value.isoformat()
        result[key] = value
    return result


def get_file(db: Session, company_id: str, file_id: str, *, for_update: bool = False) -> ImportFile:
    stmt = select(ImportFile).where(ImportFile.id == file_id, ImportFile.company_id == company_id)
    if for_update:
        stmt = stmt.with_for_update()
    file = db.scalar(stmt)
    if file is None:
        raise NotFoundError(code="IMPORT_NOT_FOUND", message="Importación no encontrada")
    return file


def _get_document(db: Session, company_id: str, file: ImportFile, document_id: str) -> ImportDocument:
    document = db.scalar(
        select(ImportDocument).where(
            ImportDocument.id == document_id,
            ImportDocument.file_id == file.id,
            ImportDocument.company_id == company_id,
        )
    )
    if document is None:
        raise NotFoundError(code="IMPORT_DOCUMENT_NOT_FOUND", message="Documento de importación no encontrado")
    return document


def create_file(
    db: Session,
    *,
    company_id: str,
    actor_id: str,
    tenant_id: str,
    data: dict[str, Any],
) -> ImportFile:
    code = data["code"].strip()
    existing = db.scalar(
        select(ImportFile).where(ImportFile.company_id == company_id, ImportFile.code == code)
    )
    if existing is not None:
        raise ConflictError(code="IMPORT_CODE_EXISTS", message="Ya existe una importación con ese código")

    master_service.require_eligible_party(
        db,
        company_id=company_id,
        party_id=data["supplier_id"],
        role="PROVEEDOR",
        require_active=True,
    )

    incoterm = data.get("incoterm")
    if incoterm and incoterm not in INCOTERMS:
        raise KontrolError(code="IMPORT_INCOTERM_INVALID", message="INCOTERM no reconocido", status_code=422)

    file = ImportFile(
        company_id=company_id,
        code=code,
        supplier_id=data["supplier_id"],
        currency=data.get("currency", "VED"),
        status="NEGOTIATING",
        incoterm=incoterm,
        incoterm_place=data.get("incoterm_place"),
        payment_conditions=data.get("payment_conditions"),
        delivery_conditions=data.get("delivery_conditions"),
        expected_dispatch_date=data.get("expected_dispatch_date"),
        expected_arrival_date=data.get("expected_arrival_date"),
        notes=data.get("notes"),
        version=1,
    )
    db.add(file)
    db.flush()

    for kind, name in DOCUMENTOS_OBLIGATORIOS:
        db.add(
            ImportDocument(
                company_id=company_id,
                file_id=file.id,
                kind=kind,
                name=name,
                required=True,
                status="PENDING",
                version=1,
            )
        )

    _audit(
        db,
        action="IMPORT_FILE_CREATED",
        file=file,
        actor_id=actor_id,
        tenant_id=tenant_id,
        after=_file_key(file, ("code", "currency", "status", "supplier_id")),
    )
    return file


def update_file(
    db: Session,
    *,
    file: ImportFile,
    actor_id: str,
    tenant_id: str,
    changes: dict[str, Any],
    if_match: str | None,
) -> ImportFile:
    if file.status not in ("NEGOTIATING", "ORDERED"):
        raise ConflictError(code="IMPORT_INVALID_STATE", message="La importación no admite este cambio en su estado actual")

    party_service.check_version(file, if_match)

    if "incoterm" in changes and changes["incoterm"] is not None and changes["incoterm"] not in INCOTERMS:
        raise KontrolError(code="IMPORT_INCOTERM_INVALID", message="INCOTERM no reconocido", status_code=422)

    before = _file_key(
        file,
        (
            "delivery_conditions",
            "expected_arrival_date",
            "expected_dispatch_date",
            "incoterm",
            "incoterm_place",
            "notes",
            "payment_conditions",
        ),
    )

    for key in (
        "incoterm",
        "incoterm_place",
        "payment_conditions",
        "delivery_conditions",
        "expected_dispatch_date",
        "expected_arrival_date",
        "notes",
    ):
        if key in changes:
            setattr(file, key, changes[key])

    party_service.bump(file)
    after = _file_key(
        file,
        (
            "delivery_conditions",
            "expected_arrival_date",
            "expected_dispatch_date",
            "incoterm",
            "incoterm_place",
            "notes",
            "payment_conditions",
        ),
    )

    _audit(
        db,
        action="IMPORT_FILE_UPDATED",
        file=file,
        actor_id=actor_id,
        tenant_id=tenant_id,
        before=before,
        after=after,
    )
    return file


def link_order(
    db: Session,
    *,
    file: ImportFile,
    order_id: str,
    actor_id: str,
    tenant_id: str,
) -> ImportFile:
    if file.status != "NEGOTIATING":
        raise ConflictError(code="IMPORT_INVALID_STATE", message="La importación no admite este cambio en su estado actual")

    missing = []
    if not file.incoterm:
        missing.append("incoterm")
    if not file.payment_conditions:
        missing.append("payment_conditions")
    if not file.delivery_conditions:
        missing.append("delivery_conditions")
    if missing:
        raise ConflictError(
            code="IMPORT_NEGOTIATION_INCOMPLETE",
            message="Completa la negociación antes de vincular la orden",
            details={"missing": missing},
        )

    order = db.get(PurchaseOrder, order_id)
    if order is None or order.company_id != file.company_id:
        raise NotFoundError(code="ORDER_NOT_FOUND", message="Orden no encontrada")

    if order.status not in ("APPROVED", "PARTIALLY_RECEIVED", "RECEIVED"):
        raise ConflictError(code="IMPORT_ORDER_NOT_APPROVED", message="La orden debe estar aprobada")

    if order.supplier_id != file.supplier_id:
        raise ConflictError(code="IMPORT_ORDER_SUPPLIER_MISMATCH", message="La orden pertenece a otro proveedor")

    if order.currency != file.currency:
        raise ConflictError(code="IMPORT_ORDER_CURRENCY_MISMATCH", message="La orden está en otra moneda")

    in_use = db.scalar(
        select(ImportFile).where(
            ImportFile.order_id == order.id,
            ImportFile.status != "CANCELLED",
            ImportFile.company_id == file.company_id,
        )
    )
    if in_use is not None:
        raise ConflictError(code="IMPORT_ORDER_IN_USE", message="La orden ya está vinculada a otra importación")

    before = _file_key(file, ("order_id", "status"))
    file.order_id = str(order.id)
    file.status = "ORDERED"
    party_service.bump(file)
    after = _file_key(file, ("order_id", "status"))

    _audit(
        db,
        action="IMPORT_ORDER_LINKED",
        file=file,
        actor_id=actor_id,
        tenant_id=tenant_id,
        before=before,
        after=after,
    )
    return file


def add_document(
    db: Session,
    *,
    file: ImportFile,
    kind: str,
    name: str,
    actor_id: str,
    tenant_id: str,
) -> ImportDocument:
    if file.status not in ("NEGOTIATING", "ORDERED"):
        raise ConflictError(code="IMPORT_INVALID_STATE", message="La importación no admite este cambio en su estado actual")

    if kind not in ("CERTIFICATE", "OTHER"):
        raise KontrolError(code="IMPORT_DOCUMENT_KIND_INVALID", message="Tipo de documento no válido", status_code=422)

    document = ImportDocument(
        company_id=file.company_id,
        file_id=file.id,
        kind=kind,
        name=name,
        required=False,
        status="PENDING",
        version=1,
    )
    db.add(document)
    db.flush()

    _audit(
        db,
        action="IMPORT_DOCUMENT_ADDED",
        file=file,
        actor_id=actor_id,
        tenant_id=tenant_id,
        after={
            "document_id": str(document.id),
            "kind": document.kind,
            "name": document.name,
            "required": document.required,
        },
    )
    party_service.bump(file)
    return document


def receive_document(
    db: Session,
    *,
    file: ImportFile,
    document: ImportDocument,
    reference: str,
    actor_id: str,
    tenant_id: str,
) -> ImportDocument:
    if file.status not in ("NEGOTIATING", "ORDERED"):
        raise ConflictError(code="IMPORT_INVALID_STATE", message="La importación no admite este cambio en su estado actual")

    if document.status not in ("PENDING", "OBSERVED"):
        raise ConflictError(code="IMPORT_DOCUMENT_INVALID_STATE", message="El documento no admite esa acción en su estado actual")

    if not reference or not reference.strip():
        raise KontrolError(code="IMPORT_DOCUMENT_REFERENCE_REQUIRED", message="La referencia es obligatoria", status_code=422)

    before = _document_key(document)
    document.reference = reference.strip()
    document.status = "RECEIVED"
    document.observation = None
    party_service.bump(document)
    party_service.bump(file)
    after = _document_key(document)

    _audit(
        db,
        action="IMPORT_DOCUMENT_CHANGED",
        file=file,
        actor_id=actor_id,
        tenant_id=tenant_id,
        before=before,
        after=after,
    )
    return document


def validate_document(
    db: Session,
    *,
    file: ImportFile,
    document: ImportDocument,
    actor_id: str,
    tenant_id: str,
) -> ImportDocument:
    if file.status not in ("NEGOTIATING", "ORDERED"):
        raise ConflictError(code="IMPORT_INVALID_STATE", message="La importación no admite este cambio en su estado actual")

    if document.status != "RECEIVED":
        raise ConflictError(code="IMPORT_DOCUMENT_INVALID_STATE", message="El documento no admite esa acción en su estado actual")

    attachments = db.scalar(
        select(DocumentLink).where(
            DocumentLink.resource_type == "ImportDocument",
            DocumentLink.resource_id == str(document.id),
            DocumentLink.company_id == file.company_id,
        )
    )
    if attachments is None:
        raise ConflictError(code="IMPORT_DOCUMENT_WITHOUT_FILE", message="Adjunta el archivo antes de validar")

    before = _document_key(document)
    document.status = "VALIDATED"
    party_service.bump(document)
    party_service.bump(file)
    after = _document_key(document)

    _audit(
        db,
        action="IMPORT_DOCUMENT_CHANGED",
        file=file,
        actor_id=actor_id,
        tenant_id=tenant_id,
        before=before,
        after=after,
    )
    return document


def observe_document(
    db: Session,
    *,
    file: ImportFile,
    document: ImportDocument,
    observation: str,
    actor_id: str,
    tenant_id: str,
) -> ImportDocument:
    if file.status not in ("NEGOTIATING", "ORDERED"):
        raise ConflictError(code="IMPORT_INVALID_STATE", message="La importación no admite este cambio en su estado actual")

    if document.status not in ("RECEIVED", "VALIDATED"):
        raise ConflictError(code="IMPORT_DOCUMENT_INVALID_STATE", message="El documento no admite esa acción en su estado actual")

    if not observation or not observation.strip():
        raise KontrolError(code="IMPORT_DOCUMENT_OBSERVATION_REQUIRED", message="La observación es obligatoria", status_code=422)

    before = _document_key(document)
    document.observation = observation.strip()
    document.status = "OBSERVED"
    party_service.bump(document)
    party_service.bump(file)
    after = _document_key(document)

    _audit(
        db,
        action="IMPORT_DOCUMENT_CHANGED",
        file=file,
        actor_id=actor_id,
        tenant_id=tenant_id,
        before=before,
        after=after,
        reason=document.observation,
    )
    return document


def confirm_documents(
    db: Session,
    *,
    file: ImportFile,
    actor_id: str,
    tenant_id: str,
) -> ImportFile:
    if file.status != "ORDERED":
        raise ConflictError(code="IMPORT_INVALID_STATE", message="La importación no admite este cambio en su estado actual")

    documents = list(
        db.scalars(
            select(ImportDocument).where(
                ImportDocument.file_id == file.id,
                ImportDocument.company_id == file.company_id,
                ImportDocument.required.is_(True),
            )
        )
    )
    missing = [document.name for document in documents if document.status != "VALIDATED"]
    if missing:
        raise ConflictError(
            code="IMPORT_DOCUMENTS_INCOMPLETE",
            message="Falta validar documentos obligatorios",
            details={"missing": missing},
        )

    file.status = "DOCUMENTS_COMPLETE"
    party_service.bump(file)

    _audit(
        db,
        action="IMPORT_DOCUMENTS_CONFIRMED",
        file=file,
        actor_id=actor_id,
        tenant_id=tenant_id,
        after=_file_key(file, ("status",)),
    )
    return file


def cancel_file(
    db: Session,
    *,
    file: ImportFile,
    reason: str,
    actor_id: str,
    tenant_id: str,
) -> ImportFile:
    if file.status not in ("NEGOTIATING", "ORDERED"):
        raise ConflictError(code="IMPORT_INVALID_STATE", message="La importación no admite este cambio en su estado actual")

    if not reason or not reason.strip():
        raise KontrolError(code="IMPORT_CANCEL_REASON_REQUIRED", message="El motivo es obligatorio", status_code=422)

    before = _file_key(file, ("status",))
    file.status = "CANCELLED"
    file.cancel_reason = reason.strip()
    party_service.bump(file)
    after = _file_key(file, ("status",))

    _audit(
        db,
        action="IMPORT_FILE_CANCELLED",
        file=file,
        actor_id=actor_id,
        tenant_id=tenant_id,
        before=before,
        after=after,
        reason=file.cancel_reason,
    )
    return file


def _document_key(document: ImportDocument) -> dict[str, Any]:
    return {
        "document_id": str(document.id),
        "kind": document.kind,
        "reference": document.reference,
        "status": document.status,
    }


def allowed_actions(file: ImportFile) -> dict[str, bool]:
    return {
        "edit": file.status in ("NEGOTIATING", "ORDERED"),
        "link_order": file.status == "NEGOTIATING",
        "add_document": file.status in ("NEGOTIATING", "ORDERED"),
        "confirm_documents": file.status == "ORDERED",
        "cancel": file.status in ("NEGOTIATING", "ORDERED"),
    }


def next_action(file: ImportFile) -> str:
    if file.status == "NEGOTIATING":
        return "Completa la negociación y vincula la orden de compra aprobada."
    if file.status == "ORDERED":
        return "Recibe y valida la documentación obligatoria."
    if file.status == "DOCUMENTS_COMPLETE":
        return "Documentación completa. El seguimiento del embarque llegará en la siguiente entrega."
    return "Importación cancelada."


def file_summary(db: Session, file: ImportFile) -> dict[str, Any]:
    party = db.get(Party, file.supplier_id)
    supplier_name = party.name if party else None
    order_code = None
    if file.order_id:
        order = db.get(PurchaseOrder, file.order_id)
        if order:
            order_code = order.code

    return {
        "id": str(file.id),
        "code": file.code,
        "status": file.status,
        "currency": file.currency,
        "supplier_id": str(file.supplier_id),
        "supplier_name": supplier_name,
        "order_id": str(file.order_id) if file.order_id else None,
        "order_code": order_code,
        "incoterm": file.incoterm,
        "expected_arrival_date": file.expected_arrival_date.isoformat() if file.expected_arrival_date else None,
        "created_at": file.created_at.isoformat(),
        "version": file.version,
    }


def file_detail(db: Session, file: ImportFile) -> dict[str, Any]:
    result = file_summary(db, file)
    result.update(
        {
            "incoterm_place": file.incoterm_place,
            "payment_conditions": file.payment_conditions,
            "delivery_conditions": file.delivery_conditions,
            "expected_dispatch_date": file.expected_dispatch_date.isoformat() if file.expected_dispatch_date else None,
            "notes": file.notes,
            "cancel_reason": file.cancel_reason,
            "documents": _documents_detail(db, file),
            "allowed_actions": allowed_actions(file),
            "next_action": next_action(file),
        }
    )
    return result


def _documents_detail(db: Session, file: ImportFile) -> list[dict[str, Any]]:
    documents = list(
        db.scalars(
            select(ImportDocument).where(
                ImportDocument.file_id == file.id,
                ImportDocument.company_id == file.company_id,
            ).order_by(ImportDocument.name)
        )
    )
    result = []
    for document in documents:
        attachments = db.scalar(
            select(func.count()).select_from(DocumentLink).where(
                DocumentLink.resource_type == "ImportDocument",
                DocumentLink.resource_id == str(document.id),
                DocumentLink.company_id == file.company_id,
            )
        ) or 0
        item = {
            "id": str(document.id),
            "kind": document.kind,
            "name": document.name,
            "required": document.required,
            "reference": document.reference,
            "status": document.status,
            "observation": document.observation,
            "version": document.version,
            "attachments": attachments,
            "allowed_actions": {
                "receive": document.status in ("PENDING", "OBSERVED"),
                "validate": document.status == "RECEIVED",
                "observe": document.status in ("RECEIVED", "VALIDATED"),
            },
        }
        result.append(item)
    return result
