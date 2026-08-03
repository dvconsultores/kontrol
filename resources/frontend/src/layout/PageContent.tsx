/** PageContent — contenedor del contenido con ancho fluido y máximos (DOC-08 §5). */
import type { ReactNode } from "react";

export interface PageContentProps {
  children: ReactNode;
  maxWidth?: "sm" | "md" | "lg" | "full";
}

const widths = {
  sm: "max-w-lg",
  md: "max-w-3xl",
  lg: "max-w-5xl",
  full: "max-w-none",
};

export function PageContent({ children, maxWidth = "lg" }: PageContentProps): React.JSX.Element {
  return <div className={`mx-auto w-full px-4 py-6 ${widths[maxWidth]}`}>{children}</div>;
}
