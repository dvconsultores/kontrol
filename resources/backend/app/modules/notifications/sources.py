"""Traducción de hechos de la 045 en efectos de la 047 (FR-047-054).

# Spec 047 · Consumo de hechos de aprobación

La 045 emite y no conoce a la 047 (CL-045-11). Aquí se **leen** sus hechos y el
estado que ella fijó —los elegibles del paso—; nunca se recalcula quién puede
aprobar, ni se decide nada por ella (FR-047-026).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.approvals.models import ApprovalEvent, ApprovalRequest, ApprovalStep
from app.modules.notifications import catalogo, service
from app.modules.notifications.models import NotificationRule

_CREADORES = {
    "NOTIFICATION": service.crear_notificacion,
    "TASK": service.crear_tarea,
    "ALERT": service.crear_alerta,
}


def aplicar_hecho_de_aprobacion(db: Session, evento: ApprovalEvent, *, correlation_id: str,
                                momento: datetime) -> str:
    """Aplica las reglas activas de **la empresa del hecho**. Devuelve el resultado del recibo."""
    company_id = evento.company_id
    solicitud = db.get(ApprovalRequest, evento.request_id) if evento.request_id else None
    if solicitud is None or solicitud.company_id != company_id:
        return "NO_RULE"

    if evento.event_type in catalogo.EVENTOS_DE_CIERRE:
        return _cerrar(db, evento, solicitud, momento)

    admitidos = catalogo.EVENTOS_CONSUMIBLES[catalogo.FUENTE_APROBACION].get(evento.event_type)
    if admitidos is None:
        return "NO_RULE"
    reglas = db.execute(select(NotificationRule).where(
        NotificationRule.company_id == company_id,
        NotificationRule.source == catalogo.FUENTE_APROBACION,
        NotificationRule.event_type == evento.event_type,
        NotificationRule.active.is_(True)).order_by(NotificationRule.code)).scalars().all()
    paso = db.get(ApprovalStep, evento.step_id) if evento.step_id else None
    if not reglas or paso is None or paso.request_id != solicitud.id:
        return "NO_RULE"

    origen = catalogo.ORIGENES["ApprovalRequest"]
    parametros = {"process_type": solicitud.process_type, "document_type": solicitud.document_type,
                  "level_order": paso.level_order}
    elegibles = frozenset(str(a) for a in (paso.eligible_actors or []))
    for regla in reglas:
        if regla.effect not in admitidos:
            continue
        clave = (f"rule:{regla.id}:item:{paso.id}:{evento.event_type}" if regla.effect == "TASK"
                 else f"rule:{regla.id}:event:{evento.id}")
        _CREADORES[regla.effect](db, service.Efecto(
            company_id=company_id, category=evento.event_type, severity=regla.severity,
            mandatory=regla.mandatory, message_key=f"{evento.event_type}.{regla.effect.lower()}",
            message_params=parametros, source_type="ApprovalRequest", source_id=str(solicitud.id),
            source_item_id=str(paso.id), route_key=origen.route_key, dedupe_key=clave,
            destinatarios=elegibles, rule_id=str(regla.id), source_event_id=str(evento.id),
            correlation_id=correlation_id, due_at=paso.due_at, priority_code=regla.priority_code))
    return "APPLIED"


def _cerrar(db: Session, evento: ApprovalEvent, solicitud: ApprovalRequest, momento: datetime) -> str:
    if evento.event_type == "approval.decided":
        paso = db.get(ApprovalStep, evento.step_id) if evento.step_id else None
        # Una decisión con quórum pendiente no cierra el paso: se lee el estado que
        # fijó la 045, no se deduce.
        if paso is None or paso.status == "IN_REVIEW":
            return "NO_RULE"
        item = str(paso.id)
    else:
        item = None
    cerradas = service.resolver_por_origen(db, company_id=solicitud.company_id,
                                           source_type="ApprovalRequest", source_id=str(solicitud.id),
                                           source_item_id=item, momento=momento)
    return "APPLIED" if cerradas else "NO_RULE"
