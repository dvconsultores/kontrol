export type EstadoImportacion = "NEGOTIATING" | "ORDERED" | "DOCUMENTS_COMPLETE" | "CANCELLED";
export type EstadoDocumento = "PENDING" | "RECEIVED" | "VALIDATED" | "OBSERVED";

export const ESTADOS: Record<EstadoImportacion, string> = {
  NEGOTIATING: "En negociación",
  ORDERED: "Orden vinculada",
  DOCUMENTS_COMPLETE: "Documentación completa",
  CANCELLED: "Cancelada",
};

export const ESTADOS_DOCUMENTO: Record<EstadoDocumento, string> = {
  PENDING: "Pendiente",
  RECEIVED: "Recibido",
  VALIDATED: "Validado",
  OBSERVED: "Observado",
};

export const INCOTERMS = ["EXW", "FCA", "CPT", "CIP", "DAP", "DPU", "DDP", "FAS", "FOB", "CFR", "CIF"] as const;

export function importacionKey(companyId: string, id: string) {
  return `${companyId}:${id}`;
}
