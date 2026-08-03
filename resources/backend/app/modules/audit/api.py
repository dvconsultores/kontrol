"""API de auditoría (FR-001-070/071/072)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.modules.audit.models import AuditEvent
from app.modules.identity_access.models import User

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/events")
def list_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    entity_type: str | None = None,
    entity_id: str | None = None,
    action: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("audit", "view")),
):
    query = select(AuditEvent).order_by(AuditEvent.event_time.desc())
    if entity_type:
        query = query.where(AuditEvent.entity_type == entity_type)
    if entity_id:
        query = query.where(AuditEvent.entity_id == entity_id)
    if action:
        query = query.where(AuditEvent.action == action)

    total = len(db.execute(query).scalars().all())
    items = db.execute(query.offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "items": [
            {
                "id": str(e.id),
                "action": e.action,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "user_id": e.user_id,
                "request_id": e.request_id,
                "source": e.source,
                "event_time": e.event_time.isoformat(),
            }
            for e in items
        ],
    }
