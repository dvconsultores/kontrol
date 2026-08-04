# RESEARCH — 005-VENTAS-CUENTAS-POR-COBRAR

| Campo | Valor |
|---|---|
| Iniciativa | 005-ventas-cuentas-por-cobrar |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Responsable | Arquitecto técnico / Arquitecto de datos |
| Ruta | `specs/005-ventas-cuentas-por-cobrar/research.md` |

## 1. Ciclo de venta (DOC-02 §7)

Flujo de 13 pasos: cliente → cotización (sin reserva) → pedido (validar datos) → análisis de crédito/margen/precios → aprobar OV y reservar → picking → validar traslado/permisos → confirmar salida (tránsito/entregado-no-facturado) → factura → CxC → cobros/anticipos/retenciones sufridas → notas/devoluciones/diferencias → conciliar y cerrar.

## 2. Máquinas de estado (DOC-03 §13)

- OV: DRAFT → SUBMITTED → CREDIT_PENDING → APPROVED → RESERVED → PREPARING → SHIPPED → CLOSED; CANCELLED.
- Factura de venta: DRAFT → VALIDATED → APPROVED → EMITTED → DELIVERED → PARTIALLY_PAID → PAID; CREDITED/VOIDED.
- Aprobación: PENDING → IN_REVIEW → APPROVED/REJECTED/EXPIRED/CANCELLED.

## 3. Integración con 003 (reserva, picking, despacho)

- 005 invoca los servicios de 003: `reserve` (al aprobar la OV), `pick` (confirmación de ubicación/lote/serial) y `ship` (salida → tránsito/entregado-no-facturado, costo de salida). 005 **no** calcula saldos ni costos (CL-005-03).
- Bloqueo de despacho: si falta documento obligatorio, está vencido o no coincide producto/lote/cantidad/origen/destino (DOC-01 §5). La regulación funcional (SICA/SIGESAI/SACS) es de 008.

## 4. Factura de venta y snapshot fiscal

- La factura de venta es **inmutable** tras emitida; corrección por nota de crédito/débito o anulación vinculada (P5).
- Base fiscal en **VES** y **tasa snapshot** por línea (DOC-04 pantalla 13). La **emisión fiscal formal** (numeración, números de control, libros) es de **007** (CL-005-02).
- Líneas mixtas producto+servicio; el servicio no afecta inventario.

## 5. CxC (reutiliza el motor de 004)

- `OpenItem` con `item_type=RECEIVABLE` (tabla `ap_open_items` de 004); saldo = documentos + débitos − cobros − retenciones − créditos (DOC-02 §9).
- Cobro = `Payment` con dirección **IN**, múltiples instrumentos/monedas, idempotencia (`Idempotency-Key`).
- `Application` reutiliza el motor atómico de 004 (no excede saldo de origen ni destino; bloqueo concurrente).
- Anticipos de clientes (`ap_advances`, dirección IN) con imputación posterior; retenciones **sufridas** (`ap_withholdings`) aplicadas.
- Notas de crédito/débito vinculadas; la devolución física (vía 003) no sustituye la nota.

## 6. Crédito y aprobaciones versionadas

- Análisis de crédito: límite, bloqueo, saldo CxC, aging, margen y precios — separados (DOC-04 pantalla 11).
- Reglas de crédito y aprobación **versionadas** por empresa (P8); segregación Vendedor/Crédito/Aprobador comercial (DOC-02 §12).

## 7. Integración con 006 (tesorería)

- 005 registra los cobros (Payment IN) y las aplicaciones; 006 los consumirá para conciliación bancaria/caja (CL-005-02). Contrato API v1.

## 8. Seguridad y consistencia

- `allowed_actions` calculadas en backend por estado y permiso (P6).
- Aislamiento multiempresa: `company_id` en cada agregado; pruebas negativas obligatorias.
- Auditoría integral en cotización → cobro (DOC-01 §3).
- Snapshot por línea (producto, precio, impuesto, tasa) — P4/P8.

## 9. Referencias técnicas (stack 001/002/003/004)

- PostgreSQL 18: transacciones, `FOR UPDATE`/advisory locks, restricciones.
- SQLAlchemy 2.0 + Alembic (head `0004_compras` → `0005_ventas`).
- FastAPI + React 19 / react-router 8 / TanStack Query (estándar DOC-08).
- La concurrencia de cobros/aplicaciones se valida con pruebas simultáneas (T-005-020).
