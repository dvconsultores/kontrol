"""Notificaciones, tareas y alertas (Spec 047).

# Spec 047 · Modelo de notificaciones, tareas y alertas

Tres reglas atraviesan este fichero:

- **Ninguna columna guarda texto visible.** Se guarda `message_key` y
  `message_params`; el texto se deriva (OQ-047-02).
- **Todo efecto tiene clave lógica única** (`dedupe_key`): repetir un hecho o un
  tick no duplica nada (ADR-D0-015 R-D0-15-5).
- **Nada se borra.** El historial de una tarea es append-only y leer o archivar
  una notificación es un estado del destinatario, no una eliminación.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.scope import Scope
from app.modules.scheduler.models import en
from app.shared.mixins import TimestampMixin, UUIDMixin

EFECTOS = ("NOTIFICATION", "TASK", "ALERT")
SEVERIDADES = ("INFO", "WARNING", "CRITICAL")
TIPOS_ACTOR = ("SYSTEM", "USER")
CANALES = ("INTERNAL", "EMAIL")
CANALES_EXTERNOS = ("EMAIL",)
ESTADOS_ENTREGA = ("PENDING", "SENT", "RETRYING", "FAILED")
RESULTADOS_RECIBO = ("APPLIED", "NO_RULE")
ESTADOS_TAREA = ("OPEN", "IN_PROGRESS", "COMPLETED", "CANCELLED", "RESOLVED_BY_SOURCE")
ESTADOS_TAREA_ABIERTOS = ("OPEN", "IN_PROGRESS")
EVENTOS_TAREA = ("CREATED", "ASSIGNED", "REASSIGNED", "STARTED", "COMPLETED", "CANCELLED",
                 "REMINDED", "ESCALATED", "RESOLVED_BY_SOURCE")
ESTADOS_ALERTA = ("ACTIVE", "RESOLVED")

#: El actor de sistema no tiene usuario; el de persona, siempre (FR-047-045).
_ACTOR = ("(actor_type = 'SYSTEM' AND actor_user_id IS NULL) "
          "OR (actor_type = 'USER' AND actor_user_id IS NOT NULL)")


class NotificationRule(UUIDMixin, TimestampMixin, Base):
    """Qué hacer con un hecho de una dueña, en una empresa."""

    __tablename__ = "notification_rules"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_notification_rules_company_code"),
        CheckConstraint(f"effect IN ({en(EFECTOS)})", name="effect"),
        CheckConstraint(f"severity IN ({en(SEVERIDADES)})", name="severity"),
        CheckConstraint("(escalation_after_minutes IS NULL) = (escalation_role_id IS NULL)",
                        name="escalation_pair"),
        CheckConstraint("effect = 'TASK' OR (reminder_offset_minutes IS NULL "
                        "AND reminder_repeat_minutes IS NULL AND escalation_after_minutes IS NULL)",
                        name="timing_task_only"),
        CheckConstraint("(reminder_offset_minutes IS NULL OR reminder_offset_minutes >= 0) "
                        "AND (reminder_repeat_minutes IS NULL OR reminder_repeat_minutes > 0) "
                        "AND (escalation_after_minutes IS NULL OR escalation_after_minutes > 0)",
                        name="minutes"),
        CheckConstraint("reminder_repeat_minutes IS NULL OR reminder_offset_minutes IS NOT NULL",
                        name="repeat_needs_offset"),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    effect: Mapped[str] = mapped_column(String(16), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="INFO")
    mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    priority_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reminder_offset_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reminder_repeat_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    escalation_after_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    escalation_role_id: Mapped[str | None] = mapped_column(ForeignKey("roles.id"), nullable=True)
    auto_close: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class TaskPriority(UUIDMixin, TimestampMixin, Base):
    """Catálogo de prioridades de la empresa (FR-047-009)."""

    __tablename__ = "task_priorities"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_task_priorities_company_code"),
        CheckConstraint("rank >= 0", name="rank"),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    #: Dato maestro que escribe la empresa, no un texto del producto.
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class NotificationEventReceipt(UUIDMixin, TimestampMixin, Base):
    """Un hecho de una dueña se consume **una** vez (FR-047-015, FR-047-054)."""

    __tablename__ = "notification_event_receipts"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("source", "source_event_id", name="uq_notification_event_receipts_source_event"),
        CheckConstraint(f"outcome IN ({en(RESULTADOS_RECIBO)})", name="outcome"),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    source_event_id: Mapped[str] = mapped_column(String(36), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    run_correlation_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class Notification(UUIDMixin, TimestampMixin, Base):
    """Mensaje informativo. Sin texto: clave y parámetros (FR-047-050)."""

    __tablename__ = "notifications"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("company_id", "dedupe_key", name="uq_notifications_company_dedupe"),
        CheckConstraint(f"severity IN ({en(SEVERIDADES)})", name="severity"),
        CheckConstraint(f"actor_type IN ({en(TIPOS_ACTOR)})", name="actor_type"),
        CheckConstraint(_ACTOR, name="actor"),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    rule_id: Mapped[str | None] = mapped_column(ForeignKey("notification_rules.id"), nullable=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    message_key: Mapped[str] = mapped_column(String(128), nullable=False)
    message_params: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[str] = mapped_column(String(36), nullable=False)
    source_item_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    route_key: Mapped[str] = mapped_column(String(64), nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(160), nullable=False)
    source_event_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    actor_type: Mapped[str] = mapped_column(String(8), nullable=False)
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class NotificationRecipient(UUIDMixin, TimestampMixin, Base):
    """El estado de lectura es de cada destinatario, nunca de la notificación."""

    __tablename__ = "notification_recipients"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("notification_id", "user_id", name="uq_notification_recipients_notification_user"),
        Index("ix_notification_recipients_user_company", "user_id", "company_id", "archived_at"),
    )

    notification_id: Mapped[str] = mapped_column(ForeignKey("notifications.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class NotificationPreference(UUIDMixin, TimestampMixin, Base):
    """Preferencia de un usuario sobre una categoría opcional (FR-047-018)."""

    __tablename__ = "notification_preferences"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("company_id", "user_id", "category", "channel",
                         name="uq_notification_preferences_user_category_channel"),
        CheckConstraint(f"channel IN ({en(CANALES)})", name="channel"),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    channel: Mapped[str] = mapped_column(String(16), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)


class NotificationDelivery(UUIDMixin, TimestampMixin, Base):
    """Entrega por un canal externo. Separada de la notificación (FR-047-022)."""

    __tablename__ = "notification_deliveries"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("recipient_id", "channel", name="uq_notification_deliveries_recipient_channel"),
        CheckConstraint(f"channel IN ({en(CANALES_EXTERNOS)})", name="channel"),
        CheckConstraint(f"status IN ({en(ESTADOS_ENTREGA)})", name="status"),
        CheckConstraint("attempts >= 0", name="attempts"),
    )

    recipient_id: Mapped[str] = mapped_column(ForeignKey("notification_recipients.id"), nullable=False)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Task(UUIDMixin, TimestampMixin, Base):
    """Acción pendiente. Completarla no ejecuta la operación del dominio (R-047-01)."""

    __tablename__ = "tasks"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("company_id", "dedupe_key", name="uq_tasks_company_dedupe"),
        CheckConstraint(f"status IN ({en(ESTADOS_TAREA)})", name="status"),
        CheckConstraint(f"actor_type IN ({en(TIPOS_ACTOR)})", name="actor_type"),
        CheckConstraint(_ACTOR, name="actor"),
        CheckConstraint("version >= 1", name="version"),
        Index("ix_tasks_company_status_due", "company_id", "status", "due_at"),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    rule_id: Mapped[str | None] = mapped_column(ForeignKey("notification_rules.id"), nullable=True)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False)
    message_key: Mapped[str] = mapped_column(String(128), nullable=False)
    message_params: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[str] = mapped_column(String(36), nullable=False)
    source_item_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    route_key: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="OPEN")
    priority_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    priority_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    assignee_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    dedupe_key: Mapped[str] = mapped_column(String(160), nullable=False)
    source_event_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    actor_type: Mapped[str] = mapped_column(String(8), nullable=False)
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class TaskCandidate(UUIDMixin, TimestampMixin, Base):
    """Quién puede atender la tarea, fijado al crearla (CL-047-03)."""

    __tablename__ = "task_candidates"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("task_id", "user_id", name="uq_task_candidates_task_user"),
    )

    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)


class TaskEvent(UUIDMixin, TimestampMixin, Base):
    """Historial append-only de la tarea (FR-047-017, R-047-04)."""

    __tablename__ = "task_events"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("task_id", "dedupe_key", name="uq_task_events_task_dedupe"),
        CheckConstraint(f"event_type IN ({en(EVENTOS_TAREA)})", name="event_type"),
        CheckConstraint(f"actor_type IN ({en(TIPOS_ACTOR)})", name="actor_type"),
        CheckConstraint(_ACTOR, name="actor"),
    )

    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"), nullable=False, index=True)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(24), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(8), nullable=False)
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    from_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    to_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    #: Motivo escrito por una persona: dato, no texto del producto.
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    #: Solo los efectos del planificador la llevan; los nulos no chocan entre sí.
    dedupe_key: Mapped[str | None] = mapped_column(String(160), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Alert(UUIDMixin, TimestampMixin, Base):
    """Condición relevante. No crea tareas (FR-047-010)."""

    __tablename__ = "alerts"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("company_id", "dedupe_key", name="uq_alerts_company_dedupe"),
        CheckConstraint(f"status IN ({en(ESTADOS_ALERTA)})", name="status"),
        CheckConstraint(f"severity IN ({en(SEVERIDADES)})", name="severity"),
        CheckConstraint(f"actor_type IN ({en(TIPOS_ACTOR)})", name="actor_type"),
        CheckConstraint(_ACTOR, name="actor"),
        Index("ix_alerts_company_status", "company_id", "status"),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    rule_id: Mapped[str | None] = mapped_column(ForeignKey("notification_rules.id"), nullable=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    message_key: Mapped[str] = mapped_column(String(128), nullable=False)
    message_params: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[str] = mapped_column(String(36), nullable=False)
    source_item_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    route_key: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dedupe_key: Mapped[str] = mapped_column(String(160), nullable=False)
    source_event_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    actor_type: Mapped[str] = mapped_column(String(8), nullable=False)
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
