# CHECKLIST — 006-TESORERIA

| Campo | Valor |
|---|---|
| Iniciativa | 006-tesoreria |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Ruta | `specs/006-tesoreria/checklist.md` |

> Leyenda: [ ] pendiente · [x] completado. La implementación solo arranca tras autorización expresa **006-tesoreria**.

## 1. Proceso de especificación (SPEC KIT)

- [x] Crear `spec.md` (alcance, actores, historias, FRs, criterios de éxito).
- [x] Crear `clarifications.md` (CL-006-01 a CL-006-10, supuestos SU-006-01 a SU-006-05).
- [x] Crear `plan.md` (estrategia, fases F1-F8, migración).
- [x] Crear `data-model.md` (maestros financieros, cajas, bancos, conciliación, IGTF, reutilización).
- [x] Crear `checklist.md` (este documento).
- [x] Crear `tasks.md` (T-006-XXX con dependencias y prueba).
- [ ] Crear `acceptance-criteria.md` (AC-006-XXX).
- [ ] Crear `research.md` (referencias DOC-01/02/03/08).
- [ ] Crear `risk-register.md` (RSK-006-XXX).
- [ ] Crear `traceability-matrix.md` (FR ↔ AC ↔ T ↔ TP ↔ CHK).
- [ ] Crear `test-plan.md` (TP-006-XXX).
- [ ] Crear `contracts/api-contracts.md` (contratos v1 de 006 e integración con 004/005).
- [ ] Crear `wireframes/README.md` (pantallas WF-02/WF-05 aplicadas a tesorería).
- [ ] Crear `analysis-report.md` (conclusión sin bloqueos y detención).
- [ ] Commit de la fase documental (`spec(006): ...`).
- [ ] **STOP — solicitar autorización expresa que mencione 006-tesoreria.**

## 2. Implementación (post-autorización)

### 2.1 Maestros financieros (F1)
- [x] Modelos `financial_banks`, `financial_accounts`, `cashboxes`, `payment_methods`, `treasury_instruments`, `currencies`, `exchange_rates`.
- [x] API de maestros financieros + registro en `database.py`/`main.py`.

### 2.2 Cajas (F2)
- [x] Modelos `cash_sessions`, `cash_session_movements`.
- [x] Servicio: apertura → movimiento → arqueo → pre-cierre → cierre/rechazo con diferencias aprobadas (FR-006-002/003).

### 2.3 Bancos e ingresos/egresos (F3)
- [x] Modelo `bank_transactions`, `treasury_transfers`.
- [x] Ejecución de ingresos (005) y egresos (004) contra caja/banco con instrumentos e idempotencia (FR-006-020/021/022).

### 2.4 Conciliación (F4)
- [x] Modelos `reconciliations`, `reconciliation_lines`.
- [x] Conciliación asistida con reglas + resolución manual auditada (FR-006-030/031).

### 2.5 IGTF (F5)
- [x] Modelos `fiscal_rules`, `igft_events`.
- [x] Evaluación por regla y evento; no confundir con IVA (FR-006-040/041).

### 2.6 Migración e integración (F6)
- [x] Migración Alembic `0006_tesoreria` (head).
- [x] Contract tests con 004/005 (pagos OUT / cobros IN).

### 2.7 Frontend (F7)
- [x] Páginas tesorería: cajas/arqueo, ingreso/egreso, transferencias, conciliación, IGTF, maestros.
- [x] Tipos en `src/api/types.ts`, sidebar, router.

### 2.8 Convergencia (F8)
- [x] Gates verdes (pytest 109/109, ruff, mypy, tsc, eslint, vitest, build).
- [x] `convergence.md` + evidencia + commit `feat(006)`.

## 3. Criterios de aceptación de entrada (fase documental)

- [x] Backend 85/85 tests verdes (001-005).
- [x] ruff/mypy limpios; alembic head `0005_ventas`.
- [x] Árbol de trabajo limpio (solo pendiente push de 004/005).
