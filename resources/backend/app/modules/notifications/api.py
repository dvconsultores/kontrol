"""API de notificaciones, tareas y alertas (Spec 047).

# Spec 047 · API de notificaciones, tareas y alertas

Toda ruta es de empresa: la empresa la decide `X-Kontrol-Company`, nunca el
cuerpo. Las listas paginan con `page` y `page_size`. Las órdenes devuelven el
estado resultante, no un «ok».
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission, require_write_allowed
from app.modules.identity_access.models import User
from app.modules.notifications import service
from app.shared.clock import InstanteDeEntrada

router = APIRouter(tags=["notifications"])


# --------------------------------------------------------------------------- #
# Esquemas
# --------------------------------------------------------------------------- #
class MensajeOut(BaseModel):
    key: str
    params: dict[str, Any]
    text: str | None
    render_error: str | None


class EnlaceOut(BaseModel):
    source_type: str
    source_id: str
    source_item_id: str | None
    route_key: str


class NotificacionOut(BaseModel):
    id: str
    category: str
    severity: str
    mandatory: bool
    message: MensajeOut
    link: EnlaceOut
    created_at: datetime
    read_at: datetime | None
    archived_at: datetime | None


class PaginaNotificaciones(BaseModel):
    items: list[NotificacionOut]
    total: int
    page: int
    page_size: int


class TareaOut(BaseModel):
    id: str
    task_type: str
    status: str
    message: MensajeOut
    link: EnlaceOut
    priority_code: str | None
    priority_rank: int | None
    assignee_user_id: str | None
    due_at: datetime | None
    overdue: bool
    closed_at: datetime | None
    version: int
    created_at: datetime


class EventoTareaOut(BaseModel):
    id: str
    event_type: str
    actor_type: str
    actor_user_id: str | None
    from_user_id: str | None
    to_user_id: str | None
    reason: str | None
    occurred_at: datetime


class TareaDetalleOut(TareaOut):
    candidates: list[str]
    history: list[EventoTareaOut]
    allowed_actions: list[str]


class PaginaTareas(BaseModel):
    items: list[TareaOut]
    total: int
    page: int
    page_size: int


class AlertaOut(BaseModel):
    id: str
    category: str
    severity: str
    status: str
    message: MensajeOut
    link: EnlaceOut
    created_at: datetime
    resolved_at: datetime | None


class PaginaAlertas(BaseModel):
    items: list[AlertaOut]
    total: int
    page: int
    page_size: int


class ContadoresOut(BaseModel):
    unread_notifications: int
    open_tasks: int
    overdue_tasks: int
    active_alerts: int


class ReglaIn(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    source: Literal["APPROVAL"]
    event_type: str = Field(min_length=1, max_length=64)
    effect: Literal["NOTIFICATION", "TASK", "ALERT"]
    severity: Literal["INFO", "WARNING", "CRITICAL"] = "INFO"
    mandatory: bool = False
    priority_code: str | None = Field(default=None, max_length=32)
    reminder_offset_minutes: int | None = None
    reminder_repeat_minutes: int | None = None
    escalation_after_minutes: int | None = None
    escalation_role_id: str | None = None
    auto_close: bool = False


class ReglaOut(BaseModel):
    id: str
    code: str
    source: str
    event_type: str
    effect: str
    severity: str
    mandatory: bool
    priority_code: str | None
    reminder_offset_minutes: int | None
    reminder_repeat_minutes: int | None
    escalation_after_minutes: int | None
    escalation_role_id: str | None
    auto_close: bool
    active: bool
    created_at: datetime


class FuenteOut(BaseModel):
    source: str
    event_type: str
    effects: list[str]


class PrioridadIn(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=120)
    rank: int = Field(ge=0)


class PrioridadOut(BaseModel):
    id: str
    code: str
    name: str
    rank: int


class PreferenciaIn(BaseModel):
    category: str = Field(min_length=1, max_length=64)
    channel: Literal["INTERNAL", "EMAIL"]
    enabled: bool


class PreferenciaOut(BaseModel):
    category: str
    channel: str
    enabled: bool
    mandatory: bool
    available: bool = True


class MotivoIn(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class ReasignarIn(BaseModel):
    assignee_user_id: str
    reason: str | None = Field(default=None, max_length=500)


def _version(if_match: str | None) -> int | None:
    limpio = (if_match or "").strip().strip('"')
    return int(limpio) if limpio.isdigit() else None


# --------------------------------------------------------------------------- #
# Notificaciones
# --------------------------------------------------------------------------- #
@router.get("/notifications/counts", response_model=ContadoresOut)
def get_counts(db: Session = Depends(get_db), user: User = Depends(get_current_user),
               ctx: CompanyContext = Depends(get_company_context)):
    return service.contadores(db, ctx=ctx, user=user)


@router.get("/notifications/sources", response_model=list[FuenteOut])
def list_sources(_: User = Depends(require_permission("notificaciones", "configure")),
                 ctx: CompanyContext = Depends(get_company_context)):
    return service.listar_fuentes()


@router.get("/notifications/rules", response_model=list[ReglaOut])
def list_rules(db: Session = Depends(get_db),
               _: User = Depends(require_permission("notificaciones", "configure")),
               ctx: CompanyContext = Depends(get_company_context)):
    return service.listar_reglas(db, ctx=ctx)


@router.post("/notifications/rules", response_model=ReglaOut, status_code=201,
             dependencies=[Depends(require_write_allowed)])
def create_rule(body: ReglaIn, db: Session = Depends(get_db),
                _: User = Depends(require_permission("notificaciones", "configure")),
                ctx: CompanyContext = Depends(get_company_context)):
    regla = service.crear_regla(db, ctx=ctx, datos=body.model_dump())
    db.commit()
    return regla


@router.post("/notifications/rules/{rule_id}/deactivate", response_model=ReglaOut,
             dependencies=[Depends(require_write_allowed)])
def deactivate_rule(rule_id: str, db: Session = Depends(get_db),
                    _: User = Depends(require_permission("notificaciones", "configure")),
                    ctx: CompanyContext = Depends(get_company_context)):
    regla = service.desactivar_regla(db, ctx=ctx, rule_id=rule_id)
    db.commit()
    return regla


@router.get("/notifications/preferences", response_model=list[PreferenciaOut])
def list_preferences(db: Session = Depends(get_db), _: User = Depends(get_current_user),
                     ctx: CompanyContext = Depends(get_company_context)):
    return service.listar_preferencias(db, ctx=ctx)


@router.put("/notifications/preferences", response_model=PreferenciaOut,
            dependencies=[Depends(require_write_allowed)])
def save_preference(body: PreferenciaIn, db: Session = Depends(get_db),
                    _: User = Depends(get_current_user),
                    ctx: CompanyContext = Depends(get_company_context)):
    fila = service.guardar_preferencia(db, ctx=ctx, category=body.category, channel=body.channel,
                                       enabled=body.enabled)
    db.commit()
    return fila


@router.get("/notifications", response_model=PaginaNotificaciones)
def list_notifications(
        state: Literal["active", "unread", "read", "archived", "all"] = "active",
        category: str | None = None, severity: str | None = None, source_type: str | None = None,
        created_from: InstanteDeEntrada | None = None, created_to: InstanteDeEntrada | None = None,
        page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
        db: Session = Depends(get_db), user: User = Depends(get_current_user),
        ctx: CompanyContext = Depends(get_company_context)):
    return service.listar_notificaciones(db, ctx=ctx, user=user, state=state, category=category,
                                         severity=severity, source_type=source_type,
                                         created_from=created_from, created_to=created_to,
                                         page=page, page_size=page_size)


@router.get("/notifications/{notification_id}", response_model=NotificacionOut)
def get_notification(notification_id: str, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user),
                     ctx: CompanyContext = Depends(get_company_context)):
    return service.obtener_notificacion(db, ctx=ctx, user=user, notification_id=notification_id)


@router.post("/notifications/{notification_id}/read", response_model=NotificacionOut,
             dependencies=[Depends(require_write_allowed)])
def read_notification(notification_id: str, db: Session = Depends(get_db),
                      user: User = Depends(get_current_user),
                      ctx: CompanyContext = Depends(get_company_context)):
    datos = service.marcar_leida(db, ctx=ctx, user=user, notification_id=notification_id)
    db.commit()
    return datos


@router.post("/notifications/{notification_id}/archive", response_model=NotificacionOut,
             dependencies=[Depends(require_write_allowed)])
def archive_notification(notification_id: str, db: Session = Depends(get_db),
                         user: User = Depends(get_current_user),
                         ctx: CompanyContext = Depends(get_company_context)):
    datos = service.archivar(db, ctx=ctx, user=user, notification_id=notification_id)
    db.commit()
    return datos


# --------------------------------------------------------------------------- #
# Tareas
# --------------------------------------------------------------------------- #
@router.get("/tasks/priorities", response_model=list[PrioridadOut])
def list_priorities(db: Session = Depends(get_db), _: User = Depends(get_current_user),
                    ctx: CompanyContext = Depends(get_company_context)):
    return service.listar_prioridades(db, ctx=ctx)


@router.post("/tasks/priorities", response_model=PrioridadOut, status_code=201,
             dependencies=[Depends(require_write_allowed)])
def create_priority(body: PrioridadIn, db: Session = Depends(get_db),
                    _: User = Depends(require_permission("tareas", "configure")),
                    ctx: CompanyContext = Depends(get_company_context)):
    fila = service.crear_prioridad(db, ctx=ctx, code=body.code, name=body.name, rank=body.rank)
    db.commit()
    return fila


@router.get("/tasks", response_model=PaginaTareas)
def list_tasks(
        scope: Literal["involved", "mine", "pool", "all"] = "involved",
        status: Literal["OPEN", "IN_PROGRESS", "COMPLETED", "CANCELLED", "RESOLVED_BY_SOURCE"] | None = None,
        overdue: bool | None = None, priority: str | None = None, source_type: str | None = None,
        due_from: InstanteDeEntrada | None = None, due_to: InstanteDeEntrada | None = None,
        page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
        db: Session = Depends(get_db), user: User = Depends(get_current_user),
        ctx: CompanyContext = Depends(get_company_context)):
    return service.listar_tareas(db, ctx=ctx, user=user, scope=scope, status=status, overdue=overdue,
                                 priority=priority, source_type=source_type, due_from=due_from,
                                 due_to=due_to, page=page, page_size=page_size)


@router.get("/tasks/{task_id}", response_model=TareaDetalleOut)
def get_task(task_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user),
             ctx: CompanyContext = Depends(get_company_context)):
    return service.obtener_tarea(db, ctx=ctx, user=user, task_id=task_id)


@router.post("/tasks/{task_id}/start", response_model=TareaDetalleOut,
             dependencies=[Depends(require_write_allowed)])
def start_task(task_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user),
               ctx: CompanyContext = Depends(get_company_context)):
    datos = service.iniciar_tarea(db, ctx=ctx, user=user, task_id=task_id)
    db.commit()
    return datos


@router.post("/tasks/{task_id}/complete", response_model=TareaDetalleOut,
             dependencies=[Depends(require_write_allowed)])
def complete_task(task_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user),
                  ctx: CompanyContext = Depends(get_company_context)):
    datos = service.completar_tarea(db, ctx=ctx, user=user, task_id=task_id)
    db.commit()
    return datos


@router.post("/tasks/{task_id}/cancel", response_model=TareaDetalleOut,
             dependencies=[Depends(require_write_allowed)])
def cancel_task(task_id: str, body: MotivoIn, db: Session = Depends(get_db),
                user: User = Depends(get_current_user),
                ctx: CompanyContext = Depends(get_company_context)):
    datos = service.cancelar_tarea(db, ctx=ctx, user=user, task_id=task_id, reason=body.reason)
    db.commit()
    return datos


@router.post("/tasks/{task_id}/reassign", response_model=TareaDetalleOut,
             dependencies=[Depends(require_write_allowed)])
def reassign_task(task_id: str, body: ReasignarIn, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user),
                  ctx: CompanyContext = Depends(get_company_context),
                  if_match: str | None = Header(default=None, alias="If-Match")):
    datos = service.reasignar_tarea(db, ctx=ctx, user=user, task_id=task_id,
                                    assignee_user_id=body.assignee_user_id, reason=body.reason,
                                    expected_version=_version(if_match))
    db.commit()
    return datos


# --------------------------------------------------------------------------- #
# Alertas
# --------------------------------------------------------------------------- #
@router.get("/alerts", response_model=PaginaAlertas)
def list_alerts(status: Literal["ACTIVE", "RESOLVED"] | None = None,
                severity: Literal["INFO", "WARNING", "CRITICAL"] | None = None,
                source_type: str | None = None,
                page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                db: Session = Depends(get_db), user: User = Depends(require_permission("alertas", "view")),
                ctx: CompanyContext = Depends(get_company_context)):
    return service.listar_alertas(db, ctx=ctx, user=user, status=status, severity=severity,
                                  source_type=source_type, page=page, page_size=page_size)
