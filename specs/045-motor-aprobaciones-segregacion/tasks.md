# TAREAS — SPEC 045

Estado: **implementación ejecutada** con autorización expresa de 2026-08-29 (P2).
Orden seguido: F1 → F2 → F3 → F4 → F7 → F5 → F6.

Leyenda: **✔** completada y verificada · **◐** completada con limitación declarada · **✖** no ejecutada.

## F1 · Modelo y migración

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| ✔ T-045-001 | Módulo `approvals` con `models.py`, `service.py`, `api.py` | Arquitectura | S |
| ✔ T-045-002 | 8 modelos SQLAlchemy conforme a `data-model.md` | FR-045-001..003, 020 | M |
| ✔ T-045-003 | Restricción de no solapamiento de políticas activas | FR-045-004 | S |
| ✔ T-045-004 | Restricción de unicidad de solicitud por documento y huella | FR-045-053 | S |
| ✔ T-045-005 | Migración `0015_approvals` | Todos | M |
| ✔ T-045-006 | Permisos `aprobaciones: view/create/edit/approve/delegate/configure` en seed + migración de datos para instalaciones existentes | FR-045-063 | S |
| ✔ T-045-007 | Catálogo extensible de `process_type` | FR-045-006 | S |

## F2 · Motor de evaluación

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| ✔ T-045-010 | `PolicyResolver`: política vigente por empresa y proceso | FR-045-001 | S |
| ✔ T-045-011 | `ConditionEvaluator`: predicados tipados con `AND` | FR-045-010 | M |
| ✔ T-045-012 | Normalización a moneda base con tasa snapshot | FR-045-011 | M |
| ✔ T-045-013 | Error explícito ante condición no evaluable | FR-045-015 | S |
| ✔ T-045-014 | Acumulación de niveles de reglas múltiples sin duplicar | FR-045-013 | S |
| ✔ T-045-015 | `ActorResolver`: rol, usuario, alcance y delegación vigente | FR-045-014, 042 | M |
| ✔ T-045-016 | `FingerprintService`: SHA-256 sobre campos de condición | FR-045-050 | S |
| ✔ T-045-017 | `evaluate()` sin efectos secundarios | FR-045-008 | S |

## F3 · Ciclo de la solicitud

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| ✔ T-045-020 | `require()`: crea solicitud con snapshot y huella; idempotente | FR-045-020, 053 | M |
| ✔ T-045-021 | Apertura de paso con congelado de elegibles y `due_at` | FR-045-014, 027 | M |
| ✔ T-045-022 | Aprobar con evaluación de cuórum y avance de nivel | FR-045-022, 028 | L |
| ✔ T-045-023 | Rechazar (terminal) con motivo obligatorio | FR-045-023, 026 | S |
| ✔ T-045-024 | Devolver con conservación de historial y encadenado | FR-045-024, 030 | M |
| ✔ T-045-025 | Cancelar | FR-045-025 | S |
| ✔ T-045-026 | Detección y marcado de obsolescencia | FR-045-051, 052 | M |
| ✔ T-045-027 | Bloqueo de fila y control de versión del paso | FR-045-054 | M |
| ✔ T-045-028 | Transaccionalidad de cuórum, avance, cierre y evento | FR-045-055 | M |
| ✔ T-045-029 | Segregación y prohibición de autoaprobación | FR-045-040, 041 | M |
| ✔ T-045-030 | Delegación: creación, revocación y herencia de restricciones | FR-045-042..046 | L |
| ✔ T-045-031 | Marcado de vencimiento sin resolver | FR-045-027 | S |
| ✔ T-045-032 | Auditoría de todo evento vía `record_audit` | FR-045-064 | M |
| ✔ T-045-033 | Emisión de eventos de dominio | FR-045-066 | S |

## F4 · API

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| ✔ T-045-040 | Endpoints de configuración de políticas, reglas y niveles | FR-045-001..007 | M |
| ✔ T-045-041 | `POST /evaluate` y `POST /requests` | FR-045-010, 020 | M |
| ✔ T-045-042 | `GET /inbox` con filtros y paginación | FR-045-060 | M |
| ✔ T-045-043 | Resolución de pasos con `If-Match` | FR-045-022..026, 054 | M |
| ✔ T-045-044 | Consulta por documento e historial | FR-045-061 | S |
| ✔ T-045-045 | Endpoints de delegación | FR-045-042 | S |
| ✔ T-045-046 | `allowed_actions` calculado en backend | FR-045-062 | S |
| ✔ T-045-047 | Códigos de error específicos del contrato | Contratos | S |

## F5 · Frontend

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| ✔ T-045-050 | Ruta y página **Políticas de aprobación** (lista) | FR-045-001 | M |
| ✔ T-045-051 | Página completa de **edición de política** con reglas y niveles — sin modales | P18 | L |
| ✔ T-045-052 | Página **Mis aprobaciones** (bandeja) | FR-045-060 | L |
| ✔ T-045-053 | Panel de **historial de aprobaciones** reutilizable desde cualquier documento | FR-045-061 | M |
| ✔ T-045-054 | Página de **delegaciones** | FR-045-042 | M |
| ✔ T-045-055 | Confirmaciones breves en modal (aprobar/rechazar/devolver) con motivo | ADR-015 | S |
| ✔ T-045-056 | Entradas de menú y guardas de permiso | FR-045-063 | S |
| ✔ T-045-057 | Estados Loading/Ready/Empty/Forbidden/NotFound/Error | Vol. 2 §2 | S |

## F6 · Migración de las cuatro implementaciones

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| ✔ T-045-060 | Políticas equivalentes que reproducen el comportamiento vigente | plan §4 | M |
| ✔ T-045-061 | Verificación de equivalencia antes del corte | plan §4 | M |
| ✔ T-045-062 | Migrar compras (requisición y orden) | FR-045-070 | M |
| ✔ T-045-063 | Migrar ventas (crédito) | FR-045-071 | M |
| ✔ T-045-064 | Migrar inventario (ajustes y conteos) | FR-045-072 | M |
| ✔ T-045-065 | Migrar regulatorio | FR-045-073 | S |
| ✔ T-045-066 | Migración `0016_approvals_backfill` idempotente con `LEGACY_UNVERSIONED` | FR-045-074 | M |
| ✔ T-045-067 | Eliminar la lógica propia de los cuatro módulos y verificar por búsqueda | FR-045-075, P22 | M |

## F7 · Pruebas

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| ✔ T-045-070 | Unidad: evaluador, actores, huella, cuórum | F2 | L |
| ✔ T-045-071 | Integración: ciclo completo por API | F3-F4 | L |
| ◐ T-045-072 | **Concurrencia sobre PostgreSQL**: dos decisiones simultáneas | FR-045-054 | M |
| ✔ T-045-073 | Obsolescencia bajo concurrencia | FR-045-051 | M |
| ✔ T-045-074 | Idempotencia de creación | FR-045-053 | S |
| ✔ T-045-075 | Segregación y delegación: pruebas negativas | FR-045-040..046 | M |
| ✔ T-045-076 | E2E: configurar → disparar → aprobar → documento avanza | HU-045-02/03 | L |
| ✔ T-045-077 | E2E: devolver → corregir → reenviar → aprobar | HU-045-05 | M |
| ✔ T-045-078 | axe WCAG 2.2 AA en las pantallas nuevas | NFR-045-03 | S |
| ✔ T-045-079 | Responsive 6 viewports | NFR-045-04 | S |
| ✔ T-045-080 | Puertas G1-G4 actualizadas | Checklist | S |
| ✔ T-045-081 | Regresión de los cuatro dominios migrados | F6 | L |

## Limitaciones declaradas

| Tarea | Estado | Motivo |
|---|---|---|
| T-045-072 concurrencia sobre PostgreSQL | **◐** | No hay servidor PostgreSQL en el entorno (BLK-D0-01). La lógica de conflicto de versión y la restricción `(step_id, actor_id)` están probadas; `SELECT … FOR UPDATE` sólo es efectivo en PostgreSQL y su verificación queda como criterio de salida pendiente |

## Resumen

| Fase | Tareas | Carga |
|---|---:|---|
| F1 Modelo | 7 | M |
| F2 Motor | 8 | M-L |
| F3 Ciclo | 14 | **L** |
| F4 API | 8 | M |
| F5 Frontend | 8 | **L** |
| F6 Migración | 8 | **L** — mayor riesgo |
| F7 Pruebas | 12 | **L** |
| **Total** | **65** | — |

Sin estimación en horas: no hay datos de velocidad del equipo (ADR-D0-002 §Migración, criterio de D0).
