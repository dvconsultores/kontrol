import type { AlcanceDeCapacidad, AutoridadValue } from "./AutoridadContext";
import type { Motivo } from "./operaciones";

export interface RequisitoDePantalla {
  capacidad: string;
  alcance: AlcanceDeCapacidad;
  operacion?: readonly [string, string];
}

export type ResultadoDePantalla =
  | { estado: "CARGANDO" }
  | { estado: "PERMITIDA" }
  | { estado: "DENEGADA"; motivo: Motivo; alcance: AlcanceDeCapacidad };

export function evaluarPantalla(
  autoridad: AutoridadValue,
  requisito: RequisitoDePantalla | null,
): ResultadoDePantalla {
  if (requisito === null) {
    return { estado: "PERMITIDA" };
  }

  if (autoridad.estado !== "LISTA") {
    return { estado: "CARGANDO" };
  }

  if (!autoridad.tiene(requisito.capacidad, requisito.alcance)) {
    const motivo = autoridad.motivoDeCapacidad(requisito.capacidad, requisito.alcance);
    return {
      estado: "DENEGADA",
      motivo: motivo ?? "PERMISSION_DENIED",
      alcance: requisito.alcance,
    };
  }

  if (requisito.operacion !== undefined) {
    const [metodo, ruta] = requisito.operacion;
    if (!autoridad.puede(metodo, ruta)) {
      return {
        estado: "DENEGADA",
        motivo: autoridad.motivo(metodo, ruta) ?? "PERMISSION_DENIED",
        alcance: "empresa",
      };
    }
  }

  return { estado: "PERMITIDA" };
}
