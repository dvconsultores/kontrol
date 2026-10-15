# Matriz de trazabilidad (FR-O11 → evidencia / prueba)
| Requisito | Evidencia | Prueba |
|---|---|---|
| FR-O11-001 checkpoint y árbol limpio | `checkpoint.md` | — |
| FR-O11-002 dueña y aserción exacta | `owner-matrix.md`, `exact-assertion.md` | — |
| FR-O11-003 procedencia, reloj canónico, invariante | `timestamp-provenance.md`, `intended-invariant.md` | O11-06 |
| FR-O11-004 vida de la referencia de módulo | `module-start-lifetime.md` | O11-05 |
| FR-O11-005 hermanos | `sibling-pattern-inventory.md` | — |
| FR-O11-006 aislada ×20 por motor | `isolated-baseline.md` | objetivo |
| FR-O11-007 envejecimiento determinista sin sleep | `aged-control.md` | O11-02 |
| FR-O11-008 control de frontera de operación | `operation-boundary-control.md` | O11-01, O11-04 |
| FR-O11-009 verdadero negativo | `true-negative-control.md` | O11-02, O11-03 |
| FR-O11-010 precisión SQLite/PostgreSQL | `precision-analysis.md` | objetivo en los dos motores |
| FR-O11-011 clasificación y gate material | `root-cause.md`, `implementation-decision.md` | — |
| FR-O11-012 corrección semántica, sin tolerancia/sleep/retry/skip | `implementation.md` | O11-05 |
| FR-O11-013 regresión envejecida y verdadero negativo | `implementation.md` | O11-02, O11-03 |
| FR-O11-014 reloj canónico y producto intactos | `implementation.md`, diff | O11-06 |
| FR-O11-015 dirigidas | `directed-tests.md` | — |
| FR-O11-016 mutaciones ≥ 10 | `mutation-campaign.md` | — |
| FR-O11-017…020 suites completas y E2E con analizador | `sqlite-full-1.md`, `sqlite-full-2.md`, `postgres-full.md`, `global-e2e.md`, `openapi.md` | — |
| FR-O11-021 OBS-12 solo como evidencia | `obs12-context.md` | — |
| FR-O11-022…026 converge, roadmap, commit/push, informe | `convergence.md`, `final-analyze.md` | — |
Huérfanos: requisitos 0, tareas 0. Trazabilidad 100 %.
