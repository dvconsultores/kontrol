"""Servicio de auditoría (FR-001-070/071/072, ADR-012).

Registra eventos append-only con contexto, antes/después, request_id y
evidencia. Los eventos de auditoría no se modifican ni eliminan.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.modules.audit.models import AuditEvent


def _now() -> datetime:
    return datetime.now(UTC)


def record_audit(
    db: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    tenant_id: str | None = None,
    company_id: str | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
    request_id: str | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    source: str = "API",
    reason: str | None = None,
    evidence: dict[str, Any] | None = None,
    ip: str | None = None,
) -> AuditEvent:
    event = AuditEvent(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        tenant_id=tenant_id,
        company_id=company_id,
        user_id=user_id,
        session_id=session_id,
        request_id=request_id,
        before=before,
        after=after,
        source=source,
        reason=reason,
        evidence=evidence,
        ip=ip,
        event_time=_now(),
    )
    db.add(event)
    # No se hace commit aquí: la operación padre define la transacción.
    return event
