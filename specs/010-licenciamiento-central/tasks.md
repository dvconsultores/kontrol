# TAREAS — 010-LICENCIAMIENTO-CENTRAL

| Campo | Valor |
|---|---|
| Iniciativa | 010-licenciamiento-central |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Ruta | `specs/010-licenciamiento-central/tasks.md` |

> Convención: `T-010-XXX`. Columna **Dependencia** = tareas que deben estar completadas. Columna **Prueba** = cómo se valida. La implementación se habilita tras autorización expresa **010-licenciamiento-central**.

## Fase documental

| ID | Tarea | Dependencia | Resultado | Prueba | Estado |
|---|---|---|---|---|---|
| T-010-D01 | Crear spec.md | — | spec.md | Revisión PA | ✔ |
| T-010-D02 | Crear clarifications.md | T-010-D01 | clarifications.md | Revisión PA | ✔ |
| T-010-D03 | Crear plan.md y data-model.md | T-010-D02 | plan.md, data-model.md | Revisión PA | ✔ |
| T-010-D04 | Crear checklist.md y tasks.md | T-010-D03 | checklist.md, tasks.md | Revisión PA | ✔ |
| T-010-D05 | Crear soporte (AC, research, riesgo, trazabilidad, TP, contratos, wireframes) | T-010-D04 | Archivos de soporte | Revisión PA | ✔ |
| T-010-D06 | Crear analysis-report.md (sin bloqueos) | T-010-D05 | analysis-report.md | Revisión PA | ✔ |
| T-010-D07 | Commit fase documental y STOP para autorización | T-010-D06 | Commit `spec(010)` | Autorización expresa | ⬜ |

## Fase de implementación (post-autorización)

| ID | Tarea | Dependencia | Resultado | Prueba | Estado |
|---|---|---|---|---|---|
| T-010-01 | Configuración central + sincronización (contrato v1) | Aut. 010 | API /licensing/* | pytest | ✔ |
| T-010-02 | Activación/verificación con tolerancia offline | T-010-01 | Servicio + API | pytest | ✔ |
| T-010-03 | Entitlements por módulo + snapshots | T-010-01 | Modelos + servicio + API | pytest | ✔ |
| T-010-04 | Renovación central (workflow) | T-010-01 | Servicio + API | pytest | ✔ |
| T-010-05 | Refuerzo de modos y bloqueo de escrituras | T-010-02 | Servicio | pytest | ✔ |
| T-010-06 | Migración `0010_licenciamiento` + head | T-010-01..05 | Migración | alembic upgrade head | ✔ |
| T-010-07 | Frontend licenciamiento (config, entitlements, renovación) | T-010-03, T-010-04 | Páginas | tsc/vitest/build | ✔ |
| T-010-08 | Gates completos + convergencia + commit | T-010-06, T-010-07 | convergence.md, feat(010) | Todos verdes | 🔄 |

## Puertas (gates) de la implementación

| Gate | Comando | Umbral |
|---|---|---|
| Backend tests | `cd resources/backend && .venv/bin/python -m pytest -q` | 100% pasan (añade suite licenciamiento) |
| Lint | `.venv/bin/ruff check .` | 0 problemas |
| Tipos | `.venv/bin/mypy .` | 0 issues |
| Migración | `alembic upgrade head` | head `0010_licenciamiento` |
| Frontend | `npx tsc -b && npx eslint . --max-warnings 0 && npx vitest run && npx vite build` | 0 errores |
