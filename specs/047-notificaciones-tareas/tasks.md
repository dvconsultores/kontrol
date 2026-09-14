# `/speckit.tasks` — SPEC 047

> Recalculadas el 2026-09-14. Rutas backend relativas a `resources/backend`,
> frontend a `resources/frontend`.

| ID | Requisito | Dueña | Ficheros | Depende de | Aceptación | Pruebas | Estado |
|---|---|---|---|---|---|---|---|
| T047-001 | Todos | 047 | `specs/047-notificaciones-tareas/*` | — | Artefactos del ciclo | — | **HECHA** |
| T047-002 | FR-047-023, 037-049 | 047 · owner | `ADR-D0-015`, registro de ADR | — | OQ-047-01 cerrada | guarda de ADR | **HECHA** |
| T047-003 | FR-047-033, 034, 050-053 | 047 · owner | `clarifications.md` | — | OQ-047-02 cerrada | — | **HECHA** |
| T047-010 | FR-047-041 | 047 | `app/modules/scheduler/models.py` | T047-002 | Ejecuciones con estados y contadores | `test_spec047_scheduler.py` | **HECHA** |
| T047-011 | FR-047-042, 049 | 047 | `scheduler/registry.py` | T047-010 | Registro explícito con dueña y política | guarda | **HECHA** |
| T047-012 | FR-047-039, 040, 043, 045, 046 | 047 | `scheduler/service.py` | T047-011 | Bloqueo, registro, manejadores, contexto por empresa | flujos A, B · M047-13, 17 | **HECHA** |
| T047-013 | FR-047-037, 047 | 047 | `scheduler/__main__.py` | T047-012 | Orden con códigos 0, 1, 2 | salida de la orden | **HECHA** |
| T047-014 | FR-047-038, 048 | 047 · 052 | `kontrol.py`, `scripts/scheduler/*`, `scripts/install-scheduler.sh`, `instalar.md` | T047-013 | Temporizador sin reglas; intervalo obligatorio | guarda · M047-16 | **HECHA** |
| T047-015 | FR-047-049 | 045 · 047 | `scheduler/registry.py` | T047-012 | Manejador de la 045 deshabilitado que llama a `mark_expired` | flujo D | **HECHA** |
| T047-020 | FR-047-033, 034, 050, 051, 052 | 047 | `app/modules/notifications/messages.py` | T047-003 | Catálogo `es`, contrato de parámetros | flujos E, F · M047-18, 19 | **HECHA** |
| T047-021 | FR-047-053 | 047 | `notifications/*.py`, `scheduler/*.py` | T047-020 | Errores con mensaje de catálogo | guarda | **HECHA** |
| T047-030 | FR-047-001, 003, 004, 011-013, 016, 018, 019, 022, 050 | 047 | `notifications/models.py` | T047-020 | Esquema con claves únicas | `test_spec047_schema.py` | **HECHA** |
| T047-031 | FR-047-001, 002, 015, 016, 026, 027 | 047 | `notifications/service.py` | T047-030 | `publish` idempotente | flujo F · M047-01 | **HECHA** |
| T047-032 | FR-047-054 | 047 | `notifications/sources.py` | T047-031, T047-012 | Consumo de `approval_events` con recibo | flujo A · integración 045 | **HECHA** |
| T047-033 | FR-047-003, 004 | 047 | `notifications/service.py`, `api.py` | T047-031 | Leer y archivar por destinatario | flujo G · M047-04 | **HECHA** |
| T047-034 | FR-047-018, 019 | 047 | `service.py`, `api.py` | T047-031 | Obligatoria no desactivable | dirigida | **HECHA** |
| T047-035 | FR-047-019, 020, 021, 022 | 047 · 048 | `notifications/delivery.py` | T047-031, T047-012 | Estado de entrega separado; reintento | flujo K · M047-06 | **HECHA** |
| T047-036 | FR-047-009, 024, 025 | 047 | `service.py`, `api.py` | T047-030 | Reglas validadas | dirigida | **HECHA** |
| T047-040 | FR-047-005, 006, 007, 008, 009 | 047 | `notifications/models.py` | T047-030 | Tarea, candidatos, historial, prioridades | flujo H | **HECHA** |
| T047-041 | FR-047-007 · R-047-01 | 047 | `service.py`, `api.py` | T047-040 | Iniciar, completar, cancelar sin tocar el dominio | flujo I · M047-05 | **HECHA** |
| T047-042 | FR-047-006 · R-047-04 | 047 | `service.py`, `api.py` | T047-040 | Reasignación con `If-Match` | carrera · M047-09 | **HECHA** |
| T047-043 | FR-047-007 · §18 | 047 | `sources.py` | T047-032 | Cierre `RESOLVED_BY_SOURCE` | dirigida | **HECHA** |
| T047-044 | FR-047-008 · NFR-047-01 | 047 | `service.py` | T047-040 | Vencido con `now` con zona | M047-10 | **HECHA** |
| T047-045 | FR-047-024, 043, 044 | 047 | `notifications/handlers.py` | T047-040, T047-012 | Recordatorio de ventana vigente | flujo C · M047-14, 15 | **HECHA** |
| T047-046 | FR-047-025 | 047 | `handlers.py` | T047-040, T047-012 | Escalada configurada, una vez | dirigida | **HECHA** |
| T047-050 | FR-047-010 | 047 | `models.py`, `service.py`, `sources.py` | T047-031 | Alerta sin tarea; resolución por la dueña | dirigida | **HECHA** |
| T047-060 | FR-047-028, 029 | 047 | `notifications/api.py` | T047-033, T047-041 | Listas paginadas con filtros reales | flujo M | **HECHA** |
| T047-061 | FR-047-030, 036 | 047 | `api.py`, `service.py` | T047-060 | Contadores agregados | flujo L · M047-11 | **HECHA** |
| T047-062 | FR-047-014, 031, 032 | 047 | `service.py` | T047-060 | Visibilidad revalidada; 404 indistinguible | flujo J · M047-07 | **HECHA** |
| T047-063 | FR-047-014 · CL-047-05 | 047 · 003 | `setup/api.py`, migración | T047-070 | Permisos concedidos a ADMIN | dirigida | **HECHA** |
| T047-064 | FR-047-017, 045 | 047 · 006 | `service.py` | T047-031 | Cada transición auditada | reconstrucción | **HECHA** |
| T047-065 | NFR-047-03 | 047 · 006 | `service.py`, `scheduler/service.py` | T047-012 | Registros sin carga sensible | dirigida | **HECHA** |
| T047-066 | FR-047-035 | 047 | `api.py` | T047-060 | Sin rutas de borrado | guarda | **HECHA** |
| T047-067 | §40 | 047 | `app/main.py` | T047-060 | Rutas en OpenAPI con cabecera de empresa | `test_n8_contract.py` | **HECHA** |
| T047-070 | NFR-047-07 | 047 | `alembic/versions/0057_spec047_notifications.py` | T047-030, T047-040, T047-010 | Aditiva; paridad | `test_spec047_schema.py` | **HECHA** |
| T047-071 | NFR-047-07 | 047 | ídem | T047-070 | Ida, vuelta y nueva ida | roundtrip | **HECHA** |
| T047-072 | P24 | 047 | `qa/` | T047-071 | Base nueva → cabeza → siembra → dirigidas → E2E | cadena limpia | **HECHA** |
| T047-080 | FR-047-051, 053 | 047 | `src/i18n/index.ts`, `src/i18n/es.ts` | T047-003 | `t()` con catálogo `es` | `i18n.test.ts` | **HECHA** |
| T047-081 | FR-047-030 | 047 | `src/modules/notificaciones/NotificationBell.tsx`, `src/layout/Topbar.tsx` | T047-061 | Contador del servidor; se actualiza sin recargar | vitest · E2E | **HECHA** |
| T047-082 | FR-047-001, 003, 011, 028, 029, 031 | 047 | `notificaciones/centro/CentroNotificacionesPage.tsx` | T047-060 | Página enrutada con cinco estados | vitest · E2E | **HECHA** |
| T047-083 | FR-047-005-009, 029 | 047 | `notificaciones/tareas/TareasPage.tsx` | T047-060 | Filtros y página 3 | vitest · E2E | **HECHA** |
| T047-084 | FR-047-006 · §46 | 047 | `notificaciones/tareas/TareaDetallePage.tsx` | T047-083 | Detalle, historial, acciones, reasignación | vitest · E2E | **HECHA** |
| T047-085 | FR-047-010 | 047 | `notificaciones/alertas/AlertasPage.tsx` | T047-060 | Condición, severidad, estado | vitest | **HECHA** |
| T047-086 | FR-047-018, 024, 025 | 047 | `notificaciones/reglas/ReglasPage.tsx`, `preferencias/PreferenciasPage.tsx` | T047-036 | Configuración sin modal complejo | vitest | **HECHA** |
| T047-087 | FR-047-053 | 047 | `src/tests/spec047-strings.test.ts` | T047-082..086 | Cero cadenas visibles fuera de catálogo | vitest | **HECHA** |
| T047-090 | FR-047-012, 013, 014 | 047 | `test_spec047_notifications.py`, `test_spec047_tasks.py` | T047-062 | Empresa, tenant, usuario AB, IDOR | M047-02, 03, 07 | **HECHA** |
| T047-091 | NFR-047-06 | 047 | `test_spec047_*.py` | T047-031, T047-042, T047-012 | Mismo hecho, completar dos veces, reasignar, ticks, leer | M047-12, 13 | **HECHA** |
| T047-092 | §77-78 · P27 | 047 | registro en `convergence.md` | T047-090, T047-091 | 19 mutaciones caen por semántica | mutaciones | **HECHA** |
| T047-093 | §80-92 | 047 | `test_spec047_*.py` | T047-032..046 | Flujos A-M | dirigidas | **HECHA** |
| T047-094 | NFR-047-02 | 047 | `test_spec047_notifications.py` | T047-060 | > 100; página 3; recuento de consultas | volumen | **HECHA** |
| T047-095 | §94 | 047 | `test_spec047_notifications.py` | T047-032 | 045 real | integración | **HECHA** |
| T047-096 | FR-047-039, 053 · G047-21 | 047 | `test_spec047_architecture.py` | T047-014 | Sin cola, sin bucles, sin textos, ADR referenciado | guardas | **HECHA** |
| T047-100 | §97 | 047 | `e2e/notifications.spec.ts` | T047-081..086 | Chromium, Firefox y WebKit | E2E | **HECHA** |
| T047-101 | §95-96 | 047 | — | T047-100 | Regresión completa sola | regresión | **HECHA** |
| T047-102 | §101-103 | 047 | `analysis-report.md`, `traceability-matrix.md`, `convergence.md` | T047-101 | Puertas a cero | — | **HECHA** |
| T047-110 | §104 | 047 | `master-56-specs-status.md` | T047-102 | Recuento desde filas | script | **HECHA** |
| T047-111 | §106-112 | 049 | `spec049-readiness-revalidation.md` | T047-110 | Solo revalidación | — | **HECHA** |
| T047-112 | Cierre | 047 | `next-spec-decision.md` | T047-111 | Decisión actualizada | — | **HECHA** |
