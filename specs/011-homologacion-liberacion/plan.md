# PLAN — 011-HOMOLOGACION-LIBERACION

| Campo | Valor |
|---|---|
| Iniciativa | 011-homologacion-liberacion |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Autor | Arquitecto de KONTROL |
| Ruta | `specs/011-homologacion-liberacion/plan.md` |

## 1. Resumen ejecutivo

Implementar un módulo nuevo `app/modules/homologation/` que registra el **acto de homologación fiscal** (versión fiscal, modalidad, acto formal, evidencia con hash, evaluación) y gestiona la **liberación de versiones** (DRAFT → CANDIDATE → RELEASED/BLOCKED) con gates. La liberación a producción exige homologación documentada y aprobada, gates verdes y licencia válida (001). Migración `0011_homologacion`, tests y frontend `src/modules/homologacion/`.

## 2. Estrategia técnica

- **Backend**: módulo nuevo `app/modules/homologation/` (models/service/api), prefijo `/homologation`. Reutiliza instalación y modo de licencia de 001 (`current_mode`).
- **Migración**: Alembic `0011_homologacion` (homologation_records, homologation_events, release_versions). Actualizar head.
- **Máquinas de estado**:
  - Homologación: `DRAFT → SUBMITTED → APPROVED | REJECTED`.
  - Liberación: `DRAFT → CANDIDATE → RELEASED | BLOCKED`.
- **Gates de liberación**: tests, seguridad, homologación documentada (APPROVED), licencia válida (FULL_ACCESS), respaldo. Se registran por gate (quién/cuándo).
- **Segregación**: quien crea/somete no aprueba la misma homologación.
- **Tests**: fixture `conftest.py` (sqlite in-memory); `tests/test_homologation.py`.
- **Frontend** (`src/modules/homologacion/`): registro/evaluación de homologación, versiones y gates, timeline.
- **Gates**: pytest (100% +), ruff, mypy, `npx tsc -b`, `npx eslint . --max-warnings 0`, `npx vitest run`, `npx vite build`, OpenAPI check.

## 3. Secuencia de implementación (tras autorización)

| Fase | Actividad | Resultado | Gate |
|---|---|---|---|
| F1 | Homologación: registro, sometimiento, evaluación + eventos | Modelos + servicio + API | pytest/ruff/mypy |
| F2 | Regla de homologación (acto formal + versión aprobada) | Servicio | pytest |
| F3 | Liberación: versiones, changelog, gates y liberación | Modelos + servicio + API | pytest |
| F4 | Migración `0011_homologacion` | Migración | alembic upgrade head |
| F5 | Frontend homologación/liberación | Páginas + tipos | tsc/eslint/vitest/build |
| F6 | Convergencia + evidencia + commit | `convergence.md` | Todos verdes |

## 4. Plan de migración de datos

Migración estructural `0011_homologacion` (tablas nuevas). No altera tablas de negocio ni de licencias.

## 5. Coordinación y riesgos clave

- No fabricar el acto formal; solo registrarlo (CL-011-02).
- Liberación de versión ≠ liberación de lotes (CL-011-03).
- Segregación de funciones en evaluación (CL-011-05).
- Dependencia de 001 (licencia/modo) para el gate de liberación.
