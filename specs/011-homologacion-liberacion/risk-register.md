# REGISTRO DE RIESGOS — 011-HOMOLOGACION-LIBERACION

| Campo | Valor |
|---|---|
| Iniciativa | 011-homologacion-liberacion |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Ruta | `specs/011-homologacion-liberacion/risk-register.md` |

> Convención: `RSK-011-XXX`. Probabilidad/Impacto: B(aja)/M(edia)/A(lta).

| ID | Riesgo | Prob | Imp | Mitigación | Dueño | Estado |
|---|---|---|---|---|---|---|
| RSK-011-001 | Declarar homologado sin acto formal | M | A | Regla FR-011-005 en backend + UI | Arquitecto | Activo |
| RSK-011-002 | Liberar sin homologación documentada | M | A | Gate FR-011-012 bloquea la liberación | Arquitecto | Activo |
| RSK-011-003 | Falta de segregación (crear y aprobar) | M | A | Validación de creador ≠ evaluador | Producto | Activo |
| RSK-011-004 | Pérdida de integridad del acto formal | B | M | Hash SHA-256 de evidencia + eventos append-only | Arquitecto | Activo |
| RSK-011-005 | Confusión con liberación de lotes | M | M | Documentado en CL-011-03 y nomenclatura UI | Producto | Activo |
| RSK-011-006 | Gates falsos (marcados sin verificar) | M | M | Registro por gate con quién/cuándo | Arquitecto | Activo |
