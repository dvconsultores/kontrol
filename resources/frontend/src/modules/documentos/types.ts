/** Tipos de gestión documental (Spec 046).
 *
 * El cliente conoce documentos, no almacenamiento: ninguna respuesta trae
 * `storage_key`, proveedor ni ruta, y este archivo no los declara.
 */

export const DOCUMENT_STATUSES = [
  "DRAFT", "ACTIVE", "SUPERSEDED", "ARCHIVED", "REVOKED",
] as const;
export type DocumentStatus = (typeof DOCUMENT_STATUSES)[number];

export const STATUS_LABEL: Record<string, string> = {
  DRAFT: "Borrador",
  ACTIVE: "Activo",
  SUPERSEDED: "Reemplazado",
  ARCHIVED: "Archivado",
  REVOKED: "Anulado",
};

/** Estado de seguridad del archivo, **distinto** del estado del documento. */
export const SECURITY_LABEL: Record<string, string> = {
  PENDING_SCAN: "Verificando",
  CLEAN: "Verificado",
  INFECTED: "Rechazado",
  SCAN_FAILED: "Sin verificar",
  SKIPPED: "Sin analizar",
};

export interface StoredFileInfo {
  original_name: string;
  mime_type: string;
  declared_mime?: string | null;
  detected_mime?: string | null;
  size: number;
  sha256?: string;
  /** Siempre presente: si es `SKIPPED`, el archivo no se analizó. */
  security_status: string;
}

export interface DocumentVersionInfo {
  id: string;
  version_number: number;
  sha256: string;
  status: string;
  replacement_reason: string | null;
  created_at: string | null;
  file: StoredFileInfo | null;
}

export interface DocumentLinkInfo {
  id: string;
  resource_type: string;
  resource_id: string;
  role: string;
  is_frozen: boolean;
  frozen_version_id: string | null;
}

export interface DocumentSummary {
  id: string;
  company_id: string;
  document_type_id: string;
  title: string;
  document_number: string | null;
  issuer: string | null;
  issued_at: string | null;
  expiration_date: string | null;
  /** Derivado del vencimiento; no es un estado persistido. */
  is_expired: boolean;
  status: string;
  is_managed: boolean;
  external_url: string | null;
  version: number;
  current_version: {
    id: string;
    version_number: number;
    sha256: string;
    file: StoredFileInfo | null;
  } | null;
  can_delete: boolean;
  delete_blocked_by: Record<string, unknown> | null;
  allowed_actions: string[];
  description?: string | null;
  metadata?: Record<string, unknown> | null;
  links?: DocumentLinkInfo[];
  /** Presente solo al consultar por recurso: el vínculo por el que aparece. */
  link?: ResourceLinkInfo;
}

/** Vínculo tal como viaja en `/documentos/por-recurso/…`: sin repetir el
 *  recurso, que ya es el de la consulta. */
export interface ResourceLinkInfo {
  id: string;
  role: string;
  is_frozen: boolean;
  frozen_version_id: string | null;
}

export interface DocumentTypeInfo {
  id: string;
  company_id: string;
  category_id: string | null;
  code: string;
  name: string;
  allowed_mime_types: string[];
  allowed_extensions: string[];
  max_size_bytes: number | null;
  versioning_policy: string;
  requires_expiration: boolean;
  audit_downloads: boolean;
  scan_required: boolean;
  inline_preview_mimes: string[];
  status: string;
  version: number;
}

export interface Paged<T> {
  total: number;
  limit: number;
  offset: number;
  items: T[];
}

export function can(entity: { allowed_actions: string[] }, action: string): boolean {
  return entity.allowed_actions.includes(action);
}

/** Tamaño legible. Nunca oculta la magnitud real. */
export function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** Trunca por el centro: un nombre largo no debe ensanchar la tabla, pero su
 *  extensión sigue siendo visible porque es lo que identifica el archivo. */
export function truncateName(name: string, max = 42): string {
  if (name.length <= max) return name;
  const keep = Math.floor((max - 1) / 2);
  return `${name.slice(0, keep)}…${name.slice(-keep)}`;
}

/** Traduce el error del backend a un mensaje accionable.
 *
 * Nunca «error desconocido»: cada causa tiene su explicación y su salida. */
export function uploadErrorMessage(err: unknown): string {
  const code = (err as { code?: string })?.code;
  const details = (err as { details?: Record<string, unknown> })?.details;
  switch (code) {
    case "FILE_TOO_LARGE":
      return `El archivo supera el tamaño máximo permitido (${
        formatSize(Number(details?.max_size_bytes ?? 0))}).`;
    case "MIME_NOT_ALLOWED":
      return `Este tipo documental no admite archivos de ese formato. Admitidos: ${
        ((details?.allowed as string[]) ?? []).join(", ") || "ninguno declarado"}.`;
    case "MIME_MISMATCH":
      return "El contenido del archivo no corresponde con el formato que declara.";
    case "FILE_INFECTED":
      return "El archivo fue identificado como malicioso y no se guardó.";
    case "SCAN_FAILED":
      return "No se pudo verificar la seguridad del archivo. Inténtelo de nuevo más tarde.";
    case "FILE_EMPTY":
      return "El archivo está vacío.";
    case "STORAGE_FAILURE":
      return "El almacenamiento no está disponible. El archivo no se guardó.";
    case "EXTERNAL_DOCUMENT_NO_FILE":
      return "Este documento es una referencia externa y no admite archivos.";
    case "DOCUMENT_IN_USE":
      return "El documento tiene vínculos o versiones: archívelo en lugar de eliminarlo.";
    case "LINK_FROZEN":
      return "El vínculo está congelado: el proceso que lo usó no se reinterpreta.";
    case "RESOURCE_ACCESS_DENIED":
      return "No tiene permiso sobre el recurso al que intenta vincular.";
    default:
      return err instanceof Error ? err.message : "No fue posible completar la operación.";
  }
}
