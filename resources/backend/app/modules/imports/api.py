"""API de expedientes de importación."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import ColumnElement, func, select
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_permission, require_write_allowed
from app.modules.audit.models import AuditEvent
from app.modules.identity_access.models import User
from app.modules.imports import service
from app.modules.imports.models import ImportFile
from app.shared.audit_catalog import label_of, safe_details
from app.shared.clock import InstanteDeEntrada

router = APIRouter(prefix="/importaciones", tags=["importaciones"])


class ReceiptBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=1, max_length=64)
    warehouse_id: str
    packing_list_ref: str | None = Field(default=None, max_length=120)
    supplier_invoice_ref: str | None = Field(default=None, max_length=120)
    packages_declared: int | None = Field(default=None, ge=0)
    unloading_scheduled_at: InstanteDeEntrada | None = None


class CreateImportFileBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=64)
    supplier_id: str
    currency: str = Field(default="VED", min_length=3, max_length=8)
    incoterm: str | None = Field(default=None, max_length=8)
    incoterm_place: str | None = Field(default=None, max_length=120)
    payment_conditions: str | None = None
    delivery_conditions: str | None = None
    expected_dispatch_date: date | None = None
    expected_arrival_date: date | None = None
    notes: str | None = None


class UpdateImportFileBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    incoterm: str | None = Field(default=None, max_length=8)
    incoterm_place: str | None = Field(default=None, max_length=120)
    payment_conditions: str | None = None
    delivery_conditions: str | None = None
    expected_dispatch_date: date | None = None
    expected_arrival_date: date | None = None
    notes: str | None = None
    agent_party_id: str | None = None
    carrier_party_id: str | None = None
    transport_document: str | None = None
    origin: str | None = None
    destination: str | None = None
    actual_departure_date: date | None = None


class LinkOrderBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: str


class AddDocumentBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=200)


class ReceiveDocumentBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reference: str = Field(min_length=1, max_length=120)


class ObserveDocumentBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observation: str = Field(min_length=1, max_length=255)


class CancelFileBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=255)


class TrackingEventBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    milestone: str = Field(min_length=1, max_length=32)
    occurred_on: date
    location: str | None = Field(default=None, max_length=120)
    notes: str | None = None


class PaymentBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str = Field(pattern="^(PAYMENT|ADVANCE)$")
    amount: Decimal = Field(gt=0, decimal_places=2)


class FinancialLinkBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str = Field(pattern="^(PAYMENT|ADVANCE)$")
    target_id: str


class CorrectionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str = Field(min_length=1, max_length=32)
    description: str = Field(min_length=1, max_length=1000)
    action_required: str | None = None
    responsible: str = Field(min_length=1, max_length=120)
    document_id: str | None = None


class ResolveCorrectionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resolution: str = Field(min_length=1, max_length=1000)


class CancelCorrectionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=255)


@router.get("")
def list_import_files(
    q: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("compras", "view")),
    ctx: CompanyContext = Depends(get_company_context),
):
    filtros: list[ColumnElement[bool]] = [ImportFile.company_id == ctx.company_id]
    if q:
        filtros.append(ImportFile.code.ilike(f"%{q}%"))
    if status:
        filtros.append(ImportFile.status == status)

    total = db.scalar(select(func.count()).select_from(ImportFile).where(*filtros)) or 0
    items = list(
        db.scalars(
            select(ImportFile)
            .where(*filtros)
            .order_by(ImportFile.created_at.desc(), ImportFile.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )

    return {
        "items": [service.file_summary(db, file) for file in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("", dependencies=[Depends(require_write_allowed)])
def create_import_file(
    body: CreateImportFileBody,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("compras", "create")),
    ctx: CompanyContext = Depends(get_company_context),
):
    file = service.create_file(
        db,
        company_id=ctx.company_id,
        actor_id=str(user.id),
        tenant_id=user.tenant_id,
        data=body.model_dump(),
    )
    db.commit()
    db.refresh(file)
    return service.file_detail(db, file)


@router.get("/eligible-orders")
def list_eligible_orders(
    file_id: str = Query(...),
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("compras", "view")),
    ctx: CompanyContext = Depends(get_company_context),
):
    file = service.get_file(db, ctx.company_id, file_id)
    return service.eligible_orders(db, file=file, q=q, page=page, page_size=page_size)


@router.get("/{file_id}")
def get_import_file(
    file_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("compras", "view")),
    ctx: CompanyContext = Depends(get_company_context),
):
    file = service.get_file(db, ctx.company_id, file_id)
    return service.file_detail(db, file)


@router.patch("/{file_id}", dependencies=[Depends(require_write_allowed)])
def patch_import_file(
    file_id: str,
    body: UpdateImportFileBody,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("compras", "create")),
    ctx: CompanyContext = Depends(get_company_context),
):
    file = service.get_file(db, ctx.company_id, file_id, for_update=True)
    file = service.update_file(
        db,
        file=file,
        actor_id=str(user.id),
        tenant_id=user.tenant_id,
        changes=body.model_dump(exclude_unset=True),
        if_match=if_match,
    )
    db.commit()
    db.refresh(file)
    return service.file_detail(db, file)


@router.post("/{file_id}/order", dependencies=[Depends(require_write_allowed)])
def link_order(
    file_id: str,
    body: LinkOrderBody,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("compras", "create")),
    ctx: CompanyContext = Depends(get_company_context),
):
    file = service.get_file(db, ctx.company_id, file_id, for_update=True)
    file = service.link_order(
        db,
        file=file,
        order_id=body.order_id,
        actor_id=str(user.id),
        tenant_id=user.tenant_id,
    )
    db.commit()
    db.refresh(file)
    return service.file_detail(db, file)


@router.post("/{file_id}/tracking", dependencies=[Depends(require_write_allowed)])
def add_tracking_event(
    file_id: str,
    body: TrackingEventBody,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("compras", "create")),
    ctx: CompanyContext = Depends(get_company_context),
):
    file = service.get_file(db, ctx.company_id, file_id, for_update=True)
    event = service.add_tracking_event(
        db,
        file=file,
        milestone=body.milestone,
        occurred_on=body.occurred_on,
        location=body.location,
        notes=body.notes,
        actor_id=str(user.id),
        tenant_id=user.tenant_id,
    )
    db.commit()
    db.refresh(file)
    db.refresh(event)
    return service.file_detail(db, file)


@router.post("/{file_id}/receipts", dependencies=[Depends(require_write_allowed)])
def create_receipt(
    file_id: str,
    body: ReceiptBody,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("compras", "create")),
    ctx: CompanyContext = Depends(get_company_context),
):
    file = service.get_file(db, ctx.company_id, file_id, for_update=True)
    receipt = service.create_file_receipt(
        db,
        file=file,
        code=body.code,
        warehouse_id=body.warehouse_id,
        packing_list_ref=body.packing_list_ref,
        supplier_invoice_ref=body.supplier_invoice_ref,
        packages_declared=body.packages_declared,
        unloading_scheduled_at=body.unloading_scheduled_at,
        actor_id=str(user.id),
        tenant_id=user.tenant_id,
    )
    db.commit()
    db.refresh(file)
    db.refresh(receipt)
    return service.file_detail(db, file)


@router.post("/{file_id}/payments", dependencies=[Depends(require_write_allowed)])
def register_payment_or_advance(
    file_id: str,
    body: PaymentBody,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("compras", "create")),
    ctx: CompanyContext = Depends(get_company_context),
):
    file = service.get_file(db, ctx.company_id, file_id, for_update=True)
    link = service.register_payment_or_advance(
        db,
        file=file,
        amount=body.amount,
        kind=body.kind,
        actor_id=str(user.id),
        tenant_id=user.tenant_id,
    )
    db.commit()
    db.refresh(file)
    db.refresh(link)
    return service.file_detail(db, file)


@router.post("/{file_id}/financial-links", dependencies=[Depends(require_write_allowed)])
def link_existing_financial(
    file_id: str,
    body: FinancialLinkBody,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("compras", "create")),
    ctx: CompanyContext = Depends(get_company_context),
):
    file = service.get_file(db, ctx.company_id, file_id, for_update=True)
    link = service.link_existing_financial(
        db,
        file=file,
        kind=body.kind,
        target_id=body.target_id,
        actor_id=str(user.id),
        tenant_id=user.tenant_id,
    )
    db.commit()
    db.refresh(file)
    db.refresh(link)
    return service.file_detail(db, file)


@router.delete(
    "/{file_id}/financial-links/{link_id}",
    dependencies=[Depends(require_write_allowed)],
)
def unlink_financial(
    file_id: str,
    link_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("compras", "create")),
    ctx: CompanyContext = Depends(get_company_context),
):
    file = service.get_file(db, ctx.company_id, file_id, for_update=True)
    link = service._get_financial_link(db, ctx.company_id, file, link_id)
    service.unlink_financial(
        db,
        file=file,
        link=link,
        actor_id=str(user.id),
        tenant_id=user.tenant_id,
    )
    db.commit()
    db.refresh(file)
    return service.file_detail(db, file)


@router.get("/{file_id}/financial-candidates")
def list_financial_candidates(
    file_id: str,
    kind: str = Query(pattern="^(PAYMENT|ADVANCE)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("compras", "view")),
    ctx: CompanyContext = Depends(get_company_context),
):
    file = service.get_file(db, ctx.company_id, file_id)
    return service.financial_candidates(db, file=file, kind=kind, page=page, page_size=page_size)



@router.post("/{file_id}/corrections", dependencies=[Depends(require_write_allowed)])
def open_correction(
    file_id: str,
    body: CorrectionBody,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("compras", "create")),
    ctx: CompanyContext = Depends(get_company_context),
):
    file = service.get_file(db, ctx.company_id, file_id, for_update=True)
    correction = service.open_correction(
        db,
        file=file,
        kind=body.kind,
        description=body.description,
        responsible=body.responsible,
        document_id=body.document_id,
        action_required=body.action_required,
        actor_id=str(user.id),
        tenant_id=user.tenant_id,
    )
    db.commit()
    db.refresh(file)
    db.refresh(correction)
    return service.file_detail(db, file)


@router.post(
    "/{file_id}/corrections/{correction_id}/resolve",
    dependencies=[Depends(require_write_allowed)],
)
def resolve_correction(
    file_id: str,
    correction_id: str,
    body: ResolveCorrectionBody,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("compras", "create")),
    ctx: CompanyContext = Depends(get_company_context),
):
    file = service.get_file(db, ctx.company_id, file_id, for_update=True)
    correction = service._get_correction(db, ctx.company_id, file, correction_id)
    correction = service.resolve_correction(
        db,
        file=file,
        correction=correction,
        resolution=body.resolution,
        actor_id=str(user.id),
        tenant_id=user.tenant_id,
    )
    db.commit()
    db.refresh(file)
    db.refresh(correction)
    return service.file_detail(db, file)


@router.post(
    "/{file_id}/corrections/{correction_id}/cancel",
    dependencies=[Depends(require_write_allowed)],
)
def cancel_correction(
    file_id: str,
    correction_id: str,
    body: CancelCorrectionBody,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("compras", "approve")),
    ctx: CompanyContext = Depends(get_company_context),
):
    file = service.get_file(db, ctx.company_id, file_id, for_update=True)
    correction = service._get_correction(db, ctx.company_id, file, correction_id)
    correction = service.cancel_correction(
        db,
        file=file,
        correction=correction,
        reason=body.reason,
        actor_id=str(user.id),
        tenant_id=user.tenant_id,
    )
    db.commit()
    db.refresh(file)
    db.refresh(correction)
    return service.file_detail(db, file)


@router.post("/{file_id}/confirm-dispatch", dependencies=[Depends(require_write_allowed)])
def confirm_dispatch(
    file_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("compras", "approve")),
    ctx: CompanyContext = Depends(get_company_context),
):
    file = service.get_file(db, ctx.company_id, file_id, for_update=True)
    file = service.confirm_dispatch(
        db,
        file=file,
        actor_id=str(user.id),
        tenant_id=user.tenant_id,
    )
    db.commit()
    db.refresh(file)
    return service.file_detail(db, file)


@router.post("/{file_id}/documents", dependencies=[Depends(require_write_allowed)])
def add_document(
    file_id: str,
    body: AddDocumentBody,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("compras", "create")),
    ctx: CompanyContext = Depends(get_company_context),
):
    file = service.get_file(db, ctx.company_id, file_id, for_update=True)
    document = service.add_document(
        db,
        file=file,
        kind=body.kind,
        name=body.name,
        actor_id=str(user.id),
        tenant_id=user.tenant_id,
    )
    db.commit()
    db.refresh(file)
    db.refresh(document)
    return service.file_detail(db, file)


@router.post("/{file_id}/documents/{document_id}/receive", dependencies=[Depends(require_write_allowed)])
def receive_document(
    file_id: str,
    document_id: str,
    body: ReceiveDocumentBody,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("compras", "create")),
    ctx: CompanyContext = Depends(get_company_context),
):
    file = service.get_file(db, ctx.company_id, file_id, for_update=True)
    document = service._get_document(db, ctx.company_id, file, document_id)
    document = service.receive_document(
        db,
        file=file,
        document=document,
        reference=body.reference,
        actor_id=str(user.id),
        tenant_id=user.tenant_id,
    )
    db.commit()
    db.refresh(file)
    db.refresh(document)
    return service.file_detail(db, file)


@router.post("/{file_id}/documents/{document_id}/validate", dependencies=[Depends(require_write_allowed)])
def validate_document(
    file_id: str,
    document_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("compras", "approve")),
    ctx: CompanyContext = Depends(get_company_context),
):
    file = service.get_file(db, ctx.company_id, file_id, for_update=True)
    document = service._get_document(db, ctx.company_id, file, document_id)
    document = service.validate_document(
        db,
        file=file,
        document=document,
        actor_id=str(user.id),
        tenant_id=user.tenant_id,
    )
    db.commit()
    db.refresh(file)
    db.refresh(document)
    return service.file_detail(db, file)


@router.post("/{file_id}/documents/{document_id}/observe", dependencies=[Depends(require_write_allowed)])
def observe_document(
    file_id: str,
    document_id: str,
    body: ObserveDocumentBody,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("compras", "approve")),
    ctx: CompanyContext = Depends(get_company_context),
):
    file = service.get_file(db, ctx.company_id, file_id, for_update=True)
    document = service._get_document(db, ctx.company_id, file, document_id)
    document = service.observe_document(
        db,
        file=file,
        document=document,
        observation=body.observation,
        actor_id=str(user.id),
        tenant_id=user.tenant_id,
    )
    db.commit()
    db.refresh(file)
    db.refresh(document)
    return service.file_detail(db, file)


@router.post("/{file_id}/confirm-documents", dependencies=[Depends(require_write_allowed)])
def confirm_documents(
    file_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("compras", "approve")),
    ctx: CompanyContext = Depends(get_company_context),
):
    file = service.get_file(db, ctx.company_id, file_id, for_update=True)
    file = service.confirm_documents(
        db,
        file=file,
        actor_id=str(user.id),
        tenant_id=user.tenant_id,
    )
    db.commit()
    db.refresh(file)
    return service.file_detail(db, file)


@router.post("/{file_id}/cancel", dependencies=[Depends(require_write_allowed)])
def cancel_file(
    file_id: str,
    body: CancelFileBody,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("compras", "approve")),
    ctx: CompanyContext = Depends(get_company_context),
):
    file = service.get_file(db, ctx.company_id, file_id, for_update=True)
    file = service.cancel_file(
        db,
        file=file,
        reason=body.reason,
        actor_id=str(user.id),
        tenant_id=user.tenant_id,
    )
    db.commit()
    db.refresh(file)
    return service.file_detail(db, file)


@router.get("/{file_id}/audit")
def import_file_audit(
    file_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("audit", "view")),
    ctx: CompanyContext = Depends(get_company_context),
):
    file = service.get_file(db, ctx.company_id, file_id)

    filtros = [
        AuditEvent.tenant_id == user.tenant_id,
        AuditEvent.company_id == file.company_id,
        AuditEvent.entity_type == "ImportFile",
        AuditEvent.entity_id == str(file.id),
    ]
    total = db.scalar(select(func.count()).select_from(AuditEvent).where(*filtros)) or 0
    items = list(
        db.scalars(
            select(AuditEvent)
            .where(*filtros)
            .order_by(AuditEvent.event_time.desc(), AuditEvent.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )

    usernames: dict[str, str] = {}
    ids = [e.user_id for e in items if e.user_id is not None]
    if ids:
        rows = db.execute(
            select(User.id, User.username).where(
                User.tenant_id == user.tenant_id, User.id.in_(ids)
            )
        ).all()
        usernames = {str(row.id): row.username for row in rows}

    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "items": [
            {
                "id": str(e.id),
                "action": e.action,
                "action_label": label_of(e.action, e.entity_type),
                "event_time": e.event_time.isoformat(),
                "username": usernames.get(str(e.user_id)) if e.user_id else None,
                "request_id": e.request_id,
                "reason": e.reason,
                "details": safe_details(
                    e.action, e.entity_type, e.before, e.after, e.evidence
                ),
            }
            for e in items
        ],
    }
