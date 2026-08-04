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
