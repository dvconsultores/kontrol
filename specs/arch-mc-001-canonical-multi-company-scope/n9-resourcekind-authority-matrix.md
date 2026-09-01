# MATRIZ AUTORITATIVA DE TIPOS VINCULABLES — N9

**23 tipos.** 19 registrados antes de N9 más los 4 que `REM-046-001` exigía.

| # | Tipo | Entidad | Tabla | PK | Alcance | Autoridad | Permiso |
|---:|---|---|---|---|---|---|---|
| 1 | `ApprovalRequest` | `ApprovalRequest` | `approval_requests` | `id` | Empresa directa | `company_id` | `aprobaciones:view` |
| 2 | `PurchaseRequisition` | `PurchaseRequisition` | `purchase_requisitions` | `id` | Empresa directa | `company_id` | `compras:view` |
| 3 | `PurchaseOrder` | `PurchaseOrder` | `purchase_orders` | `id` | Empresa directa | `company_id` | `compras:view` |
| 4 | `GoodsReceipt` | `GoodsReceipt` | `goods_receipts` | `id` | Empresa directa | `company_id` | `compras:view` |
| 5 | `SupplierInvoice` | `SupplierInvoice` | `supplier_invoices` | `id` | Empresa directa | `company_id` | `compras:view` |
| 6 | **`Payment`** | `Payment` | `ap_payments` | `id` | Empresa directa | `company_id` | `compras:view` |
| 7 | `SalesOrder` | `SalesOrder` | `sales_orders` | `id` | Empresa directa | `company_id` | `ventas:view` |
| 8 | `SalesInvoice` | `SalesInvoice` | `sales_invoices` | `id` | Empresa directa | `company_id` | `ventas:view` |
| 9 | `Shipment` | `Shipment` | `shipments` | `id` | Empresa directa | `company_id` | `ventas:view` |
| 10 | `SalesReturn` | `SalesReturn` | `sales_returns` | `id` | Empresa directa | `company_id` | `ventas:view` |
| 11 | `InventoryAdjustment` | `InventoryAdjustment` | `inventory_adjustments` | `id` | Empresa directa | `company_id` | `inventario:view` |
| 12 | `StockCount` | `StockCount` | `stock_counts` | `id` | Empresa directa | `company_id` | `inventario:view` |
| 13 | `Warehouse` | `Warehouse` | `warehouses` | `id` | Empresa directa | `company_id` | `organization:view` |
| 14 | `Party` | `Party` | `parties` | `id` | Empresa directa | `company_id` | `maestros:view` |
| 15 | `CatalogItem` | `CatalogItem` | `catalog_items` | `id` | Empresa directa | `company_id` | `maestros:view` |
| 16 | `PermitInstance` | `PermitInstance` | `permit_instances` | `id` | Empresa directa | `company_id` | `regulatorio:view` |
| 17 | `OfficialDocument` | `OfficialDocument` | `official_documents` | `id` | Empresa directa | `company_id` | `regulatorio:view` |
| 18 | `TransportVehicle` | `TransportVehicle` | `transport_vehicles` | `id` | Empresa directa | `company_id` | `regulatorio:view` |
| 19 | `TransportDriver` | `TransportDriver` | `transport_drivers` | `id` | Empresa directa | `company_id` | `regulatorio:view` |
| 20 | **`BankTransaction`** | `BankTransaction` | `bank_transactions` | `id` | Empresa directa | `company_id` | `tesoreria:view` |
| 21 | **`CashSession`** | `CashSession` | `cash_sessions` | `id` | Empresa directa | `company_id` | `tesoreria:view` |
| 22 | **`Reconciliation`** | `Reconciliation` | `reconciliations` | `id` | Empresa directa | `company_id` | `tesoreria:view` |
| 23 | `HomologationRecord` | `HomologationRecord` | `homologation_records` | `id` | **Instalación** | — | `homologacion:view` |

En negrita, las cuatro que `REM-046-001` exigía.

## La única excepción, y por qué es correcta

`HomologationRecord` no tiene `company_id`. El acto de homologar una versión
fiscal es de la **instalación**, no de una empresa, así que `resolve_resource`
devuelve `None` y el control se apoya solo en el permiso.

Está escrito en el propio registro desde 046 y la prueba de los 23 lo trata
aparte: comprobar en él un cruce entre empresas que el contrato no promete daría
un aprobado falso.

## Los 22 restantes son de empresa directa

Ninguno deriva por autoridad. Eso no es simplificación: es lo que ARCH-MC-001
consiguió. Antes de N5 y N7, cinco de esos módulos guardaban el `tenant_id` en
esa columna, y por eso `REM-046-001` proponía añadir al registro un campo que
distinguiera empresa de tenant.

Hoy los 22 tienen `company_id` con clave foránea real a `companies`, y ese campo
no hace falta.
