# Trazabilidad PROC-08

| Requisito del sponsor | FR | Tareas | Prueba |
|---|---|---|---|
| GOV-PROC-010: recomendación de la Comisión y decisión de la autoridad como actos separados | FR-001, FR-002, FR-004, FR-005, FR-009 | T1, T2, T3, T4, T5 | `test_gov_proc08_recomendacion`, `test_gov_proc08_decision`, `gobierno-decision.spec.ts` |
| GOV-PROC-011: adjudicación, desierta, terminación, anulación y rechazo con fundamento y acto | FR-003, FR-005, FR-006, FR-007, FR-008 | T1, T2, T3, T4, T5 | `test_gov_proc08_decision` (desierta, terminación, nulidad y segunda opción), `test_gov_proc08_recomendacion` (rechazo), E2E (adjudicación y notificación) |
| Encargo §1: siguiente acción de PROC-07 | FR-011 | T2 | `test_gov_proc07_*`, `gobierno-evaluacion.spec.ts` |
| Interfaz, responsive y accesibilidad | FR-010 | T4, T5 | E2E (Axe, 390/320) |

Requisitos huérfanos: 0. Tareas huérfanas: 0.
