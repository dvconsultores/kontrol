# `/speckit.analyze` — SPEC 047 · NOTIFICACIONES, TAREAS Y ALERTAS

## A. Primer análisis — 2026-09-14 sobre `88634a1`

Veredicto: `BLOCKED BY MATERIAL DECISION` (OQ-047-01 planificador, OQ-047-02
idioma). BLOCKER 2 · CONTRADICTIONS 2 · MATERIAL OQ 2. Commit `1c04241`.

## B. Re-análisis previo a implementación — 2026-09-14 sobre `370e10a`

### 1. Qué cambió

Las dos preguntas se cerraron por decisión expresa del owner. Se creó
`ADR-D0-015` y se actualizaron `spec.md` (36 → **54** requisitos),
`clarifications.md`, `plan.md`, `checklist.md`, `tasks.md` (49 → **58**
tareas) y `traceability-matrix.md`; se añadieron `research.md`,
`data-model.md` y `contracts/api-contracts.md`.

### 2. Detección exigida por el §32

| Detección | Resultado |
|---|---|
| Nueva Material OQ | **0** |
| Conflicto de ADR | ADR-D0-015 acota ADR-009 con una sola excepción y materializa ADR-D0-003 §G. ADR-009 no se edita |
| Colisión de dueñas | Marco del planificador: 047. Reglas de expiración, retención y correo: sus dueñas (FR-047-049) |
| Planificador duplicado | No existe otro |
| Outbox duplicado | No se crea; `outbox_events` no se usa en V1 (FR-047-054) |
| Cola introducida | No (FR-047-039) |
| Worker introducido | No (FR-047-039) |
| Reglas de negocio duplicadas | No: la 047 no calcula elegibles, delegaciones ni vencimientos de la 045 |
| Conflicto de dueña del i18n | Cerrado: la base es de la 047; los textos de otros módulos no se absorben |
| Ambigüedad del esquema de localización | Cerrada: `message_key` String(128) + `message_params` JSON; sin columna de texto ni de idioma |
| Semántica de destinatarios | CL-047-03 |
| Zona horaria | CL-047-04 |
| Permisos | CL-047-05 |
| Despliegue del planificador | CL-047-13 · ADR-D0-015 §Implementación |
| Tareas y huérfanos | 58 tareas, 0 sin requisito, 0 requisitos sin tarea — verificado por script |
| Huecos de prueba | 0: 54/54 requisitos con prueba prevista |
| Huecos de mutación | 0: M047-01..19 asignadas |
| Integraciones inventadas | Ninguna: 037 y 038 no publican hechos (CL-047-10) |
| Habilitar un comportamiento dañino de otra dueña | Evitado: vencimiento de la 045 deshabilitado (CL-047-14) |

### 3. Contradicciones

| ID | Estado |
|---|---|
| C-047-01 | **RESUELTA** — ADR-D0-015 |
| C-047-02 | **RESUELTA** — decisión del owner, OQ-047-02 |

### 4. Hallazgos ajenos — registrados, no corregidos

| Hallazgo | Dueña | Clasificación |
|---|---|---|
| `GET /approvals/inbox` pagina con `limit` y `offset` | 045 | `PREEXISTING` |
| La bandeja carga los pasos `IN_REVIEW` de todas las empresas y filtra en Python | 045 | `PREEXISTING` |
| Un paso `EXPIRED` no vuelve a `IN_REVIEW` por ninguna función | 045 | `OWNER_DEPENDENCY` para habilitar su manejador |

### 5. Recuento

| Puerta | Valor | Exigido |
|---|---:|---:|
| BLOCKER | **0** | 0 |
| CRITICAL | **0** | 0 |
| CONTRADICTIONS | **0** | 0 |
| ORPHAN REQUIREMENTS | **0** | 0 |
| ORPHAN TASKS | **0** | 0 |
| MATERIAL OQ | **0** | 0 |
| UNKNOWN | **0** | 0 |
| TRACEABILITY | **100 %** en diseño (54/54) | 100 % |
| CONSTITUTION GATE | 26 PASS en diseño · 0 condicionadas | — |

### 6. Veredicto

**`SPEC047 — READY FOR IMPLEMENTATION`.** Se consume la autorización expresa del
§33 del prompt y se ejecuta `/speckit.implement`.

## C. Análisis final — tras implementación y pruebas

| Puerta | Valor |
|---|---:|
| BLOCKER | **0** |
| CRITICAL | **0** |
| CONTRADICTIONS | **0** |
| ORPHAN REQUIREMENTS | **0** — 54/54 con código y prueba |
| ORPHAN TASKS | **0** — 58 tareas |
| MATERIAL OQ | **0** |
| UNKNOWN | **0** |
| TRACEABILITY | **100 %** — `traceability-matrix.md` |

Detecciones del §92 revisadas contra el código implementado: sin motor duplicado de
notificaciones, tareas, aprobación, planificador ni proveedor; completar una tarea no
toca el origen (M047-05); idempotencia con restricción única y captura estrecha
(M047-01, 08b, 12); lectura por destinatario (M047-04); ninguna fuga de empresa,
tenant ni origen (M047-02, 03, 07, 11, 17); relojes con zona (M047-10); historial
sin borrado (M047-09); fallo externo sin pérdida (M047-06); paginación real con página
3 comprobada; OpenAPI y contrato de empresa verdes (`test_n8_contract.py`); paridad
ORM ↔ Alembic a 0; guardas por marcador semántico, no por posición.

Durante la validación aparecieron dos regresiones propias —la campana tras la purga
del shell y la siembra de D2 en la cadena compartida— y se corrigieron con prueba que
las reproduce (`convergence.md` §5). La deuda ajena queda con su dueña
(`convergence.md` §6).

**Veredicto: `SPEC047 — COMPLETE / CONVERGED`.**
