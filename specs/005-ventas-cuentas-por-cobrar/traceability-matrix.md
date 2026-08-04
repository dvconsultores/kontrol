# MATRIZ DE TRAZABILIDAD — 005-VENTAS-CUENTAS-POR-COBRAR

| Campo | Valor |
|---|---|
| Iniciativa | 005-ventas-cuentas-por-cobrar |
| Versión | 1.0 |
| Ruta | `specs/005-ventas-cuentas-por-cobrar/traceability-matrix.md` |

Formato: Requisito → Fuente → Tarea → Prueba. Cadena **Requisito → Spec → Plan → Tarea → Código → Prueba → Evidencia** (Constitución P3).

## Matriz por historia (US → FR)

| Historia | FRs |
|---|---|
| US-005-001 | FR-005-001 |
| US-005-002 | FR-005-002 |
| US-005-003 | FR-005-010, FR-005-012 |
| US-005-004 | FR-005-011, FR-005-020 |
| US-005-005 | FR-005-021 |
| US-005-006 | FR-005-023, FR-005-024 |
| US-005-007 | FR-005-022 |
| US-005-008 | FR-005-030, FR-005-031, FR-005-033, FR-005-034 |
| US-005-009 | FR-005-040, FR-005-041, FR-005-043, FR-005-044 |
| US-005-010 | FR-005-042, FR-005-045, FR-005-047 |
| US-005-011 | FR-005-046 |
| US-005-012 | FR-005-048, FR-005-100, FR-005-102 |

## Matriz FR → Tarea → Prueba

| FR | Tarea | Prueba |
|---|---|---|
| FR-005-001/002 | T-005-001 | Test de flujo |
| FR-005-010/011/012 | T-005-002 | Test de crédito/máquina |
| FR-005-020/021/022/023/024 | T-005-003 | Test de integración 003 |
| FR-005-030/031/032/033/034 | T-005-004 | Test de estados/snapshot |
| FR-005-045/047 | T-005-005 | Test de nota/CxC |
| FR-005-040/100 | T-005-006 | Test de saldo |
| FR-005-041/102 | T-005-007 | Test de cobro/idempotencia |
| FR-005-042 | T-005-008 | Test de aplicación/saldo |
| FR-005-043/046 | T-005-009 | Test de aging/anticipo |
| FR-005-044 | T-005-010 | Test de retención |
| FR-005-048 | T-005-011 | Test de permisos |
| FR-005-101 | T-005-012/013 | Contract test |
| NFR multiempresa | T-005-019 | Pytest negativo |
| NFR concurrencia | T-005-020 | Pytest de concurrencia |
| NFR accesibilidad | T-005-021 | axe |
| CHK-005-DB-006 | T-005-022 | CI migración |

## Verificación de cobertura

| Verificación | Resultado |
|---|---|
| Requisitos sin tarea | Ninguno |
| Tareas sin requisito | Ninguna |
| Historias sin FR | Ninguna |
| Criterios de aceptación mapeados | ✔ (`acceptance-criteria.md`) |
