"""Servicio de notificaciones, tareas y alertas (Spec 047).

# Spec 047 · Servicio de notificaciones, tareas y alertas

El servicio **no confirma transacciones**: lo hace la ruta o el manejador que lo
llama. Toda creación es idempotente por `dedupe_key`, capturando solo la
violación única de su propia restricción (P25).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, exists, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, accessible_company_ids
from app.core.errors import ConflictError, KontrolError, NotFoundError, PermissionDeniedError
from app.core.integrity import es_violacion_unica
from app.core.logging import get_logger
from app.modules.identity_access import authority
from app.modules.identity_access.models import Role, User, UserRole, UserScope
from app.modules.notifications import catalogo, delivery
from app.modules.notifications.messages import MensajeInvalido, renderizar, texto, validar
from app.modules.notifications.models import (
    CANALES_EXTERNOS,
    EFECTOS,
    ESTADOS_TAREA_ABIERTOS,
    SEVERIDADES,
    Alert,
    Notification,
    NotificationDelivery,
    NotificationPreference,
    NotificationRecipient,
    NotificationRule,
    Task,
    TaskCandidate,
    TaskEvent,
    TaskPriority,
)
from app.modules.organization.models import Company
from app.shared.audit import record_audit

log = get_logger("kontrol.spec047")


# --------------------------------------------------------------------------- #
# Actor y reloj
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Actor:
    """Quién produce el efecto. El sistema no finge ser un usuario (FR-047-045)."""

    tipo: str
    user_id: str | None = None

    @property
    def fuente_auditoria(self) -> str:
        return "SCHEDULER" if self.tipo == "SYSTEM" else "API"


SISTEMA = Actor("SYSTEM")


def persona(user_id: str) -> Actor:
    return Actor("USER", str(user_id))


def asegurar_zona(momento: datetime) -> datetime:
    """Ningún vencimiento se calcula con un reloj sin zona (NFR-047-01)."""
    if momento.tzinfo is None or momento.utcoffset() is None:
        raise ValueError("NAIVE_DATETIME")
    return momento


def _ahora() -> datetime:
    return datetime.now(UTC)


def _auditar(db: Session, *, accion: str, entidad: str, entidad_id: str, company_id: str,
             actor: Actor, after: dict[str, Any] | None = None,
             before: dict[str, Any] | None = None, reason: str | None = None) -> None:
    record_audit(db, action=accion, entity_type=entidad, entity_id=entidad_id,
                 company_id=company_id, user_id=actor.user_id, source=actor.fuente_auditoria,
                 before=before, after=after, reason=reason)


# --------------------------------------------------------------------------- #
# Destinatarios
# --------------------------------------------------------------------------- #
def _usuarios_del_tenant(db: Session, company_id: str, ids: set[str]) -> set[str]:
    """Solo usuarios del tenant de la empresa. Un id ajeno no llega a destinatario."""
    if not ids:
        return set()
    tenant_id = db.execute(select(Company.tenant_id).where(Company.id == company_id)).scalar_one()
    return set(db.execute(select(User.id).where(User.id.in_(ids), User.tenant_id == tenant_id))
               .scalars().all())


def usuarios_con_rol(db: Session, *, role_id: str, company_id: str) -> set[str]:
    """Quienes tienen el rol **en** esta empresa: mismo tenant y acceso a la empresa."""
    tenant_id = db.execute(select(Company.tenant_id).where(Company.id == company_id)).scalar_one()
    candidatos = set(db.execute(
        select(User.id).join(UserRole, UserRole.user_id == User.id)
        .where(UserRole.role_id == role_id,
               or_(UserRole.company_id.is_(None), UserRole.company_id == company_id),
               User.tenant_id == tenant_id)
    ).scalars().all())
    if not candidatos:
        return set()
    con_ambito = set(db.execute(
        select(UserScope.user_id).where(UserScope.user_id.in_(candidatos),
                                        UserScope.company_id.is_not(None))
    ).scalars().all())
    con_esta = set(db.execute(
        select(UserScope.user_id).where(UserScope.user_id.in_(candidatos),
                                        UserScope.company_id == company_id)
    ).scalars().all())
    return {u for u in candidatos if u not in con_ambito or u in con_esta}


def _filtrar_por_preferencia(db: Session, *, company_id: str, category: str, mandatory: bool,
                             usuarios: set[str]) -> set[str]:
    if mandatory or not usuarios:
        return usuarios
    apagados = set(db.execute(
        select(NotificationPreference.user_id).where(
            NotificationPreference.company_id == company_id,
            NotificationPreference.category == category,
            NotificationPreference.channel == "INTERNAL",
            NotificationPreference.enabled.is_(False),
            NotificationPreference.user_id.in_(usuarios))
    ).scalars().all())
    return usuarios - apagados


def _validar_mensaje(clave: str, parametros: dict[str, Any]) -> None:
    try:
        validar(clave, parametros)
    except MensajeInvalido as e:
        raise KontrolError(code="NOTIFICATION_MESSAGE_INVALID",
                           message=texto("error.message_invalid", code=e.codigo),
                           details={"message_error": e.codigo}, status_code=422) from None


def _por_clave(db: Session, modelo, company_id: str, dedupe_key: str):
    return db.execute(select(modelo).where(modelo.company_id == company_id,
                                           modelo.dedupe_key == dedupe_key)).scalars().first()


def _insertar_unico(db: Session, fila, restriccion: str) -> bool:
    """Inserta en un savepoint. `False` si otra transacción ya la creó."""
    try:
        with db.begin_nested():
            db.add(fila)
            db.flush()
    except IntegrityError as e:
        if not es_violacion_unica(e, restriccion):
            raise
        return False
    return True


# --------------------------------------------------------------------------- #
# Publicación (FR-047-001, 005, 010, 015)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Efecto:
    """Todo lo que hace falta para crear un ítem, ya decidido por quien publica."""

    company_id: str
    category: str
    severity: str
    message_key: str
    message_params: dict[str, Any]
    source_type: str
    source_id: str
    route_key: str
    dedupe_key: str
    destinatarios: frozenset[str] = frozenset()
    mandatory: bool = False
    source_item_id: str | None = None
    rule_id: str | None = None
    source_event_id: str | None = None
    correlation_id: str | None = None
    due_at: datetime | None = None
    priority_code: str | None = None


def crear_notificacion(db: Session, efecto: Efecto, actor: Actor = SISTEMA) -> tuple[Notification, bool]:
    _validar_mensaje(efecto.message_key, efecto.message_params)
    existente = _por_clave(db, Notification, efecto.company_id, efecto.dedupe_key)
    if existente is not None:
        log.info("spec047.duplicate_suppressed", extra={"dedupe_key": efecto.dedupe_key})
        return existente, False
    n = Notification(
        company_id=efecto.company_id, rule_id=efecto.rule_id, category=efecto.category,
        severity=efecto.severity, mandatory=efecto.mandatory, message_key=efecto.message_key,
        message_params=dict(efecto.message_params), source_type=efecto.source_type,
        source_id=efecto.source_id, source_item_id=efecto.source_item_id,
        route_key=efecto.route_key, dedupe_key=efecto.dedupe_key,
        source_event_id=efecto.source_event_id, correlation_id=efecto.correlation_id,
        actor_type=actor.tipo, actor_user_id=actor.user_id)
    if not _insertar_unico(db, n, "uq_notifications_company_dedupe"):
        log.info("spec047.duplicate_suppressed", extra={"dedupe_key": efecto.dedupe_key})
        return _por_clave(db, Notification, efecto.company_id, efecto.dedupe_key), False

    usuarios = _usuarios_del_tenant(db, efecto.company_id, set(efecto.destinatarios))
    usuarios = _filtrar_por_preferencia(db, company_id=efecto.company_id, category=efecto.category,
                                        mandatory=efecto.mandatory, usuarios=usuarios)
    filas = [NotificationRecipient(notification_id=str(n.id), company_id=efecto.company_id, user_id=u)
             for u in sorted(usuarios)]
    db.add_all(filas)
    db.flush()
    _crear_entregas(db, efecto, filas)
    _auditar(db, accion="NOTIFICATION_CREATED", entidad="Notification", entidad_id=str(n.id),
             company_id=efecto.company_id, actor=actor,
             after={"category": efecto.category, "dedupe_key": efecto.dedupe_key,
                    "recipients": len(filas), "source_event_id": efecto.source_event_id})
    log.info("spec047.notification_created", extra={"notification_id": str(n.id),
                                                    "company_id": efecto.company_id})
    return n, True


def _crear_entregas(db: Session, efecto: Efecto, destinatarios: list[NotificationRecipient]) -> None:
    for canal in CANALES_EXTERNOS:
        if canal not in delivery.PROVEEDORES or not destinatarios:
            continue
        activos = set(db.execute(select(NotificationPreference.user_id).where(
            NotificationPreference.company_id == efecto.company_id,
            NotificationPreference.category == efecto.category,
            NotificationPreference.channel == canal,
            NotificationPreference.enabled.is_(True))).scalars().all())
        for r in destinatarios:
            if r.user_id in activos:
                db.add(NotificationDelivery(recipient_id=str(r.id), company_id=efecto.company_id,
                                            channel=canal, status="PENDING"))
    db.flush()


def _rango_prioridad(db: Session, company_id: str, code: str | None) -> int | None:
    if not code:
        return None
    return db.execute(select(TaskPriority.rank).where(TaskPriority.company_id == company_id,
                                                      TaskPriority.code == code)).scalar_one_or_none()


def crear_tarea(db: Session, efecto: Efecto, actor: Actor = SISTEMA) -> tuple[Task, bool]:
    _validar_mensaje(efecto.message_key, efecto.message_params)
    if efecto.due_at is not None:
        asegurar_zona(efecto.due_at)
    existente = _por_clave(db, Task, efecto.company_id, efecto.dedupe_key)
    if existente is not None:
        log.info("spec047.duplicate_suppressed", extra={"dedupe_key": efecto.dedupe_key})
        return existente, False
    t = Task(
        company_id=efecto.company_id, rule_id=efecto.rule_id, task_type=efecto.category,
        message_key=efecto.message_key, message_params=dict(efecto.message_params),
        source_type=efecto.source_type, source_id=efecto.source_id,
        source_item_id=efecto.source_item_id, route_key=efecto.route_key, status="OPEN",
        priority_code=efecto.priority_code,
        priority_rank=_rango_prioridad(db, efecto.company_id, efecto.priority_code),
        due_at=efecto.due_at, dedupe_key=efecto.dedupe_key,
        source_event_id=efecto.source_event_id, correlation_id=efecto.correlation_id,
        actor_type=actor.tipo, actor_user_id=actor.user_id, version=1)
    if not _insertar_unico(db, t, "uq_tasks_company_dedupe"):
        log.info("spec047.duplicate_suppressed", extra={"dedupe_key": efecto.dedupe_key})
        return _por_clave(db, Task, efecto.company_id, efecto.dedupe_key), False
    candidatos = _usuarios_del_tenant(db, efecto.company_id, set(efecto.destinatarios))
    db.add_all([TaskCandidate(task_id=str(t.id), company_id=efecto.company_id, user_id=u)
                for u in sorted(candidatos)])
    _evento(db, t, "CREATED", actor)
    db.flush()
    _auditar(db, accion="TASK_CREATED", entidad="Task", entidad_id=str(t.id),
             company_id=efecto.company_id, actor=actor,
             after={"task_type": efecto.category, "candidates": len(candidatos),
                    "dedupe_key": efecto.dedupe_key})
    return t, True


def crear_alerta(db: Session, efecto: Efecto, actor: Actor = SISTEMA) -> tuple[Alert, bool]:
    _validar_mensaje(efecto.message_key, efecto.message_params)
    existente = _por_clave(db, Alert, efecto.company_id, efecto.dedupe_key)
    if existente is not None:
        return existente, False
    a = Alert(
        company_id=efecto.company_id, rule_id=efecto.rule_id, category=efecto.category,
        severity=efecto.severity, message_key=efecto.message_key,
        message_params=dict(efecto.message_params), source_type=efecto.source_type,
        source_id=efecto.source_id, source_item_id=efecto.source_item_id,
        route_key=efecto.route_key, status="ACTIVE", dedupe_key=efecto.dedupe_key,
        source_event_id=efecto.source_event_id, correlation_id=efecto.correlation_id,
        actor_type=actor.tipo, actor_user_id=actor.user_id)
    if not _insertar_unico(db, a, "uq_alerts_company_dedupe"):
        return _por_clave(db, Alert, efecto.company_id, efecto.dedupe_key), False
    _auditar(db, accion="ALERT_CREATED", entidad="Alert", entidad_id=str(a.id),
             company_id=efecto.company_id, actor=actor, after={"category": efecto.category})
    return a, True


def _evento(db: Session, tarea: Task, tipo: str, actor: Actor, *, desde: str | None = None,
            hacia: str | None = None, motivo: str | None = None, dedupe_key: str | None = None,
            momento: datetime | None = None) -> TaskEvent:
    ev = TaskEvent(task_id=str(tarea.id), company_id=tarea.company_id, event_type=tipo,
                   actor_type=actor.tipo, actor_user_id=actor.user_id, from_user_id=desde,
                   to_user_id=hacia, reason=motivo, dedupe_key=dedupe_key,
                   occurred_at=momento or _ahora())
    db.add(ev)
    return ev


def registrar_efecto_de_tarea(db: Session, tarea: Task, tipo: str, dedupe_key: str,
                              momento: datetime) -> bool:
    """Recordatorio o escalada de la tarea, una sola vez por clave lógica."""
    return _insertar_unico(db, TaskEvent(
        task_id=str(tarea.id), company_id=tarea.company_id, event_type=tipo, actor_type="SYSTEM",
        dedupe_key=dedupe_key, occurred_at=momento), "uq_task_events_task_dedupe")


def resolver_por_origen(db: Session, *, company_id: str, source_type: str, source_id: str,
                        source_item_id: str | None, momento: datetime) -> int:
    """La dueña resolvió: se cierra lo que abrieron las reglas con `auto_close` (§18)."""
    reglas = select(NotificationRule.id).where(NotificationRule.company_id == company_id,
                                               NotificationRule.auto_close.is_(True))
    filtro_tarea = [Task.company_id == company_id, Task.source_type == source_type,
                    Task.source_id == source_id, Task.status.in_(ESTADOS_TAREA_ABIERTOS),
                    Task.rule_id.in_(reglas)]
    if source_item_id is not None:
        filtro_tarea.append(Task.source_item_id == source_item_id)
    cerradas = 0
    for tarea in db.execute(select(Task).where(*filtro_tarea).with_for_update()).scalars().all():
        tarea.status = "RESOLVED_BY_SOURCE"
        tarea.closed_at = momento
        tarea.version += 1
        _evento(db, tarea, "RESOLVED_BY_SOURCE", SISTEMA, momento=momento)
        cerradas += 1
    filtro_alerta = [Alert.company_id == company_id, Alert.source_type == source_type,
                     Alert.source_id == source_id, Alert.status == "ACTIVE", Alert.rule_id.in_(reglas)]
    if source_item_id is not None:
        filtro_alerta.append(Alert.source_item_id == source_item_id)
    for alerta in db.execute(select(Alert).where(*filtro_alerta)).scalars().all():
        alerta.status = "RESOLVED"
        alerta.resolved_at = momento
        cerradas += 1
    db.flush()
    return cerradas


# --------------------------------------------------------------------------- #
# Visibilidad (FR-047-014, FR-047-032)
# --------------------------------------------------------------------------- #
# Permisos EN la empresa de la petición (Spec 003, capacidad × empresa).
def _permisos(db: Session, user: User, company_id: str) -> set[str]:
    return authority.capabilities_in_company(db, user, company_id)


def _mensaje(clave: str, parametros: dict[str, Any]) -> dict[str, Any]:
    r = renderizar(clave, parametros)
    return {"key": clave, "params": parametros, "text": r.text, "render_error": r.render_error}


def _enlace(source_type: str, source_id: str, source_item_id: str | None, route_key: str) -> dict:
    return {"source_type": source_type, "source_id": source_id,
            "source_item_id": source_item_id, "route_key": route_key}


def _pagina(db: Session, consulta, orden, page: int, page_size: int) -> tuple[int, list]:
    total = db.execute(select(func.count()).select_from(consulta.order_by(None).subquery())).scalar_one()
    filas = db.execute(consulta.order_by(*orden).offset((page - 1) * page_size).limit(page_size)).all()
    return total, filas


# --------------------------------------------------------------------------- #
# Notificaciones del destinatario (FR-047-003, 028-030)
# --------------------------------------------------------------------------- #
def _consulta_notificaciones(ctx: CompanyContext, prohibidos: list[str]):
    q = (select(Notification, NotificationRecipient)
         .join(NotificationRecipient, NotificationRecipient.notification_id == Notification.id)
         .where(NotificationRecipient.user_id == ctx.user_id,
                NotificationRecipient.company_id == ctx.company_id,
                Notification.company_id == ctx.company_id))
    if prohibidos:
        q = q.where(Notification.source_type.not_in(prohibidos))
    return q


def _notificacion_dict(n: Notification, r: NotificationRecipient) -> dict[str, Any]:
    return {"id": str(n.id), "category": n.category, "severity": n.severity,
            "mandatory": n.mandatory, "message": _mensaje(n.message_key, n.message_params),
            "link": _enlace(n.source_type, n.source_id, n.source_item_id, n.route_key),
            "created_at": n.created_at, "read_at": r.read_at, "archived_at": r.archived_at}


def listar_notificaciones(db: Session, *, ctx: CompanyContext, user: User, state: str,
                          category: str | None, severity: str | None, source_type: str | None,
                          created_from: datetime | None, created_to: datetime | None,
                          page: int, page_size: int) -> dict[str, Any]:
    q = _consulta_notificaciones(ctx, catalogo.tipos_prohibidos(_permisos(db, user, ctx.company_id)))
    if state == "active":
        q = q.where(NotificationRecipient.archived_at.is_(None))
    elif state == "unread":
        q = q.where(NotificationRecipient.archived_at.is_(None), NotificationRecipient.read_at.is_(None))
    elif state == "read":
        q = q.where(NotificationRecipient.read_at.is_not(None))
    elif state == "archived":
        q = q.where(NotificationRecipient.archived_at.is_not(None))
    if category:
        q = q.where(Notification.category == category)
    if severity:
        q = q.where(Notification.severity == severity)
    if source_type:
        q = q.where(Notification.source_type == source_type)
    if created_from:
        q = q.where(Notification.created_at >= created_from)
    if created_to:
        q = q.where(Notification.created_at <= created_to)
    total, filas = _pagina(db, q, (Notification.created_at.desc(), Notification.id.desc()), page, page_size)
    return {"items": [_notificacion_dict(n, r) for n, r in filas], "total": total,
            "page": page, "page_size": page_size}


def _notificacion_visible(db: Session, ctx: CompanyContext, user: User, notification_id: str):
    fila = db.execute(_consulta_notificaciones(ctx, catalogo.tipos_prohibidos(_permisos(db, user, ctx.company_id)))
                      .where(Notification.id == notification_id)).first()
    if fila is None:
        raise NotFoundError(code="NOTIFICATION_NOT_FOUND", message=texto("error.notification_not_found"))
    return fila


def obtener_notificacion(db: Session, *, ctx: CompanyContext, user: User, notification_id: str) -> dict:
    n, r = _notificacion_visible(db, ctx, user, notification_id)
    return _notificacion_dict(n, r)


def marcar_leida(db: Session, *, ctx: CompanyContext, user: User, notification_id: str) -> dict:
    n, r = _notificacion_visible(db, ctx, user, notification_id)
    momento = _ahora()
    cambio = db.execute(update(NotificationRecipient)
                        .where(NotificationRecipient.id == r.id, NotificationRecipient.read_at.is_(None))
                        .values(read_at=momento)).rowcount
    if cambio:
        _auditar(db, accion="NOTIFICATION_READ", entidad="Notification", entidad_id=str(n.id),
                 company_id=ctx.company_id, actor=persona(ctx.user_id))
    db.flush()
    db.refresh(r)
    return _notificacion_dict(n, r)


def archivar(db: Session, *, ctx: CompanyContext, user: User, notification_id: str) -> dict:
    n, r = _notificacion_visible(db, ctx, user, notification_id)
    momento = _ahora()
    cambio = db.execute(update(NotificationRecipient)
                        .where(NotificationRecipient.id == r.id, NotificationRecipient.archived_at.is_(None))
                        .values(archived_at=momento)).rowcount
    if cambio:
        _auditar(db, accion="NOTIFICATION_ARCHIVED", entidad="Notification", entidad_id=str(n.id),
                 company_id=ctx.company_id, actor=persona(ctx.user_id))
    db.flush()
    db.refresh(r)
    return _notificacion_dict(n, r)


# --------------------------------------------------------------------------- #
# Tareas (FR-047-005..009, R-047-01, R-047-04)
# --------------------------------------------------------------------------- #
def _es_candidato(user_id: str):
    return exists().where(TaskCandidate.task_id == Task.id, TaskCandidate.user_id == user_id)


def _consulta_tareas(ctx: CompanyContext, permisos: set[str], scope: str):
    q = select(Task).where(Task.company_id == ctx.company_id)
    prohibidos = catalogo.tipos_prohibidos(permisos)
    if prohibidos:
        q = q.where(Task.source_type.not_in(prohibidos))
    if scope == "all":
        if "tareas:view" not in permisos:
            raise PermissionDeniedError(code="PERMISSION_DENIED", message=texto("error.permission_required"))
    elif scope == "mine":
        q = q.where(Task.assignee_user_id == ctx.user_id)
    elif scope == "pool":
        q = q.where(Task.assignee_user_id.is_(None), _es_candidato(ctx.user_id))
    else:
        q = q.where(or_(Task.assignee_user_id == ctx.user_id, _es_candidato(ctx.user_id)))
    return q


def _vencida(t: Task, ahora: datetime) -> bool:
    return bool(t.due_at is not None and t.status in ESTADOS_TAREA_ABIERTOS and t.due_at < ahora)


def _acciones(t: Task, user_id: str, permisos: set[str], candidatos: set[str]) -> list[str]:
    if t.status not in ESTADOS_TAREA_ABIERTOS:
        return []
    acciones: list[str] = []
    propia = t.assignee_user_id == user_id or (t.assignee_user_id is None and user_id in candidatos)
    if "tareas:complete" in permisos and propia:
        if t.status == "OPEN":
            acciones.append("start")
        acciones.append("complete")
    if "tareas:assign" in permisos:
        acciones += ["reassign", "cancel"]
    return acciones


def _tarea_dict(t: Task, ahora: datetime) -> dict[str, Any]:
    return {"id": str(t.id), "task_type": t.task_type, "status": t.status,
            "message": _mensaje(t.message_key, t.message_params),
            "link": _enlace(t.source_type, t.source_id, t.source_item_id, t.route_key),
            "priority_code": t.priority_code, "priority_rank": t.priority_rank,
            "assignee_user_id": t.assignee_user_id, "due_at": t.due_at,
            "overdue": _vencida(t, ahora), "closed_at": t.closed_at, "version": t.version,
            "created_at": t.created_at}


def listar_tareas(db: Session, *, ctx: CompanyContext, user: User, scope: str, status: str | None,
                  overdue: bool | None, priority: str | None, source_type: str | None,
                  due_from: datetime | None, due_to: datetime | None,
                  page: int, page_size: int) -> dict[str, Any]:
    ahora = _ahora()
    q = _consulta_tareas(ctx, _permisos(db, user, ctx.company_id), scope)
    if status:
        q = q.where(Task.status == status)
    if overdue is True:
        q = q.where(Task.status.in_(ESTADOS_TAREA_ABIERTOS), Task.due_at.is_not(None), Task.due_at < ahora)
    if priority:
        q = q.where(Task.priority_code == priority)
    if source_type:
        q = q.where(Task.source_type == source_type)
    if due_from:
        q = q.where(Task.due_at >= due_from)
    if due_to:
        q = q.where(Task.due_at <= due_to)
    total, filas = _pagina(db, q, (Task.due_at.asc().nulls_last(), Task.created_at.desc(), Task.id), page, page_size)
    return {"items": [_tarea_dict(t, ahora) for (t,) in filas], "total": total,
            "page": page, "page_size": page_size}


def _tarea_visible(db: Session, ctx: CompanyContext, user: User, task_id: str, *,
                   bloquear: bool = False) -> tuple[Task, set[str]]:
    permisos = _permisos(db, user, ctx.company_id)
    scope = "all" if "tareas:view" in permisos else "involved"
    q = _consulta_tareas(ctx, permisos, scope).where(Task.id == task_id)
    if bloquear:
        q = q.with_for_update(of=Task)
    tarea = db.execute(q).scalars().first()
    if tarea is None:
        raise NotFoundError(code="TASK_NOT_FOUND", message=texto("error.task_not_found"))
    return tarea, permisos


def _candidatos(db: Session, task_id: str) -> set[str]:
    return set(db.execute(select(TaskCandidate.user_id).where(TaskCandidate.task_id == task_id))
               .scalars().all())


def obtener_tarea(db: Session, *, ctx: CompanyContext, user: User, task_id: str) -> dict[str, Any]:
    tarea, permisos = _tarea_visible(db, ctx, user, task_id)
    candidatos = _candidatos(db, str(tarea.id))
    historial = db.execute(select(TaskEvent).where(TaskEvent.task_id == tarea.id)
                           .order_by(TaskEvent.occurred_at, TaskEvent.created_at, TaskEvent.id)).scalars().all()
    datos = _tarea_dict(tarea, _ahora())
    datos["candidates"] = sorted(candidatos)
    datos["history"] = [{"id": str(e.id), "event_type": e.event_type, "actor_type": e.actor_type,
                         "actor_user_id": e.actor_user_id, "from_user_id": e.from_user_id,
                         "to_user_id": e.to_user_id, "reason": e.reason,
                         "occurred_at": e.occurred_at} for e in historial]
    datos["allowed_actions"] = _acciones(tarea, ctx.user_id, permisos, candidatos)
    return datos


def _exigir_propia(tarea: Task, ctx: CompanyContext, permisos: set[str], candidatos: set[str]) -> None:
    if tarea.status not in ESTADOS_TAREA_ABIERTOS:
        raise ConflictError(code="TASK_ALREADY_CLOSED", message=texto("error.task_already_closed"))
    propia = (tarea.assignee_user_id == ctx.user_id
              or (tarea.assignee_user_id is None and ctx.user_id in candidatos))
    if "tareas:complete" not in permisos or not propia:
        raise PermissionDeniedError(code="TASK_NOT_ACTIONABLE", message=texto("error.task_not_actionable"))


def _auditar_tarea(db: Session, tarea: Task, accion: str, ctx: CompanyContext,
                   before: dict | None = None, reason: str | None = None) -> None:
    _auditar(db, accion=accion, entidad="Task", entidad_id=str(tarea.id), company_id=tarea.company_id,
             actor=persona(ctx.user_id), before=before,
             after={"status": tarea.status, "assignee_user_id": tarea.assignee_user_id,
                    "version": tarea.version}, reason=reason)


def iniciar_tarea(db: Session, *, ctx: CompanyContext, user: User, task_id: str) -> dict[str, Any]:
    tarea, permisos = _tarea_visible(db, ctx, user, task_id, bloquear=True)
    candidatos = _candidatos(db, str(tarea.id))
    _exigir_propia(tarea, ctx, permisos, candidatos)
    actor = persona(ctx.user_id)
    antes = {"status": tarea.status, "assignee_user_id": tarea.assignee_user_id}
    if tarea.assignee_user_id is None:
        tarea.assignee_user_id = ctx.user_id
        _evento(db, tarea, "ASSIGNED", actor, hacia=ctx.user_id)
    if tarea.status == "OPEN":
        tarea.status = "IN_PROGRESS"
        _evento(db, tarea, "STARTED", actor)
    tarea.version += 1
    db.flush()
    _auditar_tarea(db, tarea, "TASK_STARTED", ctx, before=antes)
    return obtener_tarea(db, ctx=ctx, user=user, task_id=task_id)


def completar_tarea(db: Session, *, ctx: CompanyContext, user: User, task_id: str) -> dict[str, Any]:
    """Cierra la tarea. **No** toca el objeto del dominio (R-047-01)."""
    tarea, permisos = _tarea_visible(db, ctx, user, task_id, bloquear=True)
    candidatos = _candidatos(db, str(tarea.id))
    _exigir_propia(tarea, ctx, permisos, candidatos)
    antes = {"status": tarea.status}
    tarea.status = "COMPLETED"
    tarea.closed_at = _ahora()
    tarea.closed_by = ctx.user_id
    if tarea.assignee_user_id is None:
        tarea.assignee_user_id = ctx.user_id
    tarea.version += 1
    _evento(db, tarea, "COMPLETED", persona(ctx.user_id))
    db.flush()
    _auditar_tarea(db, tarea, "TASK_COMPLETED", ctx, before=antes)
    return obtener_tarea(db, ctx=ctx, user=user, task_id=task_id)


def cancelar_tarea(db: Session, *, ctx: CompanyContext, user: User, task_id: str,
                   reason: str | None) -> dict[str, Any]:
    tarea, permisos = _tarea_visible(db, ctx, user, task_id, bloquear=True)
    if "tareas:assign" not in permisos:
        raise PermissionDeniedError(code="PERMISSION_DENIED", message=texto("error.permission_required"))
    if tarea.status not in ESTADOS_TAREA_ABIERTOS:
        raise ConflictError(code="TASK_ALREADY_CLOSED", message=texto("error.task_already_closed"))
    if not (reason or "").strip():
        raise KontrolError(code="TASK_REASON_REQUIRED", message=texto("error.task_reason_required"),
                           status_code=422)
    antes = {"status": tarea.status}
    tarea.status = "CANCELLED"
    tarea.closed_at = _ahora()
    tarea.closed_by = ctx.user_id
    tarea.version += 1
    _evento(db, tarea, "CANCELLED", persona(ctx.user_id), motivo=reason.strip())
    db.flush()
    _auditar_tarea(db, tarea, "TASK_CANCELLED", ctx, before=antes, reason=reason.strip())
    return obtener_tarea(db, ctx=ctx, user=user, task_id=task_id)


def reasignar_tarea(db: Session, *, ctx: CompanyContext, user: User, task_id: str, assignee_user_id: str,
                    reason: str | None, expected_version: int | None) -> dict[str, Any]:
    """Reasigna conservando la asignación anterior en el historial (R-047-04)."""
    if expected_version is None:
        raise KontrolError(code="TASK_IF_MATCH_REQUIRED", message=texto("error.task_if_match_required"),
                           status_code=428)
    tarea, permisos = _tarea_visible(db, ctx, user, task_id, bloquear=True)
    if "tareas:assign" not in permisos:
        raise PermissionDeniedError(code="PERMISSION_DENIED", message=texto("error.permission_required"))
    if tarea.status not in ESTADOS_TAREA_ABIERTOS:
        raise ConflictError(code="TASK_ALREADY_CLOSED", message=texto("error.task_already_closed"))
    if int(expected_version) != int(tarea.version):
        raise ConflictError(code="TASK_VERSION_CONFLICT", message=texto("error.task_version_conflict"))
    destino = db.get(User, assignee_user_id)
    if destino is None or destino.tenant_id != ctx.tenant_id \
            or ctx.company_id not in accessible_company_ids(db, destino):
        raise KontrolError(code="TASK_ASSIGNEE_NOT_IN_COMPANY",
                           message=texto("error.task_assignee_not_in_company"), status_code=422)
    antes = {"assignee_user_id": tarea.assignee_user_id, "version": tarea.version}
    anterior = tarea.assignee_user_id
    tarea.assignee_user_id = str(destino.id)
    tarea.version += 1
    _evento(db, tarea, "REASSIGNED", persona(ctx.user_id), desde=anterior, hacia=str(destino.id),
            motivo=(reason or "").strip() or None)
    db.flush()
    _auditar_tarea(db, tarea, "TASK_REASSIGNED", ctx, before=antes, reason=(reason or "").strip() or None)
    return obtener_tarea(db, ctx=ctx, user=user, task_id=task_id)


# --------------------------------------------------------------------------- #
# Alertas y contadores (FR-047-010, 030, 036)
# --------------------------------------------------------------------------- #
def listar_alertas(db: Session, *, ctx: CompanyContext, user: User, status: str | None,
                   severity: str | None, source_type: str | None, page: int, page_size: int) -> dict:
    q = select(Alert).where(Alert.company_id == ctx.company_id)
    prohibidos = catalogo.tipos_prohibidos(_permisos(db, user, ctx.company_id))
    if prohibidos:
        q = q.where(Alert.source_type.not_in(prohibidos))
    if status:
        q = q.where(Alert.status == status)
    if severity:
        q = q.where(Alert.severity == severity)
    if source_type:
        q = q.where(Alert.source_type == source_type)
    total, filas = _pagina(db, q, (Alert.created_at.desc(), Alert.id.desc()), page, page_size)
    return {"items": [{"id": str(a.id), "category": a.category, "severity": a.severity,
                       "status": a.status, "message": _mensaje(a.message_key, a.message_params),
                       "link": _enlace(a.source_type, a.source_id, a.source_item_id, a.route_key),
                       "created_at": a.created_at, "resolved_at": a.resolved_at}
                      for (a,) in filas],
            "total": total, "page": page, "page_size": page_size}


def contadores(db: Session, *, ctx: CompanyContext, user: User) -> dict[str, int]:
    """Agregados del servidor para la campana y para la 049. Nunca se cuenta en el cliente."""
    permisos = _permisos(db, user, ctx.company_id)
    prohibidos = catalogo.tipos_prohibidos(permisos)
    ahora = _ahora()
    no_leidas = (select(func.count()).select_from(NotificationRecipient)
                 .join(Notification, Notification.id == NotificationRecipient.notification_id)
                 .where(NotificationRecipient.user_id == ctx.user_id,
                        NotificationRecipient.company_id == ctx.company_id,
                        Notification.company_id == ctx.company_id,
                        NotificationRecipient.read_at.is_(None),
                        NotificationRecipient.archived_at.is_(None)))
    abiertas = select(func.count()).select_from(Task).where(
        Task.company_id == ctx.company_id, Task.status.in_(ESTADOS_TAREA_ABIERTOS),
        or_(Task.assignee_user_id == ctx.user_id,
            and_(Task.assignee_user_id.is_(None), _es_candidato(ctx.user_id))))
    alertas = select(func.count()).select_from(Alert).where(Alert.company_id == ctx.company_id,
                                                             Alert.status == "ACTIVE")
    if prohibidos:
        no_leidas = no_leidas.where(Notification.source_type.not_in(prohibidos))
        abiertas = abiertas.where(Task.source_type.not_in(prohibidos))
        alertas = alertas.where(Alert.source_type.not_in(prohibidos))
    vencidas = abiertas.where(Task.due_at.is_not(None), Task.due_at < ahora)
    return {
        "unread_notifications": db.execute(no_leidas).scalar_one(),
        "open_tasks": db.execute(abiertas).scalar_one(),
        "overdue_tasks": db.execute(vencidas).scalar_one(),
        "active_alerts": db.execute(alertas).scalar_one() if "alertas:view" in permisos else 0,
    }


# --------------------------------------------------------------------------- #
# Reglas, prioridades y preferencias (FR-047-009, 018, 024, 025)
# --------------------------------------------------------------------------- #
def _regla_invalida(motivo: str) -> KontrolError:
    return KontrolError(code="NOTIFICATION_RULE_INVALID", message=texto("error.notification_rule_invalid"),
                        details={"reason": motivo}, status_code=422)


def _regla_dict(r: NotificationRule) -> dict[str, Any]:
    return {c: getattr(r, c) for c in (
        "code", "source", "event_type", "effect", "severity", "mandatory", "priority_code",
        "reminder_offset_minutes", "reminder_repeat_minutes", "escalation_after_minutes",
        "escalation_role_id", "auto_close", "active", "created_at")} | {"id": str(r.id)}


def listar_reglas(db: Session, *, ctx: CompanyContext) -> list[dict[str, Any]]:
    filas = db.execute(select(NotificationRule).where(NotificationRule.company_id == ctx.company_id)
                       .order_by(NotificationRule.code)).scalars().all()
    return [_regla_dict(r) for r in filas]


def crear_regla(db: Session, *, ctx: CompanyContext, datos: dict[str, Any]) -> dict[str, Any]:
    efectos = catalogo.EVENTOS_CONSUMIBLES.get(datos["source"], {}).get(datos["event_type"])
    if efectos is None:
        raise _regla_invalida("EVENT_NOT_SUPPORTED")
    if datos["effect"] not in EFECTOS or datos["effect"] not in efectos:
        raise _regla_invalida("EFFECT_NOT_SUPPORTED")
    if datos["severity"] not in SEVERIDADES:
        raise _regla_invalida("SEVERITY_NOT_SUPPORTED")
    tiempos = ("reminder_offset_minutes", "reminder_repeat_minutes", "escalation_after_minutes")
    if datos["effect"] != "TASK" and any(datos.get(c) is not None for c in tiempos):
        raise _regla_invalida("TIMING_ONLY_FOR_TASKS")
    if (datos.get("escalation_after_minutes") is None) != (datos.get("escalation_role_id") is None):
        raise _regla_invalida("ESCALATION_NEEDS_MINUTES_AND_ROLE")
    if datos.get("reminder_repeat_minutes") is not None and datos.get("reminder_offset_minutes") is None:
        raise _regla_invalida("REPEAT_NEEDS_OFFSET")
    for campo, minimo in (("reminder_offset_minutes", 0), ("reminder_repeat_minutes", 1),
                          ("escalation_after_minutes", 1)):
        if datos.get(campo) is not None and datos[campo] < minimo:
            raise _regla_invalida("MINUTES_OUT_OF_RANGE")
    rol = db.get(Role, datos["escalation_role_id"]) if datos.get("escalation_role_id") else None
    if datos.get("escalation_role_id") and (
        rol is None
        or (rol.tenant_id is not None and rol.tenant_id != ctx.tenant_id)
        or (rol.company_id is not None and rol.company_id != ctx.company_id)
    ):
        raise _regla_invalida("ROLE_NOT_FOUND")
    if datos.get("priority_code") and _rango_prioridad(db, ctx.company_id, datos["priority_code"]) is None:
        raise KontrolError(code="TASK_PRIORITY_NOT_FOUND", message=texto("error.task_priority_not_found"),
                           status_code=422)
    regla = NotificationRule(company_id=ctx.company_id, created_by=ctx.user_id, active=True, **datos)
    if not _insertar_unico(db, regla, "uq_notification_rules_company_code"):
        raise ConflictError(code="NOTIFICATION_RULE_CODE_TAKEN",
                            message=texto("error.notification_rule_code_taken"))
    _auditar(db, accion="NOTIFICATION_RULE_CREATED", entidad="NotificationRule", entidad_id=str(regla.id),
             company_id=ctx.company_id, actor=persona(ctx.user_id), after={"code": regla.code})
    return _regla_dict(regla)


def desactivar_regla(db: Session, *, ctx: CompanyContext, rule_id: str) -> dict[str, Any]:
    regla = db.execute(select(NotificationRule).where(NotificationRule.id == rule_id,
                                                      NotificationRule.company_id == ctx.company_id)
                       ).scalars().first()
    if regla is None:
        raise NotFoundError(code="NOTIFICATION_RULE_NOT_FOUND", message=texto("error.notification_rule_not_found"))
    if regla.active:
        regla.active = False
        db.flush()
        _auditar(db, accion="NOTIFICATION_RULE_DEACTIVATED", entidad="NotificationRule",
                 entidad_id=str(regla.id), company_id=ctx.company_id, actor=persona(ctx.user_id))
    return _regla_dict(regla)


def listar_fuentes() -> list[dict[str, Any]]:
    return [{"source": s, "event_type": e, "effects": sorted(efectos)}
            for s, eventos in catalogo.EVENTOS_CONSUMIBLES.items() for e, efectos in eventos.items()]


def listar_prioridades(db: Session, *, ctx: CompanyContext) -> list[dict[str, Any]]:
    filas = db.execute(select(TaskPriority).where(TaskPriority.company_id == ctx.company_id,
                                                  TaskPriority.active.is_(True))
                       .order_by(TaskPriority.rank, TaskPriority.code)).scalars().all()
    return [{"id": str(p.id), "code": p.code, "name": p.name, "rank": p.rank} for p in filas]


def crear_prioridad(db: Session, *, ctx: CompanyContext, code: str, name: str, rank: int) -> dict[str, Any]:
    p = TaskPriority(company_id=ctx.company_id, code=code, name=name, rank=rank, active=True)
    if not _insertar_unico(db, p, "uq_task_priorities_company_code"):
        raise ConflictError(code="TASK_PRIORITY_CODE_TAKEN", message=texto("error.task_priority_code_taken"))
    _auditar(db, accion="TASK_PRIORITY_CREATED", entidad="TaskPriority", entidad_id=str(p.id),
             company_id=ctx.company_id, actor=persona(ctx.user_id), after={"code": code, "rank": rank})
    return {"id": str(p.id), "code": p.code, "name": p.name, "rank": p.rank}


def listar_preferencias(db: Session, *, ctx: CompanyContext) -> list[dict[str, Any]]:
    reglas = db.execute(select(NotificationRule.event_type, func.bool_or(NotificationRule.mandatory))
                        .where(NotificationRule.company_id == ctx.company_id,
                               NotificationRule.active.is_(True),
                               NotificationRule.effect == "NOTIFICATION")
                        .group_by(NotificationRule.event_type)).all()
    propias = {(p.category, p.channel): p.enabled for p in db.execute(
        select(NotificationPreference).where(NotificationPreference.company_id == ctx.company_id,
                                             NotificationPreference.user_id == ctx.user_id)).scalars().all()}
    salida = []
    for categoria, obligatoria in sorted(reglas):
        for canal in ("INTERNAL", *CANALES_EXTERNOS):
            disponible = canal == "INTERNAL" or canal in delivery.PROVEEDORES
            por_defecto = canal == "INTERNAL"
            salida.append({"category": categoria, "channel": canal, "mandatory": bool(obligatoria),
                           "available": disponible,
                           "enabled": True if (obligatoria and canal == "INTERNAL")
                           else propias.get((categoria, canal), por_defecto)})
    return salida


def guardar_preferencia(db: Session, *, ctx: CompanyContext, category: str, channel: str,
                        enabled: bool) -> dict[str, Any]:
    if channel != "INTERNAL" and channel not in delivery.PROVEEDORES:
        raise KontrolError(code="CHANNEL_UNAVAILABLE", message=texto("error.channel_unavailable"),
                           status_code=422)
    obligatoria = db.execute(select(exists().where(
        NotificationRule.company_id == ctx.company_id, NotificationRule.event_type == category,
        NotificationRule.active.is_(True), NotificationRule.mandatory.is_(True)))).scalar_one()
    if obligatoria and channel == "INTERNAL" and not enabled:
        raise ConflictError(code="NOTIFICATION_MANDATORY", message=texto("error.notification_mandatory"))
    fila = db.execute(select(NotificationPreference).where(
        NotificationPreference.company_id == ctx.company_id, NotificationPreference.user_id == ctx.user_id,
        NotificationPreference.category == category, NotificationPreference.channel == channel)
    ).scalars().first()
    if fila is None:
        fila = NotificationPreference(company_id=ctx.company_id, user_id=ctx.user_id, category=category,
                                      channel=channel, enabled=enabled)
        if not _insertar_unico(db, fila, "uq_notification_preferences_user_category_channel"):
            fila = db.execute(select(NotificationPreference).where(
                NotificationPreference.company_id == ctx.company_id,
                NotificationPreference.user_id == ctx.user_id,
                NotificationPreference.category == category,
                NotificationPreference.channel == channel)).scalars().one()
    fila.enabled = enabled
    db.flush()
    return {"category": category, "channel": channel, "enabled": fila.enabled, "mandatory": bool(obligatoria)}


def ventana_de_recordatorio(*, due_at: datetime, offset_minutes: int, repeat_minutes: int | None,
                            ahora: datetime) -> int | None:
    """Índice de la ventana vigente, o `None` si todavía no toca (política `LATEST_WINDOW`)."""
    primero = due_at.timestamp() - offset_minutes * 60
    if ahora.timestamp() < primero:
        return None
    if repeat_minutes is None:
        return 0
    return math.floor((ahora.timestamp() - primero) / (repeat_minutes * 60))
