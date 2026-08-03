/** PageLayout — contenedor de página con Sidebar, Topbar, banner y contenido. */
import type { ReactNode } from "react";

import { LicenseBanner } from "@/components/LicenseBanner";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

export interface PageLayoutProps {
  children: ReactNode;
}

export function PageLayout({ children }: PageLayoutProps): React.JSX.Element {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar />
        <LicenseBanner />
        <main className="min-w-0 flex-1 overflow-y-auto bg-surface-50">{children}</main>
      </div>
    </div>
  );
}
