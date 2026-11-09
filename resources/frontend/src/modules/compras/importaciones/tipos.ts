export type EstadoImportacion =
  | "NEGOTIATING"
  | "ORDERED"
  | "DOCUMENTS_COMPLETE"
  | "DISPATCHED"
  | "CANCELLED";
export type EstadoDocumento = "PENDING" | "RECEIVED" | "VALIDATED" | "OBSERVED";

export const ESTADOS: Record<EstadoImportacion, string> = {
  NEGOTIATING: "En negociación",
  ORDERED: "Orden vinculada",
  DOCUMENTS_COMPLETE: "Documentación completa",
  DISPATCHED: "Despachada",
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

export type EtapaLogistica =
  | "NO_RECEIPT"
  | "AWAITING_ARRIVAL"
  | "RECEIVING"
  | "INCIDENTS_OPEN"
  | "PENDING_CONFIRMATION"
  | "PENDING_PUTAWAY"
  | "PUT_AWAY";

export const ETAPAS_LOGISTICAS: Record<EtapaLogistica, string> = {
  NO_RECEIPT: "Sin recepción",
  AWAITING_ARRIVAL: "Esperando arribo",
  RECEIVING: "En recepción",
  INCIDENTS_OPEN: "Incidencias abiertas",
  PENDING_CONFIRMATION: "Por confirmar inventario",
  PENDING_PUTAWAY: "Por ubicar",
  PUT_AWAY: "Recibida y ubicada",
};

export type EstadoRecepcion =
  | "DRAFT"
  | "CONFIRMED"
  | "QUALITY_PENDING"
  | "ACCEPTED"
  | "PARTIALLY_ACCEPTED"
  | "REJECTED"
  | "CLOSED"
  | "CANCELLED";

export const ESTADOS_RECEPCION: Record<EstadoRecepcion, string> = {
  DRAFT: "Borrador",
  CONFIRMED: "Confirmada",
  QUALITY_PENDING: "En calidad",
  ACCEPTED: "Aceptada",
  PARTIALLY_ACCEPTED: "Aceptada parcialmente",
  REJECTED: "Rechazada",
  CLOSED: "Cerrada",
  CANCELLED: "Anulada",
};

export type EstadoConfirmacion = "PENDIENTE" | "CONFIRMADA";

export const ESTADOS_CONFIRMACION: Record<EstadoConfirmacion, string> = {
  PENDIENTE: "Pendiente",
  CONFIRMADA: "Confirmada",
};

export type EstadoIncidencia = "REGISTRADA" | "ESCALADA" | "RESUELTA" | "ANULADA";

export const ESTADOS_INCIDENCIA: Record<EstadoIncidencia, string> = {
  REGISTRADA: "Registrada",
  ESCALADA: "Escalada a Compras",
  RESUELTA: "Resuelta",
  ANULADA: "Anulada",
};

export type TipoIncidencia =
  | "FALTANTE"
  | "SOBRANTE"
  | "DANO"
  | "REFERENCIA_INCORRECTA"
  | "DIFERENCIA_DOCUMENTAL";

export const TIPOS_INCIDENCIA: Record<TipoIncidencia, string> = {
  FALTANTE: "Faltante",
  SOBRANTE: "Sobrante",
  DANO: "Daño",
  REFERENCIA_INCORRECTA: "Referencia incorrecta",
  DIFERENCIA_DOCUMENTAL: "Diferencia documental",
};

export type RecepcionLogistica = {
  id: string;
  code: string;
  status: EstadoRecepcion;
  quality_status: string | null;
  confirmation_status: EstadoConfirmacion | null;
  warehouse_id: string | null;
  warehouse_name: string | null;
  arrival_at: string | null;
  packages_declared: number | null;
  packages_received: number | null;
  record_issued_at: string | null;
  can_confirm_arrival: boolean;
};

export type IncidenciaLogistica = {
  id: string;
  code: string;
  receipt_id: string;
  receipt_code: string;
  incident_type: TipoIncidencia;
  status: EstadoIncidencia;
  affected_base_quantity: number | null;
  product_name: string | null;
};

export type CantidadLogistica = {
  receipt_code: string;
  product_id: string;
  product_name: string;
  received_base: number | null;
  confirmed_available: number | null;
  rejected: number | null;
  located: number | null;
  pending_putaway: number | null;
};

export type PutawayPendiente = {
  receipt_code: string;
  warehouse_id: string;
  warehouse_name: string;
  product_id: string;
  product_name: string;
  state: string | null;
  lot_id: string | null;
  serial_id: string | null;
  pending_base: number | null;
};

export type UbicacionLogistica = {
  product_name: string;
  location_label: string;
  quantity: number | null;
};

export type LogisticsDetalle = {
  stage: EtapaLogistica;
  receipts: RecepcionLogistica[];
  incidents: IncidenciaLogistica[];
  quantities: CantidadLogistica[];
  putaway_pending: PutawayPendiente[];
  locations: UbicacionLogistica[];
};

export type Documento = {
  id: string;
  kind: string;
  name: string;
  required: boolean;
  reference: string | null;
  status: EstadoDocumento;
  observation: string | null;
  version: number;
  attachments: unknown[];
  allowed_actions: {
    receive: boolean;
    validate: boolean;
    observe: boolean;
  };
};

export type GastoImportacion = {
  id: string;
  kind: string;
  concept: string;
  reference: string;
  supplier_name: string | null;
  invoice_number: string | null;
  expense_date: string;
  currency: string;
  amount: string;
  functional_amount: string;
  status: "REGISTERED" | "VOIDED";
  void_reason: string | null;
  version: number;
  username: string | null;
  created_at: string | null;
  rate: {
    value: string;
    source: string | null;
    type: string | null;
    date: string | null;
    origin: string | null;
    derivation: string | null;
    identity: boolean;
  };
  document: {
    id: string;
    name: string;
    status: string;
  } | null;
  allowed_actions: {
    void: boolean;
  };
};

export type CapaDeCosto = {
  receipt_code: string;
  product_code: string | null;
  product_name: string | null;
  warehouse_name: string | null;
  quantity_in: number;
  quantity_remaining: number;
  unit_cost: string;
  currency: string;
  landed_cost: string;
  partially_consumed: boolean;
};

export type CandidatoFactura = {
  id: string;
  invoice_number: string;
  supplier_name: string | null;
  issue_date: string | null;
  currency: string;
  total: string;
  tax_total: string;
  assigned: string;
  available: string;
  status: string;
};

export type DetalleCostos = {
  functional_currency: string;
  can_register: boolean;
  currencies: string[];
  expenses: GastoImportacion[];
  totals: {
    count: number;
    functional_total: string;
    by_currency: Array<{ currency: string; amount: string }>;
  };
  layers: CapaDeCosto[];
  goods_totals: Array<{ currency: string; amount: string }>;
  application: {
    status: string;
  };
};

export type DetalleImportacion = {
  id: string;
  code: string;
  status: EstadoImportacion;
  currency: string;
  supplier_id: string;
  supplier_name: string;
  order_id: string | null;
  order_code: string | null;
  incoterm: string | null;
  incoterm_place: string | null;
  payment_conditions: string | null;
  delivery_conditions: string | null;
  expected_dispatch_date: string | null;
  expected_arrival_date: string | null;
  notes: string | null;
  cancel_reason: string | null;
  next_action: string | null;
  agent_party_id: string | null;
  carrier_party_id: string | null;
  transport_document: string | null;
  origin: string | null;
  destination: string | null;
  actual_departure_date: string | null;
  summary: {
    pending: string[];
    missing?: string[];
    documents_validated: number;
    documents_required: number;
    open_corrections: number;
    financial_count: number;
    agent_name: string | null;
    carrier_name: string | null;
  };
  tracking_events: {
    id: string;
    milestone: "BOOKED" | "DEPARTED" | "IN_TRANSIT" | "TRANSSHIPMENT" | "DELAYED" | "OTHER";
    occurred_on: string;
    location: string | null;
    notes: string | null;
    username: string | null;
  }[];
  financial: {
    id: string;
    kind: "PAYMENT" | "ADVANCE";
    amount: string;
    currency: string;
    status: string;
    date: string;
  }[];
  corrections: {
    id: string;
    kind: "FALTANTE" | "CORRECCION_DOCUMENTAL";
    document_id: string | null;
    description: string;
    action_required: string;
    responsible: "PROVEEDOR" | "AGENTE" | "IMPORTACION";
    responsible_name: string;
    status: "OPEN" | "RESOLVED" | "CANCELLED";
    resolution: string | null;
    resolved_at: string | null;
    version: number;
    attachments: unknown[];
    allowed_actions: {
      resolve: boolean;
      cancel: boolean;
    };
  }[];
  allowed_actions: {
    edit: boolean;
    link_order: boolean;
    add_document: boolean;
    confirm_documents: boolean;
    confirm_dispatch: boolean;
    cancel: boolean;
    create_receipt?: boolean;
  };
  documents: Documento[];
  logistics: LogisticsDetalle | null;
  version: number;
};
