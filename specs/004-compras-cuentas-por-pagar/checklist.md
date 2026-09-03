# CHECKLIST — 004-COMPRAS-CUENTAS-POR-PAGAR

| Campo | Valor |
|---|---|
| Iniciativa | 004-compras-cuentas-por-pagar |
| Versión | 1.0 |
| Ruta | `specs/004-compras-cuentas-por-pagar/checklist.md` |

Formato: | ID | Punto | Responsable | Evidencia | Estado | Bloqueante |

## Documentación

| ID | Punto | Responsable | Evidencia | Estado | Bloqueante |
|---|---|---|---|---|---|
| CHK-004-DOC-001 | Spec 004 completa | Producto | `spec.md` | ✔ | Sí |
| CHK-004-DOC-002 | Clarificaciones | Funcional | `clarifications.md` | ✔ | Sí |
| CHK-004-DOC-003 | Research técnico (aplicaciones, retenciones, integración 003/006) | Arquitecto | `research.md` | ✔ | No |
| CHK-004-DOC-004 | Plan y modelo de datos | Arquitecto/Datos | `plan.md`, `data-model.md` | ✔ | Sí |
| CHK-004-DOC-005 | Trazabilidad | Convergencia | `traceability-matrix.md` | ✔ | Sí |

## Datos y modelo

| ID | Punto | Responsable | Evidencia | Estado | Bloqueante |
|---|---|---|---|---|---|
| CHK-004-DB-001 | Requisición/cotización/orden con líneas y snapshot | Datos | `data-model.md` | ✔ | Sí |
| CHK-004-DB-002 | Recepción (lotes/seriales/calidad) vinculada a 003 | Datos | `data-model.md` | ✔ | Sí |
| CHK-004-DB-003 | Factura proveedor con clave de duplicidad | Datos | `data-model.md` | ✔ | Sí |
| CHK-004-DB-004 | Conciliación triple y devoluciones/notas | Datos | `data-model.md` | ✔ | Sí |
| CHK-004-DB-005 | CxP: OpenItem, Payment, Application, Advance, aging | Datos | `data-model.md` | ✔ | Sí |
| CHK-004-DB-006 | Retención referida a reglas versionadas | Datos | `data-model.md` | ✔ | Sí |
| CHK-004-DB-007 | Migración `0004_compras` (upgrade/downgrade) | Datos | Alembic | Pendiente (implementación) | Sí |

## Backend

| ID | Punto | Responsable | Evidencia | Estado | Bloqueante |
|---|---|---|---|---|---|
| CHK-004-BE-001 | Máquinas de estado (OC, recepción, factura) | Backend | `data-model.md`, DOC-03 §13 | ✔ | Sí |
| CHK-004-BE-002 | Aprobaciones por regla versionada (monto/categoría) | Backend | `research.md` | ✔ (especificado) | Sí |
| CHK-004-BE-003 | Duplicidad de factura del proveedor | Backend | `data-model.md` | ✔ | Sí |
| CHK-004-BE-004 | Recepción invoca 003 `receive` (sin duplicar saldos) | Backend | `research.md` | ✔ | Sí |
| CHK-004-BE-005 | Aplicaciones atómicas que no exceden saldo | Backend | `research.md` | ✔ (especificado) | Sí |
| CHK-004-BE-006 | Retención por regla de referencia (motor en 007) | Backend | `research.md` | ✔ | Sí |
| CHK-004-BE-007 | Contrato `Payment`/`Application` para 006 | Backend | `contracts/api-contracts.md` | ✔ | Sí |
| CHK-004-BE-008 | Aislamiento multiempresa e idempotencia | Backend | pruebas negativas | ✔ (especificado) | Sí |

## Frontend

| ID | Punto | Responsable | Evidencia | Estado | Bloqueante |
|---|---|---|---|---|---|
| CHK-004-UI-001 | Orden de compra (WF-04) con aprobación | Frontend | DOC-04 pantalla 09 | ✔ (especificado) | Sí |
| CHK-004-UI-002 | Conciliación triple (WF-05) con diferencias | Frontend | DOC-04 pantalla 10 | ✔ (especificado) | Sí |
| CHK-004-UI-003 | Recepción con lotes/seriales/calidad | Frontend | WF-04 | ✔ (especificado) | Sí |
| CHK-004-UI-004 | Factura del proveedor + estados | Frontend | WF-02 | ✔ (especificado) | Sí |
| CHK-004-UI-005 | Pago y retenciones (WF-02) con aprobación separada | Frontend | DOC-04 pantalla 15 | ✔ (especificado) | Sí |
| CHK-004-UI-006 | CxP: programación, aplicaciones y aging | Frontend | WF-05 | ✔ (especificado) | Sí |
| CHK-004-UI-007 | Listados sin scroll, búsqueda asíncrona, pantallas completas | Frontend | hereda 001/002/003 | ✔ | Sí |
| CHK-004-UI-008 | WCAG 2.2 AA y responsive | QA | hereda 001 | ✔ (especificado) | Sí |

## QA y operación

| ID | Punto | Responsable | Evidencia | Estado | Bloqueante |
|---|---|---|---|---|---|
| CHK-004-QA-001 | Plan de pruebas 004 | QA | `test-plan.md` | ✔ | Sí |
| CHK-004-QA-002 | Pruebas de duplicidad de factura y aplicaciones | QA | `test-plan.md` | ✔ (especificado) | Sí |
| CHK-004-QA-003 | Pruebas de integración recepción → 003 y contrato 006 | QA | `test-plan.md` | ✔ (especificado) | Sí |
| CHK-004-QA-004 | Pruebas de aislamiento negativo y retención por regla | QA | `test-plan.md` | ✔ (especificado) | Sí |

## Estado global

| Métrica | Valor |
|---|---|
| Puntos totales | 27 |
| Cumplidos (fase documental) | 27 (especificados) |
| Bloqueantes sin evidencia en fase documental | Ninguno |
| Implementación | Pendiente — requiere 001 certificada, 002/003 implementados y autorización |

---

# CHECKLIST — SPEC 019 · RECEPCIÓN FÍSICA (2026-09-03)

- [x] Las etapas documentadas identificadas **desde el DOCX**: son 12, no 10
- [x] Las 3 parciales identificadas · las de 019 completadas (8 de 8)
- [x] Propiedad de las 12 reconciliada: 8 de 019, 3 de 020, 1 de 022
- [x] Los siete proveedores enumerados desde el grafo y verificados
- [x] `GoodsReceipt` y `GoodsReceiptLine` auditados
- [x] Relación con el documento origen auditada y **reforzada** (la línea debe ser de la orden de la recepción)
- [x] Autoridad del almacén confirmada
- [x] Contrato de cantidad tecleada, unidad, presentación, factor congelado y cantidad base definido
- [x] Integración con `record_movement` definida y **corregida en su raíz**
- [x] Prueba de la caja ×12 definida y verde
- [x] Datos P23 identificados y capturados
- [x] Bultos, daño, identificación y referencia resueltos
- [x] Lote, serial y vencimiento: ya eran de 019, se preservan y el serial se normaliza
- [x] Integración documental disponible por 046; ninguna etapa la exige
- [x] Ciclo de vida y aceptación definidos
- [x] Invariante de ubicación nula definido y probado
- [x] Fronteras con 020, 021 y 022 definidas y probadas
- [x] Idempotencia y concurrencia definidas
- [x] Matriz de empresa, prueba de usuario AB y cross-tenant
- [x] Invariancia histórica probada
- [x] Pruebas sobre PostgreSQL definidas
- [x] Estados del frontend definidos
- [x] Regresiones definidas
