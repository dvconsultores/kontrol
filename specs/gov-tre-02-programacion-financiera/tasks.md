# Tasks: TRE-02 Programación financiera y disponibilidad de caja

**Input**: `specs/gov-tre-02-programacion-financiera/`

**Clasificación común** (salvo indicación): EXECUTOR DEEPSEEK · MODEL deepseek-v4-pro · SECURITY_SENSITIVE sí · EGRESS_SAFE sí · RETRY_MAX 2. Después de dos intentos: dividir, rediseñar o bloquear. Claude no escribe código ni bloques SEARCH/REPLACE semánticos. Las tareas CLAUDE son de certificación y documentación.

**Registro de intentos:** `evidence/ATTEMPT_LOG.md`.

## Phase 1: Setup

- [X] T001 Registrar `gobierno_caja` (view, manage, activate) en `resources/backend/app/modules/setup/api.py` y `resources/backend/app/modules/identity_access/mfa_policy.py`, con view y manage STANDARD y activate SENSITIVE · MODEL flash · TEST `test_mfa_policy.py` · DONE_WHEN recuentos 120, SENSITIVE 52, STANDARD 51

## Phase 2: Foundational

- [X] T002 Crear los modelos en `resources/backend/app/modules/government/models.py` según `data-model.md`: importes `NUMERIC(18,2)`, `monto` > 0 en líneas y ≥ 0 en declaraciones, `mes` 1–12, `fundamento` 10–500, índices únicos parciales · TEST T007 · DONE_WHEN importan y crean tablas
- [X] T003 Crear `resources/backend/alembic/versions/0074_gov_tre02_caja.py` con las mismas restricciones y disparadores, sobre `0073_gov_tre01_cuentas`, y ampliar el proceso SoD · TEST subir, bajar y subir desde una base nueva · DONE_WHEN cabeza única y paridad con modelos
- [X] T004 [P] Crear `resources/backend/app/modules/government/schemas_caja.py` según `contracts/api.md` · MODEL flash · TEST T007 · DONE_WHEN entradas prohíben campos extra e importes usan Decimal
- [X] T005 [P] Registrar 8 acciones en `resources/backend/app/shared/audit_catalog_entries.py`, el proceso en `service_auditoria.py`, las acciones SoD en `service_sod.py` y el enum en `schemas_sod.py` · MODEL flash · TEST `test_audit_catalog_backup.py`, `test_gov_ctl01_reglas.py` · DONE_WHEN catálogo 311
- [X] T006 Actualizar en `resources/backend/tests/` los recuentos y la cabeza que muevan T001, T003 y T005 · MODEL flash · DONE_WHEN guardas verdes

## Phase 3: User Story 1 - Programar y ver la disponibilidad (P1) 🎯 MVP

**Goal**: crear, declarar, programar, ver y activar. **Independent Test**: flujo completo con cuenta vigente.

- [X] T007 [US1] RED: `resources/backend/tests/test_gov_tre02_programa.py`: alta, duplicado, declaración, cuenta inválida (ajena, otra moneda, borrador, inactiva, cerrada), fundamento, línea, mes, fórmula con céntimos, déficit, activar, faltantes
- [X] T008 [US1] Crear `resources/backend/app/modules/government/service_caja.py` con catálogo de lectura, programa, declaraciones, líneas, cálculo y activar · TEST T007
- [X] T009 [US1] Crear `resources/backend/app/modules/government/api_caja.py` y registrarlo en `resources/backend/app/main.py` · MODEL flash · TEST T007
- [X] T010 [P] [US1] Añadir contrato, rutas, pantallas y menú en `resources/frontend/src/modules/gobierno/api.ts`, `app/router.tsx`, `app/autoridad/pantallas.ts`, `layout/Sidebar.tsx` · MODEL flash · TEST tsc
- [X] T011 [P] [US1] Crear `resources/frontend/src/modules/gobierno/tesoreria/programacion/ProgramasPage.tsx` y su prueba · TEST vitest
- [X] T012 [P] [US1] Crear `.../programacion/NuevoProgramaPage.tsx` y su prueba · TEST vitest
- [X] T013 [US1] Crear `.../programacion/ProgramaPage.tsx` con datos, disponibilidad y activar, y su prueba · TEST vitest
- [X] T014 [US1] Crear `.../programacion/DeclaracionesPrograma.tsx` y `LineasPrograma.tsx` con sus pruebas · TEST vitest

## Phase 4: User Story 2 - Reprogramar (P1)

**Goal**: versiones sin reescribir historia. **Independent Test**: reprogramar y comparar.

- [X] T015 [US2] RED: `resources/backend/tests/test_gov_tre02_versiones.py`: reprogramar, mes pasado, declaración fija, superada, descartar, ejercicio terminado, inmutabilidad directa en PostgreSQL
- [X] T016 [US2] Añadir reprogramar y descartar a `service_caja.py` y `api_caja.py` · TEST T015
- [X] T017 [US2] Añadir reprogramación, descarte y versiones a `ProgramaPage.tsx` · TEST vitest

## Phase 5: User Story 3 - Cerrar (P2)

- [X] T018 [US3] RED: `resources/backend/tests/test_gov_tre02_cierre.py`: cerrar, borrador abierto, cerrado inmutable, ejercicio ocupado
- [X] T019 [US3] Añadir cerrar a `service_caja.py`, `api_caja.py` y `ProgramaPage.tsx` · TEST T018, vitest

## Phase 6: User Story 4 - Rubros (P2)

- [X] T020 [US4] RED: `resources/backend/tests/test_gov_tre02_rubros.py`: alta, duplicado, tipo fijo, inactivar, línea existente conservada
- [X] T021 [US4] Añadir rubros a `service_caja.py` y `api_caja.py` · TEST T020
- [X] T022 [P] [US4] Crear `.../programacion/RubrosPage.tsx` y su prueba · TEST vitest

## Phase 7: User Story 5 - Consulta y seguridad (P3)

- [X] T023 [US5] RED: `resources/backend/tests/test_gov_tre02_seguridad.py`: otra empresa, rol, `company_id` del cliente, versión vieja, UUID directo, historia, sin números de cuenta en auditoría, CTL-04 y SoD
- [X] T024 [US5] RED: `resources/backend/tests/test_gov_tre02_concurrencia.py`: dos reprogramaciones, activar contra editar, línea duplicada, cerrar contra reprogramar, versión vieja

## Phase 8: User Story 6 - OBS-TRE01-E2E-01 (P2)

- [X] T025 [US6] Crear `resources/frontend/e2e/gobierno-tesoreria-revocacion.spec.ts`: cuenta vigente, revocar o anular el acto en DOC-02, aviso, autorizado y reactivación bloqueados, acto de reemplazo, historia y auditoría · TEST chromium

## Phase 9: Polish & Certification

- [X] T026 Crear `resources/frontend/e2e/gobierno-programacion.spec.ts` (flujo, negativas, axe 1280/768/320) y ampliar `resources/frontend/e2e/uat-humo-gobierno.spec.ts` · TEST ×3
- [X] T027 Crear `qa/gobierno_integridad_caja.py` y registrarlo en `qa/gobierno_integridad.py` y su prueba · MODEL flash
- [X] T028 Regenerar espejo del catálogo y fixtures de frontend · EXECUTOR CLAUDE · MODEL n-a
- [X] T029 Mutaciones de negocio y `evidence/MUTATIONS.md` · EXECUTOR CLAUDE · MODEL n-a
- [X] T030 Certificación completa: PostgreSQL, SQLite, vitest, tsc, eslint, build, ruff, mypy, OpenAPI, regresión ×3, canónica, integridad · EXECUTOR CLAUDE · MODEL n-a
- [X] T031 Reclasificar TRE-01 y TRE-02 y recalcular métricas en `docs/roadmap/government-product-completeness/` · EXECUTOR CLAUDE · MODEL n-a
- [X] T032 `evidence/OWNER_UAT_CARD.md`, `REQUIRED_SUITE_INVENTORY.md`, `UAT_SMOKE.md` · EXECUTOR CLAUDE · MODEL n-a
- [ ] T033 `/speckit-converge`, commit, push, relevo UAT y humo · EXECUTOR CLAUDE · MODEL n-a

## Dependencies

Las pruebas T007, T015, T018, T020, T023 y T024 se escriben y se demuestran en rojo contra `5e3d214` antes de cualquier código de producto (hallazgo I2 de analyze). Phase 1 → Phase 2 → US1 → (US2, US3, US4, US5) → US6 y Phase 9. T008 usa rubros por modelo hasta T021; las tareas [P] tocan ficheros distintos.

## Parallel Example

T011, T012 y T022 pueden encargarse a la vez; T004 y T005 también.

## Implementation Strategy

Corte vertical: US1 llega a pantalla y prueba antes de US2. Cada tarea se prueba al aplicarse.

## Phase 10: Convergence

- [X] T034 Añadir a `resources/backend/tests/test_gov_tre02_seguridad.py` pruebas de la guarda SoD en reprogramar y cerrar, con mutantes CJ-M27 y CJ-M28, per FR-024 (partial)
- [X] T035 Mostrar «—» en «Versión vigente» de `resources/frontend/src/modules/gobierno/tesoreria/programacion/ProgramaPage.tsx` cuando no hay versión vigente, per SC-006 (partial)
- [X] T036 Dejar constancia en `specs/gov-tre-02-programacion-financiera/evidence/REQUIRED_SUITE_INVENTORY.md` de que RB-01..07 viven en `test_gov_tre02_cierre.py`, per T020 (partial)

## Phase 11: Corrección preexistente hallada al certificar

- [X] T037 Evitar los rechazos no capturados de `resources/frontend/src/modules/gobierno/hallazgos/HallazgoPage.tsx`, con la prueba HLP-03b en `HallazgoPage.test.tsx`; preexistente en `5e3d214`, necesaria para vitest rc=0 · EXECUTOR DEEPSEEK · MODEL deepseek-v4-flash
