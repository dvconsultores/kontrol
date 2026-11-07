"""Registro explícito de manejadores del planificador (Spec 047 · FR-047-042).

# Spec 047 · Registro de manejadores

Código, Spec dueña, habilitado y política de recuperación, **en código**. Nadie
configura desde fuera qué función se ejecuta (R-D0-15-7). El orden importa: los
vencimientos van antes que el consumo de hechos para que un paso vencido se
notifique en el mismo tick.
"""

from __future__ import annotations

from sqlalchemy import select

from app.modules.scheduler.service import Contexto, Manejador, Resultado


def vencer_pasos_de_aprobacion(contexto: Contexto) -> Resultado:
    """Dueña 045. Invoca `mark_expired`, su contrato canónico, empresa por empresa.

    **Deshabilitado** (CL-047-14): un paso `EXPIRED` sale de la bandeja y la 045
    no tiene camino para reabrirlo. Habilitarlo lo decide la 045.
    """
    from app.modules.approvals import service as approvals_service
    from app.modules.approvals.models import ApprovalRequest, ApprovalStep

    resultado = Resultado()
    with contexto.session_factory() as db:
        empresas = db.execute(
            select(ApprovalRequest.company_id).join(ApprovalStep, ApprovalStep.request_id == ApprovalRequest.id)
            .where(ApprovalStep.status == "IN_REVIEW", ApprovalStep.due_at.is_not(None),
                   ApprovalStep.due_at <= contexto.now)
            .distinct().order_by(ApprovalRequest.company_id)
        ).scalars().all()
    for company_id in empresas:
        resultado.seen += 1
        with contexto.session_factory() as db:
            resultado.processed += approvals_service.mark_expired(db, company_id=company_id, now=contexto.now)
            db.commit()
    return resultado


def manejadores() -> tuple[Manejador, ...]:
    from app.modules.notifications import delivery, handlers
    from app.ops import backup_job

    return (
        Manejador("approval_step_expiration", "045", False, "OWNER_IDEMPOTENT", vencer_pasos_de_aprobacion),
        Manejador("approval_event_intake", "047", True, "DRAIN", handlers.consumir_hechos_de_aprobacion),
        Manejador("task_reminders", "047", True, "LATEST_WINDOW", handlers.recordatorios),
        Manejador("task_escalations", "047", True, "EFFECT_ONCE", handlers.escaladas),
        Manejador("notification_delivery", "047", True, "DUE_RETRY", delivery.entregar),
        Manejador("installation_backup", "001", True, "LATEST_WINDOW", backup_job.ejecutar_copia),
        Manejador("backup_retention", "001", True, "OWNER_IDEMPOTENT", backup_job.aplicar_retencion),
        Manejador("backup_rpo_evaluation", "001", True, "OWNER_IDEMPOTENT", backup_job.evaluar_rpo),
    )
