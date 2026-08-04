/**
 * RouteGuard — protege rutas autenticadas (FR-001-042, DOC-08 §15.1).
 * Si no hay sesión, redirige a /login. El backend sigue siendo autoridad.
 */
import { Navigate, Outlet } from "react-router";

import { useAuth } from "@/app/contexts/AuthContext";

import { LoadingState } from "./LoadingState";

export function RouteGuard(): React.JSX.Element {
  const { isAuthenticated, isReady } = useAuth();

  if (!isReady) {
    // Esperar el intento inicial de restaurar sesión antes de decidir.
    return <LoadingState rows={3} />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
