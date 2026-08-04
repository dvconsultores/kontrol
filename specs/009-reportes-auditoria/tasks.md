# TAREAS — 009-REPORTES-AUDITORIA

| Campo | Valor |
|---|---|
| Iniciativa | 009-reportes-auditoria |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Ruta | `specs/009-reportes-auditoria/tasks.md` |

> Convención: `T-009-XXX`. Columna **Dependencia** = tareas que deben estar completadas. Columna **Prueba** = cómo se valida. La implementación se habilita tras autorización expresa **009-reportes-auditoria**.

## Fase documental

| ID | Tarea | Dependencia | Resultado | Prueba | Estado |
|---|---|---|---|---|---|
| T-009-D01 | Crear spec.md | — | spec.md | Revisión PA | ✔ |
| T-009-D02 | Crear clarifications.md | T-009-D01 | clarifications.md | Revisión PA | ✔ |
| T-009-D03 | Crear plan.md y data-model.md | T-009-D02 | plan.md, data-model.md | Revisión PA | ✔ |
| T-009-D04 | Crear checklist.md y tasks.md | T-009-D03 | checklist.md, tasks.md | Revisión PA | ✔ |
| T-009-D05 | Crear soporte (AC, research, riesgo, trazabilidad, TP, contratos, wireframes) | T-009-D04 | Archivos de soporte | Revisión PA | 🔄 |
| T-009-D06 | Crear analysis-report.md (sin bloqueos) | T-009-D05 | analysis-report.md | Revisión PA | ⬜ |
| T-009-D07 | Commit fase documental y STOP para autorización | T-009-D06 | Commit `spec(009)` | Autorización expresa | ⬜ |

## Fase de implementación (post-autorización)

| ID | Tarea | Dependencia | Resultado | Prueba | Estado |
|---|---|---|---|---|---|
| T-009-01 | Dashboard agregado (indicadores y vencimientos) | Aut. 009 | API /reporting/* | pytest | ⬜ |
| T-009-02 | Reportes ejecutivos/operativos/financieros | T-009-01 | Servicio + API | pytest | ⬜ |
| T-009-03 | Reportes fiscales (libros 007) y regulatorios | T-009-02 | Servicio + API | pytest | ⬜ |
| T-009-04 | Exportación auditada (CSV/PDF) + `report_exports` | T-009-03 | Modelos + servicio + API | pytest | ⬜ |
| T-009-05 | Trabajos asíncronos (`report_jobs`) | T-009-04 | Modelos + servicio | pytest | ⬜ |
| T-009-06 | Migración `0009_reportes` + head | T-009-01..05 | Migración | alembic upgrade head | ⬜ |
| T-009-07 | Frontend dashboard y centro de reportes | T-009-04, T-009-05 | Páginas | tsc/vitest/build | ⬜ |
| T-009-08 | Gates completos + convergencia + commit | T-009-06, T-009-07 | convergence.md, feat(009) | Todos verdes | ⬜ |

## Puertas (gates) de la implementación

| Gate | Comando | Umbral |
|---|---|---|
| Backend tests | `cd resources/backend && .venv/bin/python -m pytest -q` | 100% pasan (añade suite reportes) |
| Lint | `.venv/bin/ruff check .` | 0 problemas |
| Tipos | `.venv/bin/mypy .` | 0 issues |
| Migración | `alembic upgrade head` | head `0009_reportes` |
| Frontend | `npx tsc -b && npx eslint . --max-warnings 0 && npx vitest run && npx vite build` | 0 errores |
