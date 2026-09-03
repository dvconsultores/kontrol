# CONTRATOS DE API — 005-VENTAS-CUENTAS-POR-COBRAR (v1)

| Campo | Valor |
|---|---|
| Iniciativa | 005-ventas-cuentas-por-cobrar |
| Versión | 1.0 (borrador documental) |
| Ruta | `specs/005-ventas-cuentas-por-cobrar/contracts/api-contracts.md` |
| Fuente | DOC-03 §14 (convenciones) |

> Convenciones heredadas de 001: REST/JSON versionada; errores con `code`, `message`, `field_errors`, `correlation_id`; listados con `q`, `status`, `sort`, `page`, `page_size`; `allowed_actions` en backend; POST críticos con `Idempotency-Key`; transiciones por endpoints explícitos.

## 1. Cotizaciones y pedidos

| Método | Ruta | Descripción |
|---|---|---|
| GET/POST | `/api/v1/sales/quotes` | Listar/crear cotizaciones (sin reserva) |
| GET/POST | `/api/v1/sales/orders` | Listar/crear pedidos/órdenes |
| POST | `/api/v1/sales/orders/{id}/submit` | **Confirmar** (`DRAFT → SUBMITTED`): reserva todo-o-nada en cantidad base; sin solicitud de crédito → `RELEASED` en la misma transacción (Spec 030). `409 INSUFFICIENT_AVAILABLE` con `details.lines`; `422 WAREHOUSE_REQUIRED` / `ORDER_EMPTY` |
| POST | `/api/v1/sales/orders/{id}/release` | `SUBMITTED → RELEASED` tras la decisión de 045 (`ensure_approved`). Sustituye a `/approve`: aprobar **no** reserva |
| POST | `/api/v1/sales/orders/{id}/reject` · `/revert` · `/cancel` | Con `{reason}` obligatorio (cuerpo estricto: `company_id` → 422). Liberan la reserva atómicamente; `revert` deja el pedido en `DRAFT` y cancela la solicitud de crédito viva |
| POST | `/api/v1/sales/orders/expire-reservations` | Vence reservas de pedidos con TTL cumplido y los pedidos que las sostenían. Idempotente. Sin worker (planificador: Spec 047) |
| GET/PUT | `/api/v1/sales/settings/reservation` | Política de reserva de la empresa: `reservation_trigger` (fijo, `ORDER_CONFIRMATION`), `reservation_ttl_days` (opcional) |
| POST | `/api/v1/sales/orders/{id}/transition` | Compatibilidad: `SUBMITTED/RELEASED/REJECTED/CANCELLED/DRAFT` delegan en los anteriores (`reason` en el cuerpo); `PREPARING`, `SHIPPED`, `CLOSED` como antes. `CREDIT_PENDING`, `APPROVED`, `RESERVED` → 409 |
| POST | `/api/v1/inventory/reservations/{id}/release` | Solo reservas **manuales**, con `{reason}`; las de pedido responden `409 RESERVATION_ORDER_BOUND` |

## 2. Despacho (integración con 003)

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/v1/sales/pick-lists` | Generar picking (via 003) |
| POST | `/api/v1/sales/shipments` | Crear despacho (validación documental) |
| POST | `/api/v1/sales/shipments/{id}/validate` | Validar traslado/permisos (bloqueo si falta/venció/no coincide) |
| POST | `/api/v1/sales/shipments/{id}/confirm` | Confirmar salida (via 003 `ship` → tránsito/entregado-no-facturado) |

## 3. Factura de venta y notas

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/v1/sales/invoices` | Emitir factura de venta (snapshot fiscal; `Idempotency-Key`) |
| POST | `/api/v1/sales/invoices/{id}/validate` / `/approve` / `/emit` / `/deliver` | Estados |
| POST | `/api/v1/sales/invoices/{id}/void` | Anulación vinculada |
| POST | `/api/v1/sales/credit-notes` | Nota de crédito (reduce CxC) |
| POST | `/api/v1/sales/debit-notes` | Nota de débito (aumenta CxC) |
| POST | `/api/v1/sales/returns` | Devolución de cliente (vía 003) |

## 4. CxC (reutiliza el motor de 004)

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/v1/sales/open-items` | Open items RECEIVABLE con saldo |
| POST | `/api/v1/sales/collections` | Registrar cobro (Payment IN, instrumentos; `Idempotency-Key`) |
| POST | `/api/v1/sales/collections/{id}/approve` | Aprobación de cobro |
| POST | `/api/v1/sales/applications` | Aplicar cobro/anticipo/nota/retención sufrida (atómica) |
| POST | `/api/v1/sales/customer-advances` | Anticipo de cliente (IN) |
| POST | `/api/v1/sales/customer-advances/{id}/apply` | Imputación posterior |
| POST | `/api/v1/sales/withholdings-suffered` | Retención sufrida |
| GET | `/api/v1/sales/aging` | Aging de CxC (buckets) |
| GET | `/api/v1/sales/collections` / `/applications` | Contrato v1 para **006** (conciliación) |

## 5. Integración (consumo de 003)

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/v1/inventory/operations/reserve` | **003** — reserva al aprobar la OV |
| POST | `/api/v1/inventory/operations/pick` | **003** — confirmación de picking |
| POST | `/api/v1/inventory/operations/ship` | **003** — salida (→ tránsito/entregado-no-facturado; costo) |

Todos los POST críticos aceptan `Idempotency-Key`; las transiciones usan endpoints explícitos.
