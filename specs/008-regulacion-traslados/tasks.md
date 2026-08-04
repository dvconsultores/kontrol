# TAREAS — 008-REGULACION-TRASLADOS

| Campo | Valor |
|---|---|
| Iniciativa | 008-regulacion-traslados |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Ruta | `specs/008-regulacion-traslados/tasks.md` |

> Convención: `T-008-XXX`. Columna **Dependencia** = tareas que deben estar completadas. Columna **Prueba** = cómo se valida. La implementación se habilita tras autorización expresa **008-regulacion-traslados**.

## Fase documental

| ID | Tarea | Dependencia | Resultado | Prueba | Estado |
|---|---|---|---|---|---|
| T-008-D01 | Crear spec.md | — | spec.md | Revisión PA | ✔ |
| T-008-D02 | Crear clarifications.md | T-008-D01 | clarifications.md | Revisión PA | ✔ |
| T-008-D03 | Crear plan.md y data-model.md | T-008-D02 | plan.md, data-model.md | Revisión PA | ✔ |
| T-008-D04 | Crear checklist.md y tasks.md | T-008-D03 | checklist.md, tasks.md | Revisión PA | ✔ |
| T-008-D05 | Crear soporte (AC, research, riesgo, trazabilidad, TP, contratos, wireframes) | T-008-D04 | Archivos de soporte | Revisión PA | 🔄 |
| T-008-D06 | Crear analysis-report.md (sin bloqueos) | T-008-D05 | analysis-report.md | Revisión PA | ⬜ |
| T-008-D07 | Commit fase documental y STOP para autorización | T-008-D06 | Commit `spec(008)` | Autorización expresa | ⬜ |

## Fase de implementación (post-autorización)

| ID | Tarea | Dependencia | Resultado | Prueba | Estado |
|---|---|---|---|---|---|
| T-008-01 | Maestros regulatorios (autoridades, tipos, registros, perfiles, vehículos, conductores) | Aut. 008 | API /regulatory/* | pytest | ⬜ |
| T-008-02 | Permisos con ciclo de vida y trazabilidad | T-008-01 | Servicio + API | pytest | ⬜ |
| T-008-03 | Guías SICA/SIGESAI/SACS (registro y validación) | T-008-01 | Servicio + API | pytest | ⬜ |
| T-008-04 | Evaluación regulatoria por línea + bloqueo | T-008-02, T-008-03 | Servicio + API | pytest | ⬜ |
| T-008-05 | Contingencias con regla oficial versionada | T-008-04 | Servicio + API | pytest | ⬜ |
| T-008-06 | Migración `0008_regulacion` + head | T-008-01..05 | Migración | alembic upgrade head | ⬜ |
| T-008-07 | Integración/contract con 005 (`Shipment`) | T-008-06 | Tests de integración | pytest | ⬜ |
| T-008-08 | Frontend regulatorio (maestros, permisos, evaluación, guías) | T-008-04, T-008-05 | Páginas | tsc/vitest/build | ⬜ |
| T-008-09 | Gates completos + convergencia + commit | T-008-07, T-008-08 | convergence.md, feat(008) | Todos verdes | ⬜ |

## Puertas (gates) de la implementación

| Gate | Comando | Umbral |
|---|---|---|
| Backend tests | `cd resources/backend && .venv/bin/python -m pytest -q` | 100% pasan (añade suite regulatoria) |
| Lint | `.venv/bin/ruff check .` | 0 problemas |
| Tipos | `.venv/bin/mypy .` | 0 issues |
| Migración | `alembic upgrade head` | head `0008_regulacion` |
| Frontend | `npx tsc -b && npx eslint . --max-warnings 0 && npx vitest run && npx vite build` | 0 errores |
