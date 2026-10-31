# Plan · GOV-0-02 Estructura organizativa por ejercicio

## Decisiones

| Tipo | Id | Decisión |
|---|---|---|
| OWNER | OD-ORG02-01..04 | Ejercicio = año calendario; BORRADOR → VIGENTE → CERRADA; acto obligatorio para VIGENTE; listado + CSV (spec §2) |
| ARCHITECTURE | AD-ORG02-01 | Mismo módulo `app/modules/government/`; tablas `gov_structures`, `gov_units`, `gov_unit_versions`. No reutiliza la organización privada (empresas, sucursales, Spec 057) |
| ARCHITECTURE | AD-ORG02-02 | La estructura pertenece al `GovernmentEntity` del contenedor (FK `entity_id` + `company_id`); toda consulta filtra por `ctx.company_id` |
| ARCHITECTURE | AD-ORG02-03 | Integridad de jerarquía en dos capas: BD (FK compuesta a la misma estructura, CHECK sin autorreferencia) y backend (sin ciclos, padre ACTIVO, subordinadas) |
| ARCHITECTURE | AD-ORG02-04 | Concurrencia: `If-Match` por estructura (poner en vigor, cerrar) y por unidad (editar, desactivar, eliminar); toda escritura de unidad bloquea la fila de la estructura (`FOR UPDATE`) para serializarse con poner en vigor/cerrar y con los cambios de jerarquía |
| ARCHITECTURE | AD-ORG02-05 | Guardas: `require_permission` → `get_company_context` → `require_module("gobierno")` como **último** parámetro (lección de ORG-01) |
| PROJECT_DESIGN | PDD-ORG02-01 | Capacidades `gobierno_estructura:view/edit/publish/close`, funcionales (FUNCIONAL_COMPLETO; no ADMIN) |
| PROJECT_DESIGN | PDD-ORG02-02 | MFA: `view` ESTÁNDAR; `edit/publish/close` SENSIBLES |
| PROJECT_DESIGN | PDD-ORG02-03 | Abrir estructura exige el ente configurado; ponerla en vigor exige el ente ACTIVO |
| PROJECT_DESIGN | PDD-ORG02-04 | Sin niveles fijos por tipo ni orden manual: la norma no los fija; la lista se ordena por código |
| PROJECT_DESIGN | PDD-ORG02-05 | GOV0-UI-01: la compuerta de contexto dice «ente» solo en rutas `/gobierno/*` con el módulo habilitado |
| PROJECT_DESIGN | PDD-ORG02-06 | El árbol se presenta como una tabla jerárquica sangrada (código, denominación, tipo, superior, vigencia, estado, acciones) con nivel anunciado al lector de pantalla: todas las acciones son botones accesibles; no se usa un organigrama gráfico |

## Constitution gate

| Puerta | Valor |
|---|---|
| ORG02_REQUIREMENTS_COMPLETE · PROCESS_MODEL · EXERCISE_CONTRACT · STRUCTURE_MODEL · HIERARCHY_RULES | 1 (spec §2–§5) |
| MENU_DEFINED · SCREEN_FORM_MATRIX · FIELD_CONTRACT · ROLE_MATRIX | 1 (spec §6, §9, §10; matriz en `evidence/SCREEN_FORM_COMPLETENESS.md`) |
| DOCUMENT_CONTRACT · REPORT_CONTRACT · AUDIT_CONTRACT · ERROR_CONTRACT | 1 (spec §8–§9) |
| OWNER_UAT_SCENARIO_DEFINED | 1 (spec §11) |
| MATERIAL_BLOCKER · MATERIAL_OQ · UNKNOWN · CONTRADICTIONS | 0 (las cuatro preguntas materiales las respondió la dueña el 2026-10-30) |

Contradicción resuelta: la matriz retrospectiva contaba la compuerta REPORTS como aplicable aunque el IR §12 no lista reporte de estructura; OD-ORG02-04 la confirma aplicable (listado + CSV). No cambia el denominador.

## Puntos de contacto

| Capa | Ficheros |
|---|---|
| Backend | `app/modules/government/{models,schemas_estructura,service_estructura,api_estructura}.py`; registro del router; `setup/api.py` (catálogo de permisos); `audit_catalog_entries.py` + espejo `catalogo.md`; `documents/resources.py` (`GovernmentStructure`); `identity_access/mfa_policy.py` |
| Migración | `alembic/versions/0064_gov0_estructuras.py` |
| Frontend | `src/modules/gobierno/api.ts` (contrato), `src/modules/gobierno/estructura/*` (páginas y componentes), router, `pantallas.ts`, Sidebar, `components/company/EstadoDeEmpresa.tsx` (GOV0-UI-01) |
| Pruebas | `tests/test_gov0_estructura.py`; guardas (CATB-03, DC-T01, MFA-G00b, N9 + semilla, cabeza Alembic); vitest de la pantalla y del formulario; `e2e/gobierno-estructura.spec.ts` + regresión de ORG-01 |

## Lecciones de ORG-01 incorporadas a los encargos

- Licencia en pruebas: `LicenseEntitlementSnapshot` (un `LicenseState` sin firma suspende escrituras).
- Documento sembrado: con `DocumentType` (`document_type_id` NOT NULL).
- Casos de validación: cada uno con los demás campos válidos y el campo rechazado comprobado en `field_errors`.
- Rótulos de campo obligatorio: regex `/^Rótulo/` (llevan « *» y « (obligatorio)»).
- E2E: cerrar notificaciones persistentes antes de pulsar acciones de la cabecera; tres navegadores con `--project=firefox --project=webkit`.
- Guardas cerradas que deben declararse en el mismo corte.
