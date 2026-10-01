/**
 * EMP-Q · la caja de Empresas pregunta al servidor, no filtra lo cargado.
 * LIST · la pantalla consume el sobre paginado del contrato y pagina en el servidor.
 *
 * La pantalla enviaba `q` cuando el servidor lo ignoraba, y pedía un array cuando
 * el contrato es un sobre. Lo que se fija aquí: cada término y cada página
 * producen su propia petición; la tabla pinta exactamente los `items` recibidos;
 * el `total` del sobre gobierna la paginación; y cambiar la búsqueda vuelve a la
 * primera página.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, expectTypeOf, it, vi } from "vitest";

import type { CompanySummary, PagedResult } from "@/api/types";

const apiFetch = vi.fn();
vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));
vi.mock("@/app/contexts/CompanyContext", () => ({
  useCompany: () => ({ activeCompany: null, selectCompany: vi.fn(), clearCompany: vi.fn() }),
}));
vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify: vi.fn() }),
}));

const { EmpresasPage } = await import("./EmpresasPage");
const { listCompanies, listAllCompanies } = await import("@/api/organization");

function empresa(n: number, legal_name = `Empresa ${String(n).padStart(2, "0")} CA`): CompanySummary {
  return { id: `e-${n}`, code: `C${n}`, legal_name, trade_name: null, rif: `J-${n}`, status: "ACTIVE" } as CompanySummary;
}

function montar(): void {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <EmpresasPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

/** El servidor de mentira busca y pagina de verdad, para que la pantalla no pueda fingirlo. */
function servidor(todas: CompanySummary[]): void {
  apiFetch.mockImplementation(async (ruta: string) => {
    const url = new URL(ruta, "http://k");
    const q = (url.searchParams.get("q") ?? "").toLowerCase();
    const page = Number(url.searchParams.get("page") ?? "1");
    const page_size = Number(url.searchParams.get("page_size") ?? "20");
    const coinciden = todas.filter((c) => !q || [c.code, c.legal_name, c.rif].some((v) => v.toLowerCase().includes(q)));
    const items = coinciden.slice((page - 1) * page_size, page * page_size);
    return { items, total: coinciden.length, page, page_size } satisfies PagedResult<CompanySummary>;
  });
}

const DOS = [empresa(1, "Demo C.A."), empresa(2, "SEGUNDA EMPRESA CA")];
const VEINTITRES = Array.from({ length: 23 }, (_, i) => empresa(i + 1));

describe("EmpresasPage · búsqueda general", () => {
  it("F-Q-01 · cada término escrito produce una petición al servidor con q", async () => {
    apiFetch.mockClear();
    servidor(DOS);
    montar();
    expect(await screen.findByText("Demo C.A.")).toBeInTheDocument();
    expect(apiFetch).toHaveBeenCalledWith("/organization/companies?page=1&page_size=10");
    await userEvent.type(screen.getByLabelText("Buscar"), "SEGUNDA");
    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith("/organization/companies?q=SEGUNDA&page=1&page_size=10"));
  });

  it("F-Q-02 · la tabla pinta lo que responde el servidor y no lo que había cargado", async () => {
    apiFetch.mockClear();
    servidor(DOS);
    montar();
    expect(await screen.findByText("SEGUNDA EMPRESA CA")).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Buscar"), "SEGUNDA");
    await waitFor(() => expect(screen.queryByText("Demo C.A.")).not.toBeInTheDocument());
    expect(screen.getByText("SEGUNDA EMPRESA CA")).toBeInTheDocument();
    await userEvent.clear(screen.getByLabelText("Buscar"));
    expect(await screen.findByText("Demo C.A.")).toBeInTheDocument();
  });

  it("F-Q-03 · un término sin coincidencias deja la tabla en su estado vacío", async () => {
    apiFetch.mockClear();
    servidor(DOS);
    montar();
    await screen.findByText("Demo C.A.");
    await userEvent.type(screen.getByLabelText("Buscar"), "ZZZ-NO-EXISTE-EMPRESA-Q");
    expect(await screen.findByText("Sin empresas")).toBeInTheDocument();
    expect(screen.queryByText("Demo C.A.")).not.toBeInTheDocument();
  });
});

describe("EmpresasPage · sobre paginado del contrato", () => {
  it("LIST-F-01 · las filas son los items del sobre y la paginación la gobierna total", async () => {
    apiFetch.mockClear();
    servidor(VEINTITRES);
    montar();
    expect(await screen.findByText("Empresa 01 CA")).toBeInTheDocument();
    // Diez filas de la página 1, un solo paginador (el de la pantalla, con el total del servidor).
    expect(screen.getAllByRole("row")).toHaveLength(11);
    expect(screen.queryByText("Empresa 11 CA")).not.toBeInTheDocument();
    expect(screen.getAllByRole("navigation", { name: "Paginación" })).toHaveLength(1);
    expect(screen.getByText("Página 1 de 3")).toBeInTheDocument();
  });

  it("LIST-F-02 · pasar de página pide la página 2 al servidor y pinta sus items", async () => {
    apiFetch.mockClear();
    servidor(VEINTITRES);
    montar();
    await screen.findByText("Empresa 01 CA");
    await userEvent.click(screen.getByRole("button", { name: /siguiente/i }));
    expect(await screen.findByText("Empresa 11 CA")).toBeInTheDocument();
    expect(apiFetch).toHaveBeenCalledWith("/organization/companies?page=2&page_size=10");
    expect(screen.queryByText("Empresa 01 CA")).not.toBeInTheDocument();
    expect(screen.getAllByRole("row")).toHaveLength(11);
  });

  it("LIST-F-03 · cambiar la búsqueda vuelve a la primera página", async () => {
    apiFetch.mockClear();
    servidor(VEINTITRES);
    montar();
    await screen.findByText("Empresa 01 CA");
    await userEvent.click(screen.getByRole("button", { name: /siguiente/i }));
    await screen.findByText("Empresa 11 CA");
    await userEvent.type(screen.getByLabelText("Buscar"), "Empresa 2");
    await waitFor(() => expect(apiFetch).toHaveBeenLastCalledWith("/organization/companies?q=Empresa+2&page=1&page_size=10"));
    expect(await screen.findByText("Empresa 20 CA")).toBeInTheDocument();
  });

  it("LIST-F-06 · con una página mayor que diez, la tabla no vuelve a paginar en cliente", async () => {
    apiFetch.mockClear();
    servidor(VEINTITRES);
    montar();
    await screen.findByText("Empresa 01 CA");
    await userEvent.selectOptions(screen.getByLabelText("Registros por página"), "25");
    await waitFor(() => expect(apiFetch).toHaveBeenLastCalledWith("/organization/companies?page=1&page_size=25"));
    expect(await screen.findByText("Empresa 23 CA")).toBeInTheDocument();
    // Las 23 filas de la página del servidor, y un solo paginador: el de la pantalla.
    expect(screen.getAllByRole("row")).toHaveLength(24);
    expect(screen.getAllByRole("navigation", { name: "Paginación" })).toHaveLength(1);
    expect(screen.getByText("Página 1 de 1")).toBeInTheDocument();
  });

  it("LIST-F-04 · una respuesta que no es el sobre no se pinta por una puerta de atrás", async () => {
    apiFetch.mockClear();
    apiFetch.mockResolvedValue(DOS);
    montar();
    await waitFor(() => expect(apiFetch).toHaveBeenCalled());
    await waitFor(() => expect(screen.queryByRole("status")).not.toBeInTheDocument());
    expect(screen.queryByText("Demo C.A.")).not.toBeInTheDocument();
    expect(screen.queryByRole("row")).not.toBeInTheDocument();
  });

  it("LIST-F-05 · el contrato de tipo: la petición devuelve el sobre, nunca un array", () => {
    expectTypeOf(listCompanies).returns.resolves.toEqualTypeOf<PagedResult<CompanySummary>>();
    expectTypeOf(listCompanies).returns.resolves.not.toEqualTypeOf<CompanySummary[]>();
    expectTypeOf(listAllCompanies).returns.resolves.toEqualTypeOf<CompanySummary[]>();
  });
});
