import type { ReactNode } from "react";
import { useMatches } from "react-router";

import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import type { RequisitoDePantalla } from "@/app/autoridad/requisitos";
import { evaluarPantalla } from "@/app/autoridad/requisitos";
import { LoadingState } from "@/components/LoadingState";

import { DenegacionDeAutoridad } from "./DenegacionDeAutoridad";

interface HandleConRequisito {
  requisito?: RequisitoDePantalla | null;
}

function esHandleConRequisito(handle: unknown): handle is HandleConRequisito {
  return typeof handle === "object" && handle !== null && "requisito" in handle;
}

export function RutaAutorizada({ children }: { children: ReactNode }): React.JSX.Element {
  const matches = useMatches();
  const autoridad = useAutoridad();

  const ultimaCoincidencia = matches[matches.length - 1];
  const handle = ultimaCoincidencia?.handle;

  const requisito: RequisitoDePantalla | null =
    handle !== null && handle !== undefined && esHandleConRequisito(handle)
      ? (handle.requisito ?? null)
      : null;

  const resultado = evaluarPantalla(autoridad, requisito);

  if (resultado.estado === "CARGANDO") {
    return <LoadingState rows={3} />;
  }

  if (resultado.estado === "DENEGADA") {
    return <DenegacionDeAutoridad motivo={resultado.motivo} alcance={resultado.alcance} />;
  }

  return <>{children}</>;
}
