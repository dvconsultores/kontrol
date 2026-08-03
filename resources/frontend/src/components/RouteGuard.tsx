/**
 * RouteGuard — protege rutas autenticadas (FR-001-042, DOC-08 §15.1).
 * Si no hay sesión, redirige a /login. El backend sigue siendo autoridad.
 */
import { Navigate, Outlet } from "react-router-dom";

import { useAuth } from "@/app/contexts/AuthContext";

import { LoadingState } from "./LoadingState";

export function RouteGuard(): React.JSX.Element {
  const { isAuthenticated, accessToken, refreshSession } = useAuth();

  if (!isAuthenticated && accessToken === null) {
    // Esperar el refresh inicial antes de redirigir.
    return <LoadingState rows={3} />;
  }

  if (!isAuthenticated) {
    void refreshSession();
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
