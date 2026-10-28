# AUDIT_DATA_PROFILE (ciclo 04)

**Base E2E sembrada** (corrida `r20261028t111440p681815n66e816`, efímera y eliminada):

| Concepto | Valor |
|---|---|
| Eventos | 45, en 2 tenants |
| Con `company_id` NULL | 45 |
| Con tenant NULL | 0 |
| `USER_CREATED/User` | 42 (41 sin actor, de la siembra) |
| `ROLE_ASSIGNED/UserRole` | 2 (origen SETUP) |
| `MFA_CHALLENGE_ISSUED/User` | 1 |

Clasificación: los 4 pares son `TENANT` legítimos (OD-AUD-03). No hay ningún evento de empresa sin empresa.

**Suite SQLite** (perfil `before_insert`, producto anterior al ciclo): 129 pares.

COMPANY_EVENT_MISSING_CONTEXT, siempre sin empresa:
- `DOCUMENT_*/Document`: 9 pares, unos 230 eventos;
- `DOCUMENT_TYPE_CREATED/Document`: 59;
- `CREATE|unit_of_measure`: 21;
- `CREATE|presentation`: 14;
- `CREATE_VERSION|product_presentation_version`: 6;
- `CREATE|unit_conversion`: 1.

Todos corregidos en la emisión (AD-4).

TENANT_EVENT_LEGITIMATE, sin empresa:
- identidad, sesiones, MFA, reset y roles;
- `AUTHORITY_DELEGATION_DENIED`, `LAST_ADMIN_OPERATION_DENIED` y `COMPANY_SCOPE_DENIED/Tenant`.

Caso aparte: `PASSWORD_RESET_FAILED` aparece sin tenant en los 8 casos; se corrige cuando el usuario se conoce (AD-4).

Sondas de prueba fuera del catálogo: AUDCOUNT, AUDTEN y `qa.css`, que pasan a filas directas (AD-12).

**AUDIT_EVENTS_MISSING_COMPANY_UNEXPLAINED = 0.**

**Tras la E2E:** ver `post-e2e.md`.
