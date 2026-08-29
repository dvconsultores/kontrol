# VALIDACIÓN DE SEGURIDAD — SPEC 045 (§36, §37)

Todo verificado **en backend**. Una ruta protegida en el frontend no cuenta como control.

| Control | Verificación | Resultado |
|---|---|---|
| Autenticación | `GET /approvals/policies` y `/inbox` sin sesión | **401** |
| Autorización por permiso | `require_permission("aprobaciones", …)` en los 22 endpoints; recurso con 6 acciones | ✔ deny by default |
| Aislamiento por empresa | `inbox` con `company_id` de otra empresa | **0 resultados** |
| Aislamiento en pruebas | `test_inbox_isolated_by_company`, `test_inbox_isolated_by_company` (API) | ✔ |
| IDOR | Solicitud de otra empresa no consultable | ✔ |
| Escalada de privilegios | El creador no obtiene acciones por serlo | ✔ `allowed_actions == []` |
| Autoaprobación | `allow_self_approval=false` → **403** `APPROVAL_SELF_APPROVAL_DENIED` | ✔ |
| Segregación de funciones | `requires_segregation` → el creador no figura entre elegibles y recibe **403** | ✔ |
| Delegación no elude segregación | Delegado que es el creador → **403** | ✔ `test_delegation_cannot_bypass_segregation` |
| Solicitudes obsoletas | Documento modificado → `OBSOLETE`, `allowed_actions == []`, resolución rechazada | ✔ |
| Replay / doble envío | Dos POST simultáneos → una sola solicitud, mismo id | ✔ |
| Idempotencia | Clave `(documento, huella)` + índice único parcial | ✔ |
| Concurrencia | Dos decisiones simultáneas → una prospera, la otra 409; **una sola** decisión registrada | ✔ sobre PostgreSQL |
| Integridad de la auditoría | `AuditEvent` append-only; cada decisión con actor, motivo y delegación | ✔ |

## Multiempresa (§37)

Empresa A no puede, verificado por API y por consulta a la base:

- ver políticas de B — filtradas por `company_id` en todo endpoint
- aprobar solicitudes de B — no aparecen en su bandeja
- utilizar reglas de B — `get_active_policy` filtra por empresa
- acceder al historial de B — `status()` filtra por empresa

## Versionado de políticas (§38)

`test_policy_snapshot_is_frozen`: documento aprobado bajo v1; se crea y activa v2
con umbral distinto; el documento conserva `policy_version = 1` y su
`policy_snapshot` intacto. **La historia no se reescribe.**

## Delegación (§39)

Vigencia (`valid_from`/`valid_to`), ámbito (proceso, sucursal, centro de costo),
usuario otorgante y receptor, empresa, revocación y auditoría. Una delegación
revocada **no invalida** las decisiones ya tomadas bajo ella. No existe delegación
indefinida accidental: sin `valid_to` se declara explícitamente como sin límite y
queda registrada como tal.

## `allowed_actions` (§40)

Calculado en backend por solicitud y por paso. Verificado en tres estados:
elegible → `["approve","reject","return"]`; creador con segregación → `[]`;
solicitud resuelta → `[]`. El frontend solo representa lo que el backend autoriza.
