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

export interface HealthResponse {
  status: "ok" | "degraded";
  services: Record<string, string>;
  version: string;
}
