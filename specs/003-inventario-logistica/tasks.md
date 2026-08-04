# TASKS — 003-INVENTARIO-LOGISTICA

| Campo | Valor |
|---|---|
| Iniciativa | 003-inventario-logistica |
| Versión | 1.0 |
| Ruta | `specs/003-inventario-logistica/tasks.md` |

Formato: | ID | Requisito | Tarea | Dependencia | Archivos | Prueba | Responsable |

> Las tareas se ejecutan únicamente tras autorización expresa **003-inventario-logistica**, con **001 certificada** y **002 implementado**.

| ID | Requisito | Tarea | Dependencia | Archivos | Prueba | Responsable |
|---|---|---|---|---|---|---|
| T-003-001 | FR-003-001/002/003 | Crear Warehouse + Location + migración `0003` | 002 (maestros head) | `inventory/warehouses/`, migración `0003_inventario.py` | Test de maestros/estados | Datos |
| T-003-002 | FR-003-023/024 | Crear MovementType (versionado) + seeds | T-003-001 | `inventory/movements/`, `scripts/seed.py` | Test de tipos/seed | Datos |
| T-003-003 | FR-003-020/021/022 | Motor de movimientos balanceados e inmutables + reverso vinculado | T-003-002 | `inventory/movements/` | Test de balanceo/reverso | Backend |
| T-003-004 | FR-003-010/011/012/013 | InventoryBalance (cache reconstruible) + consulta de existencias | T-003-003 | `inventory/balances/` | Test de reconstrucción | Backend |
| T-003-005 | FR-003-030/032/035/036 | InventoryLot (unicidad, vencimiento, estados) | T-003-003 | `inventory/lots/` | Test de lote/unicidad | Backend |
| T-003-006 | FR-003-031/033/035 | ProductSerial (serial/IMEI, unicidad, historial) | T-003-005 | `inventory/lots/` | Test de serial | Backend |
| T-003-007 | FR-003-034 | Política FEFO y bloqueo de vencidos | T-003-005 | `inventory/lots/` | Test FEFO | Backend |
| T-003-008 | FR-003-040/041/042/043 | Reservation (reserva/liberación/expiración, disponible) | T-003-004 | `inventory/reservations/` | Test de reserva/concurrencia | Backend |
| T-003-009 | FR-003-050/051/052 | PickList y confirmación de salida (integración) | T-003-008 | `inventory/movements/`, `inventory/reservations/` | Test de picking/salida | Backend |
| T-003-010 | FR-003-060/061/062 | Transfer + máquina de estados + diferencias | T-003-003, T-003-008 | `inventory/transfers/` | Test de máquina de estados | Backend |
| T-003-011 | FR-003-070/071 | StockCount (plan, congelamiento, líneas, diferencias) | T-003-004 | `inventory/counts/` | Test de conteo | Backend |
| T-003-012 | FR-003-072/073 | Ajustes con motivo/evidencia/costo/aprobación y segregación | T-003-011 | `inventory/adjustments/` | Test de ajuste/segregación | Backend |
| T-003-013 | FR-003-080/081/082/083 | CostLayer + valoración promedio/FIFO + costo de salida | T-003-003 | `inventory/costing/` | Test de capas/valoración | Backend |
| T-003-014 | FR-003-090/091/092 | Kardex + trazabilidad origen/destino + auditoría | T-003-004, T-003-013 | `inventory/balances/` | Test de kardex/auditoría | Backend |
| T-003-015 | FR-003-104 | API de integración v1 para 004/005 (receive/reserve/release/pick/ship) | T-003-003, T-003-008, T-003-013 | `contracts/api-contracts.md`, servicios | Contract test | Backend |
| T-003-016 | FR-003-103 | Página de existencias (filtros, `allowed_actions`) | T-003-015 | `src/modules/inventario/existencias/` | E2E | Frontend |
| T-003-017 | FR-003-090 | Página de kardex (historial por producto/lote/serial) | T-003-015 | `src/modules/inventario/kardex/` | Component/E2E | Frontend |
| T-003-018 | FR-003-060/061 | Página de transferencias (solicitud → recepción) | T-003-015 | `src/modules/inventario/transferencias/` | E2E | Frontend |
| T-003-019 | FR-003-070/071 | Página de conteos (plan → líneas → diferencias) | T-003-015 | `src/modules/inventario/conteos/` | E2E | Frontend |
| T-003-020 | FR-003-072/073 | Página de ajustes (motivo/evidencia/aprobación) | T-003-015 | `src/modules/inventario/ajustes/` | Component/E2E | Frontend |
| T-003-021 | FR-003-001/002 | Páginas de almacenes/ubicaciones (maestros) | T-003-015 | `src/modules/inventario/almacenes/` | Component/E2E | Frontend |
| T-003-022 | NFR (concurrencia) | Pruebas de concurrencia: reservas/salidas simultáneas sin sobreadjudicación | T-003-008, T-003-013 | `tests/` | Pytest de concurrencia | QA |
| T-003-023 | NFR (multiempresa) | Pruebas de aislamiento negativo | T-003-015 | `tests/` | Pytest negativo | QA |
| T-003-024 | NFR (rendimiento) | Pruebas de índices, paginación y reconstrucción de balance | T-003-004 | `tests/` | Prueba de rendimiento | QA |
| T-003-025 | NFR (accesibilidad) | axe + responsive en rutas de inventario | T-003-016..021 | Playwright | axe | QA |
| T-003-026 | CHK-003-DB-006 | CI: migración `0003` upgrade/downgrade | T-003-001 | `.github/workflows` | CI | DevSecOps |
| T-003-027 | CHK-003-OP-002 | Reconstrucción incremental de balance (job/outbox) | T-003-004 | job + `inventory/balances/` | Test de reconstrucción | Backend |

## Notas

- No existen tareas genéricas; todas son atómicas, con dependencias y pruebas.
- T-003-001 requiere la infraestructura de 001 (Alembic, Base, módulos) certificada y el head `0002_maestros` de 002.
- La reserva (T-003-008) y la valoración (T-003-013) son los puntos de mayor riesgo de concurrencia; se prueban explícitamente (T-003-022).
