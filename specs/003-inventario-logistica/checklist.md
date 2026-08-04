# CHECKLIST — 003-INVENTARIO-LOGISTICA

| Campo | Valor |
|---|---|
| Iniciativa | 003-inventario-logistica |
| Versión | 1.0 |
| Ruta | `specs/003-inventario-logistica/checklist.md` |

Formato: | ID | Punto | Responsable | Evidencia | Estado | Bloqueante |

## Documentación

| ID | Punto | Responsable | Evidencia | Estado | Bloqueante |
|---|---|---|---|---|---|
| CHK-003-DOC-001 | Spec 003 completa | Producto | `spec.md` | ✔ | Sí |
| CHK-003-DOC-002 | Clarificaciones | Funcional | `clarifications.md` | ✔ | Sí |
| CHK-003-DOC-003 | Research técnico (concurrencia, FEFO, costeo, cache) | Arquitecto | `research.md` | ✔ | No |
| CHK-003-DOC-004 | Plan y modelo de datos | Arquitecto/Datos | `plan.md`, `data-model.md` | ✔ | Sí |
| CHK-003-DOC-005 | Trazabilidad | Convergencia | `traceability-matrix.md` | ✔ | Sí |

## Datos y modelo

| ID | Punto | Responsable | Evidencia | Estado | Bloqueante |
|---|---|---|---|---|---|
| CHK-003-DB-001 | Warehouse + Location (custodia) | Datos | `data-model.md` | ✔ | Sí |
| CHK-003-DB-002 | Movimientos balanceados e inmutables + reverso | Datos | `data-model.md` | ✔ | Sí |
| CHK-003-DB-003 | Lotes/seriales/vencimiento con unicidad y estados | Datos | `data-model.md` | ✔ | Sí |
| CHK-003-DB-004 | Reservas y balance (disponible = físico − reservas) | Datos | `data-model.md` | ✔ | Sí |
| CHK-003-DB-005 | Capas de costo + método versionado | Datos | `data-model.md` | ✔ | Sí |
| CHK-003-DB-006 | Migración `0003_inventario` (upgrade/downgrade) | Datos | Alembic | Pendiente (implementación) | Sí |

## Backend

| ID | Punto | Responsable | Evidencia | Estado | Bloqueante |
|---|---|---|---|---|---|
| CHK-003-BE-001 | Motor de movimientos transaccional (bloqueo, idempotencia) | Backend | `research.md`, contratos | ✔ (especificado) | Sí |
| CHK-003-BE-002 | Reservas atómicas sin sobreadjudicación | Backend | `research.md` | ✔ (especificado) | Sí |
| CHK-003-BE-003 | FEFO y bloqueo de vencidos | Backend | `research.md` | ✔ (especificado) | Sí |
| CHK-003-BE-004 | Máquina de estados de transferencia | Backend | `data-model.md`, DOC-03 §13 | ✔ | Sí |
| CHK-003-BE-005 | Conteo → diferencias → ajuste aprobado (segregación) | Backend | `data-model.md` | ✔ | Sí |
| CHK-003-BE-006 | Valoración de capas (promedio/FIFO) | Backend | `research.md` | ✔ (especificado) | Sí |
| CHK-003-BE-007 | API de integración v1 para 004/005 | Backend | `contracts/api-contracts.md` | ✔ | Sí |
| CHK-003-BE-008 | Aislamiento multiempresa | Backend | pruebas negativas | ✔ (especificado) | Sí |

## Frontend

| ID | Punto | Responsable | Evidencia | Estado | Bloqueante |
|---|---|---|---|---|---|
| CHK-003-UI-001 | Existencias (listado con filtros y `allowed_actions`) | Frontend | WF-01 + DOC-04 pantalla 04 | ✔ (especificado) | Sí |
| CHK-003-UI-002 | Kardex (historial por producto/lote/serial) | Frontend | WF-03 | ✔ (especificado) | Sí |
| CHK-003-UI-003 | Transferencia (solicitud → recepción) | Frontend | WF-04 | ✔ (especificado) | Sí |
| CHK-003-UI-004 | Conteo (plan → líneas → diferencias) | Frontend | WF-05 | ✔ (especificado) | Sí |
| CHK-003-UI-005 | Ajuste con motivo/evidencia/aprobación | Frontend | WF-02 + DOC-04 pantalla 12 | ✔ (especificado) | Sí |
| CHK-003-UI-006 | Almacenes/ubicaciones (maestros) | Frontend | WF-02 | ✔ (especificado) | Sí |
| CHK-003-UI-007 | Listados sin scroll horizontal, búsqueda asíncrona, pantallas completas (ADR-015) | Frontend | hereda 001/002 | ✔ | Sí |
| CHK-003-UI-008 | WCAG 2.2 AA y responsive | QA | hereda 001 | ✔ (especificado) | Sí |

## QA y operación

| ID | Punto | Responsable | Evidencia | Estado | Bloqueante |
|---|---|---|---|---|---|
| CHK-003-QA-001 | Plan de pruebas 003 | QA | `test-plan.md` | ✔ | Sí |
| CHK-003-QA-002 | Pruebas de concurrencia (reservas/salidas simultáneas) | QA | `test-plan.md` | ✔ (especificado) | Sí |
| CHK-003-QA-003 | Pruebas de aislamiento negativo y unicidad lote/serial | QA | `test-plan.md` | ✔ (especificado) | Sí |
| CHK-003-QA-004 | Pruebas de valoración (promedio/FIFO) y kardex | QA | `test-plan.md` | ✔ (especificado) | Sí |
| CHK-003-OP-001 | Seeds idempotentes (tipos de movimiento, estados) | Datos | `plan.md` | ✔ (especificado) | No |
| CHK-003-OP-002 | Job de reconstrucción de balance (o reconstrucción incremental) | Backend | `research.md` | ✔ (especificado) | No |

## Estado global

| Métrica | Valor |
|---|---|
| Puntos totales | 31 |
| Cumplidos (fase documental) | 31 (especificados) |
| Bloqueantes sin evidencia en fase documental | Ninguno |
| Implementación | Pendiente — requiere 001 certificada, 002 implementado y autorización |
