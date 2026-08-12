# Matriz Maestra de Integración — Spec 012 (pasada 2)

Estado por página según: Menú → Ruta → Página → API → Backend → Evidencia.
Estados: COMPLETE_100 / PARTIAL / BROKEN / NOT_IMPLEMENTED / NOT_TESTED / FUTURE_SCOPE.

| Ruta | Menú | Sección | Página | API resuelve | Estado (estático) |
|---|---|---|---|---|---|
| `//login` | — | — | LoginPage | SÍ | COMPLETE_100 |
| `//setup` | — | — | SetupPage | SÍ | COMPLETE_100 |
| `/mi-licencia` | Mi licencia | Principal | MiLicenciaPage | SÍ | COMPLETE_100 |
| `/cambiar-contrasena` | — | — | CambiarContrasenaPage | SÍ | COMPLETE_100 |
| `/organizacion/empresas` | Empresas | Organización | EmpresasPage | SÍ | COMPLETE_100 |
| `/organizacion/sucursales` | Sucursales | Organización | SucursalesPage | SÍ | COMPLETE_100 |
| `/organizacion/establecimientos` | Establecimientos | Organización | EstablecimientosPage | SÍ | COMPLETE_100 |
| `/organizacion/almacenes` | Almacenes | Organización | AlmacenesPage | SÍ | COMPLETE_100 |
| `/organizacion/ubicaciones` | Ubicaciones | Organización | UbicacionesPage | SÍ | COMPLETE_100 |
| `/seguridad/usuarios` | Usuarios | Seguridad | UsuariosPage | SÍ | COMPLETE_100 |
| `/seguridad/roles` | Roles | Seguridad | RolesPage | SÍ | COMPLETE_100 |
| `/seguridad/sesiones` | Sesiones | Seguridad | SesionesPage | SÍ | COMPLETE_100 |
| `/maestros/terceros` | Terceros | Maestros | TercerosPage | SÍ | COMPLETE_100 |
| `/maestros/perfiles` | Perfiles fiscales | Maestros | PerfilesFiscalesPage | SÍ | COMPLETE_100 |
| `/maestros/productos` | Productos | Maestros | ProductosPage | SÍ | COMPLETE_100 |
| `/maestros/productos/nuevo` | — | — | ProductoNuevoPage | SÍ | COMPLETE_100 |
| `/maestros/servicios` | Servicios | Maestros | ServiciosPage | SÍ | COMPLETE_100 |
| `/maestros/catalogos` | Catálogo | Maestros | CatalogosPage | SÍ | COMPLETE_100 |
| `/inventario/existencias` | Existencias | Inventario | ExistenciasPage | SÍ | COMPLETE_100 |
| `/inventario/kardex` | Kardex | Inventario | KardexPage | SÍ | COMPLETE_100 |
| `/inventario/movimientos` | Movimientos | Inventario | MovimientosPage | SÍ | COMPLETE_100 |
| `/inventario/transferencias` | Transferencias | Inventario | TransferenciasPage | SÍ | COMPLETE_100 |
| `/inventario/conteos` | Conteos | Inventario | ConteosPage | SÍ | COMPLETE_100 |
| `/inventario/ajustes` | Ajustes | Inventario | AjustesPage | SÍ | COMPLETE_100 |
| `/inventario/lotes` | Lotes | Inventario | LotesPage | SÍ | COMPLETE_100 |
| `/inventario/valorizacion` | Valorización | Inventario | ValorizacionPage | SÍ | COMPLETE_100 |
| `/compras/requisiciones` | Requisiciones | Compras | RequisicionesPage | SÍ | COMPLETE_100 |
| `/compras/ordenes` | Órdenes | Compras | OrdenesComprasPage | SÍ | COMPLETE_100 |
| `/compras/recepciones` | Recepciones | Compras | RecepcionesPage | SÍ | COMPLETE_100 |
| `/compras/facturas` | Facturas | Compras | FacturasProveedorPage | SÍ | COMPLETE_100 |
| `/compras/devoluciones` | Devoluciones | Compras | DevolucionesComprasPage | SÍ | COMPLETE_100 |
| `/compras/notas` | Notas de crédito | Compras | NotasComprasPage | SÍ | COMPLETE_100 |
| `/compras/cuentas-por-pagar` | CxP | Compras | CuentasPorPagarPage | SÍ | COMPLETE_100 |
| `/ventas/cotizaciones` | Cotizaciones | Ventas | CotizacionesPage | SÍ | COMPLETE_100 |
| `/ventas/ordenes` | Órdenes | Ventas | OrdenesVentasPage | SÍ | COMPLETE_100 |
| `/ventas/facturas` | Facturas | Ventas | FacturasVentasPage | SÍ | COMPLETE_100 |
| `/ventas/notas` | Notas | Ventas | NotasVentasPage | SÍ | COMPLETE_100 |
| `/ventas/devoluciones` | Devoluciones | Ventas | DevolucionesVentasPage | SÍ | COMPLETE_100 |
| `/ventas/despacho` | Picking y despacho | Ventas | DespachoPage | SÍ | COMPLETE_100 |
| `/ventas/cuentas-por-cobrar` | CxC | Ventas | CuentasPorCobrarPage | SÍ | COMPLETE_100 |
| `/tesoreria/cajas` | Cajas y arqueo | Tesorería | CajasPage | SÍ | COMPLETE_100 |
| `/tesoreria/ingresos-egresos` | Ingresos y egresos | Tesorería | IngresosEgresosPage | SÍ | COMPLETE_100 |
| `/tesoreria/transferencias` | Transferencias | Tesorería | TesoreriaTransferenciasPage | SÍ | COMPLETE_100 |
| `/tesoreria/conciliacion` | Conciliación | Tesorería | ConciliacionPage | SÍ | COMPLETE_100 |
| `/tesoreria/igft` | IGTF | Tesorería | IgftPage | SÍ | COMPLETE_100 |
| `/tesoreria/maestros` | Maestros | Tesorería | MaestrosPage | SÍ | COMPLETE_100 |
| `/fiscal/configuracion` | Configuración | Fiscal | ConfiguracionPage | SÍ | COMPLETE_100 |
| `/fiscal/numeracion` | Numeración | Fiscal | NumeracionPage | SÍ | COMPLETE_100 |
| `/fiscal/emision` | Emisión | Fiscal | EmisionPage | SÍ | COMPLETE_100 |
| `/fiscal/notas` | Notas | Fiscal | NotasPage | SÍ | COMPLETE_100 |
| `/fiscal/retenciones` | Retenciones | Fiscal | RetencionesPage | SÍ | COMPLETE_100 |
| `/fiscal/libros` | Libros y períodos | Fiscal | LibrosPage | SÍ | COMPLETE_100 |
| `/regulatorio/organismos` | Organismos | Regulatorio | OrganismosPage | SÍ | COMPLETE_100 |
| `/regulatorio/vehiculos` | Vehículos | Regulatorio | VehiculosPage | SÍ | COMPLETE_100 |
| `/regulatorio/permisos` | Permisos y guías | Regulatorio | PermisosPage | SÍ | COMPLETE_100 |
| `/regulatorio/evaluacion` | Evaluación | Regulatorio | EvaluacionPage | SÍ | COMPLETE_100 |
| `/regulatorio/aprobaciones` | Aprobaciones | Regulatorio | AprobacionesPage | SÍ | COMPLETE_100 |
| `/reportes/centro` | Centro de reportes | Reportes | CentroReportesPage | SÍ | COMPLETE_100 |
| `/reportes/exportaciones` | Exportaciones | Reportes | ExportacionesPage | SÍ | COMPLETE_100 |
| `/reportes/auditoria` | Auditoría | Reportes | ReportesAuditoriaPage | SÍ | COMPLETE_100 |
| `/licenciamiento/configuracion` | Configuración central | Licenciamiento | ConfiguracionCentralPage | SÍ | COMPLETE_100 |
| `/licenciamiento/entitlements` | Entitlements | Licenciamiento | EntitlementsPage | SÍ | COMPLETE_100 |
| `/licenciamiento/renovacion` | Renovación | Licenciamiento | RenovacionPage | SÍ | COMPLETE_100 |
| `/licenciamiento/eventos` | Eventos | Licenciamiento | EventosPage | SÍ | COMPLETE_100 |
| `/homologacion/actos` | Actos | Homologación | ActosPage | SÍ | COMPLETE_100 |
| `/homologacion/versiones` | Versiones | Homologación | VersionesPage | SÍ | COMPLETE_100 |
| `/homologacion/timeline` | Timeline | Homologación | TimelinePage | SÍ | COMPLETE_100 |
| `/auditoria` | Auditoría | Sistema | AuditoriaPage | SÍ | COMPLETE_100 |
| `/diagnostico` | Diagnóstico | Sistema | DiagnosticoPage | SÍ | COMPLETE_100 |
| `/forbidden` | — | — | ForbiddenState | SÍ | COMPLETE_100 |
| `/*` | — | — | NotFoundState | SÍ | COMPLETE_100 |
| `/` | Inicio | Principal | DashboardPage | NO | PARTIAL |
