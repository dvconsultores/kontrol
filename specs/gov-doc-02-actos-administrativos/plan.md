# Plan · GOV-DOC-02 Actos administrativos

## Decisiones

| Tipo | Id | Decisión |
|---|---|---|
| OWNER | OD-DOC02-01..04 | Registrar actos suscritos; tipos de la LOPA; cargo + competencia + fundamento, firmante y titularidad transcritos; requisito y cumplimiento de eficacia (spec §2) |
| ARCHITECTURE | AD-DOC02-01 | Mismo módulo `app/modules/government/`; ficheros nuevos `schemas_actos.py`, `service_actos.py`, `api_actos.py`; tablas `gov_acts`, `gov_act_versions` |
| ARCHITECTURE | AD-DOC02-02 | Integridad: FK simples a `companies`, `gov_positions`, `documents` y `gov_acts` (la guarda `test_company_id_always_references_company` prohíbe FK compuestas con `company_id`); la empresa del cargo, del documento y del acto de referencia la impone el servicio (misma empresa o 404/422) |
| ARCHITECTURE | AD-DOC02-03 | Competencia como instantánea (acción, materia) validada contra las competencias actuales del cargo, sin FK: ORG-03 no cambia (retirar competencias sigue permitido) |
| ARCHITECTURE | AD-DOC02-04 | Concurrencia: `If-Match` con la versión del acto en toda escritura; `FOR UPDATE` sobre el acto (y sobre el de referencia en revocar/anular); duplicado de número por UNIQUE en BD traducido a 409 (`IntegrityError` → `GOV_ACT_NUMBER_DUPLICATE`) |
| ARCHITECTURE | AD-DOC02-05 | Documentos por la 046: `ResourceKind("GovernmentAct")`; `documento_acto_id`/`documento_eficacia_id` elegidos entre los vinculados; `documents.service.freeze_links` al emitir y al registrar eficacia |
| ARCHITECTURE | AD-DOC02-06 | Guardas: `require_permission` → `get_company_context` → `require_module("gobierno")` como último parámetro; rutas `exportar` y `autoridades` antes de `{acto_id}`; `anio` y `fecha` como parámetros de consulta declarados (contrato global estricto) |
| PROJECT_DESIGN | PDD-DOC02-01 | Capacidades `gobierno_actos:view/edit/issue/annul`, funcionales (FUNCIONAL_COMPLETO; no ADMIN) |
| PROJECT_DESIGN | PDD-DOC02-02 | MFA: `view` ESTÁNDAR; `edit`, `issue`, `annul` SENSIBLES |
| PROJECT_DESIGN | PDD-DOC02-03 | Unicidad del número por (cargo, tipo, denominación, número) normalizados: impide el doble registro sin imponer una numeración legal que la LOPA no fija |
| PROJECT_DESIGN | PDD-DOC02-04 | `INTERNO` = asuntos internos de la administración (art. 72) y actos particulares que no afectan derechos de terceros: sin publicación ni notificación |
| PROJECT_DESIGN | PDD-DOC02-05 | La decisión es obligatoria para emitir (art. 18.6 dice «si fuere el caso»: en un registro, una circular o instrucción pone su contenido ahí) |
| PROJECT_DESIGN | PDD-DOC02-06 | La competencia se valida contra las competencias **actuales** del cargo; registrar un acto antiguo cuya competencia ya se retiró no es posible (deuda LOW documentada) |
| PROJECT_DESIGN | PDD-DOC02-07 | UI en dos pantallas (registro del año y acto) con formularios en panel y diálogos de confirmación; fechas con `formatearFechaDeNegocio` (ADR-020); etiqueta de menú «Actos administrativos» |
| PROJECT_DESIGN | PDD-DOC02-08 | Las capacidades de actos no exigen `gobierno_cargos:view`: las autoridades elegibles se leen por `/gobierno/actos/autoridades` |

## Constitution gate

| Puerta | Valor |
|---|---|
| CURRENT_BRANCH = develop · DEFAULT_BRANCH = develop · REMOTE_BRANCH_COUNT = 1 · HEAD_EQUALS_ORIGIN | 1 (`f462cc3`) |
| UAT_AUTHENTICATED_SMOKE_COMPLETE | 1 (HUMO-UAT-01 sobre la pila persistente `8ea3a92`; `evidence/UAT_SMOKE.md`) |
| DOC02_REQUIREMENTS_COMPLETE · CURRENT_STATE_MATRIX_COMPLETE · DOC02_PROCESS_MODEL_COMPLETE | 1 · 1 · 1 |
| ACT · AUTHORITY · COMPETENCY · MOTIVATION · TEMPORAL · DOCUMENT _CONTRACT_COMPLETE | 1 (spec §4) |
| NOTIFICATION_BOUNDARY · EXPEDIENTE_BOUNDARY | 1 · 1 (spec §4.8) |
| NUMBERING_CONTRACT_COMPLETE | 1 (externo, OD-DOC02-01; unicidad PDD-DOC02-03) |
| MENU · SCREEN_FORM · FIELD · ROLE · REPORT · AUDIT · ERROR | 1 (spec §5, §7–§9; `evidence/SCREEN_FORM_COMPLETENESS.md`) |
| OWNER_UAT_SUCCESS_SCENARIO_DEFINED | 1 (spec §10) |
| MATERIAL_BLOCKER · MATERIAL_OQ · UNKNOWN · CONTRADICTIONS | 0 (las cuatro decisiones materiales las tomó la dueña el 2026-11-01) |
| DOC02_FULL_PROCESS_IMPLEMENTABLE | 1 |

Contradicciones revisadas: (1) GOV-ORG-009 (catálogo de actos por ente) vive en ORG-04: resuelto por OD-DOC02-02. (2) GOV-DOC-005
(notificación con constancia) frente a «notificación» de GOV-DOC-003: resuelto por OD-DOC02-04. (3) LOPA art. 18.8 (funcionario y
delegación) frente a ORG-04/ORG-06 bloqueados: resuelto por OD-DOC02-03. (4) Firma autógrafa (art. 18) frente a DOC-05 bloqueado:
resuelto por OD-DOC02-01.

## Puntos de contacto

| Capa | Ficheros |
|---|---|
| Backend | `app/modules/government/{models,schemas_actos,service_actos,api_actos}.py`; `app/main.py`; `setup/api.py`; `shared/audit_catalog_entries.py` + espejo del catálogo; `documents/resources.py`; `identity_access/mfa_policy.py` |
| Migración | `alembic/versions/0066_gov_doc02_actos.py` |
| Frontend | `src/modules/gobierno/api.ts`, `src/modules/gobierno/actos/*`, `src/app/router.tsx`, `src/app/autoridad/pantallas.ts`, `src/layout/Sidebar.tsx`, fixtures (herramienta) |
| Pruebas | `tests/test_gov_doc02_actos.py`; guardas (cabeza, catálogo, N9 + semilla, MFA, techo de delegación, permisos de instalación); vitest; `e2e/gobierno-actos.spec.ts`; regresión ORG-01/02/03 y HUMO-UAT-01 |
