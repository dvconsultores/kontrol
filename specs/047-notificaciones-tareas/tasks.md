# `/speckit.tasks` — SPEC 047

> Tareas atómicas. Ninguna se ejecuta en este ciclo salvo las marcadas **HECHA**.
> Ficheros previstos, no creados.

| ID | Requisito | Dueña | Ficheros | Depende de | Aceptación | Pruebas | Evidencia | Estado |
|---|---|---|---|---|---|---|---|---|
| T047-001 | Todos | 047 | `specs/047-notificaciones-tareas/*` | — | Artefactos del ciclo | — | este commit | **HECHA** |
| T047-002 | FR-047-001, 005, 010, 015, 017, 023-025 | Arquitectura · Producto | ADR nuevo | — | OQ-047-01 respondida | — | ADR firmado | **BLOQUEANTE** |
| T047-003 | FR-047-033, 034 | Producto | enmienda a `spec.md` o cambio de i18n | — | OQ-047-02 respondida | — | decisión registrada | **BLOQUEANTE** |
| T047-010 | FR-047-001, 004, 011, 012, 013 | 047 | `app/modules/notifications/models.py` | T047-002 | Notificación con alcance y enlace mínimo | `test_spec047_notifications.py` | pytest | BLOQUEADA OQ-047-01 |
| T047-011 | FR-047-002 | 047 | `notifications/recipients.py` | T047-010 | Destinatarios del servidor, fijados al crear | ídem · hostil de ids del cliente | pytest | BLOQUEADA OQ-047-01 |
| T047-012 | FR-047-003 | 047 | `notifications/service.py`, `api.py` | T047-010 | Leer y archivar por destinatario; devuelve el estado resultante | flujo B · M047-04 | pytest | BLOQUEADA OQ-047-01 |
| T047-013 | FR-047-004, 018 | 047 | `service.py` | T047-012 | Obligatoria no se desactiva ni caduca | dirigida | pytest | BLOQUEADA OQ-047-01 |
| T047-020 | FR-047-005, 006, 007, 008, 009 | 047 | `models.py` | T047-002 | Tarea con asignatario, estado, prioridad configurable y vencimiento | flujo C | pytest | BLOQUEADA OQ-047-01 |
| T047-021 | FR-047-007 · R-047-01 | 047 | `service.py` | T047-020 | Completar no altera el origen | flujo D · M047-05 | pytest | BLOQUEADA OQ-047-01 |
| T047-022 | §18 | 047 | `sources.py` | T047-020 | Cierre ante `approval.resolved` u `obsolete` solo con regla | dirigida | pytest | BLOQUEADA OQ-047-01 |
| T047-023 | FR-047-006 · R-047-04 | 047 | `service.py` | T047-020 | Reasignación con versión y 409; historial intacto | carrera · M047-09 | pytest | BLOQUEADA OQ-047-01 |
| T047-030 | FR-047-010 | 047 | `models.py`, `sources.py` | T047-002 | Alerta sin tarea salvo regla | flujo E | pytest | BLOQUEADA OQ-047-01 |
| T047-040 | FR-047-016, 026 | 047 | `sources.py` | T047-002 | Consume `approval_events` y acciones de auditoría listadas, sin recalcular condiciones | flujos A y K · integración 045 | pytest | BLOQUEADA OQ-047-01 |
| T047-041 | FR-047-015 | 047 | `models.py`, `service.py` | T047-040 | Diez reintentos concurrentes, un ítem, 0 duplicados, 0 errores 500 | flujo F · M047-01 · M047-08 | pytest | BLOQUEADA OQ-047-01 |
| T047-042 | FR-047-027 | 047 | `service.py` | T047-041 | Hecho masivo sin explosión | volumen | pytest | BLOQUEADA OQ-047-01 |
| T047-050 | FR-047-008 · NFR-047-01 | 047 | `service.py` | T047-020 | Vencido según `now(UTC)` | flujo I · M047-10 | pytest | BLOQUEADA OQ-047-01 |
| T047-051 | FR-047-024 | 047 | según ADR | T047-002, T047-050 | Recordatorio configurable | dirigida | pytest | BLOQUEADA OQ-047-01 |
| T047-052 | FR-047-025 | 047 | según ADR | T047-050 | Escalado exacto configurado; nada fijo en código | flujo I | pytest | BLOQUEADA OQ-047-01 |
| T047-053 | FR-047-023 | 047 | según ADR | T047-002 | Un solo planificador, sin bucles locales | guarda de arquitectura | pytest | BLOQUEADA OQ-047-01 |
| T047-060 | FR-047-019, 020, 021, 022 | 047 · 048 | `models.py` | T047-010 | Estado de entrega separado; el fallo no borra | flujo G con proveedor simulado en la frontera · M047-06 | pytest | Frontera tras OQ-047-01; adaptador **048** |
| T047-061 | FR-047-018, 019 | 047 | `service.py`, `api.py` | T047-013 | Preferencias solo de lo opcional | dirigida | pytest | BLOQUEADA OQ-047-01 |
| T047-070 | FR-047-033 | 047 | `templates.py` | T047-003 | Versión, variables explícitas, error controlado | dirigida | pytest | BLOQUEADA OQ-047-02 |
| T047-071 | FR-047-034 | 047 · dueña del i18n | catálogos | T047-003 | Sin cadenas fuera del sistema de mensajes | vitest | vitest | BLOQUEADA OQ-047-02 |
| T047-080 | FR-047-028, 029 | 047 | `api.py` | T047-041 | Página 3 correcta con > 100; sin `limit` | volumen | pytest | Tras OQ-047-01 |
| T047-081 | FR-047-030, 036 | 047 | `api.py` | T047-041 | Agregados por empresa, tenant y permisos | flujo H · flujo K | pytest | Tras OQ-047-01 |
| T047-082 | FR-047-031, 032 | 047 | `api.py` | T047-010 | Sin permiso: prohibido y sin datos del origen | flujo J · M047-07 | pytest | Tras OQ-047-01 |
| T047-083 | §40 | 047 | `tests/test_spec047_openapi.py` | T047-080 | Rutas, esquemas, errores y filtros coinciden | contrato | pytest | Tras OQ-047-01 |
| T047-084 | FR-047-014 | 047 · 003 | `setup/api.py` | T047-080 | Recursos según CL-047-05 | hostil de permisos | pytest | Tras OQ-047-01 |
| T047-085 | FR-047-017 | 047 · 006 | `service.py` | T047-012, T047-023 | Cada transición auditada | reconstrucción §84 | pytest | Tras OQ-047-01 |
| T047-086 | NFR-047-03 | 047 · 006 | `service.py` | T047-041 | Métricas y registros sin carga sensible | dirigida | pytest | Tras OQ-047-01 |
| T047-087 | FR-047-035 | 047 | `service.py` | T047-012 | Sin borrado físico | guarda | pytest | Tras OQ-047-01 |
| T047-090 | NFR-047-07 · §56-60 | 047 | `alembic/versions/0057_spec047_*.py` | T047-041 | Aditiva, ida, vuelta y nueva ida; paridad | guarda de paridad | pytest · alembic | Tras OQ-047-01 |
| T047-091 | P24 | 047 | `qa/` | T047-090 | Instalación desde cero a cabeza, siembra mínima, dirigidas y E2E | cadena limpia | registro | Tras OQ-047-01 |
| T047-100 | FR-047-030 · §49 | 047 | `src/layout/Topbar.tsx`, `NotificationBell.tsx` | T047-081, T047-003 | Contador del servidor; se actualiza sin recargar | vitest · E2E · M047-11 | vitest · playwright | BLOQUEADA OQ-047-02 |
| T047-101 | FR-047-001, 003, 011, 028, 029, 031 | 047 | `src/modules/notificaciones/centro/` | T047-080 | Página enrutada con los cinco estados | vitest · E2E | playwright | BLOQUEADA OQ-047-02 |
| T047-102 | FR-047-005..009, 029 | 047 | `src/modules/notificaciones/tareas/` | T047-080 | Filtros de §45 | E2E página 3 | playwright | BLOQUEADA OQ-047-02 |
| T047-103 | §46 | 047 | `tareas/TareaDetallePage.tsx` | T047-102 | Origen, asignatario, estado, historial, acciones | E2E | playwright | BLOQUEADA OQ-047-02 |
| T047-104 | FR-047-010 · §47 | 047 | `src/modules/notificaciones/alertas/` | T047-080 | Condición, severidad, estado | E2E | playwright | BLOQUEADA OQ-047-02 |
| T047-110 | FR-047-012, 013, 014 | 047 | `tests/test_spec047_security.py` | T047-080 | Empresa, tenant e IDOR | M047-02 · M047-03 · M047-07 | pytest | Tras OQ-047-01 |
| T047-111 | §61-66 · P25 | 047 | `tests/test_spec047_races.py` | T047-041, T047-023 | Carreras forzadas con 500 = 0 | M047-12 | pytest | Tras OQ-047-01 |
| T047-112 | §69 · P27 | 047 | `qa/` registro de mutaciones | T047-110, T047-111 | M047-01..12 caen por semántica | mutaciones | registro | Tras OQ-047-01 |
| T047-113 | §70-80 | 047 | `tests/test_spec047_flows.py` | T047-041 | Flujos A a K | dirigidas | pytest | Tras OQ-047-01 |
| T047-114 | NFR-047-02 · §81-83 | 047 | `tests/test_spec047_volume.py` | T047-080 | > 100 ítems; página 3; recuento de consultas | volumen | pytest | Tras OQ-047-01 |
| T047-115 | §94 | 047 | `tests/test_spec047_integration.py` | T047-040 | 045 real, 038 por la 045, 037 por auditoría | integración | pytest | Tras OQ-047-01 |
| T047-120 | §100-101 | 047 | `e2e/notifications.spec.ts` | T047-101..104 | Chromium, Firefox y WebKit sobre instalación limpia | E2E | playwright | Tras OQ-047-01 y OQ-047-02 |
| T047-121 | §98-99 · §105 | 047 | — | T047-120 | Regresión completa sola; 0 fallos, 0 errores, 0 saltos inesperados | regresión | registro | Tras implementación |
| T047-122 | §107-109 | 047 | `analysis-report.md`, `traceability-matrix.md`, `convergence.md` | T047-121 | Puertas a cero | — | documentos | Tras implementación |
| T047-130 | W35 | 047 | `docs/roadmap/master-56-specs-status.md` | T047-001 | Fila y recuento desde las filas | recuento por script | commit | **HECHA** |
| T047-131 | W36 | 049 | `specs/009-reportes-auditoria/spec049-readiness-revalidation.md` | T047-001 | Solo revalidación | — | commit | **HECHA** |

**49 tareas.** Ninguna sin requisito; ningún requisito sin tarea
(`traceability-matrix.md`).
