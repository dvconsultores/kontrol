# Contratos — SPEC 047

Todas las rutas son de empresa (`X-Kontrol-Company`), autenticadas, y listan con
`page` y `page_size` ≤ 100 devolviendo `{items, total, page, page_size}`.

## Mensaje

```json
{"key": "approval.step_opened.notification",
 "params": {"process_type": "COMPRAS", "document_type": "PurchaseOrder", "level_order": 1},
 "text": "Hay una aprobación de COMPRAS pendiente (nivel 1).",
 "render_error": null}
```

Con clave desconocida o parámetro faltante: `text = null` y
`render_error ∈ {MESSAGE_KEY_UNKNOWN, MESSAGE_PARAM_MISSING, MESSAGE_PARAM_INVALID}`.

## Notificaciones

| Método | Ruta | Permiso | Resultado |
|---|---|---|---|
| GET | `/notifications` | destinatario | filtros `state` (`active`, `unread`, `read`, `archived`, `all`), `category`, `severity`, `source_type`, `created_from`, `created_to` |
| GET | `/notifications/{id}` | destinatario | 404 `NOTIFICATION_NOT_FOUND` si no es visible |
| POST | `/notifications/{id}/read` | destinatario | estado resultante; repetir no cambia `read_at` |
| POST | `/notifications/{id}/archive` | destinatario | estado resultante |
| GET | `/notifications/counts` | usuario de la empresa | `{unread_notifications, open_tasks, overdue_tasks, active_alerts}` |
| GET | `/notifications/preferences` | propio | preferencias y reglas opcionales |
| PUT | `/notifications/preferences` | propio | 409 `NOTIFICATION_MANDATORY`; 422 `CHANNEL_UNAVAILABLE` |
| GET | `/notifications/rules` | `notificaciones:configure` | |
| POST | `/notifications/rules` | `notificaciones:configure` | 409 `NOTIFICATION_RULE_CODE_TAKEN`; 422 `NOTIFICATION_RULE_INVALID` |
| POST | `/notifications/rules/{id}/deactivate` | `notificaciones:configure` | |
| GET | `/notifications/sources` | `notificaciones:configure` | eventos consumibles y efectos admitidos |

## Tareas

| Método | Ruta | Permiso | Resultado |
|---|---|---|---|
| GET | `/tasks` | propio · `tareas:view` para `scope=all` | filtros `scope` (`mine`, `candidate`, `all`), `status`, `overdue`, `priority`, `source_type`, `due_from`, `due_to` |
| GET | `/tasks/{id}` | candidato, asignatario o `tareas:view` | tarea, historial y `allowed_actions` |
| POST | `/tasks/{id}/start` | `tareas:complete` + candidato o asignatario | |
| POST | `/tasks/{id}/complete` | `tareas:complete` + candidato o asignatario | 409 `TASK_ALREADY_CLOSED` |
| POST | `/tasks/{id}/cancel` | `tareas:assign` | motivo obligatorio |
| POST | `/tasks/{id}/reassign` | `tareas:assign` · `If-Match` | 428 `TASK_IF_MATCH_REQUIRED` sin versión; 409 `TASK_VERSION_CONFLICT`; 422 `TASK_ASSIGNEE_NOT_IN_COMPANY` |
| GET | `/tasks/priorities` | usuario de la empresa | |
| POST | `/tasks/priorities` | `tareas:configure` | 409 `TASK_PRIORITY_CODE_TAKEN` |

Toda orden devuelve la tarea resultante con su `version`.

## Alertas

| Método | Ruta | Permiso |
|---|---|---|
| GET | `/alerts` | `alertas:view`; filtros `status`, `severity`, `source_type` |

## Enlaces

| `route_key` | Ruta del frontend | Permiso del origen |
|---|---|---|
| `approval_inbox` | `/aprobaciones/bandeja` | `aprobaciones:view` |

## Planificador

No hay ruta HTTP. Orden: `python -m app.modules.scheduler tick`. Salida en JSON
con `status`, `correlation_id` y contadores por manejador.
