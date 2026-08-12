# Matriz Frontend ↔ API — Spec 012 (pasada 2)

Todas las llamadas `apiFetch` del frontend resueltas contra el OpenAPI real (294 rutas).

| Página | Llamada | Endpoint backend | Métodos |
|---|---|---|---|
| `app/contexts/AuthContext.tsx` | `/auth/me` | `/auth/me` | GET |
| `app/contexts/AuthContext.tsx` | `/auth/login` | `/auth/login` | POST |
| `app/contexts/AuthContext.tsx` | `/auth/logout` | `/auth/logout` | POST |
| `app/contexts/AuthContext.tsx` | `/auth/refresh` | `/auth/refresh` | POST |
| `app/contexts/LicenseContext.tsx` | `/license/status` | `/license/status` | GET |
| `components/AsyncCombobox.tsx` | `${searchUrl}?${params.toString()}` | **SIN_ENDPOINT** | — |
| `modules/compras/cuentas-por-pagar/CuentasPorPagarPage.tsx` | `/maestros/terceros` | `/maestros/terceros` | GET, POST |
| `modules/compras/cuentas-por-pagar/CuentasPorPagarPage.tsx` | `/purchasing/open-items` | `/purchasing/open-items` | GET |
| `modules/compras/cuentas-por-pagar/CuentasPorPagarPage.tsx` | `/purchasing/payments` | `/purchasing/payments` | GET, POST |
| `modules/compras/cuentas-por-pagar/CuentasPorPagarPage.tsx` | `/purchasing/aging` | `/purchasing/aging` | GET |
| `modules/compras/cuentas-por-pagar/CuentasPorPagarPage.tsx` | `/purchasing/payments` | `/purchasing/payments` | GET, POST |
| `modules/compras/cuentas-por-pagar/CuentasPorPagarPage.tsx` | `/purchasing/advances` | `/purchasing/advances` | POST |
| `modules/compras/cuentas-por-pagar/CuentasPorPagarPage.tsx` | `/purchasing/payment-schedules` | `/purchasing/payment-schedules` | POST |
| `modules/compras/cuentas-por-pagar/CuentasPorPagarPage.tsx` | `/purchasing/applications` | `/purchasing/applications` | POST |
| `modules/compras/cuentas-por-pagar/CuentasPorPagarPage.tsx` | `/purchasing/payments/${id}/transition` | `/purchasing/payments/*/transition` | POST |
| `modules/compras/devoluciones/DevolucionesComprasPage.tsx` | `/purchasing/returns` | `/purchasing/returns` | GET, POST |
| `modules/compras/devoluciones/DevolucionesComprasPage.tsx` | `/maestros/catalogos/items?status=ACTIVE` | `/maestros/catalogos/items` | GET, POST |
| `modules/compras/devoluciones/DevolucionesComprasPage.tsx` | `/purchasing/returns` | `/purchasing/returns` | GET, POST |
| `modules/compras/devoluciones/DevolucionesComprasPage.tsx` | `/purchasing/returns/${lineReturn}/lines` | `/purchasing/returns/*/lines` | POST |
| `modules/compras/facturas/FacturasProveedorPage.tsx` | `/purchasing/supplier-invoices` | `/purchasing/supplier-invoices` | GET, POST |
| `modules/compras/facturas/FacturasProveedorPage.tsx` | `/maestros/terceros` | `/maestros/terceros` | GET, POST |
| `modules/compras/facturas/FacturasProveedorPage.tsx` | `/maestros/catalogos/items?status=ACTIVE` | `/maestros/catalogos/items` | GET, POST |
| `modules/compras/facturas/FacturasProveedorPage.tsx` | `/purchasing/supplier-invoices` | `/purchasing/supplier-invoices` | GET, POST |
| `modules/compras/facturas/FacturasProveedorPage.tsx` | `/purchasing/supplier-invoices/${lineInvoice}/lines` | `/purchasing/supplier-invoices/*/lines` | POST |
| `modules/compras/facturas/FacturasProveedorPage.tsx` | `/purchasing/supplier-invoices/${id}/transition` | `/purchasing/supplier-invoices/*/transition` | POST |
| `modules/compras/notas/NotasComprasPage.tsx` | `/purchasing/credit-notes` | `/purchasing/credit-notes` | GET, POST |
| `modules/compras/notas/NotasComprasPage.tsx` | `/maestros/terceros` | `/maestros/terceros` | GET, POST |
| `modules/compras/notas/NotasComprasPage.tsx` | `/purchasing/credit-notes` | `/purchasing/credit-notes` | GET, POST |
| `modules/compras/notas/NotasComprasPage.tsx` | `/purchasing/credit-notes/${id}/post` | `/purchasing/credit-notes/*/post` | POST |
| `modules/compras/ordenes/OrdenesComprasPage.tsx` | `/purchasing/orders` | `/purchasing/orders` | GET, POST |
| `modules/compras/ordenes/OrdenesComprasPage.tsx` | `/maestros/terceros` | `/maestros/terceros` | GET, POST |
| `modules/compras/ordenes/OrdenesComprasPage.tsx` | `/maestros/catalogos/items?status=ACTIVE` | `/maestros/catalogos/items` | GET, POST |
| `modules/compras/ordenes/OrdenesComprasPage.tsx` | `/purchasing/orders` | `/purchasing/orders` | GET, POST |
| `modules/compras/ordenes/OrdenesComprasPage.tsx` | `/purchasing/orders/${lineOrder}/lines` | `/purchasing/orders/*/lines` | POST |
| `modules/compras/ordenes/OrdenesComprasPage.tsx` | `/purchasing/orders/${id}/transition` | `/purchasing/orders/*/transition` | POST |
| `modules/compras/recepciones/RecepcionesPage.tsx` | `/purchasing/receipts` | `/purchasing/receipts` | GET, POST |
| `modules/compras/recepciones/RecepcionesPage.tsx` | `/purchasing/receipts/${id}/${action}` | `/purchasing/receipts/*/lines` | POST |
| `modules/compras/requisiciones/RequisicionesPage.tsx` | `/purchasing/requisitions` | `/purchasing/requisitions` | GET, POST |
| `modules/compras/requisiciones/RequisicionesPage.tsx` | `/purchasing/requisitions/${id}/transition` | `/purchasing/requisitions/*/transition` | POST |
| `modules/fiscal/configuracion/ConfiguracionPage.tsx` | `/fiscal/legal-sources` | `/fiscal/legal-sources` | GET, POST |
| `modules/fiscal/configuracion/ConfiguracionPage.tsx` | `/fiscal/tax-rule-versions` | `/fiscal/tax-rule-versions` | GET, POST |
| `modules/fiscal/configuracion/ConfiguracionPage.tsx` | `/fiscal/legal-sources` | `/fiscal/legal-sources` | GET, POST |
| `modules/fiscal/configuracion/ConfiguracionPage.tsx` | `/fiscal/legal-sources/${id}/activate` | `/fiscal/legal-sources/*/activate` | POST |
| `modules/fiscal/configuracion/ConfiguracionPage.tsx` | `/fiscal/tax-rule-versions` | `/fiscal/tax-rule-versions` | GET, POST |
| `modules/fiscal/configuracion/ConfiguracionPage.tsx` | `/fiscal/tax-rule-versions/${id}/approve` | `/fiscal/tax-rule-versions/*/approve` | POST |
| `modules/fiscal/configuracion/ConfiguracionPage.tsx` | `/fiscal/tax-calculations` | `/fiscal/tax-calculations` | POST, GET |
| `modules/fiscal/emision/EmisionPage.tsx` | `/fiscal/documents` | `/fiscal/documents` | GET |
| `modules/fiscal/emision/EmisionPage.tsx` | `/sales/invoices` | `/sales/invoices` | GET, POST |
| `modules/fiscal/emision/EmisionPage.tsx` | `/fiscal/number-series` | `/fiscal/number-series` | GET, POST |
| `modules/fiscal/emision/EmisionPage.tsx` | `/fiscal/control-batches` | `/fiscal/control-batches` | GET, POST |
| `modules/fiscal/emision/EmisionPage.tsx` | `/fiscal/documents/emit` | `/fiscal/documents/emit` | POST |
| `modules/fiscal/emision/EmisionPage.tsx` | `/fiscal/documents/${id}/print` | `/fiscal/documents/*/print` | POST |
| `modules/fiscal/libros/LibrosPage.tsx` | `/fiscal/books/${bookType}?period=${period || "0"}` | `/fiscal/books/*` | GET |
| `modules/fiscal/libros/LibrosPage.tsx` | `/fiscal/periods` | `/fiscal/periods` | GET, POST |
| `modules/fiscal/libros/LibrosPage.tsx` | `/fiscal/periods` | `/fiscal/periods` | GET, POST |
| `modules/fiscal/libros/LibrosPage.tsx` | `/fiscal/periods/${id}/transition` | `/fiscal/periods/*/transition` | POST |
| `modules/fiscal/notas/NotasPage.tsx` | `/fiscal/credit-debit-notes` | `/fiscal/credit-debit-notes` | POST, GET |
| `modules/fiscal/notas/NotasPage.tsx` | `/sales/invoices` | `/sales/invoices` | GET, POST |
| `modules/fiscal/notas/NotasPage.tsx` | `/fiscal/credit-debit-notes` | `/fiscal/credit-debit-notes` | POST, GET |
| `modules/fiscal/numeracion/NumeracionPage.tsx` | `/fiscal/number-series` | `/fiscal/number-series` | GET, POST |
| `modules/fiscal/numeracion/NumeracionPage.tsx` | `/fiscal/control-batches` | `/fiscal/control-batches` | GET, POST |
| `modules/fiscal/numeracion/NumeracionPage.tsx` | `/fiscal/control-numbers` | `/fiscal/control-numbers` | GET |
| `modules/fiscal/numeracion/NumeracionPage.tsx` | `/fiscal/number-series` | `/fiscal/number-series` | GET, POST |
| `modules/fiscal/numeracion/NumeracionPage.tsx` | `/fiscal/control-batches` | `/fiscal/control-batches` | GET, POST |
| `modules/fiscal/retenciones/RetencionesPage.tsx` | `/fiscal/withholding-rules` | `/fiscal/withholding-rules` | GET, POST |
| `modules/fiscal/retenciones/RetencionesPage.tsx` | `/fiscal/withholdings` | `/fiscal/withholdings` | GET |
| `modules/fiscal/retenciones/RetencionesPage.tsx` | `/maestros/terceros` | `/maestros/terceros` | GET, POST |
| `modules/fiscal/retenciones/RetencionesPage.tsx` | `/fiscal/withholding-rules` | `/fiscal/withholding-rules` | GET, POST |
| `modules/fiscal/retenciones/RetencionesPage.tsx` | `/fiscal/withholdings/calculate` | `/fiscal/withholdings/calculate` | POST |
| `modules/fiscal/retenciones/RetencionesPage.tsx` | `/fiscal/withholdings/${id}/transition` | `/fiscal/withholdings/*/transition` | POST |
| `modules/fiscal/retenciones/RetencionesPage.tsx` | `/fiscal/withholdings/${id}/certificate` | `/fiscal/withholdings/*/certificate` | POST |
| `modules/homologacion/actos/ActosPage.tsx` | `/homologation/records` | `/homologation/records` | GET, POST |
| `modules/homologacion/actos/ActosPage.tsx` | `/homologation/records` | `/homologation/records` | GET, POST |
| `modules/homologacion/actos/ActosPage.tsx` | `/homologation/records/${id}/submit` | `/homologation/records/*/submit` | POST |
| `modules/homologacion/actos/ActosPage.tsx` | `/homologation/records/${id}/evaluate` | `/homologation/records/*/evaluate` | POST |
| `modules/homologacion/timeline/TimelinePage.tsx` | `/homologation/timeline` | `/homologation/timeline` | GET |
| `modules/homologacion/versiones/VersionesPage.tsx` | `/homologation/releases` | `/homologation/releases` | GET, POST |
| `modules/homologacion/versiones/VersionesPage.tsx` | `/homologation/records` | `/homologation/records` | GET, POST |
| `modules/homologacion/versiones/VersionesPage.tsx` | `/homologation/releases` | `/homologation/releases` | GET, POST |
| `modules/homologacion/versiones/VersionesPage.tsx` | `/homologation/releases/${id}/promote` | `/homologation/releases/*/promote` | POST |
| `modules/homologacion/versiones/VersionesPage.tsx` | `/homologation/releases/${id}/release` | `/homologation/releases/*/release` | POST |
| `modules/inventario/ajustes/AjustesPage.tsx` | `/inventory/adjustments` | `/inventory/adjustments` | POST, GET |
| `modules/inventario/ajustes/AjustesPage.tsx` | `/organization/warehouses?company_id=${companyId}` | `/organization/warehouses` | GET, POST |
| `modules/inventario/ajustes/AjustesPage.tsx` | `/maestros/catalogos/items?status=ACTIVE` | `/maestros/catalogos/items` | GET, POST |
| `modules/inventario/ajustes/AjustesPage.tsx` | `/inventory/adjustments` | `/inventory/adjustments` | POST, GET |
| `modules/inventario/ajustes/AjustesPage.tsx` | `/inventory/adjustments/${id}/transition` | `/inventory/adjustments/*/transition` | POST |
| `modules/inventario/conteos/ConteosPage.tsx` | `/inventory/counts` | `/inventory/counts` | POST, GET |
| `modules/inventario/conteos/ConteosPage.tsx` | `/organization/warehouses?company_id=${companyId}` | `/organization/warehouses` | GET, POST |
| `modules/inventario/conteos/ConteosPage.tsx` | `/maestros/catalogos/items?status=ACTIVE` | `/maestros/catalogos/items` | GET, POST |
| `modules/inventario/conteos/ConteosPage.tsx` | `/inventory/counts` | `/inventory/counts` | POST, GET |
| `modules/inventario/conteos/ConteosPage.tsx` | `/inventory/counts/${lineCount}/lines` | `/inventory/counts/*/lines` | POST |
| `modules/inventario/conteos/ConteosPage.tsx` | `/inventory/counts/${id}/transition` | `/inventory/counts/*/transition` | POST |
| `modules/inventario/existencias/ExistenciasPage.tsx` | `/inventory/balances?q=${encodeURIComponent(search)}` | `/inventory/balances` | GET |
| `modules/inventario/kardex/KardexPage.tsx` | `/inventory/movements?q=${encodeURIComponent(search)}` | `/inventory/movements` | GET, POST |
| `modules/inventario/lotes/LotesPage.tsx` | `/inventory/lots` | `/inventory/lots` | GET, POST |
| `modules/inventario/lotes/LotesPage.tsx` | `/maestros/catalogos/items?status=ACTIVE` | `/maestros/catalogos/items` | GET, POST |
| `modules/inventario/lotes/LotesPage.tsx` | `/inventory/lots` | `/inventory/lots` | GET, POST |
| `modules/inventario/lotes/LotesPage.tsx` | `/inventory/lots/${id}/transition` | `/inventory/lots/*/transition` | POST |
| `modules/inventario/movimientos/MovimientosPage.tsx` | `/inventory/movements` | `/inventory/movements` | GET, POST |
| `modules/inventario/movimientos/MovimientosPage.tsx` | `/organization/warehouses?company_id=${companyId}` | `/organization/warehouses` | GET, POST |
| `modules/inventario/movimientos/MovimientosPage.tsx` | `/maestros/catalogos/items?status=ACTIVE` | `/maestros/catalogos/items` | GET, POST |
| `modules/inventario/movimientos/MovimientosPage.tsx` | `/inventory/movement-types` | `/inventory/movement-types` | GET, POST |
| `modules/inventario/movimientos/MovimientosPage.tsx` | `/inventory/movements` | `/inventory/movements` | GET, POST |
| `modules/inventario/movimientos/MovimientosPage.tsx` | `/inventory/movements/reverse` | `/inventory/movements/reverse` | POST |
| `modules/inventario/transferencias/TransferenciasPage.tsx` | `/inventory/transfers` | `/inventory/transfers` | POST, GET |
| `modules/inventario/transferencias/TransferenciasPage.tsx` | `/organization/warehouses?company_id=${companyId}` | `/organization/warehouses` | GET, POST |
| `modules/inventario/transferencias/TransferenciasPage.tsx` | `/maestros/catalogos/items?status=ACTIVE` | `/maestros/catalogos/items` | GET, POST |
| `modules/inventario/transferencias/TransferenciasPage.tsx` | `/inventory/transfers` | `/inventory/transfers` | POST, GET |
| `modules/inventario/transferencias/TransferenciasPage.tsx` | `/inventory/transfers/${id}/transition` | `/inventory/transfers/*/transition` | POST |
| `modules/inventario/valorizacion/ValorizacionPage.tsx` | `/inventory/valuation` | `/inventory/valuation` | GET |
| `modules/inventario/valorizacion/ValorizacionPage.tsx` | `/inventory/cost-layers` | `/inventory/cost-layers` | GET |
| `modules/inventario/valorizacion/ValorizacionPage.tsx` | `/inventory/costing-profiles` | `/inventory/costing-profiles` | GET, POST |
| `modules/inventario/valorizacion/ValorizacionPage.tsx` | `/inventory/costing-profiles` | `/inventory/costing-profiles` | GET, POST |
| `modules/licenciamiento/configuracion/ConfiguracionCentralPage.tsx` | `/licensing/overview` | `/licensing/overview` | GET |
| `modules/licenciamiento/configuracion/ConfiguracionCentralPage.tsx` | `/licensing/central-config` | `/licensing/central-config` | GET, PUT |
| `modules/licenciamiento/configuracion/ConfiguracionCentralPage.tsx` | `/licensing/sync` | `/licensing/sync` | POST |
| `modules/licenciamiento/entitlements/EntitlementsPage.tsx` | `/licensing/entitlements` | `/licensing/entitlements` | GET |
| `modules/licenciamiento/entitlements/EntitlementsPage.tsx` | `/licensing/entitlement-snapshots` | `/licensing/entitlement-snapshots` | GET |
| `modules/licenciamiento/eventos/EventosPage.tsx` | `/license/history` | `/license/history` | GET |
| `modules/licenciamiento/renovacion/RenovacionPage.tsx` | `/licensing/renewal-requests` | `/licensing/renewal-requests` | GET, POST |
| `modules/licenciamiento/renovacion/RenovacionPage.tsx` | `/licensing/renewal-requests` | `/licensing/renewal-requests` | GET, POST |
| `modules/licenciamiento/renovacion/RenovacionPage.tsx` | `/licensing/renewal-requests/${id}/transition` | `/licensing/renewal-requests/*/transition` | POST |
| `modules/maestros/catalogos/CatalogosPage.tsx` | `/maestros/catalogos/unidades` | `/maestros/catalogos/unidades` | GET, POST |
| `modules/maestros/catalogos/CatalogosPage.tsx` | `/maestros/catalogos/taxonomia` | `/maestros/catalogos/taxonomia` | GET, POST |
| `modules/maestros/perfiles/PerfilesFiscalesPage.tsx` | `/maestros/perfiles` | `/maestros/perfiles` | GET, POST |
| `modules/maestros/perfiles/PerfilesFiscalesPage.tsx` | `/maestros/perfiles` | `/maestros/perfiles` | GET, POST |
| `modules/maestros/productos/ProductoNuevoPage.tsx` | `/maestros/catalogos/items` | `/maestros/catalogos/items` | GET, POST |
| `modules/maestros/productos/ProductosPage.tsx` | `/maestros/catalogos/items?q=${encodeURIComponent(search)}&status=ACTIVE` | `/maestros/catalogos/items` | GET, POST |
| `modules/maestros/servicios/ServiciosPage.tsx` | `/maestros/catalogos/items?q=${encodeURIComponent(search)}&status=ACTIVE` | `/maestros/catalogos/items` | GET, POST |
| `modules/maestros/terceros/TercerosPage.tsx` | `/maestros/terceros?q=${encodeURIComponent(search)}` | `/maestros/terceros` | GET, POST |
| `modules/organizacion/almacenes/AlmacenesPage.tsx` | `/organization/warehouses?company_id=${encodeURIComponent(companyId ?? "")}` | `/organization/warehouses` | GET, POST |
| `modules/organizacion/almacenes/AlmacenesPage.tsx` | `/organization/branches?company_id=${encodeURIComponent(companyId ?? "")}` | `/organization/branches` | GET, POST |
| `modules/organizacion/almacenes/AlmacenesPage.tsx` | `/organization/warehouses` | `/organization/warehouses` | GET, POST |
| `modules/organizacion/establecimientos/EstablecimientosPage.tsx` | `/organization/branches?company_id=${encodeURIComponent(companyId ?? "")}` | `/organization/branches` | GET, POST |
| `modules/organizacion/establecimientos/EstablecimientosPage.tsx` | `/organization/establishments?branch_id=${encodeURIComponent(branchId)}` | `/organization/establishments` | GET, POST |
| `modules/organizacion/establecimientos/EstablecimientosPage.tsx` | `/organization/establishments` | `/organization/establishments` | GET, POST |
| `modules/organizacion/sucursales/SucursalesPage.tsx` | `/organization/branches?company_id=${encodeURIComponent(companyId ?? "")}` | `/organization/branches` | GET, POST |
| `modules/organizacion/sucursales/SucursalesPage.tsx` | `/organization/branches` | `/organization/branches` | GET, POST |
| `modules/organizacion/ubicaciones/UbicacionesPage.tsx` | `/organization/warehouses?company_id=${encodeURIComponent(companyId ?? "")}` | `/organization/warehouses` | GET, POST |
| `modules/organizacion/ubicaciones/UbicacionesPage.tsx` | `/organization/locations?warehouse_id=${encodeURIComponent(warehouseId)}` | `/organization/locations` | GET, POST |
| `modules/organizacion/ubicaciones/UbicacionesPage.tsx` | `/organization/locations` | `/organization/locations` | GET, POST |
| `modules/regulatorio/aprobaciones/AprobacionesPage.tsx` | `/regulatory/approval-requests` | `/regulatory/approval-requests` | POST, GET |
| `modules/regulatorio/aprobaciones/AprobacionesPage.tsx` | `/regulatory/approval-requests` | `/regulatory/approval-requests` | POST, GET |
| `modules/regulatorio/aprobaciones/AprobacionesPage.tsx` | `/regulatory/approval-requests/${id}/transition` | `/regulatory/approval-requests/*/transition` | POST |
| `modules/regulatorio/evaluacion/EvaluacionPage.tsx` | `/sales/shipments` | `/sales/shipments` | POST, GET |
| `modules/regulatorio/evaluacion/EvaluacionPage.tsx` | `/regulatory/evaluations` | `/regulatory/evaluations` | POST, GET |
| `modules/regulatorio/evaluacion/EvaluacionPage.tsx` | `/regulatory/contingencies` | `/regulatory/contingencies` | GET, POST |
| `modules/regulatorio/evaluacion/EvaluacionPage.tsx` | `/regulatory/evaluations` | `/regulatory/evaluations` | POST, GET |
| `modules/regulatorio/evaluacion/EvaluacionPage.tsx` | `/regulatory/evaluations/${id}/override` | `/regulatory/evaluations/*/override` | POST |
| `modules/regulatorio/evaluacion/EvaluacionPage.tsx` | `/regulatory/contingencies` | `/regulatory/contingencies` | GET, POST |
| `modules/regulatorio/evaluacion/EvaluacionPage.tsx` | `/regulatory/contingencies/${id}/end` | `/regulatory/contingencies/*/end` | POST |
| `modules/regulatorio/organismos/OrganismosPage.tsx` | `/regulatory/authorities` | `/regulatory/authorities` | GET, POST |
| `modules/regulatorio/organismos/OrganismosPage.tsx` | `/regulatory/permit-types` | `/regulatory/permit-types` | GET, POST |
| `modules/regulatorio/organismos/OrganismosPage.tsx` | `/regulatory/official-registrations` | `/regulatory/official-registrations` | GET, POST |
| `modules/regulatorio/organismos/OrganismosPage.tsx` | `/regulatory/profiles` | `/regulatory/profiles` | GET, POST |
| `modules/regulatorio/organismos/OrganismosPage.tsx` | `/regulatory/authorities` | `/regulatory/authorities` | GET, POST |
| `modules/regulatorio/organismos/OrganismosPage.tsx` | `/regulatory/permit-types` | `/regulatory/permit-types` | GET, POST |
| `modules/regulatorio/organismos/OrganismosPage.tsx` | `/regulatory/profiles` | `/regulatory/profiles` | GET, POST |
| `modules/regulatorio/permisos/PermisosPage.tsx` | `/regulatory/permits` | `/regulatory/permits` | GET, POST |
| `modules/regulatorio/permisos/PermisosPage.tsx` | `/regulatory/permit-types` | `/regulatory/permit-types` | GET, POST |
| `modules/regulatorio/permisos/PermisosPage.tsx` | `/regulatory/official-documents` | `/regulatory/official-documents` | GET, POST |
| `modules/regulatorio/permisos/PermisosPage.tsx` | `/regulatory/permits` | `/regulatory/permits` | GET, POST |
| `modules/regulatorio/permisos/PermisosPage.tsx` | `/regulatory/permits/${id}/transition` | `/regulatory/permits/*/transition` | POST |
| `modules/regulatorio/permisos/PermisosPage.tsx` | `/regulatory/official-documents` | `/regulatory/official-documents` | GET, POST |
| `modules/regulatorio/vehiculos/VehiculosPage.tsx` | `/regulatory/vehicles` | `/regulatory/vehicles` | GET, POST |
| `modules/regulatorio/vehiculos/VehiculosPage.tsx` | `/regulatory/drivers` | `/regulatory/drivers` | GET, POST |
| `modules/regulatorio/vehiculos/VehiculosPage.tsx` | `/maestros/terceros` | `/maestros/terceros` | GET, POST |
| `modules/regulatorio/vehiculos/VehiculosPage.tsx` | `/regulatory/vehicles` | `/regulatory/vehicles` | GET, POST |
| `modules/regulatorio/vehiculos/VehiculosPage.tsx` | `/regulatory/drivers` | `/regulatory/drivers` | GET, POST |
| `modules/reportes/auditoria/ReportesAuditoriaPage.tsx` | `/reporting/audit/timeline${qs ? ` | **SIN_ENDPOINT** | — |
| `modules/reportes/centro/CentroReportesPage.tsx` | `/reporting/reports/${reportKey}?period=${period || "0"}` | `/reporting/reports/*` | GET |
| `modules/reportes/centro/CentroReportesPage.tsx` | `/reporting/exports` | `/reporting/exports` | POST, GET |
| `modules/reportes/exportaciones/ExportacionesPage.tsx` | `/reporting/exports` | `/reporting/exports` | POST, GET |
| `modules/reportes/exportaciones/ExportacionesPage.tsx` | `/reporting/jobs` | `/reporting/jobs` | POST, GET |
| `modules/reportes/exportaciones/ExportacionesPage.tsx` | `/reporting/jobs` | `/reporting/jobs` | POST, GET |
| `modules/reportes/exportaciones/ExportacionesPage.tsx` | `/reporting/jobs/${created.id}/run` | `/reporting/jobs/*/run` | POST |
| `modules/seguridad/roles/RolesPage.tsx` | `/roles` | `/roles` | GET |
| `modules/seguridad/roles/RolesPage.tsx` | `/users` | `/users` | GET, POST |
| `modules/seguridad/roles/RolesPage.tsx` | `/users/${userId}/roles` | `/users/*/roles` | POST |
| `modules/seguridad/roles/RolesPage.tsx` | `/users/${uid}/roles/${rid}` | `/users/*/roles/*` | DELETE |
| `modules/seguridad/sesiones/SesionesPage.tsx` | `/auth/sessions` | `/auth/sessions` | GET |
| `modules/seguridad/sesiones/SesionesPage.tsx` | `/auth/sessions/${id}` | `/auth/sessions/*` | DELETE |
| `modules/seguridad/usuarios/UsuariosPage.tsx` | `/users` | `/users` | GET, POST |
| `modules/seguridad/usuarios/UsuariosPage.tsx` | `/users` | `/users` | GET, POST |
| `modules/tesoreria/cajas/CajasPage.tsx` | `/treasury/cash-sessions` | `/treasury/cash-sessions` | GET, POST |
| `modules/tesoreria/cajas/CajasPage.tsx` | `/treasury/cashboxes` | `/treasury/cashboxes` | GET, POST |
| `modules/tesoreria/cajas/CajasPage.tsx` | `/treasury/cash-sessions` | `/treasury/cash-sessions` | GET, POST |
| `modules/tesoreria/cajas/CajasPage.tsx` | `/treasury/cash-sessions/${id}/${endpoint}` | `/treasury/cash-sessions/*/movements` | POST |
| `modules/tesoreria/cajas/CajasPage.tsx` | `/treasury/cash-sessions/${selected.id}/arqueo` | `/treasury/cash-sessions/*/arqueo` | POST |
| `modules/tesoreria/cajas/CajasPage.tsx` | `/treasury/cash-sessions/${selected.id}/close` | `/treasury/cash-sessions/*/close` | POST |
| `modules/tesoreria/conciliacion/ConciliacionPage.tsx` | `/treasury/reconciliations` | `/treasury/reconciliations` | GET, POST |
| `modules/tesoreria/conciliacion/ConciliacionPage.tsx` | `/treasury/accounts` | `/treasury/accounts` | GET, POST |
| `modules/tesoreria/conciliacion/ConciliacionPage.tsx` | `/treasury/bank-transactions` | `/treasury/bank-transactions` | GET, POST |
| `modules/tesoreria/conciliacion/ConciliacionPage.tsx` | `/treasury/reconciliations` | `/treasury/reconciliations` | GET, POST |
| `modules/tesoreria/conciliacion/ConciliacionPage.tsx` | `/treasury/reconciliations/${id}/match` | `/treasury/reconciliations/*/match` | POST |
| `modules/tesoreria/conciliacion/ConciliacionPage.tsx` | `/treasury/reconciliations/${id}/transition` | `/treasury/reconciliations/*/transition` | POST |
| `modules/tesoreria/conciliacion/ConciliacionPage.tsx` | `/treasury/reconciliations/${selected.id}/lines` | `/treasury/reconciliations/*/lines` | POST |
| `modules/tesoreria/conciliacion/ConciliacionPage.tsx` | `/treasury/reconciliation-lines/${resolveLineId}/resolve` | `/treasury/reconciliation-lines/*/resolve` | POST |
| `modules/tesoreria/igft/IgftPage.tsx` | `/treasury/igft-events` | `/treasury/igft-events` | GET |
| `modules/tesoreria/igft/IgftPage.tsx` | `/treasury/fiscal-rules` | `/treasury/fiscal-rules` | GET, POST |
| `modules/tesoreria/igft/IgftPage.tsx` | `/treasury/fiscal-rules` | `/treasury/fiscal-rules` | GET, POST |
| `modules/tesoreria/igft/IgftPage.tsx` | `/treasury/igft-events/evaluate` | `/treasury/igft-events/evaluate` | POST |
| `modules/tesoreria/ingresos-egresos/IngresosEgresosPage.tsx` | `/treasury/bank-transactions` | `/treasury/bank-transactions` | GET, POST |
| `modules/tesoreria/ingresos-egresos/IngresosEgresosPage.tsx` | `/treasury/accounts` | `/treasury/accounts` | GET, POST |
| `modules/tesoreria/ingresos-egresos/IngresosEgresosPage.tsx` | `/treasury/cashboxes` | `/treasury/cashboxes` | GET, POST |
| `modules/tesoreria/ingresos-egresos/IngresosEgresosPage.tsx` | `/purchasing/payments` | `/purchasing/payments` | GET, POST |
| `modules/tesoreria/ingresos-egresos/IngresosEgresosPage.tsx` | `/sales/collections` | `/sales/collections` | GET, POST |
| `modules/tesoreria/ingresos-egresos/IngresosEgresosPage.tsx` | `/treasury/executions/${kind}` | `/treasury/executions/egresos` | POST |
| `modules/tesoreria/ingresos-egresos/IngresosEgresosPage.tsx` | `/treasury/bank-transactions` | `/treasury/bank-transactions` | GET, POST |
| `modules/tesoreria/maestros/MaestrosPage.tsx` | `/treasury/banks` | `/treasury/banks` | GET, POST |
| `modules/tesoreria/maestros/MaestrosPage.tsx` | `/treasury/accounts` | `/treasury/accounts` | GET, POST |
| `modules/tesoreria/maestros/MaestrosPage.tsx` | `/treasury/cashboxes` | `/treasury/cashboxes` | GET, POST |
| `modules/tesoreria/maestros/MaestrosPage.tsx` | `/treasury/payment-methods` | `/treasury/payment-methods` | GET, POST |
| `modules/tesoreria/maestros/MaestrosPage.tsx` | `/treasury/instruments` | `/treasury/instruments` | GET, POST |
| `modules/tesoreria/maestros/MaestrosPage.tsx` | `/treasury/currencies` | `/treasury/currencies` | GET, POST |
| `modules/tesoreria/maestros/MaestrosPage.tsx` | `/treasury/banks` | `/treasury/banks` | GET, POST |
| `modules/tesoreria/maestros/MaestrosPage.tsx` | `/treasury/accounts` | `/treasury/accounts` | GET, POST |
| `modules/tesoreria/maestros/MaestrosPage.tsx` | `/treasury/cashboxes` | `/treasury/cashboxes` | GET, POST |
| `modules/tesoreria/maestros/MaestrosPage.tsx` | `/treasury/payment-methods` | `/treasury/payment-methods` | GET, POST |
| `modules/tesoreria/maestros/MaestrosPage.tsx` | `/treasury/instruments` | `/treasury/instruments` | GET, POST |
| `modules/tesoreria/maestros/MaestrosPage.tsx` | `/treasury/currencies` | `/treasury/currencies` | GET, POST |
| `modules/tesoreria/maestros/MaestrosPage.tsx` | `/treasury/exchange-rates` | `/treasury/exchange-rates` | POST |
| `modules/tesoreria/transferencias/TransferenciasPage.tsx` | `/treasury/transfers` | `/treasury/transfers` | GET, POST |
| `modules/tesoreria/transferencias/TransferenciasPage.tsx` | `/treasury/accounts` | `/treasury/accounts` | GET, POST |
| `modules/tesoreria/transferencias/TransferenciasPage.tsx` | `/treasury/cashboxes` | `/treasury/cashboxes` | GET, POST |
| `modules/tesoreria/transferencias/TransferenciasPage.tsx` | `/treasury/transfers` | `/treasury/transfers` | GET, POST |
| `modules/ventas/cotizaciones/CotizacionesPage.tsx` | `/sales/quotes` | `/sales/quotes` | GET, POST |
| `modules/ventas/cotizaciones/CotizacionesPage.tsx` | `/maestros/terceros` | `/maestros/terceros` | GET, POST |
| `modules/ventas/cotizaciones/CotizacionesPage.tsx` | `/maestros/catalogos/items?status=ACTIVE` | `/maestros/catalogos/items` | GET, POST |
| `modules/ventas/cotizaciones/CotizacionesPage.tsx` | `/sales/quotes` | `/sales/quotes` | GET, POST |
| `modules/ventas/cotizaciones/CotizacionesPage.tsx` | `/sales/quotes/${lineQuote}/lines` | `/sales/quotes/*/lines` | POST |
| `modules/ventas/cuentas-por-cobrar/CuentasPorCobrarPage.tsx` | `/maestros/terceros` | `/maestros/terceros` | GET, POST |
| `modules/ventas/cuentas-por-cobrar/CuentasPorCobrarPage.tsx` | `/sales/open-items` | `/sales/open-items` | GET |
| `modules/ventas/cuentas-por-cobrar/CuentasPorCobrarPage.tsx` | `/sales/collections` | `/sales/collections` | GET, POST |
| `modules/ventas/cuentas-por-cobrar/CuentasPorCobrarPage.tsx` | `/sales/aging` | `/sales/aging` | GET |
| `modules/ventas/cuentas-por-cobrar/CuentasPorCobrarPage.tsx` | `/sales/collections` | `/sales/collections` | GET, POST |
| `modules/ventas/cuentas-por-cobrar/CuentasPorCobrarPage.tsx` | `/sales/customer-advances` | `/sales/customer-advances` | POST |
| `modules/ventas/cuentas-por-cobrar/CuentasPorCobrarPage.tsx` | `/sales/applications` | `/sales/applications` | POST |
| `modules/ventas/cuentas-por-cobrar/CuentasPorCobrarPage.tsx` | `/sales/collections/${id}/transition` | `/sales/collections/*/transition` | POST |
| `modules/ventas/despacho/DespachoPage.tsx` | `/sales/pick-lists` | `/sales/pick-lists` | GET, POST |
| `modules/ventas/despacho/DespachoPage.tsx` | `/sales/shipments` | `/sales/shipments` | POST, GET |
| `modules/ventas/despacho/DespachoPage.tsx` | `/sales/orders` | `/sales/orders` | GET, POST |
| `modules/ventas/despacho/DespachoPage.tsx` | `/organization/warehouses?company_id=${companyId}` | `/organization/warehouses` | GET, POST |
| `modules/ventas/despacho/DespachoPage.tsx` | `/sales/pick-lists` | `/sales/pick-lists` | GET, POST |
| `modules/ventas/despacho/DespachoPage.tsx` | `/sales/shipments` | `/sales/shipments` | POST, GET |
| `modules/ventas/despacho/DespachoPage.tsx` | `/sales/shipments/${id}/${action}` | `/sales/shipments/*/validate` | POST |
| `modules/ventas/devoluciones/DevolucionesVentasPage.tsx` | `/sales/returns` | `/sales/returns` | GET, POST |
| `modules/ventas/devoluciones/DevolucionesVentasPage.tsx` | `/maestros/catalogos/items?status=ACTIVE` | `/maestros/catalogos/items` | GET, POST |
| `modules/ventas/devoluciones/DevolucionesVentasPage.tsx` | `/sales/returns` | `/sales/returns` | GET, POST |
| `modules/ventas/devoluciones/DevolucionesVentasPage.tsx` | `/sales/returns/${lineReturn}/lines` | `/sales/returns/*/lines` | POST |
| `modules/ventas/facturas/FacturasVentasPage.tsx` | `/sales/invoices` | `/sales/invoices` | GET, POST |
| `modules/ventas/facturas/FacturasVentasPage.tsx` | `/maestros/terceros` | `/maestros/terceros` | GET, POST |
| `modules/ventas/facturas/FacturasVentasPage.tsx` | `/maestros/catalogos/items?status=ACTIVE` | `/maestros/catalogos/items` | GET, POST |
| `modules/ventas/facturas/FacturasVentasPage.tsx` | `/sales/invoices` | `/sales/invoices` | GET, POST |
| `modules/ventas/facturas/FacturasVentasPage.tsx` | `/sales/invoices/${lineInvoice}/lines` | `/sales/invoices/*/lines` | POST |
| `modules/ventas/facturas/FacturasVentasPage.tsx` | `/sales/invoices/${id}/transition` | `/sales/invoices/*/transition` | POST |
| `modules/ventas/notas/NotasVentasPage.tsx` | `/sales/credit-notes` | `/sales/credit-notes` | GET, POST |
| `modules/ventas/notas/NotasVentasPage.tsx` | `/sales/debit-notes` | `/sales/debit-notes` | GET, POST |
| `modules/ventas/notas/NotasVentasPage.tsx` | `/maestros/terceros` | `/maestros/terceros` | GET, POST |
| `modules/ventas/notas/NotasVentasPage.tsx` | `/sales/open-items` | `/sales/open-items` | GET |
| `modules/ventas/notas/NotasVentasPage.tsx` | `/sales/credit-notes` | `/sales/credit-notes` | GET, POST |
| `modules/ventas/notas/NotasVentasPage.tsx` | `/sales/debit-notes` | `/sales/debit-notes` | GET, POST |
| `modules/ventas/notas/NotasVentasPage.tsx` | `/sales/credit-notes/${id}/post` | `/sales/credit-notes/*/post` | POST |
| `modules/ventas/notas/NotasVentasPage.tsx` | `/sales/credit-notes/${applyNoteId}/apply` | `/sales/credit-notes/*/apply` | POST |
| `modules/ventas/ordenes/OrdenesVentasPage.tsx` | `/sales/orders` | `/sales/orders` | GET, POST |
| `modules/ventas/ordenes/OrdenesVentasPage.tsx` | `/maestros/terceros` | `/maestros/terceros` | GET, POST |
| `modules/ventas/ordenes/OrdenesVentasPage.tsx` | `/maestros/catalogos/items?status=ACTIVE` | `/maestros/catalogos/items` | GET, POST |
| `modules/ventas/ordenes/OrdenesVentasPage.tsx` | `/sales/orders` | `/sales/orders` | GET, POST |
| `modules/ventas/ordenes/OrdenesVentasPage.tsx` | `/sales/orders/${lineOrder}/lines` | `/sales/orders/*/lines` | POST |
| `modules/ventas/ordenes/OrdenesVentasPage.tsx` | `/sales/orders/${id}/transition` | `/sales/orders/*/transition` | POST |
| `pages/AuditoriaPage.tsx` | `/audit/events?q=${encodeURIComponent(search)}` | `/audit/events` | GET |
| `pages/CambiarContrasenaPage.tsx` | `/auth/change-password` | `/auth/change-password` | POST |
| `pages/DashboardPage.tsx` | `/health/ready` | `/health/ready` | GET |
| `pages/DashboardPage.tsx` | `/reporting/dashboard` | `/reporting/dashboard` | GET |
| `pages/DiagnosticoPage.tsx` | `/system/diagnostics` | `/system/diagnostics` | GET |
| `pages/EmpresasPage.tsx` | `/organization/companies?q=${encodeURIComponent(search)}` | `/organization/companies` | GET, POST |
| `pages/LoginPage.tsx` | `/setup/status` | `/setup/status` | GET |
| `pages/LoginPage.tsx` | `/setup/status` | `/setup/status` | GET |
| `pages/MiLicenciaPage.tsx` | `/license/status` | `/license/status` | GET |
| `pages/MiLicenciaPage.tsx` | `/license/renewal-request` | `/license/renewal-request` | POST |
| `pages/SetupPage.tsx` | `/setup/initialize` | `/setup/initialize` | POST |

Total llamadas: 281 · Sin endpoint: 2

## Nota sobre SIN_ENDPOINT (falsos positivos de extracción)
Las 2 filas `SIN_ENDPOINT` son artefactos del escáner con template literals
dinámicos (interpolación con backticks anidados), no llamadas rotas:
- `AsyncCombobox` → `${searchUrl}?${params}` (URL de búsqueda pasada por prop).
- `ReportesAuditoriaPage` → `/reporting/audit/timeline${qs ? ...}` (filtros opcionales).
El gate autoritativo G3/G4 (`src/tests/audit-completeness.test.ts`, 193 casos)
valida que todo endpoint estático del frontend existe en el OpenAPI y pasa.
