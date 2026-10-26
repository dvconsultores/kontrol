/**
 * Punto de entrada de KONTROL frontend.
 * Providers: QueryClient, Auth, License, Company, Notification, Router.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router";

import { getActiveCompanyId } from "./api/client";
import { debeReintentar } from "./app/company/errores";
import { crearHashDeClave } from "./app/company/queryScope";
import { AuthProvider } from "./app/contexts/AuthContext";
import { CompanyProvider } from "./app/contexts/CompanyContext";
import { LicenseProvider } from "./app/contexts/LicenseContext";
import { NotificationProvider } from "./app/contexts/NotificationContext";
import { ReauthProvider } from "./app/contexts/ReauthContext";
import { router } from "./app/router";
import { NotificationViewport } from "./components/NotificationViewport";
import "./index.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      // Un rechazo de empresa no se reintenta: repetir contra una empresa que
      // el servidor acaba de rechazar da el mismo rechazo para siempre.
      retry: debeReintentar,
      // La identidad de cada consulta incluye la empresa activa, salvo las
      // pocas raíces que no dependen de ella. Es lo que impide que los datos
      // de una empresa se sirvan bajo otra mientras llega la respuesta nueva.
      queryKeyHashFn: crearHashDeClave(getActiveCompanyId),
    },
  },
});

createRoot(document.getElementById("root") as HTMLElement).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <NotificationProvider>
        <AuthProvider>
          <ReauthProvider>
            <LicenseProvider>
              <CompanyProvider>
                <RouterProvider router={router} />
                <NotificationViewport />
              </CompanyProvider>
            </LicenseProvider>
          </ReauthProvider>
        </AuthProvider>
      </NotificationProvider>
    </QueryClientProvider>
  </StrictMode>,
);
