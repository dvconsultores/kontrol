# CHECKLIST — 009-REPORTES-AUDITORIA

| Campo | Valor |
|---|---|
| Iniciativa | 009-reportes-auditoria |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Ruta | `specs/009-reportes-auditoria/checklist.md` |

> Leyenda: [ ] pendiente · [x] completado. La implementación solo arranca tras autorización expresa **009-reportes-auditoria**.

## 1. Proceso de especificación (SPEC KIT)

- [x] Crear `spec.md` (alcance, actores, historias, FRs, criterios de éxito).
- [x] Crear `clarifications.md` (CL-009-01 a CL-009-12, supuestos SU-009-01 a SU-009-05).
- [x] Crear `plan.md` (estrategia, fases F1-F8, migración).
- [x] Crear `data-model.md` (exportaciones, jobs, definiciones, reutilización).
- [x] Crear `checklist.md` (este documento).
- [x] Crear `tasks.md` (T-009-XXX con dependencias y prueba).
- [ ] Crear `acceptance-criteria.md` (AC-009-XXX).
- [ ] Crear `research.md` (referencias DOC-01/02/03/08).
- [ ] Crear `risk-register.md` (RSK-009-XXX).
- [ ] Crear `traceability-matrix.md` (FR ↔ AC ↔ T ↔ TP ↔ CHK).
- [ ] Crear `test-plan.md` (TP-009-XXX).
- [ ] Crear `contracts/api-contracts.md` (contratos v1 de 009 e integración 003-008).
- [ ] Crear `wireframes/README.md` (dashboard y centro de reportes).
- [ ] Crear `analysis-report.md` (conclusión sin bloqueos y detención).
- [ ] Commit de la fase documental (`spec(009): ...`).
- [ ] **STOP — solicitar autorización expresa que mencione 009-reportes-auditoria.**

## 2. Implementación (post-autorización)

### 2.1 Dashboard (F1)
- [ ] Endpoint agregado de indicadores y vencimientos (solo lectura).

### 2.2 Reportes ejecutivos/operativos/financieros (F2)
- [ ] Endpoints agregados sobre 003/004/005/006.

### 2.3 Reportes fiscales y regulatorios (F3)
- [ ] Reutiliza libros de 007 y evaluaciones/permisos de 008.

### 2.4 Exportación auditada (F4)
- [ ] Modelo `report_exports` + exportación CSV/PDF con registro de evento.

### 2.5 Trabajos asíncronos (F5)
- [ ] Modelo `report_jobs` con estado/error.

### 2.6 Migración (F6)
- [ ] Migración Alembic `0009_reportes` (head).

### 2.7 Frontend (F7)
- [ ] Páginas: dashboard y centro de reportes con filtros y exportación.
- [ ] Tipos en `src/api/types.ts`, sidebar, router.

### 2.8 Convergencia (F8)
- [ ] Gates verdes (pytest, ruff, mypy, tsc, eslint, vitest, build).
- [ ] `convergence.md` + evidencia + commit `feat(009)`.

## 3. Criterios de aceptación de entrada (fase documental)

- [x] Backend 145/145 tests verdes (001-008).
- [x] ruff/mypy limpios; alembic head `0008_regulacion`.
- [x] Árbol de trabajo limpio (origin = 78ce2f6; local 25e9bec).
