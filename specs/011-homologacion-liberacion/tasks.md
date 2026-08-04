# TAREAS — 011-HOMOLOGACION-LIBERACION

| Campo | Valor |
|---|---|
| Iniciativa | 011-homologacion-liberacion |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Ruta | `specs/011-homologacion-liberacion/tasks.md` |

> Convención: `T-011-XXX`. Columna **Dependencia** = tareas que deben estar completadas. Columna **Prueba** = cómo se valida. La implementación se habilita tras autorización expresa **011-homologacion-liberacion**.

## Fase documental

| ID | Tarea | Dependencia | Resultado | Prueba | Estado |
|---|---|---|---|---|---|
| T-011-D01 | Crear spec.md | — | spec.md | Revisión PA | ✔ |
| T-011-D02 | Crear clarifications.md | T-011-D01 | clarifications.md | Revisión PA | ✔ |
| T-011-D03 | Crear plan.md y data-model.md | T-011-D02 | plan.md, data-model.md | Revisión PA | ✔ |
| T-011-D04 | Crear checklist.md y tasks.md | T-011-D03 | checklist.md, tasks.md | Revisión PA | ✔ |
| T-011-D05 | Crear soporte (AC, research, riesgo, trazabilidad, TP, contratos, wireframes) | T-011-D04 | Archivos de soporte | Revisión PA | ✔ |
| T-011-D06 | Crear analysis-report.md (sin bloqueos) | T-011-D05 | analysis-report.md | Revisión PA | ✔ |
| T-011-D07 | Commit fase documental y STOP para autorización | T-011-D06 | Commit `spec(011)` | Autorización expresa | ⬜ |

## Fase de implementación (post-autorización)

| ID | Tarea | Dependencia | Resultado | Prueba | Estado |
|---|---|---|---|---|---|
| T-011-01 | Módulo homologation: models/service/api | Aut. 011 | API /homologation/* | pytest | ✔ |
| T-011-02 | Homologación: registro, sometimiento, evaluación + eventos | T-011-01 | Servicio + API | pytest | ✔ |
| T-011-03 | Regla de homologado (acto formal + versión aprobada) | T-011-02 | Servicio | pytest | ✔ |
| T-011-04 | Liberación: versiones, changelog, gates, liberación gateada | T-011-01, T-011-03 | Servicio + API | pytest | ✔ |
| T-011-05 | Migración `0011_homologacion` + head | T-011-01..04 | Migración | alembic upgrade head | ✔ |
| T-011-06 | Frontend homologación/liberación | T-011-03, T-011-04 | Páginas | tsc/vitest/build | ✔ |
| T-011-07 | Gates completos + convergencia + commit | T-011-05, T-011-06 | convergence.md, feat(011) | Todos verdes | 🔄 |

## Puertas (gates) de la implementación

| Gate | Comando | Umbral |
|---|---|---|
| Backend tests | `cd resources/backend && .venv/bin/python -m pytest -q` | 100% pasan (añade suite homologación) |
| Lint | `.venv/bin/ruff check .` | 0 problemas |
| Tipos | `.venv/bin/mypy .` | 0 issues |
| Migración | `alembic upgrade head` | head `0011_homologacion` |
| Frontend | `npx tsc -b && npx eslint . --max-warnings 0 && npx vitest run && npx vite build` | 0 errores |
