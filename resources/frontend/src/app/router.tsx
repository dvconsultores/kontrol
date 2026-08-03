/** Definición de rutas con guards (FR-001-042/061, DOC-08 §5). */
import { createBrowserRouter } from "react-router-dom";

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
          { path: "auditoria", element: <AuditoriaPage /> },
          { path: "diagnostico", element: <DiagnosticoPage /> },
          { path: "forbidden", element: <ForbiddenState /> },
          { path: "*", element: <NotFoundState /> },
        ],
      },
    ],
  },
]);
