/** Tipos compartidos de la API fundacional (contrato DOC-08 §3, API v1). */

export type LicenseMode =
  | "FULL_ACCESS"
  | "RENEWAL_NOTICE"
  | "CRITICAL_RENEWAL_NOTICE"
  | "READ_ONLY"
  | "SECURITY_SUSPENSION";

export interface LicenseStatus {
  installation_id: string;
  activated: boolean;
  mode: LicenseMode | "PENDING";
  period_start: string | null;
  period_end: string | null;
  read_only_start: string | null;
  entitlements: Record<string, unknown>;
  minimum_version: string | null;
  license_url: string;
}

export interface UserInfo {
  id: string;
  username: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  must_change_password: boolean;
  user: UserInfo;
}

export interface CompanySummary {
  id: string;
  code: string;
  legal_name: string;
  rif: string;
  status: string;
}

export interface AuditEvent {
  id: string;
  action: string;
  entity_type: string;
  entity_id: string | null;
  user_id: string | null;
  request_id: string | null;
  source: string | null;
  reason: string | null;
  /** Sello del servidor (ISO 8601 con zona, nunca nulo). El servidor no publica `created_at`. */
  event_time: string;
}

export interface SetupStatus {
  installation: string | null;
  tenant: string | null;
  company: string | null;
  initialized: boolean;
}

/* -------------------------------------------------------------------------- */
/* Maestros (002-maestros)                                                     */
/* -------------------------------------------------------------------------- */

export interface AllowedActions {
  view: boolean;
  edit: boolean;
  activate: boolean;
  deactivate: boolean;
  delete: boolean;
  approve?: boolean;
  audit?: boolean;
  print?: boolean;
  export?: boolean;
  [action: string]: boolean | undefined;
}

export interface Party {
  id: string;
  code: string;
  name: string;
  person_type: string;
  legal_name: string | null;
  trade_name: string | null;
  tax_id: string | null;
  roles: string[];
  status: string;
  allowed_actions: AllowedActions;
}

export interface PagedResult<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface CatalogItemSummary {
  id: string;
  code: string;
  name: string;
  item_type: "PRODUCT" | "SERVICE";
  status: string;
  allowed_actions: AllowedActions;
}

export interface CatalogItemSearchResult {
  id: string;
  code: string;
  name: string;
  item_type: "PRODUCT" | "SERVICE";
}

export interface TaxonomyNode {
  id: string;
  code: string;
  name: string;
  level: string;
  status: string;
}

export interface UnitOfMeasure {
  id: string;
  code: string;
  name: string;
  symbol: string;
  dimension: string;
}

export interface CatalogAttribute {
  id: string;
  code: string;
  name: string;
  data_type: string;
  searchable: boolean;
}

export interface ProfileSummary {
  id: string;
  code: string;
  name: string;
  profile_type: string;
  version: number;
  status: string;
  approval_status: string;
}

export interface HealthResponse {
  status: "ok" | "degraded";
  services: Record<string, string>;
  version: string;
}

/** Lo que responde `GET /system/diagnostics` (FR-001-084). */
export interface DiagnosticsResponse {
  environment: string;
  version: string;
  database: { ok: boolean };
  installation: { id: string | null; state: string | null };
  license: { activated: boolean; mode: string | null; period_end: string | null };
}

// ---------------------------------------------------------------------------
// Inventario y logística (003-inventario-logistica)
// ---------------------------------------------------------------------------
export interface InventoryBalance {
  id: string;
  company_id: string;
  warehouse_id: string;
  location_id: string | null;
  product_id: string;
  lot_id: string | null;
  serial_id: string | null;
  state: string;
  qty_on_hand: number;
  qty_reserved: number;
  qty_available: number;
  last_rebuilt_at: string | null;
}

/** Spec 022 — ubicación candidata para el put-away. */
export interface PutAwayLocation {
  id: string;
  code: string;
  name: string | null;
  warehouse_id: string;
  zone_id: string | null;
  aisle_id: string | null;
  rack_id: string | null;
  level_id: string | null;
  sequence: number | null;
  status: string;
  /** `enforced` es siempre false en V1: la capacidad informa, no bloquea (`R-D0-14-6`). */
  capacity: { units: number | null; weight: number | null; uom: string | null; enforced: boolean };
}

export interface InventoryMovement {
  id: string;
  company_id: string;
  warehouse_id: string;
  location_id: string | null;
  product_id: string;
  movement_type_id: string;
  quantity: number;
  unit_cost: number | null;
  currency: string;
  document_ref: string | null;
  occurred_at: string;
  reversed_by_id: string | null;
  status: string;
  allowed_actions: AllowedActions;
}

export interface InventoryLot {
  id: string;
  product_id: string;
  lot_number: string;
  manufacture_date: string | null;
  expiry_date: string | null;
  supplier_id: string | null;
  receipt_ref: string | null;
  status: string;
  allowed_actions: AllowedActions;
}

export interface ProductSerial {
  id: string;
  product_id: string;
  serial: string;
  imei1: string | null;
  imei2: string | null;
  mac: string | null;
  lot_id: string | null;
  status: string;
  warehouse_id: string | null;
  warranty_until: string | null;
}

export interface Reservation {
  id: string;
  source_document: string | null;
  product_id: string;
  warehouse_id: string;
  lot_id: string | null;
  serial_id: string | null;
  quantity: number;
  status: string;
  expires_at: string | null;
  /** Identidad y ciclo (Spec 030). */
  source_type?: "SALES_ORDER" | "MANUAL" | null;
  source_order_id?: string | null;
  source_line_id?: string | null;
  trigger?: string | null;
  oversell?: boolean;
  base_quantity?: string | null;
  presentation_id?: string | null;
  uom_id?: string | null;
  released_at?: string | null;
  release_reason?: string | null;
}

export interface TransferLineSummary {
  id: string;
  product_id: string;
  quantity_sent: number;
  quantity_received: number | null;
  difference: number | null;
  destination_state: string;
}

export interface TransferSummary {
  id: string;
  code: string;
  origin_warehouse_id: string;
  destination_warehouse_id: string;
  request_ref: string | null;
  shipment_ref: string | null;
  receipt_ref: string | null;
  status: string;
  allowed_actions: AllowedActions;
  lines: TransferLineSummary[];
}

export interface StockCount {
  id: string;
  code: string;
  warehouse_id: string;
  plan_ref: string | null;
  scope: unknown[];
  freeze_policy: string;
  status: string;
  allowed_actions: AllowedActions;
}

export interface InventoryAdjustment {
  id: string;
  warehouse_id: string;
  product_id: string;
  quantity: number;
  reason: string;
  evidence_ref: string | null;
  unit_cost: number | null;
  currency: string;
  status: string;
  allowed_actions: AllowedActions;
}

export interface CostLayer {
  id: string;
  product_id: string;
  warehouse_id: string;
  receipt_ref: string | null;
  quantity_in: number;
  quantity_remaining: number;
  unit_cost: number;
  currency: string;
  fiscal_rate: number | null;
  landed_cost: number;
  status: string;
}

export interface CostingProfile {
  id: string;
  code: string;
  method: "AVERAGE" | "FIFO";
  currency: string;
  product_id: string | null;
  effective_from: string | null;
  effective_to: string | null;
  version: number;
  status: string;
}

export interface MovementType {
  id: string;
  code: string;
  name: string;
  direction: "IN" | "OUT" | "INTERNAL";
  version: number;
  status: string;
}

export interface ValuationResult {
  valuation: number;
  currency: string;
}

// ---------------------------------------------------------------------------
// Compras y cuentas por pagar (004)
// ---------------------------------------------------------------------------
export interface PurchaseOrderLine {
  id: string;
  product_id: string;
  quantity_ordered: number;
  quantity_received: number;
  unit_price: number;
  needs_inventory: boolean;
}

export interface PurchaseOrderSummary {
  id: string;
  code: string;
  supplier_id: string;
  terms: string | null;
  expected_date: string | null;
  currency: string;
  status: string;
  approval_ref: string | null;
  allowed_actions: AllowedActions;
  lines: PurchaseOrderLine[];
}

export interface SupplierInvoiceSummary {
  id: string;
  supplier_id: string;
  invoice_number: string;
  control_number: string | null;
  issue_date: string | null;
  currency: string;
  tax_total: number;
  total: number;
  status: string;
  reversed_by_id: string | null;
  allowed_actions: AllowedActions;
}

export interface GoodsReceiptSummary {
  id: string;
  code: string;
  order_id: string;
  warehouse_id: string;
  status: string;
  /** Veredicto de conformidad de la etapa 7 del proceso. */
  quality_status: string;
  /** Etapas 1 y 2: arribo confirmado y descarga programada. */
  arrival_at?: string | null;
  unloading_scheduled_at?: string | null;
  /** Etapa 6: bultos declarados por el documento y contados en el muelle. */
  packages_declared?: number | null;
  packages_received?: number | null;
  /** Etapa 5. */
  inspected_at?: string | null;
  /** Etapa 11: acta emitida. */
  record_issued_at?: string | null;
}

/** Línea de recepción con su unidad y lo que se observó (Spec 019). */
export interface GoodsReceiptLine {
  id: string;
  order_line_id: string;
  product_id: string;
  quantity_received: string;
  quantity_accepted: string;
  quantity_rejected: string;
  presentation_id: string | null;
  uom_id: string | null;
  conversion_factor_snapshot: string | null;
  base_quantity_received: string | null;
  base_quantity_accepted: string | null;
  base_quantity_rejected: string | null;
  uom_source: string | null;
  physical_condition: string | null;
  damaged_quantity: string | null;
  damage_notes: string | null;
  identification_ok: boolean | null;
  reference_ok: boolean | null;
  overage_base_quantity: string | null;
  lot_number: string | null;
  lot_id: string | null;
  expiry_date: string | null;
  serials: string | null;
  quality: string;
}

/** Incidencia de recepción (Spec 020). Los cinco tipos y los cuatro
 *  tratamientos salen del proceso documentado; no hay más. */
export type IncidentType =
  | "FALTANTE"
  | "SOBRANTE"
  | "DANO"
  | "REFERENCIA_INCORRECTA"
  | "DIFERENCIA_DOCUMENTAL";

export type IncidentResolution =
  | "AJUSTE_AUTORIZADO"
  | "RECLAMO_PROVEEDOR"
  | "INVESTIGACION_INTERNA"
  | "CUARENTENA";

export type IncidentStatus =
  | "REGISTRADA"
  | "ESCALADA"
  | "PENDIENTE_AUTORIZACION"
  | "RESUELTA"
  | "ANULADA";

export interface ReceiptIncident {
  id: string;
  code: string;
  receipt_id: string;
  receipt_line_id: string | null;
  incident_type: IncidentType | string;
  affected_base_quantity: string | null;
  description: string | null;
  status: IncidentStatus | string;
  escalated_at: string | null;
  escalated_by: string | null;
  escalation_notes: string | null;
  resolution: IncidentResolution | string | null;
  resolution_reason: string | null;
  resolved_at: string | null;
  resolved_by: string | null;
  approval_request_id: string | null;
  cancelled_reason: string | null;
}

/** Lo que la Spec 021 consumirá para confirmar el inventario. */
export interface IncidentOutcome {
  receipt_id: string;
  total: number;
  unresolved: number;
  ready_for_confirmation: boolean;
  items: Array<
    Pick<ReceiptIncident, "code" | "incident_type" | "receipt_line_id" | "affected_base_quantity" | "status" | "resolution" | "approval_request_id"> & {
      incident_id: string;
    }
  >;
}

export interface GoodsReceiptDetail extends GoodsReceiptSummary {
  arrival_confirmed_by: string | null;
  packing_list_ref: string | null;
  supplier_invoice_ref: string | null;
  packing_list_match: boolean | null;
  supplier_invoice_match: boolean | null;
  order_match: boolean | null;
  documentation_match: boolean | null;
  inspected_by: string | null;
  inspection_notes: string | null;
  record_issued_by: string | null;
  lines: GoodsReceiptLine[];
}

/** Spec 021: dimensión distinta del `status`. Aceptada no es confirmada. */
export interface GoodsReceiptConfirmationFields {
  confirmation_status?: string;
  confirmed_at?: string | null;
  confirmed_by?: string | null;
}

/** Spec 021 — la conciliación por línea y qué falta para poder confirmar. */
export interface ReconciliationItem {
  receipt_line_id: string;
  product_id: string;
  base_quantity_received: string;
  base_quantity_ordered: string | null;
  counted_base_quantity: string | null;
  counted: boolean;
  matches_order: boolean | null;
  matches_physical: boolean | null;
  difference_kinds: string[];
  already_confirmed_base: string;
  pending_base: string;
}

export interface ReceiptReconciliation {
  receipt_id: string;
  confirmation_status: string;
  packing_list_match: boolean | null;
  supplier_invoice_match: boolean | null;
  order_match: boolean | null;
  documentation_match: boolean | null;
  quality_status: string;
  incidents: { total: number; unresolved: number; ready_for_confirmation: boolean };
  lines_pending_count: string[];
  ready_for_confirmation: boolean;
  items: ReconciliationItem[];
}

export interface ReceiptConfirmationRow {
  id: string;
  receipt_id: string;
  receipt_line_id: string;
  source_state: string;
  target_state: string;
  base_quantity: string;
  movement_id: string | null;
  incident_id: string | null;
  reason: string | null;
  created_by: string | null;
  created_at: string | null;
}

export interface RequisitionSummary {
  id: string;
  code: string;
  requester_id: string | null;
  cost_center_id: string | null;
  need_date: string | null;
  status: string;
}

export interface OpenItem {
  id: string;
  party_id: string;
  source_document: string | null;
  item_type: string;
  currency: string;
  original: number;
  applied: number;
  balance: number;
  due_date: string | null;
  status: string;
}

export interface PaymentSummary {
  id: string;
  party_id: string;
  direction: string;
  date: string | null;
  currency: string;
  amount: number;
  applied: number;
  status: string;
  approver_id: string | null;
  allowed_actions: AllowedActions;
}

export interface AgingResult {
  total: number;
  buckets: Record<string, number>;
}

// ---------------------------------------------------------------------------
// Ventas y cuentas por cobrar (005)
// ---------------------------------------------------------------------------
/** Reserva vista desde el pedido (Spec 030): lo que la Spec 031 recibe. */
export interface OrderLineReservation {
  id: string;
  status: string;
  quantity: string;
  base_quantity: string | null;
  warehouse_id: string;
  trigger: string | null;
  oversell: boolean;
  expires_at: string | null;
  release_reason: string | null;
}

export interface SalesOrderLine {
  id: string;
  product_id: string;
  quantity: number | string;
  unit_price: number | string;
  needs_inventory: boolean;
  presentation_id?: string | null;
  uom_id?: string | null;
  conversion_factor_snapshot?: string | null;
  base_quantity?: string | null;
  pricing_source?: string | null;
  reservations?: OrderLineReservation[];
}

/**
 * Estados del pedido (FR-030-002). `RELEASED` es la entrega a preparación;
 * `SUBMITTED` espera la decisión de crédito con la reserva ya hecha.
 */
export type SalesOrderStatus =
  | "DRAFT"
  | "SUBMITTED"
  | "RELEASED"
  | "PREPARING"
  | "SHIPPED"
  | "CLOSED"
  | "CANCELLED"
  | "REJECTED"
  | "EXPIRED";

export interface SalesOrderSummary {
  id: string;
  code: string;
  customer_id: string;
  warehouse_id: string | null;
  credit_decision: string | null;
  margin: number | null;
  currency: string;
  status: SalesOrderStatus | string;
  approval_ref: string | null;
  status_reason?: string | null;
  submitted_at?: string | null;
  released_at?: string | null;
  reservation_trigger?: string;
  eligible_for_picking?: boolean;
  quote_id?: string | null;
  allowed_actions: AllowedActions;
  lines: SalesOrderLine[];
}

/** Política de reserva de la empresa (Spec 030): el disparador es fijo. */
export interface ReservationPolicy {
  reservation_trigger: string;
  trigger_configurable: boolean;
  reservation_ttl_days: number | null;
}

/** Detalle de `409 INSUFFICIENT_AVAILABLE` al confirmar. */
export interface InsufficientLine {
  line_id: string;
  product_id: string;
  requested_base: string;
  available_base: string;
}

export interface SalesInvoiceSummary {
  id: string;
  customer_id: string;
  invoice_number: string | null;
  base_fiscal_currency: string;
  base_fiscal: number;
  tax_total: number;
  total: number;
  status: string;
  reversed_by_id: string | null;
  allowed_actions: AllowedActions;
}

export interface SalesQuoteSummary {
  id: string;
  code: string;
  customer_id: string;
  currency: string;
  status: string;
}

export interface SupplierQuoteSummary {
  id: string;
  code: string;
  supplier_id: string;
  currency: string;
  validity_until: string | null;
  status: string;
}

export interface ShipmentSummary {
  id: string;
  code: string;
  order_id: string;
  origin_warehouse_id: string;
  status: string;
  validation_status: string;
}

export interface PickListSummary {
  id: string;
  code: string;
  order_id: string;
  warehouse_id: string;
  status: string;
}

/** Un pedido esperando preparación. `position` es su puesto en la cola. */
export interface PickingQueueItem {
  position: number;
  order_id: string;
  code: string;
  customer_id: string | null;
  warehouse_id: string;
  released_at: string | null;
}

/** Ubicación de la que se puede recoger, con lo que queda asignable en ella. */
export interface PickingCandidate {
  location_id: string;
  product_id: string;
  state: string;
  lot_id: string | null;
  serial_id: string | null;
  on_hand: string;
  allocatable: string;
  sequence: number;
}

/** Lo que una línea del pedido exige, tiene asignado y le falta. */
export interface PickingDemand {
  order_line_id: string;
  product_id: string;
  required_base_quantity: string;
  allocated_base_quantity: string;
  remaining_base_quantity: string;
  /** Lo efectivamente preparado, presente tras la ejecución (Spec 032). */
  prepared_base_quantity?: string;
}

/** Un paso del recorrido: de esta ubicación, esta cantidad. */
export interface PickingRouteStep {
  id: string;
  sequence: number | null;
  location_id: string;
  order_line_id: string | null;
  product_id: string;
  state: string | null;
  lot_id: string | null;
  serial_id: string | null;
  base_quantity: string;
}

/** Una parada del recorrido con lo planificado y lo recogido de verdad. */
export interface PickingStep {
  id: string;
  sequence: number | null;
  order_line_id: string;
  location_id: string;
  product_id: string;
  lot_id: string | null;
  serial_id: string | null;
  planned_base_quantity: string;
  picked_base_quantity: string | null;
  difference: string | null;
  discrepancy_kind: string | null;
  discrepancy_note: string | null;
  picked_at: string | null;
  picked_by: string | null;
}

/** Los cinco motivos de diferencia del proceso fuente (¶48-52). */
export const PICK_DISCREPANCY_KINDS = [
  "PRODUCTO_NO_LOCALIZADO",
  "CANTIDAD_INSUFICIENTE",
  "UBICACION_INCORRECTA",
  "DIFERENCIA_SISTEMA_FISICO",
  "MERCANCIA_DANADA",
] as const;

/** Un pedido preparado esperando el control independiente. */
export interface PendingConfirmation {
  order_id: string;
  code: string;
  customer_id: string | null;
  warehouse_id: string;
  status: string;
  updated_at: string | null;
}

/** Una línea del pedido con lo requerido y lo que la preparación dejó. */
export interface ConfirmationWorksheetLine {
  order_line_id: string;
  product_id: string;
  presentation_id: string | null;
  conversion_factor_snapshot: string | null;
  quantity: string;
  required_base_quantity: string;
  prepared_base_quantity: string;
}

export interface ConfirmationAttempt {
  id: string;
  attempt: number;
  status: string;
  checked_by: string | null;
  checked_at: string | null;
  notes: string | null;
}

export interface ConfirmationWorksheet {
  order_id: string;
  code: string;
  status: string;
  picklist_id: string;
  warehouse_id: string;
  consolidation_location_id: string | null;
  prepared_by: string[];
  same_user_allowed: boolean;
  attempts: ConfirmationAttempt[];
  lines: ConfirmationWorksheetLine[];
}

/** El resultado del control: las tres cifras y en qué dimensión falló. */
export interface ConfirmationResultLine {
  order_line_id: string | null;
  product_id: string;
  required_base_quantity: string;
  prepared_base_quantity: string;
  checked_base_quantity: string;
  presentation_id: string | null;
  presentation_ok: boolean;
  condition_ok: boolean;
  conforms: boolean;
  difference_kind: string | null;
  note: string | null;
}

export interface ConfirmationResult {
  id: string;
  order_id: string;
  picklist_id: string;
  attempt: number;
  status: string;
  checked_by: string | null;
  checked_at: string | null;
  notes: string | null;
  lines: ConfirmationResultLine[];
}

/** Un pedido confirmado esperando su factura, o ya liberado. */
export interface BillableOrder {
  order_id: string;
  code: string;
  customer_id: string | null;
  status: string;
  currency: string | null;
  billing_requested_at: string | null;
}

export interface BillingInvoiceLine {
  product_id: string;
  quantity: string;
  unit_price: string;
  base_quantity: string | null;
  presentation_id: string | null;
  conversion_factor_snapshot: string | null;
  tax_amount: string;
  base_fiscal: string;
  total: string;
}

export interface BillingInvoice {
  id: string;
  status: string;
  order_id: string | null;
  confirmation_id: string | null;
  customer_id: string;
  currency: string;
  base_fiscal: string;
  tax_total: string;
  total: string;
  invoice_number: string | null;
  control_number: string | null;
  fiscal_document_id: string | null;
  issued_at: string | null;
  lines_without_tax: number;
  lines: BillingInvoiceLine[];
}

/** Lo que el despacho necesita saber antes de dejar salir la mercancía. */
export interface OrderBillingStatus {
  order_id: string;
  order_status: string;
  invoiced: boolean;
  invoice: BillingInvoice | null;
}

/**
 * Spec 035 · un pedido facturado esperando su salida física.
 *
 * La cola no la forma el estado del pedido por sí solo: se muestra la factura
 * que lo respalda, porque el ¶103 exige que exista y esté **emitida**.
 */
export interface DispatchableOrder {
  order_id: string;
  code: string;
  status: string;
  invoice_id: string | null;
  invoice_number: string | null;
  invoice_status: string | null;
  shipment_id: string | null;
  shipment_code: string | null;
  shipment_status: string | null;
}

export interface DispatchLine {
  product_id: string;
  quantity: string;
  base_quantity: string | null;
  presentation_id: string | null;
  conversion_factor_snapshot: string | null;
  lot_id: string | null;
  serial_id: string | null;
}

export interface Dispatch {
  id: string;
  code: string;
  order_id: string;
  origin_warehouse_id: string;
  status: string;
  validation_status: string;
  /** `CLEARED` o `BLOCKED`; nulo mientras nadie haya validado. */
  regulatory_status: string | null;
  invoice_id: string | null;
  destination: string | null;
  transport: string | null;
  vehicle_id: string | null;
  driver_id: string | null;
  validated_at: string | null;
  validated_by: string | null;
  dispatched_at: string | null;
  dispatched_by: string | null;
  lines: DispatchLine[];
}

export interface OrderDispatchStatus {
  order_id: string;
  order_status: string;
  shipment: Dispatch | null;
}

/**
 * Spec 036 · lo que se puede devolver de una factura.
 *
 * El tope no lo calcula la pantalla: «no ajustar por encima de cantidades/base/
 * IVA pendientes del original» es una resta que solo el backend, que ve todas
 * las devoluciones, puede hacer.
 */
export interface ReturnEligibilityLine {
  invoice_line_id: string;
  product_id: string;
  quantity: string;
  dispatched_base_quantity: string;
  returned_base_quantity: string;
  returnable_base_quantity: string;
  presentation_id: string | null;
  conversion_factor_snapshot: string | null;
}

export interface ReturnEligibility {
  invoice_id: string;
  invoice_status: string;
  invoice_number: string | null;
  control_number: string | null;
  order_id: string | null;
  customer_id: string;
  shipment_id: string | null;
  dispatched: boolean;
  lines: ReturnEligibilityLine[];
}

export interface SalesReturnLine {
  id: string;
  product_id: string;
  invoice_line_id: string | null;
  quantity: string;
  base_quantity: string;
  accepted_base_quantity: string | null;
  /** `DISPONIBLE` o `RECHAZADO`; nulo mientras nadie haya verificado. */
  disposition: string | null;
  condition: string;
  lot_id: string | null;
  serial_id: string | null;
  presentation_id: string | null;
  conversion_factor_snapshot: string | null;
}

export interface SalesReturnDetail {
  id: string;
  code: string;
  status: string;
  status_reason: string | null;
  reason: string;
  invoice_id: string | null;
  order_id: string | null;
  shipment_id: string | null;
  customer_id: string | null;
  warehouse_id: string | null;
  location_id: string | null;
  requested_at: string | null;
  received_at: string | null;
  inspected_at: string | null;
  approved_at: string | null;
  reentered_at: string | null;
  lines: SalesReturnLine[];
}

export interface CreditEligibilityLine {
  invoice_line_id: string;
  product_id: string;
  quantity: string;
  credited_quantity: string;
  creditable_quantity: string;
  unit_price: string;
  base_fiscal: string;
  tax_amount: string;
}

export interface CreditEligibility {
  invoice_id: string;
  invoice_status: string;
  invoice_number: string | null;
  control_number: string | null;
  issued_at: string | null;
  customer_id: string;
  currency: string;
  creditable: boolean;
  lines: CreditEligibilityLine[];
}

export interface SalesNoteLine {
  invoice_line_id: string | null;
  product_id: string | null;
  quantity?: string;
  unit_price?: string;
  base_quantity?: string | null;
  concept?: string;
  base_fiscal: string;
  tax_amount: string;
  total: string;
}

/**
 * Spec 037 · el saldo del cliente, con sus sumandos a la vista.
 *
 * «Saldo = documentos + débitos − cobros − retenciones − créditos». Lo calcula
 * el backend con el motor compartido: la pantalla no hace aritmética monetaria.
 */
export interface CustomerBalance {
  customer_id: string;
  documents: string;
  applied: string;
  outstanding: string;
  credits: string;
  credit_applied: string;
  /** Reservado para devolver en efectivo (Spec 038): ya no es imputable. */
  credit_refund_reserved: string;
  /** Ya devuelto en efectivo: ni imputable ni debido. */
  credit_refunded: string;
  /** Lo **imputable** a documentos, no lo que se debe. Son cifras distintas. */
  credit_available: string;
  balance: string;
}

export interface StatementEntry {
  type: string;
  id: string;
  reference: string | null;
  date: string | null;
  currency: string;
  debit: string;
  credit: string;
  outstanding?: string;
  available?: string;
  status: string;
}

export interface CustomerStatement extends CustomerBalance {
  entries: StatementEntry[];
}

/** Un crédito del cliente con importe todavía sin aplicar. */
export interface CustomerCredit {
  id: string;
  number: string;
  control_number: string | null;
  cause: string | null;
  invoice_id: string | null;
  currency: string;
  amount: string;
  applied: string;
  refund_reserved: string;
  refunded: string;
  available: string;
  issued_at: string | null;
}

export interface CreditApplicationRow {
  id: string;
  source_type: string;
  source_id: string;
  target_open_item_id: string;
  amount: string;
  currency: string;
  rate: string | null;
  date: string | null;
  status: string;
  created_at: string | null;
}

export interface CreditApplicationResult {
  target_open_item_id: string;
  target_outstanding: string;
  target_status: string;
  credit_remaining: string;
  currency: string;
}

export interface SalesNote {
  id: string;
  status: string;
  cause: string | null;
  invoice_id: string | null;
  return_id?: string | null;
  customer_id: string;
  currency: string;
  base_fiscal: string;
  tax_total: string;
  total: string;
  applied?: string;
  invoice_number: string | null;
  control_number: string | null;
  fiscal_document_id: string | null;
  issued_at: string | null;
  lines: SalesNoteLine[];
}

export interface PickingPlan {
  id: string;
  code: string;
  order_id: string;
  warehouse_id: string;
  status: string;
  status_reason: string | null;
  confirmed_at: string | null;
  cancelled_at: string | null;
  invalidated_at: string | null;
  remaining_base_quantity: string;
  confirmable: boolean;
  demand: PickingDemand[];
  route: PickingRouteStep[];
  /** Presentes cuando el plan ya se está preparando (Spec 032). */
  picking?: PickingStep[];
  has_discrepancy?: boolean;
  route_complete?: boolean;
  consolidation_location_id?: string | null;
  consolidated_at?: string | null;
}

export interface ReturnSummary {
  id: string;
  code: string;
  source_document: string | null;
  reason: string;
  condition: string;
  inventory_destination: string;
  status: string;
}

export interface CreditNoteSummary {
  id: string;
  number: string;
  party_id: string;
  invoice_ref: string | null;
  amount: number;
  applied: number;
  currency: string;
  status: string;
}

export interface DebitNoteSummary {
  id: string;
  number: string;
  customer_id: string;
  invoice_ref: string | null;
  amount: number;
  currency: string;
  status: string;
}

export interface AdvanceSummary {
  id: string;
  party_id: string;
  direction: string;
  currency: string;
  amount: number;
  available: number;
  status: string;
}

export interface ScheduleSummary {
  id: string;
  party_id: string;
  due_date: string | null;
  amount: number;
  status: string;
}

// ---------------------------------------------------------------------------
// Tesorería (006-tesoreria)
// ---------------------------------------------------------------------------
export interface FinancialBankSummary {
  id: string;
  code: string;
  name: string;
  swift: string | null;
  country: string | null;
  status: string;
}

export interface FinancialAccountSummary {
  id: string;
  code: string;
  name: string;
  bank_id: string;
  currency: string;
  status: string;
}

export interface CashboxSummary {
  id: string;
  code: string;
  name: string;
  currency: string;
  warehouse_id: string | null;
  status: string;
}

export interface PaymentMethodSummary {
  id: string;
  code: string;
  name: string;
  kind: string;
  status: string;
}

export interface TreasuryInstrumentSummary {
  id: string;
  code: string;
  name: string;
  method_id: string;
  cashbox_id: string | null;
  account_id: string | null;
  status: string;
}

export interface CurrencySummary {
  id: string;
  code: string;
  name: string | null;
  symbol: string | null;
  decimal_places: number;
  status: string;
}

export interface CashSessionMovement {
  id: string;
  movement_type: string;
  payment_id: string | null;
  /** Texto decimal exacto con dos decimales (Spec 038 · FLOAT-038-B). */
  amount: string;
  instrument_id: string | null;
  reference: string | null;
}

/** Sesión de caja: todos sus importes son texto decimal exacto (Spec 038 · FLOAT-038-B). Nunca `Number`. */
export interface CashSessionSummary {
  id: string;
  cashbox_id: string;
  opened_by: string | null;
  opened_at: string | null;
  closed_at: string | null;
  opened_amount: string;
  counted_amount: string | null;
  expected_amount: string;
  /** Contado − esperado: positiva si sobra, negativa si falta. */
  difference: string | null;
  status: string;
  approval_note: string | null;
  allowed_actions: AllowedActions;
  movements: CashSessionMovement[];
}

export interface BankTransactionSummary {
  id: string;
  account_id: string;
  txn_date: string | null;
  value_date: string | null;
  direction: string;
  /** Texto decimal exacto con dos decimales (Spec 038 · FLOAT-038-A). Nunca `Number`. */
  amount: string;
  currency: string;
  reference: string | null;
  source: string;
  payment_id: string | null;
  /** Texto decimal exacto con dos decimales, o `null`. */
  commission: string | null;
  status: string;
}

export interface TreasuryTransferSummary {
  id: string;
  from_cashbox_id: string | null;
  from_account_id: string | null;
  to_cashbox_id: string | null;
  to_account_id: string | null;
  /** Texto decimal exacto (Spec 038 · FLOAT-038-C). */
  amount: string;
  currency: string;
  value_date: string | null;
  reference: string | null;
  status: string;
}

export interface ReconciliationLineSummary {
  id: string;
  bank_transaction_id: string | null;
  system_movement_id: string | null;
  system_movement_type: string | null;
  match_score: number | null;
  matched_by: string;
  status: string;
  resolution: string | null;
  notes: string | null;
}

export interface ReconciliationSummary {
  id: string;
  account_id: string;
  statement_date: string | null;
  statement_ref: string | null;
  /** Texto decimal exacto, con signo si el saldo está en descubierto (FLOAT-038-C). */
  opening_balance: string | null;
  closing_balance: string | null;
  status: string;
  approved_by: string | null;
  approved_at: string | null;
  allowed_actions: AllowedActions;
  lines: ReconciliationLineSummary[];
}

export interface FiscalRuleSummary {
  id: string;
  rule_code: string;
  name: string | null;
  rule_type: string;
  version: string;
  effective_from: string | null;
  effective_to: string | null;
  params: string | null;
  status: string;
}

export interface IgftEventSummary {
  id: string;
  event_type: string;
  source_document: string | null;
  /** Texto decimal exacto (Spec 038 · FLOAT-038-C). */
  amount: string;
  currency: string;
  rate_snapshot: number | null;
  igft_amount: string | null;
  rule_id: string | null;
  evaluated_at: string | null;
  status: string;
}

export interface ExecutionResult {
  execution_id: string;
  kind: string;
  idempotent: boolean;
  amount: number;
  currency: string;
}

// ---------------------------------------------------------------------------
// Núcleo fiscal (007-nucleo-fiscal)
// ---------------------------------------------------------------------------
export interface LegalSourceSummary {
  id: string;
  authority: string;
  source_type: string;
  number: string | null;
  gazette: string | null;
  status: string;
}

export interface TaxRuleSummary {
  id: string;
  tax_code: string;
  version: number;
  effective_from: string | null;
  effective_to: string | null;
  rate: unknown;
  fiscal_release: string | null;
  status: string;
}

export interface NumberSeriesSummary {
  id: string;
  establishment_id: string | null;
  document_type: string;
  prefix: string | null;
  next_number: number;
  validity: unknown;
}

export interface ControlBatchSummary {
  id: string;
  establishment_id: string | null;
  printer: string | null;
  range_from: string;
  range_to: string;
  status: string;
  counts: unknown;
}

export interface ControlNumberSummary {
  id: string;
  batch_id: string;
  value: string;
  state: string;
  document_ref: string | null;
}

export interface FiscalDocumentSummary {
  id: string;
  business_document: string;
  document_type: string;
  series: string | null;
  invoice_number: string | null;
  control_number: string | null;
  fiscal_currency: string;
  emitted_at: string | null;
  hash: string | null;
  status: string;
}

export interface FiscalDocumentDetail extends FiscalDocumentSummary {
  exchange_rate_snapshot: number | null;
  prints: Array<{
    id: string;
    copy_type: string;
    printer: string | null;
    user_id: string | null;
    printed_at: string | null;
    reason: string | null;
  }>;
}

export interface CreditDebitNoteSummary {
  id: string;
  original_document: string;
  note_type: string;
  cause: string;
  amount: number;
  status: string;
}

export interface WithholdingRuleSummary {
  id: string;
  tax_type: string;
  code: string;
  concept: string | null;
  rate: number;
  minimum: number | null;
  subtractor: number | null;
  status: string;
}

export interface WithholdingSummary {
  id: string;
  party_id: string;
  tax_type: string;
  rule_ref: string | null;
  base: number;
  amount: number;
  period: string | null;
  certificate: string | null;
  status: string;
}

export interface FiscalPeriodSummary {
  id: string;
  tax_type: string;
  period_key: string;
  start: string | null;
  end: string | null;
  status: string;
  approvals: unknown;
}

export interface TaxReturnBatchSummary {
  id: string;
  tax_type: string;
  period: string;
  status: string;
}

export interface BookRow {
  document?: string;
  number?: string | null;
  series?: string | null;
  control?: string | null;
  total?: number;
  bolivares?: number;
  amount?: number;
  igft_amount?: number;
  base?: number;
  [key: string]: unknown;
}

export interface BookResult {
  tax_type: string;
  period: string;
  count: number;
  total: number;
  rows: BookRow[];
}

// ---------------------------------------------------------------------------
// Regulación y traslados (008-regulacion-traslados)
// ---------------------------------------------------------------------------
export interface RegulatoryAuthoritySummary {
  id: string;
  code: string;
  name: string;
  validation_method: string | null;
  status: string;
}

export interface PermitTypeSummary {
  id: string;
  authority_id: string;
  code: string;
  name: string;
  scope: string | null;
  status: string;
}

export interface OfficialRegistrationSummary {
  id: string;
  authority_id: string;
  scope: string;
  ref_number: string;
  expires_at: string | null;
  status: string;
}

export interface RegulatoryProfileSummary {
  id: string;
  operation: string;
  product_id: string | null;
  rubric_id: string | null;
  required_documents: string | null;
  version: string;
  status: string;
}

export interface TransportVehicleSummary {
  id: string;
  plate: string;
  vehicle_type: string | null;
  capacity: number | null;
  owner_party_id: string | null;
  status: string;
}

export interface TransportDriverSummary {
  id: string;
  party_id: string;
  license: string | null;
  status: string;
}

export interface PermitInstanceSummary {
  id: string;
  permit_type_id: string;
  number: string;
  expires_at: string | null;
  hash: string | null;
  verification: string | null;
  status: string;
}

export interface OfficialDocumentSummary {
  id: string;
  kind: string;
  number: string;
  organism: string | null;
  expires_at: string | null;
  hash: string | null;
  verification: string | null;
  status: string;
}

export interface RegulatoryEvaluationSummary {
  id: string;
  shipment_id: string;
  shipment_line_ref: string | null;
  required: string | null;
  blockers: string | null;
  override: string | null;
  status: string;
}

export interface RegulatoryContingencySummary {
  id: string;
  rule_ref: string;
  reason: string;
  allowed_by: string | null;
  status: string;
}

export interface ApprovalRequestSummary {
  id: string;
  object_ref: string;
  rule_ref: string | null;
  risk: string | null;
  amount: number | null;
  status: string;
  decision: string | null;
}

export interface EvaluationResult {
  shipment_id: string;
  evaluated: number;
  blocked: number;
  status: string;
}

// ---------------------------------------------------------------------------
// Reportes y auditoría (009-reportes-auditoria)
// ---------------------------------------------------------------------------
export interface DashboardResult {
  indicators: {
    ventas: number;
    compras: number;
    tesoreria_banco: number;
    cxc: number;
    cxp: number;
    documentos_fiscales: number;
    despachos_bloqueados: number;
  };
  vencimientos: {
    open_items_vencidos: number;
    periodos_fiscales_abiertos: number;
    permisos_activos: number;
  };
}

export interface ReportResult {
  report_key: string;
  count: number;
  total: number;
  period?: string;
  base?: number;
  tax?: number;
  rows: Array<Record<string, unknown>>;
  [key: string]: unknown;
}

export interface ReportExportSummary {
  id: string;
  report_key: string;
  format: string;
  file_ref: string | null;
  exported_by: string | null;
  exported_at: string | null;
  status: string;
}

export interface ReportJobSummary {
  id: string;
  report_key: string;
  status: string;
  error: string | null;
  result_ref: string | null;
}

export interface AuditTimelineItem {
  id: string;
  action: string;
  entity_type: string;
  entity_id: string | null;
  user_id: string | null;
  source: string | null;
  reason: string | null;
  event_time: string | null;
}

/* -------------------------------------------------------------------------- */
/* Licenciamiento central (010)                                                */
/* -------------------------------------------------------------------------- */

export interface CentralConfig {
  id: string;
  server_url: string;
  public_key: string | null;
  sync_policy: Record<string, unknown>;
  grace_days: number;
  enabled: boolean;
  status: string;
  updated_at: string;
}

export interface SyncRunSummary {
  id: string;
  status: "SUCCESS" | "FAILED";
  request: Record<string, unknown> | null;
  response: Record<string, unknown> | null;
  error: string | null;
  ran_at: string;
}

export interface EntitlementSnapshotSummary {
  id: string;
  modules: Record<string, boolean>;
  version: string;
  taken_at: string;
}

export interface EntitlementsResult {
  modules: Record<string, boolean>;
  version: string;
  taken_at: string | null;
}

export interface OfflineStatus {
  offline_valid: boolean;
  reason: string;
  grace_days: number;
  grace_days_left: number;
  grace_end: string | null;
  last_reliable_date: string | null;
}

export interface RenewalRequestSummary {
  id: string;
  payment_proof_ref: string | null;
  status: "REPORTED" | "VERIFIED" | "ISSUED" | "REJECTED";
  notes: string | null;
  created_by: string | null;
  created_at: string;
}

export interface LicensingOverview {
  status: LicenseStatus;
  central_config: CentralConfig | null;
  entitlements: EntitlementsResult;
  offline: OfflineStatus;
  last_sync: SyncRunSummary | null;
  modules: string[];
}

export interface LicenseEventItem {
  id: string;
  event_type: string;
  detail: Record<string, unknown> | null;
  source: string;
  created_at: string;
}

/* -------------------------------------------------------------------------- */
/* Homologación y liberación (011)                                             */
/* -------------------------------------------------------------------------- */

export type HomologationStatus = "DRAFT" | "SUBMITTED" | "APPROVED" | "REJECTED";

export interface HomologationRecordSummary {
  id: string;
  fiscal_version: string;
  modality: string;
  formal_act_ref: string | null;
  evidence_sha256: string | null;
  status: HomologationStatus;
  homologated: boolean;
  evaluated_by: string | null;
  evaluated_at: string | null;
  notes: string | null;
  created_by: string | null;
  created_at: string;
}

export interface HomologationEventItem {
  id: string;
  event_type: string;
  detail: Record<string, unknown> | null;
  created_by: string | null;
  created_at: string;
}

export interface HomologationRecordDetail extends HomologationRecordSummary {
  events: HomologationEventItem[];
}

export type ReleaseStatus = "DRAFT" | "CANDIDATE" | "RELEASED" | "BLOCKED";

export interface ReleaseVersionSummary {
  id: string;
  version: string;
  changelog: Record<string, unknown>;
  gates: Record<string, unknown>;
  homologation_id: string | null;
  status: ReleaseStatus;
  blocked_reasons: { reasons?: string[] } | null;
  released_by: string | null;
  released_at: string | null;
  notes: string | null;
  created_by: string | null;
  created_at: string;
}

export interface HomologationTimelineItem {
  id: string;
  source: "HOMOLOGATION" | "RELEASE";
  event_type: string;
  detail: Record<string, unknown> | null;
  entity_id: string | null;
  created_by: string | null;
  created_at: string;
}


/* -------------------------------------------------------------------------- */
/* Motor de aprobaciones (Spec 045)                                           */
/* -------------------------------------------------------------------------- */
export type ApprovalRequestStatus =
  | "DRAFT" | "PENDING" | "IN_REVIEW" | "APPROVED" | "REJECTED"
  | "RETURNED" | "CANCELLED" | "OBSOLETE";

export type ApprovalStepStatus =
  | "PENDING" | "IN_REVIEW" | "APPROVED" | "REJECTED" | "RETURNED" | "EXPIRED" | "SKIPPED";

export type ApprovalPolicyStatus = "DRAFT" | "ACTIVE" | "CLOSED";

export interface ApprovalCondition {
  field: string;
  operator: string;
  value?: unknown;
}

export interface ApprovalLevelSummary {
  id?: string;
  level_order: number;
  resolver_type: "ROLE" | "USER" | "SCOPE_OWNER";
  resolver_ref: string;
  quorum_type: "ANY" | "ALL" | "N_OF_M";
  quorum_n: number | null;
  can_delegate?: boolean;
  sla_hours: number | null;
}

export interface ApprovalRuleSummary {
  id: string;
  name: string;
  sequence: number;
  conditions: ApprovalCondition[];
  condition_fields: string[];
  is_exception: boolean;
  risk_class: string | null;
  levels: ApprovalLevelSummary[];
}

export interface ApprovalPolicySummary {
  id: string;
  company_id: string;
  process_type: string;
  code: string;
  name: string;
  version: number;
  status: ApprovalPolicyStatus;
  valid_from: string | null;
  valid_to: string | null;
  requires_segregation: boolean;
  allow_self_approval: boolean;
  distinct_actors_across_levels: boolean;
  base_currency: string;
  rules: ApprovalRuleSummary[];
  allowed_actions: string[];
}

export interface ApprovalInboxItem {
  step_id: string;
  request_id: string;
  process_type: string;
  document_type: string;
  document_id: string;
  level_order: number;
  quorum_type: string;
  amount_base: number | null;
  base_currency: string | null;
  requested_by: string | null;
  requested_at: string | null;
  due_at: string | null;
  overdue: boolean;
  step_version: number;
  allowed_actions: string[];
}

export interface ApprovalDecisionSummary {
  actor_id: string;
  decision: "APPROVE" | "REJECT" | "RETURN" | "CANCEL";
  reason: string | null;
  observations: string | null;
  decided_at: string | null;
  on_behalf_of_id: string | null;
}

export interface ApprovalStepSummary {
  id: string;
  level_order: number;
  status: ApprovalStepStatus;
  quorum_type: string;
  quorum_n: number | null;
  eligible_actors: string[];
  due_at: string | null;
  version: number;
  decisions: ApprovalDecisionSummary[];
}

export interface ApprovalRequestDetail {
  id: string;
  status: ApprovalRequestStatus;
  process_type: string;
  policy_id: string | null;
  policy_version: string;
  amount_base: number | null;
  base_currency: string | null;
  requested_by: string | null;
  requested_at: string | null;
  resolved_at: string | null;
  resolution_reason: string | null;
  previous_request_id: string | null;
  fingerprint_fields: string[];
  steps: ApprovalStepSummary[];
  allowed_actions: string[];
}

export interface ApprovalDocumentStatus {
  document: string;
  requests: ApprovalRequestDetail[];
  current: ApprovalRequestDetail | null;
  is_approved: boolean;
  blocks_advance: boolean;
}

export interface ApprovalDelegationSummary {
  id: string;
  grantor_id: string;
  grantee_id: string;
  scope_process_type: string | null;
  valid_from: string | null;
  valid_to: string | null;
  reason: string | null;
  is_temporary_substitution: boolean;
  revoked_at: string | null;
  status: "ACTIVE" | "REVOKED";
}

// --------------------------------------------------------------------------- //
// Tesorería — Spec 038: política cambiaria, conversión y reembolso
// --------------------------------------------------------------------------- //

/** Una versión de política cambiaria. Se sustituye, no se edita. */
export interface FxPolicy {
  id: string;
  policy_code: string;
  version: number;
  functional_currency: string;
  effective_date_basis: string;
  rate_source: string | null;
  rate_type: string | null;
  allow_cross_currency: boolean;
  allow_manual_rate: boolean;
  allow_refund: boolean;
  authority_reference: string | null;
  effective_from: string;
  effective_to: string | null;
  status: "DRAFT" | "ACTIVE" | "SUPERSEDED";
}

/**
 * Una conversión ejecutada, con la procedencia de su tasa.
 *
 * `rate_origin` distingue la tasa registrada de la que tecleó una persona: sin
 * ese dato no se puede auditar a qué cambio se movió el dinero.
 */
export interface FxConversion {
  id: string;
  status: string;
  source_account_id: string;
  target_account_id: string;
  source_currency: string;
  target_currency: string;
  source_amount: string;
  target_amount: string;
  exchange_difference: string | null;
  rate: string | null;
  rate_source: string | null;
  rate_date: string | null;
  rate_origin: string | null;
  policy_version: number | null;
}

/** Un reembolso: solicitado, decidido y ejecutado son tres actos distintos. */
export interface TreasuryRefund {
  id: string;
  status: "REQUESTED" | "APPROVED" | "REJECTED" | "SETTLED" | "CANCELLED";
  status_reason: string | null;
  customer_id: string;
  credit_note_id: string;
  currency: string;
  amount: string;
  account_id: string | null;
  movement_id: string | null;
  reason: string | null;
  requested_at: string | null;
  approved_at: string | null;
  settled_at: string | null;
}

export interface CashPositionAccount {
  account_id: string;
  code: string;
  name: string;
  currency: string;
  balance: string;
  status: string;
}

/** Por cuenta y por moneda. **Sin total**: sumar monedas exige convertirlas. */
export interface CashPosition {
  accounts: CashPositionAccount[];
  by_currency: { currency: string; balance: string }[];
}

// --------------------------------------------------------------------------- //
// Maestros financieros — Spec 013: la autoridad de la tasa
// --------------------------------------------------------------------------- //

/** De dónde viene una tasa. `source_type` es del maestro, no del código. */
export interface RateSource {
  id: string;
  code: string;
  name: string;
  source_type: string;
  authority_reference: string | null;
  provider_code: string | null;
  allows_manual: boolean;
  priority: number;
  status: "ACTIVE" | "DISABLED";
  effective_from: string | null;
  effective_to: string | null;
  /** Salud del canal, no una cotización: confundirlos haría pasar un error de red por una tasa. */
  last_sync_at: string | null;
  last_success_at: string | null;
  last_error: string | null;
}

/**
 * Cómo se **resuelve** una tasa.
 *
 * Distinta de la política cambiaria de la Spec 038, que decide si se puede
 * convertir: ésta decide de dónde sale el número.
 */
export interface RatePolicy {
  id: string;
  policy_code: string;
  version: number;
  allow_inversion: boolean;
  allow_triangulation: boolean;
  triangulation_currency: string | null;
  max_age_days: number | null;
  carry_forward: boolean;
  require_rate_approval: boolean;
  rate_scale: number;
  authority_reference: string | null;
  status: "DRAFT" | "ACTIVE" | "SUPERSEDED";
  effective_from: string;
  effective_to: string | null;
}

/** Una cotización con su par explícito: **1 base = `rate` quote**. */
export interface RateObservation {
  id: string;
  base_currency: string | null;
  quote_currency: string | null;
  rate: string;
  rate_type: string;
  status: string;
  version: number;
  source_id: string | null;
  source_code: string | null;
  effective_at: string | null;
  published_at: string | null;
  observed_at: string | null;
  supersedes_id: string | null;
  import_batch_id: string | null;
  provider_observation_id: string | null;
  source_reference: string | null;
  reason: string | null;
  entered_by: string | null;
  approved_by: string | null;
}

/** El resultado de resolver, nunca un número pelado. */
export interface RateResolution {
  base_currency: string;
  quote_currency: string;
  rate: string;
  /** «1 USD = 100 VES», escrito, porque `USD/VES` a secas no dice nada. */
  meaning: string;
  observation_id: string | null;
  source_code: string | null;
  rate_type: string | null;
  effective_at: string | null;
  published_at: string | null;
  observed_at: string | null;
  version: number | null;
  status: string | null;
  identity: boolean;
  /** `INVERSE` o `TRIANGULATION` cuando el número no salió de una fila tal cual. */
  derived: string | null;
  derived_from: string[];
}

export interface RateImportResult {
  batch_id: string;
  rows: number;
  imported: number;
  rejected: number;
  status: string;
  errors: { row: number; code: string; message: string; value: Record<string, string> }[];
}

export interface RateImportBatch {
  id: string;
  filename: string | null;
  status: string;
  rows: number;
  imported: number;
  rejected: number;
  source_id: string;
  rate_type: string | null;
  created_at: string | null;
}
