# `/speckit.clarify` — SPEC 047 · NOTIFICACIONES, TAREAS Y ALERTAS

> Inventario inicial: 2026-09-14 sobre `88634a1`. Reapertura con las decisiones
> del owner: 2026-09-14 sobre `370e10a`, rama `develop`, árbol limpio.

## 1. Mapa de capacidades

| Capacidad | Artefacto existente | Dueña canónica | ¿Implementado? | ¿Reutilizable? | ¿Falta? | Riesgo de duplicado |
|---|---|---|---|---|---|---|
| Modelo de notificación | ninguno | 047 | No | — | Sí | Bajo |
| Modelo de tarea | ninguno; `GET /approvals/inbox` calcula pasos pendientes | 045 (aprobaciones) · 047 (tareas) | Solo aprobaciones | La bandeja como destino del enlace | Tareas | **Alto**: una segunda bandeja |
| Modelo de alerta | ninguno | 047 | No | — | Sí | Bajo |
| Outbox | `outbox_events`, sin productor ni consumidor | ADR-009 | Declarada | No se usa en V1 | — | **Alto**: un segundo outbox |
| Hechos de dominio | `approval_events` (6 tipos); auditoría en el resto; la 046 no emite | Cada dueña | 045 sí | `approval_events` (CVG-045-05) | Emisión de la 046 | Medio |
| Bus de eventos | ninguno | — | No | — | — | §10 lo prohíbe |
| Cola y workers | ninguno | ADR-009 | No | — | **No se crean** (ADR-D0-015) | — |
| Planificador | ninguno; `mark_expired` sin llamador | **047** (ADR-D0-003, ADR-D0-015) | No | — | Sí | Alto sin ADR → cerrado |
| Ejecución de órdenes en la pila | `docker compose exec -T backend python …` en `scripts/diagnose.sh` y `activate-test-license.sh`; CLI de host `kontrol.py` | 001 · 052 | Sí | **Sí**: el planificador usa el mismo camino | — | Bajo |
| Adaptador de correo | ninguno | 048 | No | — | En la 048 | — |
| WebSocket / SSE | ninguno | — | No | — | No | — |
| Sondeo | TanStack Query | 001 | Librería | Sí | — | — |
| Campana | `Topbar.tsx` sin campana | 047 | No | El `Topbar` | Sí | — |
| Avisos de interfaz | `NotificationContext` (FR-001-063) | 001 | Sí | Para respuestas a acciones | — | Medio |
| Plantillas de mensaje | ninguna | 047 | No | — | Catálogo | Bajo |
| Permisos | `setup/api.py`, recurso en español y acción en inglés | 003 | Sí | Convención | Recursos de la 047 | Medio |
| Auditoría | `record_audit` | 006 | Sí | Sí | — | Bajo |
| Actor de sistema | ninguno; `record_audit` acepta `user_id=None` y `source` libre | 006 | Parcial | Sí | `actor_type` en la 047 | — |
| Reloj inyectable | `mark_expired(now=…)` en la 045; sin librería de congelación | — | Parcial | Parámetro `now` | — | — |
| Internacionalización | ninguna | **047** por decisión del owner | No | — | Base + catálogo `es` | Conflicto de dueño → cerrado |
| Zona horaria | columnas con zona | 001 | Sí | Sí | — | — |
| Paginación | `page`/`page_size` en `audit/api.py`; `Pagination.tsx` | 001 | Sí | Sí | — | — |
| Carreras | `es_violacion_unica`, `tests/concurrency.py` | P25 | Sí | Sí | — | — |
| Acceso a empresas | `company_context.accessible_company_ids`, `company_context_for` | ARCH-MC-001 | Sí | Sí | — | — |

## 2. Decisiones con autoridad

| ID | Pregunta | Decisión | Autoridad |
|---|---|---|---|
| CL-047-01 | ¿Dónde vive la Spec? | `specs/047-notificaciones-tareas/` | Precedente 045/046 |
| CL-047-02 | ¿Tareas para aprobaciones? | **Enmendada 2026-09-14.** Una regla puede crear la tarea «atender aprobación» a partir de `approval.step_opened`, con los elegibles que la 045 fijó como candidatos y enlace a la bandeja. **Completarla no decide nada**; se cierra como `RESOLVED_BY_SOURCE` cuando la 045 resuelve. No calcula elegibles ni delegación | §60 y §95 del prompt; R-047-01; R-047-11 |
| CL-047-03 | ¿Destinatario fijado o dinámico? | Fijado al crear; reasignación explícita; visibilidad revalidada en cada lectura | `eligible_actors` de la 045; R-D0-02-3 |
| CL-047-04 | ¿Reloj y zona? | Instantes con zona entregados por la dueña; recordatorios y escaladas en minutos; ninguna fecha de calendario | `ApprovalStep.due_at` |
| CL-047-05 | ¿Permisos? | `notificaciones:configure` (reglas) · `tareas:view` (todas las de la empresa), `tareas:assign`, `tareas:complete`, `tareas:configure` (prioridades) · `alertas:view`. Lo propio no pide permiso de recurso | Convención de `setup/api.py`; precedente de migración 0024 |
| CL-047-06 | ¿Paginación? | `page`, `page_size` ≤ 100 | `audit/api.py` |
| CL-047-07 | ¿Sobre de evento? | `approval_events` es la fuente V1. La auditoría no se consume: sus acciones no son contrato y no tiene índice para sondearse (RK-047-05) | CVG-045-05 |
| CL-047-08 | ¿Canales externos? | Frontera con registro de proveedores vacío en producción | 048 sin adaptador |
| CL-047-09 | ¿Eventos de la 046? | Cuando la 046 los emita | `OWNER_DEPENDENCY` |
| CL-047-10 | ¿Integración con 037 y 038? | No publican hechos: la 038 no pasa por la 045 y ambas solo auditan. Queda disponible `publish`; integrarlas es un delta de su dueña, no necesario para demostrar la 047 | §94 «if applicable»; §15 |
| CL-047-11 | ¿Tiempo real? | Sondeo | §50 |
| CL-047-12 | ¿Los avisos de interfaz son notificaciones? | No | FR-001-063 |
| CL-047-13 | ¿Camino de ejecución del planificador? | El de los scripts: `docker compose exec -T backend python -m app.modules.scheduler tick`, envuelto en `kontrol.py scheduler-tick` | `scripts/diagnose.sh`; ADR-D0-015 |
| CL-047-14 | ¿Se habilita el vencimiento de la 045? | **No.** Un paso `EXPIRED` sale de la bandeja (`inbox` solo lista `IN_REVIEW`) y ninguna función lo reabre, aunque la máquina de estados lo permita. Se registra deshabilitado y se prueba el contrato | `approvals/service.py` · `state-machines.md` |
| CL-047-15 | ¿Clave de mensaje o texto? | Solo clave y parámetros; ninguna columna de texto | OQ-047-02 |
| CL-047-16 | ¿Versionado del catálogo? | Clave estable. Ningún mensaje de la 047 tiene valor legal; si lo tuviera, lo decidiría su dueña | §22 |
| CL-047-17 | ¿Hechos anteriores a una regla? | Un hecho se consume una vez; sin regla activa queda con resultado `NO_RULE` y no se reprocesa al crear reglas después | Idempotencia; evita tormentas retroactivas |

## 3. Contradicciones

| ID | Contradicción | Estado |
|---|---|---|
| C-047-01 | ADR-D0-003 da el planificador a la 047; ADR-009 lo impedía sin ADR | **RESUELTA** por ADR-D0-015 |
| C-047-02 | FR-047-034 exigía ES/EN sin sistema ni dueña; R-D0-10-2 lo reserva a un cambio propio | **RESUELTA** por decisión del owner: la base de localización es de la 047 y en V1 solo existe el catálogo `es`. Migrar los textos de otros módulos no se absorbe |

## 4. Preguntas materiales

### OQ-047-01 · Planificador de plataforma — `CLOSED_BY_OWNER_DECISION`

| Campo | Contenido |
|---|---|
| Autoridad previa | ADR-D0-003 §G; ADR-009 |
| Opciones | A temporizador del sistema → orden idempotente · B proyección en lectura · C llamada síncrona · D bucle en proceso |
| Decisión | **A** |
| Razón | Única que da ejecutor a 047, 045, 030, 048 y 052 sin cola |
| Consecuencias | ADR-D0-015; tablas de ejecución; bloqueo consultivo; plantillas de despliegue; filas materializadas de notificación, tarea y alerta |
| Diferido | Manejadores de 030, 048 y 052; habilitar el de la 045 |
| Afecta | FR-047-001, 005, 010, 015, 017, 023-025, 027, 037-049, 054 · tareas T047-010..015, 031, 032, 045, 046 · M047-13..17 |

### OQ-047-02 · Localización — `CLOSED_BY_OWNER_DECISION`

| Campo | Contenido |
|---|---|
| Autoridad previa | FR-047-034; R-D0-10-2 |
| Opciones | A i18n antes como cambio propio · B base en la 047 con ES/EN · C contrato neutro con `es` |
| Decisión | Arquitectura i18n **sí**, catálogo `es` **sí**, catálogo `en` **DEFERRED**; persistir `message_key` + parámetros |
| Razón | Lo irreversible —qué se guarda— queda bien hecho; añadir inglés no toca filas ni contratos |
| Consecuencias | Renderizador y catálogo en backend; catálogo de interfaz en frontend; cero cadenas visibles nuevas fuera de catálogo |
| Diferido | Catálogo `en`; idioma del usuario (003); textos de otros módulos |
| Afecta | FR-047-033, 034, 050-053 · tareas T047-020, 021, 080, 087 · M047-18, M047-19 |

**MATERIAL OQ = 0.**

## 5. Dependencias de dueña — no bloquean la 047

| Dependencia | Dueña | Efecto |
|---|---|---|
| Adaptador de correo, push o SMS | 048 | Frontera sin proveedor |
| Emisión de `document.*` | 046 | Sin hechos documentales |
| Camino tras `EXPIRED` | 045 | Manejador deshabilitado |
| Hechos de CxC y tesorería | 037 · 038 | Sin publicación |
| Idioma del usuario | 003 | Solo cuando exista `en` |
| Caducidad de reservas, retención | 030 · 052 | Manejadores no registrados |
