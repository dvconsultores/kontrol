# CRITERIOS DE ACEPTACIÓN — 011-HOMOLOGACION-LIBERACION

| Campo | Valor |
|---|---|
| Iniciativa | 011-homologacion-liberacion |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Ruta | `specs/011-homologacion-liberacion/acceptance-criteria.md` |

> Convención: `AC-011-XXX`. Cada AC vincula un FR (ver traceability-matrix.md).

## Homologación

| ID | Criterio | FR |
|---|---|---|
| AC-011-001 | El administrador registra un acto de homologación en DRAFT con versión fiscal, modalidad, acto formal y evidencia con SHA-256. | FR-011-001 |
| AC-011-002 | La homologación pasa a SUBMITTED con evidencia; un evaluador distinto del creador puede aprobar o rechazar. | FR-011-002, FR-011-003 |
| AC-011-003 | Quien crea/somete no puede aprobar su propia homologación (segregación). | FR-011-003 |
| AC-011-004 | Cada transición genera un evento append-only (`homologation_events`). | FR-011-004 |
| AC-011-005 | El sistema no reporta HOMOLOGADO sin acto formal + versión fiscal aprobada. | FR-011-005 |

## Liberación

| ID | Criterio | FR |
|---|---|---|
| AC-011-010 | Se crea una versión en DRAFT con changelog y gates. | FR-011-010 |
| AC-011-011 | La versión pasa a CANDIDATE con los gates verificados. | FR-011-011 |
| AC-011-012 | La liberación a RELEASED solo ocurre con homologación aprobada + gates verdes + licencia FULL_ACCESS; en otro caso BLOCKED. | FR-011-012 |
| AC-011-013 | La liberación registra quién/cuándo/versión y bloquea re-liberar versiones anteriores. | FR-011-013 |
| AC-011-020 | El timeline de homologación y liberación es consultable. | FR-011-020 |
| AC-011-021 | Frontend operativo: registro/evaluación, versiones/gates y timeline. | FR-011-021 |
| AC-011-100 | Aislamiento por instalación; idempotencia; hash de evidencia; decimal exacto. | FR-011-100 |
