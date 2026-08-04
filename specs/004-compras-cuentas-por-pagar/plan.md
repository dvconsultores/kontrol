# PLAN — 004-COMPRAS-CUENTAS-POR-PAGAR

| Campo | Valor |
|---|---|
| Iniciativa | 004-compras-cuentas-por-pagar |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Responsable | Arquitecto de software / Arquitecto de datos |
| Ruta | `specs/004-compras-cuentas-por-pagar/plan.md` |

## 1. Validación contra la Constitución

| Principio | Cumplimiento |
|---|---|
| P1 Spec antes que código | ✔ Este plan no implementa |
| P2 Autorización expresa | ✔ Se detiene en `/speckit.analyze` |
| P3 Trazabilidad | ✔ `traceability-matrix.md` |
| P4 Núcleo fiscal separado | ✔ retenciones referidas a reglas; motor fiscal en 007 |
| P5 Datos históricos protegidos | ✔ facturas postadas/pagos inmutables; reverso vinculado; saldos calculados |
| P6 Seguridad en backend | ✔ permisos/alcance/aprobaciones en backend |
| P7 Frontend uniforme | ✔ patrones WF y componentes compartidos |
| P8 No hardcodear reglas | ✔ aprobaciones y retenciones por reglas versionadas |
| P9 Instalación independiente | ✔ hereda 001 |
| P13 Integridad transaccional | ✔ idempotencia, aplicaciones atómicas, versión/ETag |
| P15 Datos del cliente protegidos | ✔ hereda 001 |
| P17 No retrabajo visual | ✔ componentes compartidos |
| P18 Política de modales | ✔ pantallas completas (ADR-015) |

**Resultado: compatible con la Constitución.**

## 2. Arquitectura

Módulo de backend `purchasing` (extiende 001/002/003):

| Submódulo | Responsabilidad en 004 |
|---|---|
| `purchasing/requisitions` | PurchaseRequisition + líneas + aprobación |
| `purchasing/quotes` | SupplierQuote + comparación |
| `purchasing/orders` | PurchaseOrder + líneas + máquina de estados + aprobación |
| `purchasing/receipts` | GoodsReceipt + líneas + calidad; **invoca 003 `receive`** |
| `purchasing/supplier_invoices` | SupplierInvoice + duplicidad + estados |
| `purchasing/triple_match` | TripleMatch (orden/recepción/factura) |
| `purchasing/returns` | Return (devolución) + nota de crédito |
| `purchasing/ap` | OpenItem (PAYABLE), Payment, PaymentInstrument, Application, Advance, PaymentSchedule, aging |
| `purchasing/withholding` | Estructura de retención referida a reglas versionadas (motor en 007) |

Frontend: módulo `compras/` (`requisiciones`, `cotizaciones`, `ordenes`, `recepciones`, `facturas-proveedor`, `conciliacion`, `devoluciones`, `cuentas-por-pagar`), reutilizando `design-system`.

## 3. Estructura de archivos esperada

```text
resources/backend/app/modules/purchasing/
├── requisitions/  quotes/  orders/  receipts/  supplier_invoices/
├── triple_match/  returns/  ap/  withholding/
resources/backend/alembic/versions/0004_compras.py
resources/frontend/src/modules/compras/
├── requisiciones/  cotizaciones/  ordenes/  recepciones/
├── facturas/  conciliacion/  devoluciones/  cuentas-por-pagar/
specs/004-compras-cuentas-por-pagar/... (este paquete)
```

## 4. Datos y migraciones

- Modelo en `data-model.md`; migración Alembic `0004_compras` (upgrade/downgrade) sobre head `0003_inventario`.
- Seeds idempotentes: no se siembran reglas fiscales (P8); solo catálogos de configuración si aplican (ninguno crítico).
- Constraints: unique de factura proveedor `(company, supplier, invoice_number, control_number)`; aplicaciones no exceden saldo; idempotencia en pagos; multiempresa en cada agregado; versión/ETag en documentos editables (borrador).

## 5. Contratos

- OpenAPI con endpoints REST de compras/CxP (`/purchasing/*`): requisiciones, cotizaciones, órdenes, recepciones, facturas, conciliación, devoluciones, CxP, pagos, aplicaciones, anticipos, aging.
- `allowed_actions` calculadas en backend (transiciones por estado y permiso).
- Integración: 004 invoca `POST /inventory/operations/receive` de 003; expone `Payment`/`Application` para 006.
- Contrato de errores e idempotencia heredados de 001 (DOC-03 §14).

## 6. Pruebas

Plan en `test-plan.md`: unitarias (máquinas de estado, duplicidad de factura, cálculo de saldo CxP, aplicaciones que no exceden saldo, aging), integración (recepción → 003, conciliación triple, retención por regla de referencia, multiempresa, idempotencia), E2E (orden de compra, recepción, factura + conciliación, pago con aplicación).

## 7. Fases de implementación (para `/speckit.implement`)

1. Modelos + migración `0004_compras`.
2. Requisiciones (flujo + aprobación).
3. Cotizaciones y comparación.
4. Órdenes de compra (máquina de estados + aprobación por regla versionada).
5. Recepciones (invoca 003 `receive`; lotes/seriales/calidad).
6. Factura del proveedor (duplicidad + estados) y conciliación triple.
7. Devoluciones y notas.
8. CxP: open items, programación, pagos (idempotencia), instrumentos, aplicaciones, anticipos, aging.
9. Retenciones referidas a reglas (estructura; motor en 007).
10. API `/purchasing/*` + contrato para 006.
11. Frontend: requisiciones, cotizaciones, órdenes, recepciones, facturas+conciliación, devoluciones, CxP.
12. Tests (unit/integración/E2E), concurrencia y CI.
13. Documentación y evidencia.

## 8. Entregables de esta fase documental

Este plan forma parte de la fase documental de `004-compras-cuentas-por-pagar`; **no autoriza implementación**. La implementación requiere `/speckit.analyze` consistente, **001 certificada**, **002 y 003 implementados**, y autorización expresa.

## 9. Estado de aprobación

| Elemento | Estado |
|---|---|
| Arquitectura | ✔ |
| Datos | ✔ (data-model.md) |
| Pruebas | ✔ (test-plan.md) |
| Aprobación | Pendiente |
