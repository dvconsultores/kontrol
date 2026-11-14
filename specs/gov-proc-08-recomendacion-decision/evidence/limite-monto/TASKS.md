# AAL · Tareas

Gate previo: `BLOCKER = CRITICAL = CONTRADICTIONS = OWNER CONFLICT = 0`, `MATERIAL OQ = 0`, `UNKNOWN = 0` y trazabilidad del 100 %. La regla monetaria la fijó la dueña (OQ-OMA-01), y Claude fijó el contrato, la escala, la comparación y los vectores (casos 1–7). Por eso las tareas sensibles se delegan como código mecánico sobre un contrato cerrado.

| Tarea | Qué | EXECUTOR | MODEL | SECURITY_SENSITIVE | EGRESS_SAFE | RETRY_MAX | FILES | TEST | DONE_WHEN |
|---|---|---|---|---|---|---|---|---|---|
| T001 | Delta, gate, plan y tareas | CLAUDE | n-a | NO | n-a | 0 | delta y evidencia | — | gate PASS |
| T002 | Servicio del límite, hook en la ejecución, vista previa, catálogo y recuento | DEEPSEEK | deepseek-v4-pro | YES (autoridad) | YES | 2 | `service_decision_limite.py`, `service_decision_resolver.py`, `service_decision.py`, `audit_catalog_entries.py`, `test_audit_catalog_backup.py` | ruff, mypy y PROC-08 existente | contrato AAL-01..14 literal |
| T003 | Pruebas backend: 7 casos, concurrencia, auditoría, vista previa y aislamiento | DEEPSEEK | deepseek-v4-pro | YES | YES | 2 | `tests/test_gov_proc08_limite_monto.py` | PG dirigida | verde en PG y las mutaciones mueren |
| T004 | Panel de UI y Vitest | DEEPSEEK | deepseek-v4-pro | NO | YES | 2 | `ExpedienteDecision.tsx` y su test | typecheck, lint y Vitest | 5 datos y 6 estados sin UUID |
| T005 | E2E: ayudantes, recorrido y garantías | DEEPSEEK | deepseek-v4-pro | NO | YES | 2 | `helpers/gobierno.ts`, `gobierno-decision.spec.ts` y `gobierno-garantias.spec.ts` | E2E dirigida | bloqueo → suficiente → 201; Axe en 3 anchos |
| T006 | QA final, UAT, cierre y publicación | CLAUDE | n-a | — | — | — | evidencia | ronda final | puertas en PASS |

**Separación de frentes:** los ficheros de P1 (BUD-05, presupuesto) no se tocan. `audit_catalog_entries.py` y `test_audit_catalog_backup.py` son compartidos, pero solo se añade una línea y se cambia el recuento.
