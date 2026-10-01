/**
 * LIST · el selector de contexto reúne todas las empresas recorriendo las páginas
 * del contrato; no se queda con la primera ni inventa un tamaño fuera de contrato.
 */
import { describe, expect, it, vi } from "vitest";

const apiFetch = vi.fn();
vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));
const { listAllCompanies, listCompanies, TAMANO_MAXIMO_DE_PAGINA } = await import("./organization");

function servidor(total: number): void {
  apiFetch.mockImplementation(async (ruta: string) => {
    const url = new URL(ruta, "http://k");
    const page = Number(url.searchParams.get("page") ?? "1");
    const page_size = Number(url.searchParams.get("page_size") ?? "20");
    const items = Array.from({ length: total }, (_, i) => ({ id: `e-${i + 1}` })).slice((page - 1) * page_size, page * page_size);
    return { items, total, page, page_size };
  });
}

describe("listAllCompanies", () => {
  it("con más empresas que una página, recorre todas las páginas y devuelve el conjunto entero", async () => {
    apiFetch.mockClear();
    servidor(230);
    const todas = await listAllCompanies();
    expect(todas).toHaveLength(230);
    expect(new Set(todas.map((c) => c.id)).size).toBe(230);
    expect(apiFetch).toHaveBeenCalledTimes(3);
    expect(apiFetch).toHaveBeenNthCalledWith(1, `/organization/companies?page=1&page_size=${TAMANO_MAXIMO_DE_PAGINA}`);
    expect(apiFetch).toHaveBeenNthCalledWith(3, `/organization/companies?page=3&page_size=${TAMANO_MAXIMO_DE_PAGINA}`);
  });

  it("con pocas empresas, una sola página basta", async () => {
    apiFetch.mockClear();
    servidor(2);
    expect(await listAllCompanies()).toHaveLength(2);
    expect(apiFetch).toHaveBeenCalledTimes(1);
  });

  it("sin empresas, devuelve vacío sin pedir una segunda página", async () => {
    apiFetch.mockClear();
    servidor(0);
    expect(await listAllCompanies()).toEqual([]);
    expect(apiFetch).toHaveBeenCalledTimes(1);
  });

  it("el tamaño máximo es el del contrato", () => {
    expect(TAMANO_MAXIMO_DE_PAGINA).toBe(100);
  });

  it("listCompanies construye la consulta con q, page y page_size", async () => {
    apiFetch.mockClear();
    servidor(1);
    await listCompanies({ q: "alfa beta", page: 2, page_size: 25 });
    expect(apiFetch).toHaveBeenCalledWith("/organization/companies?q=alfa+beta&page=2&page_size=25");
    await listCompanies();
    expect(apiFetch).toHaveBeenLastCalledWith("/organization/companies?page=1&page_size=20");
  });
});
