/**
 * PermissionGuard — oculta/bloquea contenido según permiso del usuario
 * (FR-001-042, DOC-08 §15.2, KAUD-004).
 *
 * Los permisos vienen del backend (`GET /auth/me`, resource:action) y se
 * resuelven en el AuthContext. El backend sigue siendo la autoridad de
 * seguridad (require_permission / allowed_actions); este guard mejora la UX
 * evitando mostrar menús/acciones no permitidas.
 *
 * - `permission` (formato "resource:action"): si el usuario NO lo tiene, se
 *   oculta el contenido (o se renderiza null).
 * - `hide` (legacy): si es true, oculta el contenido.
 */
import { type ReactNode } from "react";

import { useAuth } from "@/app/contexts/AuthContext";

export interface PermissionGuardProps {
  /** Permiso requerido en formato "resource:action". */
  permission?: string;
  /** Si es true, oculta el contenido en lugar de renderizarlo. */
  hide?: boolean;
  children: ReactNode;
}

export function PermissionGuard({ permission, hide, children }: PermissionGuardProps): React.JSX.Element | null {
  const { hasPermission } = useAuth();
  if (hide) {
    return null;
  }
  if (permission && !hasPermission(permission)) {
    return null;
  }
  return <>{children}</>;
}
