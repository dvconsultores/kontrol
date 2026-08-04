# PLAN DE PRUEBAS — 005-VENTAS-CUENTAS-POR-COBRAR

| Campo | Valor |
|---|---|
| Iniciativa | 005-ventas-cuentas-por-cobrar |
| Versión | 1.0 |
| Ruta | `specs/005-ventas-cuentas-por-cobrar/test-plan.md` |

## 1. Estrategia

- **Unitarias**: máquinas de estado (OV/factura de venta), análisis de crédito, cálculo de saldo CxC, aplicaciones que no exceden saldo, aging, snapshot.
- **Integración**: API + PostgreSQL; reserva/picking/despacho → 003; factura → CxC (reutiliza 004); retención sufrida; contrato cobros/aplicaciones para 006; aislamiento multiempresa.
- **Concurrencia**: cobros/aplicaciones simultáneos sin sobrededucción (T-005-020).
- **E2E/UI**: Playwright (rutas de ventas), axe, responsive.

## 2. Casos de prueba

| ID | Tipo | Objetivo | Criterio de éxito |
|---|---|---|---|
| TP-005-001 | Unit | Máquina de estados OV | Transiciones válidas/inválidas DRAFT→…→CLOSED |
| TP-005-002 | Unit | Análisis de crédito | Límite/bloqueo/margen separados; excepción aprobada |
| TP-005-003 | Unit | Cotización sin reserva | Cotizar no reserva inventario |
| TP-005-004 | Integración | Reserva al aprobar | Disponible baja, físico sin cambio (via 003) |
| TP-005-005 | Integración | Picking y salida | Salida a tránsito/entregado-no-facturado con costo (via 003) |
| TP-005-006 | Integración | Bloqueo de despacho | Falta documento/venció/no coincide → bloqueado |
| TP-005-007 | Unit | Máquina de estados factura | DRAFT→…→EMITTED→PAID; CREDITED/VOIDED vinculado |
| TP-005-008 | Unit | Snapshot fiscal | Base VES y tasa snapshot por línea |
| TP-005-009 | Unit | Saldo de CxC | `balance = original − applied`; saldo calculado |
| TP-005-010 | Unit | Idempotencia de cobro | Reintento no duplica el cobro |
| TP-005-011 | Unit/Integración | Aplicación atómica | Ninguna aplicación excede saldo de origen ni destino |
| TP-005-012 | Concurrencia | Cobros simultáneos | N cobros concurrentes no sobrededucen |
| TP-005-013 | Unit | Aging | Buckets 0-30/31-60/61-90/>90 correctos |
| TP-005-014 | Unit | Retención sufrida | Registrada y aplicada por regla versionada |
| TP-005-015 | Contract | Contrato 006 | Cobros/aplicaciones cumplen el contrato y la idempotencia |
| TP-005-016 | Multiempresa | Aislamiento negativo | Empresa A no ve/afecta CxC de B |
| TP-005-017 | E2E | Orden de venta y despacho | Flujo completo hasta salida |
| TP-005-018 | E2E | Factura y CxC | Factura emite open item RECEIVABLE |
| TP-005-019 | E2E | Cobro multimoneda | Múltiples medios/monedas aplicados |
| TP-005-020 | Accesibilidad | axe + responsive | WCAG 2.2 AA en rutas de ventas |

## 3. Ambiente

- Backend: pytest + PostgreSQL 18 (integración), SQLite in-memory (unitarias), Alembic head `0005_ventas`.
- Frontend: Vitest (componentes), Playwright (E2E), axe (accesibilidad).
- CI: jobs heredados de 001 (con `KONTROL_SECRET_KEY`).

## 4. Evidencia

- Resultados de pytest, vitest, Playwright, axe y concurrencia en `evidence/`.
- Contract tests en `contracts/`.
