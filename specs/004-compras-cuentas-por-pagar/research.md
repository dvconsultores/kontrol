# RESEARCH — 004-COMPRAS-CUENTAS-POR-PAGAR

| Campo | Valor |
|---|---|
| Iniciativa | 004-compras-cuentas-por-pagar |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Responsable | Arquitecto técnico / Arquitecto de datos |
| Ruta | `specs/004-compras-cuentas-por-pagar/research.md` |

## 1. Ciclo de compra (DOC-02 §6)

Flujo de 14 pasos: requisición → aprobación → cotizaciones → ofertas → comparación → orden → aprobación → recepción (lotes/seriales/vencimiento/calidad) → factura (duplicidad) → conciliación triple → retenciones en pago → CxP → pago → devolución/nota. 004 implementa estos pasos como transiciones de estado con `allowed_actions` en backend (P6).

## 2. Máquinas de estado (DOC-03 §13)

- OC: DRAFT → SUBMITTED → APPROVED → PARTIALLY_RECEIVED → RECEIVED → CLOSED; CANCELLED.
- Recepción: DRAFT → CONFIRMED → QUALITY_PENDING → ACCEPTED/PARTIALLY_ACCEPTED/REJECTED → CLOSED.
- Factura proveedor: DRAFT → VALIDATED → MATCHED/EXCEPTION → APPROVED → POSTED → PARTIALLY_PAID → PAID; REVERSED.
- Retención: CALCULADA → PRACTICADA → EMITIDA → DECLARADA → PAGADA → CONCILIADA; REVERSADA.
- Aprobación: PENDING → IN_REVIEW → APPROVED/REJECTED/EXPIRED/CANCELLED.

## 3. Integración con 003 (recepciones)

- La recepción (004) invoca `POST /api/v1/inventory/operations/receive` de 003 (entrada + lotes/seriales + capas de costo). 004 **no** calcula saldos ni costos (CL-004-03, FR-004-104).
- Las líneas de servicio de una OC no requieren recepción de inventario (SU-004-04).

## 4. Duplicidad de factura del proveedor

- Clave `(company_id, supplier_id, invoice_number, control_number)` (DOC-03 §12) con excepciones documentadas (notas/reemisiones).
- Idempotencia: `Idempotency-Key` en POST de factura, recepción, pago y aplicación (DOC-03 §14).

## 5. Saldo de CxP y aplicaciones

- `OpenItem.balance = original − applied`; saldo CxP = facturas + débitos − pagos − retenciones − créditos (DOC-02 §9).
- `Application` es **atómica** con bloqueo (`SELECT ... FOR UPDATE` o advisory lock por `(company, open_item)`); ninguna aplicación excede el saldo de origen ni destino (DOC-03 §12).
- Pagos parciales y múltiples instrumentos/monedas; tasa histórica; la moneda de pago no altera el IVA causado (DOC-01 §5).

## 6. Retenciones (referencia a reglas versionadas)

- 004 estructura `Withholding` con estados y referencia a `WithholdingRule` versionada (perfil del proveedor desde 002).
- El **motor fiscal** (cálculo IVA/ISLR/IGTF, comprobantes, libros, cierres) es de **007** (Constitución P4). Hasta 007, 004 calcula con la regla de referencia y marca el estado; no se hardcodean tasas (P8).

## 7. Aprobaciones versionadas

- Reglas de aprobación de compra (monto, categoría, excepción) por empresa, **versionadas** (P8); segregación Solicitante/Comprador/Aprobador (DOC-02 §12).
- Pago: crea CxP, revisa Tesorería, aprueba Aprobador de pago (DOC-02 §12).

## 8. Integración con 006 (tesorería)

- 004 registra el pago OUT y las aplicaciones; 006 consumirá `Payment`/`Application` para conciliación bancaria/caja (CL-004-01). Contrato API v1.

## 9. Seguridad y consistencia

- `allowed_actions` calculadas en backend por estado y permiso (P6).
- Aislamiento multiempresa: `company_id` en cada agregado; pruebas negativas obligatorias.
- Auditoría integral en requisición → pago (DOC-01 §3).
- Snapshot por línea (producto, precio, impuesto, tasa) — P4/P8.

## 10. Referencias técnicas (stack 001/002/003)

- PostgreSQL 18: transacciones, `FOR UPDATE`/advisory locks, restricciones CHECK y unique.
- SQLAlchemy 2.0 + Alembic (head `0003_inventario` → `0004_compras`).
- FastAPI + React 19 / react-router 8 / TanStack Query (estándar DOC-08).
- La concurrencia de aplicaciones se valida con pruebas simultáneas (T-004-024).
