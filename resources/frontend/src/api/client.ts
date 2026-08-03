/**
 * Cliente API de KONTROL (FR-001-063, contrato de errores DOC-08 §11.1).
 * Normaliza 400/401/403/404/409/422/423/429/5xx y adjunta request ID.
 * El refresh token va en cookie HttpOnly; el access token en memoria (ADR-004).
 */

export interface ApiErrorBody {
  code: string;
  message: string;
  field_errors?: Record<string, string[]>;
  request_id?: string;
  details?: unknown;
}

export class ApiError extends Error {
  code: string;
  status: number;
  fieldErrors: Record<string, string[]>;
  requestId?: string;

  constructor(status: number, body: Partial<ApiErrorBody>) {
    super(body.message ?? "No fue posible completar la operación");
    this.name = "ApiError";
    this.code = body.code ?? "UNKNOWN_ERROR";
    this.status = status;
    this.fieldErrors = body.field_errors ?? {};
    this.requestId = body.request_id;
  }
}

const isApiErrorBody = (value: unknown): value is ApiErrorBody =>
  typeof value === "object" && value !== null && "code" in value;

let accessToken: string | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

export interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  /** Clave de idempotencia para POST críticos (ADR-013). */
  idempotencyKey?: string;
  signal?: AbortSignal;
}

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {
    Accept: "application/json",
  };
  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`;
  }
  if (options.idempotencyKey) {
    headers["Idempotency-Key"] = options.idempotencyKey;
  }

  const response = await fetch(`/api/v1${path}`, {
    method: options.method ?? (options.body !== undefined ? "POST" : "GET"),
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    credentials: "include",
    signal: options.signal,
  });

  // 204 / sin contenido
  if (response.status === 204) {
    return undefined as T;
  }

  let payload: unknown = null;
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }
  }

  if (!response.ok) {
    const body = isApiErrorBody(payload) ? payload : {};
    throw new ApiError(response.status, body);
  }

  return payload as T;
}
