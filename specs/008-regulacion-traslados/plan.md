# PLAN — 008-REGULACION-TRASLADOS

| Campo | Valor |
|---|---|
| Iniciativa | 008-regulacion-traslados |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Autor | Arquitecto de KONTROL |
| Ruta | `specs/008-regulacion-traslados/plan.md` |

## 1. Resumen ejecutivo

Implementar el módulo de **regulación y traslados**: maestros regulatorios (organismos, tipos de permiso, registros, perfiles, vehículos, conductores, certificados), permisos con ciclo de vida, guías SICA/SIGESAI/SACS (registro y validación, no emisión), evaluación regulatoria **por línea de despacho** con consolidación de requisitos y **bloqueo de salida**. Backend `app/modules/regulatory/`, migración `0008_regulacion`, tests, frontend `src/modules/regulatorio/`.

## 2. Estrategia técnica

- **Backend** (`app/modules/regulatory/`): patrón `models.py` / `service.py` / `api.py` / `__init__.py`, registrado en `init_models` y `app/main.py`. Prefijo `/regulatory`.
- **Migración**: Alembic `0008_regulacion`. Actualizar head.
- **Reutilización**: 008 **consume** los despachos de 005 (`Shipment`) vía contrato v1; **no reimplementa** el despacho. Maestros de terceros/almacenes de 002/001.
- **Entidades** (DOC-03 §11): `RegulatoryAuthority`, `PermitType`, `RegulatoryProfile`, `OfficialRegistration`, `PermitInstance`, `RegulatoryEvaluation`, `ApprovalRequest` + vehículos/conductores (maestros).
- **Bloqueo**: `RegulatoryEvaluation` por línea; el despacho no sale si hay bloqueos no anulados (FR-008-022).
- **Contingencias**: solo con regla oficial versionada (P8).
- **Tests**: fixture `conftest.py` (sqlite in-memory). Cobertura de maestros, permisos, evaluación por línea, bloqueo y aislamiento.
- **Frontend** (`src/modules/regulatorio/`): organismos/perfiles, vehículos/conductores, guías/permisos, evaluación y contingencias con patrón `DataTable`.
- **Gates**: pytest (100% +), ruff, mypy, `npx tsc -b`, `npx eslint . --max-warnings 0`, `npx vitest run`, `npx vite build`, OpenAPI check.

## 3. Secuencia de implementación (tras autorización)

| Fase | Actividad | Resultado | Gate |
|---|---|---|---|
| F1 | Maestros: autoridades, tipos, registros, perfiles, vehículos, conductores | Modelos + API | pytest/ruff/mypy |
| F2 | Permisos: `PermitInstance` con ciclo de vida y trazabilidad | Modelos + servicio + API | pytest |
| F3 | Guías SICA/SIGESAI/SACS: registro y validación (archivo/hash) | Modelos + servicio + API | pytest |
| F4 | Evaluación regulatoria por línea de despacho + bloqueo | Modelos + servicio + API | pytest |
| F5 | Contingencias con regla oficial versionada | Modelos + servicio | pytest |
| F6 | Migración `0008_regulacion` + integración con 005 (`Shipment`) | Migración + contract tests | alembic upgrade head |
| F7 | Frontend regulatorio (maestros, permisos, evaluación, guías) | Páginas + tipos | tsc/eslint/vitest/build |
| F8 | Convergencia + evidencia + commit | `convergence.md` | Todos verdes |

## 4. Plan de migración de datos

No hay datos legacy; migración estructural `0008_regulacion`. Las tablas de 005 no se alteran (se consumen).

## 5. Coordinación y riesgos clave

- Acoplamiento con 005: consumir `Shipment` vía contrato v1 (CL-008-07/SU-008-05).
- No fabricar permisos externos: registro/validación documental (CL-008-01/02).
- Reglas versionadas para aplicabilidad y contingencias (CL-008-10, FR-008-030).
- Bloqueo efectivo del despacho ante faltante/vencido/no coincidencia (FR-008-022).
