# CHECKLIST — 005-VENTAS-CUENTAS-POR-COBRAR

| Campo | Valor |
|---|---|
| Iniciativa | 005-ventas-cuentas-por-cobrar |
| Versión | 1.0 |
| Ruta | `specs/005-ventas-cuentas-por-cobrar/checklist.md` |

Formato: | ID | Punto | Responsable | Evidencia | Estado | Bloqueante |

## Documentación

| ID | Punto | Responsable | Evidencia | Estado | Bloqueante |
|---|---|---|---|---|---|
| CHK-005-DOC-001 | Spec 005 completa | Producto | `spec.md` | ✔ | Sí |
| CHK-005-DOC-002 | Clarificaciones | Funcional | `clarifications.md` | ✔ | Sí |
| CHK-005-DOC-003 | Research técnico (crédito, reserva/despacho, CxC, integración 003/004/006) | Arquitecto | `research.md` | ✔ | No |
| CHK-005-DOC-004 | Plan y modelo de datos | Arquitecto/Datos | `plan.md`, `data-model.md` | ✔ | Sí |
| CHK-005-DOC-005 | Trazabilidad | Convergencia | `traceability-matrix.md` | ✔ | Sí |

## Datos y modelo

| ID | Punto | Responsable | Evidencia | Estado | Bloqueante |
|---|---|---|---|---|---|
| CHK-005-DB-001 | Cotización/pedido/orden con líneas y snapshot | Datos | `data-model.md` | ✔ | Sí |
| CHK-005-DB-002 | Despacho (PickList/Shipment) vinculado a 003 | Datos | `data-model.md` | ✔ | Sí |
| CHK-005-DB-003 | Factura de venta con snapshot fiscal | Datos | `data-model.md` | ✔ | Sí |
| CHK-005-DB-004 | Notas y devoluciones | Datos | `data-model.md` | ✔ | Sí |
| CHK-005-DB-005 | CxC reutiliza el motor de 004 (RECEIVABLE) | Datos | `data-model.md` | ✔ | Sí |
| CHK-005-DB-006 | Migración `0005_ventas` (upgrade/downgrade) | Datos | Alembic | Pendiente (implementación) | Sí |

## Backend

| ID | Punto | Responsable | Evidencia | Estado | Bloqueante |
|---|---|---|---|---|---|
| CHK-005-BE-001 | Máquinas de estado (OV, factura de venta) | Backend | `data-model.md`, DOC-03 §13 | ✔ | Sí |
| CHK-005-BE-002 | Análisis de crédito y aprobación por regla versionada | Backend | `research.md` | ✔ (especificado) | Sí |
| CHK-005-BE-003 | Reserva/picking/despacho invoca 003 | Backend | `research.md` | ✔ | Sí |
| CHK-005-BE-004 | Bloqueo de despacho (documento/vencido/no coincide) | Backend | `research.md` | ✔ (especificado) | Sí |
| CHK-005-BE-005 | CxC: cobros idempotentes y aplicaciones atómicas (reutiliza 004) | Backend | `research.md` | ✔ | Sí |
| CHK-005-BE-006 | Retención sufrida registrada y aplicada | Backend | `research.md` | ✔ | Sí |
| CHK-005-BE-007 | Contrato cobros/aplicaciones para 006 | Backend | `contracts/api-contracts.md` | ✔ | Sí |
| CHK-005-BE-008 | Aislamiento multiempresa e idempotencia | Backend | pruebas negativas | ✔ (especificado) | Sí |

## Frontend

| ID | Punto | Responsable | Evidencia | Estado | Bloqueante |
|---|---|---|---|---|---|
| CHK-005-UI-001 | Orden de venta (WF-04) con crédito/margen/reserva separados | Frontend | DOC-04 pantalla 11 | ✔ (especificado) | Sí |
| CHK-005-UI-002 | Preparación y despacho (lotes/seriales/documentos) | Frontend | DOC-04 pantalla 12 | ✔ (especificado) | Sí |
| CHK-005-UI-003 | Factura de venta (base VES, tasa snapshot) | Frontend | DOC-04 pantalla 13 | ✔ (especificado) | Sí |
| CHK-005-UI-004 | Cobro multimoneda (WF-02) | Frontend | DOC-04 pantalla 14 | ✔ (especificado) | Sí |
| CHK-005-UI-005 | CxC: aging y gestión de cobranza | Frontend | WF-05 | ✔ (especificado) | Sí |
| CHK-005-UI-006 | Listados sin scroll, búsqueda asíncrona, pantallas completas | Frontend | hereda 001/002/003/004 | ✔ | Sí |
| CHK-005-UI-007 | WCAG 2.2 AA y responsive | QA | hereda 001 | ✔ (especificado) | Sí |

## QA y operación

| ID | Punto | Responsable | Evidencia | Estado | Bloqueante |
|---|---|---|---|---|---|
| CHK-005-QA-001 | Plan de pruebas 005 | QA | `test-plan.md` | ✔ | Sí |
| CHK-005-QA-002 | Pruebas de crédito, reserva y bloqueo de despacho | QA | `test-plan.md` | ✔ (especificado) | Sí |
| CHK-005-QA-003 | Pruebas de CxC: cobros, aplicaciones, aging, multiempresa | QA | `test-plan.md` | ✔ (especificado) | Sí |
| CHK-005-QA-004 | Pruebas de integración 003/004 y contrato 006 | QA | `test-plan.md` | ✔ (especificado) | Sí |

## Estado global

| Métrica | Valor |
|---|---|
| Puntos totales | 26 |
| Cumplidos (fase documental) | 26 (especificados) |
| Bloqueantes sin evidencia en fase documental | Ninguno |
| Implementación | Pendiente — requiere 001 certificada, 002/003/004 implementados y autorización |

---

# CHECKLIST — SPEC 029 · IMPLEMENTACIÓN

- [x] Esquema de cotización auditado — `price_list` era texto libre
- [x] Esquema de pedido auditado — sin vínculo con la cotización
- [x] Campos `P23` identificados — 0 columnas de origen en ambas líneas
- [x] Contrato del resolutor identificado — `resolve_price` de la Spec 012
- [x] Origen del precio definido y persistido
- [x] Origen del descuento definido y persistido
- [x] Unidad y presentación conservadas — Spec 011, sin redefinir
- [x] Ciclo de la cotización definido — no existía
- [x] Vigencia comprobada al enviar, aceptar y convertir
- [x] Cardinalidad definida — 1:1, con índice único parcial
- [x] Política de reprecio definida — **no** hay reprecio silencioso
- [x] Cambio manual con motivo obligatorio y valor resuelto conservado
- [x] Frontera 029/030 explícita, y comprobada por medición
- [x] `D0-03` excluida: la reserva existente no se tocó
- [x] Seguridad de rutas hijas
- [x] Prueba del usuario con acceso a las dos, en los dos sentidos
- [x] Prueba entre tenants
- [x] Pruebas de invariancia histórica — tres
- [x] Precisión igualada con el maestro
- [x] Permisos existentes reutilizados — sin nombres nuevos
- [x] Auditoría de transición y conversión
- [x] API y OpenAPI — 3 operaciones, las 3 con empresa
- [x] Frontend: precio automático, motivo del manual, detalle con origen
- [x] Regresión completa

---

# CHECKLIST — SPEC 030 · PREVIA A IMPLEMENTACIÓN (D0-03 CLOSED, 2026-09-02)

## Contrato
- [x] Disparador fijado: `ORDER_CONFIRMATION` (ADR-D0-003 v2)
- [x] Máquina de estados objetivo definida (FR-030-002)
- [x] Contado / crédito / sin crédito definidos (FR-030-003..007)
- [x] Insuficiencia, parcial, backorder, sobreventa decididos (FR-030-010..012)
- [x] Almacén, ubicación, lote/serial delimitados (FR-030-013..018)
- [x] Modificación, cancelación, expiración, liberación definidas (FR-030-020..027)
- [x] Multiempresa y permisos definidos (FR-030-030..035)
- [x] Concurrencia e idempotencia con prueba exigida (FR-030-040..044)
- [x] Handoff a 031 y fronteras 032/033/034/035 (FR-030-050..054)
- [x] Auditoría y modelo (FR-030-060..063)
- [x] Dependencias 011/012/023/029/045 satisfechas
- [x] OQ material: 0

## Pendiente para el ciclo de implementación (no iniciado)
- [ ] `/speckit.plan` propio con diseño del bloqueo (fila vs. advisory para fila inexistente)
- [ ] Migración `0043+` con rename, columnas, índices y `CHECK`; informe `MANUAL_REVIEW`
- [ ] Permiso `ventas:submit` en el catálogo de permisos y en el frontend
- [ ] Pruebas de la lista de ADR v2 §«Implicaciones de prueba»
- [ ] Regresión completa sobre PostgreSQL 18.6 (0 fallos, 8 saltos S3)
