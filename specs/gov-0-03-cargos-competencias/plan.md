# Plan · GOV-0-03 Cargos con competencias y límites de firma/aprobación

## Decisiones

| Tipo | Id | Decisión |
|---|---|---|
| OWNER | OD-ORG03-01..04 | Cargo por ejercicio en una unidad (copia con la estructura); competencia acción × materia; límite sin límite o monto + moneda (VES/USD/EUR); acto por cargo (spec §2) |
| ARCHITECTURE | AD-ORG03-01 | Mismo módulo `app/modules/government/`; ficheros nuevos `schemas_cargos.py`, `service_cargos.py`, `api_cargos.py`; tablas `gov_positions`, `gov_position_competencies`, `gov_position_versions`. No reutiliza `identity_access.roles` (cargo ≠ rol de seguridad) |
| ARCHITECTURE | AD-ORG03-02 | El cargo pertenece a la estructura (FK `structure_id` + `company_id`) y a una unidad de la misma estructura (FK compuesta a `gov_units(structure_id, id)`); la competencia, a su cargo (FK simple `position_id → gov_positions.id`) y su `company_id` solo a `companies`, como exige la guarda de arquitectura (enmienda del 2026-11-01: la FK compuesta inicial a `gov_positions(id, company_id)` violaba `test_company_id_always_references_company`); la empresa de la competencia la impone el servicio (se crea con la del cargo y toda lectura filtra por ella) |
| ARCHITECTURE | AD-ORG03-03 | Concurrencia: `If-Match` con la versión del **cargo** en toda escritura sobre él o sus competencias; toda escritura bloquea la fila de la estructura (`FOR UPDATE`), como ORG-02, para serializarse con cerrar la estructura, desactivar/eliminar unidades y copiar |
| ARCHITECTURE | AD-ORG03-04 | Guardas: `require_permission` → `get_company_context` → `require_module("gobierno")` como **último** parámetro. Para competencias, la API además calcula `puede_publicar` (`identity_service.user_has_permission(user, get_user_permissions(db, user), "gobierno_cargos", "publish")`) y el servicio exige `publish` si el cargo está VIGENTE (403 `GOV_POSITION_AUTHORITY_REQUIRED`) |
| ARCHITECTURE | AD-ORG03-05 | Dinero: `Numeric(18,2)`; entrada con `app.shared.money.texto_decimal(..., positivo=True)` (solo texto), salida con texto de 2 decimales; nunca `float` (RNF-GOV-002) |
| ARCHITECTURE | AD-ORG03-06 | Rutas bajo `/gobierno/estructuras/{ejercicio}/cargos` en un router propio; `exportar` se declara **antes** de `{cargo_id}` |
| PROJECT_DESIGN | PDD-ORG03-01 | Capacidades `gobierno_cargos:view/edit/publish`, funcionales (FUNCIONAL_COMPLETO; no ADMIN, GOV-CTL-004) |
| PROJECT_DESIGN | PDD-ORG03-02 | MFA: `view` ESTÁNDAR; `edit` y `publish` SENSIBLES |
| PROJECT_DESIGN | PDD-ORG03-03 | Separación preparación / autoridad (N20): `edit` prepara borradores y cambia datos descriptivos; poner en vigor, desactivar y todo cambio de competencias de un cargo VIGENTE exige `publish` |
| PROJECT_DESIGN | PDD-ORG03-04 | Un cargo VIGENTE conserva al menos una competencia (409 `GOV_COMPETENCY_LAST`): para dejarlo sin autoridad se desactiva |
| PROJECT_DESIGN | PDD-ORG03-05 | Eliminar un cargo BORRADOR con acto vinculado se rechaza (409 `GOV_POSITION_HAS_DOCUMENTS`): el acto se desvincula en el panel 046; Gobierno no escribe tablas de documentos |
| PROJECT_DESIGN | PDD-ORG03-06 | Interacción con ORG-02: copiar estructura copia cargos VIGENTES en BORRADOR (sin acto); desactivar o eliminar unidad con cargos no inactivos/cualesquiera → 409 `GOV_UNIT_HAS_POSITIONS` |
| PROJECT_DESIGN | PDD-ORG03-07 | UI en tres pantallas (ejercicios, cargos del ejercicio, cargo); el límite se muestra en lenguaje de negocio («Hasta 50.000,00 USD por operación» / «Sin límite») con `formatMoney`; fechas civiles con `formatearFechaDeNegocio` (ADR-020) |
| PROJECT_DESIGN | PDD-ORG03-08 | Etiqueta de menú «Cargos y competencias» (vocabulario del IR: cargo, competencias) |
| PROJECT_DESIGN | PDD-ORG03-09 | Las pantallas de cargos leen la estructura del ejercicio (unidades y estado): todo rol que consulte o prepare cargos incluye `gobierno_estructura:view` (FUNCIONAL_COMPLETO ya la tiene). El cargo vive en la estructura (OD-ORG03-01) |

## Constitution gate

| Puerta | Valor |
|---|---|
| SINGLE_BRANCH_POLICY_PASS · REMOTE_BRANCH_COUNT = 1 · DEFAULT_BRANCH = develop · CURRENT_BRANCH = develop · HEAD_EQUALS_ORIGIN_DEVELOP | 1 (2026-11-01: `feature/001-fundacion` con 0 commits propios, eliminada; `git-governance.md` §0) |
| ORG03_REQUIREMENTS_COMPLETE · PROCESS_MODEL · CARGO_CONTRACT · COMPETENCY_CONTRACT · LIMIT_CONTRACT · AUTHORITY_MODEL · STRUCTURE_DEPENDENCY · HISTORICAL_INTEGRITY | 1 (spec §2–§5) |
| MENU_DEFINED · SCREEN_FORM_MATRIX · FIELD_CONTRACT · ROLE_MATRIX | 1 (spec §6, §9, §10; matriz en `evidence/SCREEN_FORM_COMPLETENESS.md`) |
| DOCUMENT_CONTRACT · REPORT_CONTRACT · AUDIT_CONTRACT · ERROR_CONTRACT | 1 (spec §8–§9) |
| OWNER_UAT_SUCCESS_SCENARIO_DEFINED | 1 (spec §11) |
| MATERIAL_BLOCKER · MATERIAL_OQ · UNKNOWN · CONTRADICTIONS | 0 (las cuatro preguntas materiales las respondió la dueña el 2026-11-01) |

Contradicciones revisadas: (1) la arquitectura agrupa GOV-ORG-003/004 en «AUTORIDAD»; la matriz canónica separa ORG-03 de ORG-04 y esta Spec no implementa delegación. (2) GOV-ORG-010 da el vocabulario de acciones pero la matriz es ORG-07: se usa el catálogo, no se construye la matriz. Ninguna cambia el denominador.

## Puntos de contacto

| Capa | Ficheros |
|---|---|
| Backend | `app/modules/government/{models,schemas_cargos,service_cargos,api_cargos,service_estructura}.py`; `app/main.py` (router); `setup/api.py` (catálogo de permisos); `shared/audit_catalog_entries.py` + espejo `specs/…/evidence/audit-catalog/catalogo.md`; `documents/resources.py` (`GovernmentPosition`); `identity_access/mfa_policy.py` |
| Migración | `alembic/versions/0065_gov0_cargos.py` |
| Frontend | `src/modules/gobierno/api.ts`, `src/modules/gobierno/cargos/*`, `src/app/router.tsx`, `src/app/autoridad/pantallas.ts`, `src/layout/Sidebar.tsx`, fixtures `openapi-routes.json` / `operaciones.json` (herramienta) |
| Pruebas | `tests/test_gov0_cargos.py`; guardas (cabeza Alembic, catálogo de auditoría, N9 + semilla, MFA, barridos de aislamiento, techo de delegación, permisos de instalación); regresión `tests/test_gov0_estructura.py`; vitest de pantallas y formularios; `e2e/gobierno-cargos.spec.ts` + regresión ORG-01/02 |

## Lecciones incorporadas a los encargos

- ORG-01/02: licencia en pruebas por `LicenseEntitlementSnapshot`; documento con `DocumentType`; un caso de validación por campo con los demás válidos; rótulos obligatorios por regex; cerrar notificaciones antes de pulsar cabeceras; tres navegadores; guardas cerradas en el mismo corte.
- ORG-02 (E2E real): fechas civiles con `formatearFechaDeNegocio`; el arnés sella con `app.core.clock.now()`; contenedores con desplazamiento horizontal llevan `relative`; consultas de licencia bajo `["licencia", …]`; correr la E2E en chromium antes de gastar el último reintento.
