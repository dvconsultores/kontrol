"""Servicio de auditoría (FR-001-070/071/072, ADR-012).

Registra eventos append-only con contexto, antes/después, request_id y
evidencia. Los eventos de auditoría no se modifican ni eliminan.

Validación contra el catálogo cerrado antes de crear el evento
(FR-001-257/258, OD-AUD-04), correlación automática del request_id de la
petición en curso (FR-001-261) y frontera explícita para auditar rechazos
(OD-AUD-07).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import contexto_tecnico_actual, request_id_actual
from app.modules.audit.models import AuditEvent
from app.shared.audit_catalog import validate_event

ProveedorContexto = Callable[..., dict[str, Any] | None]
_proveedor_contexto: ProveedorContexto | None = None


def registrar_proveedor_contexto(proveedor: ProveedorContexto) -> None:
    """Un módulo de producto aporta el contexto institucional sin que el núcleo lo conozca."""
    global _proveedor_contexto
    _proveedor_contexto = proveedor


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
    request_id = request_id or request_id_actual.get()
    if company_id and not tenant_id:
        # El tenant se deduce de la empresa en vez de pedirlo dos veces: así el
        # rastro no puede acabar diciendo una empresa de un tenant y un tenant
        # distinto, que es una contradicción que nadie sabría resolver después.
        from app.modules.organization.models import Company

        empresa = db.get(Company, company_id)
        if empresa is not None:
            tenant_id = empresa.tenant_id

    # El catálogo es cerrado y falla cerrado: un evento no catalogado o
    # incompatible con su alcance no llega a añadirse a la sesión.
    validate_event(
        action=action,
        entity_type=entity_type,
        tenant_id=tenant_id,
        company_id=company_id,
        before=before,
        after=after,
        evidence=evidence,
    )

    contexto = None
    if _proveedor_contexto is not None:
        contexto = _proveedor_contexto(
            db,
            action=action,
            entity_type=entity_type,
            tenant_id=tenant_id,
            company_id=company_id,
            user_id=user_id,
        )

    if contexto is not None:
        tecnico = contexto_tecnico_actual.get()
        if tecnico is not None:
            session_id = session_id or tecnico.session_id
            ip = ip or tecnico.ip

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
        institutional_context=contexto,
    )
    db.add(event)
    # No se hace commit aquí: la operación padre define la transacción.
    return event


def record_audit_after_rollback(db: Session, **campos: Any) -> AuditEvent:
    """Frontera de las clases REJECTION y SECURITY_DENIAL (OD-AUD-07).

    La transacción de la operación rechazada se deshace y el evento se
    confirma en una transacción propia, así sobrevive al rechazo; es el mismo
    patrón que `authority._denegar`.
    """
    db.rollback()
    evento = record_audit(db, **campos)
    db.commit()
    return evento
