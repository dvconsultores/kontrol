/** Definición de rutas con guards (FR-001-042/061, DOC-08 §5). */
import { createBrowserRouter } from "react-router";

import { AppShell } from "./AppShell";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { ForbiddenState } from "@/components/ForbiddenState";
import { NotFoundState } from "@/components/NotFoundState";
import { RouteGuard } from "@/components/RouteGuard";
import { AuditoriaPage } from "@/pages/AuditoriaPage";
import { CambiarContrasenaPage } from "@/pages/CambiarContrasenaPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { DiagnosticoPage } from "@/pages/DiagnosticoPage";
import { EmpresasPage } from "@/pages/EmpresasPage";
import { LoginPage } from "@/pages/LoginPage";
import { MiLicenciaPage } from "@/pages/MiLicenciaPage";
import { SetupPage } from "@/pages/SetupPage";
import { CatalogosPage } from "@/modules/maestros/catalogos/CatalogosPage";
import { ProductosPage } from "@/modules/maestros/productos/ProductosPage";
import { ProductoNuevoPage } from "@/modules/maestros/productos/ProductoNuevoPage";
import { ServiciosPage } from "@/modules/maestros/servicios/ServiciosPage";
import { TercerosPage } from "@/modules/maestros/terceros/TercerosPage";
import { AjustesPage } from "@/modules/inventario/ajustes/AjustesPage";
import { ConteosPage } from "@/modules/inventario/conteos/ConteosPage";
import { ExistenciasPage } from "@/modules/inventario/existencias/ExistenciasPage";
import { KardexPage } from "@/modules/inventario/kardex/KardexPage";
import { TransferenciasPage } from "@/modules/inventario/transferencias/TransferenciasPage";
import { CuentasPorPagarPage } from "@/modules/compras/cuentas-por-pagar/CuentasPorPagarPage";
import { FacturasProveedorPage } from "@/modules/compras/facturas/FacturasProveedorPage";
import { OrdenesComprasPage } from "@/modules/compras/ordenes/OrdenesComprasPage";
import { RecepcionesPage } from "@/modules/compras/recepciones/RecepcionesPage";
import { RequisicionesPage } from "@/modules/compras/requisiciones/RequisicionesPage";
import { CotizacionesPage } from "@/modules/ventas/cotizaciones/CotizacionesPage";
import { CuentasPorCobrarPage } from "@/modules/ventas/cuentas-por-cobrar/CuentasPorCobrarPage";
import { FacturasVentasPage } from "@/modules/ventas/facturas/FacturasVentasPage";
import { OrdenesVentasPage } from "@/modules/ventas/ordenes/OrdenesVentasPage";
import { CajasPage } from "@/modules/tesoreria/cajas/CajasPage";
import { ConciliacionPage } from "@/modules/tesoreria/conciliacion/ConciliacionPage";
import { IgftPage } from "@/modules/tesoreria/igft/IgftPage";
import { IngresosEgresosPage } from "@/modules/tesoreria/ingresos-egresos/IngresosEgresosPage";
import { MaestrosPage } from "@/modules/tesoreria/maestros/MaestrosPage";
import { TransferenciasPage as TesoreriaTransferenciasPage } from "@/modules/tesoreria/transferencias/TransferenciasPage";
import { ConfiguracionPage } from "@/modules/fiscal/configuracion/ConfiguracionPage";
import { EmisionPage } from "@/modules/fiscal/emision/EmisionPage";
import { LibrosPage } from "@/modules/fiscal/libros/LibrosPage";
import { NotasPage } from "@/modules/fiscal/notas/NotasPage";
import { NumeracionPage } from "@/modules/fiscal/numeracion/NumeracionPage";
import { RetencionesPage } from "@/modules/fiscal/retenciones/RetencionesPage";
import { EvaluacionPage } from "@/modules/regulatorio/evaluacion/EvaluacionPage";
import { OrganismosPage } from "@/modules/regulatorio/organismos/OrganismosPage";
import { PermisosPage } from "@/modules/regulatorio/permisos/PermisosPage";
import { VehiculosPage } from "@/modules/regulatorio/vehiculos/VehiculosPage";
import { ReportesAuditoriaPage } from "@/modules/reportes/auditoria/ReportesAuditoriaPage";
import { CentroReportesPage } from "@/modules/reportes/centro/CentroReportesPage";
import { ExportacionesPage } from "@/modules/reportes/exportaciones/ExportacionesPage";

export const router = createBrowserRouter([
  {
    path: "/login",
    element: <LoginPage />,
    errorElement: <ErrorBoundary />,
  },
  {
    path: "/setup",
    element: <SetupPage />,
    errorElement: <ErrorBoundary />,
  },
  {
    element: <RouteGuard />,
    errorElement: <ErrorBoundary />,
    children: [
      {
        element: <AppShell />,
        children: [
          { index: true, element: <DashboardPage /> },
          { path: "mi-licencia", element: <MiLicenciaPage /> },
          { path: "cambiar-contrasena", element: <CambiarContrasenaPage /> },
          { path: "organizacion/empresas", element: <EmpresasPage /> },
          { path: "maestros/terceros", element: <TercerosPage /> },
          { path: "maestros/productos", element: <ProductosPage /> },
          { path: "maestros/productos/nuevo", element: <ProductoNuevoPage /> },
          { path: "maestros/servicios", element: <ServiciosPage /> },
          { path: "maestros/catalogos", element: <CatalogosPage /> },
          { path: "inventario/existencias", element: <ExistenciasPage /> },
          { path: "inventario/kardex", element: <KardexPage /> },
          { path: "inventario/transferencias", element: <TransferenciasPage /> },
          { path: "inventario/conteos", element: <ConteosPage /> },
          { path: "inventario/ajustes", element: <AjustesPage /> },
          { path: "compras/requisiciones", element: <RequisicionesPage /> },
          { path: "compras/ordenes", element: <OrdenesComprasPage /> },
          { path: "compras/recepciones", element: <RecepcionesPage /> },
          { path: "compras/facturas", element: <FacturasProveedorPage /> },
          { path: "compras/cuentas-por-pagar", element: <CuentasPorPagarPage /> },
          { path: "ventas/cotizaciones", element: <CotizacionesPage /> },
          { path: "ventas/ordenes", element: <OrdenesVentasPage /> },
          { path: "ventas/facturas", element: <FacturasVentasPage /> },
          { path: "ventas/cuentas-por-cobrar", element: <CuentasPorCobrarPage /> },
          { path: "tesoreria/cajas", element: <CajasPage /> },
          { path: "tesoreria/ingresos-egresos", element: <IngresosEgresosPage /> },
          { path: "tesoreria/transferencias", element: <TesoreriaTransferenciasPage /> },
          { path: "tesoreria/conciliacion", element: <ConciliacionPage /> },
          { path: "tesoreria/igft", element: <IgftPage /> },
          { path: "tesoreria/maestros", element: <MaestrosPage /> },
          { path: "fiscal/configuracion", element: <ConfiguracionPage /> },
          { path: "fiscal/numeracion", element: <NumeracionPage /> },
          { path: "fiscal/emision", element: <EmisionPage /> },
          { path: "fiscal/notas", element: <NotasPage /> },
          { path: "fiscal/retenciones", element: <RetencionesPage /> },
          { path: "fiscal/libros", element: <LibrosPage /> },
          { path: "regulatorio/organismos", element: <OrganismosPage /> },
          { path: "regulatorio/vehiculos", element: <VehiculosPage /> },
          { path: "regulatorio/permisos", element: <PermisosPage /> },
          { path: "regulatorio/evaluacion", element: <EvaluacionPage /> },
          { path: "reportes/centro", element: <CentroReportesPage /> },
          { path: "reportes/exportaciones", element: <ExportacionesPage /> },
          { path: "reportes/auditoria", element: <ReportesAuditoriaPage /> },
          { path: "auditoria", element: <AuditoriaPage /> },
          { path: "diagnostico", element: <DiagnosticoPage /> },
          { path: "forbidden", element: <ForbiddenState /> },
          { path: "*", element: <NotFoundState /> },
        ],
      },
    ],
  },
]);
