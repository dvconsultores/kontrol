"""Spec 047 — notificaciones, tareas, alertas y planificador de plataforma.

Aditiva: trece tablas nuevas y los permisos `notificaciones`, `tareas` y
`alertas` concedidos al rol ADMIN, con el patrón idempotente de `0024`. Ninguna
tabla existente se toca.

Ninguna columna guarda texto visible: los mensajes son `message_key` y
`message_params` (OQ-047-02). Todo efecto lleva `dedupe_key` con restricción
única (ADR-D0-015 R-D0-15-5).

Revision ID: 0057_spec047_notifications
Revises: 0056_spec013_masters
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa

from alembic import op

revision = "0057_spec047_notifications"
down_revision = "0056_spec013_masters"
branch_labels = None
depends_on = None

PERMISOS = {
    "notificaciones": ("configure",),
    "tareas": ("view", "assign", "complete", "configure"),
    "alertas": ("view",),
}

_CONTADORES = ("items_seen >= 0 AND items_processed >= 0 "
               "AND items_skipped >= 0 AND items_failed >= 0")
_ACTOR = ("(actor_type = 'SYSTEM' AND actor_user_id IS NULL) "
          "OR (actor_type = 'USER' AND actor_user_id IS NOT NULL)")


def _en(*valores: str) -> str:
    return ", ".join(f"'{v}'" for v in valores)


def _tiempos() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    ]


def _contadores() -> list[sa.Column]:
    return [sa.Column(c, sa.Integer(), nullable=False, server_default="0")
            for c in ("items_seen", "items_processed", "items_skipped", "items_failed")]


def _empresa() -> sa.Column:
    return sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id"), nullable=False)


def _mensaje_y_origen() -> list[sa.Column]:
    return [
        sa.Column("message_key", sa.String(128), nullable=False),
        sa.Column("message_params", sa.JSON(), nullable=False),
        sa.Column("source_type", sa.String(64), nullable=False),
        sa.Column("source_id", sa.String(36), nullable=False),
    ]


def _identidad_y_actor() -> list[sa.Column]:
    return [
        sa.Column("dedupe_key", sa.String(160), nullable=False),
        sa.Column("source_event_id", sa.String(36), nullable=True),
        sa.Column("correlation_id", sa.String(64), nullable=True),
        sa.Column("actor_type", sa.String(8), nullable=False),
        sa.Column("actor_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
    ]


def _indice(tabla: str, *columnas: str, nombre: str | None = None) -> None:
    op.create_index(nombre or f"ix_{tabla}_{columnas[0]}", tabla, list(columnas))


def upgrade() -> None:
    # -- planificador -----------------------------------------------------------
    op.create_table(
        "scheduler_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("correlation_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        *_contadores(),
        sa.Column("error_code", sa.String(64), nullable=True),
        *_tiempos(),
        sa.UniqueConstraint("correlation_id", name="uq_scheduler_runs_correlation_id"),
        sa.CheckConstraint(
            f"status IN ({_en('STARTED', 'COMPLETED', 'COMPLETED_WITH_ERRORS', 'FAILED', 'SKIPPED_OVERLAP')})",
            name="status"),
        sa.CheckConstraint(_CONTADORES, name="counters"),
    )
    _indice("scheduler_runs", "status")

    op.create_table(
        "scheduler_handler_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("scheduler_runs.id"), nullable=False),
        sa.Column("handler_code", sa.String(64), nullable=False),
        sa.Column("owner_spec", sa.String(8), nullable=False),
        sa.Column("catch_up", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        *_contadores(),
        sa.Column("error_code", sa.String(64), nullable=True),
        *_tiempos(),
        sa.UniqueConstraint("run_id", "handler_code", name="uq_scheduler_handler_runs_run_handler"),
        sa.CheckConstraint(f"status IN ({_en('COMPLETED', 'FAILED', 'DISABLED')})",
                           name="status"),
        sa.CheckConstraint(
            f"catch_up IN ({_en('DRAIN', 'LATEST_WINDOW', 'EFFECT_ONCE', 'DUE_RETRY', 'OWNER_IDEMPOTENT')})",
            name="catch_up"),
        sa.CheckConstraint(_CONTADORES, name="counters"),
    )
    _indice("scheduler_handler_runs", "run_id")

    # -- reglas y catálogos ---------------------------------------------------------
    op.create_table(
        "notification_rules",
        sa.Column("id", sa.String(36), primary_key=True),
        _empresa(),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("effect", sa.String(16), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("mandatory", sa.Boolean(), nullable=False),
        sa.Column("priority_code", sa.String(32), nullable=True),
        sa.Column("reminder_offset_minutes", sa.Integer(), nullable=True),
        sa.Column("reminder_repeat_minutes", sa.Integer(), nullable=True),
        sa.Column("escalation_after_minutes", sa.Integer(), nullable=True),
        sa.Column("escalation_role_id", sa.String(36), sa.ForeignKey("roles.id"), nullable=True),
        sa.Column("auto_close", sa.Boolean(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        *_tiempos(),
        sa.UniqueConstraint("company_id", "code", name="uq_notification_rules_company_code"),
        sa.CheckConstraint(f"effect IN ({_en('NOTIFICATION', 'TASK', 'ALERT')})",
                           name="effect"),
        sa.CheckConstraint(f"severity IN ({_en('INFO', 'WARNING', 'CRITICAL')})",
                           name="severity"),
        sa.CheckConstraint("(escalation_after_minutes IS NULL) = (escalation_role_id IS NULL)",
                           name="escalation_pair"),
        sa.CheckConstraint("effect = 'TASK' OR (reminder_offset_minutes IS NULL "
                           "AND reminder_repeat_minutes IS NULL AND escalation_after_minutes IS NULL)",
                           name="timing_task_only"),
        sa.CheckConstraint("(reminder_offset_minutes IS NULL OR reminder_offset_minutes >= 0) "
                           "AND (reminder_repeat_minutes IS NULL OR reminder_repeat_minutes > 0) "
                           "AND (escalation_after_minutes IS NULL OR escalation_after_minutes > 0)",
                           name="minutes"),
        sa.CheckConstraint("reminder_repeat_minutes IS NULL OR reminder_offset_minutes IS NOT NULL",
                           name="repeat_needs_offset"),
    )
    _indice("notification_rules", "company_id")

    op.create_table(
        "task_priorities",
        sa.Column("id", sa.String(36), primary_key=True),
        _empresa(),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        *_tiempos(),
        sa.UniqueConstraint("company_id", "code", name="uq_task_priorities_company_code"),
        sa.CheckConstraint("rank >= 0", name="rank"),
    )
    _indice("task_priorities", "company_id")

    op.create_table(
        "notification_event_receipts",
        sa.Column("id", sa.String(36), primary_key=True),
        _empresa(),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("source_event_id", sa.String(36), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("run_correlation_id", sa.String(36), nullable=True),
        *_tiempos(),
        sa.UniqueConstraint("source", "source_event_id", name="uq_notification_event_receipts_source_event"),
        sa.CheckConstraint(f"outcome IN ({_en('APPLIED', 'NO_RULE')})",
                           name="outcome"),
    )
    _indice("notification_event_receipts", "company_id")

    # -- notificaciones -------------------------------------------------------------
    op.create_table(
        "notifications",
        sa.Column("id", sa.String(36), primary_key=True),
        _empresa(),
        sa.Column("rule_id", sa.String(36), sa.ForeignKey("notification_rules.id"), nullable=True),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("mandatory", sa.Boolean(), nullable=False),
        *_mensaje_y_origen(),
        sa.Column("source_item_id", sa.String(36), nullable=True),
        sa.Column("route_key", sa.String(64), nullable=False),
        *_identidad_y_actor(),
        *_tiempos(),
        sa.UniqueConstraint("company_id", "dedupe_key", name="uq_notifications_company_dedupe"),
        sa.CheckConstraint(f"severity IN ({_en('INFO', 'WARNING', 'CRITICAL')})",
                           name="severity"),
        sa.CheckConstraint(f"actor_type IN ({_en('SYSTEM', 'USER')})", name="actor_type"),
        sa.CheckConstraint(_ACTOR, name="actor"),
    )
    _indice("notifications", "company_id")

    op.create_table(
        "notification_recipients",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("notification_id", sa.String(36), sa.ForeignKey("notifications.id"), nullable=False),
        _empresa(),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        *_tiempos(),
        sa.UniqueConstraint("notification_id", "user_id", name="uq_notification_recipients_notification_user"),
    )
    _indice("notification_recipients", "notification_id")
    _indice("notification_recipients", "company_id")
    _indice("notification_recipients", "user_id", "company_id", "archived_at",
            nombre="ix_notification_recipients_user_company")

    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.String(36), primary_key=True),
        _empresa(),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("channel", sa.String(16), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        *_tiempos(),
        sa.UniqueConstraint("company_id", "user_id", "category", "channel",
                            name="uq_notification_preferences_user_category_channel"),
        sa.CheckConstraint(f"channel IN ({_en('INTERNAL', 'EMAIL')})", name="channel"),
    )
    _indice("notification_preferences", "company_id")
    _indice("notification_preferences", "user_id")

    op.create_table(
        "notification_deliveries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("recipient_id", sa.String(36), sa.ForeignKey("notification_recipients.id"), nullable=False),
        _empresa(),
        sa.Column("channel", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(64), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        *_tiempos(),
        sa.UniqueConstraint("recipient_id", "channel", name="uq_notification_deliveries_recipient_channel"),
        sa.CheckConstraint(f"channel IN ({_en('EMAIL')})", name="channel"),
        sa.CheckConstraint(f"status IN ({_en('PENDING', 'SENT', 'RETRYING', 'FAILED')})",
                           name="status"),
        sa.CheckConstraint("attempts >= 0", name="attempts"),
    )
    _indice("notification_deliveries", "company_id")
    _indice("notification_deliveries", "status")

    # -- tareas ---------------------------------------------------------------------
    op.create_table(
        "tasks",
        sa.Column("id", sa.String(36), primary_key=True),
        _empresa(),
        sa.Column("rule_id", sa.String(36), sa.ForeignKey("notification_rules.id"), nullable=True),
        sa.Column("task_type", sa.String(64), nullable=False),
        *_mensaje_y_origen(),
        sa.Column("source_item_id", sa.String(36), nullable=True),
        sa.Column("route_key", sa.String(64), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("priority_code", sa.String(32), nullable=True),
        sa.Column("priority_rank", sa.Integer(), nullable=True),
        sa.Column("assignee_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_by", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        *_identidad_y_actor(),
        *_tiempos(),
        sa.UniqueConstraint("company_id", "dedupe_key", name="uq_tasks_company_dedupe"),
        sa.CheckConstraint(
            f"status IN ({_en('OPEN', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED', 'RESOLVED_BY_SOURCE')})",
            name="status"),
        sa.CheckConstraint(f"actor_type IN ({_en('SYSTEM', 'USER')})", name="actor_type"),
        sa.CheckConstraint(_ACTOR, name="actor"),
        sa.CheckConstraint("version >= 1", name="version"),
    )
    _indice("tasks", "company_id")
    _indice("tasks", "source_item_id")
    _indice("tasks", "assignee_user_id")
    _indice("tasks", "company_id", "status", "due_at", nombre="ix_tasks_company_status_due")

    op.create_table(
        "task_candidates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("task_id", sa.String(36), sa.ForeignKey("tasks.id"), nullable=False),
        _empresa(),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        *_tiempos(),
        sa.UniqueConstraint("task_id", "user_id", name="uq_task_candidates_task_user"),
    )
    _indice("task_candidates", "task_id")
    _indice("task_candidates", "company_id")
    _indice("task_candidates", "user_id")

    op.create_table(
        "task_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("task_id", sa.String(36), sa.ForeignKey("tasks.id"), nullable=False),
        _empresa(),
        sa.Column("event_type", sa.String(24), nullable=False),
        sa.Column("actor_type", sa.String(8), nullable=False),
        sa.Column("actor_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("from_user_id", sa.String(36), nullable=True),
        sa.Column("to_user_id", sa.String(36), nullable=True),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column("dedupe_key", sa.String(160), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        *_tiempos(),
        sa.UniqueConstraint("task_id", "dedupe_key", name="uq_task_events_task_dedupe"),
        sa.CheckConstraint(
            f"event_type IN ({_en('CREATED', 'ASSIGNED', 'REASSIGNED', 'STARTED', 'COMPLETED', 'CANCELLED', 'REMINDED', 'ESCALATED', 'RESOLVED_BY_SOURCE')})",
            name="event_type"),
        sa.CheckConstraint(f"actor_type IN ({_en('SYSTEM', 'USER')})", name="actor_type"),
        sa.CheckConstraint(_ACTOR, name="actor"),
    )
    _indice("task_events", "task_id")
    _indice("task_events", "company_id")

    # -- alertas --------------------------------------------------------------------
    op.create_table(
        "alerts",
        sa.Column("id", sa.String(36), primary_key=True),
        _empresa(),
        sa.Column("rule_id", sa.String(36), sa.ForeignKey("notification_rules.id"), nullable=True),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        *_mensaje_y_origen(),
        sa.Column("source_item_id", sa.String(36), nullable=True),
        sa.Column("route_key", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        *_identidad_y_actor(),
        *_tiempos(),
        sa.UniqueConstraint("company_id", "dedupe_key", name="uq_alerts_company_dedupe"),
        sa.CheckConstraint(f"status IN ({_en('ACTIVE', 'RESOLVED')})", name="status"),
        sa.CheckConstraint(f"severity IN ({_en('INFO', 'WARNING', 'CRITICAL')})", name="severity"),
        sa.CheckConstraint(f"actor_type IN ({_en('SYSTEM', 'USER')})", name="actor_type"),
        sa.CheckConstraint(_ACTOR, name="actor"),
    )
    _indice("alerts", "company_id")
    _indice("alerts", "company_id", "status", nombre="ix_alerts_company_status")

    _conceder_permisos(op.get_bind())


def _conceder_permisos(bind) -> None:
    admin = bind.execute(sa.text(
        "SELECT id FROM roles WHERE code = 'ADMIN' AND company_id IS NULL LIMIT 1")).fetchone()
    for recurso, acciones in PERMISOS.items():
        for accion in acciones:
            fila = bind.execute(sa.text(
                "SELECT id FROM permissions WHERE resource = :r AND action = :a"),
                {"r": recurso, "a": accion}).fetchone()
            if fila:
                permiso = fila[0]
            else:
                permiso = str(uuid.uuid4())
                bind.execute(sa.text(
                    "INSERT INTO permissions (id, resource, action, scope_type) VALUES (:id, :r, :a, 'COMPANY')"),
                    {"id": permiso, "r": recurso, "a": accion})
            if not admin:
                continue
            ya = bind.execute(sa.text(
                "SELECT 1 FROM role_permissions WHERE role_id = :rol AND permission_id = :p"),
                {"rol": admin[0], "p": permiso}).fetchone()
            if not ya:
                bind.execute(sa.text(
                    "INSERT INTO role_permissions (id, role_id, permission_id) VALUES (:id, :rol, :p)"),
                    {"id": str(uuid.uuid4()), "rol": admin[0], "p": permiso})


def downgrade() -> None:
    for tabla in ("alerts", "task_events", "task_candidates", "tasks", "notification_deliveries",
                  "notification_preferences", "notification_recipients", "notifications",
                  "notification_event_receipts", "task_priorities", "notification_rules",
                  "scheduler_handler_runs", "scheduler_runs"):
        op.drop_table(tabla)
    recursos = tuple(PERMISOS)
    op.get_bind().execute(sa.text(
        "DELETE FROM role_permissions WHERE permission_id IN "
        "(SELECT id FROM permissions WHERE resource IN :r)").bindparams(sa.bindparam("r", expanding=True)),
        {"r": list(recursos)})
    op.get_bind().execute(sa.text("DELETE FROM permissions WHERE resource IN :r")
                          .bindparams(sa.bindparam("r", expanding=True)), {"r": list(recursos)})
