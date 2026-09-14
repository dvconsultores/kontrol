# `/speckit.plan` — SPEC 047 · NOTIFICACIONES, TAREAS Y ALERTAS

> Plan redactado **sin autorización de implementación**: dos preguntas materiales
> abiertas (`clarifications.md` §4). Separa lo que ya está decidido de lo que
> cambia según la respuesta.

## 1. Lo que no depende de las preguntas

| Elemento | Decisión | Base |
|---|---|---|
| Dueña única | Un módulo backend `app/modules/notifications` para notificaciones, tareas y alertas; guardas de arquitectura con `tests/spec_blocks.py · bloque_de_spec` | P22 · §104 |
| Alcance | `CompanyContext` con `X-Kontrol-Company`; `__scope__ = Scope.COMPANY`; `company_id` del cuerpo ignorado | FR-047-012/013 |
| Estado por destinatario | Fila única `(ítem, usuario)` con `read_at` y `archived_at` con zona | FR-047-003 · R-047-02 |
| Destinatarios | Resueltos en el servidor desde asignación de la dueña, rol, permiso o configuración; fijados al crear; visibilidad revalidada en cada lectura | CL-047-03 |
| Asignación | Historial append-only; reasignación con `version` y 409 en conflicto, como `step_version` de la 045 | FR-047-006 · §66-67 |
| Completar | Cambia solo la tarea. Cierre por la dueña solo ante `approval.resolved` u `approval.obsolete` si la regla lo autoriza | R-047-01 · §18 |
| Enlace | `source_type`, `source_id` y clave de ruta; carga mínima; el detalle del origen exige permiso del recurso origen | FR-047-011/031/032 |
| Identificador ajeno | 404 idéntico al de uno inexistente | R-047-06 |
| Listas | `page`, `page_size` ≤ 100, `{items,total,page,page_size}`; filtros solo sobre campos reales | CL-047-06 |
| Contadores | Un agregado SQL por tipo; nunca contar en el cliente | FR-047-030/036 |
| Auditoría | `record_audit` para cada transición | FR-047-017 |
| Carreras | Restricción única + `es_violacion_unica` + conflicto de dominio; pruebas con `tests/concurrency.py · carrera` | P25 |
| Entrega externa | Estado de entrega separado del ítem; sin adaptador hasta la 048 | CL-047-08 |
| Frontend | Campana en `layout/Topbar.tsx` con sondeo; páginas enrutadas para centro, tareas, detalle y alertas; componentes de estado y `Pagination.tsx` existentes | §43-51 |
| Esquema | Una migración aditiva sobre la cabeza `0056_spec013_masters`, ida, vuelta y nueva ida; guardas de paridad | P26 · §59-60 |

## 2. Lo que cambia con la respuesta

### OQ-047-01

| Elemento | Con A · planificador | Con B · proyección en lectura |
|---|---|---|
| Filas de notificación, tarea y alerta | Materializadas al procesar el hecho | Solo filas de estado cuando el usuario actúa |
| Clave de idempotencia | Única `(regla, hecho de origen)` en la fila materializada | Identidad derivada del hecho; la fila de estado es única por `(ítem derivado, usuario)` |
| Auditoría de «creado» y «escalado» | Hechos propios con momento de proceso | Derivados; se audita la primera acción |
| Recordatorios y escaladas | Trabajos programados | Predicados de tiempo en consulta |
| `outbox_events` | Posible publicador | Sin uso |
| Canal externo | Posible cuando exista la 048 | Imposible |
| Despliegue | Temporizador del sistema y ADR nuevo | Sin cambios |

### OQ-047-02

| Elemento | A · i18n antes | B · base en la 047 | C · contrato neutro |
|---|---|---|---|
| Qué se guarda | Clave y parámetros | Clave y parámetros | Clave y parámetros |
| Catálogos | ES y EN | ES y EN | ES; EN después |
| Idioma del usuario | Campo en la 003 | Campo en la 003 | Ninguno en v1 |
| Prerrequisito | Cambio de i18n cerrado | Ninguno | Ninguno |

## 3. Olas

| Ola | Contenido | Estado |
|---|---|---|
| W01 | Inventario del repositorio | **HECHA** — `clarifications.md` §1 |
| W02 | Mapa de artefactos y dueñas | **HECHA** — `clarifications.md` §1-2 |
| W03 | Contrato de eventos | Parcial: fuentes identificadas (CL-047-07); modo de consumo **OQ-047-01** |
| W04 | Núcleo de notificación | **OQ-047-01** |
| W05 | Estado por destinatario | Diseñado; su clave depende de W04 |
| W06 | Núcleo de tareas | **OQ-047-01** |
| W07 | Asignación e historial | Diseñado; clave de W06 |
| W08 | Alertas | **OQ-047-01** |
| W09 | Idempotencia | **OQ-047-01** |
| W10 | Seguridad multiempresa | Diseñado |
| W11 | Permisos | Diseñado — CL-047-05 |
| W12 | Vencimientos y zona | Diseñado — CL-047-04 |
| W13 | Preferencias | Diseñado, mínimo |
| W14 | Frontera de entrega externa | Diseñado; adaptador **048** |
| W15 | Planificador y recordatorios, si se autoriza | **OQ-047-01** |
| W16 | Escalado, si se autoriza | **OQ-047-01** |
| W17 | API y OpenAPI | Tras W04-W09 |
| W18 | Centro de notificaciones | **OQ-047-02** |
| W19 | Tareas en el frontend | **OQ-047-02** |
| W20 | Alertas en el frontend | **OQ-047-02** |
| W21 | Campana y contadores | **OQ-047-02** |
| W22 | Paginación | Diseñado — CL-047-06 |
| W23 | Auditoría y observabilidad | Diseñado; momentos según OQ-047-01 |
| W24 | Pruebas hostiles | Definidas (`tasks.md` T047-110) |
| W25 | Concurrencia real | Definidas (T047-111) |
| W26 | Mutaciones M047-01..12 | Definidas (T047-112) |
| W27 | Migraciones | Tras W04-W09 |
| W28 | Instalación limpia | Tras W27 |
| W29 | Regresiones cruzadas 037, 038, 045 | Tras implementación; la 048 no aplica, sin proveedor |
| W30 | E2E en tres navegadores | Tras implementación |
| W31 | Regresión completa | Tras implementación |
| W32 | `/speckit.analyze` final | Tras implementación |
| W33 | Trazabilidad final | Tras implementación |
| W34 | Convergencia | Tras implementación |
| W35 | Máster 56 | **HECHA** — estado de bloqueo |
| W36 | Revalidar solo la 049 | **HECHA** — `spec049-readiness-revalidation.md` §9 |

## 4. CONSTITUTION GATE

| Puerta | Resultado | Evidencia |
|---|---|---|
| G047-01 Se usa la Spec 047 existente | **PASS** | CL-047-01 |
| G047-02 Sin Spec paralela | **PASS** | Una carpeta; ninguna variante |
| G047-03 Sin motor de aprobación duplicado | **PASS** | CL-047-02 · R-047-11 |
| G047-04 Sin motor de integración duplicado | **PASS** | CL-047-08 |
| G047-05 Sin planificador duplicado | **CONDICIONADA** | No se crea ninguno; la capacidad que `ADR-D0-003` asigna a la 047 queda sin mecanismo — OQ-047-01 |
| G047-06 Sin robar reglas de negocio | **PASS** | §5 de `spec.md` · FR-047-026 |
| G047-07 Autoridad del contexto de petición | **PASS** | §1 |
| G047-08 Lectura por destinatario | **PASS** | §1 |
| G047-09 Idempotencia de hechos | **CONDICIONADA** | La clave depende de OQ-047-01 |
| G047-10 Completar ≠ ejecutar el dominio | **PASS** | R-047-01 |
| G047-11 Fallo externo no destruye la interna | **PASS** | R-047-05 |
| G047-12 Historial conservado | **PASS** | R-047-03/04 |
| G047-13 Sin cruce de empresa | **PASS** | §1 |
| G047-14 Sin cruce de tenant | **PASS** | §1 |
| G047-15 IDOR | **PASS** | R-047-06/07 |
| G047-16 Permisos canónicos | **PASS** | CL-047-05 |
| G047-17 Instantes con zona | **PASS** | CL-047-04 |
| G047-18 Paridad ORM ↔ Alembic | **PREVISTA** | Se demuestra con el esquema (T047-090) |
| G047-19 Sin 500 en carreras | **PREVISTA** | Se demuestra con carreras forzadas (T047-111) |
| G047-20 El dashboard solo consume | **PASS** | FR-047-036 |

**16 PASS · 2 CONDICIONADAS · 2 PREVISTAS.** La puerta **no** autoriza
implementación: las dos condicionadas dependen de una pregunta material.

Principios transversales: P21 PostgreSQL — `ENVIRONMENT_BASELINE_DEVIATION`
declarada (16.2); P22 capacidad única — cumplida en diseño, con el hueco de dueña
del i18n registrado; P24-P27 — previstos en T047-090, T047-091, T047-111 y
T047-112.

## 5. Riesgos

| ID | Riesgo | Mitigación |
|---|---|---|
| RK-047-01 | Construir una segunda bandeja de aprobaciones | CL-047-02, R-047-11, guarda de arquitectura |
| RK-047-02 | Materializar tareas en consultas GET y escribir en modo `READ_ONLY` | Descartado en ambas opciones: B solo escribe por acción del usuario |
| RK-047-03 | Contadores lentos por recalcular destinatarios | Agregado SQL con índice; prueba de volumen > 100 |
| RK-047-04 | Tomar los avisos de interfaz por notificaciones | CL-047-12 |
| RK-047-05 | Depender de nombres de acción de auditoría como contrato | Tabla explícita de acciones consumidas, con prueba que falle si la dueña renombra |
