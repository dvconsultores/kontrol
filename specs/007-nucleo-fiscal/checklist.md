# CHECKLIST — 007-NUCLEO-FISCAL

| Campo | Valor |
|---|---|
| Iniciativa | 007-nucleo-fiscal |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Ruta | `specs/007-nucleo-fiscal/checklist.md` |

> Leyenda: [ ] pendiente · [x] completado. La implementación solo arranca tras autorización expresa **007-nucleo-fiscal**.

## 1. Proceso de especificación (SPEC KIT)

- [x] Crear `spec.md` (alcance, actores, historias, FRs, criterios de éxito).
- [x] Crear `clarifications.md` (CL-007-01 a CL-007-12, supuestos SU-007-01 a SU-007-05).
- [x] Crear `plan.md` (estrategia, fases F1-F9, migración).
- [x] Crear `data-model.md` (reglas, numeración/control, emisión, notas, retenciones, períodos/libros, reutilización).
- [x] Crear `checklist.md` (este documento).
- [x] Crear `tasks.md` (T-007-XXX con dependencias y prueba).
- [ ] Crear `acceptance-criteria.md` (AC-007-XXX).
- [ ] Crear `research.md` (referencias DOC-01/02/03/08).
- [ ] Crear `risk-register.md` (RSK-007-XXX).
- [ ] Crear `traceability-matrix.md` (FR ↔ AC ↔ T ↔ TP ↔ CHK).
- [ ] Crear `test-plan.md` (TP-007-XXX).
- [ ] Crear `contracts/api-contracts.md` (contratos v1 de 007 e integración con 004/005/006).
- [ ] Crear `wireframes/README.md` (pantallas de configuración/emisión/libros).
- [ ] Crear `analysis-report.md` (conclusión sin bloqueos y detención).
- [ ] Commit de la fase documental (`spec(007): ...`).
- [ ] **STOP — solicitar autorización expresa que mencione 007-nucleo-fiscal.**

## 2. Implementación (post-autorización)

### 2.1 Reglas fiscales (F1)
- [ ] Modelos `legal_sources`, `tax_rule_versions`, `tax_profiles`, `tax_calculations`.
- [ ] API de reglas + registro en `database.py`/`main.py`.

### 2.2 Numeración y control (F2)
- [ ] Modelos `fiscal_number_series`, `control_number_batches`, `control_numbers`.
- [ ] Asignación atómica de correlativo y control (lock/transacción).

### 2.3 Emisión e impresión (F3)
- [ ] Modelos `fiscal_documents`, `print_events`.
- [ ] Emisión consume correlativo + control en transacción atómica con `hash`.

### 2.4 Notas fiscales (F4)
- [ ] Modelo `credit_debit_notes` con límites al saldo ajustable.

### 2.5 Retenciones (F5)
- [ ] Modelos `withholding_rules`, `withholdings` con ciclo completo.

### 2.6 Períodos, declaraciones y libros (F6)
- [ ] Modelos `fiscal_periods`, `tax_return_batches`.
- [ ] Libros reconstruibles desde documentos/eventos (vista).

### 2.7 Migración e integración (F7)
- [ ] Migración Alembic `0007_nucleo_fiscal` (head).
- [ ] Contract tests con 004/005/006 (facturas, retenciones, eventos IGTF).

### 2.8 Frontend (F8)
- [ ] Páginas fiscal: configuración, numeración/control, emisión, impresión, retenciones, libros.
- [ ] Tipos en `src/api/types.ts`, sidebar, router.

### 2.9 Convergencia (F9)
- [ ] Gates verdes (pytest, ruff, mypy, tsc, eslint, vitest, build).
- [ ] `convergence.md` + evidencia + commit `feat(007)`.

## 3. Criterios de aceptación de entrada (fase documental)

- [x] Backend 109/109 tests verdes (001-006).
- [x] ruff/mypy limpios; alembic head `0006_tesoreria`.
- [x] Árbol de trabajo limpio (pusheado: origin = e414677).
