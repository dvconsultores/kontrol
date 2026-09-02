# D0-03 — MATRIZ DE TRAZABILIDAD DEL CHECKPOINT

Criterio de inclusión: todo requisito FR-D0-03-xxx del `/speckit.specify` debe tener evidencia
auditada, clarificación, análisis de opción, decisión, regla en el ADR v2 e impacto en Spec 030.
Cobertura exigida: 100 %. Huérfanos permitidos: 0.

Abreviaturas: **B** `current-reservation-behavior.md` · **CS** `d0-03-reservation-current-state.md`
· **O** `d0-03-reservation-options.md` · **F** `d0-03-reservation-flow-matrix.md` · **C**
`d0-03-reservation-concurrency-analysis.md` · **D** `d0-03-reservation-decision.md` · **L**
`d0-03-checkpoint-lifecycle.md` · **ADR** `ADR-D0-003` v2 · **S30** `specs/005-…/spec.md` §SPEC 030.

| Decision Requirement | Evidence | Clarification | Option Analysis | Decision | ADR | Spec030 Impact | Status |
|---|---|---|---|---|---|---|---|
| FR-D0-03-001 trigger definido | B «Current trigger» · CS §3 | L-Q5, Q27 | O §3-§5 | D §1 | R-D0-03-1 | FR-030-001..003 | ✔ |
| FR-D0-03-002 no depende de código implícito | B CD-01 · CS §1 | L-Q6 | O §4-C | D §1, §8 | ADR «Contexto» | FR-030-001 | ✔ |
| FR-D0-03-003 contado definido | CS §5 | L-Q7 | O E4/E10 | D §2.P, §3 · F-A/B | R-D0-03-2 | FR-030-004 | ✔ |
| FR-D0-03-004 crédito definido | CS §5 | L-Q7, Q20 | O §4-B/C | D §2.P, §3 · F-C/D | R-D0-03-2, -9 | FR-030-005..007 | ✔ |
| FR-D0-03-005 sin crédito definido | CS §5 (`ensure_approved`) | L-Q7 | O E10 | D §3 fila «sin política» | R-D0-03-2 | FR-030-004 | ✔ |
| FR-D0-03-006 stock insuficiente | B (`INSUFFICIENT_AVAILABLE`) | L-Q8 | O E6 | D §2.K · F-B | R-D0-03-4 | FR-030-010 | ✔ |
| FR-D0-03-007 parcial prohibida | B (no existe) | L-Q8 | O criterio «modificación» | D §2.D · F-H | R-D0-03-4 | FR-030-011 | ✔ |
| FR-D0-03-008 backorder OUT_OF_SCOPE | OQ-04 | L-Q9 | O E6 | D §2.M | R-D0-03-12 | FR-030-012 | ✔ |
| FR-D0-03-009 autoridad de almacén | B CD-02 · CS §4 | L-Q11 | — | D §2.E | R-D0-03-5 | FR-030-013..014 | ✔ |
| FR-D0-03-010 aislamiento por empresa | B «Contract alignment» ARCH-MC-001 | — | — | D §6 | R-D0-03-10 | FR-030-030..034 | ✔ |
| FR-D0-03-011 semántica de cantidad | B CD-07 | L-Q14 | — | D §2.D | R-D0-03-4 | FR-030-015 | ✔ |
| FR-D0-03-012 UOM / base | B CD-07 · Spec 011 | L-Q14-15 | — | D §2.D | R-D0-03-4 | FR-030-015..016 | ✔ |
| FR-D0-03-013 modificación | B CD-10 | L-Q16, Q22-23 | O criterio «modificación» | D §2.I · F-E | R-D0-03-7 | FR-030-020..022 | ✔ |
| FR-D0-03-014 cancelación libera | B CD-05 | L-Q21 | O criterio «cancelación» | D §2.J · F-F | R-D0-03-6 | FR-030-023 | ✔ |
| FR-D0-03-015 rechazo de crédito | CS §5 | L-Q20 | O §4-B | D §2.P · F-D | R-D0-03-6 | FR-030-007 | ✔ |
| FR-D0-03-016 expiración | B CD-09 | L-Q18 | — | D §2.F-G · F-I | R-D0-03-8 | FR-030-024..026 | ✔ |
| FR-D0-03-017 liberación manual | B CD-11 | L-Q19 | — | D §2.H | R-D0-03-6 | FR-030-027 | ✔ |
| FR-D0-03-018 idempotencia | B CD-08 | L-Q24 | — | C §6 | R-D0-03-3 | FR-030-042..043 | ✔ |
| FR-D0-03-019 concurrencia | B CD-03/04 | L-Q25 | O E8 | C §3-§5 · F-G | R-D0-03-3 | FR-030-040..041 | ✔ |
| FR-D0-03-020 sobreventa | B (`allow_negative`) | L-Q10 | — | D §2.K · C §7 | R-D0-03-4 | FR-030-010 | ✔ |
| FR-D0-03-021 no consume otra empresa | B ARCH-MC-001 | — | — | D §6 | R-D0-03-10 | FR-030-030..034 | ✔ |
| FR-D0-03-022 no consume no elegible | CS §4 (ADR-D0-010) | — | — | D §2.E | R-D0-03-5 | FR-030-017 | ✔ |
| FR-D0-03-023 no absorbe picking | CS §6 | L-Q12-13, Q26 | — | D §2.Q, §0 · F-J | R-D0-03-11 | FR-030-050..052 | ✔ |
| FR-D0-03-024 no absorbe facturación | ADR v1 R-D0-03-7 | — | — | D §2.H | R-D0-03-9 | FR-030-053 | ✔ |
| FR-D0-03-025 no absorbe despacho | B CD-06 | L-Q17 | — | D §2.H | R-D0-03-9 | FR-030-054 | ✔ |
| FR-D0-03-026 aprobación usa 045 | CS §5 | — | — | D §2.P | R-D0-03-2 | FR-030-005 | ✔ |
| FR-D0-03-027 permiso ≠ contexto | B CD-12 · ARCH-MC-001 | — | — | D §2.O, §6 | R-D0-03-10 | FR-030-035 | ✔ |
| FR-D0-03-028 auditoría | B CD-13 | — | — | D §7 | R-D0-03-3 | FR-030-060..061 | ✔ |
| FR-D0-03-029 handoff a 031 | CS §6 | L-Q26 | O criterio «picking» | D §2.Q · F-J | R-D0-03-11 | FR-030-050 | ✔ |
| FR-D0-03-030 contrato implementable | — | L (30/30) | O §5 | D §9 | ADR completo | S30 completo | ✔ |

**Cobertura: 30/30 = 100 %. Requisitos huérfanos: 0.**

## Tareas → artefactos

| Rango | Artefacto | Estado |
|---|---|---|
| T-D003-001..007 | B · CS | ✔ |
| T-D003-008..011 | F-A..D | ✔ |
| T-D003-012..018 | D §2.D-E, §2.K-M | ✔ |
| T-D003-019..022 | D §2.F-J | ✔ |
| T-D003-023..024 | C | ✔ |
| T-D003-025 | D §2.Q · F-J | ✔ |
| T-D003-026..027 | O · D §1 | ✔ |
| T-D003-028 | ADR v2 · POL v2 | ✔ |
| T-D003-029 | `specs/005-…/clarifications.md` §SPEC 030 | ✔ |
| T-D003-030 | `docs/roadmap/*` · registro D0 · baseline | ✔ |
| T-D003-031 | este documento | ✔ |
| T-D003-032 | `convergence.md` | ✔ |

**Tareas huérfanas: 0 (32/32).**

## Decisiones → evidencia

| Decisión | Evidencia que la sostiene |
|---|---|
| Trigger `ORDER_CONFIRMATION` | DOCX Pedido §1 (E1) · FR-005-011 (`SUBMITTED` no editable) · FR-029-035 · `ensure_approved` sin política (E10) · ausencia de backorder (E6) |
| Fijo, no configurable | E6/E7 · P8 (semántica de producto vs. política de cliente) · bloqueo detectado por Master 56 |
| Todo-o-nada por pedido | E6 · edición en `DRAFT` posible · sin backorder |
| Sin abastecimiento cruzado | `SalesOrder.warehouse_id` único · ausencia de contrato multi-almacén |
| Base con snapshot | Spec 011 / R-D0-09-1 · CD-07 |
| Reversión a borrador como única modificación | CD-10 · 045 `document_changed` · simplicidad frente a deltas |
| Cancelación/rechazo/reversión liberan atómicamente | CD-05 · POL-D0-002 §6 · FR-003-043 |
| TTL opcional, defecto desactivado, dueño 047 | CD-09 · ausencia de planificador · R-D0-03-4 v1 no cumplible · §51 del prompt |
| Bloqueo de fila + unicidad + prueba | CD-03/04 · R-D0-03-3 v1 · P21 |
| Sobreventa solo por `allow_negative` | FR-003-042 · `_allow_negative` existente · §29 del prompt |
| `RELEASED` como handoff | ADR v1 ciclo de vida · 031 asume reserva firme |
| `FULFILLED` en despacho | R-D0-03-7 · CD-06 |
