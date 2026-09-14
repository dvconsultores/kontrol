# SPEC 047 — NOTIFICACIONES, TAREAS Y ALERTAS

| Campo | Valor |
|---|---|
| Estado | Ciclo documental hasta `/speckit.analyze` · **no implementada** · `BLOCKED BY MATERIAL DECISION` (OQ-047-01, OQ-047-02) |
| Tipo | **Capacidad transversal** (P22) |
| Fuente funcional | Vol. 2 §1, rama Inicio (`requirements-to-specs-map.md`) · pantallas «Mis tareas · Mis aprobaciones · Alertas» (`screens-to-specs-map.md`) · B-080 (`master-backlog.md`) |
| Autoridades | `ADR-D0-002` y `CL-045-11` (la 045 emite, la 047 consume) · `ADR-D0-003` (planificador de plataforma, propietaria 047) · `ADR-009` (cola y workers aplazados) · `ADR-D0-010` R-D0-10-2 (internacionalización como cambio propio) |
| Depende de | 045 `COMPLETE / CONVERGED` · 048 para canales externos (sin adaptador de correo) |
| Consumidora prevista | 049 (contadores) |
| Motor | PostgreSQL 18.x (`ADR-D0-001`); el QA actual corre sobre 16.2 — `ENVIRONMENT_BASELINE_DEVIATION` |

---

## 1. Propósito

Que un hecho que exige atención no dependa de que alguien vaya a buscarlo.

Hoy la 045 registra que un paso de aprobación se abrió y nadie se entera salvo
que abra su bandeja. La 046 declara que un archivo infectado es un evento para la
047 y no lo emite. Una reserva con caducidad no tiene quién la venza. La 047
convierte hechos de sus dueñas en notificaciones, tareas y alertas, **sin decidir
nunca cuándo un dominio tiene una obligación**.

## 2. Punto de partida — verificado el 2026-09-14 sobre `88634a1`

| Comprobación | Estado real |
|---|---|
| Tablas de notificación, tarea, alerta, recordatorio, preferencia o entrega | **ninguna** |
| Carpeta de Spec | **ninguna** (`spec-equivalence-map.md`: «Requisito huérfano») |
| Hechos de dominio | `approval_events` (045, 6 tipos, contrato CVG-045-05); `audit_events` en el resto; la 046 declara 4 eventos y **no emite ninguno** |
| `outbox_events` | declarada (ADR-009), **sin publicador ni consumidor** |
| Planificador, cola, worker, cron, temporizador | **ninguno**; `mark_expired` de la 045 **no tiene llamador** |
| Correo, push, SMS | **ninguno**; dueña 048 |
| WebSocket, SSE, sondeo | **ninguno** |
| Campana, centro de notificaciones, pantalla de tareas | **ninguna**; «Mis aprobaciones» es de la 045 (`/aprobaciones/bandeja`) |
| `NotificationContext` del frontend | avisos persistentes de interfaz (FR-001-063), **no** notificaciones de dominio |
| Sistema de internacionalización | **ninguno**; `<html lang="es">`, textos en español en los componentes |
| Auditoría | `app/shared/audit.py · record_audit`, append-only |
| Permisos | catálogo en `setup/api.py`, recurso en español y acción en inglés; ninguno de notificaciones, tareas o alertas |

## 3. Alcance

### Incluido

Notificación interna y su estado por destinatario · tarea con asignación,
historial, prioridad y vencimiento · alerta derivada de un hecho · enlace al
origen sin copiar datos de negocio · idempotencia por hecho de origen ·
preferencias mínimas · frontera con la entrega externa · contadores para la 049 ·
recordatorios y escalado **si OQ-047-01 los autoriza** · campana, centro de
notificaciones, tareas y alertas en el frontend.

### Fuera de alcance

Motor de reglas de negocio · motor de aprobación (045) · proveedor de correo,
push o SMS (048) · dashboard (049) · motor fiscal · motor de flujos paralelo ·
`reportes:view` y los defectos del dashboard (049) · la bandeja «Mis
aprobaciones», que ya existe y es de la 045.

## 4. Cuatro conceptos que no se mezclan

| Concepto | Qué es | Dueña |
|---|---|---|
| **Notificación** | Mensaje informativo para un destinatario | 047 |
| **Tarea** | Acción pendiente que requiere ejecución | 047 |
| **Alerta** | Señal de una condición relevante; no exige acción formal | 047 |
| **Aprobación** | Decisión formal | **045** — la 047 solo avisa, crea la tarea de atenderla y muestra su estado |

## 5. Principio

La dueña del dominio produce el hecho. La 047 lo transforma según configuración.
La 047 **nunca** revisa saldos, plazos o condiciones de otra Spec para decidir que
algo requiere atención.

## 6. Requisitos funcionales

| ID | Requisito | Precisión con el repositorio real |
|---|---|---|
| FR-047-001 | Notificación interna para uno o más destinatarios | Cómo nace a partir del hecho: **OQ-047-01** |
| FR-047-002 | Destinatario derivado de usuario, rol, permiso o asignación de negocio | Resuelto por el servidor; nunca identificadores enviados por el frontend para eventos de sistema. Fijado al crear (CL-047-03) |
| FR-047-003 | Estados no leída, leída, archivada | **Por destinatario**: `read_at`, `archived_at`. No hay estados previos que mapear |
| FR-047-004 | Notificación crítica persistente | No desaparece por tiempo de interfaz; se archiva solo por acción del destinatario |
| FR-047-005 | Tarea vinculada a un hecho de origen | Cómo nace: **OQ-047-01** |
| FR-047-006 | Asignación a usuario, rol o capacidad | Reasignación explícita, auditada y con control de versión |
| FR-047-007 | Estados `OPEN`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED` | No existe enum previo de tareas; los estados de `ApprovalStep` son de la 045 y **no** se reutilizan |
| FR-047-008 | Vencimiento | Instante `timestamptz` entregado por la dueña (CL-047-04) |
| FR-047-009 | Prioridad configurable | No existe catálogo de prioridades; se crea el mínimo configurable por empresa |
| FR-047-010 | Alertas derivadas de hechos | Una alerta no crea tarea sin regla que lo diga |
| FR-047-011 | Enlace `source_type`, `source_id`, referencia de ruta | Clave de ruta, no URL libre; sin datos de negocio copiados |
| FR-047-012 | Alcance de empresa | `CompanyContext` y cabecera `X-Kontrol-Company`; nunca `company_id` del cuerpo |
| FR-047-013 | Alcance de tenant | Ningún ítem cruza tenant |
| FR-047-014 | Visibilidad del destinatario | Revalidada en cada lectura contra alcance y permisos vigentes |
| FR-047-015 | Idempotencia | Un hecho lógico produce un único ítem por regla. Clave: **OQ-047-01** |
| FR-047-016 | `correlation_id`, `source_event_id`, clave de idempotencia | `request_id` y el id del hecho de origen existen en `audit_events` y `approval_events` |
| FR-047-017 | Auditoría de creación, asignación, lectura, completado, cancelado, escalado, reasignación | Con `record_audit`. El momento de «creado» y «escalado» depende de **OQ-047-01** |
| FR-047-018 | Preferencias solo de lo configurable | Una notificación obligatoria no se desactiva |
| FR-047-019 | Canal interno como base; externos solo si existe proveedor | Hoy no existe ninguno (048) |
| FR-047-020 | La 048 es dueña del adaptador externo | Sin SMTP ni credenciales en la 047 |
| FR-047-021 | Reintento externo idempotente | Según el contrato del proveedor de la 048, **inexistente** |
| FR-047-022 | Un fallo externo no elimina la notificación interna | Estado de entrega separado del ítem |
| FR-047-023 | Reutilizar el planificador canónico; no crear uno paralelo | **No existe**; `ADR-D0-003` lo asigna a la 047 y `ADR-009` exige ADR: **OQ-047-01** |
| FR-047-024 | Recordatorio asociado a vencimiento | «Si la arquitectura existente lo permite»: **OQ-047-01** |
| FR-047-025 | Escalado configurable con reglas explícitas | Sin plazos ni roles fijos en código. Ejecución: **OQ-047-01** |
| FR-047-026 | Sin duplicar lógica de negocio | La 047 no recalcula condiciones de la dueña |
| FR-047-027 | Seguridad ante hechos masivos | Sin explosión de duplicados |
| FR-047-028 | Paginación con contrato real | `page` y `page_size` ≤ 100, respuesta `{items, total, page, page_size}` |
| FR-047-029 | Filtros por estado, tipo, prioridad, asignatario, fecha y origen | Solo sobre campos reales |
| FR-047-030 | Contador por empresa, tenant y permisos | Agregado en el servidor |
| FR-047-031 | Enlace profundo al recurso correcto | Si el usuario tiene permiso del recurso origen |
| FR-047-032 | Enlace sin permiso | Prohibido, sin filtrar datos del origen |
| FR-047-033 | Plantillas reutilizables, versionadas, variables explícitas | Variable ausente = error controlado; sin ejecución de código |
| FR-047-034 | ES/EN; sin mensajes fuera del sistema i18n | **No existe sistema i18n** y `R-D0-10-2` lo reserva a un cambio propio: **OQ-047-02** |
| FR-047-035 | Sin borrado de historial sin política | Estado y archivo; no hay política de retención autorizada |
| FR-047-036 | La 049 consume contadores sin duplicar lógica | No leídas, tareas abiertas, tareas vencidas, alertas activas |

## 7. Requisitos no funcionales

| ID | Requisito |
|---|---|
| NFR-047-01 | Todo instante con zona; ningún `datetime` ingenuo |
| NFR-047-02 | Listas y contadores sin N+1; volumen de prueba > 100 con página 3 comprobada |
| NFR-047-03 | Registros y métricas sin carga sensible: hecho consumido, ítem creado, duplicado suprimido, entrega intentada o fallida, tarea vencida |
| NFR-047-04 | Interfaz WCAG 2.2 AA, adaptable, estados de carga, vacío, error, prohibido y no encontrado; sin tablas con desplazamiento horizontal |
| NFR-047-05 | Sin WebSocket ni SSE: el sondeo es la base (§50) |
| NFR-047-06 | Carreras forzadas con `HTTP 500 = 0` (P25) |
| NFR-047-07 | Paridad modelo ↔ migración ↔ PostgreSQL (P26); instalación limpia (P24) |

## 8. Reglas no negociables

| ID | Regla |
|---|---|
| R-047-01 | Completar una tarea **no** ejecuta la operación del dominio. Marcar «aprobar pago» como completada no aprueba nada |
| R-047-02 | El estado de lectura es del destinatario, nunca global |
| R-047-03 | Archivar no borra |
| R-047-04 | Reasignar conserva la asignación anterior |
| R-047-05 | Un fallo de canal externo no toca la notificación interna |
| R-047-06 | Un identificador ajeno responde igual que uno inexistente |
| R-047-07 | La carga del ítem no contiene datos del origen más allá del mínimo |
| R-047-08 | Ningún plazo, rol ni prioridad de escalado fijos en código |
| R-047-09 | Ni segundo outbox, ni cola privada, ni bus local |
| R-047-10 | La 047 no escribe en el catálogo de otra Spec ni corrige deudas ajenas |
| R-047-11 | La bandeja «Mis aprobaciones» no se duplica |
| R-047-12 | Nada se certifica aceptando un 500 como rechazo |

## 9. Estado del ciclo

`/speckit.clarify` encontró dos preguntas materiales sin autoridad que las
resuelva (`clarifications.md` §4). Conforme al §4 del prompt maestro, **no se
implementa**. Veredicto y recuento en `analysis-report.md`.
