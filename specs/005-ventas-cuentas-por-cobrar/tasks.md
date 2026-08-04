# TASKS — 005-VENTAS-CUENTAS-POR-COBRAR

| Campo | Valor |
|---|---|
| Iniciativa | 005-ventas-cuentas-por-cobrar |
| Versión | 1.0 |
| Ruta | `specs/005-ventas-cuentas-por-cobrar/tasks.md` |

Formato: | ID | Requisito | Tarea | Dependencia | Archivos | Prueba | Responsable |

> Las tareas se ejecutan únicamente tras autorización expresa **005-ventas-cuentas-por-cobrar**, con **001 certificada** y **002/003/004 implementados**.

| ID | Requisito | Tarea | Dependencia | Archivos | Prueba | Responsable |
|---|---|---|---|---|---|---|
| T-005-001 | FR-005-001/002 | Modelos de cotización/pedido + migración `0005` | 004 (head) | `sales/`, migración `0005_ventas.py` | Test de flujo | Datos |
| T-005-002 | FR-005-010/011/012 | Orden de venta (crédito + máquina de estados + aprobación por regla) | T-005-001 | `sales/orders/` | Test de crédito/máquina | Backend |
| T-005-003 | FR-005-020/021/022/023/024 | Reserva/picking/despacho (invoca 003 `reserve`/`pick`/`ship`; bloqueos) | T-005-002, 003 | `sales/fulfillment/` | Test de integración 003 | Backend |
| T-005-004 | FR-005-030/031/032/033/034 | Factura de venta (snapshot fiscal + estados + inmutabilidad) | T-005-003 | `sales/invoices/` | Test de estados/snapshot | Backend |
| T-005-005 | FR-005-045/047 | Notas de crédito/débito y devoluciones | T-005-004 | `sales/notes/` | Test de nota/CxC | Backend |
| T-005-006 | FR-005-040/100 | OpenItem RECEIVABLE al emitir (reutiliza 004) | T-005-004 | `sales/ar/` | Test de saldo | Backend |
| T-005-007 | FR-005-041/102 | Cobros (Payment IN) + instrumentos + idempotencia | T-005-006 | `sales/ar/` | Test de cobro/idempotencia | Backend |
| T-005-008 | FR-005-042 | Aplicaciones (cobro/anticipo/nota/retención sufrida) atómicas | T-005-007 | `sales/ar/` (reutiliza 004) | Test de aplicación/saldo | Backend |
| T-005-009 | FR-005-043/046 | Anticipos de cliente + aging + gestión de cobranza | T-005-008 | `sales/ar/` | Test de aging/anticipo | Backend |
| T-005-010 | FR-005-044 | Retención sufrida registrada y aplicada | T-005-007 | `sales/ar/` | Test de retención | Backend |
| T-005-011 | FR-005-048 | Segregación de cobros/aprobaciones | T-005-007 | `sales/ar/` | Test de permisos | Backend |
| T-005-012 | FR-005-101 | API `/sales/*` + `allowed_actions` | T-005-001..011 | `contracts/api-contracts.md` | Contract test | Backend |
| T-005-013 | FR-005-101 | Contrato cobros/aplicaciones para 006 | T-005-012 | `contracts/api-contracts.md` | Contract test | Backend |
| T-005-014 | FR-005-002/011 | Página de pedidos/órdenes de venta (WF-04) | T-005-012 | `src/modules/ventas/ordenes/` | E2E | Frontend |
| T-005-015 | FR-005-021/022 | Página de preparación y despacho (WF-04) | T-005-012 | `src/modules/ventas/despachos/` | E2E | Frontend |
| T-005-016 | FR-005-030/033 | Página de factura de venta (WF-04) | T-005-012 | `src/modules/ventas/facturas/` | Component/E2E | Frontend |
| T-005-017 | FR-005-041/046 | Página de cobro multimoneda y CxC (WF-02/WF-05) | T-005-012 | `src/modules/ventas/cuentas-por-cobrar/` | Component/E2E | Frontend |
| T-005-018 | FR-005-001/002 | Páginas de cotizaciones y pedidos | T-005-012 | `src/modules/ventas/` | Component/E2E | Frontend |
| T-005-019 | NFR (multiempresa) | Pruebas de aislamiento negativo | T-005-012 | `tests/` | Pytest negativo | QA |
| T-005-020 | NFR (concurrencia) | Cobros/aplicaciones simultáneos sin sobrededucción | T-005-008 | `tests/` | Pytest de concurrencia | QA |
| T-005-021 | NFR (accesibilidad) | axe + responsive en rutas de ventas | T-005-014..018 | Playwright | axe | QA |
| T-005-022 | CHK-005-DB-006 | CI: migración `0005` upgrade/downgrade | T-005-001 | `.github/workflows` | CI | DevSecOps |

## Notas

- No existen tareas genéricas; todas son atómicas, con dependencias y pruebas.
- T-005-003 requiere los servicios de 003 (`reserve`/`pick`/`ship`).
- La CxC (T-005-006..011) reutiliza el motor de aplicaciones de 004; no se duplica.
