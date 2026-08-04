# MATRIZ DE TRAZABILIDAD — 004-COMPRAS-CUENTAS-POR-PAGAR

| Campo | Valor |
|---|---|
| Iniciativa | 004-compras-cuentas-por-pagar |
| Versión | 1.0 |
| Ruta | `specs/004-compras-cuentas-por-pagar/traceability-matrix.md` |

Formato: Requisito → Fuente → Tarea → Prueba. Cadena **Requisito → Spec → Plan → Tarea → Código → Prueba → Evidencia** (Constitución P3).

## Matriz por historia (US → FR)

| Historia | FRs |
|---|---|
| US-004-001 | FR-004-001, FR-004-002 |
| US-004-002 | FR-004-010, FR-004-011 |
| US-004-003 | FR-004-012 |
| US-004-004 | FR-004-020, FR-004-021, FR-004-022, FR-004-023 |
| US-004-005 | FR-004-030, FR-004-031, FR-004-032, FR-004-033, FR-004-034 |
| US-004-006 | FR-004-040, FR-004-041, FR-004-042, FR-004-043 |
| US-004-007 | FR-004-050, FR-004-051, FR-004-052 |
| US-004-008 | FR-004-060, FR-004-061 |
| US-004-009 | FR-004-070, FR-004-071, FR-004-072, FR-004-075 |
| US-004-010 | FR-004-073, FR-004-074, FR-004-076 |
| US-004-011 | FR-004-075 |
| US-004-012 | FR-004-041 |
| US-004-013 | FR-004-104, FR-004-100 |

## Matriz FR → Tarea → Prueba

| FR | Tarea | Prueba |
|---|---|---|
| FR-004-001/002 | T-004-001 | Test de flujo |
| FR-004-010/011/012 | T-004-002 | Test de comparación |
| FR-004-020/021/022/023 | T-004-003 | Test de máquina/aprobación |
| FR-004-030/031/032/033/034 | T-004-004 | Test de integración 003 |
| FR-004-040/041/042/043 | T-004-005 | Test de duplicidad |
| FR-004-050/051/052 | T-004-006 | Test de diferencias |
| FR-004-060/061 | T-004-007 | Test de nota/CxP |
| FR-004-070/071/104 | T-004-008 | Test de saldo |
| FR-004-072/101 | T-004-009 | Test de pago/idempotencia |
| FR-004-073 | T-004-010 | Test de aplicación/saldo |
| FR-004-074/075 | T-004-011 | Test de aging/anticipo |
| FR-004-076/078 | T-004-012 | Test de retención |
| FR-004-077 | T-004-013 | Test de permisos |
| FR-004-103 | T-004-014/015 | Contract test |
| FR-004-100 | T-004-023 | Pytest negativo |
| NFR concurrencia | T-004-024 | Pytest de concurrencia |
| NFR accesibilidad | T-004-025 | axe |
| CHK-004-DB-007 | T-004-026 | CI migración |

## Verificación de cobertura

| Verificación | Resultado |
|---|---|
| Requisitos sin tarea | Ninguno |
| Tareas sin requisito | Ninguna |
| Historias sin FR | Ninguna |
| Criterios de aceptación mapeados | ✔ (`acceptance-criteria.md`) |
