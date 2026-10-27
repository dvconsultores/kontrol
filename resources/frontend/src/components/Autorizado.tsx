import type { ReactNode } from "react";

import { useAutoridad } from "@/app/autoridad/AutoridadContext";

/**
 * Envuelve el control que dispara EXACTAMENTE esa llamada; ocultar es UX,
 * el backend autoriza (ADR-018).
 */
export function Autorizado({
  operacion,
  children,
  fallback = null,
}: {
  operacion: readonly [string, string];
  children: ReactNode;
  fallback?: ReactNode;
}): React.JSX.Element | null {
  const autoridad = useAutoridad();

  if (!autoridad.puede(operacion[0], operacion[1])) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}
