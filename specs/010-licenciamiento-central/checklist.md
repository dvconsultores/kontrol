# CHECKLIST — 010-LICENCIAMIENTO-CENTRAL

| Campo | Valor |
|---|---|
| Iniciativa | 010-licenciamiento-central |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Ruta | `specs/010-licenciamiento-central/checklist.md` |

> Leyenda: [ ] pendiente · [x] completado. La implementación solo arranca tras autorización expresa **010-licenciamiento-central**.

## 1. Proceso de especificación (SPEC KIT)

- [x] Crear `spec.md` (alcance, actores, historias, FRs, criterios de éxito).
- [x] Crear `clarifications.md` (CL-010-01 a CL-010-10, supuestos SU-010-01 a SU-010-05).
- [x] Crear `plan.md` (estrategia, fases F1-F8, migración).
- [x] Crear `data-model.md` (config central, sync runs, entitlements, reutilización 001).
- [x] Crear `checklist.md` (este documento).
- [x] Crear `tasks.md` (T-010-XXX con dependencias y prueba).
- [x] Crear `acceptance-criteria.md` (AC-010-XXX).
- [x] Crear `research.md` (referencias DOC y módulo licensing 001).
- [x] Crear `risk-register.md` (RSK-010-XXX).
- [x] Crear `traceability-matrix.md` (FR ↔ AC ↔ T ↔ TP ↔ CHK).
- [x] Crear `test-plan.md` (TP-010-XXX).
- [x] Crear `contracts/api-contracts.md` (contrato v1 de sincronización central).
- [x] Crear `wireframes/README.md` (configuración central, entitlements, renovación).
- [x] Crear `analysis-report.md` (conclusión sin bloqueos y detención).
- [ ] Commit de la fase documental (`spec(010): ...`).
- [ ] **STOP — solicitar autorización expresa que mencione 010-licenciamiento-central.**

## 2. Implementación (post-autorización)

### 2.1 Configuración y sincronización (F1/F2)
- [x] Modelos `license_central_config`, `license_sync_runs` + activación offline.
- [x] API de configuración/sincronización.

### 2.2 Entitlements (F3)
- [x] Modelo `license_entitlement_snapshots` + consulta por módulo.

### 2.3 Renovación central (F4)
- [x] Workflow REPORTED→VERIFIED→ISSUED/REJECTED (reutiliza `LicenseRenewalRequest`).

### 2.4 Modos (F5)
- [x] Refuerzo de transiciones y `ensure_write_allowed`.

### 2.5 Migración (F6)
- [x] Migración Alembic `0010_licenciamiento` (head).

### 2.6 Frontend (F7)
- [x] Páginas: configuración central, sincronización, entitlements, renovación, eventos.
- [x] Tipos en `src/api/types.ts`, sidebar, router.

### 2.7 Convergencia (F8)
- [x] Gates verdes (pytest, ruff, mypy, tsc, eslint, vitest, build).
- [x] `convergence.md` + evidencia + commit `feat(010)`.

## 3. Criterios de aceptación de entrada (fase documental)

- [x] Backend 158/158 tests verdes (001-009).
- [x] ruff/mypy limpios; alembic head `0009_reportes`.
- [x] Árbol de trabajo limpio (origin = 27ee812; local 63bf1ee).
