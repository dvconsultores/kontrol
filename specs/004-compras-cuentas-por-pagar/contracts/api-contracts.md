# CONTRATOS DE API — 004-COMPRAS-CUENTAS-POR-PAGAR (v1)

| Campo | Valor |
|---|---|
| Iniciativa | 004-compras-cuentas-por-pagar |
| Versión | 1.0 (borrador documental) |
| Ruta | `specs/004-compras-cuentas-por-pagar/contracts/api-contracts.md` |
| Fuente | DOC-03 §14 (convenciones) |

> Convenciones heredadas de 001: REST/JSON versionada; IDs opacos; errores con `code`, `message`, `field_errors`, `correlation_id`; listados con `q`, `status`, `sort`, `page`, `page_size`; `allowed_actions` en backend; POST críticos con `Idempotency-Key`; transiciones por endpoints explícitos.

## 1. Requisiciones y cotizaciones

| Método | Ruta | Descripción |
|---|---|---|
| GET/POST | `/api/v1/purchasing/requisitions` | Listar/crear requisiciones |
| POST | `/api/v1/purchasing/requisitions/{id}/submit` | Enviar a aprobación |
| POST | `/api/v1/purchasing/requisitions/{id}/approve` | Aprobar/Rechazar |
| GET/POST | `/api/v1/purchasing/quotes` | Listar/crear cotizaciones |
| GET | `/api/v1/purchasing/quotes/compare` | Comparación por necesidad |

## 2. Órdenes de compra

| Método | Ruta | Descripción |
|---|---|---|
| GET/POST | `/api/v1/purchasing/orders` | Listar/crear OC (`Idempotency-Key`) |
| GET | `/api/v1/purchasing/orders/{id}` | Detalle con líneas y snapshot |
| POST | `/api/v1/purchasing/orders/{id}/submit` | Enviar a aprobación |
| POST | `/api/v1/purchasing/orders/{id}/approve` | Aprobar (regla versionada) |
| POST | `/api/v1/purchasing/orders/{id}/reject` | Rechazar |
| POST | `/api/v1/purchasing/orders/{id}/cancel` | Cancelar (DRAFT/APPROVED) |
| POST | `/api/v1/purchasing/orders/{id}/close` | Cerrar |

## 3. Recepciones (integración con 003)

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/v1/purchasing/receipts` | Crear recepción contra OC |
| POST | `/api/v1/purchasing/receipts/{id}/confirm` | Confirmar (→ CONFIRMED) |
| POST | `/api/v1/purchasing/receipts/{id}/quality` | Calidad (→ QUALITY_PENDING) |
| POST | `/api/v1/purchasing/receipts/{id}/accept` | Aceptar → invoca 003 `receive` (lotes/seriales/capas) |
| POST | `/api/v1/purchasing/receipts/{id}/reject` | Rechazar línea |

## 4. Factura del proveedor y conciliación triple

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/v1/purchasing/supplier-invoices` | Crear factura (valida duplicidad; `Idempotency-Key`) |
| POST | `/api/v1/purchasing/supplier-invoices/{id}/validate` | Validar (→ VALIDATED) |
| POST | `/api/v1/purchasing/supplier-invoices/{id}/match` | Conciliar triple (→ MATCHED/EXCEPTION) |
| POST | `/api/v1/purchasing/supplier-invoices/{id}/approve` | Aprobar |
| POST | `/api/v1/purchasing/supplier-invoices/{id}/post` | Postar (→ POSTED) |
| POST | `/api/v1/purchasing/supplier-invoices/{id}/reverse` | Reverso vinculado |
| GET | `/api/v1/purchasing/triple-match` | Diferencias orden/recepción/factura |

## 5. Devoluciones y notas

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/v1/purchasing/returns` | Crear devolución (destino de inventario vía 003) |
| POST | `/api/v1/purchasing/credit-notes` | Nota de crédito del proveedor (reduce CxP) |

## 6. CxP — open items, pagos, aplicaciones, anticipos, aging

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/v1/purchasing/open-items` | Open items PAYABLE con saldo |
| POST | `/api/v1/purchasing/payments` | Registrar pago OUT (instrumentos; `Idempotency-Key`) |
| POST | `/api/v1/purchasing/payments/{id}/approve` | Aprobación de pago (segregación) |
| POST | `/api/v1/purchasing/applications` | Aplicar pago/anticipo/nota/retención a open item (atómica) |
| POST | `/api/v1/purchasing/advances` | Anticipo a proveedor (OUT) |
| POST | `/api/v1/purchasing/advances/{id}/apply` | Imputación posterior |
| GET | `/api/v1/purchasing/payment-schedules` | Programación de pagos |
| GET | `/api/v1/purchasing/aging` | Aging de CxP (buckets) |

## 7. Retenciones (referencia a reglas versionadas)

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/v1/purchasing/withholdings` | Registrar retención (estados; regla de referencia) |
| GET | `/api/v1/purchasing/withholdings` | Listar por proveedor/período/estado |
| POST | `/api/v1/purchasing/withholdings/{id}/transition` | Transición (practicada/emitida/…) |

## 8. Integración (consumo de 003 y contrato para 006)

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/v1/inventory/operations/receive` | **003** — invocado por la recepción de 004 (entrada + lotes + capas) |
| GET | `/api/v1/purchasing/payments` / `/applications` | Contrato v1 para **006** (conciliación bancaria) |

Todos los POST críticos aceptan `Idempotency-Key`; las transiciones usan endpoints explícitos.
