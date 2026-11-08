# ORG-06 · USER_OFFICIAL_CARDINALITY_CONTRACT

| Pregunta | Respuesta | Fundamento |
|---|---|---|
| CAN_ONE_USER_MAP_TO_MULTIPLE_OFFICIALS_SAME_ENTITY | **NO** en la misma vigencia | Una cuenta con dos identidades rompe la atribución del actor |
| CAN_ONE_OFFICIAL_MAP_TO_MULTIPLE_ACTIVE_USERS_SAME_ENTITY | **NO** en la misma vigencia | Dos cuentas activas de una persona evaden maker-checker y SoD. Ninguna fuente exige lo contrario |
| CAN_ONE_USER_MAP_TO_DIFFERENT_OFFICIALS_ACROSS_ENTITIES | **SÍ** | `GovernmentOfficial` es propio del ente; el usuario es del tenant |
| CAN_LINK_CHANGE_OVER_TIME | **SÍ** | Cerrado un vínculo, puede abrirse otro; la historia se conserva |
| CAN_LINK_OVERLAP | **NO**, ni por cuenta ni por funcionario | Dos exclusiones PostgreSQL sobre vínculos ACTIVO |
| WHAT_HAPPENS_IF_USER_DISABLED | No actúa; el vínculo y su historia siguen; autoridad NINGUNA | `users.status != ACTIVE` |
| WHAT_HAPPENS_IF_OFFICIAL_INACTIVE | Autoridad NINGUNA; no se activa un vínculo nuevo | `gov_officials.estado` |

**Actor efectivo:** el conjunto de cuentas que han representado alguna vez al mismo funcionario. Maker-checker y SoD comparan ese conjunto, no el `user_id`. Así, una cuenta nueva de la misma persona no aprueba lo que preparó la anterior.

**Vínculo sin autoridad:** `USER_LINK_GRANTS_FUNCTIONAL_AUTHORITY_BY_ITSELF = 0`. La autoridad nace de la ocupación vigente de ORG-04, el cargo y sus competencias.

**Soporte:** el vínculo es CONFIGURACIÓN DE SEGURIDAD, no acto administrativo. Lleva motivo obligatorio y referencia documental opcional. El acto que habilita autoridad sigue siendo el de ORG-04.
