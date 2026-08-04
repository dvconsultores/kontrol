# CHECKLIST — 011-HOMOLOGACION-LIBERACION

| Campo | Valor |
|---|---|
| Iniciativa | 011-homologacion-liberacion |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Ruta | `specs/011-homologacion-liberacion/checklist.md` |

> Leyenda: [ ] pendiente · [x] completado. La implementación solo arranca tras autorización expresa **011-homologacion-liberacion**.

## 1. Proceso de especificación (SPEC KIT)

- [x] Crear `spec.md` (alcance, actores, historias, FRs, criterios de éxito).
- [x] Crear `clarifications.md` (CL-011-01 a CL-011-10, supuestos SU-011-01 a SU-011-05).
- [x] Crear `plan.md` (estrategia, fases F1-F6, migración).
- [x] Crear `data-model.md` (homologation_records, homologation_events, release_versions).
- [x] Crear `checklist.md` (este documento).
- [x] Crear `tasks.md` (T-011-XXX con dependencias y prueba).
- [x] Crear `acceptance-criteria.md` (AC-011-XXX).
- [x] Crear `research.md` (referencias DOC y módulos base).
- [x] Crear `risk-register.md` (RSK-011-XXX).
- [x] Crear `traceability-matrix.md` (FR ↔ AC ↔ T ↔ TP ↔ CHK).
- [x] Crear `test-plan.md` (TP-011-XXX).
- [x] Crear `contracts/api-contracts.md` (API `/homologation/*`).
- [x] Crear `wireframes/README.md` (panel de homologación y liberación).
- [x] Crear `analysis-report.md` (conclusión sin bloqueos y detención).
- [ ] Commit de la fase documental (`spec(011): ...`).
- [ ] **STOP — solicitar autorización expresa que mencione 011-homologacion-liberacion.**

## 2. Implementación (post-autorización)

### 2.1 Homologación (F1/F2)
- [x] Módulo `app/modules/homologation/`: models, service, api.
- [x] Máquinas DRAFT→SUBMITTED→APPROVED/REJECTED; segregación; regla de homologado.
- [x] Eventos append-only.

### 2.2 Liberación (F3)
- [x] `release_versions` con changelog, gates y liberación gateada.

### 2.3 Migración (F4)
- [x] Migración Alembic `0011_homologacion` (head).

### 2.4 Frontend (F5)
- [x] Páginas: homologación, versiones/liberación, timeline.
- [x] Tipos en `src/api/types.ts`, sidebar, router.

### 2.5 Convergencia (F6)
- [x] Gates verdes (pytest, ruff, mypy, tsc, eslint, vitest, build).
- [x] `convergence.md` + evidencia + commit `feat(011)`.

## 3. Criterios de aceptación de entrada (fase documental)

- [x] Backend 173/173 tests verdes (001-010).
- [x] ruff/mypy limpios; alembic head `0010_licenciamiento`.
- [x] Árbol de trabajo limpio; origin al día (d13632a).
