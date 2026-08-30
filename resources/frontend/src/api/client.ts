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
  /** Contexto del error (límite excedido, formatos admitidos…). Sin esto, la
   *  interfaz solo podría decir «no se pudo»: el detalle es lo que la vuelve
   *  accionable. */
  details?: Record<string, unknown>;

  constructor(status: number, body: Partial<ApiErrorBody>) {
    super(body.message ?? "No fue posible completar la operación");
    this.name = "ApiError";
    this.code = body.code ?? "UNKNOWN_ERROR";
    this.status = status;
    this.fieldErrors = body.field_errors ?? {};
    this.requestId = body.request_id;
    this.details = (body.details ?? undefined) as Record<string, unknown> | undefined;
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

// Renovación automática de sesión (ADR-004): si el servidor responde 401
// (access token expirado), se renueva la sesión una vez y se reintenta.
type RefreshHandler = () => Promise<boolean>;
let refreshHandler: RefreshHandler | null = null;
let refreshInFlight: Promise<boolean> | null = null;

export function setRefreshHandler(handler: RefreshHandler | null): void {
  refreshHandler = handler;
}

function refreshOnce(): Promise<boolean> {
  if (!refreshHandler) {
    return Promise.resolve(false);
  }
  if (!refreshInFlight) {
    refreshInFlight = refreshHandler().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

/** Rutas de autenticación que nunca deben disparar la renovación (evita bucles). */
const isAuthRoute = (path: string): boolean =>
  path === "/auth/login" ||
  path === "/auth/logout" ||
  path.startsWith("/auth/refresh") ||
  path.startsWith("/auth/password-reset");

export interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  /** Clave de idempotencia para POST críticos (ADR-013). */
  idempotencyKey?: string;
  /** Versión esperada del recurso para control optimista; 409 en conflicto (ADR-013). */
  ifMatch?: string;
  signal?: AbortSignal;
  /** `blob` para descargas binarias (Spec 046): el cuerpo no se interpreta como JSON. */
  responseType?: "json" | "blob";
}

async function rawFetch<T>(path: string, options: RequestOptions): Promise<T> {
  const wantsBlob = options.responseType === "blob";
  // Multipart: el navegador debe poner el Content-Type con su propio boundary.
  const isMultipart = typeof FormData !== "undefined" && options.body instanceof FormData;

  const headers: Record<string, string> = {
    Accept: wantsBlob ? "*/*" : "application/json",
  };
  if (options.body !== undefined && !isMultipart) {
    headers["Content-Type"] = "application/json";
  }
  if (accessToken) {
    headers.Authorization = `Bearer ${accessToken}`;
  }
  if (options.idempotencyKey) {
    headers["Idempotency-Key"] = options.idempotencyKey;
  }
  if (options.ifMatch) {
    headers["If-Match"] = options.ifMatch;
  }

  const response = await fetch(`/api/v1${path}`, {
    method: options.method ?? (options.body !== undefined ? "POST" : "GET"),
    headers,
    body:
      options.body === undefined
        ? undefined
        : isMultipart
          ? (options.body as FormData)
          : JSON.stringify(options.body),
    credentials: "include",
    signal: options.signal,
  });

  // 204 / sin contenido
  if (response.status === 204) {
    return undefined as T;
  }

  // Una descarga correcta se devuelve como binario; un fallo sigue siendo JSON
  // y debe pasar por el contrato de errores como cualquier otra respuesta.
  if (wantsBlob && response.ok) {
    return (await response.blob()) as T;
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

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  try {
    return await rawFetch<T>(path, options);
  } catch (error) {
    // Access token expirado (401): renovar la sesión una vez y reintentar la
    // petición original con el nuevo token. Si la renovación falla, la sesión
    // se limpia y el router redirige a /login.
    if (
      error instanceof ApiError &&
      error.status === 401 &&
      refreshHandler &&
      !isAuthRoute(path) &&
      (await refreshOnce())
    ) {
      return rawFetch<T>(path, options);
    }
    throw error;
  }
}
