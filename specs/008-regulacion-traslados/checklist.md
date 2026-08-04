# CHECKLIST — 008-REGULACION-TRASLADOS

| Campo | Valor |
|---|---|
| Iniciativa | 008-regulacion-traslados |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Ruta | `specs/008-regulacion-traslados/checklist.md` |

> Leyenda: [ ] pendiente · [x] completado. La implementación solo arranca tras autorización expresa **008-regulacion-traslados**.

## 1. Proceso de especificación (SPEC KIT)

- [x] Crear `spec.md` (alcance, actores, historias, FRs, criterios de éxito).
- [x] Crear `clarifications.md` (CL-008-01 a CL-008-12, supuestos SU-008-01 a SU-008-05).
- [x] Crear `plan.md` (estrategia, fases F1-F8, migración).
- [x] Crear `data-model.md` (maestros, permisos/guías, evaluación/bloqueo, contingencias, reutilización).
- [x] Crear `checklist.md` (este documento).
- [x] Crear `tasks.md` (T-008-XXX con dependencias y prueba).
- [ ] Crear `acceptance-criteria.md` (AC-008-XXX).
- [ ] Crear `research.md` (referencias DOC-01/02/03/08).
- [ ] Crear `risk-register.md` (RSK-008-XXX).
- [ ] Crear `traceability-matrix.md` (FR ↔ AC ↔ T ↔ TP ↔ CHK).
- [ ] Crear `test-plan.md` (TP-008-XXX).
- [ ] Crear `contracts/api-contracts.md` (contratos v1 de 008 e integración con 005).
- [ ] Crear `wireframes/README.md` (pantallas de organismos/permisos/evaluación).
- [ ] Crear `analysis-report.md` (conclusión sin bloqueos y detención).
- [ ] Commit de la fase documental (`spec(008): ...`).
- [ ] **STOP — solicitar autorización expresa que mencione 008-regulacion-traslados.**

## 2. Implementación (post-autorización)

### 2.1 Maestros regulatorios (F1)
- [x] Modelos `regulatory_authorities`, `permit_types`, `official_registrations`, `regulatory_profiles`, `transport_vehicles`, `transport_drivers`.
- [x] API de maestros + registro en `database.py`/`main.py`.

### 2.2 Permisos (F2)
- [x] Modelo `permit_instances` con ciclo DRAFT→REGISTERED→VERIFIED→APPROVED_FOR_USE→USED→EXPIRED; REJECTED/CANCELLED.
- [x] Servicio de transiciones + trazabilidad (hash/auditoría).

### 2.3 Guías (F3)
- [x] Modelo `official_documents` (SICA/SIGESAI/SACS/guía fiscal) con registro y validación.

### 2.4 Evaluación y bloqueo (F4)
- [x] Modelo `regulatory_evaluations` por línea de despacho.
- [x] Evaluación consolida requisitos y bloquea ante faltante/vencido; anulación auditada.

### 2.5 Contingencias (F5)
- [x] Modelo `regulatory_contingencies` con regla oficial versionada.

### 2.6 Migración e integración (F6)
- [x] Migración Alembic `0008_regulacion` (head).
- [x] Contract tests con 005 (`Shipment`); `GET /sales/shipments` aditivo.

### 2.7 Frontend (F7)
- [x] Páginas regulatorio: organismos, vehículos/conductores, permisos/guías, evaluación, contingencias.
- [x] Tipos en `src/api/types.ts`, sidebar, router.

### 2.8 Convergencia (F8)
- [x] Gates verdes (pytest 145/145, ruff, mypy, tsc, eslint, vitest, build).
- [x] `convergence.md` + evidencia + commit `feat(008)`.

## 3. Criterios de aceptación de entrada (fase documental)

- [x] Backend 130/130 tests verdes (001-007).
- [x] ruff/mypy limpios; alembic head `0007_nucleo_fiscal`.
- [x] Árbol de trabajo limpio (origin = 5551662; local 09128da).
