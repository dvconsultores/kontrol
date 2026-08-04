# TAREAS — 006-TESORERIA

| Campo | Valor |
|---|---|
| Iniciativa | 006-tesoreria |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Ruta | `specs/006-tesoreria/tasks.md` |

> Convención: `T-006-XXX`. Columna **Dependencia** = tareas que deben estar completadas. Columna **Prueba** = cómo se valida. La implementación se habilita tras autorización expresa **006-tesoreria**.

## Fase documental

| ID | Tarea | Dependencia | Resultado | Prueba | Estado |
|---|---|---|---|---|---|
| T-006-D01 | Crear spec.md | — | spec.md | Revisión PA | ✔ |
| T-006-D02 | Crear clarifications.md | T-006-D01 | clarifications.md | Revisión PA | ✔ |
| T-006-D03 | Crear plan.md y data-model.md | T-006-D02 | plan.md, data-model.md | Revisión PA | ✔ |
| T-006-D04 | Crear checklist.md y tasks.md | T-006-D03 | checklist.md, tasks.md | Revisión PA | ✔ |
| T-006-D05 | Crear soporte (AC, research, riesgo, trazabilidad, TP, contratos, wireframes) | T-006-D04 | Archivos de soporte | Revisión PA | 🔄 |
| T-006-D06 | Crear analysis-report.md (sin bloqueos) | T-006-D05 | analysis-report.md | Revisión PA | ⬜ |
| T-006-D07 | Commit fase documental y STOP para autorización | T-006-D06 | Commit `spec(006)` | Autorización expresa | ⬜ |

## Fase de implementación (post-autorización)

| ID | Tarea | Dependencia | Resultado | Prueba | Estado |
|---|---|---|---|---|---|
| T-006-01 | Modelos maestros financieros + API | Aut. 006 | API /treasury/* | pytest | ⬜ |
| T-006-02 | Cajas: sesiones/movimientos/arqueo/cierre | T-006-01 | Servicio + API | pytest | ⬜ |
| T-006-03 | Bancos: BankTransaction, ingresos/egresos | T-006-02 | Servicio + API | pytest | ⬜ |
| T-006-04 | Transferencias y depósitos | T-006-03 | Servicio + API | pytest | ⬜ |
| T-006-05 | Conciliación asistida + resolución manual | T-006-03 | Servicio + API | pytest | ⬜ |
| T-006-06 | IGTF por regla y evento (reglas versionadas) | T-006-01 | Servicio + maestra | pytest | ⬜ |
| T-006-07 | Migración `0006_tesoreria` + head | T-006-01..06 | Migración | alembic upgrade head | ⬜ |
| T-006-08 | Integración/contract con 004/005 | T-006-07 | Tests de integración | pytest | ⬜ |
| T-006-09 | Frontend cajas/arqueo | T-006-02 | Páginas | tsc/vitest/build | ⬜ |
| T-006-10 | Frontend ingreso/egreso y transferencias | T-006-03, T-006-04 | Páginas | tsc/vitest/build | ⬜ |
| T-006-11 | Frontend conciliación e IGTF | T-006-05, T-006-06 | Páginas | tsc/vitest/build | ⬜ |
| T-006-12 | Gates completos + convergencia + commit | T-006-08..11 | convergence.md, feat(006) | Todos verdes | ⬜ |

## Puertas (gates) de la implementación

| Gate | Comando | Umbral |
|---|---|---|
| Backend tests | `cd resources/backend && .venv/bin/python -m pytest -q` | 100% pasan (añade suite tesorería) |
| Lint | `.venv/bin/ruff check .` | 0 problemas |
| Tipos | `.venv/bin/mypy .` | 0 issues |
| Migración | `alembic upgrade head` | head `0006_tesoreria` |
| Frontend | `npx tsc -b && npx eslint . --max-warnings 0 && npx vitest run && npx vite build` | 0 errores |
