/** PageLayout — contenedor de página con Sidebar, Topbar, banner y contenido. */
import { useCallback, useRef, useState, type ReactNode } from "react";

import { LicenseBanner } from "@/components/LicenseBanner";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

export interface PageLayoutProps {
  children: ReactNode;
}

export function PageLayout({ children }: PageLayoutProps): React.JSX.Element {
  // Estado del menú superpuesto para viewports < 768 px (md). A partir de md
  // el Sidebar vuelve a comportarse exactamente como antes (en el flujo).
  const [menuAbierto, setMenuAbierto] = useState(false);
  const botonMenuRef = useRef<HTMLButtonElement | null>(null);

  const abrirMenu = useCallback(() => setMenuAbierto(true), []);
  const cerrarMenu = useCallback(() => {
    setMenuAbierto(false);
    // El foco vuelve al botón que abrió el menú.
    botonMenuRef.current?.focus();
  }, []);

  return (
    <div className="flex h-screen overflow-hidden">
      {/* En md+ el Sidebar va en el flujo como siempre. En <md se superpone
          como panel: se monta solo al abrir. */}
      <div className="hidden md:flex md:h-full">
        <Sidebar />
      </div>
      {menuAbierto ? (
        <div className="fixed inset-0 z-40 md:hidden" role="presentation">
          <div
            className="absolute inset-0 bg-black/40"
            onClick={cerrarMenu}
            aria-hidden="true"
          />
          <div className="absolute inset-y-0 left-0 z-50 flex h-full">
            <Sidebar onNavigated={cerrarMenu} onClose={cerrarMenu} autoFocus />
          </div>
        </div>
      ) : null}
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar onAbrirMenu={abrirMenu} botonMenuRef={botonMenuRef} />
        <LicenseBanner />
        <main className="min-w-0 flex-1 overflow-y-auto bg-surface-50">{children}</main>
      </div>
    </div>
  );
}
