# Causa raíz
`UNSCOPED_BODY_REFERENCE` · ROOT_CAUSE_PROVEN = 1. `create_location_full`, `bulk_locations` y `patch_location` copian
`location_type_id`; el `_create` y el `_patch` de nodo copian `zone_type_id` (solo zonas); nadie comprueba la empresa. Las FK
simples `location_types.id` / `zone_types.id` prueban existencia, no pertenencia. `ZoneType` y `LocationType` son
`Scope.COMPANY` con `company_id` (ADR-D0-014): no hay ambigüedad. Misma clase que WAREHOUSE-BRANCH-CROSS-COMPANY.
