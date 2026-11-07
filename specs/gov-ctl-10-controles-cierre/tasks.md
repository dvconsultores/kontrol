# Tasks: CTL-10 Controles materiales previos al cierre

**Input**: `specs/gov-ctl-10-controles-cierre/`

**Clasificación**: todo código, prueba y migración es EXECUTOR DEEPSEEK (`deepseek-v4-flash` lo mecánico, `deepseek-v4-pro` la lógica local); la certificación, las mutaciones, la evidencia y Git son CLAUDE. Cada tarea lleva EXECUTOR, MODEL, SECURITY_SENSITIVE, EGRESS_SAFE, RETRY_MAX 2, FILES, TEST y DONE_WHEN. Tras dos intentos fallidos: dividir, rediseñar o bloquear. Claude no escribe código ni SEARCH/REPLACE semánticos. Un encargo ≤ 40.000 caracteres por llamada; las tareas con varios ficheros se encargan fichero a fichero. EGRESS_SAFE: YES = sin secretos, PII ni datos reales.

**Registro de intentos:** `evidence/ATTEMPT_LOG.md`.

**RED primero:** cada tarea «RED» se escribe y se demuestra en rojo contra `HEAD` (y se registra en `evidence/RED.md`) antes de cualquier código de producto de su historia; las historias se ordenan por prioridad, pero el RED de una historia precede siempre a su implementación.


## Phase 1: Setup (registro autorizado por OD-CTL10-01)

- [X] T001 Registrar la capacidad `gobierno_cierre` (view, manage, activate) en `resources/backend/app/modules/setup/api.py` y `resources/backend/app/modules/identity_access/mfa_policy.py`: view y manage STANDARD, activate SENSITIVE; solo añadidos, sin cambiar lógica
  - EXECUTOR: DEEPSEEK · MODEL: deepseek-v4-flash · SECURITY_SENSITIVE: YES · EGRESS_SAFE: YES · RETRY_MAX: 2
  - FILES: `resources/backend/app/modules/setup/api.py`, `resources/backend/app/modules/identity_access/mfa_policy.py`, `resources/backend/tests/test_mfa_policy.py`
  - TEST: `.venv/bin/python -m pytest tests/test_mfa_policy.py`
  - DONE_WHEN: recuentos SENSITIVE 52→53 y STANDARD 51→53; `gobierno_cierre` otorgada a FUNCIONAL_COMPLETO y no al ADMIN técnico
- [X] T002 Registrar las 8 acciones de auditoría (`GOV_CLOSURE_POLICY_CREATED`, `_UPDATED`, `_CONTROL_ADDED`, `_CONTROL_REMOVED`, `_ACTIVATED`, `_RETIRED`, `GOV_MATERIAL_CLOSE_BLOCKED`, `GOV_MATERIAL_CLOSE_ALLOWED`; owner_spec `gov-ctl-10`, entidad `GovernmentClosurePolicy`) en `app/shared/audit_catalog_entries.py` y `specs/001-fundacion/evidence/audit-catalog/catalogo.md`; solo añadidos
  - EXECUTOR: DEEPSEEK · MODEL: deepseek-v4-flash · SECURITY_SENSITIVE: YES · EGRESS_SAFE: YES · RETRY_MAX: 2
  - FILES: `resources/backend/app/shared/audit_catalog_entries.py`, `specs/001-fundacion/evidence/audit-catalog/catalogo.md`, `resources/backend/tests/test_audit_catalog_backup.py`
  - TEST: `.venv/bin/python -m pytest tests/test_audit_catalog_backup.py`
  - DONE_WHEN: catálogo 311→319 y espejo `catalogo.md` coincide
- [X] T003 Registrar el proceso CTL-10 en `service_auditoria.py` (`PROCESOS`: «CTL-10», «Controles de cierre», «gov-ctl-10», rastreo `/gobierno/cierres/{id}`), en `service_sod.py` (`CATALOGO_SOD`: CTL10_REGISTRAR→GOV_CLOSURE_POLICY_CREATED con crea=True, CTL10_ACTIVAR→_ACTIVATED, CTL10_RETIRAR→_RETIRED; sin reglas por defecto) y el enum en `schemas_sod.py`
  - EXECUTOR: DEEPSEEK · MODEL: deepseek-v4-pro · SECURITY_SENSITIVE: YES · EGRESS_SAFE: YES · RETRY_MAX: 2
  - FILES: `resources/backend/app/modules/government/service_auditoria.py`, `resources/backend/app/modules/government/service_sod.py`, `resources/backend/app/modules/government/schemas_sod.py`, `resources/backend/tests/test_gov_ctl01_reglas.py`
  - TEST: `.venv/bin/python -m pytest tests/test_gov_ctl01_reglas.py tests/test_audit_catalog_backup.py`
  - DONE_WHEN: el proceso CTL-10 aparece en los catálogos de CTL-04 y CTL-01 sin reglas sembradas; pruebas existentes verdes

## Phase 2: Foundational (bloquea todas las historias)

- [X] T004 RED: crear `resources/backend/tests/test_gov_ctl10_modelo.py`: paridad modelo-migración, `codigo` único por empresa, índice parcial una VIGENTE por empresa+accion_cierre, único policy+tipo, CHECK de `riesgo_minimo` (obligatorio si HALLAZGOS_ABIERTOS, nulo si ACTOS_SIN_EFICACIA), `materialidad` 10-500, `fundamento` ≥10, disparadores de inmutabilidad (política VIGENTE/RETIRADA no editable ni borrable, controles fuera de BORRADOR, historia sin UPDATE ni DELETE) en PostgreSQL
  - EXECUTOR: DEEPSEEK · MODEL: deepseek-v4-pro · SECURITY_SENSITIVE: YES · EGRESS_SAFE: YES · RETRY_MAX: 2
  - FILES: `resources/backend/tests/test_gov_ctl10_modelo.py`
  - TEST: `.venv/bin/python -m pytest tests/test_gov_ctl10_modelo.py` en PostgreSQL
  - DONE_WHEN: la prueba falla contra HEAD por ausencia de modelos y tablas (registrado por Claude en `evidence/RED.md`)
- [X] T005 Crear en `resources/backend/app/modules/government/models.py` los modelos `GovernmentClosurePolicy` (gov_closure_policies), `GovernmentClosureControl` (gov_closure_controls) y `GovernmentClosurePolicyHistory` (gov_closure_policy_history) según `data-model.md`; `codigo` PC-### hasta 10, `nombre` 3–200, `accion_cierre` ORG02_CERRAR_ESTRUCTURA|TRE02_CERRAR_PROGRAMA, `estado` BORRADOR|VIGENTE|RETIRADA, `riesgo_minimo` ALTO|MEDIO|BAJO nulo según tipo, `materialidad` 10–500; sin FK compuestas con `company_id`
  - EXECUTOR: DEEPSEEK · MODEL: deepseek-v4-pro · SECURITY_SENSITIVE: YES · EGRESS_SAFE: YES · RETRY_MAX: 2
  - FILES: `resources/backend/app/modules/government/models.py`
  - TEST: T de modelo (`test_gov_ctl10_modelo.py`)
  - DONE_WHEN: los modelos importan y crean tablas en SQLite y PostgreSQL
- [X] T006 Crear `resources/backend/alembic/versions/0075_gov_ctl10_cierres.py` sobre `0074_gov_tre02_caja`: tres tablas `gov_*`, mismos CHECK, únicos, índice parcial y disparadores que el modelo (controles inmutables si la política no está en BORRADOR; VIGENTE/RETIRADA no editables ni borrables; historia sin UPDATE ni DELETE)
  - EXECUTOR: DEEPSEEK · MODEL: deepseek-v4-pro · SECURITY_SENSITIVE: YES · EGRESS_SAFE: YES · RETRY_MAX: 2
  - FILES: `resources/backend/alembic/versions/0075_gov_ctl10_cierres.py`
  - TEST: subir, bajar y subir desde una base nueva en PostgreSQL; `test_gov_ctl10_modelo.py`
  - DONE_WHEN: cabeza única `0075_gov_ctl10_cierres` y paridad con los modelos
- [X] T007 Crear `resources/backend/app/modules/government/schemas_cierres.py` según `contracts/api.md`: entradas que prohíben campos extra (`PoliticaIn`, `PoliticaCambios`, `ControlIn`, `RetiroIn`), salidas de detalle, lista, catálogo y bloqueo
  - EXECUTOR: DEEPSEEK · MODEL: deepseek-v4-flash · SECURITY_SENSITIVE: YES · EGRESS_SAFE: YES · RETRY_MAX: 2
  - FILES: `resources/backend/app/modules/government/schemas_cierres.py`
  - TEST: mypy y pruebas de las historias
  - DONE_WHEN: entradas con `extra=forbid`; sin campo `company_id` en ninguna entrada
- [X] T008 Actualizar las guardas de cabeza de migración a `0075_gov_ctl10_cierres` en `resources/backend/tests/test_installation_key_reference.py` y `resources/backend/tests/test_migraciones_url_porcentaje.py`
  - EXECUTOR: DEEPSEEK · MODEL: deepseek-v4-flash · SECURITY_SENSITIVE: NO · EGRESS_SAFE: YES · RETRY_MAX: 2
  - FILES: `resources/backend/tests/test_installation_key_reference.py`, `resources/backend/tests/test_migraciones_url_porcentaje.py`
  - TEST: ambas pruebas
  - DONE_WHEN: guardas verdes con la cabeza nueva

## Phase 3: User Story 1 - Definir y activar una política de cierre (Priority: P1) MVP

**Goal**: crear, controlar, activar. **Independent Test**: flujo completo desde el menú con MFA.

- [X] T009 [US1] RED: crear `resources/backend/tests/test_gov_ctl10_politicas.py` (alta con código PC-001, nombre 3-200, fundamento ≥10, control HALLAZGOS_ABIERTOS con riesgo, tipo repetido, riesgo en ACTOS_SIN_EFICACIA, tipo fuera del catálogo 422, activar sin controles, activar con MFA, activar con otra VIGENTE → 409 `GOV_CLOSURE_POLICY_ACTIVE_EXISTS`, historia, auditoría, SoD CTL10_ACTIVAR) y las pruebas vitest `PoliticasPage.test.tsx`, `NuevaPoliticaPage.test.tsx`, `PoliticaPage.test.tsx` en `resources/frontend/src/modules/gobierno/cierres/`
  - EXECUTOR: DEEPSEEK · MODEL: deepseek-v4-pro · SECURITY_SENSITIVE: YES · EGRESS_SAFE: YES · RETRY_MAX: 2
  - FILES: `resources/backend/tests/test_gov_ctl10_politicas.py`, `resources/frontend/src/modules/gobierno/cierres/PoliticasPage.test.tsx`, `resources/frontend/src/modules/gobierno/cierres/NuevaPoliticaPage.test.tsx`, `resources/frontend/src/modules/gobierno/cierres/PoliticaPage.test.tsx`
  - TEST: pytest del fichero; `npx vitest run src/modules/gobierno/cierres`
  - DONE_WHEN: fallan contra HEAD por la razón esperada (registrado en `evidence/RED.md`)
- [X] T010 [US1] Crear `resources/backend/app/modules/government/service_cierres.py` con catálogo, crear política (código PC-### por empresa), añadir control y activar (MFA lo exige la ruta; ≥1 control; una VIGENTE por empresa+acción; historia y auditoría; SoD en activar)
  - EXECUTOR: DEEPSEEK · MODEL: deepseek-v4-pro · SECURITY_SENSITIVE: YES · EGRESS_SAFE: YES · RETRY_MAX: 2
  - FILES: `resources/backend/app/modules/government/service_cierres.py`
  - TEST: `test_gov_ctl10_politicas.py`
  - DONE_WHEN: pruebas del backend de US1 en verde en PostgreSQL y SQLite
- [X] T011 [US1] Crear `resources/backend/app/modules/government/api_cierres.py` con GET `/catalogo`, GET/POST `/politicas`, GET `/politicas/{id}`, POST `/politicas/{id}/controles` y POST `/politicas/{id}/activar` (guardas autenticación → permiso → empresa → módulo `gobierno`) y registrarlo en `resources/backend/app/main.py` (solo añadido)
  - EXECUTOR: DEEPSEEK · MODEL: deepseek-v4-pro · SECURITY_SENSITIVE: YES · EGRESS_SAFE: YES · RETRY_MAX: 2
  - FILES: `resources/backend/app/modules/government/api_cierres.py`, `resources/backend/app/main.py`
  - TEST: `test_gov_ctl10_politicas.py`
  - DONE_WHEN: endpoints responden según `contracts/api.md`; OpenAPI regenerable
- [X] T012 [US1] Añadir contrato, rutas, pantallas y menú «Controles de cierre» en `resources/frontend/src/modules/gobierno/api.ts`, `resources/frontend/src/app/router.tsx`, `resources/frontend/src/app/autoridad/pantallas.ts` y `resources/frontend/src/layout/Sidebar.tsx` (solo añadidos; rutas `/gobierno/cierres`, `/nueva`, `/:politicaId`, `/bloqueos`)
  - EXECUTOR: DEEPSEEK · MODEL: deepseek-v4-flash · SECURITY_SENSITIVE: YES · EGRESS_SAFE: YES · RETRY_MAX: 2
  - FILES: `resources/frontend/src/modules/gobierno/api.ts`, `resources/frontend/src/app/router.tsx`, `resources/frontend/src/app/autoridad/pantallas.ts`, `resources/frontend/src/layout/Sidebar.tsx`
  - TEST: `npm run typecheck`
  - DONE_WHEN: tipos y rutas compilan; el menú aparece solo con `gobierno_cierre:view`
- [X] T013 [P] [US1] Crear `resources/frontend/src/modules/gobierno/cierres/PoliticasPage.tsx` (lista, indicadores, filtros acción y estado) según `evidence/CTL10_SCREEN_FORM_MATRIX.md` S1
  - EXECUTOR: DEEPSEEK · MODEL: deepseek-v4-pro · SECURITY_SENSITIVE: NO · EGRESS_SAFE: YES · RETRY_MAX: 2
  - FILES: `resources/frontend/src/modules/gobierno/cierres/PoliticasPage.tsx`, `resources/frontend/src/modules/gobierno/cierres/PoliticasPage.test.tsx`
  - TEST: `npx vitest run src/modules/gobierno/cierres/PoliticasPage.test.tsx`
  - DONE_WHEN: prueba de la página en verde; estados vacío, error y 403 cubiertos
- [X] T014 [P] [US1] Crear `resources/frontend/src/modules/gobierno/cierres/NuevaPoliticaPage.tsx` (campos C01–C05) según matriz S2
  - EXECUTOR: DEEPSEEK · MODEL: deepseek-v4-pro · SECURITY_SENSITIVE: NO · EGRESS_SAFE: YES · RETRY_MAX: 2
  - FILES: `resources/frontend/src/modules/gobierno/cierres/NuevaPoliticaPage.tsx`, `resources/frontend/src/modules/gobierno/cierres/NuevaPoliticaPage.test.tsx`
  - TEST: `npx vitest run src/modules/gobierno/cierres/NuevaPoliticaPage.test.tsx`
  - DONE_WHEN: prueba verde; rótulos obligatorios y `aria-invalid`
- [X] T015 [US1] Crear `resources/frontend/src/modules/gobierno/cierres/PoliticaPage.tsx` con datos, controles (K01–K03), activar con MFA e historia, según matriz S3
  - EXECUTOR: DEEPSEEK · MODEL: deepseek-v4-pro · SECURITY_SENSITIVE: YES · EGRESS_SAFE: YES · RETRY_MAX: 2
  - FILES: `resources/frontend/src/modules/gobierno/cierres/PoliticaPage.tsx`, `resources/frontend/src/modules/gobierno/cierres/PoliticaPage.test.tsx`
  - TEST: `npx vitest run src/modules/gobierno/cierres/PoliticaPage.test.tsx`
  - DONE_WHEN: prueba verde; sin acciones de escritura con solo `view`

## Phase 4: User Story 2 - El cierre se bloquea con controles materiales pendientes (Priority: P1)

**Goal**: la guarda en los dos cierres y el panel. **Independent Test**: flujo A (estructura de un ejercicio pasado con hallazgo abierto) y flujo B (programa con acto emitido).

- [X] T016 [US2] RED: crear `resources/backend/tests/test_gov_ctl10_guarda.py` (hallazgo ALTO/MEDIO/BAJO contra `riesgo_minimo`, hallazgo CERRADO no cuenta, hallazgos de todo el ente, acto EMITIDO dentro y fuera del ejercicio, otros estados de acto no cuentan, sin política, BORRADOR, RETIRADA, futura, vencida, pasa con política efectiva y `GOV_MATERIAL_CLOSE_ALLOWED` en la misma transacción, bloqueo → rollback + `GOV_MATERIAL_CLOSE_BLOCKED` REJECTION con `after` del contrato, 409 con `details` y muestra ≤5 con rutas, orden estado → SoD → CTL-10 en `service_caja.cerrar`, cierre de estructura y de programa sin cambio cuando no hay política, el cliente no envía controles) y `BloqueoDeCierre.test.tsx`, `EstructuraPage.bloqueo.test.tsx`, `ProgramaPage.bloqueo.test.tsx`
  - EXECUTOR: DEEPSEEK · MODEL: deepseek-v4-pro · SECURITY_SENSITIVE: YES · EGRESS_SAFE: YES · RETRY_MAX: 2
  - FILES: `resources/backend/tests/test_gov_ctl10_guarda.py`, `resources/frontend/src/modules/gobierno/cierres/BloqueoDeCierre.test.tsx`, `resources/frontend/src/modules/gobierno/estructura/EstructuraPage.bloqueo.test.tsx`, `resources/frontend/src/modules/gobierno/tesoreria/programacion/ProgramaPage.bloqueo.test.tsx`
  - TEST: pytest del fichero; vitest de los tres
  - DONE_WHEN: fallan contra HEAD por la razón esperada (registrado en `evidence/RED.md`)
- [X] T017 [US2] Añadir `evaluar_cierre(db, ctx, accion, objeto_tipo, objeto_id, objeto_codigo, ejercicio)` a `service_cierres.py`: política efectiva (fecha civil America/Caracas) con FOR SHARE; consultas fijas por tipo (HALLAZGOS_ABIERTOS: `estado <> 'CERRADO'` y riesgo ≥ `riesgo_minimo` en todo el ente; ACTOS_SIN_EFICACIA: `status = 'EMITIDO'` y `fecha` en el año del ejercicio); sin política no hace nada; con pendientes `record_audit_after_rollback` y 409 `GOV_MATERIAL_CLOSE_BLOCKED`; sin pendientes audita `GOV_MATERIAL_CLOSE_ALLOWED`
  - EXECUTOR: DEEPSEEK · MODEL: deepseek-v4-pro · SECURITY_SENSITIVE: YES · EGRESS_SAFE: YES · RETRY_MAX: 2
  - FILES: `resources/backend/app/modules/government/service_cierres.py`
  - TEST: `test_gov_ctl10_guarda.py`
  - DONE_WHEN: pruebas de la guarda en verde en PostgreSQL y SQLite
- [X] T018 [US2] Insertar la llamada a `evaluar_cierre` en `service_estructura.cerrar` (objeto_tipo `GovernmentStructure`, código `EST-<ejercicio>`, ejercicio de la estructura, tras estado y ejercicio terminado, antes de la mutación) y en `service_caja.cerrar` (`GovernmentCashProgram`, `programa.codigo`, `programa.ejercicio`, tras estado, borrador abierto y `evaluar_antes_de_actuar`, antes de la mutación); sin cambiar nada más
  - EXECUTOR: DEEPSEEK · MODEL: deepseek-v4-pro · SECURITY_SENSITIVE: YES · EGRESS_SAFE: YES · RETRY_MAX: 2
  - FILES: `resources/backend/app/modules/government/service_estructura.py`, `resources/backend/app/modules/government/service_caja.py`
  - TEST: `test_gov_ctl10_guarda.py` y la regresión de ORG-02 y TRE-02
  - DONE_WHEN: diff limitado a la llamada y su import; regresión de ORG-02 y TRE-02 sin cambio de contrato
- [X] T019 [US2] Crear `resources/frontend/src/modules/gobierno/cierres/BloqueoDeCierre.tsx` (qué lo impide, por qué es material, pendientes con enlaces `/gobierno/hallazgos/{id}` y `/gobierno/actos/{id}`, ruta de lista, dueño «Control Interno»; `role=alert`) y su tipo en `api.ts`
  - EXECUTOR: DEEPSEEK · MODEL: deepseek-v4-pro · SECURITY_SENSITIVE: NO · EGRESS_SAFE: YES · RETRY_MAX: 2
  - FILES: `resources/frontend/src/modules/gobierno/cierres/BloqueoDeCierre.tsx`, `resources/frontend/src/modules/gobierno/api.ts`
  - TEST: `npx vitest run src/modules/gobierno/cierres/BloqueoDeCierre.test.tsx`
  - DONE_WHEN: prueba verde; más de 5 pendientes muestra el total real
- [X] T020 [US2] Montar `BloqueoDeCierre` ante el 409 `GOV_MATERIAL_CLOSE_BLOCKED` en `resources/frontend/src/modules/gobierno/estructura/EstructuraPage.tsx` y `resources/frontend/src/modules/gobierno/tesoreria/programacion/ProgramaPage.tsx`, sin cambiar el resto del comportamiento
  - EXECUTOR: DEEPSEEK · MODEL: deepseek-v4-pro · SECURITY_SENSITIVE: NO · EGRESS_SAFE: YES · RETRY_MAX: 2
  - FILES: `resources/frontend/src/modules/gobierno/estructura/EstructuraPage.tsx`, `resources/frontend/src/modules/gobierno/tesoreria/programacion/ProgramaPage.tsx`
  - TEST: `npx vitest run` de ambas páginas y de sus pruebas existentes
  - DONE_WHEN: pruebas nuevas y existentes de ambas páginas en verde

## Phase 5: User Story 3 - Retirar una política (Priority: P1)

**Goal**: retirar con MFA y motivo. **Independent Test**: retirar una vigente y ver que el cierre procede.

- [X] T021 [US3] RED: crear `resources/backend/tests/test_gov_ctl10_retiro.py` (retirar VIGENTE con MFA y motivo 10-500, retirar BORRADOR con MFA, política RETIRADA no vuelve, editar/añadir/quitar/borrar tras activar → rechazo incluso por SQL directo, tras retirar el cierre procede, SoD CTL10_RETIRAR, auditoría `_RETIRED`) y ampliar `PoliticaPage.test.tsx` con retirar
  - EXECUTOR: DEEPSEEK · MODEL: deepseek-v4-pro · SECURITY_SENSITIVE: YES · EGRESS_SAFE: YES · RETRY_MAX: 2
  - FILES: `resources/backend/tests/test_gov_ctl10_retiro.py`, `resources/frontend/src/modules/gobierno/cierres/PoliticaPage.test.tsx`
  - TEST: pytest del fichero; vitest de la página
  - DONE_WHEN: fallan contra HEAD por la razón esperada (registrado en `evidence/RED.md`)
- [X] T022 [US3] Añadir `retirar` a `service_cierres.py` y POST `/politicas/{id}/retirar` a `api_cierres.py` (BORRADOR o VIGENTE; MFA siempre; motivo 10-500; historia RETIRADA; auditoría; SoD CTL10_RETIRAR)
  - EXECUTOR: DEEPSEEK · MODEL: deepseek-v4-pro · SECURITY_SENSITIVE: YES · EGRESS_SAFE: YES · RETRY_MAX: 2
  - FILES: `resources/backend/app/modules/government/service_cierres.py`, `resources/backend/app/modules/government/api_cierres.py`
  - TEST: `test_gov_ctl10_retiro.py`
  - DONE_WHEN: pruebas de US3 en verde
- [X] T023 [US3] Añadir retirar con motivo a `resources/frontend/src/modules/gobierno/cierres/PoliticaPage.tsx`
  - EXECUTOR: DEEPSEEK · MODEL: deepseek-v4-pro · SECURITY_SENSITIVE: NO · EGRESS_SAFE: YES · RETRY_MAX: 2
  - FILES: `resources/frontend/src/modules/gobierno/cierres/PoliticaPage.tsx`
  - TEST: `npx vitest run src/modules/gobierno/cierres/PoliticaPage.test.tsx`
  - DONE_WHEN: prueba verde; MFA requerida mostrada

## Phase 6: User Story 4 - Consultar los cierres bloqueados (Priority: P2)

**Goal**: ver los bloqueos desde auditoría. **Independent Test**: provocar un bloqueo y verlo con filtros.

- [X] T024 [US4] RED: crear `resources/backend/tests/test_gov_ctl10_bloqueos.py` (listar `GOV_MATERIAL_CLOSE_BLOCKED` de la empresa, filtros acción y fechas, paginación, otra empresa no se ve, sin permiso 403) y `BloqueosPage.test.tsx`
  - EXECUTOR: DEEPSEEK · MODEL: deepseek-v4-pro · SECURITY_SENSITIVE: YES · EGRESS_SAFE: YES · RETRY_MAX: 2
  - FILES: `resources/backend/tests/test_gov_ctl10_bloqueos.py`, `resources/frontend/src/modules/gobierno/cierres/BloqueosPage.test.tsx`
  - TEST: pytest del fichero; vitest
  - DONE_WHEN: fallan contra HEAD por la razón esperada (registrado en `evidence/RED.md`)
- [X] T025 [US4] Añadir `listar_bloqueos` a `service_cierres.py` y GET `/bloqueos` a `api_cierres.py`, leídos de auditoría como los `conflictos` de CTL-01
  - EXECUTOR: DEEPSEEK · MODEL: deepseek-v4-pro · SECURITY_SENSITIVE: YES · EGRESS_SAFE: YES · RETRY_MAX: 2
  - FILES: `resources/backend/app/modules/government/service_cierres.py`, `resources/backend/app/modules/government/api_cierres.py`
  - TEST: `test_gov_ctl10_bloqueos.py`
  - DONE_WHEN: pruebas de US4 en verde
- [X] T026 [US4] Crear `resources/frontend/src/modules/gobierno/cierres/BloqueosPage.tsx` según matriz S4
  - EXECUTOR: DEEPSEEK · MODEL: deepseek-v4-pro · SECURITY_SENSITIVE: NO · EGRESS_SAFE: YES · RETRY_MAX: 2
  - FILES: `resources/frontend/src/modules/gobierno/cierres/BloqueosPage.tsx`, `resources/frontend/src/modules/gobierno/cierres/BloqueosPage.test.tsx`
  - TEST: `npx vitest run src/modules/gobierno/cierres/BloqueosPage.test.tsx`
  - DONE_WHEN: prueba verde; vacío con filtros cubierto

## Phase 7: User Story 5 - Editar un borrador y mantener sus controles (Priority: P2)

- [X] T027 [US5] RED: crear `resources/backend/tests/test_gov_ctl10_edicion.py` (PATCH con If-Match, 428 sin cabecera, 409 `GOV_CLOSURE_POLICY_STALE`, quitar control con If-Match solo en BORRADOR, historia ACTUALIZADA y CONTROL_RETIRADO, `vigente_hasta` ≥ `vigente_desde`) y ampliar `PoliticaPage.test.tsx` con edición
  - EXECUTOR: DEEPSEEK · MODEL: deepseek-v4-pro · SECURITY_SENSITIVE: YES · EGRESS_SAFE: YES · RETRY_MAX: 2
  - FILES: `resources/backend/tests/test_gov_ctl10_edicion.py`, `resources/frontend/src/modules/gobierno/cierres/PoliticaPage.test.tsx`
  - TEST: pytest del fichero; vitest
  - DONE_WHEN: fallan contra HEAD por la razón esperada (registrado en `evidence/RED.md`)
- [X] T028 [US5] Añadir `editar` y `quitar_control` a `service_cierres.py` y PATCH `/politicas/{id}` y DELETE `/politicas/{id}/controles/{control_id}` a `api_cierres.py` (If-Match sobre `version`, bloqueo de fila)
  - EXECUTOR: DEEPSEEK · MODEL: deepseek-v4-pro · SECURITY_SENSITIVE: YES · EGRESS_SAFE: YES · RETRY_MAX: 2
  - FILES: `resources/backend/app/modules/government/service_cierres.py`, `resources/backend/app/modules/government/api_cierres.py`
  - TEST: `test_gov_ctl10_edicion.py`
  - DONE_WHEN: pruebas de US5 en verde
- [X] T029 [US5] Añadir edición del borrador y quitar control a `resources/frontend/src/modules/gobierno/cierres/PoliticaPage.tsx`, con aviso de conflicto de versión
  - EXECUTOR: DEEPSEEK · MODEL: deepseek-v4-pro · SECURITY_SENSITIVE: NO · EGRESS_SAFE: YES · RETRY_MAX: 2
  - FILES: `resources/frontend/src/modules/gobierno/cierres/PoliticaPage.tsx`
  - TEST: `npx vitest run src/modules/gobierno/cierres/PoliticaPage.test.tsx`
  - DONE_WHEN: prueba verde

## Phase 8: User Story 6 - Consulta y seguridad (Priority: P3)

- [X] T030 [US6] RED: crear `resources/backend/tests/test_gov_ctl10_seguridad.py` (solo `view` sin escritura, ADMIN técnico sin acceso, otra empresa, UUID directo de otra empresa → 404, `company_id` del cliente rechazado, tipo manipulado, política inactiva/futura/vencida, bypass directo por SQL a políticas y controles, sin dinero ni PII en historia y auditoría, CTL-04 rastrea la política, SoD CTL10_ACTIVAR/RETIRAR) y `test_gov_ctl10_concurrencia.py` (dos cierres, cierre contra retirar, dos activaciones, edición vieja)
  - EXECUTOR: DEEPSEEK · MODEL: deepseek-v4-pro · SECURITY_SENSITIVE: YES · EGRESS_SAFE: YES · RETRY_MAX: 2
  - FILES: `resources/backend/tests/test_gov_ctl10_seguridad.py`, `resources/backend/tests/test_gov_ctl10_concurrencia.py`
  - TEST: pytest de ambos ficheros en PostgreSQL
  - DONE_WHEN: fallan o, si ya pasan por el diseño, se demuestran con mutante (registrado por Claude en `evidence/RED.md`)
- [X] T031 [US6] Cerrar los fallos de seguridad y concurrencia que revelen `test_gov_ctl10_seguridad.py` y `test_gov_ctl10_concurrencia.py` en `service_cierres.py` y `api_cierres.py`, sin ampliar el alcance
  - EXECUTOR: DEEPSEEK · MODEL: deepseek-v4-pro · SECURITY_SENSITIVE: YES · EGRESS_SAFE: YES · RETRY_MAX: 2
  - FILES: `resources/backend/app/modules/government/service_cierres.py`, `resources/backend/app/modules/government/api_cierres.py`
  - TEST: ambos ficheros de pruebas
  - DONE_WHEN: SC-003 y SC-005 en verde en PostgreSQL

## Phase 9: Polish & Certification

- [X] T032 Crear `resources/frontend/e2e/gobierno-cierres.spec.ts`: flujo A (cerrar la estructura de un ejercicio pasado con un hallazgo abierto → panel → cerrar el hallazgo → cierre procede), flujo B (programa con acto emitido), retirar, negativas, axe a 1280/768/320 y chromium, firefox, webkit (CIE-E2E-01..03)
  - EXECUTOR: DEEPSEEK · MODEL: deepseek-v4-pro · SECURITY_SENSITIVE: YES · EGRESS_SAFE: YES · RETRY_MAX: 2
  - FILES: `resources/frontend/e2e/gobierno-cierres.spec.ts`
  - TEST: `resources/backend/.venv/bin/python qa/e2e-run.py --con-analizador -- e2e/gobierno-cierres.spec.ts` ×3
  - DONE_WHEN: E2E verde en los tres navegadores con 0 reintentos
- [X] T033 Ampliar `resources/frontend/e2e/uat-humo-gobierno.spec.ts` con la entrada de menú «Controles de cierre» y el humo sin login MFA
  - EXECUTOR: DEEPSEEK · MODEL: deepseek-v4-flash · SECURITY_SENSITIVE: NO · EGRESS_SAFE: YES · RETRY_MAX: 2
  - FILES: `resources/frontend/e2e/uat-humo-gobierno.spec.ts`
  - TEST: humo separado de la canónica (OD-QA-UAT-01)
  - DONE_WHEN: humo verde
- [X] T034 Crear `qa/gobierno_integridad_cierres.py` (una VIGENTE por empresa+acción, controles de política BORRADOR/VIGENTE/RETIRADA coherentes, historia sin huecos, empresa cruzada) y registrarlo en `qa/gobierno_integridad.py` con su prueba
  - EXECUTOR: DEEPSEEK · MODEL: deepseek-v4-flash · SECURITY_SENSITIVE: YES · EGRESS_SAFE: YES · RETRY_MAX: 2
  - FILES: `qa/gobierno_integridad_cierres.py`, `qa/gobierno_integridad.py`
  - TEST: su prueba y `qa/gobierno_integridad.py`
  - DONE_WHEN: integridad versionada verde tras la E2E
- [X] T035 Regenerar el espejo del catálogo de auditoría y los fixtures de frontend afectados; verificar que no queda diferencia
  - EXECUTOR: CLAUDE · MODEL: n-a · SECURITY_SENSITIVE: NO · EGRESS_SAFE: YES · RETRY_MAX: 2
  - FILES: `specs/001-fundacion/evidence/audit-catalog/catalogo.md`, `resources/frontend/src/`
  - TEST: `git diff --stat` y pruebas de catálogo
  - DONE_WHEN: sin diferencias pendientes
- [X] T036 Registrar en `evidence/RED.md` y `evidence/ATTEMPT_LOG.md` cada RED demostrado contra `HEAD` antes del código de producto de su historia, y los intentos de DeepSeek
  - EXECUTOR: CLAUDE · MODEL: n-a · SECURITY_SENSITIVE: NO · EGRESS_SAFE: YES · RETRY_MAX: 2
  - FILES: `specs/gov-ctl-10-controles-cierre/evidence/RED.md`, `specs/gov-ctl-10-controles-cierre/evidence/ATTEMPT_LOG.md`
  - TEST: lectura de las trazas de pytest y vitest
  - DONE_WHEN: un RED por cada tarea RED
- [X] T037 Diseñar y ejecutar las mutaciones (guarda ausente, ámbito de empresa, vigencia futura/vencida, pendiente contado, `riesgo_minimo`, ejercicio de actos, inmutabilidad, auditoría omitida, resultado invertido, orden respecto de SoD) y escribir `evidence/MUTATIONS.md`; purgar `__pycache__` entre mutantes
  - EXECUTOR: CLAUDE · MODEL: n-a · SECURITY_SENSITIVE: YES · EGRESS_SAFE: YES · RETRY_MAX: 2
  - FILES: `specs/gov-ctl-10-controles-cierre/evidence/MUTATIONS.md`
  - TEST: familia completa de pruebas CTL-10 contra cada mutante
  - DONE_WHEN: todo mutante válido muerto o justificado
- [X] T038 Certificación completa: PostgreSQL, SQLite, vitest, tsc, eslint, build, ruff, mypy, OpenAPI, regresión de Gobierno ×3, canónica, integridad post-E2E
  - EXECUTOR: CLAUDE · MODEL: n-a · SECURITY_SENSITIVE: NO · EGRESS_SAFE: YES · RETRY_MAX: 2
  - FILES: `specs/gov-ctl-10-controles-cierre/evidence/REQUIRED_SUITE_INVENTORY.md`
  - TEST: órdenes canónicas del repositorio
  - DONE_WHEN: todo verde sobre el árbol final
- [X] T039 Reclasificar CTL-10 y recalcular las tres métricas en `docs/roadmap/government-product-completeness/`
  - EXECUTOR: CLAUDE · MODEL: n-a · SECURITY_SENSITIVE: NO · EGRESS_SAFE: YES · RETRY_MAX: 2
  - FILES: `docs/roadmap/government-product-completeness/`
  - TEST: revisión de las matrices
  - DONE_WHEN: métricas coherentes; TRE-08 sigue BLOCKED
- [X] T040 Escribir `evidence/OWNER_UAT_CARD.md` (escenario de `CTL10_SCREEN_FORM_MATRIX.md`) y `evidence/UAT_SMOKE.md`
  - EXECUTOR: CLAUDE · MODEL: n-a · SECURITY_SENSITIVE: NO · EGRESS_SAFE: YES · RETRY_MAX: 2
  - FILES: `specs/gov-ctl-10-controles-cierre/evidence/OWNER_UAT_CARD.md`, `specs/gov-ctl-10-controles-cierre/evidence/UAT_SMOKE.md`
  - TEST: humo contra la pila UAT
  - DONE_WHEN: OWNER_UAT_READY solo con READY y ACCESSIBLE
- [X] T041 `/speckit-converge`, commit y push a `origin/develop` con `git status` vacío; relevo UAT
  - EXECUTOR: CLAUDE · MODEL: n-a · SECURITY_SENSITIVE: NO · EGRESS_SAFE: YES · RETRY_MAX: 2
  - FILES: `specs/gov-ctl-10-controles-cierre/`
  - TEST: `git status` y `git log origin/develop`
  - DONE_WHEN: HEAD == origin/develop, árbol limpio, solo ficheros del ciclo

## Dependencies

Phase 1 → Phase 2 → US1 → US2 (necesita US1: políticas) → US3 → (US4, US5) → US6 → Phase 9. Las tareas [P] tocan ficheros distintos. Los RED de cada historia preceden a su código. La integración en `service_estructura.py` y `service_caja.py` (tarea de US2) es la única edición de lógica ajena y se limita a la llamada.

## Parallel Example

T007 y T008 a la vez tras T005; PoliticasPage y NuevaPoliticaPage de US1 a la vez.

## Implementation Strategy

Corte vertical: US1 y US2 forman el MVP (política activa que bloquea un cierre real, con su panel). Cada tarea se prueba al aplicarse; no se apila trabajo sobre una tarea rota.

## Phase 10: Convergence

- [ ] T042 Decidir y resolver que el enlace `ruta_lista` lleve a la lista filtrada, que hoy abre la lista completa sin filtro, per spec Edge Cases «más de 5 pendientes» (partial). OBS-CTL10-LISTA-01, LOW: exige leer filtros de la URL en las listas de CTL-06 y DOC-02, o ajustar la spec; decisión de la dueña
- [ ] T043 Añadir a `resources/backend/tests/test_gov_ctl10_guarda.py` una prueba con más de 5 hallazgos pendientes: la muestra trae 5 y `pendientes` el recuento real, per FR-013 (partial)
