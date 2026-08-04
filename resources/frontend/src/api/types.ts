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
  created_at: string;
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

