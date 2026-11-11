# Trazabilidad PROC-10

| Requisito del sponsor | FR | Tareas | Prueba |
|---|---|---|---|
| GOV-PROC-013 · tipo | FR-001, FR-003 | T1, T2 | `test_gov_proc10_garantias` (reglas, porcentaje fuera de rango, OTRA sin nombre) |
| GOV-PROC-013 · emisor | FR-002, FR-004 | T1, T2 | prueba de emisor (BANCO con banco, RIF único, otro ente) |
| GOV-PROC-013 · vigencia | FR-004, FR-006 | T1, T2, T3 | vigencia derivada; E2E (días y por vencer) |
| GOV-PROC-013 · monto | FR-003, FR-004, FR-005 | T1, T2, T3 | suficiencia con monto fijo; NO_EVALUABLE porcentual; E2E |
| GOV-PROC-013 · renovación | FR-007, FR-011 | T1, T2, T3 | renovación con historia; E2E |
| GOV-PROC-013 · liberación | FR-009 | T1, T2, T3 | liberación con acto y precondición; E2E con MFA |
| GOV-PROC-013 · ejecución | FR-010 | T1, T2, T3 | ejecución única, monto, concurrencia; E2E (acto, confirmación, historial, cronología) |
| Encargo §21 sustitución | FR-008 | T1, T2, T3 | sustitución de fiel cumplimiento; E2E (anterior «Sustituida», nueva encadenada) |
| Encargo §25-27, §43-46 | FR-012, FR-013, FR-014 | T1, T2 | negativas, aislamiento, inmutabilidad, auditoría, cronología, SoD |
| Encargo §30-34, §59-60 | FR-015 | T2, T3 | E2E (Axe, 390/320) |

Requisitos huérfanos: 0. Tareas huérfanas: 0.
