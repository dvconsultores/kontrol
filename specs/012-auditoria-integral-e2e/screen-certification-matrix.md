# Matriz de Certificación por Pantalla — Spec 012 (pasada 2)

Fuente: evidencia regenerada + E2E ejecutado. Estado estructural por pantalla:
COMPLETE_100 = menú+ruta+página+API+backend; PARTIAL = falta capa o prueba; BROKEN = ruta sin página.
Browser: C = crawler chromium PASS (pasada 2); Responsive/axe/otros = pendiente (checklists).

| Pantalla | Ruta | Menú | Sección | API resuelve | Backend | Permiso | Browser | Estado |
|---|---|---|---|---|---|---|---|---|
| LoginPage | `//login` | — | — | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| SetupPage | `//setup` | — | — | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| MiLicenciaPage | `/mi-licencia` | Mi licencia | Principal | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| CambiarContrasenaPage | `/cambiar-contrasena` | — | — | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| EmpresasPage | `/organizacion/empresas` | Empresas | Organización | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| SucursalesPage | `/organizacion/sucursales` | Sucursales | Organización | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| EstablecimientosPage | `/organizacion/establecimientos` | Establecimientos | Organización | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| AlmacenesPage | `/organizacion/almacenes` | Almacenes | Organización | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| UbicacionesPage | `/organizacion/ubicaciones` | Ubicaciones | Organización | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| UsuariosPage | `/seguridad/usuarios` | Usuarios | Seguridad | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| RolesPage | `/seguridad/roles` | Roles | Seguridad | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| SesionesPage | `/seguridad/sesiones` | Sesiones | Seguridad | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| TercerosPage | `/maestros/terceros` | Terceros | Maestros | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| PerfilesFiscalesPage | `/maestros/perfiles` | Perfiles fiscales | Maestros | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| ProductosPage | `/maestros/productos` | Productos | Maestros | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| ProductoNuevoPage | `/maestros/productos/nuevo` | — | — | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| ServiciosPage | `/maestros/servicios` | Servicios | Maestros | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| CatalogosPage | `/maestros/catalogos` | Catálogo | Maestros | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| ExistenciasPage | `/inventario/existencias` | Existencias | Inventario | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| KardexPage | `/inventario/kardex` | Kardex | Inventario | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| MovimientosPage | `/inventario/movimientos` | Movimientos | Inventario | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| TransferenciasPage | `/inventario/transferencias` | Transferencias | Inventario | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| ConteosPage | `/inventario/conteos` | Conteos | Inventario | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| AjustesPage | `/inventario/ajustes` | Ajustes | Inventario | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| LotesPage | `/inventario/lotes` | Lotes | Inventario | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| ValorizacionPage | `/inventario/valorizacion` | Valorización | Inventario | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| RequisicionesPage | `/compras/requisiciones` | Requisiciones | Compras | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| OrdenesComprasPage | `/compras/ordenes` | Órdenes | Compras | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| RecepcionesPage | `/compras/recepciones` | Recepciones | Compras | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| FacturasProveedorPage | `/compras/facturas` | Facturas | Compras | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| DevolucionesComprasPage | `/compras/devoluciones` | Devoluciones | Compras | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| NotasComprasPage | `/compras/notas` | Notas de crédito | Compras | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| CuentasPorPagarPage | `/compras/cuentas-por-pagar` | CxP | Compras | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| CotizacionesPage | `/ventas/cotizaciones` | Cotizaciones | Ventas | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| OrdenesVentasPage | `/ventas/ordenes` | Órdenes | Ventas | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| FacturasVentasPage | `/ventas/facturas` | Facturas | Ventas | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| NotasVentasPage | `/ventas/notas` | Notas | Ventas | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| DevolucionesVentasPage | `/ventas/devoluciones` | Devoluciones | Ventas | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| DespachoPage | `/ventas/despacho` | Picking y despacho | Ventas | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| CuentasPorCobrarPage | `/ventas/cuentas-por-cobrar` | CxC | Ventas | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| CajasPage | `/tesoreria/cajas` | Cajas y arqueo | Tesorería | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| IngresosEgresosPage | `/tesoreria/ingresos-egresos` | Ingresos y egresos | Tesorería | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| TesoreriaTransferenciasPage | `/tesoreria/transferencias` | Transferencias | Tesorería | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| ConciliacionPage | `/tesoreria/conciliacion` | Conciliación | Tesorería | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| IgftPage | `/tesoreria/igft` | IGTF | Tesorería | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| MaestrosPage | `/tesoreria/maestros` | Maestros | Tesorería | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| ConfiguracionPage | `/fiscal/configuracion` | Configuración | Fiscal | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| NumeracionPage | `/fiscal/numeracion` | Numeración | Fiscal | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| EmisionPage | `/fiscal/emision` | Emisión | Fiscal | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| NotasPage | `/fiscal/notas` | Notas | Fiscal | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| RetencionesPage | `/fiscal/retenciones` | Retenciones | Fiscal | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| LibrosPage | `/fiscal/libros` | Libros y períodos | Fiscal | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| OrganismosPage | `/regulatorio/organismos` | Organismos | Regulatorio | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| VehiculosPage | `/regulatorio/vehiculos` | Vehículos | Regulatorio | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| PermisosPage | `/regulatorio/permisos` | Permisos y guías | Regulatorio | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| EvaluacionPage | `/regulatorio/evaluacion` | Evaluación | Regulatorio | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| AprobacionesPage | `/regulatorio/aprobaciones` | Aprobaciones | Regulatorio | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| CentroReportesPage | `/reportes/centro` | Centro de reportes | Reportes | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| ExportacionesPage | `/reportes/exportaciones` | Exportaciones | Reportes | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| ReportesAuditoriaPage | `/reportes/auditoria` | Auditoría | Reportes | NO | SÍ | require_permission | C* | PARTIAL |
| ConfiguracionCentralPage | `/licenciamiento/configuracion` | Configuración central | Licenciamiento | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| EntitlementsPage | `/licenciamiento/entitlements` | Entitlements | Licenciamiento | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| RenovacionPage | `/licenciamiento/renovacion` | Renovación | Licenciamiento | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| EventosPage | `/licenciamiento/eventos` | Eventos | Licenciamiento | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| ActosPage | `/homologacion/actos` | Actos | Homologación | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| VersionesPage | `/homologacion/versiones` | Versiones | Homologación | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| TimelinePage | `/homologacion/timeline` | Timeline | Homologación | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| AuditoriaPage | `/auditoria` | Auditoría | Sistema | NO | SÍ | require_permission | C* | PARTIAL |
| DiagnosticoPage | `/diagnostico` | Diagnóstico | Sistema | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| ForbiddenState | `/forbidden` | — | — | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| NotFoundState | `/*` | — | — | SÍ | SÍ | require_permission | C* | COMPLETE_100 |
| DashboardPage | `/` | Inicio | Principal | NO | SÍ | require_permission | C* | PARTIAL |

* C = crawler chromium recorrió la ruta sin 404 y con H1 (pasada 2). Responsive/axe/firefox/webkit: pendientes de ambiente autorizado.
