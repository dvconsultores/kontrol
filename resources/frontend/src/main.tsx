/**
 * Punto de entrada de KONTROL frontend.
 * Providers: QueryClient, Auth, License, Company, Notification, Router.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router";

import { AuthProvider } from "./app/contexts/AuthContext";
import { CompanyProvider } from "./app/contexts/CompanyContext";
import { LicenseProvider } from "./app/contexts/LicenseContext";
import { NotificationProvider } from "./app/contexts/NotificationContext";
import { router } from "./app/router";
import { NotificationViewport } from "./components/NotificationViewport";
import "./index.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
});

createRoot(document.getElementById("root") as HTMLElement).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <NotificationProvider>
        <AuthProvider>
          <LicenseProvider>
            <CompanyProvider>
              <RouterProvider router={router} />
              <NotificationViewport />
            </CompanyProvider>
          </LicenseProvider>
        </AuthProvider>
      </NotificationProvider>
    </QueryClientProvider>
  </StrictMode>,
);
