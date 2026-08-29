# DEPENDENCIAS TÉCNICAS — COMPONENTE ↔ API ↔ SERVICIO ↔ TABLA ↔ INTEGRACIÓN

## Cadenas verificadas completas

| Componente frontend | API | Servicio | Tabla(s) | Worker | Integración |
|---|---|---|---|---|---|
| `OrdenesPage` (compras) | `/purchasing/orders/*` | `purchasing.service` | purchase_orders, purchase_order_lines | — | — |
| `RecepcionesPage` | `/purchasing/receipts/*` | `purchasing.service` → `inventory.service` | goods_receipts, inventory_movements, inventory_balances | — | — |
| `FacturasPage` (compras) | `/purchasing/invoices/*` | `purchasing.service` | supplier_invoices, triple_matches, ap_open_items | — | — |
| `CuentasPorPagarPage` | `/purchasing/ap/*` | `purchasing.service` | ap_payments, ap_applications, ap_advances | — | — |
| `ExistenciasPage` / `KardexPage` | `/inventory/balances`, `/movements` | `inventory.service` | inventory_balances, inventory_movements | — | — |
| `CajasPage` | `/treasury/cash-sessions/*` | `treasury.service` | cash_sessions, cash_session_movements | — | — |
| `EmisionPage` (fiscal) | `/fiscal/documents/*` | `fiscal.service` | fiscal_documents, control_numbers, fiscal_number_series | — | — |
| `ConfiguracionPage` (licenciamiento) | `/licensing/*` | `licensing.service` | license_* | — | `urllib.request` → servidor central |

## Cadenas rotas o incompletas

| Punto de ruptura | Detalle | Spec |
|---|---|---|
| `PickListLine` → `locations` | **No hay FK ni columna.** El picking no puede ordenarse por ubicación | 031, 032 |
| `GoodsReceiptLine` → `locations` | **No hay columna.** La recepción no ubica | 022 |
| `SalesInvoice` → `sales_orders` | **No hay FK.** La factura no conoce su pedido | 034 |
| Todas las `*_lines` → `units_of_measure` / `presentations` | **No hay columnas.** La unidad se pierde en la transacción | 011 |
| `file_metadata` → cualquier entidad | Sin `entity_type`/`entity_id`; **sin endpoint de subida** | 046 |
| `outbox_events` → publicador | Tabla declarada, **cero referencias** en el código | 048 |
| `feature_flags` → consumidor | Tabla declarada, **cero referencias** en el código | 001 |
| `cost_center_id` → `cost_centers` | Columna `String(36)` **sin tabla destino** | 007 |
| `customers.price_list` → maestro | `String(120)` **sin catálogo** | 012 |
| `organization` / `master_data` → `audit_events` | **Cero llamadas** a `_audit()` | 006, 051 |

## Integraciones — estado real

| Integración | Cliente HTTP | Configuración | Prueba | Estado |
|---|---|---|---|---|
| Licencia central | `urllib.request` (`licensing/service.py:375`) | `license_central_config` | Contrato v1 + idempotencia, **sin red real** | `implemented_not_tested` |
| Correo / SMTP | ✖ ninguno | 1 referencia textual | ✖ | `not_started` |
| BCV (tasas) | ✖ | ✖ | ✖ | `not_started` |
| Storage de archivos | ✖ (`storage_key` solo como columna) | ✖ | ✖ | `not_started` |
| Webhooks | ✖ | ✖ | ✖ | `not_started` |
| SENIAT / SICA / SIGESAI / SACS | ✖ | ✖ | ✖ | `future_scope` (P20: requiere convenio) |
| Bancos | ✖ | ✖ | ✖ | `future_scope` |
| Cola asíncrona (celery/redis) | ✖ | ✖ | ✖ | `not_started` — `report_jobs` se ejecuta en proceso |

**Ninguna integración externa ha sido probada contra un servicio real.**

## Infraestructura

| Elemento | Estado | Observación |
|---|---|---|
| `compose.yaml` | ✔ | Tag por defecto `latest` (P14) |
| `Dockerfile.backend` / `.frontend` / `.nginx` | ✔ | — |
| Healthchecks | ✔ | `/api/v1/health/live`, `/ready` |
| Volúmenes y persistencia | ✔ declarados | Nunca validados con restore |
| `watchtower` | ✔ opt-in por perfil | Requiere socket Docker |
| Nginx CSP/HSTS | ✔ | KAUD-005 resuelto |
| CI GitHub | ◐ | 2 workflows de build; sin pipeline de gates |
| `kontrol.py` + `scripts/*.sh` | ◐ | 8 scripts, solo `bash -n` |
