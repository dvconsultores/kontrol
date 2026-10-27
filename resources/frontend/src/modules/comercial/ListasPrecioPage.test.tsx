/**
 * LISTAS-MONEDAS · Listas de precios pinta las monedas de la empresa (FR-054-E2EDB-030).
 * El servidor responde las monedas dentro de un sobre `{ items: [...] }`, no como array.
 * La pantalla leía la respuesta como un array y caía al pintarlas (`map is not a function`).
 * Aquí se le da a `apiFetch` la respuesta real del servidor para comprobar que la pantalla
 * muestra las monedas como opciones y permanece en pie.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiFetch = vi.fn();
let empresa: { id: string } | null = { id: "c-1" };

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));
vi.mock("@/app/contexts/CompanyContext", () => ({
  useCompany: () => ({ activeCompany: empresa }),
}));
vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify: vi.fn() }),
}));
vi.mock("@/app/autoridad/AutoridadContext", () => ({
  useAutoridad: () => ({
    estado: "LISTA",
    puede: () => true,
    tiene: () => true,
    motivo: () => null,
    motivoDeCapacidad: () => null,
  }),
}));

const { ListasPrecioPage } = await import("./ListasPrecioPage");

function montar(): void {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <ListasPrecioPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function responder(monedas: { id: string; code: string }[]): void {
  apiFetch.mockImplementation((ruta: string) =>
    Promise.resolve(
      ruta === "/treasury/currencies"
        ? { items: monedas, total: monedas.length, page: 1, page_size: monedas.length || 1 }
        : { items: [] },
    ),
  );
}

describe("ListasPrecioPage · monedas", () => {
  beforeEach(() => {
    apiFetch.mockReset();
    empresa = { id: "c-1" };
  });

  it("LM-01 · con el sobre que responde el servidor, las monedas salen como opciones y la pantalla sigue en pie", async () => {
    responder([
      { id: "m-1", code: "VED" },
      { id: "m-2", code: "USD" },
    ]);
    montar();

    expect(await screen.findByRole("option", { name: "VED" })).toBeTruthy();
    expect(screen.getByRole("option", { name: "USD" })).toBeTruthy();
    expect(screen.getAllByRole("option").map((o) => o.textContent)).toEqual([
      "Seleccionar…",
      "VED",
      "USD",
    ]);
    expect(screen.getByRole("heading", { level: 1, name: "Listas de precios" })).toBeTruthy();
    expect(apiFetch).toHaveBeenCalledWith("/treasury/currencies");
  });

  it("LM-02 · sin monedas solo queda la opción vacía, y la pantalla sigue en pie", async () => {
    responder([]);
    montar();

    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith("/treasury/currencies"));
    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith("/comercial/listas-precio"));
    expect(screen.getAllByRole("option").map((o) => o.textContent)).toEqual(["Seleccionar…"]);
    expect(screen.getByRole("heading", { level: 1, name: "Listas de precios" })).toBeTruthy();
  });

  it("LM-03 · sin empresa activa no se pide nada", () => {
    empresa = null;
    responder([{ id: "m-1", code: "VED" }]);
    montar();

    expect(screen.getByRole("alert").textContent).toContain("Seleccione una empresa");
    expect(apiFetch).not.toHaveBeenCalled();
  });
});
