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
          { path: "auditoria", element: <AuditoriaPage /> },
          { path: "diagnostico", element: <DiagnosticoPage /> },
          { path: "forbidden", element: <ForbiddenState /> },
          { path: "*", element: <NotFoundState /> },
        ],
      },
    ],
  },
]);
