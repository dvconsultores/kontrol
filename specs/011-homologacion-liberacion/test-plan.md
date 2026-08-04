# PLAN DE PRUEBAS — 011-HOMOLOGACION-LIBERACION

| Campo | Valor |
|---|---|
| Iniciativa | 011-homologacion-liberacion |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Ruta | `specs/011-homologacion-liberacion/test-plan.md` |

> Convención: `TP-011-XXX`. Pruebas automatizadas con pytest (sqlite in-memory) y vitest (frontend). Cobertura objetivo: todas las rutas nuevas del módulo homologation.

## Backend

| ID | Escenario | Pasos clave | Resultado esperado | FR |
|---|---|---|---|---|
| TP-011-001 | Registrar acto de homologación | Crear DRAFT con versión fiscal, modalidad, acto formal, evidencia hash | Persistido; evento creado | FR-011-001 |
| TP-011-002 | Someter homologación | DRAFT → SUBMITTED | Estado SUBMITTED + evento | FR-011-002 |
| TP-011-003 | Evaluar con segregación | SUBMITTED → APPROVED por evaluador ≠ creador; mismo usuario → error | Aprobado o 403/conflicto | FR-011-003 |
| TP-011-004 | Eventos append-only | Ejecutar transiciones | `homologation_events` completo | FR-011-004 |
| TP-011-005 | Regla de homologado | Consultar estado sin acto formal/versión aprobada | No HOMOLOGADO | FR-011-005 |
| TP-011-010 | Crear versión en DRAFT | Crear con changelog y gates | Persistido | FR-011-010 |
| TP-011-011 | Promover a CANDIDATE | Verificar gates | Estado CANDIDATE | FR-011-011 |
| TP-011-012 | Liberar gateada | Liberar sin homologación aprobada → BLOCKED; con homologación + licencia válida → RELEASED | Gate correcto | FR-011-012 |
| TP-011-013 | Registro y bloqueo de re-liberación | Registrar liberación; intentar re-liberar versión anterior | Registro + bloqueo | FR-011-013 |
| TP-011-020 | Timeline | Consultar timeline de homologación y liberación | Lista ordenada | FR-011-020 |
| TP-011-100 | Aislamiento e idempotencia | Datos de otra instalación; doble liberación | Sin fugas; sin duplicados | FR-011-100 |

## Frontend

| ID | Escenario | Resultado esperado | FR |
|---|---|---|---|
| TP-011-021 | Panel homologación | Registro/evaluación OK | FR-011-021 |
| TP-011-021 | Panel versiones y gates | Creación, gates y liberación OK | FR-011-021 |
| TP-011-021 | Timeline | Histórico con DataTable | FR-011-021 |

## Evidencia

- Backend: `pytest -q` (suite 001-010 + nueva homologación).
- Lint/tipos: `ruff check .`, `mypy .`.
- Migración: `alembic upgrade head` (head `0011_homologacion`).
- Frontend: `tsc -b`, `eslint . --max-warnings 0`, `vitest run`, `vite build`.
