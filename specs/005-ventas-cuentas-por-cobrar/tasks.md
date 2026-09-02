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

---

# TAREAS — SPEC 029 · IMPLEMENTACIÓN

| Id | Tarea | Estado |
|---|---|---|
| T-029-I-001..004 | Precheck y auditoría forense de cotización y pedido | Hecha — 0 columnas de origen |
| T-029-I-005..008 | Modelo, migración `0042`, paridad ORM | Hecha — desviación 0 |
| T-029-I-009..012 | Alcance de empresa y derivación de líneas | Hecha |
| T-029-I-013..016 | Integración del resolutor y persistencia del origen | Hecha |
| T-029-I-017..020 | Cotización, líneas, ciclo y vigencia | Hecha |
| T-029-I-021..022 | Conversión e idempotencia | Hecha |
| T-029-I-023..024 | Pedido directo y sus líneas, con la misma autoridad | Hecha |
| T-029-I-025 | Invariancia histórica | Hecha — tres pruebas |
| T-029-I-026..030 | Tercero, artículo, unidad, presentación, moneda | Hecha |
| T-029-I-031..032 | Permisos y auditoría | Hecha |
| T-029-I-033..034 | API y OpenAPI | Hecha — 311 rutas, 429 operaciones |
| T-029-I-035..041 | Frontend y aislamiento de empresa | Hecha |
| T-029-I-042..045 | Seguridad de rutas hijas y pruebas hostiles | Hecha |
| T-029-I-046..051 | Instalación limpia y regresiones | Hecha |
| T-029-I-052..053 | Artefactos y convergencia | Hecha |

---

# TAREAS — SPEC 030 · ESQUELETO DOCUMENTAL (D0-03 CLOSED, 2026-09-02)

Esqueleto derivado del contrato. Se valida y completa en el ciclo `/speckit.tasks` de la Spec 030,
que **no** ha sido autorizado. Ninguna tarea está iniciada.

| Tarea | Descripción | FR |
|---|---|---|
| T-030-001 | Renombrar `RESERVED → RELEASED`; `REVERT_TO_DRAFT`; `CANCELLED` desde estados de crédito; `EXPIRED` | FR-030-002 |
| T-030-002 | Mover el disparo a `DRAFT → SUBMITTED`; retirar de `APPROVED`; `APPROVED → RELEASED` automático | FR-030-001, -003, -004 |
| T-030-003 | Precondiciones: almacén obligatorio, base resuelta, líneas > 0 | FR-030-013, -015 |
| T-030-004 | Reserva por línea en base con campos Spec 011, `source_*`, `trigger`, `oversell` | FR-030-015, -062 |
| T-030-005 | Bloqueo `FOR UPDATE`, orden determinista, unicidad de saldo, índice parcial, `CHECK` | FR-030-040..042 |
| T-030-006 | Liberación atómica en cancelar, rechazar, revertir; obsolescencia 045 | FR-030-007, -021, -023 |
| T-030-007 | `FULFILLED` en despacho | FR-030-054 |
| T-030-008 | `reservation_ttl_days`; `expire` consciente del pedido | FR-030-024..026 |
| T-030-009 | Liberación manual con motivo, solo `MANUAL` | FR-030-027 |
| T-030-010 | Permiso `ventas:submit` y separación de `ventas:approve` | FR-030-035 |
| T-030-011 | Auditoría de reservas en inventario | FR-030-060, -061 |
| T-030-012 | Migración + informe `MANUAL_REVIEW` | FR-030-063 |
| T-030-013 | Pruebas: carrera PostgreSQL, sobreventa, liberaciones, base, multiempresa, idempotencia, conversión, despacho, expiración | FR-030-044 y ADR v2 |
| T-030-014 | Frontend: insuficiencia por línea, reversión con motivo, disponible vs. reservado | plan |
| T-030-015 | Documentación: contracts, data-model, traceability, convergence de 030 | — |
