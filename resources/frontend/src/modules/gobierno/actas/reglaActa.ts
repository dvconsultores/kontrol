import type { EvidenciaAnexo, HitoPlazo, PlazoEstado, PlazoRegla } from "./api";

/** Etiquetas de la regla del acta (CTL-09-DELIVERY-ACT-POLICY). Solo presentación: los valores los da el backend. */

export const ETIQUETAS_HITO: Record<HitoPlazo, string> = {
  ELABORACION: "Elaboración del acta",
  REMISION_UAI: "Remisión a la UAI",
  OBSERVACIONES: "Observaciones del receptor",
};

export const ETIQUETAS_UNIDAD_PLAZO: Record<PlazoRegla["unidad"], string> = {
  DIAS_HABILES: "días hábiles",
  DIAS_CONTINUOS: "días continuos",
};

export const ETIQUETAS_ESTADO_PLAZO: Record<PlazoEstado["estado"], string> = {
  SIN_CALENDARIO_HABIL: "Sin calendario hábil oficial",
  REGISTRADO: "Registrado",
  PENDIENTE: "Pendiente",
  EN_PLAZO: "En plazo",
  VENCIDO: "Vencido",
  CUMPLIDO: "Cumplido",
  CUMPLIDO_FUERA_DE_PLAZO: "Cumplido fuera de plazo",
};

export const ETIQUETAS_EVIDENCIA: Record<EvidenciaAnexo, string> = {
  DOCUMENTO: "Documento",
  CERTIFICACION: "Certificación",
  DECLARACION: "Declaración",
  DATO: "Dato",
};

export const ETIQUETAS_RELACION: Record<"SUCESOR" | "DESIGNADO", string> = {
  SUCESOR: "Sucesor en el cargo",
  DESIGNADO: "Designado para recibir",
};

/** «3 días hábiles», «10 días continuos». */
export function describirPlazo(plazo: Pick<PlazoRegla, "valor" | "unidad">): string {
  return `${plazo.valor} ${ETIQUETAS_UNIDAD_PLAZO[plazo.unidad]}`;
}

/** Los anexos DECLARACION y DATO se resuelven con texto; los demás, con documentos (D-AE-04). */
export function seResuelveConTexto(evidencia: EvidenciaAnexo): boolean {
  return evidencia === "DECLARACION" || evidencia === "DATO";
}
