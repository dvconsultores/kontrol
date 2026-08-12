# Matriz de Integración Full-Stack — Spec 012 (pasada 2)

Función (página) → endpoints consumidos → backend (existe) → evidencia.

| Página | Endpoints (únicos) | Resuelve backend |
|---|---|---|
| `app/contexts/AuthContext.tsx` | `/auth/login`, `/auth/logout`, `/auth/me`, `/auth/refresh` | SÍ |
| `app/contexts/LicenseContext.tsx` | `/license/status` | SÍ |
| `components/AsyncCombobox.tsx` | `SIN_ENDPOINT` | **NO** |
| `modules/compras/cuentas-por-pagar/CuentasPorPagarPage.tsx` | `/maestros/terceros`, `/purchasing/advances`, `/purchasing/aging`, `/purchasing/applications`, `/purchasing/open-items`, `/purchasing/payment-schedules`… | SÍ |
| `modules/compras/devoluciones/DevolucionesComprasPage.tsx` | `/maestros/catalogos/items`, `/purchasing/returns`, `/purchasing/returns/*/lines` | SÍ |
| `modules/compras/facturas/FacturasProveedorPage.tsx` | `/maestros/catalogos/items`, `/maestros/terceros`, `/purchasing/supplier-invoices`, `/purchasing/supplier-invoices/*/lines`, `/purchasing/supplier-invoices/*/transition` | SÍ |
| `modules/compras/notas/NotasComprasPage.tsx` | `/maestros/terceros`, `/purchasing/credit-notes`, `/purchasing/credit-notes/*/post` | SÍ |
| `modules/compras/ordenes/OrdenesComprasPage.tsx` | `/maestros/catalogos/items`, `/maestros/terceros`, `/purchasing/orders`, `/purchasing/orders/*/lines`, `/purchasing/orders/*/transition` | SÍ |
| `modules/compras/recepciones/RecepcionesPage.tsx` | `/purchasing/receipts`, `/purchasing/receipts/*/lines` | SÍ |
| `modules/compras/requisiciones/RequisicionesPage.tsx` | `/purchasing/requisitions`, `/purchasing/requisitions/*/transition` | SÍ |
| `modules/fiscal/configuracion/ConfiguracionPage.tsx` | `/fiscal/legal-sources`, `/fiscal/legal-sources/*/activate`, `/fiscal/tax-calculations`, `/fiscal/tax-rule-versions`, `/fiscal/tax-rule-versions/*/approve` | SÍ |
| `modules/fiscal/emision/EmisionPage.tsx` | `/fiscal/control-batches`, `/fiscal/documents`, `/fiscal/documents/*/print`, `/fiscal/documents/emit`, `/fiscal/number-series`, `/sales/invoices` | SÍ |
| `modules/fiscal/libros/LibrosPage.tsx` | `/fiscal/books/*`, `/fiscal/periods`, `/fiscal/periods/*/transition` | SÍ |
| `modules/fiscal/notas/NotasPage.tsx` | `/fiscal/credit-debit-notes`, `/sales/invoices` | SÍ |
| `modules/fiscal/numeracion/NumeracionPage.tsx` | `/fiscal/control-batches`, `/fiscal/control-numbers`, `/fiscal/number-series` | SÍ |
| `modules/fiscal/retenciones/RetencionesPage.tsx` | `/fiscal/withholding-rules`, `/fiscal/withholdings`, `/fiscal/withholdings/*/certificate`, `/fiscal/withholdings/*/transition`, `/fiscal/withholdings/calculate`, `/maestros/terceros` | SÍ |
| `modules/homologacion/actos/ActosPage.tsx` | `/homologation/records`, `/homologation/records/*/evaluate`, `/homologation/records/*/submit` | SÍ |
| `modules/homologacion/timeline/TimelinePage.tsx` | `/homologation/timeline` | SÍ |
| `modules/homologacion/versiones/VersionesPage.tsx` | `/homologation/records`, `/homologation/releases`, `/homologation/releases/*/promote`, `/homologation/releases/*/release` | SÍ |
| `modules/inventario/ajustes/AjustesPage.tsx` | `/inventory/adjustments`, `/inventory/adjustments/*/transition`, `/maestros/catalogos/items`, `/organization/warehouses` | SÍ |
| `modules/inventario/conteos/ConteosPage.tsx` | `/inventory/counts`, `/inventory/counts/*/lines`, `/inventory/counts/*/transition`, `/maestros/catalogos/items`, `/organization/warehouses` | SÍ |
| `modules/inventario/existencias/ExistenciasPage.tsx` | `/inventory/balances` | SÍ |
| `modules/inventario/kardex/KardexPage.tsx` | `/inventory/movements` | SÍ |
| `modules/inventario/lotes/LotesPage.tsx` | `/inventory/lots`, `/inventory/lots/*/transition`, `/maestros/catalogos/items` | SÍ |
| `modules/inventario/movimientos/MovimientosPage.tsx` | `/inventory/movement-types`, `/inventory/movements`, `/inventory/movements/reverse`, `/maestros/catalogos/items`, `/organization/warehouses` | SÍ |
| `modules/inventario/transferencias/TransferenciasPage.tsx` | `/inventory/transfers`, `/inventory/transfers/*/transition`, `/maestros/catalogos/items`, `/organization/warehouses` | SÍ |
| `modules/inventario/valorizacion/ValorizacionPage.tsx` | `/inventory/cost-layers`, `/inventory/costing-profiles`, `/inventory/valuation` | SÍ |
| `modules/licenciamiento/configuracion/ConfiguracionCentralPage.tsx` | `/licensing/central-config`, `/licensing/overview`, `/licensing/sync` | SÍ |
| `modules/licenciamiento/entitlements/EntitlementsPage.tsx` | `/licensing/entitlement-snapshots`, `/licensing/entitlements` | SÍ |
| `modules/licenciamiento/eventos/EventosPage.tsx` | `/license/history` | SÍ |
| `modules/licenciamiento/renovacion/RenovacionPage.tsx` | `/licensing/renewal-requests`, `/licensing/renewal-requests/*/transition` | SÍ |
| `modules/maestros/catalogos/CatalogosPage.tsx` | `/maestros/catalogos/taxonomia`, `/maestros/catalogos/unidades` | SÍ |
| `modules/maestros/perfiles/PerfilesFiscalesPage.tsx` | `/maestros/perfiles` | SÍ |
| `modules/maestros/productos/ProductoNuevoPage.tsx` | `/maestros/catalogos/items` | SÍ |
| `modules/maestros/productos/ProductosPage.tsx` | `/maestros/catalogos/items` | SÍ |
| `modules/maestros/servicios/ServiciosPage.tsx` | `/maestros/catalogos/items` | SÍ |
| `modules/maestros/terceros/TercerosPage.tsx` | `/maestros/terceros` | SÍ |
| `modules/organizacion/almacenes/AlmacenesPage.tsx` | `/organization/branches`, `/organization/warehouses` | SÍ |
| `modules/organizacion/establecimientos/EstablecimientosPage.tsx` | `/organization/branches`, `/organization/establishments` | SÍ |
| `modules/organizacion/sucursales/SucursalesPage.tsx` | `/organization/branches` | SÍ |
| `modules/organizacion/ubicaciones/UbicacionesPage.tsx` | `/organization/locations`, `/organization/warehouses` | SÍ |
| `modules/regulatorio/aprobaciones/AprobacionesPage.tsx` | `/regulatory/approval-requests`, `/regulatory/approval-requests/*/transition` | SÍ |
| `modules/regulatorio/evaluacion/EvaluacionPage.tsx` | `/regulatory/contingencies`, `/regulatory/contingencies/*/end`, `/regulatory/evaluations`, `/regulatory/evaluations/*/override`, `/sales/shipments` | SÍ |
| `modules/regulatorio/organismos/OrganismosPage.tsx` | `/regulatory/authorities`, `/regulatory/official-registrations`, `/regulatory/permit-types`, `/regulatory/profiles` | SÍ |
| `modules/regulatorio/permisos/PermisosPage.tsx` | `/regulatory/official-documents`, `/regulatory/permit-types`, `/regulatory/permits`, `/regulatory/permits/*/transition` | SÍ |
| `modules/regulatorio/vehiculos/VehiculosPage.tsx` | `/maestros/terceros`, `/regulatory/drivers`, `/regulatory/vehicles` | SÍ |
| `modules/reportes/auditoria/ReportesAuditoriaPage.tsx` | `SIN_ENDPOINT` | **NO** |
| `modules/reportes/centro/CentroReportesPage.tsx` | `/reporting/exports`, `/reporting/reports/*` | SÍ |
| `modules/reportes/exportaciones/ExportacionesPage.tsx` | `/reporting/exports`, `/reporting/jobs`, `/reporting/jobs/*/run` | SÍ |
| `modules/seguridad/roles/RolesPage.tsx` | `/roles`, `/users`, `/users/*/roles`, `/users/*/roles/*` | SÍ |
| `modules/seguridad/sesiones/SesionesPage.tsx` | `/auth/sessions`, `/auth/sessions/*` | SÍ |
| `modules/seguridad/usuarios/UsuariosPage.tsx` | `/users` | SÍ |
| `modules/tesoreria/cajas/CajasPage.tsx` | `/treasury/cash-sessions`, `/treasury/cash-sessions/*/arqueo`, `/treasury/cash-sessions/*/close`, `/treasury/cash-sessions/*/movements`, `/treasury/cashboxes` | SÍ |
| `modules/tesoreria/conciliacion/ConciliacionPage.tsx` | `/treasury/accounts`, `/treasury/bank-transactions`, `/treasury/reconciliation-lines/*/resolve`, `/treasury/reconciliations`, `/treasury/reconciliations/*/lines`, `/treasury/reconciliations/*/match`… | SÍ |
| `modules/tesoreria/igft/IgftPage.tsx` | `/treasury/fiscal-rules`, `/treasury/igft-events`, `/treasury/igft-events/evaluate` | SÍ |
| `modules/tesoreria/ingresos-egresos/IngresosEgresosPage.tsx` | `/purchasing/payments`, `/sales/collections`, `/treasury/accounts`, `/treasury/bank-transactions`, `/treasury/cashboxes`, `/treasury/executions/egresos` | SÍ |
| `modules/tesoreria/maestros/MaestrosPage.tsx` | `/treasury/accounts`, `/treasury/banks`, `/treasury/cashboxes`, `/treasury/currencies`, `/treasury/exchange-rates`, `/treasury/instruments`… | SÍ |
| `modules/tesoreria/transferencias/TransferenciasPage.tsx` | `/treasury/accounts`, `/treasury/cashboxes`, `/treasury/transfers` | SÍ |
| `modules/ventas/cotizaciones/CotizacionesPage.tsx` | `/maestros/catalogos/items`, `/maestros/terceros`, `/sales/quotes`, `/sales/quotes/*/lines` | SÍ |
| `modules/ventas/cuentas-por-cobrar/CuentasPorCobrarPage.tsx` | `/maestros/terceros`, `/sales/aging`, `/sales/applications`, `/sales/collections`, `/sales/collections/*/transition`, `/sales/customer-advances`… | SÍ |
| `modules/ventas/despacho/DespachoPage.tsx` | `/organization/warehouses`, `/sales/orders`, `/sales/pick-lists`, `/sales/shipments`, `/sales/shipments/*/validate` | SÍ |
| `modules/ventas/devoluciones/DevolucionesVentasPage.tsx` | `/maestros/catalogos/items`, `/sales/returns`, `/sales/returns/*/lines` | SÍ |
| `modules/ventas/facturas/FacturasVentasPage.tsx` | `/maestros/catalogos/items`, `/maestros/terceros`, `/sales/invoices`, `/sales/invoices/*/lines`, `/sales/invoices/*/transition` | SÍ |
| `modules/ventas/notas/NotasVentasPage.tsx` | `/maestros/terceros`, `/sales/credit-notes`, `/sales/credit-notes/*/apply`, `/sales/credit-notes/*/post`, `/sales/debit-notes`, `/sales/open-items` | SÍ |
| `modules/ventas/ordenes/OrdenesVentasPage.tsx` | `/maestros/catalogos/items`, `/maestros/terceros`, `/sales/orders`, `/sales/orders/*/lines`, `/sales/orders/*/transition` | SÍ |
| `pages/AuditoriaPage.tsx` | `/audit/events` | SÍ |
| `pages/CambiarContrasenaPage.tsx` | `/auth/change-password` | SÍ |
| `pages/DashboardPage.tsx` | `/health/ready`, `/reporting/dashboard` | SÍ |
| `pages/DiagnosticoPage.tsx` | `/system/diagnostics` | SÍ |
| `pages/EmpresasPage.tsx` | `/organization/companies` | SÍ |
| `pages/LoginPage.tsx` | `/setup/status` | SÍ |
| `pages/MiLicenciaPage.tsx` | `/license/renewal-request`, `/license/status` | SÍ |
| `pages/SetupPage.tsx` | `/setup/initialize` | SÍ |
