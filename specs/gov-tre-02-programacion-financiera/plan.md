# Implementation Plan: TRE-02 Programación financiera y disponibilidad de caja

**Branch**: `develop` (rama única) | **Date**: 2026-11-05 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/gov-tre-02-programacion-financiera/spec.md`

## Summary

Tesorería programa por ejercicio, mes y moneda: declara la disponibilidad por cuenta, registra ingresos y desembolsos por rubro, y el sistema calcula la disponibilidad mensual. Activa con MFA, reprograma por versiones y cierra. Es un proceso nuevo dentro del módulo Gobierno, separado de cualquier presupuesto. Incluye el delta OBS-TRE01-E2E-01 y la reclasificación de reportes de TRE-01.

## Technical Context

**Language/Version**: Python 3.11; TypeScript estricto

**Primary Dependencies**: FastAPI, SQLAlchemy 2, Alembic, React 18, TanStack Query

**Storage**: PostgreSQL; cinco tablas nuevas más la historia (ver data-model.md); migración `0074_gov_tre02_caja`

**Testing**: pytest (mundo multiempresa en PostgreSQL), vitest, Playwright ×3, mutaciones, `qa/gobierno_integridad.py`

**Target Platform**: instalación independiente por cliente

**Project Type**: aplicación web, módulo existente

**Performance Goals**: el detalle se calcula con consultas en bloque, sin N+1

**Constraints**: importes Decimal; fechas civiles de Caracas; instantes UTC; sin conversión de moneda; sin saldos inventados

**Scale/Scope**: 12 meses, 2 tipos de rubro, 16 operaciones, 4 pantallas

### Decisiones de arquitectura

| Id | Decisión | Razón |
|---|---|---|
| AD-TRE02-01 | `service_caja.py`, `schemas_caja.py`, `api_caja.py` en `government`, bajo `/gobierno/tesoreria` | Mismo patrón que TRE-01 |
| AD-TRE02-02 | Versión como fila propia; líneas por versión; declaraciones por programa | FR-005 y reprogramación no destructiva |
| AD-TRE02-03 | Disponibilidad calculada al leer | Una sola fuente de verdad |
| AD-TRE02-04 | Inmutabilidad por disparador en PostgreSQL | FR-017 |
| AD-TRE02-05 | Unicidad por índices parciales | Principio 25: la base gobierna las altas concurrentes |
| AD-TRE02-06 | Capacidad `gobierno_caja` view, manage, activate (SENSITIVE) | FR-019 |
| AD-TRE02-07 | Pantallas en `modules/gobierno/tesoreria/programacion/` y menú «Programación financiera» y «Rubros de caja» | FR-025; sin módulo nuevo |
| AD-TRE02-08 | Guarda SoD en activar, reprogramar y cerrar | Reutiliza la guarda única de CTL-01 |

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Estado |
|---|---|
| P1 Spec antes que código · P2 Autorización expresa · P3 Trazabilidad | PASS: encargo GOV-TRE-FUNCTIONAL-02 nombra TRE-02 |
| P4 Núcleo fiscal separado | PASS: sin fiscal, presupuesto ni contabilidad |
| P5 Datos históricos protegidos | PASS: versiones y disparadores |
| P6 Seguridad en backend · P7 Frontend uniforme · P11 Accesibilidad | PASS |
| P8 No hardcodear reglas · P19 Reglas con fuente | PASS: rubros en catálogo; fuentes citadas |
| P20 No sustitución de organismos oficiales | PASS: cuotas del art. 64 fuera |
| P13 Integridad transaccional · P25 Altas concurrentes · P26 Paridad modelo y migración | PASS por diseño; se verifica en pruebas |
| P24 Instalación limpia | Se demuestra migrando desde cero |
| P27 Mutaciones | Se aplican en T-mutaciones |

| Compuerta del encargo §39 | Valor |
|---|---|
| TRE02_REQUIREMENTS_COMPLETE · TRE02_FULL_PROCESS_IMPLEMENTABLE | 1 · 1 |
| PROGRAMMING_SEMANTICS_RESOLVED · CASH_AVAILABILITY_SEMANTICS_RESOLVED | 1 · 1 |
| OPENING_AVAILABILITY_SOURCE_RESOLVED · TEMPORAL_GRANULARITY_RESOLVED · ACCOUNT_GRANULARITY_RESOLVED | 1 · 1 · 1 |
| BUDGET · TRE06 · TRE09 · ACCOUNTING _DEPENDENCY_REQUIRED | 0 · 0 · 0 · 0 |
| PROGRAMMING_STATE_MACHINE_COMPLETE · ROLE_MATRIX_COMPLETE · MENU_DEFINED | 1 · 1 · 1 |
| SCREEN_FORM_MATRIX_COMPLETE · FIELD_CONTRACT_COMPLETE · AUDIT_CONTRACT_COMPLETE | 1 · 1 · 1 |
| REPORTING_CLASSIFIED · DOCUMENT_CLASSIFIED · OWNER_UAT_SCENARIO_DEFINED | 1 · 1 · 1 |
| MATERIAL_BLOCKER · MATERIAL_OQ · UNKNOWN · CONTRADICTIONS | 0 · 0 · 0 · 0 |

**GATE = PASS** antes y después del diseño de la Fase 1.

## Project Structure

### Documentation (this feature)

```text
specs/gov-tre-02-programacion-financiera/
├── plan.md · research.md · data-model.md · quickstart.md · tasks.md
├── contracts/api.md
├── checklists/requirements.md
└── evidence/ (matriz, contrato de campos, mutaciones, tarjeta UAT, inventario, humo)
```

### Source Code (repository root)

```text
resources/backend/app/modules/government/{models,service_caja,schemas_caja,api_caja}.py
resources/backend/alembic/versions/0074_gov_tre02_caja.py
resources/backend/tests/test_gov_tre02_*.py
resources/frontend/src/modules/gobierno/tesoreria/programacion/
resources/frontend/e2e/gobierno-programacion.spec.ts
resources/frontend/e2e/gobierno-tesoreria-revocacion.spec.ts
qa/gobierno_integridad_caja.py
```

**Structure Decision**: extender el módulo `government` existente, sin módulo nuevo.

## Complexity Tracking

Sin violaciones de la Constitución que justificar.
