/** Renovación de sesión en el cliente (ADR-004, `REM-AUTH-ROUTE-CRAWL-001`).
 *
 * El refresh token es de un solo uso: el servidor revoca el anterior al emitir
 * el nuevo. Por eso el cliente **no puede** lanzar dos renovaciones a la vez, y
 * lo que se comprueba aquí es precisamente eso: que todas las que coincidan
 * compartan una sola petición en vuelo.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  ApiError, apiFetch, requestSessionRefresh, setAccessToken, setRefreshHandler,
} from "./client";

const originalFetch = globalThis.fetch;

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status, headers: { "content-type": "application/json" },
  });
}

beforeEach(() => {
  setAccessToken(null);
  setRefreshHandler(null);
});

afterEach(() => {
  globalThis.fetch = originalFetch;
  setRefreshHandler(null);
  setAccessToken(null);
  vi.restoreAllMocks();
});

describe("renovación única en vuelo", () => {
  it("varias llamadas simultáneas comparten una sola renovación", async () => {
    let llamadas = 0;
    let resolver: ((v: boolean) => void) | undefined;
    const enVuelo = new Promise<boolean>((r) => { resolver = r; });

    setRefreshHandler(() => { llamadas += 1; return enVuelo; });

    const peticiones = [
      requestSessionRefresh(), requestSessionRefresh(), requestSessionRefresh(),
    ];
    resolver?.(true);
    const resultados = await Promise.all(peticiones);

    expect(llamadas).toBe(1);
    expect(resultados).toEqual([true, true, true]);
  });

  it("una renovación posterior sí vuelve a pedirse", async () => {
    let llamadas = 0;
    setRefreshHandler(() => { llamadas += 1; return Promise.resolve(true); });

    await requestSessionRefresh();
    await requestSessionRefresh();

    expect(llamadas).toBe(2);
  });

  it("sin manejador registrado no renueva ni falla", async () => {
    await expect(requestSessionRefresh()).resolves.toBe(false);
  });

  it("la restauración inicial y un 401 concurrente no se duplican", async () => {
    // Reproduce el arranque: el contexto restaura la sesión mientras una
    // consulta ya lanzada recibe 401. Antes eran dos POST /auth/refresh.
    let llamadas = 0;
    let resolver: ((v: boolean) => void) | undefined;
    const enVuelo = new Promise<boolean>((r) => { resolver = r; });
    setRefreshHandler(() => { llamadas += 1; return enVuelo; });

    let intentos = 0;
    globalThis.fetch = vi.fn(async () => {
      intentos += 1;
      return intentos === 1
        ? jsonResponse({ code: "AUTH_REQUIRED", message: "Debe iniciar sesión" }, 401)
        : jsonResponse({ ok: true });
    }) as unknown as typeof fetch;

    const restauracion = requestSessionRefresh();   // el contexto, al montar
    const consulta = apiFetch<{ ok: boolean }>("/organization/companies");
    // La renovación se resuelve **después** de que el 401 haya llegado: es lo
    // que hace que las dos coincidan de verdad. Resolverla antes convertiría la
    // prueba en dos renovaciones sucesivas, que no es el caso que interesa.
    setTimeout(() => resolver?.(true), 20);

    await restauracion;
    await expect(consulta).resolves.toEqual({ ok: true });
    expect(llamadas, "solo debe renovarse una vez").toBe(1);
    expect(intentos, "la petición original se reintenta una sola vez").toBe(2);
  });
});

describe("reintento y bucles", () => {
  it("un 401 renueva y reintenta la petición una sola vez", async () => {
    setRefreshHandler(() => Promise.resolve(true));
    let intentos = 0;
    globalThis.fetch = vi.fn(async () => {
      intentos += 1;
      return intentos === 1
        ? jsonResponse({ code: "AUTH_REQUIRED", message: "no" }, 401)
        : jsonResponse({ ok: true });
    }) as unknown as typeof fetch;

    await expect(apiFetch("/maestros/terceros")).resolves.toEqual({ ok: true });
    expect(intentos).toBe(2);
  });

  it("si la renovación falla, el 401 se propaga sin reintentar", async () => {
    setRefreshHandler(() => Promise.resolve(false));
    let intentos = 0;
    globalThis.fetch = vi.fn(async () => {
      intentos += 1;
      return jsonResponse({ code: "AUTH_REQUIRED", message: "no" }, 401);
    }) as unknown as typeof fetch;

    await expect(apiFetch("/maestros/terceros")).rejects.toBeInstanceOf(ApiError);
    expect(intentos, "no debe reintentarse cuando la renovación fracasa").toBe(1);
  });

  it("un 401 del propio endpoint de renovación no dispara otra renovación", async () => {
    // Sin esta exclusión, un refresh rechazado renovaría en bucle.
    let llamadas = 0;
    setRefreshHandler(() => { llamadas += 1; return Promise.resolve(true); });
    globalThis.fetch = vi.fn(async () =>
      jsonResponse({ code: "AUTH_REQUIRED", message: "no" }, 401)) as unknown as typeof fetch;

    await expect(apiFetch("/auth/refresh", { method: "POST" }))
      .rejects.toBeInstanceOf(ApiError);
    expect(llamadas).toBe(0);
  });

  it("el login rechazado no intenta renovar", async () => {
    let llamadas = 0;
    setRefreshHandler(() => { llamadas += 1; return Promise.resolve(true); });
    globalThis.fetch = vi.fn(async () =>
      jsonResponse({ code: "AUTH_INVALID_CREDENTIALS", message: "no" }, 401),
    ) as unknown as typeof fetch;

    await expect(apiFetch("/auth/login", { method: "POST", body: {} }))
      .rejects.toBeInstanceOf(ApiError);
    expect(llamadas).toBe(0);
  });

  it("un 403 no renueva: autenticado sin permiso no es sesión caducada", async () => {
    let llamadas = 0;
    setRefreshHandler(() => { llamadas += 1; return Promise.resolve(true); });
    globalThis.fetch = vi.fn(async () =>
      jsonResponse({ code: "PERMISSION_DENIED", message: "no" }, 403)) as unknown as typeof fetch;

    await expect(apiFetch("/documentos")).rejects.toBeInstanceOf(ApiError);
    expect(llamadas).toBe(0);
  });
});
