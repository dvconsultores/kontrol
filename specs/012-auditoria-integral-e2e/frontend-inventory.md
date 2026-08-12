# Inventario del Frontend — Spec 012 (pasada 2)

Fuente: evidencia regenerada (menu-inventory, route-audit, frontend-api-calls).

## 1. Menú

| Sección | Etiqueta | Ruta | Ruta declarada |
|---|---|---|---|
| Principal | Inicio | `/` | **NO** |
| Principal | Mi licencia | `/mi-licencia` | **NO** |
| Organización | Empresas | `/organizacion/empresas` | **NO** |
| Organización | Sucursales | `/organizacion/sucursales` | **NO** |
| Organización | Establecimientos | `/organizacion/establecimientos` | **NO** |
| Organización | Almacenes | `/organizacion/almacenes` | **NO** |
| Organización | Ubicaciones | `/organizacion/ubicaciones` | **NO** |
| Maestros | Terceros | `/maestros/terceros` | **NO** |
| Maestros | Productos | `/maestros/productos` | **NO** |
| Maestros | Servicios | `/maestros/servicios` | **NO** |
| Maestros | Catálogo | `/maestros/catalogos` | **NO** |
| Maestros | Perfiles fiscales | `/maestros/perfiles` | **NO** |
| Inventario | Existencias | `/inventario/existencias` | **NO** |
| Inventario | Kardex | `/inventario/kardex` | **NO** |
| Inventario | Movimientos | `/inventario/movimientos` | **NO** |
| Inventario | Transferencias | `/inventario/transferencias` | **NO** |
| Inventario | Conteos | `/inventario/conteos` | **NO** |
| Inventario | Ajustes | `/inventario/ajustes` | **NO** |
| Inventario | Lotes | `/inventario/lotes` | **NO** |
| Inventario | Valorización | `/inventario/valorizacion` | **NO** |
| Compras | Requisiciones | `/compras/requisiciones` | **NO** |
| Compras | Órdenes | `/compras/ordenes` | **NO** |
| Compras | Recepciones | `/compras/recepciones` | **NO** |
| Compras | Facturas | `/compras/facturas` | **NO** |
| Compras | Devoluciones | `/compras/devoluciones` | **NO** |
| Compras | Notas de crédito | `/compras/notas` | **NO** |
| Compras | CxP | `/compras/cuentas-por-pagar` | **NO** |
| Ventas | Cotizaciones | `/ventas/cotizaciones` | **NO** |
| Ventas | Órdenes | `/ventas/ordenes` | **NO** |
| Ventas | Picking y despacho | `/ventas/despacho` | **NO** |
| Ventas | Facturas | `/ventas/facturas` | **NO** |
| Ventas | Notas | `/ventas/notas` | **NO** |
| Ventas | Devoluciones | `/ventas/devoluciones` | **NO** |
| Ventas | CxC | `/ventas/cuentas-por-cobrar` | **NO** |
| Tesorería | Cajas y arqueo | `/tesoreria/cajas` | **NO** |
| Tesorería | Ingresos y egresos | `/tesoreria/ingresos-egresos` | **NO** |
| Tesorería | Transferencias | `/tesoreria/transferencias` | **NO** |
| Tesorería | Conciliación | `/tesoreria/conciliacion` | **NO** |
| Tesorería | IGTF | `/tesoreria/igft` | **NO** |
| Tesorería | Maestros | `/tesoreria/maestros` | **NO** |
| Fiscal | Configuración | `/fiscal/configuracion` | **NO** |
| Fiscal | Numeración | `/fiscal/numeracion` | **NO** |
| Fiscal | Emisión | `/fiscal/emision` | **NO** |
| Fiscal | Notas | `/fiscal/notas` | **NO** |
| Fiscal | Retenciones | `/fiscal/retenciones` | **NO** |
| Fiscal | Libros y períodos | `/fiscal/libros` | **NO** |
| Regulatorio | Organismos | `/regulatorio/organismos` | **NO** |
| Regulatorio | Vehículos | `/regulatorio/vehiculos` | **NO** |
| Regulatorio | Permisos y guías | `/regulatorio/permisos` | **NO** |
| Regulatorio | Evaluación | `/regulatorio/evaluacion` | **NO** |
| Regulatorio | Aprobaciones | `/regulatorio/aprobaciones` | **NO** |
| Reportes | Centro de reportes | `/reportes/centro` | **NO** |
| Reportes | Exportaciones | `/reportes/exportaciones` | **NO** |
| Reportes | Auditoría | `/reportes/auditoria` | **NO** |
| Licenciamiento | Configuración central | `/licenciamiento/configuracion` | **NO** |
| Licenciamiento | Entitlements | `/licenciamiento/entitlements` | **NO** |
| Licenciamiento | Renovación | `/licenciamiento/renovacion` | **NO** |
| Licenciamiento | Eventos | `/licenciamiento/eventos` | **NO** |
| Homologación | Actos | `/homologacion/actos` | **NO** |
| Homologación | Versiones | `/homologacion/versiones` | **NO** |
| Homologación | Timeline | `/homologacion/timeline` | **NO** |
| Seguridad | Usuarios | `/seguridad/usuarios` | **NO** |
| Seguridad | Roles | `/seguridad/roles` | **NO** |
| Seguridad | Sesiones | `/seguridad/sesiones` | **NO** |
| Sistema | Auditoría | `/auditoria` | **NO** |
| Sistema | Diagnóstico | `/diagnostico` | **NO** |

## 2. Rutas → Página

| Ruta | Componente | Import resuelve |
|---|---|---|
| `//login` | LoginPage | SÍ |
| `//setup` | SetupPage | SÍ |
| `/mi-licencia` | MiLicenciaPage | SÍ |
| `/cambiar-contrasena` | CambiarContrasenaPage | SÍ |
| `/organizacion/empresas` | EmpresasPage | SÍ |
| `/organizacion/sucursales` | SucursalesPage | SÍ |
| `/organizacion/establecimientos` | EstablecimientosPage | SÍ |
| `/organizacion/almacenes` | AlmacenesPage | SÍ |
| `/organizacion/ubicaciones` | UbicacionesPage | SÍ |
| `/seguridad/usuarios` | UsuariosPage | SÍ |
| `/seguridad/roles` | RolesPage | SÍ |
| `/seguridad/sesiones` | SesionesPage | SÍ |
| `/maestros/terceros` | TercerosPage | SÍ |
| `/maestros/perfiles` | PerfilesFiscalesPage | SÍ |
| `/maestros/productos` | ProductosPage | SÍ |
| `/maestros/productos/nuevo` | ProductoNuevoPage | SÍ |
| `/maestros/servicios` | ServiciosPage | SÍ |
| `/maestros/catalogos` | CatalogosPage | SÍ |
| `/inventario/existencias` | ExistenciasPage | SÍ |
| `/inventario/kardex` | KardexPage | SÍ |
| `/inventario/movimientos` | MovimientosPage | SÍ |
| `/inventario/transferencias` | TransferenciasPage | SÍ |
| `/inventario/conteos` | ConteosPage | SÍ |
| `/inventario/ajustes` | AjustesPage | SÍ |
| `/inventario/lotes` | LotesPage | SÍ |
| `/inventario/valorizacion` | ValorizacionPage | SÍ |
| `/compras/requisiciones` | RequisicionesPage | SÍ |
| `/compras/ordenes` | OrdenesComprasPage | SÍ |
| `/compras/recepciones` | RecepcionesPage | SÍ |
| `/compras/facturas` | FacturasProveedorPage | SÍ |
| `/compras/devoluciones` | DevolucionesComprasPage | SÍ |
| `/compras/notas` | NotasComprasPage | SÍ |
| `/compras/cuentas-por-pagar` | CuentasPorPagarPage | SÍ |
| `/ventas/cotizaciones` | CotizacionesPage | SÍ |
| `/ventas/ordenes` | OrdenesVentasPage | SÍ |
| `/ventas/facturas` | FacturasVentasPage | SÍ |
| `/ventas/notas` | NotasVentasPage | SÍ |
| `/ventas/devoluciones` | DevolucionesVentasPage | SÍ |
| `/ventas/despacho` | DespachoPage | SÍ |
| `/ventas/cuentas-por-cobrar` | CuentasPorCobrarPage | SÍ |
| `/tesoreria/cajas` | CajasPage | SÍ |
| `/tesoreria/ingresos-egresos` | IngresosEgresosPage | SÍ |
| `/tesoreria/transferencias` | TesoreriaTransferenciasPage | SÍ |
| `/tesoreria/conciliacion` | ConciliacionPage | SÍ |
| `/tesoreria/igft` | IgftPage | SÍ |
| `/tesoreria/maestros` | MaestrosPage | SÍ |
| `/fiscal/configuracion` | ConfiguracionPage | SÍ |
| `/fiscal/numeracion` | NumeracionPage | SÍ |
| `/fiscal/emision` | EmisionPage | SÍ |
| `/fiscal/notas` | NotasPage | SÍ |
| `/fiscal/retenciones` | RetencionesPage | SÍ |
| `/fiscal/libros` | LibrosPage | SÍ |
| `/regulatorio/organismos` | OrganismosPage | SÍ |
| `/regulatorio/vehiculos` | VehiculosPage | SÍ |
| `/regulatorio/permisos` | PermisosPage | SÍ |
| `/regulatorio/evaluacion` | EvaluacionPage | SÍ |
| `/regulatorio/aprobaciones` | AprobacionesPage | SÍ |
| `/reportes/centro` | CentroReportesPage | SÍ |
| `/reportes/exportaciones` | ExportacionesPage | SÍ |
| `/reportes/auditoria` | ReportesAuditoriaPage | SÍ |
| `/licenciamiento/configuracion` | ConfiguracionCentralPage | SÍ |
| `/licenciamiento/entitlements` | EntitlementsPage | SÍ |
| `/licenciamiento/renovacion` | RenovacionPage | SÍ |
| `/licenciamiento/eventos` | EventosPage | SÍ |
| `/homologacion/actos` | ActosPage | SÍ |
| `/homologacion/versiones` | VersionesPage | SÍ |
| `/homologacion/timeline` | TimelinePage | SÍ |
| `/auditoria` | AuditoriaPage | SÍ |
| `/diagnostico` | DiagnosticoPage | SÍ |
| `/forbidden` | ForbiddenState | SÍ |
| `/*` | NotFoundState | SÍ |
| `/` | DashboardPage | SÍ |

## 3. Páginas → llamadas API (primer literal por página)

| Página | Llamadas (muestra) |
|---|---|
| `app/contexts/AuthContext.tsx` | `/auth/login`, `/auth/logout`, `/auth/me`, `/auth/refresh` |
| `app/contexts/LicenseContext.tsx` | `/license/status` |
| `modules/compras/cuentas-por-pagar/CuentasPorPagarPage.tsx` | `/purchasing/advances`, `/purchasing/aging`, `/purchasing/applications`, `/purchasing/open-items` |
| `modules/compras/devoluciones/DevolucionesComprasPage.tsx` | `/purchasing/returns`, `/purchasing/returns/*/lines (template)` |
| `modules/compras/facturas/FacturasProveedorPage.tsx` | `/purchasing/supplier-invoices`, `/purchasing/supplier-invoices/*/lines (template)`, `/purchasing/supplier-invoices/*/transition (template)` |
| `modules/compras/notas/NotasComprasPage.tsx` | `/purchasing/credit-notes`, `/purchasing/credit-notes/*/post (template)` |
| `modules/compras/ordenes/OrdenesComprasPage.tsx` | `/purchasing/orders`, `/purchasing/orders/*/lines (template)`, `/purchasing/orders/*/transition (template)` |
| `modules/compras/recepciones/RecepcionesPage.tsx` | `/purchasing/receipts`, `/purchasing/receipts/*/* (template)` |
| `modules/compras/requisiciones/RequisicionesPage.tsx` | `/purchasing/requisitions/*/transition (template)` |
| `modules/fiscal/configuracion/ConfiguracionPage.tsx` | `/fiscal/legal-sources`, `/fiscal/legal-sources/*/activate (template)`, `/fiscal/tax-calculations`, `/fiscal/tax-rule-versions` |
| `modules/fiscal/emision/EmisionPage.tsx` | `/fiscal/control-batches`, `/fiscal/documents`, `/fiscal/documents/*/print (template)`, `/fiscal/documents/emit` |
| `modules/fiscal/libros/LibrosPage.tsx` | `/fiscal/books/* (template)`, `/fiscal/periods`, `/fiscal/periods/*/transition (template)` |
| `modules/fiscal/notas/NotasPage.tsx` | `/fiscal/credit-debit-notes`, `/sales/invoices` |
| `modules/fiscal/numeracion/NumeracionPage.tsx` | `/fiscal/control-batches`, `/fiscal/control-numbers`, `/fiscal/number-series` |
| `modules/fiscal/retenciones/RetencionesPage.tsx` | `/fiscal/withholding-rules`, `/fiscal/withholdings`, `/fiscal/withholdings/*/certificate (template)`, `/fiscal/withholdings/*/transition (template)` |
| `modules/homologacion/actos/ActosPage.tsx` | `/homologation/records`, `/homologation/records/*/evaluate (template)`, `/homologation/records/*/submit (template)` |
| `modules/homologacion/timeline/TimelinePage.tsx` | `/homologation/timeline` |
| `modules/homologacion/versiones/VersionesPage.tsx` | `/homologation/records`, `/homologation/releases`, `/homologation/releases/*/promote (template)`, `/homologation/releases/*/release (template)` |
| `modules/inventario/ajustes/AjustesPage.tsx` | `/inventory/adjustments`, `/inventory/adjustments/*/transition (template)`, `/organization/warehouses (template)` |
| `modules/inventario/conteos/ConteosPage.tsx` | `/inventory/counts`, `/inventory/counts/*/lines (template)`, `/inventory/counts/*/transition (template)`, `/organization/warehouses (template)` |
| `modules/inventario/lotes/LotesPage.tsx` | `/inventory/lots`, `/inventory/lots/*/transition (template)` |
| `modules/inventario/movimientos/MovimientosPage.tsx` | `/inventory/movements`, `/inventory/movements/reverse`, `/organization/warehouses (template)` |
| `modules/inventario/transferencias/TransferenciasPage.tsx` | `/inventory/transfers`, `/inventory/transfers/*/transition (template)`, `/organization/warehouses (template)` |
| `modules/inventario/valorizacion/ValorizacionPage.tsx` | `/inventory/cost-layers`, `/inventory/costing-profiles`, `/inventory/valuation` |
| `modules/licenciamiento/configuracion/ConfiguracionCentralPage.tsx` | `/licensing/central-config`, `/licensing/overview`, `/licensing/sync` |
| `modules/licenciamiento/entitlements/EntitlementsPage.tsx` | `/licensing/entitlement-snapshots`, `/licensing/entitlements` |
| `modules/licenciamiento/eventos/EventosPage.tsx` | `/license/history` |
| `modules/licenciamiento/renovacion/RenovacionPage.tsx` | `/licensing/renewal-requests`, `/licensing/renewal-requests/*/transition (template)` |
| `modules/maestros/catalogos/CatalogosPage.tsx` | `/maestros/catalogos/taxonomia`, `/maestros/catalogos/unidades` |
| `modules/maestros/perfiles/PerfilesFiscalesPage.tsx` | `/maestros/perfiles` |
| `modules/maestros/productos/ProductoNuevoPage.tsx` | `/maestros/catalogos/items` |
| `modules/organizacion/almacenes/AlmacenesPage.tsx` | `/organization/branches (template)`, `/organization/warehouses`, `/organization/warehouses (template)` |
| `modules/organizacion/establecimientos/EstablecimientosPage.tsx` | `/organization/branches (template)`, `/organization/establishments`, `/organization/establishments (template)` |
| `modules/organizacion/sucursales/SucursalesPage.tsx` | `/organization/branches`, `/organization/branches (template)` |
| `modules/organizacion/ubicaciones/UbicacionesPage.tsx` | `/organization/locations`, `/organization/locations (template)`, `/organization/warehouses (template)` |
| `modules/regulatorio/aprobaciones/AprobacionesPage.tsx` | `/regulatory/approval-requests`, `/regulatory/approval-requests/*/transition (template)` |
| `modules/regulatorio/evaluacion/EvaluacionPage.tsx` | `/regulatory/contingencies`, `/regulatory/contingencies/*/end (template)`, `/regulatory/evaluations`, `/regulatory/evaluations/*/override (template)` |
| `modules/regulatorio/organismos/OrganismosPage.tsx` | `/regulatory/authorities`, `/regulatory/official-registrations`, `/regulatory/permit-types`, `/regulatory/profiles` |
| `modules/regulatorio/permisos/PermisosPage.tsx` | `/regulatory/official-documents`, `/regulatory/permit-types`, `/regulatory/permits`, `/regulatory/permits/*/transition (template)` |
| `modules/regulatorio/vehiculos/VehiculosPage.tsx` | `/maestros/terceros`, `/regulatory/drivers`, `/regulatory/vehicles` |
| `modules/reportes/auditoria/ReportesAuditoriaPage.tsx` | `/reporting/audit/timeline${qs  (template)` |
| `modules/reportes/centro/CentroReportesPage.tsx` | `/reporting/exports`, `/reporting/reports/* (template)` |
| `modules/reportes/exportaciones/ExportacionesPage.tsx` | `/reporting/exports`, `/reporting/jobs`, `/reporting/jobs/*/run (template)` |
| `modules/seguridad/roles/RolesPage.tsx` | `/roles`, `/users`, `/users/*/roles (template)`, `/users/*/roles/* (template)` |
| `modules/seguridad/sesiones/SesionesPage.tsx` | `/auth/sessions`, `/auth/sessions/* (template)` |
| `modules/seguridad/usuarios/UsuariosPage.tsx` | `/users` |
| `modules/tesoreria/cajas/CajasPage.tsx` | `/treasury/cash-sessions`, `/treasury/cash-sessions/*/* (template)`, `/treasury/cash-sessions/*/arqueo (template)`, `/treasury/cash-sessions/*/close (template)` |
| `modules/tesoreria/conciliacion/ConciliacionPage.tsx` | `/treasury/accounts`, `/treasury/bank-transactions`, `/treasury/reconciliation-lines/*/resolve (template)`, `/treasury/reconciliations` |
| `modules/tesoreria/igft/IgftPage.tsx` | `/treasury/fiscal-rules`, `/treasury/igft-events`, `/treasury/igft-events/evaluate` |
| `modules/tesoreria/ingresos-egresos/IngresosEgresosPage.tsx` | `/purchasing/payments`, `/sales/collections`, `/treasury/accounts`, `/treasury/bank-transactions` |
| `modules/tesoreria/maestros/MaestrosPage.tsx` | `/treasury/accounts`, `/treasury/banks`, `/treasury/cashboxes`, `/treasury/currencies` |
| `modules/tesoreria/transferencias/TransferenciasPage.tsx` | `/treasury/accounts`, `/treasury/cashboxes`, `/treasury/transfers` |
| `modules/ventas/cotizaciones/CotizacionesPage.tsx` | `/sales/quotes`, `/sales/quotes/*/lines (template)` |
| `modules/ventas/cuentas-por-cobrar/CuentasPorCobrarPage.tsx` | `/sales/aging`, `/sales/applications`, `/sales/collections`, `/sales/collections/*/transition (template)` |
| `modules/ventas/despacho/DespachoPage.tsx` | `/organization/warehouses (template)`, `/sales/orders`, `/sales/pick-lists`, `/sales/shipments` |
| `modules/ventas/devoluciones/DevolucionesVentasPage.tsx` | `/sales/returns`, `/sales/returns/*/lines (template)` |
| `modules/ventas/facturas/FacturasVentasPage.tsx` | `/sales/invoices`, `/sales/invoices/*/lines (template)`, `/sales/invoices/*/transition (template)` |
| `modules/ventas/notas/NotasVentasPage.tsx` | `/sales/credit-notes`, `/sales/credit-notes/*/apply (template)`, `/sales/credit-notes/*/post (template)`, `/sales/debit-notes` |
| `modules/ventas/ordenes/OrdenesVentasPage.tsx` | `/sales/orders`, `/sales/orders/*/lines (template)`, `/sales/orders/*/transition (template)` |
| `pages/AuditoriaPage.tsx` | `/audit/events (template)` |
| `pages/CambiarContrasenaPage.tsx` | `/auth/change-password` |
| `pages/DashboardPage.tsx` | `/health/ready`, `/reporting/dashboard` |
| `pages/DiagnosticoPage.tsx` | `/system/diagnostics` |
| `pages/EmpresasPage.tsx` | `/organization/companies (template)` |
| `pages/LoginPage.tsx` | `/setup/status` |
| `pages/MiLicenciaPage.tsx` | `/license/renewal-request`, `/license/status` |
| `pages/SetupPage.tsx` | `/setup/initialize` |
