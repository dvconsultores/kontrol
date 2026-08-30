# MATRIZ DE ALCANCE POR ENDPOINT — ARCH-MC-001

**404 operaciones** sobre **294 rutas**.
Toda operación queda clasificada; no se admite ruta sensible al negocio sin alcance declarado.

## Recuento

| Alcance | Operaciones |
|---|---:|
| `COMPANY_SCOPE` | 276 |
| `MIXTO` | 79 |
| `TENANT/INSTALLATION` | 49 |
| **Total** | **404** |

`MIXTO` son las rutas de organización y unidades, donde la empresa ya viaja
explícita: no necesitan contexto, pero **sí** validarla contra los accesos del
usuario, cosa que hoy no hacen del todo.

## Detalle por dominio

### organization-structure (53)

| Método | Ruta | Alcance | Origen de la empresa | Hoy | Debe |
|---|---|---|---|---|---|
| DELETE | `/api/v1/organization/aisles/{node_id}` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| GET | `/api/v1/organization/aisles/{node_id}` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| PATCH | `/api/v1/organization/aisles/{node_id}` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| POST | `/api/v1/organization/aisles/{node_id}/activate` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| POST | `/api/v1/organization/aisles/{node_id}/deactivate` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| DELETE | `/api/v1/organization/levels/{node_id}` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| GET | `/api/v1/organization/levels/{node_id}` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| PATCH | `/api/v1/organization/levels/{node_id}` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| POST | `/api/v1/organization/levels/{node_id}/activate` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| POST | `/api/v1/organization/levels/{node_id}/deactivate` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| GET | `/api/v1/organization/location-types` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| POST | `/api/v1/organization/location-types` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| PATCH | `/api/v1/organization/location-types/{item_id}` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| GET | `/api/v1/organization/locations` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| POST | `/api/v1/organization/locations` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| POST | `/api/v1/organization/locations/bulk` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| GET | `/api/v1/organization/locations/ordered` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| DELETE | `/api/v1/organization/locations/{location_id}` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| GET | `/api/v1/organization/locations/{location_id}` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| PATCH | `/api/v1/organization/locations/{location_id}` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| POST | `/api/v1/organization/locations/{location_id}/activate` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| POST | `/api/v1/organization/locations/{location_id}/block` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| POST | `/api/v1/organization/locations/{location_id}/deactivate` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| DELETE | `/api/v1/organization/racks/{node_id}` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| GET | `/api/v1/organization/racks/{node_id}` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| PATCH | `/api/v1/organization/racks/{node_id}` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| POST | `/api/v1/organization/racks/{node_id}/activate` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| POST | `/api/v1/organization/racks/{node_id}/deactivate` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| GET | `/api/v1/organization/warehouses` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| POST | `/api/v1/organization/warehouses` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| DELETE | `/api/v1/organization/warehouses/{warehouse_id}` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| GET | `/api/v1/organization/warehouses/{warehouse_id}` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| PATCH | `/api/v1/organization/warehouses/{warehouse_id}` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| POST | `/api/v1/organization/warehouses/{warehouse_id}/activate` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| GET | `/api/v1/organization/warehouses/{warehouse_id}/aisles` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| POST | `/api/v1/organization/warehouses/{warehouse_id}/aisles` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| POST | `/api/v1/organization/warehouses/{warehouse_id}/deactivate` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| GET | `/api/v1/organization/warehouses/{warehouse_id}/levels` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| POST | `/api/v1/organization/warehouses/{warehouse_id}/levels` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| GET | `/api/v1/organization/warehouses/{warehouse_id}/racks` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| POST | `/api/v1/organization/warehouses/{warehouse_id}/racks` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| GET | `/api/v1/organization/warehouses/{warehouse_id}/structure` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| PATCH | `/api/v1/organization/warehouses/{warehouse_id}/structure-levels` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| GET | `/api/v1/organization/warehouses/{warehouse_id}/zones` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| POST | `/api/v1/organization/warehouses/{warehouse_id}/zones` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| GET | `/api/v1/organization/zone-types` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| POST | `/api/v1/organization/zone-types` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| PATCH | `/api/v1/organization/zone-types/{item_id}` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| DELETE | `/api/v1/organization/zones/{node_id}` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| GET | `/api/v1/organization/zones/{node_id}` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| PATCH | `/api/v1/organization/zones/{node_id}` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| POST | `/api/v1/organization/zones/{node_id}/activate` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| POST | `/api/v1/organization/zones/{node_id}/deactivate` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |

### compras (40)

| Método | Ruta | Alcance | Origen de la empresa | Hoy | Debe |
|---|---|---|---|---|---|
| POST | `/api/v1/purchasing/advances` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/purchasing/aging` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/purchasing/applications` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/purchasing/credit-notes` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/purchasing/credit-notes` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/purchasing/credit-notes/{note_id}/post` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/purchasing/open-items` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/purchasing/orders` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/purchasing/orders` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/purchasing/orders/{order_id}` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/purchasing/orders/{order_id}/lines` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/purchasing/orders/{order_id}/transition` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/purchasing/payment-schedules` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/purchasing/payments` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/purchasing/payments` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/purchasing/payments/{payment_id}/transition` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/purchasing/quotes` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/purchasing/quotes` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/purchasing/quotes/{quote_id}/lines` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/purchasing/receipts` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/purchasing/receipts` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/purchasing/receipts/{receipt_id}/accept` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/purchasing/receipts/{receipt_id}/confirm` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/purchasing/receipts/{receipt_id}/lines` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/purchasing/receipts/{receipt_id}/quality` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/purchasing/requisitions` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/purchasing/requisitions` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/purchasing/requisitions/{req_id}/lines` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/purchasing/requisitions/{req_id}/transition` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/purchasing/returns` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/purchasing/returns` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/purchasing/returns/{return_id}/lines` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/purchasing/supplier-invoices` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/purchasing/supplier-invoices` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/purchasing/supplier-invoices/{invoice_id}` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/purchasing/supplier-invoices/{invoice_id}/lines` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/purchasing/supplier-invoices/{invoice_id}/transition` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/purchasing/triple-match` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/purchasing/withholdings` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/purchasing/withholdings/{withholding_id}/transition` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |

### tesoreria (38)

| Método | Ruta | Alcance | Origen de la empresa | Hoy | Debe |
|---|---|---|---|---|---|
| GET | `/api/v1/treasury/accounts` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/treasury/accounts` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/treasury/bank-transactions` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/treasury/bank-transactions` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/treasury/banks` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/treasury/banks` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/treasury/cash-sessions` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/treasury/cash-sessions` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/treasury/cash-sessions/{session_id}` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/treasury/cash-sessions/{session_id}/arqueo` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/treasury/cash-sessions/{session_id}/close` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/treasury/cash-sessions/{session_id}/movements` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/treasury/cash-sessions/{session_id}/pre-close` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/treasury/cash-sessions/{session_id}/reject` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/treasury/cashboxes` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/treasury/cashboxes` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/treasury/currencies` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/treasury/currencies` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/treasury/exchange-rates` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/treasury/executions/egresos` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/treasury/executions/ingresos` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/treasury/fiscal-rules` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/treasury/fiscal-rules` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/treasury/igft-events` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/treasury/igft-events/evaluate` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/treasury/instruments` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/treasury/instruments` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/treasury/payment-methods` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/treasury/payment-methods` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/treasury/reconciliation-lines/{line_id}/resolve` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/treasury/reconciliations` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/treasury/reconciliations` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/treasury/reconciliations/{reconciliation_id}` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/treasury/reconciliations/{reconciliation_id}/lines` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/treasury/reconciliations/{reconciliation_id}/match` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/treasury/reconciliations/{reconciliation_id}/transition` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/treasury/transfers` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/treasury/transfers` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |

### ventas (36)

| Método | Ruta | Alcance | Origen de la empresa | Hoy | Debe |
|---|---|---|---|---|---|
| GET | `/api/v1/sales/aging` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/sales/applications` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/sales/collections` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/sales/collections` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/sales/collections/{collection_id}/transition` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/sales/credit-notes` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/sales/credit-notes` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/sales/credit-notes/{note_id}/apply` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/sales/credit-notes/{note_id}/post` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/sales/customer-advances` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/sales/debit-notes` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/sales/debit-notes` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/sales/invoices` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/sales/invoices` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/sales/invoices/{invoice_id}/lines` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/sales/invoices/{invoice_id}/transition` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/sales/open-items` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/sales/orders` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/sales/orders` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/sales/orders/{order_id}` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/sales/orders/{order_id}/lines` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/sales/orders/{order_id}/transition` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/sales/pick-lists` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/sales/pick-lists` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/sales/quotes` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/sales/quotes` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/sales/quotes/{quote_id}/lines` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/sales/returns` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/sales/returns` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/sales/returns/{return_id}/lines` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/sales/shipments` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/sales/shipments` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/sales/shipments/{shipment_id}/confirm` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/sales/shipments/{shipment_id}/validate` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/sales/withholdings-suffered` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/sales/withholdings-suffered/{withholding_id}/transition` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |

### inventario (34)

| Método | Ruta | Alcance | Origen de la empresa | Hoy | Debe |
|---|---|---|---|---|---|
| GET | `/api/v1/inventory/adjustments` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/inventory/adjustments` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/inventory/adjustments/{adjustment_id}/transition` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/inventory/balances` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/inventory/balances/recompute` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/inventory/balances/{balance_id}` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/inventory/cost-layers` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/inventory/costing-profiles` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/inventory/costing-profiles` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/inventory/counts` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/inventory/counts` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/inventory/counts/{count_id}/lines` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/inventory/counts/{count_id}/transition` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/inventory/lots` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/inventory/lots` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/inventory/lots/{lot_id}/transition` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/inventory/movement-types` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/inventory/movement-types` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/inventory/movements` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/inventory/movements` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/inventory/movements/reverse` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/inventory/movements/{movement_id}` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/inventory/operations/receive` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/inventory/operations/ship` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/inventory/reservations` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/inventory/reservations` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/inventory/reservations/expire` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/inventory/reservations/{reservation_id}/release` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/inventory/serials` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/inventory/serials` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/inventory/transfers` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/inventory/transfers` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/inventory/transfers/{transfer_id}/transition` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/inventory/valuation` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |

### fiscal (32)

| Método | Ruta | Alcance | Origen de la empresa | Hoy | Debe |
|---|---|---|---|---|---|
| GET | `/api/v1/fiscal/books/{tax_type}` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/fiscal/control-batches` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/fiscal/control-batches` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/fiscal/control-numbers` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/fiscal/credit-debit-notes` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/fiscal/credit-debit-notes` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/fiscal/documents` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/fiscal/documents/emit` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/fiscal/documents/{document_id}` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/fiscal/documents/{document_id}/print` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/fiscal/legal-sources` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/fiscal/legal-sources` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/fiscal/legal-sources/{source_id}/activate` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/fiscal/number-series` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/fiscal/number-series` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/fiscal/periods` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/fiscal/periods` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/fiscal/periods/{period_id}/transition` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/fiscal/tax-calculations` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/fiscal/tax-calculations` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/fiscal/tax-profiles` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/fiscal/tax-return-batches` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/fiscal/tax-return-batches` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/fiscal/tax-rule-versions` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/fiscal/tax-rule-versions` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/fiscal/tax-rule-versions/{rule_id}/approve` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/fiscal/withholding-rules` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/fiscal/withholding-rules` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/fiscal/withholdings` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/fiscal/withholdings/calculate` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/fiscal/withholdings/{withholding_id}/certificate` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/fiscal/withholdings/{withholding_id}/transition` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |

### regulatorio (26)

| Método | Ruta | Alcance | Origen de la empresa | Hoy | Debe |
|---|---|---|---|---|---|
| GET | `/api/v1/regulatory/approval-requests` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/regulatory/approval-requests` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/regulatory/approval-requests/{request_id}/transition` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/regulatory/authorities` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/regulatory/authorities` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/regulatory/contingencies` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/regulatory/contingencies` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/regulatory/contingencies/{contingency_id}/end` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/regulatory/drivers` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/regulatory/drivers` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/regulatory/evaluations` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/regulatory/evaluations` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/regulatory/evaluations/{evaluation_id}/override` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/regulatory/official-documents` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/regulatory/official-documents` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/regulatory/official-registrations` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/regulatory/official-registrations` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/regulatory/permit-types` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/regulatory/permit-types` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/regulatory/permits` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/regulatory/permits` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/regulatory/permits/{permit_id}/transition` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/regulatory/profiles` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/regulatory/profiles` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/regulatory/vehicles` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/regulatory/vehicles` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |

### aprobaciones (22)

| Método | Ruta | Alcance | Origen de la empresa | Hoy | Debe |
|---|---|---|---|---|---|
| GET | `/api/v1/approvals/delegations` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/approvals/delegations` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/approvals/delegations/{delegation_id}/revoke` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/approvals/evaluate` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/approvals/inbox` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/approvals/policies` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/approvals/policies` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/approvals/policies/{policy_id}` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| PATCH | `/api/v1/approvals/policies/{policy_id}` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/approvals/policies/{policy_id}/activate` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/approvals/policies/{policy_id}/close` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/approvals/policies/{policy_id}/rules` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/approvals/policies/{policy_id}/rules/{rule_id}/levels` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/approvals/process-types` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/approvals/requests` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/approvals/requests` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/approvals/requests/by-document` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/approvals/requests/{request_id}` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/approvals/requests/{request_id}/cancel` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/approvals/steps/{step_id}/approve` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/approvals/steps/{step_id}/reject` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/approvals/steps/{step_id}/return` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |

### maestros-uom (20)

| Método | Ruta | Alcance | Origen de la empresa | Hoy | Debe |
|---|---|---|---|---|---|
| POST | `/api/v1/maestros/conversion/preview` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| DELETE | `/api/v1/maestros/presentaciones/{presentation_id}` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| GET | `/api/v1/maestros/presentaciones/{presentation_id}` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| PATCH | `/api/v1/maestros/presentaciones/{presentation_id}` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| POST | `/api/v1/maestros/presentaciones/{presentation_id}/activate` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| POST | `/api/v1/maestros/presentaciones/{presentation_id}/deactivate` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| GET | `/api/v1/maestros/presentaciones/{presentation_id}/versiones` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| POST | `/api/v1/maestros/presentaciones/{presentation_id}/versiones` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| GET | `/api/v1/maestros/productos/{product_id}/presentaciones` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| POST | `/api/v1/maestros/productos/{product_id}/presentaciones` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| PATCH | `/api/v1/maestros/productos/{product_id}/unidad-base` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| GET | `/api/v1/maestros/unidades` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| POST | `/api/v1/maestros/unidades` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| DELETE | `/api/v1/maestros/unidades/{unit_id}` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| GET | `/api/v1/maestros/unidades/{unit_id}` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| PATCH | `/api/v1/maestros/unidades/{unit_id}` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| POST | `/api/v1/maestros/unidades/{unit_id}/activate` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| GET | `/api/v1/maestros/unidades/{unit_id}/conversiones` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| POST | `/api/v1/maestros/unidades/{unit_id}/conversiones-fisicas` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| POST | `/api/v1/maestros/unidades/{unit_id}/deactivate` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |

### documentos (20)

| Método | Ruta | Alcance | Origen de la empresa | Hoy | Debe |
|---|---|---|---|---|---|
| GET | `/api/v1/documentos` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/documentos` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/documentos/categorias` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/documentos/categorias` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/documentos/por-recurso/{resource_type}/{resource_id}` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/documentos/salud/almacenamiento` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/documentos/tipos` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/documentos/tipos` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| PATCH | `/api/v1/documentos/tipos/{type_id}` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| DELETE | `/api/v1/documentos/vinculos/{link_id}` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| DELETE | `/api/v1/documentos/{document_id}` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/documentos/{document_id}` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| PATCH | `/api/v1/documentos/{document_id}` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/documentos/{document_id}/archive` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/documentos/{document_id}/descargar` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/documentos/{document_id}/preview` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/documentos/{document_id}/versiones` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/documentos/{document_id}/versiones` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/documentos/{document_id}/versiones/{version_id}/descargar` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/documentos/{document_id}/vinculos` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |

### maestros (18)

| Método | Ruta | Alcance | Origen de la empresa | Hoy | Debe |
|---|---|---|---|---|---|
| GET | `/api/v1/maestros/catalogos/atributos` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/maestros/catalogos/atributos` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/maestros/catalogos/items` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/maestros/catalogos/items` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/maestros/catalogos/items/search` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/maestros/catalogos/items/{item_id}` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/maestros/catalogos/taxonomia` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/maestros/catalogos/taxonomia` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/maestros/catalogos/unidades` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/maestros/catalogos/unidades` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/maestros/catalogos/unidades/{unit_id}/conversiones` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/maestros/perfiles` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/maestros/perfiles` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/maestros/terceros` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/maestros/terceros` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/maestros/terceros/{party_id}` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/maestros/terceros/{party_id}/deactivate` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/maestros/terceros/{party_id}/roles/{role}` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |

### licenciamiento (12)

| Método | Ruta | Alcance | Origen de la empresa | Hoy | Debe |
|---|---|---|---|---|---|
| GET | `/api/v1/licensing/central-config` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |
| PUT | `/api/v1/licensing/central-config` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |
| GET | `/api/v1/licensing/entitlement-snapshots` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |
| GET | `/api/v1/licensing/entitlements` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |
| POST | `/api/v1/licensing/mode-transition` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |
| GET | `/api/v1/licensing/offline-status` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |
| GET | `/api/v1/licensing/overview` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |
| GET | `/api/v1/licensing/renewal-requests` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |
| POST | `/api/v1/licensing/renewal-requests` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |
| POST | `/api/v1/licensing/renewal-requests/{request_id}/transition` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |
| POST | `/api/v1/licensing/sync` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |
| GET | `/api/v1/licensing/sync-runs` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |

### reportes (10)

| Método | Ruta | Alcance | Origen de la empresa | Hoy | Debe |
|---|---|---|---|---|---|
| GET | `/api/v1/reporting/audit/timeline` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/reporting/dashboard` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/reporting/exports` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/reporting/exports` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/reporting/exports/{export_id}/download` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/reporting/jobs` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/reporting/jobs` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/reporting/jobs/{job_id}` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| POST | `/api/v1/reporting/jobs/{job_id}/run` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |
| GET | `/api/v1/reporting/reports/{key}` | `COMPANY_SCOPE` | CompanyContext | `tenant_id` del usuario | Filtrar y escribir por CompanyContext |

### homologacion (10)

| Método | Ruta | Alcance | Origen de la empresa | Hoy | Debe |
|---|---|---|---|---|---|
| GET | `/api/v1/homologation/records` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |
| POST | `/api/v1/homologation/records` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |
| GET | `/api/v1/homologation/records/{record_id}` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |
| POST | `/api/v1/homologation/records/{record_id}/evaluate` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |
| POST | `/api/v1/homologation/records/{record_id}/submit` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |
| GET | `/api/v1/homologation/releases` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |
| POST | `/api/v1/homologation/releases` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |
| POST | `/api/v1/homologation/releases/{release_id}/promote` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |
| POST | `/api/v1/homologation/releases/{release_id}/release` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |
| GET | `/api/v1/homologation/timeline` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |

### auth (9)

| Método | Ruta | Alcance | Origen de la empresa | Hoy | Debe |
|---|---|---|---|---|---|
| POST | `/api/v1/auth/change-password` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |
| POST | `/api/v1/auth/login` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |
| POST | `/api/v1/auth/logout` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |
| GET | `/api/v1/auth/me` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |
| POST | `/api/v1/auth/password-reset/confirm` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |
| POST | `/api/v1/auth/password-reset/request` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |
| POST | `/api/v1/auth/refresh` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |
| GET | `/api/v1/auth/sessions` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |
| DELETE | `/api/v1/auth/sessions/{session_id}` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |

### license (6)

| Método | Ruta | Alcance | Origen de la empresa | Hoy | Debe |
|---|---|---|---|---|---|
| POST | `/api/v1/license/activate` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |
| GET | `/api/v1/license/history` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |
| POST | `/api/v1/license/import` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |
| GET | `/api/v1/license/installation-request` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |
| POST | `/api/v1/license/renewal-request` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |
| GET | `/api/v1/license/status` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |

### organization (6)

| Método | Ruta | Alcance | Origen de la empresa | Hoy | Debe |
|---|---|---|---|---|---|
| GET | `/api/v1/organization/branches` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| POST | `/api/v1/organization/branches` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| GET | `/api/v1/organization/companies` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| POST | `/api/v1/organization/companies` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| GET | `/api/v1/organization/establishments` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |
| POST | `/api/v1/organization/establishments` | `MIXTO` | `company_id` explícito en la ruta o el cuerpo | empresa explícita | Validar la empresa contra el contexto |

### users (4)

| Método | Ruta | Alcance | Origen de la empresa | Hoy | Debe |
|---|---|---|---|---|---|
| GET | `/api/v1/users` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |
| POST | `/api/v1/users` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |
| POST | `/api/v1/users/{user_id}/roles` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |
| DELETE | `/api/v1/users/{user_id}/roles/{role_id}` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |

### system (3)

| Método | Ruta | Alcance | Origen de la empresa | Hoy | Debe |
|---|---|---|---|---|---|
| GET | `/api/v1/health/live` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |
| GET | `/api/v1/health/ready` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |
| GET | `/api/v1/system/diagnostics` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |

### setup (2)

| Método | Ruta | Alcance | Origen de la empresa | Hoy | Debe |
|---|---|---|---|---|---|
| POST | `/api/v1/setup/initialize` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |
| GET | `/api/v1/setup/status` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |

### roles (1)

| Método | Ruta | Alcance | Origen de la empresa | Hoy | Debe |
|---|---|---|---|---|---|
| GET | `/api/v1/roles` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |

### audit (1)

| Método | Ruta | Alcance | Origen de la empresa | Hoy | Debe |
|---|---|---|---|---|---|
| GET | `/api/v1/audit/events` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |

### - (1)

| Método | Ruta | Alcance | Origen de la empresa | Hoy | Debe |
|---|---|---|---|---|---|
| GET | `/` | `TENANT/INSTALLATION` | no aplica | tenant | Sin cambio |
