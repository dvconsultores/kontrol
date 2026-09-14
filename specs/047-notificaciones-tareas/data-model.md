# Modelo de datos — SPEC 047

Migración aditiva `0057_spec047_notifications` sobre `0056_spec013_masters`:
**trece tablas**. Toda columna temporal lleva zona. Ninguna tabla admite borrado por
la API. Los `CHECK` se llaman `ck_<tabla>_<sufijo>`: modelo y migración declaran solo
el sufijo y la convención del `MetaData` compone el nombre.

## Planificador — `app/modules/scheduler`

### `scheduler_runs` · `Scope.INSTALLATION`

| Columna | Tipo | Nota |
|---|---|---|
| `id` | String(36) PK | |
| `correlation_id` | String(36) | **único** |
| `status` | String(32) | `STARTED`, `COMPLETED`, `COMPLETED_WITH_ERRORS`, `FAILED`, `SKIPPED_OVERLAP` (check) |
| `scheduled_for` | timestamptz | «ahora» lógico con el que corrieron los manejadores |
| `started_at`, `finished_at` | timestamptz | `finished_at` nulo mientras corre |
| `items_seen`, `items_processed`, `items_skipped`, `items_failed` | Integer ≥ 0 | |
| `error_code` | String(64) nulo | sin mensajes ni secretos |

### `scheduler_handler_runs` · `Scope.INSTALLATION`

`run_id` FK → `scheduler_runs` · `handler_code` · `owner_spec` · `catch_up` · `status`
(`COMPLETED`, `FAILED`, `DISABLED`) · tiempos · contadores · `error_code`.
Único `(run_id, handler_code)`.

## Notificaciones — `app/modules/notifications`

### `notification_rules` · `Scope.COMPANY`

| Columna | Nota |
|---|---|
| `company_id` FK | |
| `code` | único con `company_id` |
| `source`, `event_type` | del catálogo de fuentes (`APPROVAL`, `approval.*`) |
| `effect` | `NOTIFICATION`, `TASK`, `ALERT` |
| `severity` | `INFO`, `WARNING`, `CRITICAL` |
| `mandatory` | la preferencia no la desactiva |
| `priority_code` | nulo o código de `task_priorities` |
| `reminder_offset_minutes`, `reminder_repeat_minutes` | ≥ 0 / > 0, solo `TASK` |
| `escalation_after_minutes` + `escalation_role_id` FK `roles` | ambos o ninguno, solo `TASK` |
| `auto_close` | cierra tareas y alertas cuando la dueña resuelve |
| `active`, `created_by` | |

### `task_priorities` · `Scope.COMPANY`

`company_id`, `code`, `name`, `rank ≥ 0`, `active`. Único `(company_id, code)`.

### `notification_event_receipts` · `Scope.COMPANY`

`company_id`, `source`, `source_event_id`, `event_type`, `outcome`
(`APPLIED`, `NO_RULE`), `run_correlation_id`. **Único `(source, source_event_id)`.**

### `notifications` · `Scope.COMPANY`

`company_id`, `rule_id` FK nulo, `category`, `severity`, `mandatory`,
`message_key`, `message_params` JSON, `source_type`, `source_id`,
`source_item_id`, `route_key`, `dedupe_key`, `source_event_id`,
`correlation_id`, `actor_type` (`SYSTEM`, `USER`), `actor_user_id` FK nulo.
Único `(company_id, dedupe_key)`. Check: `USER` exige usuario y `SYSTEM` lo
prohíbe. **Sin columna de texto.**

### `notification_recipients` · `Scope.COMPANY`

`notification_id` FK, `company_id`, `user_id` FK, `read_at`, `archived_at`.
Único `(notification_id, user_id)`. Índice `(user_id, company_id, archived_at)`.

### `notification_preferences` · `Scope.COMPANY`

`company_id`, `user_id` FK, `category`, `channel` (`INTERNAL`, `EMAIL`),
`enabled`. Único `(company_id, user_id, category, channel)`.

### `notification_deliveries` · `Scope.COMPANY`

`recipient_id` FK, `company_id`, `channel` (`EMAIL`), `status`
(`PENDING`, `SENT`, `RETRYING`, `FAILED`), `attempts ≥ 0`, `next_attempt_at`,
`last_error_code`, `sent_at`. Único `(recipient_id, channel)`.

## Tareas

### `tasks` · `Scope.COMPANY`

`company_id`, `rule_id`, `task_type`, `message_key`, `message_params`,
`source_type`, `source_id`, `source_item_id`, `route_key`, `status`
(`OPEN`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`, `RESOLVED_BY_SOURCE`),
`priority_code`, `priority_rank`, `assignee_user_id` FK nulo, `due_at`,
`closed_at`, `closed_by` FK nulo, `version ≥ 1`, `dedupe_key`,
`source_event_id`, `correlation_id`, `actor_type`, `actor_user_id`.
Único `(company_id, dedupe_key)`. Índice `(company_id, status, due_at)`.

### `task_candidates` · `Scope.COMPANY`

`task_id` FK, `company_id`, `user_id` FK. Único `(task_id, user_id)`. Instantánea
fijada al crear.

### `task_events` · `Scope.COMPANY` — append-only

`task_id` FK, `company_id`, `event_type` (`CREATED`, `ASSIGNED`, `REASSIGNED`,
`STARTED`, `COMPLETED`, `CANCELLED`, `REMINDED`, `ESCALATED`,
`RESOLVED_BY_SOURCE`), `actor_type`, `actor_user_id`, `from_user_id`,
`to_user_id`, `reason`, `dedupe_key`, `occurred_at`. Único parcial
`(task_id, dedupe_key) WHERE dedupe_key IS NOT NULL`.

## Alertas

### `alerts` · `Scope.COMPANY`

`company_id`, `rule_id`, `category`, `severity`, `message_key`,
`message_params`, `source_type`, `source_id`, `source_item_id`, `route_key`,
`status` (`ACTIVE`, `RESOLVED`), `resolved_at`, `dedupe_key`,
`source_event_id`, `correlation_id`, `actor_type`, `actor_user_id`.
Único `(company_id, dedupe_key)`.

## Permisos

Migración idempotente al estilo de `0024`: `notificaciones:configure`,
`tareas:view|assign|complete|configure`, `alertas:view`, concedidos al rol ADMIN.
