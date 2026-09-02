# PLAN — 005-VENTAS-CUENTAS-POR-COBRAR

| Campo | Valor |
|---|---|
| Iniciativa | 005-ventas-cuentas-por-cobrar |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Responsable | Arquitecto de software / Arquitecto de datos |
| Ruta | `specs/005-ventas-cuentas-por-cobrar/plan.md` |

## 1. Validación contra la Constitución

| Principio | Cumplimiento |
|---|---|
| P1 Spec antes que código | ✔ Este plan no implementa |
| P2 Autorización expresa | ✔ Se detiene en `/speckit.analyze` |
| P3 Trazabilidad | ✔ `traceability-matrix.md` |
| P4 Núcleo fiscal separado | ✔ factura comercial con snapshot; emisión fiscal en 007 |
| P5 Datos históricos protegidos | ✔ facturas/cobros inmutables; notas/anulaciones vinculadas; saldos calculados |
| P6 Seguridad en backend | ✔ permisos/crédito/aprobaciones en backend |
| P7 Frontend uniforme | ✔ patrones WF y componentes compartidos |
| P8 No hardcodear reglas | ✔ crédito y aprobaciones por reglas versionadas |
| P9 Instalación independiente | ✔ hereda 001 |
| P13 Integridad transaccional | ✔ idempotencia, aplicaciones atómicas, versión/ETag |
| P15 Datos del cliente protegidos | ✔ hereda 001 |
| P17 No retrabajo visual | ✔ componentes compartidos |
| P18 Política de modales | ✔ pantallas completas (ADR-015) |

**Resultado: compatible con la Constitución.**

## 2. Arquitectura

Módulo de backend `sales` (extiende 001/002/003/004):

| Submódulo | Responsabilidad en 005 |
|---|---|
| `sales/quotes` | SalesQuote + líneas (sin reserva) |
| `sales/orders` | SalesOrder + líneas + crédito + máquina de estados |
| `sales/fulfillment` | PickList, despacho, salida; **invoca 003** (reserve/pick/ship) |
| `sales/invoices` | SalesInvoice + líneas + snapshot fiscal + estados |
| `sales/notes` | Nota de crédito/débito, devoluciones |
| `sales/ar` | OpenItem RECEIVABLE + cobros + aplicaciones + anticipos + retenciones sufridas + aging (reutiliza 004) |

Frontend: módulo `ventas/` (`cotizaciones`, `pedidos`, `ordenes`, `despachos`, `facturas`, `cuentas-por-cobrar`), reutilizando `design-system`.

## 3. Estructura de archivos esperada

```text
resources/backend/app/modules/sales/
├── quotes/  orders/  fulfillment/  invoices/  notes/  ar/
resources/backend/alembic/versions/0005_ventas.py
resources/frontend/src/modules/ventas/
├── cotizaciones/  pedidos/  ordenes/  despachos/  facturas/  cuentas-por-cobrar/
specs/005-ventas-cuentas-por-cobrar/... (este paquete)
```

## 4. Datos y migraciones

- Modelo en `data-model.md`; migración Alembic `0005_ventas` (upgrade/downgrade) sobre head `0004_compras`.
- **CxC reutiliza las tablas de 004** (`ap_open_items` RECEIVABLE, `ap_applications`, `ap_advances`, `ap_withholdings`) — no se duplican.
- Constraints: factura de venta con numeración (draft sin correlativo fiscal hasta 007); aplicaciones no exceden saldo; multiempresa; idempotencia en cobros.

## 5. Contratos

- OpenAPI con endpoints REST de ventas/CxC (`/sales/*`): cotizaciones, pedidos, órdenes, despachos, facturas, notas, CxC, cobros, aplicaciones, anticipos, aging.
- `allowed_actions` calculadas en backend (transiciones por estado y permiso).
- Integración: 005 invoca 003 (`reserve`, `pick`, `ship`) y reutiliza el motor de aplicaciones de 004; expone cobros/aplicaciones para 006.
- Contrato de errores e idempotencia heredados de 001 (DOC-03 §14).

## 6. Pruebas

Plan en `test-plan.md`: unitarias (máquinas de estado OV/factura, crédito, saldo CxC, aplicaciones atómicas, aging), integración (reserva/picking/despacho → 003, factura + CxC, retención sufrida, multiempresa, idempotencia), E2E (orden de venta, despacho, factura, cobro multimoneda).

## 7. Fases de implementación (para `/speckit.implement`)

1. Modelos + migración `0005_ventas`.
2. Cotizaciones y pedidos.
3. Órdenes de venta (crédito + máquina de estados + aprobación por regla).
4. Reserva/picking/despacho (invoca 003 `reserve`/`pick`/`ship`; bloqueos).
5. Factura de venta (snapshot fiscal + estados + inmutabilidad).
6. Notas y devoluciones.
7. CxC: open items RECEIVABLE, cobros (Payment IN), aplicaciones (reutiliza 004), anticipos, retenciones sufridas, aging.
8. API `/sales/*` + contrato para 006.
9. Frontend: cotizaciones, pedidos, órdenes, despachos, facturas, CxC.
10. Tests (unit/integración/E2E), concurrencia y CI.
11. Documentación y evidencia.

## 8. Entregables de esta fase documental

Este plan forma parte de la fase documental de `005-ventas-cuentas-por-cobrar`; **no autoriza implementación**. La implementación requiere `/speckit.analyze` consistente, **001 certificada**, **002/003/004 implementados**, y autorización expresa.

## 9. Estado de aprobación

| Elemento | Estado |
|---|---|
| Arquitectura | ✔ |
| Datos | ✔ (data-model.md) |
| Pruebas | ✔ (test-plan.md) |
| Aprobación | Pendiente |

---

# PLAN — SPEC 030 · SUPUESTOS ACTUALIZADOS (D0-03 CLOSED, 2026-09-02)

Este bloque fija los supuestos que la fase `/speckit.plan` de la Spec 030 debe respetar. No es su
plan de implementación (ese se escribe en su propio ciclo, con autorización expresa).

| Supuesto anterior | Supuesto vigente |
|---|---|
| La reserva ocurre al aprobar (`APPROVED`) | La reserva ocurre al confirmar (`SUBMITTED`); aprobar libera a preparación |
| Disparador configurable por empresa (ADR v1) | Disparador fijo; configurable: TTL, sobreventa, política de crédito |
| Estado `RESERVED` | Renombrado `RELEASED`; `APPROVED` transitorio |
| Modificación de líneas «la maneja el servicio» | Solo en `DRAFT`; `REVERT_TO_DRAFT` libera todo |
| Cancelación sin efecto en inventario | Cancelación libera atómicamente |
| Reserva en cantidad tecleada | Reserva en base con snapshot |
| Comprobación de disponible sin bloqueo | `FOR UPDATE` + unicidad + prueba de carrera |
| Despacho libera | Despacho consume (`FULFILLED`) |
| Expiración por job pendiente (CVG-003-04) | TTL opcional, defecto desactivado; endpoint existente; planificador de 047 |
| Auditoría solo del pedido | Eventos de reserva en inventario |

Arquitectura que **no** cambia: un motor de inventario (003/023), un motor de aprobaciones (045),
`CompanyContext` como autoridad, rutas anidadas validando el padre, contrato `__scope__`.

Migración prevista: una revisión Alembic `SAFE_MIGRATION` + informe de `MANUAL_REVIEW` para pedidos
en vuelo. Id ≤ 32 caracteres. Restricciones en ORM y migración (lección N7).

Frontend previsto: confirmación con detalle de insuficiencia por línea; reversión con motivo;
disponible vs. reservado en el detalle de pedido; reservas con trigger, motivo y sobreventa.
