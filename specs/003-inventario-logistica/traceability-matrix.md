# MATRIZ DE TRAZABILIDAD — 003-INVENTARIO-LOGISTICA

| Campo | Valor |
|---|---|
| Iniciativa | 003-inventario-logistica |
| Versión | 1.0 |
| Ruta | `specs/003-inventario-logistica/traceability-matrix.md` |

Formato: Requisito → Fuente → Tarea → Prueba. Cadena **Requisito → Spec → Plan → Tarea → Código → Prueba → Evidencia** (Constitución P3).

## Matriz por historia (US → FR)

| Historia | FRs |
|---|---|
| US-003-001 | FR-003-010, FR-003-012, FR-003-013 |
| US-003-002 | FR-003-090, FR-003-092 |
| US-003-003 | FR-003-030, FR-003-032, FR-003-034, FR-003-036 |
| US-003-004 | FR-003-031, FR-003-033, FR-003-036 |
| US-003-005 | FR-003-040, FR-003-041, FR-003-042, FR-003-043 |
| US-003-006 | FR-003-060, FR-003-061, FR-003-062 |
| US-003-007 | FR-003-070, FR-003-071 |
| US-003-008 | FR-003-072, FR-003-073 |
| US-003-009 | FR-003-080, FR-003-081, FR-003-082, FR-003-083 |
| US-003-010 | FR-003-050, FR-003-051, FR-003-052 |
| US-003-011 | FR-003-020, FR-003-021, FR-003-022, FR-003-024 |
| US-003-012 | FR-003-035 |
| US-003-013 | FR-003-092 |

## Matriz FR → Tarea → Prueba

| FR | Tarea | Prueba |
|---|---|---|
| FR-003-001/002/003/004 | T-003-001 | Test de maestros/estados |
| FR-003-023/024 | T-003-002 | Test de tipos/seed |
| FR-003-020/021/022 | T-003-003 | Test de balanceo/reverso |
| FR-003-010/011/012/013 | T-003-004 | Test de reconstrucción |
| FR-003-030/032/035/036 | T-003-005 | Test de lote/unicidad |
| FR-003-031/033/035 | T-003-006 | Test de serial |
| FR-003-034 | T-003-007 | Test FEFO |
| FR-003-040/041/042/043 | T-003-008 | Test de reserva/concurrencia |
| FR-003-050/051/052 | T-003-009 | Test de picking/salida |
| FR-003-060/061/062 | T-003-010 | Test de máquina de estados |
| FR-003-070/071 | T-003-011 | Test de conteo |
| FR-003-072/073 | T-003-012 | Test de ajuste/segregación |
| FR-003-080/081/082/083 | T-003-013 | Test de capas/valoración |
| FR-003-090/091/092 | T-003-014 | Test de kardex/auditoría |
| FR-003-104 | T-003-015 | Contract test |
| FR-003-103 | T-003-016..021 | E2E + axe |
| NFR concurrencia | T-003-022 | Pytest de concurrencia |
| NFR multiempresa | T-003-023 | Pytest negativo |
| NFR rendimiento | T-003-024 | Prueba de rendimiento |
| NFR accesibilidad | T-003-025 | axe |
| CHK-003-DB-006 | T-003-026 | CI migración |
| CHK-003-OP-002 | T-003-027 | Test de reconstrucción |

## Verificación de cobertura

| Verificación | Resultado |
|---|---|
| Requisitos sin tarea | Ninguno |
| Tareas sin requisito | Ninguna |
| Historias sin FR | Ninguna |
| Criterios de aceptación mapeados | ✔ (`acceptance-criteria.md`) |
