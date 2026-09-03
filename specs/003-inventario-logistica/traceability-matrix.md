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

---

# TRAZABILIDAD — CICLO DIRIGIDO DE SALDO MULTIESTADO (2026-09-03)

Ciclo de auditoría. **Cero código de producto.** La trazabilidad cubre lo auditado y lo decidido,
no lo implementado, porque el ciclo se detuvo antes de `/speckit.implement` por dos OQ materiales.

| Requisito | Regla ADR | Estado del catálogo | Evidencia | Resultado |
|---|---|---|---|---|
| IMP-023-MS-001 · el estado es autoridad de inventario | R-D0-10-1 | los 15 | `uq_inventory_balances_key` incluye `state` | **Ya cumplido** |
| IMP-023-MS-002 · los estados vienen del ADR | R-D0-10-2 | los 15 | catálogo extraído, §4 del ciclo | **Verificado** |
| IMP-023-MS-003 · no hay estados inventados | — | los 15 | `VENCIDO` es de lote/serial (`FR-003-035`), no de mercancía | **Verificado** |
| IMP-023-MS-004 · vendibilidad definida | R-D0-10-3 | los 15 | exclusivamente `DISPONIBLE` | **Cerrado por el ADR** |
| IMP-023-MS-005 · reservabilidad definida | R-D0-03-5 · POL-D0-002 §7 | los 15 | solo `DISPONIBLE`; la reserva no cambia custodia | **Cerrado por autoridad** |
| IMP-023-MS-006 · disponible excluye lo no vendible | POL-D0-002 §1 | `DISPONIBLE` | la consulta ya filtra por estado | **Ya cumplido** |
| IMP-023-MS-007 · la 030 no reserva lo no reservable | R-D0-03-5 | `DISPONIBLE` | `lock_balance` por defecto `DISPONIBLE`; así lo llama ventas | **Ya cumplido** |
| IMP-023-MS-008 · el movimiento conserva el estado | R-D0-10-5 | — | `InventoryMovement` **no tiene columna de estado** | **HUECO ESTRUCTURAL** |
| IMP-023-MS-009 · el saldo diferencia por estado | R-D0-10-5 | los 15 | la clave ya lo permite; solo hay filas `DISPONIBLE` | **Parcial: capacidad sin ejercicio** |
| IMP-023-MS-010 · la clave incluye las dimensiones | — | los 15 | empresa, almacén, ubicación, producto, lote, serial, estado | **Ya cumplido** |
| IMP-023-MS-011 · la reclasificación conserva físico | R-D0-10-5 | — | derivable, no requiere decisión | **Definido, no implementado** |
| IMP-023-MS-012 · la reclasificación deja rastro | R-D0-10-5 | — | imposible sin IMP-023-MS-008 | **Bloqueado por el hueco** |
| IMP-023-MS-013 · no altera unidad ni cantidad base | Spec 011 | — | el saldo ya acumula base desde la Spec 019 | **Ya cumplido** |
| IMP-023-MS-014/015/016/017 · preserva almacén, ubicación, `NULL`, lote y serial | Spec 008 · 024 | — | la clave los lleva; `COALESCE` los hace únicos | **Ya cumplido** |
| IMP-023-MS-018 · sin negativo ilegal | — | — | derivable de la conservación | **Definido, no implementado** |
| IMP-023-MS-019/020 · idempotencia y concurrencia | POL-D0-002 §5 | — | patrón de la Spec 030 disponible y probado | **Definido, no implementado** |
| IMP-023-MS-021..024 · empresa, tenant, usuario AB, contexto | ARCH-MC-001 | — | el saldo es `Scope.COMPANY`; sin cambios | **Ya cumplido** |
| IMP-023-MS-025/026 · un solo motor y un solo disponible | — | — | Constitution Gate PASS | **Verificado** |
| IMP-023-MS-027 · los llamantes siguen funcionando | — | — | diez puntos localizados y atribuidos | **Verificado** |
| IMP-023-MS-028 · la caja ×12 de la Spec 019 | Spec 011 · 019 | `DISPONIBLE` | sin cambios de código; regresión intacta | **Ya cumplido** |
| IMP-023-MS-029 · la reserva solo sobre elegible | R-D0-03-5 | `DISPONIBLE` | la suma nunca cruza estados | **Ya cumplido** |
| IMP-023-MS-030 · el total se reconstruye del ledger | R-D0-10-5 | — | `recompute_balances` colapsaría todo en `DISPONIBLE` | **HUECO ESTRUCTURAL** |
| IMP-023-MS-031/032 · paridad ORM/Alembic/OpenAPI | — | — | sin delta: no se tocó nada | **N/A en este ciclo** |
| IMP-023-MS-033 · trazabilidad | — | — | esta tabla | **100 % de lo auditado** |
| IMP-023-MS-034 · deuda P0 propia | — | — | el ciclo no introduce código | **0** |
| IMP-023-MS-035 · la 021 puede consumir estados no vendibles | R-D0-10-4 | — | **exige OQ-023-MS-01 y OQ-023-MS-02** | **BLOQUEADO** |

**Cobertura del alcance auditado: 100 %. Huérfanos: 0. OQ materiales: 2.**
