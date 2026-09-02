# TRAZABILIDAD DEL CHECKPOINT MAESTRO

Cobertura: **56/56**. Sin estado: **0**. Sin evidencia: **0**.

| Requisito | Artefacto | Evidencia |
|---|---|---|
| FR-DP-001 · las 56 tienen estado | `master-56-specs-status.md` | 56 filas |
| FR-DP-002 · cada estado con evidencia | ídem | columna «Evidencia», medida contra el repositorio |
| FR-DP-003 · cada Spec con dependencias | `capability-dependency-matrix.md`, `spec-dependency-graph.md` | — |
| FR-DP-004 · capacidad ≠ Spec completa | `capability-dependency-matrix.md` | dos columnas separadas |
| FR-DP-005 · desbloqueo por capacidad | ídem | 028 y 038 desbloqueadas por capacidad de 046 sin que 046 cambiara de estado |
| FR-DP-006 · bloqueos históricos revalidados | `resolved-blockers.md` | 8 filas comprobadas contra el código |
| FR-DP-007 · bloqueos resueltos retirados | ídem | D-01, D-02, D-05, D-08 |
| FR-DP-008 · bloqueos nuevos registrados | `active-blockers.md` | 12 filas |
| FR-DP-009 · nada READY con dependencia pendiente | `readiness-ranking.md` | 022 puntúa 26 y **no** se selecciona |
| FR-DP-010 · nada BLOCKED con capacidad satisfecha | `capability-dependency-matrix.md` | 029 sale de bloqueada a lista |
| FR-DP-011 · camino crítico | `critical-path-analysis.md` | cuatro caminos |
| FR-DP-012 · una siguiente Spec | `next-spec-decision.md` | 029 |
| FR-DP-013 · selección por dependencias y riesgo | ídem | 022 desbloquea más y no gana |
| FR-DP-014 · la selección no autoriza | ídem | «no inicia la implementación» |
| FR-DP-015 · ningún código productivo | guarda de `git diff` | 0 archivos en `resources/` y `alembic` |
| FR-DP-016 · numeración inmutable | `master-56-specs-status.md` | 001–056 |
| FR-DP-017 · metodología preservada | este ciclo | lifecycle completo |
| FR-DP-018 · toda deuda con responsable | `active-blockers.md` | columna «Responsable» |
| FR-DP-019 · la P0 bloquea | — | **no hay deuda P0 abierta** |
| FR-DP-020 · la P1 externa no bloquea de más | `active-blockers.md` §«Lo que no bloquean» | S3 solo afecta a 046 |
