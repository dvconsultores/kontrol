# TAREAS — 007-NUCLEO-FISCAL

| Campo | Valor |
|---|---|
| Iniciativa | 007-nucleo-fiscal |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Ruta | `specs/007-nucleo-fiscal/tasks.md` |

> Convención: `T-007-XXX`. Columna **Dependencia** = tareas que deben estar completadas. Columna **Prueba** = cómo se valida. La implementación se habilita tras autorización expresa **007-nucleo-fiscal**.

## Fase documental

| ID | Tarea | Dependencia | Resultado | Prueba | Estado |
|---|---|---|---|---|---|
| T-007-D01 | Crear spec.md | — | spec.md | Revisión PA | ✔ |
| T-007-D02 | Crear clarifications.md | T-007-D01 | clarifications.md | Revisión PA | ✔ |
| T-007-D03 | Crear plan.md y data-model.md | T-007-D02 | plan.md, data-model.md | Revisión PA | ✔ |
| T-007-D04 | Crear checklist.md y tasks.md | T-007-D03 | checklist.md, tasks.md | Revisión PA | ✔ |
| T-007-D05 | Crear soporte (AC, research, riesgo, trazabilidad, TP, contratos, wireframes) | T-007-D04 | Archivos de soporte | Revisión PA | 🔄 |
| T-007-D06 | Crear analysis-report.md (sin bloqueos) | T-007-D05 | analysis-report.md | Revisión PA | ⬜ |
| T-007-D07 | Commit fase documental y STOP para autorización | T-007-D06 | Commit `spec(007)` | Autorización expresa | ⬜ |

## Fase de implementación (post-autorización)

| ID | Tarea | Dependencia | Resultado | Prueba | Estado |
|---|---|---|---|---|---|
| T-007-01 | Reglas fiscales (LegalSource/TaxRuleVersion/TaxProfile/TaxCalculation) | Aut. 007 | API /fiscal/* | pytest | ⬜ |
| T-007-02 | Numeración y números de control (asignación atómica) | T-007-01 | Servicio + API | pytest | ⬜ |
| T-007-03 | Emisión FiscalDocument (+hash) e impresión PrintEvent | T-007-02 | Servicio + API | pytest | ⬜ |
| T-007-04 | Notas fiscales con límites al saldo ajustable | T-007-03 | Servicio + API | pytest | ⬜ |
| T-007-05 | Retenciones (reglas + ciclo completo) | T-007-01 | Servicio + API | pytest | ⬜ |
| T-007-06 | Períodos/declaraciones y libros reconstruibles | T-007-04, T-007-05 | Servicio + API | pytest | ⬜ |
| T-007-07 | Migración `0007_nucleo_fiscal` + head | T-007-01..06 | Migración | alembic upgrade head | ⬜ |
| T-007-08 | Integración/contract con 004/005/006 | T-007-07 | Tests de integración | pytest | ⬜ |
| T-007-09 | Frontend configuración/numeración | T-007-01, T-007-02 | Páginas | tsc/vitest/build | ⬜ |
| T-007-10 | Frontend emisión/impresión/retenciones/libros | T-007-03..06 | Páginas | tsc/vitest/build | ⬜ |
| T-007-11 | Gates completos + convergencia + commit | T-007-08..10 | convergence.md, feat(007) | Todos verdes | ⬜ |

## Puertas (gates) de la implementación

| Gate | Comando | Umbral |
|---|---|---|
| Backend tests | `cd resources/backend && .venv/bin/python -m pytest -q` | 100% pasan (añade suite fiscal) |
| Lint | `.venv/bin/ruff check .` | 0 problemas |
| Tipos | `.venv/bin/mypy .` | 0 issues |
| Migración | `alembic upgrade head` | head `0007_nucleo_fiscal` |
| Frontend | `npx tsc -b && npx eslint . --max-warnings 0 && npx vitest run && npx vite build` | 0 errores |
