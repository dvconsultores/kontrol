# PLAN — 010-LICENCIAMIENTO-CENTRAL

| Campo | Valor |
|---|---|
| Iniciativa | 010-licenciamiento-central |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Autor | Arquitecto de KONTROL |
| Ruta | `specs/010-licenciamiento-central/plan.md` |

## 1. Resumen ejecutivo

Implementar el **licenciamiento central** sobre el módulo licensing de 001: configuración del servidor central, sincronización/activación con contrato v1 y tolerancia offline, matriz de **entitlements por módulo** (002-009), renovación con comprobante y workflow central, gestión de multi-instalación y refuerzo de modos/lectura. Backend `app/modules/licensing/` (extiende 001), migración `0010_licenciamiento`, tests, frontend `src/modules/licenciamiento/`.

## 2. Estrategia técnica

- **Backend**: extender `app/modules/licensing/` (models/service/api) con configuración central, sincronización, entitlements y renovación. Prefijo `/licensing` (existente).
- **Migración**: Alembic `0010_licenciamiento` (config central, sync runs, entitlement snapshots). Actualizar head.
- **Entidades nuevas**: `license_central_config`, `license_sync_runs`, `license_entitlement_snapshots`. Reutiliza LicenseState/Artifact/Event/RenewalRequest.
- **Sincronización**: cliente configurable (fake server en tests) con contrato v1; idempotencia y registro de ejecución.
- **Entitlements**: snapshot de la matriz por módulo; los módulos 002-009 la consultan (backend).
- **Modos**: reutiliza `current_mode`/`ensure_write_allowed`; refuerza transiciones.
- **Tests**: fixture `conftest.py` (sqlite in-memory). Cobertura de configuración, sincronización, entitlements, renovación y eventos.
- **Frontend** (`src/modules/licenciamiento/`): configuración central, sincronización, entitlements, renovación y eventos con `DataTable`.
- **Gates**: pytest (100% +), ruff, mypy, `npx tsc -b`, `npx eslint . --max-warnings 0`, `npx vitest run`, `npx vite build`, OpenAPI check.

## 3. Secuencia de implementación (tras autorización)

| Fase | Actividad | Resultado | Gate |
|---|---|---|---|
| F1 | Configuración central + sincronización (`license_central_config`, `license_sync_runs`) | Modelos + servicio + API | pytest/ruff/mypy |
| F2 | Activación/verificación con tolerancia offline | Servicio + API | pytest |
| F3 | Entitlements por módulo + snapshots | Modelos + servicio + API | pytest |
| F4 | Renovación central (workflow REPORTED→VERIFIED→ISSUED/REJECTED) | Servicio + API | pytest |
| F5 | Refuerzo de modos y bloqueo de escrituras | Servicio | pytest |
| F6 | Migración `0010_licenciamiento` | Migración | alembic upgrade head |
| F7 | Frontend licenciamiento | Páginas + tipos | tsc/eslint/vitest/build |
| F8 | Convergencia + evidencia + commit | `convergence.md` | Todos verdes |

## 4. Plan de migración de datos

Migración estructural `0010_licenciamiento` (tablas nuevas). No se alteran las tablas de 001 ni de negocio.

## 5. Coordinación y riesgos clave

- Extender licensing de 001 sin redefinirlo (CL-010-01).
- Cliente central configurable; contrato v1; fake server en tests (CL-010-02/SU-010-01).
- Tolerancia offline con `last_reliable_date` (CL-010-03).
- Entitlements respetados en backend (CL-010-04).
