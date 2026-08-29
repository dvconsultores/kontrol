# MODELO DE DATOS — SPEC 045

**8 tablas** nuevas en el esquema del módulo `approvals`.

> **Corrección de convergencia (2026-08-29).** Este documento declaraba 7 tablas, pero `plan.md` §5
> ya exigía registrar los eventos de dominio «en tabla propia del motor» y FR-045-066 los hace
> obligatorios. La octava tabla, `approval_events`, no es alcance nuevo: es una inconsistencia
> interna de la Spec, resuelta a favor de `plan.md`. Todas con `company_id` y filtro de alcance
(ADR-011, P11). Importes en `Numeric` (ADR-016); fechas en `DateTime(timezone=True)` (P21).

## `approval_policies`

Política de aprobación versionada por empresa y tipo de proceso.

| Campo | Tipo | Notas |
|---|---|---|
| `id` | UUID | |
| `company_id` | FK companies | |
| `process_type` | String(64) | Catálogo extensible por datos (FR-045-006) |
| `code`, `name` | String | |
| `version` | Integer | Correlativo por (empresa, proceso) |
| `valid_from`, `valid_to` | DateTime tz | `valid_to` nulo = vigente |
| `status` | String(32) | `DRAFT · ACTIVE · CLOSED` |
| `requires_segregation` | Boolean | El creador no resuelve (FR-045-040) |
| `allow_self_approval` | Boolean | Independiente de la anterior (FR-045-041) |
| `distinct_actors_across_levels` | Boolean | Defecto `true` con segregación (CL-045-07) |
| `base_currency` | String(8) | Moneda de evaluación de umbrales |
| `created_by`, `created_at`, `updated_at` | | |

**Restricciones:** único `(company_id, process_type, version)`; **no puede haber dos políticas
`ACTIVE` solapadas** para el mismo `(company_id, process_type)`.

## `approval_rules`

Condición de disparo dentro de una política.

| Campo | Tipo | Notas |
|---|---|---|
| `id` | UUID | |
| `policy_id` | FK approval_policies | |
| `sequence` | Integer | Orden de evaluación |
| `name` | String | |
| `conditions` | JSON | Lista de predicados tipados `{field, operator, value}` combinados con `AND` |
| `condition_fields` | JSON | Campos que participan — **base de la huella** (CL-045-05) |
| `is_exception` | Boolean | Marca de excepción |
| `risk_class` | String(32) | Clasificación opcional |

Varias reglas de la misma política expresan el `OR`. Si aplican varias, los niveles se acumulan sin
duplicar (FR-045-013).

## `approval_levels`

| Campo | Tipo | Notas |
|---|---|---|
| `id` | UUID | |
| `rule_id` | FK approval_rules | |
| `level_order` | Integer | Secuencial; 1 abre primero |
| `resolver_type` | String(32) | `ROLE · USER · SCOPE_OWNER` |
| `resolver_ref` | String(120) | Rol, usuario o expresión de alcance |
| `quorum_type` | String(16) | `ANY · ALL · N_OF_M` |
| `quorum_n` | Integer nulo | Para `N_OF_M` |
| `can_delegate` | Boolean | |
| `sla_hours` | Integer nulo | Vencimiento del paso (FR-045-027) |

## `approval_requests`

| Campo | Tipo | Notas |
|---|---|---|
| `id` | UUID | |
| `company_id` | FK companies | |
| `process_type` | String(64) | |
| `document_type`, `document_id` | String | Referencia al documento de origen |
| `policy_id`, `policy_version` | FK / Integer | **Snapshot de la política aplicada** (FR-045-020) |
| `policy_snapshot` | JSON | Copia de reglas y niveles vigentes al crear |
| `fingerprint` | String(64) | SHA-256 de los campos de condición |
| `fingerprint_fields` | JSON | Qué campos la componen — auditable |
| `amount_base` | Numeric(18,2) nulo | Monto normalizado a moneda base |
| `base_currency`, `rate_snapshot` | String / Numeric(14,6) | Tasa usada (research §4) |
| `requested_by`, `requested_at` | | |
| `status` | String(32) | Máquina de estados de `state-machines.md` |
| `current_level` | Integer | |
| `resolved_at`, `resolution_reason` | | |
| `previous_request_id` | UUID nulo | Encadena tras devolución (FR-045-030) |
| `idempotency_key` | String(120) | `(document_ref, fingerprint)` (FR-045-053) |

**Restricciones:** único `(company_id, document_type, document_id, fingerprint)` sobre solicitudes no
terminales — impide duplicar solicitud para el mismo estado del documento.

## `approval_steps`

| Campo | Tipo | Notas |
|---|---|---|
| `id` | UUID | |
| `request_id` | FK approval_requests | |
| `level_order` | Integer | |
| `quorum_type`, `quorum_n` | | Copiados del nivel — snapshot |
| `eligible_actors` | JSON | **Congelado al abrir el paso** (FR-045-014) |
| `status` | String(32) | `PENDING · IN_REVIEW · APPROVED · REJECTED · RETURNED · SKIPPED · EXPIRED` |
| `opened_at`, `due_at`, `closed_at` | DateTime tz | |
| `version` | Integer | Control optimista para concurrencia (FR-045-054) |

## `approval_decisions`

Append-only. Nunca se edita ni se borra (P5).

| Campo | Tipo | Notas |
|---|---|---|
| `id` | UUID | |
| `step_id` | FK approval_steps | |
| `actor_id` | FK users | Quien decide efectivamente |
| `on_behalf_of_id` | FK users nulo | Delegante, si actuó por delegación |
| `delegation_id` | FK approval_delegations nulo | Cuál delegación lo habilitó (FR-045-045) |
| `decision` | String(16) | `APPROVE · REJECT · RETURN · CANCEL` |
| `reason` | Text | **Obligatorio** en `REJECT` y `RETURN` (FR-045-026) |
| `observations` | Text nulo | |
| `decided_at` | DateTime tz | |

## `approval_delegations`

| Campo | Tipo | Notas |
|---|---|---|
| `id` | UUID | |
| `company_id` | FK companies | |
| `grantor_id`, `grantee_id` | FK users | |
| `scope_process_type` | String(64) nulo | Nulo = todos los procesos, declarado explícitamente |
| `scope_branch_id`, `scope_cost_center_id` | FK nulos | Ámbito acotado (CL-045-08) |
| `valid_from`, `valid_to` | DateTime tz | |
| `reason` | Text | Motivo, especialmente en sustitución temporal |
| `is_temporary_substitution` | Boolean | FR-045-044 |
| `revoked_at`, `revoked_by` | | Revocar no invalida lo ya decidido (FR-045-046) |

## `approval_events`

Evento de dominio emitido por el motor (FR-045-066). El motor **emite**; no notifica.

| Campo | Tipo | Notas |
|---|---|---|
| `id` | UUID | |
| `company_id` | String(36) | |
| `request_id`, `step_id` | String(36) nulos | |
| `event_type` | String(64) | `approval.requested` · `step_opened` · `decided` · `resolved` · `obsolete` · `step_expired` |
| `payload` | JSON | |
| `occurred_at` | DateTime tz | |

La Spec 047 los consumirá. 045 no conoce a 047.

## Vinculación con otras capacidades

| Necesidad | Mecanismo | Estado |
|---|---|---|
| Auditoría | `AuditEvent` existente (ADR-012) — **no se crea rastro paralelo** | Disponible |
| Evidencia adjunta | `AttachmentLink(entity_type='ApprovalRequest', entity_id=…)` (ADR-D0-008) | **Contrato declarado; activo cuando exista la Spec 046** |
| Notificación | Eventos de dominio emitidos por el motor | **Consumidos por la Spec 047** |

## Diagrama de relaciones

```
approval_policies 1─n approval_rules 1─n approval_levels
        │
        │ snapshot
        ▼
approval_requests 1─n approval_steps 1─n approval_decisions
        │                                      │
        │                                      └─ n─1 approval_delegations
        └─ 0..1 previous_request_id (auto-referencia tras devolución)
```

## Migración

`0015_approvals` — **migración de esquema pura**: 8 tablas + renombrado de la tabla legada
`approval_requests` (regulatorio) a `regulatory_approval_requests`.

`0016_approvals_backfill` — **migración de datos**: permisos del recurso `aprobaciones` en
instalaciones existentes + traslado del histórico regulatorio con
`policy_version = LEGACY_UNVERSIONED` (FR-045-074). Idempotente.

> **Corrección de convergencia.** La separación esquema/datos no era opcional: una migración de
> datos rompe `alembic upgrade --sql` (modo offline), que es cómo se valida la cadena en dialecto
> PostgreSQL sin instancia. El proyecto ya aplicaba esta separación en 0013.
