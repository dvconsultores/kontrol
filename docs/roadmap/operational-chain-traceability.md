# CADENA OPERATIVA — TRAZABILIDAD DEL CHECKPOINT

> Formato exigido: `| Spec | Requirement/Capability | Provider | Evidence | Current Status | Blocker | Next Dependency | Readiness |`.
> Cobertura exigida: 100 %. Huérfanos: 0.

## Requisitos del checkpoint (FR-OP)

| Requisito | Qué exige | Dónde se resuelve | Estado |
|---|---|---|---|
| FR-OP-001 | Estado medido de las seis Specs | checkpoint §«Cadena operativa» | ✔ |
| FR-OP-002 | Cada dependencia expresada como capacidad | `operational-chain-capability-matrix.md` | ✔ |
| FR-OP-003 | Capacidad de 019 para 020 clasificada | matriz, filas 020; checkpoint §019 | ✔ |
| FR-OP-004 | Preparación de 020 determinada | checkpoint §020: `READY_FOR_IMPLEMENTATION` | ✔ |
| FR-OP-005 | Dependencia de 021 sobre 020 determinada | capacidad de excepción, no registro obligatorio | ✔ |
| FR-OP-006 | Dependencia de 022 sobre 021 determinada | estado de origen inequívoco | ✔ |
| FR-OP-007 | Dependencia de 031 sobre 022 determinada | existencia ubicada y cantidad por ubicación | ✔ |
| FR-OP-008 | Dependencias de 032 determinadas | 031 + 022; 024 y 030 satisfechas | ✔ |
| FR-OP-009 | Punto de disponibilidad identificado | checkpoint §«Punto de disponibilidad»: aceptación de la recepción | ✔ |
| FR-OP-010 | Semántica de ubicación nula identificada | checkpoint §«Semántica de la ubicación»: legítima entre recepción y put-away | ✔ |
| FR-OP-011 | Comportamiento recepción→movimiento clasificado | checkpoint §«Movimiento de recepción»: A/C/B por dimensión | ✔ |
| FR-OP-012 | Propiedad de lote, serial y vencimiento | checkpoint §«Datos de entrada y P23»: los tres en 019 | ✔ |
| FR-OP-013 | Handoff de 030 preservado | matriz, filas 031/032: satisfecho y sin cambios | ✔ |
| FR-OP-014 | Ninguna dependencia histórica sin evidencia | §«Bloqueos reconciliados»: dos retiradas, dos reformuladas | ✔ |
| FR-OP-015 | Ninguna capacidad satisfecha sigue como bloqueo | ídem: 008 y 030 dejan de bloquear | ✔ |
| FR-OP-016 | Ruta crítica recalculada | checkpoint §«Ruta crítica» | ✔ |
| FR-OP-017 | Una Spec seleccionada | `NEXT SPEC = 019` | ✔ |
| FR-OP-018 | Sin cambios de código productivo | `git diff` sobre `resources/` y `alembic/` = 0 | ✔ |
| FR-OP-019 | Master 56 actualizado | `master-56-specs-status.md` | ✔ |
| FR-OP-020 | Trazabilidad 100 % | este documento | ✔ |

**20/20. Requisitos huérfanos: 0.**

## Tareas (T-OP)

| Rango | Tareas | Resultado |
|---|---|---|
| 001 | Baseline del repositorio | checkpoint §«Baseline remedida» |
| 002-005 | 019: requisitos, implementación, pruebas, capacidades | checkpoint §019 |
| 006-008 | 020: requisitos, implementación, dependencias | checkpoint §020 · matriz |
| 009-011 | 021: requisitos, implementación, dependencias | checkpoint §021 · matriz |
| 012-014 | 022: requisitos, implementación, dependencias | checkpoint §022 · matriz |
| 015-017 | 031: requisitos, implementación, dependencias | checkpoint §031 · matriz |
| 018-020 | 032: requisitos, implementación, dependencias | checkpoint §032 · matriz |
| 021-022 | Capacidades de 023 y 024 | matriz §«Proveedores» |
| 023 | Movimiento de recepción | checkpoint §«Movimiento de recepción» |
| 024 | Inventario sin ubicar | checkpoint §«Semántica de la ubicación» |
| 025 | Transición a disponible | checkpoint §«Punto de disponibilidad» |
| 026 | Propiedad de lote/serial/vencimiento | checkpoint §«Datos de entrada y P23» |
| 027-028 | Camino feliz y camino con incidencia | checkpoint §«Camino feliz» y §«Camino con incidencia» |
| 029 | Grafo de capacidades | `operational-chain-capability-matrix.md` |
| 030-031 | Bloqueos históricos y activos | checkpoint §«Bloqueos reconciliados» · `active-blockers.md` · `resolved-blockers.md` |
| 032 | Ruta crítica | checkpoint §«Ruta crítica» · `critical-path-analysis.md` |
| 033 | Ranking | checkpoint §«Ranking de preparación» · `readiness-ranking.md` |
| 034 | Selección | `next-spec-decision.md` |
| 035-036 | Master 56 y trazabilidad | `master-56-specs-status.md` · este documento |
| 037-038 | Implementación documental y convergencia | commit · `operational-chain-convergence.md` |

**38/38. Tareas huérfanas: 0.**

## Specs de la cadena

| Spec | Capacidad | Proveedor | Evidencia | Estado | Bloqueo | Siguiente dependencia | Preparación |
|---|---|---|---|---|---|---|---|
| 019 | Recepción contra orden con lote, vencimiento y serial | 017, 010, 008, 023, 024 | `GoodsReceipt(+Line)`, `accept_receipt`, `test_purchasing.py` | PARTIAL | ninguno | — | **lista** |
| 019 | Presentación y unidad de lo recibido | 011 | columnas presentes, nadie las escribe | ausente | deuda propia | — | pendiente en 019 |
| 020 | Registro y resolución de incidencias | — | cero tablas | NOT_STARTED | ninguno | 019 (capacidad ✓) | **lista** |
| 021 | Conciliación y liberación formal | 019, 020, 023 | solo `quality_status` | PARTIAL | 020 + estados de mercancía | 020, 023 | bloqueada |
| 022 | Ubicar mercancía confirmada | 021, 008, 023 | cero proceso | NOT_STARTED | estado de origen | 021 | bloqueada |
| 031 | Cola y ruta de picking | 030 ✓, 022 ✗, 008 ✓ | `pick_lists`; línea sin ubicación ni secuencia | BLOCKED | existencia ubicada | 022 | bloqueada |
| 032 | Ejecución y consolidación | 031 ✗, 022 ✗, 024 ✓, 030 ✓ | esqueleto de despacho | BLOCKED | 031 + 022 | 031 | bloqueada |

## Proveedores

| Proveedor | Capacidad consumida por la cadena | Evidencia | Estado |
|---|---|---|---|
| 008 | Ubicaciones con `sequence` y capacidad; `/locations/ordered` | modelo y 11 rutas | COMPLETE |
| 010 | Catálogo de productos | `catalog_items` | PARTIAL, suficiente |
| 011 | `to_base` y columnas de unidad | motor y columnas en todas las líneas | COMPLETE |
| 023 | Movimientos, saldos, dimensión de ubicación y lote/serial | `inventory` | PARTIAL, **insuficiente para estados** |
| 024 | Lotes con vencimiento, seriales con estado | `inventory_lots`, `product_serials` | PARTIAL, suficiente |
| 029 | Pedido con origen comercial | `sales_quotes`, `sales_orders` | COMPLETE |
| 030 | Pedido `RELEASED` con reservas por línea | `order_dict`, `reservations` | COMPLETE |
| 045 | Motor único de aprobaciones | `approvals` | COMPLETE |
| 046 | Documentos y evidencia | `documents` | RECONVERGED |

**Cobertura: 100 %. Huérfanos: 0.**
