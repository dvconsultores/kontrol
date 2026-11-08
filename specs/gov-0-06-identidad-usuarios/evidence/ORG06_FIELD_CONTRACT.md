# ORG-06 · ORG06_FIELD_CONTRACT

## `gov_user_official_links`
| Campo | Por qué | Origen |
|---|---|---|
| `company_id` | Ente del vínculo | Contexto del servidor, nunca el cliente |
| `codigo` | Referencia legible `VIN-00001` | Servidor |
| `user_id` | Cuenta. FK a `users`; sin duplicar autenticación | Selector |
| `official_id` | Identidad. FK a `gov_officials` | Selector |
| `desde`, `hasta` | Vigencia propia, distinta de la ocupación | Formulario |
| `fin_efectivo` | Cierre real sin reescribir `hasta` | Acción |
| `status` | BORRADOR, ACTIVO, CERRADO, REVOCADO, DESCARTADO | Servidor |
| `motivo`, `soporte` | Razón obligatoria; referencia documental opcional | Formulario |
| `motivo_fin`, `activated_*`, `ended_*`, `created_by`, `version` | Trazabilidad y concurrencia | Servidor |

**No se guardan** `position_id`, `unit_id` ni alcance: se derivan de ORG-04 y ORG-03 en cada consulta.

## `gov_user_official_link_history`
Historia inmutable: `link_id`, `company_id`, `tipo`, `detalle` (antes, después, funcionario, cuenta).

## `gov_role_categories`
Clasificación configurable de un rol existente en una categoría de separación. `company_id`, `role_id`, `categoria`, `desde`, `hasta`, `status` (ACTIVA, RETIRADA), `motivo`, `version`. Historia en `gov_role_category_history`. Los roles siguen en el núcleo.

Categorías: OPERATIVO, APROBADOR, CONTROL_INTERNO, AUDITORIA, ADMINISTRACION_TECNICA. No crean roles ni permisos: clasifican los que el ente ya tiene.

## `gov_identity_policies`
Una fila por ente. `exige_identidad` (por defecto falso), `version`, `motivo`. Historia en `gov_identity_policy_history`. Con la exigencia activa, las operaciones protegidas requieren vínculo, ocupación vigente y competencia. Por defecto queda inactiva para que el ente vincule primero a su gente sin bloquearse.
