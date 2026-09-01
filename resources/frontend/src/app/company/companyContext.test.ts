/**
 * Contexto de empresa en el cliente (ARCH-MC-001, N6).
 *
 * Lo que se comprueba aquí no es seguridad —el backend valida cada petición—
 * sino que el frontend no se equivoque de empresa por su cuenta: que la
 * cabecera lleve la empresa correcta, que la caché de una no se sirva bajo
 * otra, y que un formulario abierto en A no acabe guardando en B.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  COMPANY_HEADER, apiFetch, esRutaDeEmpresa, setAccessToken, setCompanyResolver,
} from "@/api/client";
import { debeReintentar, esErrorDeContexto } from "@/app/company/errores";
import { crearHashDeClave, esClaveDeEmpresa } from "@/app/company/queryScope";
import { ApiError } from "@/api/client";

const fetchOriginal = globalThis.fetch;
const EMPRESA_A = "11111111-1111-1111-1111-111111111111";
const EMPRESA_B = "22222222-2222-2222-2222-222222222222";
const TENANT = "99999999-9999-9999-9999-999999999999";

function respuesta(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status, headers: { "content-type": "application/json" },
  });
}

function espiarFetch(): ReturnType<typeof vi.fn> {
  const espia = vi.fn(async () => respuesta({ ok: true }));
  globalThis.fetch = espia as unknown as typeof fetch;
  return espia;
}

function cabecerasDe(espia: ReturnType<typeof vi.fn>, llamada = 0): Record<string, string> {
  return (espia.mock.calls[llamada]?.[1] as RequestInit).headers as Record<string, string>;
}

beforeEach(() => {
  setAccessToken("token");
  setCompanyResolver(null);
});

afterEach(() => {
  globalThis.fetch = fetchOriginal;
  setCompanyResolver(null);
  setAccessToken(null);
});

// --------------------------------------------------------- cabecera
describe("la cabecera de empresa", () => {
  it("viaja en las peticiones de empresa", async () => {
    setCompanyResolver(() => EMPRESA_A);
    const espia = espiarFetch();
    await apiFetch("/sales/orders");
    expect(cabecerasDe(espia)[COMPANY_HEADER]).toBe(EMPRESA_A);
  });

  it("cambia cuando cambia la empresa activa", async () => {
    let actual = EMPRESA_A;
    setCompanyResolver(() => actual);
    const espia = espiarFetch();
    await apiFetch("/sales/orders");
    actual = EMPRESA_B;
    await apiFetch("/sales/orders");
    expect(cabecerasDe(espia, 0)[COMPANY_HEADER]).toBe(EMPRESA_A);
    expect(cabecerasDe(espia, 1)[COMPANY_HEADER]).toBe(EMPRESA_B);
  });

  it("no se envía cuando no hay empresa resuelta", async () => {
    setCompanyResolver(() => null);
    const espia = espiarFetch();
    await apiFetch("/sales/orders");
    // Nunca cadena vacía, ni «undefined», ni el tenant: si no hay empresa, no
    // hay cabecera, y el servidor responderá que hace falta elegir.
    expect(cabecerasDe(espia)).not.toHaveProperty(COMPANY_HEADER);
  });

  it("nunca lleva el identificador del tenant", async () => {
    setCompanyResolver(() => EMPRESA_A);
    const espia = espiarFetch();
    await apiFetch("/purchasing/orders");
    expect(cabecerasDe(espia)[COMPANY_HEADER]).not.toBe(TENANT);
  });

  it("no se envía a rutas que no son de empresa", async () => {
    setCompanyResolver(() => EMPRESA_A);
    const espia = espiarFetch();
    await apiFetch("/auth/me");
    expect(cabecerasDe(espia)).not.toHaveProperty(COMPANY_HEADER);
  });

  it("clasifica correctamente las rutas", () => {
    expect(esRutaDeEmpresa("/sales/orders")).toBe(true);
    expect(esRutaDeEmpresa("/fiscal/documents")).toBe(true);
    expect(esRutaDeEmpresa("/organization/warehouses")).toBe(true);
    expect(esRutaDeEmpresa("/auth/login")).toBe(false);
    expect(esRutaDeEmpresa("/organization/companies")).toBe(false);
    expect(esRutaDeEmpresa("/licensing/status")).toBe(false);
  });

  it("respeta la empresa que fija quien crea la petición", async () => {
    // Una operación larga termina en la empresa donde empezó, aunque el usuario
    // ya haya cambiado a otra.
    setCompanyResolver(() => EMPRESA_B);
    const espia = espiarFetch();
    await apiFetch("/sales/orders", { method: "POST", body: {}, companyId: EMPRESA_A });
    expect(cabecerasDe(espia)[COMPANY_HEADER]).toBe(EMPRESA_A);
  });
});

// --------------------------------------------------------- caché
describe("la separación de la caché", () => {
  it("da identidades distintas a la misma clave en dos empresas", () => {
    let actual = EMPRESA_A;
    const hash = crearHashDeClave(() => actual);
    const enA = hash(["ventas", "ordenes"]);
    actual = EMPRESA_B;
    const enB = hash(["ventas", "ordenes"]);
    expect(enA).not.toBe(enB);
  });

  it("mantiene una sola identidad para lo que no es de empresa", () => {
    let actual = EMPRESA_A;
    const hash = crearHashDeClave(() => actual);
    const enA = hash(["license", "status"]);
    actual = EMPRESA_B;
    expect(hash(["license", "status"])).toBe(enA);
  });

  it("trata como de empresa cualquier clave no declarada", () => {
    // El lado seguro de equivocarse: una consulta nueva que nadie clasifique
    // queda separada por empresa en vez de compartida entre todas.
    expect(esClaveDeEmpresa(["modulo-que-nadie-clasifico"])).toBe(true);
    expect(esClaveDeEmpresa(["license"])).toBe(false);
  });

  it("no confunde la ausencia de empresa con una empresa concreta", () => {
    const hash = crearHashDeClave(() => null);
    const sinEmpresa = hash(["ventas", "ordenes"]);
    const conA = crearHashDeClave(() => EMPRESA_A)(["ventas", "ordenes"]);
    expect(sinEmpresa).not.toBe(conA);
  });
});

// --------------------------------------------------------- errores
describe("los errores de contexto", () => {
  it("se distinguen de los de sesión", () => {
    expect(esErrorDeContexto(new ApiError(404, { code: "COMPANY_NOT_FOUND" }))).toBe(true);
    expect(esErrorDeContexto(new ApiError(409, { code: "COMPANY_INACTIVE" }))).toBe(true);
    expect(esErrorDeContexto(new ApiError(400, { code: "COMPANY_CONTEXT_REQUIRED" }))).toBe(true);
    // Un 401 es sesión, no empresa: confundirlos expulsaría al usuario por
    // haber perdido el acceso a una sola de sus empresas.
    expect(esErrorDeContexto(new ApiError(401, { code: "TOKEN_EXPIRED" }))).toBe(false);
  });

  it("no se reintentan", () => {
    expect(debeReintentar(0, new ApiError(404, { code: "COMPANY_NOT_FOUND" }))).toBe(false);
    expect(debeReintentar(0, new ApiError(500, { code: "INTERNAL" }))).toBe(true);
    expect(debeReintentar(1, new ApiError(500, { code: "INTERNAL" }))).toBe(false);
  });
});
