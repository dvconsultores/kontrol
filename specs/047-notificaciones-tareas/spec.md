# SPEC 047 — NOTIFICACIONES, TAREAS Y ALERTAS

| Campo | Valor |
|---|---|
| Estado | **`COMPLETE / CONVERGED`** (2026-09-14) · OQ-047-01 y OQ-047-02 cerradas por decisión del owner · evidencia en `convergence.md` |
| Tipo | **Capacidad transversal** (P22): notificaciones, tareas, alertas, **planificador de plataforma** y **base de localización** |
| Fuente funcional | Vol. 2 §1, rama Inicio (`requirements-to-specs-map.md`) · pantallas «Mis tareas · Mis aprobaciones · Alertas» (`screens-to-specs-map.md`) · B-080 (`master-backlog.md`) |
| Autoridades | `ADR-D0-015` (planificador) · `ADR-D0-002` y `CL-045-11` (la 045 emite, la 047 consume) · `ADR-D0-003` §G · `ADR-009` (acotado por ADR-D0-015) · `ADR-D0-010` R-D0-10-2 |
| Depende de | 045 `COMPLETE / CONVERGED` · 048 para canales externos (sin adaptador) |
| Consumidora prevista | 049 (contadores) |
| Motor | PostgreSQL 18.x (`ADR-D0-001`); QA sobre 16.2 — `ENVIRONMENT_BASELINE_DEVIATION` |

---

## 1. Propósito

Que un hecho que exige atención no dependa de que alguien vaya a buscarlo, y que
KONTROL pueda hacer algo cuando pasa el tiempo sin que nadie lo pida.

La 047 convierte hechos de sus dueñas en notificaciones, tareas y alertas, y
posee el único mecanismo con el que KONTROL ejecuta trabajo programado. **Nunca
decide cuándo un dominio tiene una obligación.**

## 2. Punto de partida — verificado el 2026-09-14 sobre `370e10a`

| Comprobación | Estado real |
|---|---|
| Tablas de notificación, tarea, alerta, preferencia, entrega o planificación | **ninguna** |
| Hechos de dominio | `approval_events` (045, 6 tipos); el resto solo audita; la 046 declara 4 eventos y no emite |
| `outbox_events` | declarada, sin productor ni consumidor |
| Planificador, cola, worker, cron | **ninguno**; `mark_expired` (045) sin llamador |
| Ejecución de órdenes en la pila | `docker compose exec -T backend python …` (`scripts/diagnose.sh`, `activate-test-license.sh`); CLI de host `kontrol.py` |
| Correo, push, SMS | ninguno; dueña 048 |
| Internacionalización | ninguna; `<html lang="es">` |
| Auditoría | `app/shared/audit.py · record_audit` |
| Permisos | recurso en español, acción en inglés (`setup/api.py`) |

## 3. Alcance

### Incluido

Planificador de plataforma (ADR-D0-015) · notificación interna con estado por
destinatario · tarea con candidatos, asignación, historial, prioridad y
vencimiento · alerta · reglas por empresa · consumo de `approval_events` ·
recordatorios y escaladas configurables · frontera de entrega externa ·
preferencias · mensajes por `message_key` y parámetros con catálogo `es` ·
contadores para la 049 · campana, centro, tareas, detalle, alertas, reglas y
preferencias en el frontend.

### Fuera de alcance

Motor de reglas de negocio · aprobación (045) · proveedor de correo, push o SMS
(048) · dashboard (049) · catálogo `en` (**DEFERRED**) · motor de plantillas
legales · reglas de caducidad de reservas (030), de retención (052) o de correo
(048) · habilitar el vencimiento de la 045 · migrar los textos de otros módulos
al catálogo · `reportes:view` y los defectos de la 049.

## 4. Cinco conceptos que no se mezclan

| Concepto | Qué es | Dueña |
|---|---|---|
| Notificación | Mensaje informativo para un destinatario | 047 |
| Tarea | Acción pendiente que requiere ejecución | 047 |
| Alerta | Señal de una condición relevante; no exige acción formal | 047 |
| Aprobación | Decisión formal | **045** |
| Trabajo programado | Qué hacer cuando pasa el tiempo | Marco 047 · regla de la Spec dueña del manejador |

## 5. Principios

1. La dueña produce el hecho; la 047 lo transforma según reglas configuradas.
2. El temporizador decide cuándo; la orden decide qué (R-D0-15-2).
3. Se guarda la clave del mensaje y sus parámetros; el texto se deriva.

## 6. Requisitos funcionales

### Notificaciones, tareas y alertas

| ID | Requisito | Precisión |
|---|---|---|
| FR-047-001 | Notificación interna para uno o más destinatarios | Nace de `publish`, llamado por el consumo de hechos o por una dueña |
| FR-047-002 | Destinatario derivado de asignación de negocio, rol o permiso | Resuelto en servidor y fijado al crear (CL-047-03); nunca ids del cliente |
| FR-047-003 | Estados no leída, leída, archivada | Por destinatario: `read_at`, `archived_at` |
| FR-047-004 | Notificación crítica persistente | Solo desaparece por acción del destinatario |
| FR-047-005 | Tarea vinculada a un hecho | Regla con efecto `TASK` |
| FR-047-006 | Asignación y reasignación | Candidatos fijados al crear; reasignación con `If-Match` y historial |
| FR-047-007 | Estados `OPEN`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED` + `RESOLVED_BY_SOURCE` | El último distingue el cierre por la dueña del completado por una persona |
| FR-047-008 | Vencimiento | Instante con zona entregado por la dueña |
| FR-047-009 | Prioridad configurable | Catálogo `task_priorities` por empresa |
| FR-047-010 | Alertas derivadas de hechos | Regla con efecto `ALERT`; no crean tareas |
| FR-047-011 | Enlace `source_type`, `source_id`, clave de ruta | Sin datos de negocio copiados |
| FR-047-012 | Alcance de empresa | `CompanyContext`; nunca `company_id` del cuerpo |
| FR-047-013 | Alcance de tenant | Ningún ítem cruza tenant |
| FR-047-014 | Visibilidad del destinatario | Revalidada en cada lectura: empresa accesible y permiso del recurso origen |
| FR-047-015 | Idempotencia | Clave lógica única por efecto; recibo único por hecho |
| FR-047-016 | Correlación | `source_event_id`, `correlation_id` y `dedupe_key` |
| FR-047-017 | Auditoría | Creación, lectura, archivo, asignación, reasignación, inicio, completado, cancelación, recordatorio, escalada, cierre por la dueña |
| FR-047-018 | Preferencias de lo configurable | Una notificación obligatoria no se desactiva |
| FR-047-019 | Canal interno como base | Externos solo con proveedor registrado |
| FR-047-020 | Adaptador externo de la 048 | La 047 no contiene SMTP ni credenciales |
| FR-047-021 | Reintento externo idempotente | Según el contrato del proveedor; clave = id de la entrega |
| FR-047-022 | Fallo externo no elimina la interna | Estado de entrega separado |
| FR-047-023 | Reutilizar el planificador canónico | Es el de ADR-D0-015; ninguno paralelo |
| FR-047-024 | Recordatorio asociado a vencimiento | Desplazamiento y repetición configurables por regla |
| FR-047-025 | Escalada configurable | Minutos tras vencer y rol destino por regla; nada fijo en código |
| FR-047-026 | Sin duplicar lógica de negocio | La 047 no recalcula condiciones de la dueña |
| FR-047-027 | Seguridad ante hechos masivos | Lotes acotados por tick; sin duplicados |
| FR-047-028 | Paginación real | `page`, `page_size` ≤ 100 |
| FR-047-029 | Filtros sobre campos reales | Estado, categoría, prioridad, ámbito, vencidas, origen, fechas |
| FR-047-030 | Contador por empresa, tenant y permisos | Agregado en servidor |
| FR-047-031 | Enlace al recurso correcto | Solo si el usuario tiene el permiso del origen |
| FR-047-032 | Enlace sin permiso | Ítem invisible; 404 idéntico al inexistente; sin datos del origen |
| FR-047-033 | Mensajes reutilizables | Catálogo por `message_key` estable; sin motor de plantillas legales (§22) |
| FR-047-034 | Localización | Arquitectura lista para varios idiomas; catálogo `es` en V1; `en` **DEFERRED** |
| FR-047-035 | Sin borrado de historial | Estados y archivo; ninguna ruta de borrado |
| FR-047-036 | Contadores para la 049 | No leídas, tareas abiertas, tareas vencidas, alertas activas |

### Planificador de plataforma (ADR-D0-015)

| ID | Requisito | Precisión |
|---|---|---|
| FR-047-037 | Orden canónica | `python -m app.modules.scheduler tick`; en el host, `python kontrol.py scheduler-tick` |
| FR-047-038 | Temporizador del sistema | Plantillas systemd instaladas con intervalo obligatorio de despliegue; sin reglas, SQL ni HTTP |
| FR-047-039 | Sin cola ni proceso residente | Ni Celery, Redis, RabbitMQ, Kafka, daemon, hilo ni bucle de espera |
| FR-047-040 | Protección de solapamiento | Bloqueo consultivo de PostgreSQL; el segundo tick queda `SKIPPED_OVERLAP` |
| FR-047-041 | Registro de ejecución | `scheduler_runs` y `scheduler_handler_runs` con estados y contadores; sin secretos |
| FR-047-042 | Registro explícito de manejadores | Código, Spec dueña, habilitado y política de recuperación; nunca rutas configurables |
| FR-047-043 | Idempotencia del tick | Repetir el tick no duplica efectos |
| FR-047-044 | Recuperación controlada | Tras una caída, como máximo el efecto lógico vigente |
| FR-047-045 | Actor de sistema | `actor_type = SYSTEM`, sin usuario ficticio; auditoría con `source = "SCHEDULER"` |
| FR-047-046 | Contexto explícito por empresa | Cada efecto lleva tenant, empresa, actor y correlación del tick |
| FR-047-047 | Códigos de salida | `0` completado u omitido · `2` completado con errores · `1` fallo operacional |
| FR-047-048 | Aislamiento por instalación | Un temporizador por pila de cliente |
| FR-047-049 | Manejadores de otras dueñas | Invocan su contrato canónico; 045 registrado y deshabilitado; 030, 048 y 052 como puntos de integración |

### Mensajes y localización

| ID | Requisito | Precisión |
|---|---|---|
| FR-047-050 | Persistencia de mensaje | `message_key` + `message_params`; ningún texto compuesto se guarda |
| FR-047-051 | Renderizador por idioma | Catálogo `es`; añadir `en` no exige migración ni cambio de contrato |
| FR-047-052 | Contrato de parámetros | Declarados por clave; faltante o clave desconocida → error controlado; sobrante → ignorado; no escalar → inválido; sin ejecución de código |
| FR-047-053 | Cadenas visibles nuevas fuera de catálogo | **0**, en backend y frontend |
| FR-047-054 | Transporte de hechos V1 | El tick consume `approval_events` con recibo por evento; `outbox_events` no se usa; `publish` es la llamada de servicio canónica |

**54 requisitos funcionales.**

## 7. Requisitos no funcionales

| ID | Requisito |
|---|---|
| NFR-047-01 | Ningún `datetime` ingenuo: el planificador rechaza un reloj sin zona |
| NFR-047-02 | Listas y contadores sin N+1; volumen > 100 con página 3 |
| NFR-047-03 | Registros sin carga sensible |
| NFR-047-04 | WCAG 2.2 AA, adaptable, estados de carga, vacío, error, prohibido y no encontrado |
| NFR-047-05 | Sin WebSocket ni SSE: sondeo |
| NFR-047-06 | Carreras forzadas con 0 errores 500 y 0 `IntegrityError` sin capturar |
| NFR-047-07 | Paridad modelo ↔ migración ↔ PostgreSQL; instalación limpia |

## 8. Reglas no negociables

| ID | Regla |
|---|---|
| R-047-01 | Completar una tarea no ejecuta la operación del dominio |
| R-047-02 | Lectura por destinatario, nunca global |
| R-047-03 | Archivar no borra |
| R-047-04 | Reasignar conserva la asignación anterior |
| R-047-05 | Un fallo externo no toca la notificación interna |
| R-047-06 | Un id ajeno responde igual que uno inexistente |
| R-047-07 | Carga mínima del origen |
| R-047-08 | Ningún plazo, rol ni prioridad fijos en código |
| R-047-09 | Ni segundo outbox, ni cola, ni bus local |
| R-047-10 | La 047 no corrige deudas ajenas |
| R-047-11 | La bandeja de aprobaciones no se duplica: una tarea de aprobación enlaza a ella y nunca decide |
| R-047-12 | Nada se certifica aceptando un 500 como rechazo |
| R-047-13 | El temporizador no conoce reglas de negocio |
| R-047-14 | El texto renderizado nunca es autoridad |
