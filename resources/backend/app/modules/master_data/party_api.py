"""API de Terceros: creación y edición con versión optimista."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_permission, require_write_allowed
from app.modules.audit.models import AuditEvent
from app.modules.identity_access.models import User
from app.modules.master_data import party_service
from app.shared.audit_catalog import label_of, safe_details

router = APIRouter(prefix="/maestros", tags=["maestros"])


@router.get("/terceros/{party_id}")
def get_party(
    party_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("maestros", "view")),
    ctx: CompanyContext = Depends(get_company_context),
):
    party = party_service.get_party(db, ctx.company_id, party_id, for_update=False)
    return party_service.party_detail(db, party)


@router.get("/terceros/{party_id}/audit")
def party_audit(
    party_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("audit", "view")),
    ctx: CompanyContext = Depends(get_company_context),
):
    party = party_service.get_party(db, ctx.company_id, party_id, for_update=False)

    filtros = [
        AuditEvent.tenant_id == user.tenant_id,
        AuditEvent.company_id == party.company_id,
        AuditEvent.entity_type == "Party",
        AuditEvent.entity_id == str(party.id),
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


@router.post("/terceros/{party_id}/activate", dependencies=[Depends(require_write_allowed)])
def activate_party(
    party_id: str,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("maestros", "edit")),
    ctx: CompanyContext = Depends(get_company_context),
):
    party = party_service.get_party(db, ctx.company_id, party_id, for_update=True)
    party = party_service.activate_party(
        db,
        party=party,
        actor_id=str(actor.id),
        tenant_id=ctx.tenant_id,
    )
    db.commit()
    db.refresh(party)
    return party_service.party_detail(db, party)


@router.post("/terceros/{party_id}/deactivate", dependencies=[Depends(require_write_allowed)])
def deactivate_party(
    party_id: str,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("maestros", "deactivate")),
    ctx: CompanyContext = Depends(get_company_context),
):
    party = party_service.get_party(db, ctx.company_id, party_id, for_update=True)
    party = party_service.deactivate_party(
        db,
        party=party,
        actor_id=str(actor.id),
        tenant_id=ctx.tenant_id,
    )
    db.commit()
    db.refresh(party)
    return party_service.party_detail(db, party)


@router.post("/terceros/{party_id}/roles/{role}", dependencies=[Depends(require_write_allowed)])
def add_party_role(
    party_id: str,
    role: str,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("maestros", "edit")),
    ctx: CompanyContext = Depends(get_company_context),
):
    party = party_service.get_party(db, ctx.company_id, party_id, for_update=True)
    party = party_service.add_role(
        db,
        party=party,
        role=role,
        actor_id=str(actor.id),
        tenant_id=ctx.tenant_id,
    )
    db.commit()
    db.refresh(party)
    return party_service.party_detail(db, party)


@router.delete("/terceros/{party_id}/roles/{role}", dependencies=[Depends(require_write_allowed)])
def remove_party_role(
    party_id: str,
    role: str,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("maestros", "edit")),
    ctx: CompanyContext = Depends(get_company_context),
):
    party = party_service.get_party(db, ctx.company_id, party_id, for_update=True)
    party = party_service.remove_role(
        db,
        party=party,
        role=role,
        actor_id=str(actor.id),
        tenant_id=ctx.tenant_id,
    )
    db.commit()
    db.refresh(party)
    return party_service.party_detail(db, party)


@router.delete("/terceros/{party_id}", dependencies=[Depends(require_write_allowed)])
def delete_party(
    party_id: str,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("maestros", "deactivate")),
    ctx: CompanyContext = Depends(get_company_context),
):
    party = party_service.get_party(db, ctx.company_id, party_id, for_update=True)
    party_service.delete_party(
        db,
        party=party,
        actor_id=str(actor.id),
        tenant_id=ctx.tenant_id,
    )
    db.commit()
    return {"deleted": True}


class PartyCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    person_type: str = "JURIDICA"
    nationality: str | None = None
    residence: str | None = None
    legal_name: str | None = None
    trade_name: str | None = None
    tax_id: str | None = None
    economic_activity: str | None = None
    roles: list[str] = Field(default_factory=lambda: ["CLIENTE"])


class PartyUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    person_type: str | None = None
    nationality: str | None = None
    residence: str | None = None
    legal_name: str | None = None
    trade_name: str | None = None
    tax_id: str | None = None
    economic_activity: str | None = None


@router.post("/terceros", dependencies=[Depends(require_write_allowed)])
def create_party(
    body: PartyCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("maestros", "create")),
    ctx: CompanyContext = Depends(get_company_context),
):
    party = party_service.create_party(
        db,
        company_id=ctx.company_id,
        actor_id=str(actor.id),
        tenant_id=ctx.tenant_id,
        data=body.model_dump(),
    )
    db.commit()
    db.refresh(party)
    return party_service.party_dict(party)


@router.patch("/terceros/{party_id}", dependencies=[Depends(require_write_allowed)])
def update_party(
    party_id: str,
    body: PartyUpdate,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("maestros", "edit")),
    ctx: CompanyContext = Depends(get_company_context),
):
    party = party_service.get_party(db, ctx.company_id, party_id, for_update=True)
    party_service.check_version(party, if_match)
    party = party_service.update_party(
        db,
        party=party,
        actor_id=str(actor.id),
        tenant_id=ctx.tenant_id,
        changes=body.model_dump(exclude_unset=True),
    )
    db.commit()
    db.refresh(party)
    return party_service.party_dict(party)
