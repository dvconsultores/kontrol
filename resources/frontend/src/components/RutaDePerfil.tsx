/**
 * RutaDePerfil — guard de UI por superficie de KONTROL Gobierno (Spec 004 delta §5).
 * GOVERNMENT_PROFILE_DIRECT_ENTERPRISE_ROUTE=BLOCKED_UI: el backend sigue siendo la
 * autoridad; aquí solo se evita mostrar pantallas de otra superficie.
 */
import type { ReactNode } from "react";
import { useLocation } from "react-router";

import { usePerfilDeInstalacion } from "@/modules/gobierno/api";
import { superficieDeRuta, superficieVisible } from "@/app/perfil/superficies";
import { LoadingState } from "@/components/LoadingState";
import { ErrorState } from "@/components/ErrorState";
import { ForbiddenState } from "@/components/ForbiddenState";

export function RutaDePerfil({ children }: { children: ReactNode }): React.JSX.Element {
  const { pathname } = useLocation();
  const perfil = usePerfilDeInstalacion();
  const superficie = superficieDeRuta(pathname);

  if (superficie !== "SHARED" && perfil.estado === "RESOLVIENDO") {
    return <LoadingState rows={3} />;
  }
  if (superficie !== "SHARED" && perfil.estado === "ERROR") {
    return <ErrorState message="No fue posible determinar el perfil de producto de esta instalación. Las funciones de Gobierno y Enterprise permanecen ocultas hasta resolverlo." />;
  }

  if (!superficieVisible(perfil, superficie)) {
    return <ForbiddenState />;
  }

  return <>{children}</>;
}
