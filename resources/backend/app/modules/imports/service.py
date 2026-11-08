from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.documents.models import DocumentLink
from app.modules.identity_access.models import User
from app.modules.imports.models import (
    ImportCorrection,
    ImportDocument,
    ImportFile,
    ImportFinancialLink,
    ImportTrackingEvent,
)
from app.modules.master_data import party_service
from app.modules.master_data import service as master_service
from app.modules.master_data.models import Party
from app.modules.purchasing import service as ap_service
from app.modules.purchasing.models import Advance, Payment, PurchaseOrder
from app.shared.audit import record_audit
from app.shared.clock import hoy_de_negocio

INCOTERMS = ("EXW", "FCA", "CPT", "CIP", "DAP", "DPU", "DDP", "FAS", "FOB", "CFR", "CIF")
DOCUMENTOS_OBLIGATORIOS = (
    ("PROFORMA_INVOICE", "Factura proforma"),
    ("PACKING_LIST", "Packing list"),
    ("SHIPPING_DOCUMENT", "Documento de embarque"),
)

MILESTONES = ("BOOKED", "DEPARTED", "IN_TRANSIT", "TRANSSHIPMENT", "DELAYED", "OTHER")
CORRECTION_KINDS = ("FALTANTE", "CORRECCION_DOCUMENTAL")
CORRECTION_RESPONSIBLES = ("PROVEEDOR", "AGENTE", "IMPORTACION")
FINANCIAL_KINDS = ("PAYMENT", "ADVANCE")


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
    negotiation_fields = {
        "incoterm",
        "incoterm_place",
        "payment_conditions",
        "delivery_conditions",
        "expected_dispatch_date",
        "expected_arrival_date",
        "notes",
    }
    shipment_fields = {
        "agent_party_id",
        "carrier_party_id",
        "transport_document",
        "origin",
        "destination",
        "actual_departure_date",
    }

    requested = set(changes)
    has_negotiation = bool(requested & negotiation_fields)
    has_shipment = bool(requested & shipment_fields)

    if has_negotiation and file.status not in ("NEGOTIATING", "ORDERED"):
        raise ConflictError(code="IMPORT_INVALID_STATE", message="La importación no admite este cambio en su estado actual")
    if has_shipment and file.status not in ("NEGOTIATING", "ORDERED", "DOCUMENTS_COMPLETE", "DISPATCHED"):
        raise ConflictError(code="IMPORT_INVALID_STATE", message="La importación no admite este cambio en su estado actual")

    party_service.check_version(file, if_match)

    if "incoterm" in changes and changes["incoterm"] is not None and changes["incoterm"] not in INCOTERMS:
        raise KontrolError(code="IMPORT_INCOTERM_INVALID", message="INCOTERM no reconocido", status_code=422)

    if "agent_party_id" in changes and changes["agent_party_id"] is not None:
        master_service.require_eligible_party(
            db,
            company_id=file.company_id,
            party_id=changes["agent_party_id"],
            role=None,
            require_active=True,
        )

    if "carrier_party_id" in changes and changes["carrier_party_id"] is not None:
        master_service.require_eligible_party(
            db,
            company_id=file.company_id,
            party_id=changes["carrier_party_id"],
            role="TRANSPORTISTA",
            require_active=True,
        )

    # Auditar cada grupo solo si se modificó realmente y con sus claves permitidas.
    if has_negotiation:
        negotiation_before = _file_key(file, tuple(sorted(negotiation_fields)))
        for key in negotiation_fields:
            if key in changes:
                setattr(file, key, changes[key])
        party_service.bump(file)
        negotiation_after = _file_key(file, tuple(sorted(negotiation_fields)))
        if negotiation_before != negotiation_after:
            _audit(
                db,
                action="IMPORT_FILE_UPDATED",
                file=file,
                actor_id=actor_id,
                tenant_id=tenant_id,
                before=negotiation_before,
                after=negotiation_after,
            )

    if has_shipment:
        shipment_before = _file_key(file, tuple(sorted(shipment_fields)))
        for key in shipment_fields:
            if key in changes:
                setattr(file, key, changes[key])
        party_service.bump(file)
        shipment_after = _file_key(file, tuple(sorted(shipment_fields)))
        if shipment_before != shipment_after:
            _audit(
                db,
                action="IMPORT_SHIPMENT_UPDATED",
                file=file,
                actor_id=actor_id,
                tenant_id=tenant_id,
                before=shipment_before,
                after=shipment_after,
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
    if file.status not in ("NEGOTIATING", "ORDERED", "DOCUMENTS_COMPLETE", "DISPATCHED"):
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
    if file.status not in ("NEGOTIATING", "ORDERED", "DOCUMENTS_COMPLETE", "DISPATCHED"):
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
    if file.status not in ("NEGOTIATING", "ORDERED", "DOCUMENTS_COMPLETE", "DISPATCHED"):
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
    if file.status not in ("NEGOTIATING", "ORDERED", "DOCUMENTS_COMPLETE", "DISPATCHED"):
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

    if file.status == "DOCUMENTS_COMPLETE":
        file.status = "ORDERED"
        party_service.bump(file)

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


def add_tracking_event(
    db: Session,
    *,
    file: ImportFile,
    milestone: str,
    occurred_on: date,
    location: str | None,
    notes: str | None,
    actor_id: str,
    tenant_id: str,
) -> ImportTrackingEvent:
    if file.status not in ("ORDERED", "DOCUMENTS_COMPLETE", "DISPATCHED"):
        raise ConflictError(code="IMPORT_INVALID_STATE", message="La importación no admite este cambio en su estado actual")

    if milestone not in MILESTONES:
        raise KontrolError(code="IMPORT_TRACKING_MILESTONE_INVALID", message="Hito no reconocido", status_code=422)

    event = ImportTrackingEvent(
        company_id=file.company_id,
        file_id=file.id,
        milestone=milestone,
        occurred_on=occurred_on,
        location=location.strip() if location else None,
        notes=notes.strip() if notes else None,
    )
    db.add(event)
    db.flush()

    if milestone == "DEPARTED" and file.actual_departure_date is None:
        file.actual_departure_date = occurred_on
        party_service.bump(file)

    _audit(
        db,
        action="IMPORT_TRACKING_ADDED",
        file=file,
        actor_id=actor_id,
        tenant_id=tenant_id,
        after={
            "milestone": event.milestone,
            "occurred_on": event.occurred_on.isoformat(),
            "location": event.location,
            "notes": event.notes,
        },
    )
    return event


def register_payment_or_advance(
    db: Session,
    *,
    file: ImportFile,
    amount: Decimal,
    kind: str,
    actor_id: str,
    tenant_id: str,
) -> ImportFinancialLink:
    if file.status not in ("ORDERED", "DOCUMENTS_COMPLETE", "DISPATCHED"):
        raise ConflictError(code="IMPORT_INVALID_STATE", message="La importación no admite este cambio en su estado actual")

    if kind not in FINANCIAL_KINDS:
        raise KontrolError(code="IMPORT_FINANCIAL_KIND_INVALID", message="Tipo financiero no válido", status_code=422)

    if kind == "PAYMENT":
        target: ap_service.Payment | ap_service.Advance = ap_service.register_payment(
            db,
            company_id=file.company_id,
            party_id=str(file.supplier_id),
            amount=amount,
            currency=file.currency,
            actor=actor_id,
            direction="OUT",
        )
    else:
        target = ap_service.register_advance(
            db,
            company_id=file.company_id,
            party_id=str(file.supplier_id),
            amount=amount,
            currency=file.currency,
            actor=actor_id,
            direction="OUT",
        )

    link = ImportFinancialLink(
        company_id=file.company_id,
        file_id=file.id,
        kind=kind,
        target_id=str(target.id),
    )
    db.add(link)
    db.flush()

    _audit(
        db,
        action="IMPORT_FINANCIAL_LINKED",
        file=file,
        actor_id=actor_id,
        tenant_id=tenant_id,
        after={"kind": kind, "target_id": str(target.id)},
    )
    return link


def link_existing_financial(
    db: Session,
    *,
    file: ImportFile,
    kind: str,
    target_id: str,
    actor_id: str,
    tenant_id: str,
) -> ImportFinancialLink:
    if file.status not in ("ORDERED", "DOCUMENTS_COMPLETE", "DISPATCHED"):
        raise ConflictError(code="IMPORT_INVALID_STATE", message="La importación no admite este cambio en su estado actual")

    if kind not in FINANCIAL_KINDS:
        raise KontrolError(code="IMPORT_FINANCIAL_KIND_INVALID", message="Tipo financiero no válido", status_code=422)

    duplicate = db.scalar(
        select(ImportFinancialLink).where(
            ImportFinancialLink.company_id == file.company_id,
            ImportFinancialLink.kind == kind,
            ImportFinancialLink.target_id == target_id,
        )
    )
    if duplicate is not None:
        raise ConflictError(code="IMPORT_FINANCIAL_IN_USE", message="El documento financiero ya está vinculado")

    if kind == "PAYMENT":
        target: Payment | Advance | None = db.get(Payment, target_id)
    else:
        target = db.get(Advance, target_id)

    if target is None or target.company_id != file.company_id:
        raise NotFoundError(code="IMPORT_FINANCIAL_NOT_FOUND", message="Documento financiero no encontrado")

    if target.direction != "OUT":
        raise ConflictError(
            code="IMPORT_FINANCIAL_DIRECTION_INVALID",
            message="Solo documentos de salida pueden vincularse a una importación",
        )

    if str(target.party_id) != str(file.supplier_id):
        raise ConflictError(
            code="IMPORT_FINANCIAL_SUPPLIER_MISMATCH",
            message="El documento financiero pertenece a otro proveedor",
        )

    link = ImportFinancialLink(
        company_id=file.company_id,
        file_id=file.id,
        kind=kind,
        target_id=target_id,
    )
    db.add(link)
    db.flush()

    _audit(
        db,
        action="IMPORT_FINANCIAL_LINKED",
        file=file,
        actor_id=actor_id,
        tenant_id=tenant_id,
        after={"kind": kind, "target_id": target_id},
    )
    return link


def unlink_financial(
    db: Session,
    *,
    file: ImportFile,
    link: ImportFinancialLink,
    actor_id: str,
    tenant_id: str,
) -> None:
    if file.status not in ("ORDERED", "DOCUMENTS_COMPLETE", "DISPATCHED"):
        raise ConflictError(code="IMPORT_INVALID_STATE", message="La importación no admite este cambio en su estado actual")

    db.delete(link)
    db.flush()
    _audit(
        db,
        action="IMPORT_FINANCIAL_UNLINKED",
        file=file,
        actor_id=actor_id,
        tenant_id=tenant_id,
        after={"kind": link.kind, "target_id": link.target_id},
    )


def open_correction(
    db: Session,
    *,
    file: ImportFile,
    kind: str,
    description: str,
    responsible: str,
    document_id: str | None,
    action_required: str | None,
    actor_id: str,
    tenant_id: str,
) -> ImportCorrection:
    if file.status not in ("ORDERED", "DOCUMENTS_COMPLETE", "DISPATCHED"):
        raise ConflictError(code="IMPORT_INVALID_STATE", message="La importación no admite este cambio en su estado actual")

    if kind not in CORRECTION_KINDS:
        raise KontrolError(code="IMPORT_CORRECTION_KIND_INVALID", message="Tipo de corrección no válido", status_code=422)

    if responsible not in CORRECTION_RESPONSIBLES:
        raise KontrolError(code="IMPORT_CORRECTION_RESPONSIBLE_INVALID", message="Responsable no válido", status_code=422)

    if responsible == "AGENTE" and file.agent_party_id is None:
        raise ConflictError(code="IMPORT_AGENT_REQUIRED", message="Debe designar un agente antes de abrir esta corrección")

    if not description or not description.strip():
        raise KontrolError(code="IMPORT_CORRECTION_DESCRIPTION_REQUIRED", message="La descripción es obligatoria", status_code=422)

    if document_id is not None:
        _get_document(db, file.company_id, file, document_id)

    correction = ImportCorrection(
        company_id=file.company_id,
        file_id=file.id,
        document_id=document_id,
        kind=kind,
        description=description.strip(),
        action_required=action_required.strip() if action_required else None,
        responsible=responsible,
        status="OPEN",
        version=1,
    )
    db.add(correction)
    db.flush()

    if file.status == "DOCUMENTS_COMPLETE":
        file.status = "ORDERED"
        party_service.bump(file)

    _audit(
        db,
        action="IMPORT_CORRECTION_OPENED",
        file=file,
        actor_id=actor_id,
        tenant_id=tenant_id,
        after={
            "correction_id": str(correction.id),
            "kind": correction.kind,
            "responsible": correction.responsible,
            "status": correction.status,
        },
    )
    return correction


def resolve_correction(
    db: Session,
    *,
    file: ImportFile,
    correction: ImportCorrection,
    resolution: str,
    actor_id: str,
    tenant_id: str,
) -> ImportCorrection:
    if correction.status != "OPEN":
        raise ConflictError(code="IMPORT_CORRECTION_INVALID_STATE", message="La corrección no admite esa acción en su estado actual")

    if not resolution or not resolution.strip():
        raise KontrolError(code="IMPORT_CORRECTION_RESOLUTION_REQUIRED", message="La resolución es obligatoria", status_code=422)

    correction.resolution = resolution.strip()
    correction.status = "RESOLVED"
    correction.resolved_at = hoy_de_negocio()
    party_service.bump(correction)

    _audit(
        db,
        action="IMPORT_CORRECTION_RESOLVED",
        file=file,
        actor_id=actor_id,
        tenant_id=tenant_id,
        after={"correction_id": str(correction.id), "status": correction.status},
    )
    return correction


def cancel_correction(
    db: Session,
    *,
    file: ImportFile,
    correction: ImportCorrection,
    reason: str,
    actor_id: str,
    tenant_id: str,
) -> ImportCorrection:
    if correction.status != "OPEN":
        raise ConflictError(code="IMPORT_CORRECTION_INVALID_STATE", message="La corrección no admite esa acción en su estado actual")

    if not reason or not reason.strip():
        raise KontrolError(code="IMPORT_CORRECTION_CANCEL_REASON_REQUIRED", message="El motivo es obligatorio", status_code=422)

    correction.status = "CANCELLED"
    correction.resolution = reason.strip()
    correction.resolved_at = hoy_de_negocio()
    party_service.bump(correction)

    _audit(
        db,
        action="IMPORT_CORRECTION_CANCELLED",
        file=file,
        actor_id=actor_id,
        tenant_id=tenant_id,
        after={"correction_id": str(correction.id), "status": correction.status},
        reason=reason.strip(),
    )
    return correction


def confirm_documents(
    db: Session,
    *,
    file: ImportFile,
    actor_id: str,
    tenant_id: str,
) -> ImportFile:
    if file.status != "ORDERED":
        raise ConflictError(code="IMPORT_INVALID_STATE", message="La importación no admite este cambio en su estado actual")

    open_corrections = db.scalar(
        select(func.count())
        .select_from(ImportCorrection)
        .where(
            ImportCorrection.file_id == file.id,
            ImportCorrection.company_id == file.company_id,
            ImportCorrection.status == "OPEN",
        )
    ) or 0

    if open_corrections:
        raise ConflictError(
            code="IMPORT_CORRECTIONS_OPEN",
            message="Hay correcciones abiertas que impiden confirmar la documentación",
            details={"open": open_corrections},
        )

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


def confirm_dispatch(
    db: Session,
    *,
    file: ImportFile,
    actor_id: str,
    tenant_id: str,
) -> ImportFile:
    if file.status != "DOCUMENTS_COMPLETE":
        raise ConflictError(code="IMPORT_INVALID_STATE", message="La importación no admite este cambio en su estado actual")

    if file.actual_departure_date is None:
        raise ConflictError(
            code="IMPORT_DISPATCH_PRECONDITION",
            message="Registre la fecha real de salida antes de confirmar el despacho",
            details={"missing": ["actual_departure_date"]},
        )

    file.status = "DISPATCHED"
    file.dispatched_at = hoy_de_negocio()
    party_service.bump(file)

    _audit(
        db,
        action="IMPORT_DISPATCH_CONFIRMED",
        file=file,
        actor_id=actor_id,
        tenant_id=tenant_id,
        after=_file_key(file, ("status", "dispatched_at")),
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
    if file.status not in ("NEGOTIATING", "ORDERED", "DOCUMENTS_COMPLETE"):
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


def financial_candidates(
    db: Session,
    *,
    file: ImportFile,
    kind: str,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    target_model: Any
    if kind == "PAYMENT":
        target_model = ap_service.Payment
    else:
        target_model = ap_service.Advance

    linked_subq = (
        select(ImportFinancialLink.target_id)
        .where(
            ImportFinancialLink.company_id == file.company_id,
            ImportFinancialLink.kind == kind,
        )
        .subquery()
    )

    base_conditions = [
        target_model.company_id == file.company_id,
        target_model.party_id == file.supplier_id,
        target_model.direction == "OUT",
        ~target_model.id.in_(select(linked_subq.c.target_id)),
    ]
    query = select(target_model).where(*base_conditions)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    items_db = db.scalars(
        query.order_by(target_model.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()

    items = [
        {
            "id": str(item.id),
            "amount": str(item.amount),
            "currency": item.currency,
            "direction": item.direction,
            "party_id": str(item.party_id),
            "linked": False,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "status": item.status,
        }
        for item in items_db
    ]
    return {"items": items, "total": total or 0, "page": page, "page_size": page_size}


def _get_financial_link(
    db: Session,
    company_id: str,
    file: ImportFile,
    link_id: str,
) -> ImportFinancialLink:
    link = db.scalar(
        select(ImportFinancialLink).where(
            ImportFinancialLink.id == link_id,
            ImportFinancialLink.company_id == company_id,
            ImportFinancialLink.file_id == file.id,
        )
    )
    if link is None:
        raise NotFoundError(
            code="IMPORT_FINANCIAL_LINK_NOT_FOUND",
            message="Vínculo financiero no encontrado",
        )
    return link


def _get_correction(
    db: Session,
    company_id: str,
    file: ImportFile,
    correction_id: str,
) -> ImportCorrection:
    correction = db.scalar(
        select(ImportCorrection).where(
            ImportCorrection.id == correction_id,
            ImportCorrection.company_id == company_id,
            ImportCorrection.file_id == file.id,
        )
    )
    if correction is None:
        raise NotFoundError(
            code="IMPORT_CORRECTION_NOT_FOUND",
            message="Corrección no encontrada",
        )
    return correction


def eligible_orders(
    db: Session,
    *,
    file: ImportFile,
    q: str | None,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    stmt = select(PurchaseOrder).where(
        PurchaseOrder.company_id == file.company_id,
        PurchaseOrder.supplier_id == file.supplier_id,
        PurchaseOrder.currency == file.currency,
        PurchaseOrder.status.in_(("APPROVED", "PARTIALLY_RECEIVED", "RECEIVED")),
        ~PurchaseOrder.id.in_(
            select(ImportFile.order_id).where(
                ImportFile.company_id == file.company_id,
                ImportFile.order_id.is_not(None),
                ImportFile.status != "CANCELLED",
            )
        ),
    )

    if q:
        stmt = stmt.where(PurchaseOrder.code.ilike(f"%{q}%"))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    orders = list(
        db.scalars(
            stmt.order_by(PurchaseOrder.code)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    items = [
        {
            "id": str(order.id),
            "code": order.code,
            "name": f"Moneda {order.currency}",
        }
        for order in orders
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def _document_key(document: ImportDocument) -> dict[str, Any]:
    return {
        "document_id": str(document.id),
        "kind": document.kind,
        "reference": document.reference,
        "status": document.status,
    }


def allowed_actions(file: ImportFile) -> dict[str, bool]:
    return {
        "edit": file.status in ("NEGOTIATING", "ORDERED", "DOCUMENTS_COMPLETE", "DISPATCHED"),
        "link_order": file.status == "NEGOTIATING",
        "add_document": file.status in ("NEGOTIATING", "ORDERED", "DOCUMENTS_COMPLETE", "DISPATCHED"),
        "confirm_documents": file.status == "ORDERED",
        "confirm_dispatch": file.status == "DOCUMENTS_COMPLETE",
        "cancel": file.status in ("NEGOTIATING", "ORDERED", "DOCUMENTS_COMPLETE"),
    }


def next_action(file: ImportFile) -> str:
    if file.status == "NEGOTIATING":
        return "Completa la negociación y vincula la orden de compra aprobada."
    if file.status == "ORDERED":
        return "Recibe y valida la documentación obligatoria y gestiona correcciones abiertas."
    if file.status == "DOCUMENTS_COMPLETE":
        return "Confirma la salida real y el despacho de la mercancía."
    if file.status == "DISPATCHED":
        return "Importación despachada."
    return "Importación cancelada."


def _party_name(db: Session, party_id: str | None) -> str | None:
    if party_id is None:
        return None
    party = db.get(Party, party_id)
    return party.name if party else None


def file_summary(db: Session, file: ImportFile) -> dict[str, Any]:
    supplier_name = _party_name(db, str(file.supplier_id))
    agent_name = _party_name(db, file.agent_party_id)
    carrier_name = _party_name(db, file.carrier_party_id)
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
        "agent_name": agent_name,
        "carrier_name": carrier_name,
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
            "actual_departure_date": file.actual_departure_date.isoformat() if file.actual_departure_date else None,
            "transport_document": file.transport_document,
            "origin": file.origin,
            "destination": file.destination,
            "dispatched_at": file.dispatched_at.isoformat() if file.dispatched_at else None,
            "notes": file.notes,
            "cancel_reason": file.cancel_reason,
            "documents": _documents_detail(db, file),
            "tracking_events": _tracking_events_detail(db, file),
            "financial": _financial_detail(db, file),
            "corrections": _corrections_detail(db, file),
            "summary": _summary_detail(db, file),
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


def _tracking_events_detail(db: Session, file: ImportFile) -> list[dict[str, Any]]:
    events = list(
        db.scalars(
            select(ImportTrackingEvent).where(
                ImportTrackingEvent.file_id == file.id,
                ImportTrackingEvent.company_id == file.company_id,
            ).order_by(ImportTrackingEvent.occurred_on.desc(), ImportTrackingEvent.created_at.desc())
        )
    )
    result = []
    for event in events:
        user = db.get(User, event.created_by)
        username = user.username if user is not None else "desconocido"
        item = {
            "id": str(event.id),
            "milestone": event.milestone,
            "occurred_on": event.occurred_on.isoformat(),
            "location": event.location,
            "notes": event.notes,
            "username": username,
        }
        result.append(item)
    return result


def _financial_detail(db: Session, file: ImportFile) -> list[dict[str, Any]]:
    links = list(
        db.scalars(
            select(ImportFinancialLink).where(
                ImportFinancialLink.file_id == file.id,
                ImportFinancialLink.company_id == file.company_id,
            )
        )
    )
    result = []
    for link in links:
        target: Any = None
        if link.kind == "PAYMENT":
            target = db.get(ap_service.Payment, link.target_id)
        else:
            target = db.get(ap_service.Advance, link.target_id)
        if target is None:
            continue
        item = {
            "id": str(link.id),
            "kind": link.kind,
            "amount": str(target.amount),
            "currency": target.currency,
            "status": target.status,
            "date": target.created_at.date().isoformat(),
        }
        result.append(item)
    return result


def _corrections_detail(db: Session, file: ImportFile) -> list[dict[str, Any]]:
    corrections = list(
        db.scalars(
            select(ImportCorrection).where(
                ImportCorrection.file_id == file.id,
                ImportCorrection.company_id == file.company_id,
            ).order_by(ImportCorrection.created_at.desc())
        )
    )
    result = []
    for correction in corrections:
        responsible_name = "Responsable de importación"
        if correction.responsible == "PROVEEDOR":
            responsible_name = _party_name(db, str(file.supplier_id)) or "Proveedor"
        elif correction.responsible == "AGENTE" and file.agent_party_id:
            responsible_name = _party_name(db, file.agent_party_id) or "Agente"

        attachments = db.scalar(
            select(func.count()).select_from(DocumentLink).where(
                DocumentLink.resource_type == "ImportCorrection",
                DocumentLink.resource_id == str(correction.id),
                DocumentLink.company_id == file.company_id,
            )
        ) or 0

        item = {
            "id": str(correction.id),
            "document_id": str(correction.document_id) if correction.document_id else None,
            "kind": correction.kind,
            "description": correction.description,
            "action_required": correction.action_required,
            "responsible": correction.responsible,
            "responsible_name": responsible_name,
            "status": correction.status,
            "resolution": correction.resolution,
            "resolved_at": correction.resolved_at.isoformat() if correction.resolved_at else None,
            "version": correction.version,
            "attachments": attachments,
            "allowed_actions": {
                "resolve": correction.status == "OPEN",
                "cancel": correction.status == "OPEN",
            },
        }
        result.append(item)
    return result


def _summary_detail(db: Session, file: ImportFile) -> dict[str, Any]:
    pending: list[str] = []
    if file.status == "ORDERED":
        open_corrections = db.scalar(
            select(func.count()).select_from(ImportCorrection).where(
                ImportCorrection.file_id == file.id,
                ImportCorrection.company_id == file.company_id,
                ImportCorrection.status == "OPEN",
            )
        ) or 0
        if open_corrections:
            pending.append("Resuelva las correcciones abiertas antes de confirmar la documentación.")
        required = list(
            db.scalars(
                select(ImportDocument).where(
                    ImportDocument.file_id == file.id,
                    ImportDocument.company_id == file.company_id,
                    ImportDocument.required.is_(True),
                )
            )
        )
        missing = [document.name for document in required if document.status != "VALIDATED"]
        if missing:
            pending.append("Falta validar: " + ", ".join(missing) + ".")
    elif file.status == "DOCUMENTS_COMPLETE":
        if file.actual_departure_date is None:
            pending.append("Registre la fecha real de salida para confirmar el despacho.")

    documents = list(
        db.scalars(
            select(ImportDocument).where(
                ImportDocument.file_id == file.id,
                ImportDocument.company_id == file.company_id,
            )
        )
    )
    documents_validated = sum(1 for document in documents if document.status == "VALIDATED")
    documents_required = sum(1 for document in documents if document.required)
    open_corrections = db.scalar(
        select(func.count()).select_from(ImportCorrection).where(
            ImportCorrection.file_id == file.id,
            ImportCorrection.company_id == file.company_id,
            ImportCorrection.status == "OPEN",
        )
    ) or 0
    financial_count = db.scalar(
        select(func.count()).select_from(ImportFinancialLink).where(
            ImportFinancialLink.file_id == file.id,
            ImportFinancialLink.company_id == file.company_id,
        )
    ) or 0

    return {
        "pending": pending,
        "documents_validated": documents_validated,
        "documents_required": documents_required,
        "open_corrections": open_corrections,
        "financial_count": financial_count,
        "agent_name": _party_name(db, file.agent_party_id),
        "carrier_name": _party_name(db, file.carrier_party_id),
    }
