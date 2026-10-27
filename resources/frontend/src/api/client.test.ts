/** Renovación de sesión en el cliente (ADR-004, `REM-AUTH-ROUTE-CRAWL-001`).
 *
 * El refresh token es de un solo uso: el servidor revoca el anterior al emitir
 * el nuevo. Por eso el cliente **no puede** lanzar dos renovaciones a la vez, y
 * lo que se comprueba aquí es precisamente eso: que todas las que coincidan
 * compartan una sola petición en vuelo.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  apiFetch,
  requestSessionRefresh,
  setAccessToken,
  setAuthorityDenialHandler,
  setReauthHandler,
  setRefreshHandler,
  type ArchivoDescargado,
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
  setReauthHandler(null);
});

afterEach(() => {
  globalThis.fetch = originalFetch;
  setRefreshHandler(null);
  setReauthHandler(null);
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

describe("reautenticación", () => {
  it("un 403 REAUTH_REQUIRED con manejador que devuelve true reautentica y reintenta una vez", async () => {
    let llamadas = 0;
    setReauthHandler(() => {
      llamadas += 1;
      return Promise.resolve(true);
    });
    let intentos = 0;
    globalThis.fetch = vi.fn(async () => {
      intentos += 1;
      return intentos === 1
        ? jsonResponse({ code: "REAUTH_REQUIRED", message: "reautentique" }, 403)
        : jsonResponse({ ok: true });
    }) as unknown as typeof fetch;

    await expect(apiFetch("/documentos")).resolves.toEqual({ ok: true });
    expect(llamadas).toBe(1);
    expect(intentos).toBe(2);
  });

  it("un 403 REAUTH_REQUIRED con manejador que devuelve false se propaga sin reintentar", async () => {
    let llamadas = 0;
    setReauthHandler(() => {
      llamadas += 1;
      return Promise.resolve(false);
    });
    let intentos = 0;
    globalThis.fetch = vi.fn(async () => {
      intentos += 1;
      return jsonResponse({ code: "REAUTH_REQUIRED", message: "reautentique" }, 403);
    }) as unknown as typeof fetch;

    await expect(apiFetch("/documentos")).rejects.toMatchObject({ code: "REAUTH_REQUIRED" });
    expect(llamadas).toBe(1);
    expect(intentos).toBe(1);
  });

  it("varias peticiones simultáneas con 403 comparten una única reautenticación", async () => {
    let llamadas = 0;
    let resolver: ((v: boolean) => void) | undefined;
    const enVuelo = new Promise<boolean>((r) => { resolver = r; });
    setReauthHandler(() => {
      llamadas += 1;
      return enVuelo;
    });

    let intentos = 0;
    globalThis.fetch = vi.fn(async () => {
      intentos += 1;
      return intentos <= 2
        ? jsonResponse({ code: "REAUTH_REQUIRED", message: "reautentique" }, 403)
        : jsonResponse({ ok: true });
    }) as unknown as typeof fetch;

    const primera = apiFetch("/documentos/a");
    const segunda = apiFetch("/documentos/b");
    setTimeout(() => resolver?.(true), 20);

    await expect(primera).resolves.toEqual({ ok: true });
    await expect(segunda).resolves.toEqual({ ok: true });
    expect(llamadas).toBe(1);
  });

  it("un 401 de /auth/mfa/verify no dispara la renovación", async () => {
    let llamadas = 0;
    setRefreshHandler(() => { llamadas += 1; return Promise.resolve(true); });
    globalThis.fetch = vi.fn(async () =>
      jsonResponse({ code: "MFA_INVALID_CODE", message: "no" }, 401)) as unknown as typeof fetch;

    await expect(apiFetch("/auth/mfa/verify", { method: "POST", body: {} }))
      .rejects.toBeInstanceOf(ApiError);
    expect(llamadas).toBe(0);
  });

  it("un 401 de /auth/reauth no dispara la renovación", async () => {
    let llamadas = 0;
    setRefreshHandler(() => { llamadas += 1; return Promise.resolve(true); });
    globalThis.fetch = vi.fn(async () =>
      jsonResponse({ code: "REAUTH_FAILED", message: "no" }, 401)) as unknown as typeof fetch;

    await expect(apiFetch("/auth/reauth", { method: "POST", body: {} }))
      .rejects.toBeInstanceOf(ApiError);
    expect(llamadas).toBe(0);
  });
});

describe("aviso de denegación de autoridad (Spec 003)", () => {
  afterEach(() => setAuthorityDenialHandler(null));

  it("avisa con COMPANY_SCOPE_FORBIDDEN y rechaza con ApiError 403", async () => {
    const manejador = vi.fn();
    setAuthorityDenialHandler(manejador);
    globalThis.fetch = vi.fn(() =>
      Promise.resolve(
        jsonResponse({ code: "COMPANY_SCOPE_FORBIDDEN", message: "forbidden" }, 403),
      ),
    );

    const p = apiFetch("/maestros/unidades");
    await expect(p).rejects.toBeInstanceOf(ApiError);
    await expect(p).rejects.toMatchObject({ status: 403 });
    expect(manejador).toHaveBeenCalledTimes(1);
    expect(manejador).toHaveBeenCalledWith("COMPANY_SCOPE_FORBIDDEN");
  });

  it("avisa con PERMISSION_DENIED", async () => {
    const manejador = vi.fn();
    setAuthorityDenialHandler(manejador);
    globalThis.fetch = vi.fn(() =>
      Promise.resolve(
        jsonResponse({ code: "PERMISSION_DENIED", message: "forbidden" }, 403),
      ),
    );

    await expect(apiFetch("/maestros/unidades")).rejects.toBeInstanceOf(ApiError);
    expect(manejador).toHaveBeenCalledTimes(1);
    expect(manejador).toHaveBeenCalledWith("PERMISSION_DENIED");
  });

  it("no avisa para otros códigos de error", async () => {
    const manejador = vi.fn();
    setAuthorityDenialHandler(manejador);

    globalThis.fetch = vi.fn(() =>
      Promise.resolve(
        jsonResponse({ code: "REAUTH_REQUIRED", message: "reauth" }, 403),
      ),
    );
    await expect(apiFetch("/maestros/unidades")).rejects.toBeInstanceOf(ApiError);

    globalThis.fetch = vi.fn(() =>
      Promise.resolve(
        jsonResponse({ code: "COMPANY_NOT_FOUND", message: "not found" }, 404),
      ),
    );
    await expect(apiFetch("/maestros/unidades")).rejects.toBeInstanceOf(ApiError);

    expect(manejador).not.toHaveBeenCalled();
  });

  it("un manejador que lanza no cambia el error", async () => {
    setAuthorityDenialHandler(() => {
      throw new Error("fallo del aviso");
    });
    globalThis.fetch = vi.fn(() =>
      Promise.resolve(
        jsonResponse({ code: "PERMISSION_DENIED", message: "forbidden" }, 403),
      ),
    );

    const p = apiFetch("/maestros/unidades");
    await expect(p).rejects.toMatchObject({ status: 403 });
    await expect(p).rejects.toBeInstanceOf(ApiError);
  });
});

describe("descarga autenticada (responseType archivo)", () => {
  it("ARCH-01 devuelve el blob y el content-disposition en un 2xx", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response("%PDF", {
        status: 200,
        headers: {
          "content-type": "application/pdf",
          "content-disposition": 'attachment; filename="r.pdf"',
        },
      }),
    );
    setAccessToken("tok-prueba");

    const resultado = await apiFetch<ArchivoDescargado>(
      "/reporting/exports/e1/download",
      {
        responseType: "archivo",
      },
    );

    expect(resultado.contentDisposition).toBe('attachment; filename="r.pdf"');
    expect(resultado.blob.size).toBe(4);
  });

  it("ARCH-02 lleva la credencial en la cabecera y no en la URL", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response("ok", {
        status: 200,
        headers: { "content-type": "application/octet-stream" },
      }),
    );
    setAccessToken("tok-prueba");

    await apiFetch<ArchivoDescargado>("/reporting/exports/e1/download", {
      responseType: "archivo",
    });

    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
    const [url, init] = (globalThis.fetch as ReturnType<typeof vi.fn>).mock
      .calls[0] as [string, RequestInit];
    expect(url).toBe("/api/v1/reporting/exports/e1/download");
    expect(url).not.toContain("tok-prueba");
    expect((init.headers as Record<string, string>).Authorization).toBe(
      "Bearer tok-prueba",
    );
  });

  it("ARCH-03 lanza ApiError en lugar de devolver el error como archivo", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      jsonResponse({ code: "EXPORT_FILE_MISSING", message: "x" }, 404),
    );
    setAccessToken("tok-prueba");

    const p = apiFetch<ArchivoDescargado>("/reporting/exports/e1/download", {
      responseType: "archivo",
    });

    await expect(p).rejects.toMatchObject({
      code: "EXPORT_FILE_MISSING",
      status: 404,
    });
    await expect(p).rejects.toBeInstanceOf(ApiError);
  });
});
