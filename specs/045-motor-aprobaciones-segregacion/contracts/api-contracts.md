# CONTRATOS DE API — SPEC 045

Prefijo `/api/v1/approvals`. Todos los endpoints exigen sesión y permiso; todos filtran por empresa
activa (P11). Errores conforme al contrato de errores de 001.

## Configuración de políticas

| Método | Ruta | Permiso | Descripción |
|---|---|---|---|
| `GET` | `/policies` | `aprobaciones:view` | Lista con filtros por proceso y estado |
| `POST` | `/policies` | `aprobaciones:configure` | Crea política en `DRAFT` |
| `GET` | `/policies/{id}` | `aprobaciones:view` | Detalle con reglas y niveles |
| `PATCH` | `/policies/{id}` | `aprobaciones:configure` | Edita solo en `DRAFT`. ETag → 409 |
| `POST` | `/policies/{id}/activate` | `aprobaciones:configure` | Activa y cierra la versión anterior |
| `POST` | `/policies/{id}/close` | `aprobaciones:configure` | Cierra vigencia. **No elimina** |
| `POST` | `/policies/{id}/rules` | `aprobaciones:configure` | Añade regla |
| `PATCH` | `/policies/{id}/rules/{rule_id}` | `aprobaciones:configure` | Edita regla en `DRAFT` |
| `POST` | `/policies/{id}/rules/{rule_id}/levels` | `aprobaciones:configure` | Añade nivel |
| `GET` | `/process-types` | `aprobaciones:view` | Catálogo extensible |

## Evaluación y solicitud — consumo por dominios

| Método | Ruta | Permiso | Descripción |
|---|---|---|---|
| `POST` | `/evaluate` | `aprobaciones:view` | **No crea nada.** Devuelve niveles previstos o «no requiere» |
| `POST` | `/requests` | `aprobaciones:create` | Crea solicitud. **Idempotente** por `(document_ref, fingerprint)` |
| `GET` | `/requests` | `aprobaciones:view` | Lista con filtros |
| `GET` | `/requests/{id}` | `aprobaciones:view` | Detalle con pasos, decisiones y `allowed_actions` |
| `GET` | `/requests/by-document` | `aprobaciones:view` | Historial por `document_type` + `document_id` |
| `POST` | `/requests/{id}/cancel` | `aprobaciones:create` | Cancela. Motivo obligatorio |

### `POST /evaluate` — petición

```json
{
  "process_type": "PURCHASE_ORDER",
  "context": {
    "amount": 15000.00,
    "currency": "USD",
    "rate_snapshot": 36.5,
    "branch_id": "…",
    "cost_center_id": "…",
    "category": "CAPEX",
    "is_exception": false
  }
}
```

### `POST /evaluate` — respuesta

```json
{
  "requires_approval": true,
  "policy_id": "…", "policy_version": 3,
  "amount_base": 547500.00, "base_currency": "VED",
  "levels": [
    {"level_order": 1, "resolver_type": "ROLE", "resolver_ref": "…", "quorum_type": "ANY"},
    {"level_order": 2, "resolver_type": "ROLE", "resolver_ref": "…", "quorum_type": "N_OF_M", "quorum_n": 2}
  ],
  "fingerprint_fields": ["amount", "currency", "cost_center_id"]
}
```

> El motor **nunca** devuelve umbrales ni valores de política a un usuario sin
> `aprobaciones:configure`: informa qué niveles aplican, no por qué monto se disparó.

## Bandeja y resolución

| Método | Ruta | Permiso | Descripción |
|---|---|---|---|
| `GET` | `/inbox` | `aprobaciones:approve` | «Mis aprobaciones»: pasos abiertos donde el usuario es elegible, directamente o por delegación |
| `POST` | `/steps/{id}/approve` | `aprobaciones:approve` | Aprueba. `If-Match` con `version` → 409 |
| `POST` | `/steps/{id}/reject` | `aprobaciones:approve` | Rechaza. **`reason` obligatorio** |
| `POST` | `/steps/{id}/return` | `aprobaciones:approve` | Devuelve. **`reason` obligatorio** |

### Códigos de error específicos

| Código | HTTP | Cuándo |
|---|---|---|
| `APPROVAL_NOT_ELIGIBLE` | 403 | El actor no está entre los elegibles del paso |
| `APPROVAL_SEGREGATION_VIOLATION` | 403 | El creador intenta resolver con segregación activa |
| `APPROVAL_SELF_APPROVAL_DENIED` | 403 | Autoaprobación prohibida por política |
| `APPROVAL_REQUEST_OBSOLETE` | 409 | El documento cambió tras solicitar |
| `APPROVAL_STEP_VERSION_CONFLICT` | 409 | Decisión concurrente sobre el mismo paso |
| `APPROVAL_STEP_NOT_OPEN` | 409 | El paso no está `IN_REVIEW` |
| `APPROVAL_DUPLICATE_DECISION` | 409 | El actor ya decidió sobre este paso |
| `APPROVAL_REASON_REQUIRED` | 422 | Rechazo o devolución sin motivo |
| `APPROVAL_POLICY_OVERLAP` | 409 | Dos políticas activas solapadas |
| `APPROVAL_CONDITION_UNEVALUABLE` | 422 | Falta un dato de la condición (FR-045-015) |

## Delegaciones

| Método | Ruta | Permiso | Descripción |
|---|---|---|---|
| `GET` | `/delegations` | `aprobaciones:view` | Propias y, con permiso, de la empresa |
| `POST` | `/delegations` | `aprobaciones:delegate` | Crea con ámbito y vigencia |
| `POST` | `/delegations/{id}/revoke` | `aprobaciones:delegate` | Revoca. No invalida lo decidido |

## `allowed_actions`

Calculado en backend por solicitud y por paso (FR-045-062). El frontend **no** deduce permisos:

```json
{ "allowed_actions": ["approve", "reject", "return"] }
```

Un actor no elegible recibe `[]`. Ocultar el botón es presentación; la autoridad es el 403 (P6).

## Eventos de dominio emitidos

Para consumo futuro de la Spec 047. El motor los registra; no los envía.

| Evento | Cuándo |
|---|---|
| `approval.requested` | Solicitud creada |
| `approval.step_opened` | Paso abierto — quién debe actuar |
| `approval.decided` | Decisión registrada |
| `approval.resolved` | Solicitud terminal |
| `approval.obsolete` | Solicitud invalidada por cambio |
| `approval.step_expired` | Vencimiento de paso |

## Contrato con la Spec 046 (adjuntos)

Cuando exista, la evidencia se vincula con
`AttachmentLink(entity_type="ApprovalRequest", entity_id=<request_id>, document_type_id=<tipo>)`.
**Este contrato no exige cambios en el modelo de 045** (CL-045-10).
