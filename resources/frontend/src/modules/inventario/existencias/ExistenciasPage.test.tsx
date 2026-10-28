/**
 * EXS-F · la caja de Existencias pregunta al servidor, no filtra lo cargado.
 * FR-001-272 · búsqueda y paginación de servidor en Existencias.
 *
 * La pantalla enviaba `q` sin paginar y pedía `product_id` como columna de
 * producto. Lo que se fija aquí: cada término y cada página producen su propia
 * petición; la tabla pinta exactamente los `items` recibidos; el `total` del
 * sobre gobierna la paginación; cambiar la búsqueda vuelve a la primera página;
 * la columna Producto combina código y nombre del servidor, y los errores 4xx
 * muestran el mensaje seguro del contrato.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";

import type { InventoryBalance, PagedResult } from "@/api/types";

const apiFetch = vi.fn();
vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));

const { ExistenciasPage } = await import("./ExistenciasPage");
const { ApiError } = await import("@/api/client");

function saldo(n: number, sobre: Partial<InventoryBalance> = {}): InventoryBalance {
  return {
    id: `s-${n}`,
    product_id: `EXS-${n}`,
    product_code: `EXS-${n}`,
    product_name: `Producto ${n}`,
    warehouse_id: `w-${n}`,
    lot_id: null,
    serial_id: null,
    state: "AVAILABLE",
    qty_on_hand: 10,
    qty_reserved: 0,
    qty_available: 10,
    ...sobre,
  } as InventoryBalance;
}

function montar(): void {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <ExistenciasPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

/** El servidor de mentira busca y pagina de verdad sobre producto. */
function servidor(todos: InventoryBalance[]): void {
  apiFetch.mockImplementation(async (ruta: string) => {
    const url = new URL(ruta, "http://k");
    const q = (url.searchParams.get("q") ?? "").toLowerCase();
    const page = Number(url.searchParams.get("page") ?? "1");
    const page_size = Number(url.searchParams.get("page_size") ?? "10");
    const coinciden = todos.filter((f) => {
      if (!q) return true;
      return [f.product_code, f.product_name].some((v) => v && v.toLowerCase().includes(q));
    });
    const items = coinciden.slice((page - 1) * page_size, page * page_size);
    return { items, total: coinciden.length, page, page_size } satisfies PagedResult<InventoryBalance>;
  });
}

const DOS = [
  saldo(1, { product_code: "EXS-A", product_name: "Tornillo galvanizado" }),
  saldo(2, { product_code: "EXS-B", product_name: "Tuerca hexagonal" }),
];
const VEINTITRES = Array.from({ length: 23 }, (_, i) => saldo(i + 1));

describe("ExistenciasPage · búsqueda de servidor", () => {
  it("EXS-F-01 · la primera petición es exactamente page=1 y page_size=10", async () => {
    apiFetch.mockClear();
    servidor(DOS);
    montar();
    expect(await screen.findByText("EXS-A — Tornillo galvanizado")).toBeInTheDocument();
    expect(apiFetch).toHaveBeenCalledWith("/inventory/balances?page=1&page_size=10");
  });

  it("EXS-F-02 · escribir un término produce q y la tabla pinta solo lo que responde el servidor", async () => {
    apiFetch.mockClear();
    servidor(DOS);
    montar();
    expect(await screen.findByText("EXS-B — Tuerca hexagonal")).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Buscar por producto"), "tornillo");
    await waitFor(() =>
      expect(apiFetch).toHaveBeenLastCalledWith("/inventory/balances?q=tornillo&page=1&page_size=10"),
    );
    expect(await screen.findByText("EXS-A — Tornillo galvanizado")).toBeInTheDocument();
    expect(screen.queryByText("EXS-B — Tuerca hexagonal")).not.toBeInTheDocument();
  });

  it("EXS-F-03 · limpiar la caja vuelve a pintar ambas", async () => {
    apiFetch.mockClear();
    servidor(DOS);
    montar();
    await screen.findByText("EXS-A — Tornillo galvanizado");
    await userEvent.type(screen.getByLabelText("Buscar por producto"), "tornillo");
    await screen.findByText("EXS-A — Tornillo galvanizado");
    await userEvent.clear(screen.getByLabelText("Buscar por producto"));
    expect(await screen.findByText("EXS-B — Tuerca hexagonal")).toBeInTheDocument();
    expect(screen.getByText("EXS-A — Tornillo galvanizado")).toBeInTheDocument();
  });

  it("EXS-F-04 · paginar avanza y una nueva búsqueda vuelve a page=1", async () => {
    apiFetch.mockClear();
    servidor(VEINTITRES);
    montar();
    await screen.findByText("EXS-1 — Producto 1");
    await waitFor(() => expect(apiFetch).toHaveBeenLastCalledWith("/inventory/balances?page=1&page_size=10"));
    await waitFor(() => expect(screen.getByText("Página 1 de 3")).toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: /siguiente/i }));
    await waitFor(() => expect(apiFetch).toHaveBeenLastCalledWith("/inventory/balances?page=2&page_size=10"));
    await userEvent.type(screen.getByLabelText("Buscar por producto"), "Producto 2");
    await waitFor(() =>
      expect(apiFetch).toHaveBeenLastCalledWith("/inventory/balances?q=Producto+2&page=1&page_size=10"),
    );
  });

  it("EXS-F-05 · sin product_code ni product_name la columna muestra el product_id", async () => {
    apiFetch.mockClear();
    servidor([saldo(7, { product_code: null, product_name: null })]);
    montar();
    expect(await screen.findByText("EXS-7")).toBeInTheDocument();
  });

  it("EXS-F-06a · un ApiError 422 muestra el mensaje seguro del servidor", async () => {
    apiFetch.mockReset();
    apiFetch.mockRejectedValue(
      new ApiError(422, {
        code: "UNKNOWN_QUERY_PARAMETER",
        message: "La consulta incluye parámetros que esta operación no admite.",
      }),
    );
    montar();
    expect(
      await screen.findByText("La consulta incluye parámetros que esta operación no admite."),
    ).toBeInTheDocument();
  });

  it("EXS-F-06b · un Error genérico muestra el mensaje por defecto", async () => {
    apiFetch.mockReset();
    apiFetch.mockRejectedValue(new Error("boom"));
    montar();
    expect(await screen.findByText("No fue posible cargar las existencias.")).toBeInTheDocument();
    expect(
      screen.queryByText("La consulta incluye parámetros que esta operación no admite."),
    ).not.toBeInTheDocument();
  });

  it("EXS-F-07 · ninguna petición contiene company_id ni parámetros distintos de q, page y page_size", async () => {
    apiFetch.mockClear();
    servidor(VEINTITRES);
    montar();
    await screen.findByText("EXS-1 — Producto 1");
    await userEvent.type(screen.getByLabelText("Buscar por producto"), "tornillo");
    await waitFor(() => expect(apiFetch.mock.calls.length).toBeGreaterThan(1));
    let conQ = false;
    for (const llamada of apiFetch.mock.calls) {
      const ruta = String(llamada[0]);
      const url = new URL(ruta, "http://k");
      for (const clave of url.searchParams.keys()) {
        expect(["q", "page", "page_size"]).toContain(clave);
      }
      expect(url.searchParams.has("company_id")).toBe(false);
      if (url.searchParams.has("q")) {
        conQ = true;
      }
    }
    expect(conQ).toBe(true);
  });
});
