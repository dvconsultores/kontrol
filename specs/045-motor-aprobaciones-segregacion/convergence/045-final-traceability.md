# TRAZABILIDAD FINAL — SPEC 045 (§41)

Cadena exigida por P3: **Requisito → Tarea → Código → Prueba → Evidencia.**

## Cobertura

| Métrica | Valor |
|---|---:|
| Requisitos funcionales | 40 |
| Requisitos no funcionales | 7 |
| Tareas | 65 |
| Criterios de aceptación | 24 |
| **Requisitos sin tarea** | **0** |
| **Tareas sin requisito** | **0** |
| **Requisitos sin prueba (cuando la exigen)** | **0** |
| Requisitos cubiertos por contrato diferido | 1 — FR-045-067 (Spec 046) |

## Requisitos con prueba y evidencia

| Requisito | Tarea | Código | Prueba | Evidencia |
|---|---|---|---|---|
| FR-045-001..007 configuración | T-045-002/003/007/040 | `service.create_policy/add_rule/add_level`, `api` | `test_policy_versioning_and_activation`, `test_policy_lifecycle_by_api` | AC-01, AC-02 |
| FR-045-010..015 evaluación | T-045-011..014 | `ConditionEvaluator`, `compute_amount_base` | `test_amount_is_evaluated_in_base_currency`, `test_unevaluable_condition_never_passes_silently` | AC-03, AC-04 |
| FR-045-020..030 ciclo | T-045-020..026 | `require`, `decide`, `cancel` | 14 pruebas de ciclo + E2E 1-3 | AC-10..AC-15 |
| FR-045-027 vencimiento | T-045-031 | `mark_expired` | `test_expiry_marks_but_does_not_resolve` | AC-16 |
| FR-045-029 bloqueo del documento | T-045-062..065 | `integration.ensure_approved` | `test_domain_blocked_while_approval_pending` + E2E 1 | AC-17 |
| FR-045-040..046 segregación y delegación | T-045-029/030 | `_assert_can_decide`, `resolve_actors` | 5 pruebas negativas + E2E 4 | AC-05, AC-06, AC-18 |
| FR-045-050..052 obsolescencia | T-045-016/026 | `compute_fingerprint`, `document_changed` | 3 pruebas + E2E 6 | AC-07, AC-08 |
| FR-045-053..055 idempotencia y concurrencia | T-045-020/027/028 | `require` con `begin_nested`, `_lock_step` | 3 pruebas + E2E 8 y 9 **sobre PostgreSQL** | AC-09, AC-10 |
| FR-045-060..062 consulta | T-045-042/044/046 | `inbox`, `status`, `allowed_actions_for` | `test_inbox_is_transversal_across_domains` + E2E 1 | AC-19 |
| FR-045-063 permisos | T-045-006 | seed + migración `0016` | `test_requires_authentication` + E2E 5 | §36 |
| FR-045-064 auditoría | T-045-032 | `_audit` → `record_audit` | `test_audit_is_recorded` + E2E 1 | ADR-012 |
| FR-045-066 eventos | T-045-033 | `_emit` → `approval_events` | `test_domain_events_are_emitted` + E2E 11 | CVG-045-05 |
| FR-045-067 adjuntos | — | contrato declarado | — | **Diferido a 046** |
| FR-045-070..075 migración | T-045-060..067 | `integration.py` en 4 dominios, `0016` | `test_no_domain_keeps_its_own_approval_logic`, regresión de 4 dominios | AC-20, AC-21, AC-22 |
| NFR-045-03/04 a11y y responsive | T-045-078/079 | páginas | axe 22/22 ×3 · responsive 18/18 | AC-24 |
| NFR-045-06 PostgreSQL | todas | — | suite 276/276 sobre PG | CVG-045-01/02 |
| NFR-045-07 sin negocio en código | todas | — | búsqueda de literales | AC-23 |

## Estado de las tareas (§42)

| Estado | Cantidad | Nota |
|---|---:|---|
| `DONE` | **65** | Todas con evidencia verificable |
| `FAILED` | 0 | — |
| `BLOCKED` | 0 | — |
| `DEFERRED_EXTERNAL_DEPENDENCY` | 0 | FR-045-067 es contrato, no tarea |

T-045-072 (concurrencia sobre PostgreSQL), antes marcada `◐` por falta de motor,
queda **`DONE`**: ejecutada sobre PostgreSQL 16.2 real.

## Criterios de aceptación

**24 de 24 cubiertos.** AC-09, antes parcial, queda cubierto por completo con la
prueba de concurrencia real y el E2E de decisiones simultáneas.
