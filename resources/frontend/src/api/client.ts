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

// --------------------------------------------------------------------------
// Contexto de empresa (ARCH-MC-001, N6)
// --------------------------------------------------------------------------

/** Nombre exacto de la cabecera definida por N1. No se construye en otro sitio. */
export const COMPANY_HEADER = "X-Kontrol-Company";

type CompanyResolver = () => string | null;
let companyResolver: CompanyResolver | null = null;

/**
 * Conecta el cliente con la empresa activa de **esta pestaña**.
 *
 * Es el único punto donde se decide qué empresa lleva una petición. Añadir la
 * cabecera a mano en cada servicio garantizaría que alguna se olvidara, y esa
 * sería exactamente la que operase en la empresa equivocada.
 */
export function setCompanyResolver(resolver: CompanyResolver | null): void {
  companyResolver = resolver;
}

export function getActiveCompanyId(): string | null {
  return companyResolver?.() ?? null;
}

/**
 * Rutas que **no** son de empresa: el contexto no aplica y no debe exigirse.
 *
 * La lista es corta a propósito. En KONTROL casi todo es de empresa —136 de 166
 * modelos, medidos en N10—, así que la excepción es lo que se enumera, no la
 * regla. Un endpoint
 * nuevo que no aparezca aquí llevará la cabecera, que es el lado seguro del
 * error.
 */
const RUTAS_SIN_EMPRESA = [
  "/auth/",
  "/organization/companies",
  "/organization/tenants",
  "/setup",
  "/system/",
  "/licensing/",
  "/health",
  "/diagnostics",
];

export function esRutaDeEmpresa(path: string): boolean {
  return !RUTAS_SIN_EMPRESA.some((prefijo) => path === prefijo || path.startsWith(prefijo));
}

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

/**
 * Puerta **única** de renovación de sesión (ADR-004, REM-AUTH-ROUTE-CRAWL-001).
 *
 * El refresh token es de un solo uso: `rotate_session` revoca el anterior al
 * emitir el nuevo. Dos renovaciones concurrentes con la misma cookie no pueden
 * ganar las dos —la segunda encuentra la sesión revocada y recibe 401—, así que
 * **todo** camino que renueve debe pasar por aquí y compartir la que ya está en
 * vuelo. Incluida la restauración inicial al cargar la aplicación, que antes
 * llamaba al endpoint por su cuenta.
 */
export function requestSessionRefresh(): Promise<boolean> {
  return refreshOnce();
}

/** Rutas de autenticación que nunca deben disparar la renovación (evita bucles). */
const isAuthRoute = (path: string): boolean =>
  path === "/auth/login" ||
  path === "/auth/logout" ||
  path.startsWith("/auth/refresh") ||
  path.startsWith("/auth/password-reset") ||
  path.startsWith("/auth/mfa/verify") ||
  path.startsWith("/auth/mfa/enrollment") ||
  path === "/auth/reauth";

/**
 * Reautenticación transversal (Spec 002, ADR-004).
 *
 * Cuando el backend responde 403 `REAUTH_REQUIRED`, la UI debe pedir la
 * contraseña (y segundo factor si procede) antes de reintentar. El cliente no
 * muestra el diálogo: la UI registra aquí un manejador y `apiFetch` reintenta
 * la petición original una sola vez.
 */
type ReauthHandler = () => Promise<boolean>;
let reauthHandler: ReauthHandler | null = null;
let reauthInFlight: Promise<boolean> | null = null;

/**
 * La autoridad que la UI muestra puede caducar con la sesión abierta (rol o
 * alcance revocados). El proveedor de autoridad se registra aquí para poder
 * recargarla cuando el backend la niega.
 */
export type CodigoDeDenegacion = "PERMISSION_DENIED" | "COMPANY_SCOPE_FORBIDDEN";
type DenegacionHandler = (codigo: CodigoDeDenegacion) => void;
let denegacionHandler: DenegacionHandler | null = null;

export function setAuthorityDenialHandler(handler: DenegacionHandler | null): void {
  denegacionHandler = handler;
}

export function setReauthHandler(handler: ReauthHandler | null): void {
  reauthHandler = handler;
}

function reauthOnce(): Promise<boolean> {
  if (!reauthHandler) {
    return Promise.resolve(false);
  }
  if (!reauthInFlight) {
    reauthInFlight = reauthHandler().finally(() => {
      reauthInFlight = null;
    });
  }
  return reauthInFlight;
}

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
  /**
   * Empresa de esta petición, fijada por quien la crea.
   *
   * Sirve para que una operación larga —un formulario que se envía, una
   * descarga— termine en la empresa donde empezó aunque el usuario cambie de
   * empresa mientras tanto. Nunca concede acceso: el servidor la valida igual.
   */
  companyId?: string | null;
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
  // La empresa se resuelve **al construir la petición**, no dentro del `fetch`
  // ni en un reintento posterior. Leer un valor mutable más tarde permitiría
  // que una petición nacida en la empresa A saliera con la cabecera de B si el
  // usuario cambia mientras la promesa espera.
  const empresa = options.companyId !== undefined ? options.companyId : getActiveCompanyId();
  if (empresa && esRutaDeEmpresa(path)) {
    headers[COMPANY_HEADER] = empresa;
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
    const error = new ApiError(response.status, body);
    if (
      response.status === 403 &&
      (error.code === "PERMISSION_DENIED" || error.code === "COMPANY_SCOPE_FORBIDDEN")
    ) {
      try {
        denegacionHandler?.(error.code);
      } catch {
        /* un fallo del aviso no cambia el error */
      }
    }
    throw error;
  }

  return payload as T;
}

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  // La empresa queda fijada aquí, antes de cualquier espera. Si la petición se
  // reintenta tras renovar la sesión, se reintenta en la misma empresa en la
  // que se pidió, no en la que esté activa al terminar la renovación.
  const fijada: RequestOptions =
    options.companyId !== undefined || !esRutaDeEmpresa(path)
      ? options
      : { ...options, companyId: getActiveCompanyId() };
  try {
    return await rawFetch<T>(path, fijada);
  } catch (error) {
    // Access token expirado (401): renovar la sesión una vez y reintentar la
    // petición original con el nuevo token. Si la renovación falla, la sesión
    // se limpia y el router redirige a /login.
    // Reautenticación (Spec 002): si el backend exige repetir la
    // identificación (`REAUTH_REQUIRED`), se pide a la UI una sola vez y, si
    // tiene éxito, se reintenta la petición original.
    if (
      error instanceof ApiError &&
      error.status === 403 &&
      error.code === "REAUTH_REQUIRED" &&
      reauthHandler &&
      !isAuthRoute(path) &&
      (await reauthOnce())
    ) {
      return rawFetch<T>(path, fijada);
    }
    if (
      error instanceof ApiError &&
      error.status === 401 &&
      refreshHandler &&
      !isAuthRoute(path) &&
      (await refreshOnce())
    ) {
      return rawFetch<T>(path, fijada);
    }
    throw error;
  }
}
