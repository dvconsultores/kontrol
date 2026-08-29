# MATRIZ DE TRAZABILIDAD — 013

| Requisito de auditoría | Tarea | Artefacto producido | Verificado |
|---|---|---|---|
| FR-013-001 cadena completa | T-013-005..013 | `56-specs-gap-analysis.md` | ✔ |
| FR-013-002 patrón Sucursales | T-013-008, T-013-011/012 | `false-completion-findings.md` | ✔ |
| FR-013-003 cinco estados | T-013-015 | `56-specs-gap-analysis.md` col. Documentada/Front/Back/DB/E2E | ✔ |
| FR-013-004 estado único, suma 56 | T-013-015 | Informe maestro §4 (25+20+5+5+1 = 56) | ✔ |
| FR-013-005 requisito → Spec | T-013-002/003 | `requirements-to-specs-map.md` | ✔ |
| FR-013-006 código → Spec | T-013-005/006/007 | `code-to-specs-map.md` | ✔ |
| FR-013-007 grafo | T-013-016 | `spec-dependency-graph.md` | ✔ |
| FR-013-008 roadmap ejecutable | T-013-017 | `roadmap-by-waves.md` | ✔ |
| FR-013-009 backlog | T-013-018 | `master-backlog.md` | ✔ |
| FR-013-010 bloqueantes y decisiones | T-013-014, T-013-B01..B05 | Informe maestro §12-13 | ✔ |

## Trazabilidad inversa: artefacto → fuente documental

| Artefacto | Fuente principal |
|---|---|
| `source-inventory.md` | `requerimientos/` (18 archivos) |
| `requirements-to-specs-map.md` | Vol. 1 §4/§7/§9, Vol. 2 §1-§5, DOCX de proceso |
| `processes-to-specs-map.md` | DOCX Importación, DOCX Pedido, `procesos.png` |
| `spec-equivalence-map.md` | `specs/001..012/spec.md` + `convergence.md` |
| `false-completion-findings.md` | Inspección de modelos y máquinas de estado |
| `current-quality-baseline.md` | pytest/vitest ejecutados + auditoría 012 |
