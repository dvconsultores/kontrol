/**
 * EMP-Q · la caja de Empresas pregunta al servidor, no filtra lo cargado.
 *
 * La pantalla ya enviaba `q` cuando el servidor lo ignoraba; lo que se fija aquí
 * es que siga siendo el servidor quien decide: cada término produce su propia
 * petición con `q`, y la tabla pinta exactamente lo que el servidor devuelve.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

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

const D1 = { id: "d1", code: "D1", legal_name: "Demo C.A.", trade_name: null, rif: "J-12345678-9", status: "ACTIVE" };
const D2 = { id: "d2", code: "D2", legal_name: "SEGUNDA EMPRESA CA", trade_name: null, rif: "J-40470470-7", status: "ACTIVE" };

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

/** El servidor de mentira busca de verdad, para que la pantalla no pueda fingirlo. */
function servidorQueBusca(): void {
  apiFetch.mockImplementation(async (ruta: string) => {
    const q = decodeURIComponent(new URL(ruta, "http://k").searchParams.get("q") ?? "").toLowerCase();
    return [D1, D2].filter((c) => !q || [c.code, c.legal_name, c.rif].some((v) => v.toLowerCase().includes(q)));
  });
}

describe("EmpresasPage · búsqueda general", () => {
  beforeEach(() => apiFetch.mockReset());

  it("F-Q-01 · cada término escrito produce una petición al servidor con q", async () => {
    servidorQueBusca();
    montar();
    expect(await screen.findByText("Demo C.A.")).toBeInTheDocument();
    expect(apiFetch).toHaveBeenCalledWith("/organization/companies?q=");

    await userEvent.type(screen.getByLabelText("Buscar"), "SEGUNDA");
    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith("/organization/companies?q=SEGUNDA"));
  });

  it("F-Q-02 · la tabla pinta lo que responde el servidor y no lo que había cargado", async () => {
    servidorQueBusca();
    montar();
    expect(await screen.findByText("SEGUNDA EMPRESA CA")).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText("Buscar"), "SEGUNDA");
    await waitFor(() => expect(screen.queryByText("Demo C.A.")).not.toBeInTheDocument());
    expect(screen.getByText("SEGUNDA EMPRESA CA")).toBeInTheDocument();

    await userEvent.clear(screen.getByLabelText("Buscar"));
    expect(await screen.findByText("Demo C.A.")).toBeInTheDocument();
  });

  it("F-Q-03 · un término sin coincidencias deja la tabla en su estado vacío", async () => {
    servidorQueBusca();
    montar();
    await screen.findByText("Demo C.A.");
    await userEvent.type(screen.getByLabelText("Buscar"), "ZZZ-NO-EXISTE-EMPRESA-Q");
    expect(await screen.findByText("Sin empresas")).toBeInTheDocument();
    expect(screen.queryByText("Demo C.A.")).not.toBeInTheDocument();
    expect(apiFetch).toHaveBeenLastCalledWith("/organization/companies?q=ZZZ-NO-EXISTE-EMPRESA-Q");
  });
});
