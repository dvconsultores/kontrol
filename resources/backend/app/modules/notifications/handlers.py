"""Manejadores de la Spec 047 que ejecuta el planificador (ADR-D0-015).

# Spec 047 · Manejadores programados

Cada manejador procesa cada ítem en su **propia transacción** y con el contexto
explícito de **su** empresa: un fallo en un ítem no arrastra a los demás, y ningún
efecto se crea en una empresa distinta de la de su origen (FR-047-046).
"""

from __future__ import annotations

from sqlalchemy import exists, literal_column, select
from sqlalchemy.exc import IntegrityError

from app.core.integrity import es_violacion_unica
from app.core.logging import get_logger
from app.modules.approvals.models import ApprovalEvent
from app.modules.notifications import catalogo, service, sources
from app.modules.notifications.models import (
    ESTADOS_TAREA_ABIERTOS,
    NotificationEventReceipt,
    NotificationRule,
    Task,
    TaskCandidate,
)

log = get_logger("kontrol.spec047.handlers")

#: Tope operacional por tick para que un hecho masivo no bloquee el tick
#: (FR-047-027). Lo que no cabe, entra en el siguiente.
LOTE_POR_TICK = 500
RECIBO = "uq_notification_event_receipts_source_event"
_MINUTO = literal_column("interval '1 minute'")


def consumir_hechos_de_aprobacion(contexto):
    """`approval_event_intake` — política `DRAIN`."""
    from app.modules.scheduler.service import Resultado

    resultado = Resultado()
    with contexto.session_factory() as db:
        pendientes = db.execute(
            select(ApprovalEvent.id)
            .where(~exists().where(NotificationEventReceipt.source == catalogo.FUENTE_APROBACION,
                                   NotificationEventReceipt.source_event_id == ApprovalEvent.id))
            .order_by(ApprovalEvent.occurred_at, ApprovalEvent.created_at, ApprovalEvent.id)
            .limit(LOTE_POR_TICK)
        ).scalars().all()

    for event_id in pendientes:
        resultado.seen += 1
        with contexto.session_factory() as db:
            try:
                evento = db.get(ApprovalEvent, event_id)
                recibo = NotificationEventReceipt(
                    company_id=evento.company_id, source=catalogo.FUENTE_APROBACION,
                    source_event_id=str(evento.id), event_type=evento.event_type,
                    outcome="NO_RULE", run_correlation_id=contexto.correlation_id)
                try:
                    with db.begin_nested():
                        db.add(recibo)
                        db.flush()
                except IntegrityError as e:
                    if not es_violacion_unica(e, RECIBO):
                        raise
                    resultado.skipped += 1
                    continue
                recibo.outcome = sources.aplicar_hecho_de_aprobacion(
                    db, evento, correlation_id=contexto.correlation_id, momento=contexto.now)
                db.commit()
                resultado.processed += 1
                log.info("spec047.event_consumed", extra={"event_id": str(event_id),
                                                          "outcome": recibo.outcome})
            except Exception as error:
                db.rollback()
                resultado.failed += 1
                log.warning("spec047.event_failed", extra={"event_id": str(event_id),
                                                           "error_code": type(error).__name__})
    return resultado


def _destinatarios_de(db, tarea: Task) -> frozenset[str]:
    if tarea.assignee_user_id:
        return frozenset({tarea.assignee_user_id})
    return frozenset(db.execute(select(TaskCandidate.user_id).where(TaskCandidate.task_id == tarea.id))
                     .scalars().all())


def recordatorios(contexto):
    """`task_reminders` — política `LATEST_WINDOW`: tras una caída, solo la ventana vigente."""
    from app.modules.scheduler.service import Resultado

    resultado = Resultado()
    with contexto.session_factory() as db:
        vencen = db.execute(
            select(Task.id)
            .join(NotificationRule, NotificationRule.id == Task.rule_id)
            .where(Task.status.in_(ESTADOS_TAREA_ABIERTOS), Task.due_at.is_not(None),
                   NotificationRule.active.is_(True),
                   NotificationRule.reminder_offset_minutes.is_not(None),
                   Task.due_at - NotificationRule.reminder_offset_minutes * _MINUTO <= contexto.now)
            .order_by(Task.company_id, Task.due_at, Task.id)
        ).scalars().all()

    for task_id in vencen:
        resultado.seen += 1
        with contexto.session_factory() as db:
            try:
                tarea = db.get(Task, task_id)
                regla = db.get(NotificationRule, tarea.rule_id)
                ventana = service.ventana_de_recordatorio(
                    due_at=tarea.due_at, offset_minutes=regla.reminder_offset_minutes,
                    repeat_minutes=regla.reminder_repeat_minutes, ahora=contexto.now)
                if ventana is None or not service.registrar_efecto_de_tarea(
                        db, tarea, "REMINDED", f"reminder:{regla.id}:{ventana}", contexto.now):
                    resultado.skipped += 1
                    db.rollback()
                    continue
                service.crear_notificacion(db, service.Efecto(
                    company_id=tarea.company_id, category=catalogo.CATEGORIA_RECORDATORIO,
                    severity=regla.severity, mandatory=regla.mandatory,
                    message_key="task.reminder.notification", message_params={},
                    source_type=tarea.source_type, source_id=tarea.source_id,
                    source_item_id=tarea.source_item_id, route_key=tarea.route_key,
                    dedupe_key=f"task:{tarea.id}:reminder:{regla.id}:{ventana}",
                    destinatarios=_destinatarios_de(db, tarea), rule_id=str(regla.id),
                    correlation_id=contexto.correlation_id))
                db.commit()
                resultado.processed += 1
            except Exception as error:
                db.rollback()
                resultado.failed += 1
                log.warning("spec047.reminder_failed", extra={"task_id": str(task_id),
                                                              "error_code": type(error).__name__})
    return resultado


def escaladas(contexto):
    """`task_escalations` — política `EFFECT_ONCE`."""
    from app.modules.scheduler.service import Resultado

    resultado = Resultado()
    with contexto.session_factory() as db:
        vencidas = db.execute(
            select(Task.id)
            .join(NotificationRule, NotificationRule.id == Task.rule_id)
            .where(Task.status.in_(ESTADOS_TAREA_ABIERTOS), Task.due_at.is_not(None),
                   NotificationRule.active.is_(True),
                   NotificationRule.escalation_after_minutes.is_not(None),
                   Task.due_at + NotificationRule.escalation_after_minutes * _MINUTO <= contexto.now)
            .order_by(Task.company_id, Task.due_at, Task.id)
        ).scalars().all()

    for task_id in vencidas:
        resultado.seen += 1
        with contexto.session_factory() as db:
            try:
                tarea = db.get(Task, task_id)
                regla = db.get(NotificationRule, tarea.rule_id)
                if not service.registrar_efecto_de_tarea(db, tarea, "ESCALATED",
                                                         f"escalation:{regla.id}", contexto.now):
                    resultado.skipped += 1
                    db.rollback()
                    continue
                log.info("spec047.task_overdue", extra={"task_id": str(tarea.id),
                                                        "company_id": tarea.company_id})
                service.crear_notificacion(db, service.Efecto(
                    company_id=tarea.company_id, category=catalogo.CATEGORIA_ESCALADA,
                    severity=regla.severity, mandatory=True,
                    message_key="task.escalation.notification", message_params={},
                    source_type=tarea.source_type, source_id=tarea.source_id,
                    source_item_id=tarea.source_item_id, route_key=tarea.route_key,
                    dedupe_key=f"task:{tarea.id}:escalation:{regla.id}",
                    destinatarios=frozenset(service.usuarios_con_rol(
                        db, role_id=regla.escalation_role_id, company_id=tarea.company_id)),
                    rule_id=str(regla.id), correlation_id=contexto.correlation_id))
                db.commit()
                resultado.processed += 1
            except Exception as error:
                db.rollback()
                resultado.failed += 1
                log.warning("spec047.escalation_failed", extra={"task_id": str(task_id),
                                                                "error_code": type(error).__name__})
    return resultado
