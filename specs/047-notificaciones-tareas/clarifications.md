# `/speckit.clarify` — SPEC 047 · NOTIFICACIONES, TAREAS Y ALERTAS

> 2026-09-14, sobre `88634a1`, rama `develop`, árbol limpio. Inventario hecho con
> búsquedas sobre el código, las migraciones y la documentación, no con informes
> previos.

## 1. Mapa de capacidades

| Capacidad | Artefacto existente | Dueña canónica | ¿Implementado? | ¿Reutilizable? | ¿Falta? | Riesgo de duplicado |
|---|---|---|---|---|---|---|
| Modelo de notificación | ninguno | 047 | No | — | Sí | Bajo |
| Modelo de tarea | ninguno; la bandeja `GET /approvals/inbox` calcula pasos pendientes | 045 (aprobaciones) · 047 (tareas genéricas) | Solo para aprobaciones | La bandeja, como fuente y como pantalla | Tareas genéricas | **Alto**: una segunda bandeja de aprobaciones |
| Modelo de alerta | ninguno | 047 | No | — | Sí | Bajo |
| Outbox | `outbox_events` (`system/models.py`), sin publicador ni consumidor | ADR-009 («integraciones futuras») | Declarada | El sobre, sí | Publicador y consumidor | **Alto**: un segundo outbox |
| Hechos de dominio | `approval_events` (6 tipos); `audit_events` en 030, 037, 038 y el resto; 046 declara `document.uploaded`, `.version_created`, `.expiring`, `.scan_failed` y no emite | Cada dueña | 045 sí · 046 no · resto por auditoría | `approval_events` (contrato CVG-045-05) y `audit_events` (D0-03: «si 047 los introduce, la auditoría anterior es la fuente») | Emisión de la 046 | Medio |
| Bus de eventos | ninguno | — | No | — | — | §10 lo prohíbe si es local |
| Cola y workers | ninguno; ADR-009 los aplaza hasta «Spec con necesidad demostrada (reportes pesados, correos, tareas programadas)» | ADR-009, revisión trasladada a 048 y 050 | No | — | — | **Alto** |
| Planificador | ninguno. La 001 prevé «scheduler del sistema» para salud y diagnóstico; no hay `.timer`, `crontab` ni `OnCalendar` en el repositorio; `mark_expired` (045) no tiene llamador; las reservas vencen por endpoint de operador | `ADR-D0-003`: «planificador de plataforma, propietaria Spec 047» | No | — | Sí | **Alto** → OQ-047-01 |
| Adaptador de correo | ninguno; `httpx` solo lo usa el licenciamiento central | 048 | No | — | Sí, en la 048 | — |
| WebSocket / SSE | ninguno | — | No | — | No se necesita | — |
| Sondeo | ninguno (`refetchInterval`: 0 usos) | TanStack Query | Capacidad de librería | Sí | — | — |
| Contador de no leídas | ninguno | 047 | No | — | Sí | — |
| Campana en cabecera | `layout/Topbar.tsx` sin campana | 047 | No | El `Topbar` como lugar | Sí | — |
| Avisos de interfaz | `NotificationContext`, `PersistentNotification` (FR-001-063) | 001 | Sí | Para dar respuesta a acciones, **no** como almacén de notificaciones | — | Medio: confundirlos |
| Pantalla de tareas | ninguna, salvo `aprobaciones/bandeja/BandejaPage.tsx` | 045 · 047 | Solo aprobaciones | — | Tareas genéricas | **Alto** |
| Aviso de aprobación | la 045 emite, no notifica | 045 → 047 | Eventos, sí | Sí | El aviso | — |
| Plantillas de mensaje | ninguna (`product_templates` y `service_templates` son maestros; ReportLab es para documentos, ADR-007) | 047 | No | No | Sí | Bajo |
| Permisos | `setup/api.py`: `aprobaciones:[view,create,edit,approve,delegate,configure]`, `documentos:[…]`, `reportes:[view,export]` | 003 | Convención, sí | Sí | Recursos de la 047 | Medio: inventar cadenas |
| Auditoría | `app/shared/audit.py · record_audit` y `_audit` locales por módulo | 006 | Sí | Sí | — | Bajo |
| Trabajos en segundo plano | `report_jobs` de la 009, síncronos en la petición | 009 | Sí | No como planificador | — | — |
| Reintentos | `IdempotencyRecord` para `Idempotency-Key` en POST críticos (ADR-013) | 001 | Sí | Sí, para órdenes HTTP | Reintento de entrega externa (048) | — |
| Internacionalización | ninguna; `<html lang="es">`; textos en español en componentes; fechas con `toLocaleString("es-VE")` | **ninguna Spec del catálogo** | No | — | Sí | → OQ-047-02 |
| Idioma del usuario | `User` sin idioma ni zona horaria | 003 | No | — | Solo si OQ-047-02 lo exige | — |
| Zona horaria | columnas `DateTime(timezone=True)`; `license_timezone` solo para la licencia; el frontend formatea en la zona del navegador | 001 | Sí | Sí | — | — |
| Paginación | `page`, `page_size` ≤ 100 y `{items,total,page,page_size}` en `audit/api.py`; `components/Pagination.tsx` | 001 | Sí | Sí | — | — |
| Estados de interfaz | `LoadingState`, `EmptyState`, `ErrorState`, `ForbiddenState`, `NotFoundState`, `AsyncButton` | 001 · 005 | Sí | Sí | — | — |
| Carreras | `core/integrity.py · es_violacion_unica`; `tests/concurrency.py · carrera` | P25 | Sí | Sí | — | — |

## 2. Decisiones resueltas con autoridad existente

| ID | Pregunta | Decisión | Autoridad |
|---|---|---|---|
| CL-047-01 | ¿Dónde vive la Spec? | `specs/047-notificaciones-tareas/`. No es una Spec paralela: la 047 no tenía carpeta | Precedente de 045 y 046; `spec-equivalence-map.md` |
| CL-047-02 | ¿Se crean tareas espejo de los pasos de aprobación? | **No.** «Mis aprobaciones» es la bandeja de la 045. La 047 avisa de `approval.step_opened` y enlaza a la bandeja; no duplica ni el cálculo de elegibles ni la delegación | §7 D y §95 del prompt; CVG-045-05 («la bandeja es el canal actual») |
| CL-047-03 | ¿Destinatario fijado o dinámico? | **Fijado al crear**; la reasignación es explícita y auditada. La **visibilidad** se revalida en cada lectura: quien pierde alcance o permiso deja de ver, sin que el ítem cambie de dueño | La 045 fija `eligible_actors` al abrir el paso (`approvals/service.py:389`); R-D0-02-3 (instantánea) y R-D0-02-8 (delegación explícita) |
| CL-047-04 | ¿Reloj y zona? | Vencimientos como instante `timestamptz` entregado por la dueña; vencido = `now(UTC) > due_at`; la 047 no convierte fechas de calendario. No hace falta zona por empresa mientras las dueñas entreguen instantes | `ApprovalStep.due_at` con zona; convención de modelos |
| CL-047-05 | ¿Nombres de permiso? | Convención real: recurso en español y acción en inglés. Propuesta: `notificaciones:view`, `tareas:view`, `tareas:assign`, `tareas:complete`, `alertas:view`. **No se escriben en el catálogo hasta implementar.** Leer lo propio no pide permiso de recurso: lo autoriza la fila de destinatario, más el alcance de empresa | `setup/api.py` |
| CL-047-06 | ¿Paginación? | `page` y `page_size` ≤ 100; nunca `limit` | `audit/api.py`; invariante de selector paginado |
| CL-047-07 | ¿Sobre de evento? | No se inventa uno. Las fuentes reales son `approval_events` y `audit_events`, cuyos campos cubren el §12 (`id`, tipo o `action`, `tenant_id`, `company_id`, `user_id`, `entity_type`, `entity_id`, `event_time`, `request_id`, `after`). Dónde lee el consumidor depende de OQ-047-01 | CVG-045-05; D0-03 §7 |
| CL-047-08 | ¿Canales externos? | Solo frontera: intención y estado de entrega. Sin adaptador | FR-047-019/020; la 048 no tiene correo → `OWNER_DEPENDENCY`, no pregunta de la 047 |
| CL-047-09 | ¿Eventos de la 046? | Se consumirán cuando la 046 los emita | `OWNER_DEPENDENCY` 046 |
| CL-047-10 | ¿Hechos de la 038 para el flujo A? | La aprobación de pago pasa por la 045 (`approval.step_opened`). Reembolsos y conciliación solo dejan auditoría (`RECONCILIATION_TRANSITIONED`, …) | Código de `treasury` |
| CL-047-11 | ¿Tiempo real? | Sondeo con TanStack Query | §50 |
| CL-047-12 | ¿Los avisos de interfaz son notificaciones? | No. `NotificationContext` sigue dando respuesta a acciones; el centro de notificaciones es otra cosa | FR-001-063 |

## 3. Contradicciones abiertas

**C-047-01 · Dueña sin mecanismo.** `ADR-D0-003` y la decisión D0-03 asignan a la
047 el «planificador de plataforma». `ADR-009` prohíbe cola y worker sin un ADR que
demuestre la necesidad, compare alternativas y evalúe instalaciones
independientes, y sitúa la revisión en las Specs 048 y 050, no en la 047. El §29
del prompt prohíbe bucles de espera y workers locales. FR-047-023 pide reutilizar
el planificador canónico, que no existe. → **OQ-047-01**.

**C-047-02 · Requisito sin sistema.** FR-047-034 y §28 exigen ES/EN dentro del
sistema i18n y prohíben cadenas solo en español. No existe sistema i18n, ninguna
Spec del catálogo lo posee, y `R-D0-10-2` dice que la internacionalización «se
abordará como cambio propio, con su migración». → **OQ-047-02**.

## 4. Preguntas materiales

### OQ-047-01 · Cuándo y cómo nacen notificaciones, tareas, recordatorios y escaladas

Un recordatorio o una escalada dependen del paso del tiempo, y hoy nada en KONTROL
ejecuta nada si no llega una petición.

| Opción | Qué construye | Consecuencias |
|---|---|---|
| **A · Planificador de plataforma de la 047** ejecutado por el temporizador del sistema operativo, que lanza una orden idempotente; los trabajos se reclaman en PostgreSQL con bloqueo por fila y salto de bloqueadas. Sin Redis ni Celery | Filas propias de notificación, tarea y alerta creadas al procesar el hecho; recordatorios y escaladas reales | Exige enmendar ADR-009 con un ADR nuevo, un artefacto de despliegue (052) y vigilancia. **Desbloquea además** la caducidad de reservas de la 030, `mark_expired` de la 045 y el correo de la 048. La latencia es el intervalo del temporizador |
| **B · Proyección en lectura.** Notificaciones y alertas se derivan en consulta de `approval_events` y `audit_events`; hay filas propias solo cuando el usuario actúa (leer, archivar, reasignar, completar); vencido y escalado se calculan en consulta | Sin ADR ni despliegue nuevos | Canal externo **imposible** sin A; «creado» y «escalado» son derivados, no hechos propios con momento; cada contador recalcula destinatarios; `mark_expired` y la caducidad de la 030 siguen sin ejecutor |
| C · Llamada síncrona de cada dueña a la 047 | — | **Descartada** salvo autoridad: contradice CL-045-11 («045 no conoce a 047») y §10 (bus local) |
| D · Bucle periódico dentro del proceso de la API | — | **Descartada**: §29 y ADR-009 |

**Por qué es material.** Cambia el esquema (filas materializadas o solo filas de
estado), el significado de la auditoría (FR-047-017), si FR-047-021/022/024/025
llegan a cumplirse, la topología de despliegue, y es precisamente el acto de
gobierno que ADR-009 reserva. Ninguna autoridad del repositorio elige.

**Recomendación: A**, decidida como ADR. Es lo que `ADR-D0-003` anticipa y la
única que desbloquea también a 030, 045 y 048. B solo es válida si se acepta que la
047 v1 sea exclusivamente interna.

**Decide:** Arquitectura y Producto.

### OQ-047-02 · Idioma de notificaciones, tareas y alertas

| Opción | Qué construye | Consecuencias |
|---|---|---|
| **A · Internacionalización como cambio propio, antes** | Sistema de mensajes del frontend, preferencia de idioma de usuario (003), catálogos ES/EN, con dueña designada | La 047 espera a ese cambio; es lo que dice `R-D0-10-2` |
| **B · La 047 sienta la base transversal** | Lo mismo, dentro de la 047 | Absorbe una capacidad transversal sin designación (P22) y contradice `R-D0-10-2` |
| **C · FR-047-034 enmendado para la 047** | Contrato independiente del idioma: clave de mensaje y parámetros, **nunca texto ya compuesto en la base de datos**; catálogo solo ES en v1; EN cuando exista el cambio de i18n | La parte irreversible —qué se guarda— queda bien hecha; la interfaz en inglés espera |

**Por qué es material.** A añade un prerrequisito y toca el modelo de la 003; B
cambia el alcance; C modifica un requisito dado expresamente.

**Recomendación: C**, con A programada como cambio propio.

**Decide:** Producto.

## 5. Dependencias de dueña — no son preguntas de la 047

| Dependencia | Dueña | Efecto |
|---|---|---|
| Adaptador de correo, push o SMS | 048 | FR-047-019..022 quedan en frontera sin adaptador |
| Emisión de `document.*` | 046 | Sin hechos documentales que consumir |
| Idioma del usuario | 003 | Solo si OQ-047-02 elige A o B |
| Internacionalización | **sin dueña** | `OWNER GAP = 1` |

## 6. Recuento

| | |
|---|---|
| Decisiones resueltas con autoridad | 12 |
| Contradicciones abiertas | 2 |
| Preguntas materiales | **2** |
| UNKNOWN | 0 |
| Dependencias de dueña | 3 |
| Huecos de dueña | 1 — internacionalización |
