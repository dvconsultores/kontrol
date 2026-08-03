/** PageActions — contenedor de acciones de página alineadas a la derecha. */
import type { ReactNode } from "react";

export interface PageActionsProps {
  children: ReactNode;
}

export function PageActions({ children }: PageActionsProps): React.JSX.Element {
  return <div className="flex items-center gap-2">{children}</div>;
}
