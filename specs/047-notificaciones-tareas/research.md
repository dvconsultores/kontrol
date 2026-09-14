# Investigación — SPEC 047

## 1. Protección de solapamiento

| Opción | Evaluación |
|---|---|
| `pg_try_advisory_lock` en una conexión dedicada durante el tick | **Elegida.** Si el proceso muere, PostgreSQL libera el bloqueo al cerrar la conexión: el arrendamiento es la propia sesión. Precedente: `pg_advisory_xact_lock` en `licensing/service.py` |
| `pg_advisory_xact_lock` | Se liberaría en el primer `commit` de un manejador |
| Fila con arrendamiento y caducidad | Exige elegir una caducidad; un tick largo podría perderla |
| Bloqueo en memoria | Prohibido (§9) |

El tick solapado **no espera**: registra `SKIPPED_OVERLAP` y sale con `0`. Esperar
acumularía procesos si el temporizador es más corto que un tick lento.

## 2. Idempotencia de efectos

Cada efecto tiene `dedupe_key` determinista y una restricción única:

| Efecto | Clave |
|---|---|
| Recibo de hecho | `(source, source_event_id)` |
| Notificación | `(company_id, "rule:{regla}:event:{hecho}")` o `task:{tarea}:reminder:{regla}:{ventana}` |
| Tarea | `(company_id, "rule:{regla}:item:{paso}")` |
| Alerta | `(company_id, "rule:{regla}:event:{hecho}")` |
| Recordatorio o escalada en el historial | `(task_id, "reminder:{regla}:{ventana}")`, `(task_id, "escalation:{regla}")` |

La colisión se captura con `es_violacion_unica` sobre esa restricción y se trata
como «ya hecho» (P25).

## 3. Recuperación tras una caída

| Manejador | Política | Efecto tras 48 h sin ticks |
|---|---|---|
| `approval_event_intake` | `DRAIN` — procesa todo hecho sin recibo, en lotes | Cada hecho, una vez |
| `task_reminders` | `LATEST_WINDOW` — solo la ventana vigente | Un recordatorio, no uno por ventana perdida |
| `task_escalations` | `EFFECT_ONCE` | Una escalada por regla |
| `notification_delivery` | `DUE_RETRY` | Un intento por entrega vencida |
| `approval_step_expiration` (045) | `OWNER_IDEMPOTENT` | La 045 marca cada paso una vez |

## 4. Mensajes

- La sustitución es propia: `{nombre}` con nombres `[a-z_][a-z0-9_]*`. **No** se
  usa `str.format`, que permite `{x.atributo}` y `{x[0]}`.
- Parámetros escalares: cadena, entero, booleano, nulo. Los importes viajan como
  cadena. Un valor compuesto es `MESSAGE_PARAM_INVALID`.
- Validación al publicar: una clave desconocida o un parámetro faltante no se
  persiste.
- Validación al leer: una fila histórica cuya clave ya no exista devuelve
  `render_error` y el frontend muestra un texto de catálogo; nunca la clave cruda.

## 5. Reloj

No hay librería de congelación en `requirements.txt`. El tick y los manejadores
reciben `now`; la API usa `datetime.now(UTC)`. Un `now` sin zona se rechaza con
`ValueError`. Las pruebas no duermen.

## 6. Coste de visibilidad

La lista y los contadores resuelven los permisos del usuario una vez, calculan los
`source_type` prohibidos y filtran en SQL con `NOT IN`. El recuento es un `COUNT`
por tipo; ninguna fila se trae al cliente para contar.
