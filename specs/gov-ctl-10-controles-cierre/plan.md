# Implementation Plan: CTL-10 Controles materiales previos al cierre

**Branch**: `develop` (rama única) | **Date**: 2026-11-06 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/gov-ctl-10-controles-cierre/spec.md`. Diseño cerrado: `/home/maria/.cache/kontrol-qa/herramientas/ctl10/DISENO.md`.

## Summary

Control Interno define políticas de cierre por acción (cerrar la estructura de ORG-02, cerrar el programa de TRE-02) con dos tipos de control fijos (hallazgos abiertos, actos emitidos sin eficacia). Una guarda única, `evaluar_cierre`, se invoca dentro de los dos servicios de cierre después de estado y SoD: con política efectiva y pendientes bloquea con 409 y auditoría; sin ellos audita el paso. Incluye pantallas de gestión, «Cierres bloqueados» y el panel `BloqueoDeCierre` en las páginas de estructura y programa. Proceso nuevo dentro del módulo Gobierno; sin motor genérico.

## Technical Context

**Language/Version**: Python 3.11; TypeScript estricto

**Primary Dependencies**: FastAPI, SQLAlchemy 2, Alembic, React 18, TanStack Query

**Storage**: PostgreSQL; tres tablas nuevas `gov_*` (ver data-model.md); migración `0075_gov_ctl10_cierres` sobre `0074_gov_tre02_caja`

**Testing**: pytest (mundo multiempresa en PostgreSQL y SQLite), vitest, Playwright ×3, mutaciones, `qa/gobierno_integridad.py`

**Target Platform**: instalación independiente por cliente

**Project Type**: aplicación web, módulo existente

**Performance Goals**: pendientes contados con consultas agregadas por tipo, sin N+1; muestra limitada a 5

**Constraints**: fechas civiles de Caracas; instantes UTC; sin expresiones ni SQL de usuario; sin dinero en historia; solo añadidos de registro en ficheros compartidos (OD-CTL10-01)

**Scale/Scope**: 2 acciones de cierre, 2 tipos de control, 10 endpoints, 4 pantallas más un panel

### Decisiones de arquitectura

| Id | Decisión | Razón |
|---|---|---|
| AD-CTL10-01 | `service_cierres.py`, `schemas_cierres.py`, `api_cierres.py` en `government`, bajo `/gobierno/cierres` | Mismo patrón que CTL-01 y TRE-02 |
| AD-CTL10-02 | Guarda única `evaluar_cierre(db, ctx, accion, objeto_tipo, objeto_id, objeto_codigo, ejercicio)` llamada desde `service_estructura.cerrar` y `service_caja.cerrar` | Un solo punto; sin motor genérico |
| AD-CTL10-03 | Orden: autenticación → permiso → ámbito → estado → SoD → CTL-10 → mutación → auditoría, con la fila del objeto ya bloqueada | El bloqueo no oculta errores de estado ni de SoD |
| AD-CTL10-04 | Política efectiva leída con FOR SHARE | Serializa cierre contra retirar |
| AD-CTL10-05 | Tipos como catálogo cerrado en código, con CHECK en base; cada tipo es una consulta fija | Sin expresiones (OD-CTL10-03) |
| AD-CTL10-06 | Inmutabilidad por disparador en PostgreSQL (política activa/retirada, controles fuera de BORRADOR, historia) | Principio 5 y 25 |
| AD-CTL10-07 | Unicidad por índice parcial: una VIGENTE por empresa y acción | Principio 25 |
| AD-CTL10-08 | Bloqueos leídos de auditoría como `conflictos` de CTL-01; sin tabla propia | Una sola fuente de verdad |
| AD-CTL10-09 | Capacidad `gobierno_cierre` view, manage (STANDARD), activate (SENSITIVE) | OD-CTL10-04 |
| AD-CTL10-10 | Pantallas en `modules/gobierno/cierres/`; panel `BloqueoDeCierre` bajo `modules/gobierno/`; en EstructuraPage y ProgramaPage solo se monta el panel ante el 409 | OD-CTL10-01 y regla de ficheros |
| AD-CTL10-11 | Migración solo tablas `gov_*` y el proceso CTL-10 en el catálogo SoD | OD-CTL10-01 |

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Estado |
|---|---|
| P1 Spec antes que código · P2 Autorización expresa · P3 Trazabilidad | PASS: el encargo nombra CTL-10; decisiones OD-CTL10-01..04 |
| P4 Núcleo fiscal separado | PASS: sin fiscal, presupuesto ni contabilidad |
| P5 Datos históricos protegidos | PASS: disparadores, historia inmutable |
| P6 Seguridad en backend · P7 Frontend uniforme · P11 Accesibilidad | PASS |
| P8 No hardcodear reglas · P19 Reglas con fuente | PASS: la política es dato configurable por Control Interno; catálogo cerrado de tipos citando N20 y N21 |
| P20 No sustitución de organismos oficiales | PASS |
| P13 Integridad transaccional · P25 Altas concurrentes · P26 Paridad modelo y migración | PASS por diseño; se verifica en pruebas |
| P21 Paridad del motor | PASS: pruebas en PG y SQLite |
| P22 Autoridad única por capacidad transversal | PASS: la guarda de cierre es una sola función |
| P24 Instalación limpia | Se demuestra migrando desde cero |
| P27 Mutaciones | Se aplican en la fase de certificación |

### CONSTITUTION GATE

| Compuerta | Valor exigido |
|---|---|
| CTL10_REQUIREMENTS_COMPLETE | 1 |
| CTL10_FULL_PROCESS_IMPLEMENTABLE | 1 |
| CURRENT_CLOSE_ACTION_INVENTORY_COMPLETE | 1 |
| INITIAL_INTEGRATED_CLOSE_ACTIONS | 2 |
| POLICY_CONTRACT_COMPLETE | 1 |
| CONTROL_TYPE_CONTRACT_COMPLETE | 1 |
| CONTROL_TYPES_REAL_DATA_BACKED | 1 |
| ACCOUNTING_DEPENDENCY_REQUIRED | 0 |
| BUDGET_DEPENDENCY_REQUIRED | 0 |
| ORG06_DEPENDENCY_REQUIRED | 0 |
| SHARED_CORE_CHANGE_REQUIRED | 0 (solo añadidos de registro autorizados por OD-CTL10-01 y la llamada a la guarda en los dos cierres integrados) |
| GENERIC_RULE_ENGINE_REQUIRED | 0 |
| ROLE_MATRIX_COMPLETE · MENU_DEFINED · SCREEN_FORM_MATRIX_COMPLETE | 1 · 1 · 1 |
| AUDIT_CONTRACT_COMPLETE · SECURITY_CONTRACT_COMPLETE · OWNER_UAT_SCENARIO_DEFINED | 1 · 1 · 1 |
| MATERIAL_BLOCKER · MATERIAL_OQ · UNKNOWN · CONTRADICTIONS | 0 · 0 · 0 · 0 |

**Nota sobre el valor de SHARED_CORE_CHANGE_REQUIRED**: la llamada a `evaluar_cierre` dentro de `service_estructura.cerrar` y `service_caja.cerrar` es una inserción en dos funciones de proceso (no del núcleo compartido); el valor 0 queda condicionado a que no cambie ninguna lógica previa de esas funciones (verificado por regresión de ORG-02 y TRE-02 sin cambios de contrato, FR-016, FR-026).

**GATE = PASS** antes y después del diseño de la Fase 1.

### Matriz de roles

| Capacidad | Rol | view | manage | activate (MFA) |
|---|---|---|---|---|
| `gobierno_cierre` | FUNCIONAL_COMPLETO (Control Interno) | sí | sí | sí |
| `gobierno_cierre` | Solo consulta (permiso asignado) | sí | no | no |
| `gobierno_cierre` | ADMIN técnico | no | no | no |

## Project Structure

### Documentation (this feature)

```text
specs/gov-ctl-10-controles-cierre/
├── plan.md · research.md · data-model.md · quickstart.md · tasks.md
├── contracts/api.md
├── checklists/requirements.md
└── evidence/ (CTL10_SCREEN_FORM_MATRIX, CTL10_CLOSE_ACTION_INTEGRATION_MATRIX, ANALYZE_REPORT; luego RED, ATTEMPT_LOG, MUTATIONS, OWNER_UAT_CARD, REQUIRED_SUITE_INVENTORY, UAT_SMOKE)
```

### Source Code (repository root)

```text
resources/backend/app/modules/government/{models,service_cierres,schemas_cierres,api_cierres}.py
resources/backend/app/modules/government/{service_estructura,service_caja,service_sod,service_auditoria,schemas_sod}.py   (llamada a la guarda y registro)
resources/backend/app/{shared/audit_catalog_entries.py,main.py}
resources/backend/app/modules/{identity_access/mfa_policy.py,setup/api.py}
resources/backend/alembic/versions/0075_gov_ctl10_cierres.py
resources/backend/tests/test_gov_ctl10_*.py
resources/frontend/src/modules/gobierno/cierres/
resources/frontend/src/modules/gobierno/{api.ts,estructura/EstructuraPage.tsx,tesoreria/programacion/ProgramaPage.tsx}
resources/frontend/src/app/{router.tsx,autoridad/pantallas.ts}  resources/frontend/src/layout/Sidebar.tsx
resources/frontend/e2e/gobierno-cierres.spec.ts
qa/gobierno_integridad_cierres.py
```

**Structure Decision**: extender el módulo `government` existente, sin módulo nuevo.

## Complexity Tracking

Sin violaciones de la Constitución que justificar.
