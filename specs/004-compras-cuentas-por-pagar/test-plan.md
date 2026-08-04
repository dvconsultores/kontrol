# PLAN DE PRUEBAS — 004-COMPRAS-CUENTAS-POR-PAGAR

| Campo | Valor |
|---|---|
| Iniciativa | 004-compras-cuentas-por-pagar |
| Versión | 1.0 |
| Ruta | `specs/004-compras-cuentas-por-pagar/test-plan.md` |

## 1. Estrategia

- **Unitarias**: máquinas de estado (OC/recepción/factura), duplicidad de factura, cálculo de saldo CxP, aplicaciones que no exceden saldo, aging, snapshot.
- **Integración**: API + PostgreSQL; recepción → 003 `receive`; conciliación triple; retención por regla de referencia; contrato `Payment`/`Application` para 006; aislamiento multiempresa.
- **Concurrencia**: aplicaciones/pagos simultáneos sin sobrededucción (T-004-024).
- **E2E/UI**: Playwright (rutas de compras), axe, responsive.

## 2. Casos de prueba

| ID | Tipo | Objetivo | Criterio de éxito |
|---|---|---|---|
| TP-004-001 | Unit | Máquina de estados OC | Transiciones válidas/inválidas DRAFT→…→CLOSED |
| TP-004-002 | Unit | Aprobación por regla versionada | Aprueba/rechaza según monto/categoría; segregación |
| TP-004-003 | Unit | Máquina de estados recepción | DRAFT→…→ACCEPTED/REJECTED→CLOSED |
| TP-004-004 | Integración | Recepción → 003 | Al recibir, 003 registra entrada/lotes/capas; saldo actualizado una vez |
| TP-004-005 | Unit | Duplicidad de factura | Factura duplicada rechazada; excepción documentada permitida |
| TP-004-006 | Unit | Máquina de estados factura | DRAFT→…→POSTED→PAID; REVERSED vinculado |
| TP-004-007 | Unit | Conciliación triple | Diferencias de precio/cantidad/impuesto explícitas; POSTED condicionado |
| TP-004-008 | Unit | Saldo de CxP | `balance = original − applied`; saldo calculado, no editado |
| TP-004-009 | Unit | Idempotencia de pago | Reintento no duplica el pago |
| TP-004-010 | Unit/Integración | Aplicación atómica | Ninguna aplicación excede saldo de origen ni destino |
| TP-004-011 | Concurrencia | Aplicaciones simultáneas | N aplicaciones concurrentes no sobrededucen |
| TP-004-012 | Unit | Aging | Buckets 0-30/31-60/61-90/>90 correctos |
| TP-004-013 | Unit | Anticipo e imputación | Disponible sin aplicar; imputación posterior |
| TP-004-014 | Unit | Retención por regla | Calculada por regla versionada (referencia); sin hardcodeo |
| TP-004-015 | Contract | Contrato 006 | `Payment`/`Application` cumplen el contrato y la idempotencia |
| TP-004-016 | Multiempresa | Aislamiento negativo | Empresa A no ve/afecta CxP de B |
| TP-004-017 | Snapshot | Líneas con snapshot | Cambios de catálogo no alteran histórico |
| TP-004-018 | E2E | Orden de compra y recepción | Flujo completo hasta recepción con lotes/calidad |
| TP-004-019 | E2E | Factura + conciliación triple | Diferencias visibles y resolución |
| TP-004-020 | E2E | Pago y retenciones | Aprobación separada; neto conciliado |
| TP-004-021 | Accesibilidad | axe + responsive | WCAG 2.2 AA en rutas de compras |

## 3. Ambiente

- Backend: pytest + PostgreSQL 18 (integración), SQLite in-memory (unitarias), Alembic head `0004_compras`.
- Frontend: Vitest (componentes), Playwright (E2E), axe (accesibilidad).
- CI: jobs heredados de 001 (con `KONTROL_SECRET_KEY`).

## 4. Evidencia

- Resultados de pytest, vitest, Playwright, axe y concurrencia en `evidence/`.
- Contract tests en `contracts/`.
