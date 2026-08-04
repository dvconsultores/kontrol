# CONVERGENCIA — 004-COMPRAS-CUENTAS-POR-PAGAR

| Campo | Valor |
|---|---|
| Iniciativa | 004-compras-cuentas-por-pagar |
| Versión | 1.0 |
| Ruta | `specs/004-compras-cuentas-por-pagar/convergence.md` |

## 1. Propósito

Registrar brechas y nuevas tareas tras la implementación. `/speckit.converge` se ejecuta al cierre.

## 2. Brechas identificadas

| ID | Brecha | Acción | Responsable | Estado |
|---|---|---|---|---|
| CVG-004-01 | Umbrales de aprobación por monto/categoría por empresa | Decisión de negocio (CL-004-11) | Compras | Pendiente |
| CVG-004-02 | Tolerancias de recepción/sobrefacturación por empresa | Decisión (CL-004-12) | Compras | Pendiente |
| CVG-004-03 | Motor fiscal de retenciones (cálculo completo IVA/ISLR/IGTF) | Spec 007 | Fiscal | Pendiente (007) |
| CVG-004-04 | Conciliación bancaria de pagos | Spec 006 (tesorería) | Tesorería | Pendiente (006) |
| CVG-004-05 | Contrato `Payment`/`Application` consumido por 006 | Integración 006 | Arquitecto | Pendiente (006) |

## 3. Implementado (004)

| Elemento | Estado |
|---|---|
| Modelos (21 tablas) + migración `0004_compras` | ✔ |
| Requisición (flujo + aprobación) | ✔ |
| Cotizaciones y comparación | ✔ |
| Órdenes de compra (máquina de estados + aprobación por regla) | ✔ |
| Recepción → **invoca el motor de 003** (lotes/seriales/calidad/costos) | ✔ |
| Factura del proveedor (duplicidad + estados + reverso) | ✔ |
| Conciliación triple (orden/recepción/factura) | ✔ |
| Devoluciones y nota de crédito del proveedor | ✔ |
| CxP: open items, pagos (idempotencia), aplicaciones atómicas, anticipos, programación, aging | ✔ |
| Retención estructural referida a reglas versionadas | ✔ |
| API `/purchasing/*` (32 endpoints) | ✔ |
| Frontend: requisiciones, órdenes, recepciones, facturas, CxP | ✔ |

## 4. Validación local

| Compuerta | Resultado |
|---|---|
| Backend pytest | ✔ 74/74 (incluye 17 de compras) |
| Backend ruff | ✔ limpio (incluye migración) |
| Backend mypy | ✔ 60 archivos, 0 issues |
| Alembic | ✔ head `0004_compras` (upgrade/downgrade) |
| OpenAPI | ✔ 32 endpoints `/purchasing/*` (96 rutas totales) |
| Frontend tsc / eslint | ✔ limpios |
| Frontend vitest / build | ✔ 16/16 · build OK |

## 5. Estado

| Elemento | Estado |
|---|---|
| Fase documental | ✔ |
| Implementación | ✔ (sujeta a 001 certificada + 002/003 implementados + autorización expresa) |
| Certificación (Docker/CI/legal, integración 005/006/007) | Pendiente — depende de 001 certificada y de Specs 005/006/007 |
