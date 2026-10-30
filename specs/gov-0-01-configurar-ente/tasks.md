# Tareas · GOV-0-01 Configurar el ente

Todas las tareas de código las escribe DeepSeek con un encargo de Claude (regla suprema); Claude audita, aplica, prueba y certifica. `RETRY_MAX: 2` en todas. `EGRESS_SAFE`: sí (sin datos reales; contraseñas solo generadas en las pruebas).

## Phase 1: Corte vertical

- [x] T001 [RED] Suite de backend del proceso `tests/test_gov0_ente.py`: máquina de estados, campos, faltantes, documento, versión/`If-Match`, motivo, historial, auditoría, permisos, módulo y aislamiento (otro ente/tenant) · EXECUTOR DEEPSEEK · MODEL pro · SECURITY_SENSITIVE sí · FILES `tests/test_gov0_ente.py` · DONE_WHEN falla en rojo sin el módulo (rutas inexistentes)
- [x] T002 Licencia y dependencia del módulo: `gobierno` en `ENTITLED_MODULES` y `require_module(module)` en `app/core/dependencies.py` (403 `MODULE_NOT_ENTITLED`) · DEEPSEEK · flash · sí · FILES `app/modules/licensing/service.py`, `app/core/dependencies.py`
- [x] T003 Modelos y migración: `app/modules/government/{__init__,models}.py`, `alembic/versions/0063_gov0_entes.py` (tablas, CHECK, índices y concesión de `gobierno_ente:*` a FUNCIONAL_COMPLETO en instalaciones existentes); `init_models` · DEEPSEEK · pro · sí
- [x] T004 Servicio, esquemas y API: `app/modules/government/{schemas,service,api}.py`, el registro en `app/main.py`, `CATALOGO_DE_PERMISOS`, `ResourceKind("GovernmentEntity")` y las 3 acciones en `audit_catalog_entries.py` · DEEPSEEK · pro · sí · DONE_WHEN T001 en verde
- [x] T005 Guardas y contratos: `RUTAS_SIN_EMPRESA_CLASIFICADAS` (`GET /gobierno/modulo`), cabeza `0063` (MIG-09/10, KR-18/19); regenerar las instantáneas del frontend (`qa/fixtures_de_frontend.py`, herramienta) · DEEPSEEK + herramienta
- [x] T006 Frontend: tipos, `useModuloGobierno`, `GobiernoEntePage` (vacío/alta/ficha/edición/modificación con motivo/activación con confirmación/faltantes/documentos/historial/estados), router, grupo «Gobierno» del menú, `pantallas.ts` y el rótulo «Ente» del selector en el perfil de Gobierno · DEEPSEEK · pro
- [x] T007 Pruebas de frontend (vitest): menú, pantalla, campos condicionales, acciones por estado y permiso, errores (403 módulo, 409, 422 faltantes, 428) · DEEPSEEK · pro
- [x] T008 E2E de usuario `e2e/gobierno-ente.spec.ts` (login → menú → alta → documento → faltantes → activación → modificación con motivo → historial → auditoría; negativos: sin capacidad, otro ente; axe a 1280/320) y el entitlement `gobierno` en `qa/pg-e2e-seed.py` · DEEPSEEK · pro
- [x] T009 Mutaciones de negocio, campaña GOV0 (herramienta de Claude) · CLAUDE · n-a
- [x] T010 Certificación: suites PG/SQLite, frontend, E2E ×3 y canónica, base tras la E2E, OpenAPI (deriva explicada: 6 operaciones nuevas), residuos, tarjeta UAT, métricas de Gobierno · CLAUDE · n-a

## Phase 2: Correcciones y divisiones (auditoría, suites y E2E)

Tareas nacidas de la auditoría de Claude, de la suite completa, de las mutaciones o de la E2E real. Cada una nombra su evidencia; ninguna se cerró sin la prueba que la demuestra.

- [x] T011 [T001b] Ayudante de prueba `_documento_activo` con tipo documental (`document_type_id` NOT NULL) · DEEPSEEK · flash · evidencia: `NotNullViolation` en GE-07/14 → 18/18
- [x] T012 [T001c] GE-05 sin verde falso: denominación válida en cada caso y campo rechazado en `field_errors` · DEEPSEEK · flash · evidencia: mutante GB14 sobreviviente → muerto
- [x] T013 [T004c] Orden de guardas permiso → empresa → módulo (contrato de aislamiento del ciclo 07) y clasificación MFA de `gobierno_ente:*` (PDD-GOV0-04) · DEEPSEEK · flash · evidencia: barrido de cabecera manipulada y MFA-G00; reintento 1 por GE-12 (`COMPANY_SCOPE_FORBIDDEN` en vez de `PERMISSION_DENIED`)
- [x] T014 [T005b] Declaraciones en guardas cerradas: CATB-03 236, DC-T01 89, MFA-G00b 37/35, N10, lecturas sin capacidad, N9 (25 tipos y semilla `GovernmentEntity`) · DEEPSEEK · flash · evidencia: suite PG completa
- [x] T015 [T006c] El alta era inalcanzable (la guarda genérica de error iba antes) · DEEPSEEK · flash · evidencia: GEP-02
- [x] T016 [T008b] La siembra de QA reimporta una licencia sin el módulo `gobierno` · DEEPSEEK · flash
- [x] T017 [T008c] Rótulo de campo obligatorio por regex en la E2E · DEEPSEEK · flash · evidencia: timeout en GOV-E2E-01
- [x] T018 [T008d] Cerrar las notificaciones persistentes antes de pulsar acciones de la cabecera · DEEPSEEK · flash · evidencia: «notification-root intercepts pointer events» en los tres navegadores

## Phase 3: Convergence

- [x] T019 Record in plan.md that the frontend API contract of the slice lives in `src/modules/gobierno/api.ts` (per-module contract pattern of Spec 047, `src/modules/notificaciones/api.ts`) instead of `src/api/types.ts`, per plan: touch-points (partial)
