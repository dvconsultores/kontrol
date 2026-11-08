import type { Party } from "@/api/types";

export const ROLE_LABELS: Record<string, string> = {
  CLIENTE: "Cliente",
  PROVEEDOR: "Proveedor",
  TRANSPORTISTA: "Transportista",
  CONDUCTOR: "Conductor",
  VENDEDOR: "Vendedor",
  BENEFICIARIO: "Beneficiario",
};

export const PERSON_TYPES: { value: string; label: string }[] = [
  { value: "JURIDICA", label: "Jurídica" },
  { value: "NATURAL", label: "Natural" },
  { value: "GUBERNAMENTAL", label: "Gubernamental" },
  { value: "PUBLICA", label: "Pública" },
  { value: "EXTRANJERA", label: "Extranjera" },
];

export interface BlockingDocument {
  module: string;
  document: string;
  count: number;
}

export interface PartyDetail extends Party {
  blocking_documents: BlockingDocument[];
  supplier_approval_status: string | null;
}

export interface PartyAuditItem {
  id: string;
  action: string;
  action_label: string;
  event_time: string;
  username: string | null;
  request_id: string | null;
  reason: string | null;
  details: Record<string, Record<string, unknown>>;
}

export function terceroKey(
  companyId: string | undefined,
  partyId: string,
): readonly unknown[] {
  return ["maestros", "tercero", companyId, partyId];
}
