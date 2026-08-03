/**
 * PermissionGuard — punto de extensión para ocultar/bloquear según permiso
 * (FR-001-042, DOC-08 §15.2). En la fundación la autoridad es el backend
 * (allowed_actions); este guard mejora UX y no es control de seguridad.
 */
import type { ReactNode } from "react";

export interface PermissionGuardProps {
  /** Permiso requerido en formato "resource:action". */
  permission?: string;
  /** Si es true, oculta el contenido en lugar de renderizarlo. */
  hide?: boolean;
  children: ReactNode;
}

export function PermissionGuard({ hide, children }: PermissionGuardProps): React.JSX.Element | null {
  // La verificación fina se resuelve con allowed_actions del backend.
  void hide;
  return <>{children}</>;
}

