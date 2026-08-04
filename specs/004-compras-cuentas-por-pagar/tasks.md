# TASKS — 004-COMPRAS-CUENTAS-POR-PAGAR

| Campo | Valor |
|---|---|
| Iniciativa | 004-compras-cuentas-por-pagar |
| Versión | 1.0 |
| Ruta | `specs/004-compras-cuentas-por-pagar/tasks.md` |

Formato: | ID | Requisito | Tarea | Dependencia | Archivos | Prueba | Responsable |

> Las tareas se ejecutan únicamente tras autorización expresa **004-compras-cuentas-por-pagar**, con **001 certificada** y **002/003 implementados**.

| ID | Requisito | Tarea | Dependencia | Archivos | Prueba | Responsable |
|---|---|---|---|---|---|---|
| T-004-001 | FR-004-001/002 | Modelos de requisición + líneas + migración `0004` | 003 (head) | `purchasing/requisitions/`, migración `0004_compras.py` | Test de flujo | Datos |
| T-004-002 | FR-004-010/011/012 | Cotizaciones y comparación | T-004-001 | `purchasing/quotes/` | Test de comparación | Backend |
| T-004-003 | FR-004-020/021/022/023 | Orden de compra (máquina de estados + aprobación por regla) | T-004-001 | `purchasing/orders/` | Test de máquina/aprobación | Backend |
| T-004-004 | FR-004-030/031/032/033/034 | Recepción (invoca 003 `receive`; lotes/seriales/calidad) | T-004-003, 003 | `purchasing/receipts/` | Test de integración 003 | Backend |
| T-004-005 | FR-004-040/041/042/043 | Factura del proveedor (duplicidad + estados + reverso) | T-004-004 | `purchasing/supplier_invoices/` | Test de duplicidad | Backend |
| T-004-006 | FR-004-050/051/052 | Conciliación triple | T-004-005 | `purchasing/triple_match/` | Test de diferencias | Backend |
| T-004-007 | FR-004-060/061 | Devoluciones y nota de crédito del proveedor | T-004-004 | `purchasing/returns/` | Test de nota/CxP | Backend |
| T-004-008 | FR-004-070/071/104 | OpenItem (PAYABLE) y saldo calculado | T-004-005 | `purchasing/ap/` | Test de saldo | Backend |
| T-004-009 | FR-004-072/101 | Payment (OUT) + instrumentos + idempotencia | T-004-008 | `purchasing/ap/` | Test de pago/idempotencia | Backend |
| T-004-010 | FR-004-073 | Application (pago/anticipo/nota/retención) atómica | T-004-009 | `purchasing/ap/` | Test de aplicación/saldo | Backend |
| T-004-011 | FR-004-074/075 | Advance (anticipos) + programación + aging | T-004-010 | `purchasing/ap/` | Test de aging/anticipo | Backend |
| T-004-012 | FR-004-076/078 | Retención referida a regla versionada (estructura; motor en 007) | T-004-009 | `purchasing/withholding/` | Test de retención | Backend |
| T-004-013 | FR-004-077 | Segregación de pagos/aprobaciones | T-004-009 | `purchasing/ap/` | Test de permisos | Backend |
| T-004-014 | FR-004-103 | API `/purchasing/*` + `allowed_actions` | T-004-001..013 | `contracts/api-contracts.md` | Contract test | Backend |
| T-004-015 | FR-004-103 | Contrato `Payment`/`Application` para 006 | T-004-014 | `contracts/api-contracts.md` | Contract test | Backend |
| T-004-016 | FR-004-020/023 | Página de órdenes de compra (WF-04) | T-004-014 | `src/modules/compras/ordenes/` | E2E | Frontend |
| T-004-017 | FR-004-030/032 | Página de recepciones (lotes/seriales/calidad) | T-004-014 | `src/modules/compras/recepciones/` | E2E | Frontend |
| T-004-018 | FR-004-040/041 | Página de facturas del proveedor | T-004-014 | `src/modules/compras/facturas/` | Component/E2E | Frontend |
| T-004-019 | FR-004-050/051 | Página de conciliación triple (WF-05) | T-004-014 | `src/modules/compras/conciliacion/` | E2E | Frontend |
| T-004-020 | FR-004-072/076 | Página de pagos y retenciones (WF-02) | T-004-014 | `src/modules/compras/cuentas-por-pagar/` | Component/E2E | Frontend |
| T-004-021 | FR-004-075 | Página de aging y programación de CxP | T-004-014 | `src/modules/compras/cuentas-por-pagar/` | Component/E2E | Frontend |
| T-004-022 | FR-004-001/010/060 | Páginas de requisiciones, cotizaciones y devoluciones | T-004-014 | `src/modules/compras/` | Component/E2E | Frontend |
| T-004-023 | NFR (multiempresa) | Pruebas de aislamiento negativo | T-004-014 | `tests/` | Pytest negativo | QA |
| T-004-024 | NFR (concurrencia) | Aplicaciones/pagos simultáneos sin sobrededucción | T-004-010 | `tests/` | Pytest de concurrencia | QA |
| T-004-025 | NFR (accesibilidad) | axe + responsive en rutas de compras | T-004-016..022 | Playwright | axe | QA |
| T-004-026 | CHK-004-DB-007 | CI: migración `0004` upgrade/downgrade | T-004-001 | `.github/workflows` | CI | DevSecOps |

## Notas

- No existen tareas genéricas; todas son atómicas, con dependencias y pruebas.
- T-004-004 requiere el servicio `receive` de 003 (ya implementado).
- La retención (T-004-012) es estructural: el cálculo fiscal completo es de 007.
