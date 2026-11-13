import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiFetch = vi.fn();
vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));

vi.mock("@/app/autoridad/AutoridadContext", () => ({
  useAutoridad: () => ({ estado: "LISTA", tiene: () => true, puede: () => true, motivo: () => null, motivoDeCapacidad: () => null }),
}));

vi.mock("@/app/contexts/CompanyContext", () => ({
  useCompany: () => ({ activeCompany: { id: "emp-1" } }),
}));

vi.mock("@/modules/organizacion/almacenes/useAlmacenesDeEmpresa", () => ({
  useAlmacenesDeEmpresa: () => ({
    data: {
      items: [
        { id: "wh-1", code: "ALM1", name: "Central", status: "ACTIVE" },
        { id: "wh-2", code: "ALM2", name: "Norte", status: "ACTIVE" },
      ],
    },
    isLoading: false,
    isError: false,
  }),
}));

const { LineasDeOrden } = await import("./LineasDeOrden");

const order = {
  id: "o1",
  code: "OC-1",
  supplier_id: "s1",
  currency: "VED",
  status: "DRAFT",
  allowed_actions: {},
  lines: [
    {
      id: "l1",
      product_id: "p1",
      quantity_ordered: 100,
      quantity_received: 40,
      unit_price: 1,
      needs_inventory: true,
      destination_warehouse: { id: "wh-1", code: "ALM1", name: "Central" },
      open_quantity: "60.000000",
      can_set_destination: false,
    },
    {
      id: "l2",
      product_id: "p2",
      quantity_ordered: 10,
      quantity_received: 10,
      unit_price: 1,
      needs_inventory: true,
      destination_warehouse: null,
      open_quantity: "0.000000",
      can_set_destination: true,
    },
  ],
};

beforeEach(() => {
  apiFetch.mockReset();
});

function renderLineas(onCambios?: () => void | Promise<void>) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <LineasDeOrden orderId="o1" onCambios={onCambios} />
    </QueryClientProvider>,
  );
}

describe("LineasDeOrden", () => {
  it("shows destination, open quantity and no-UUID warning", async () => {
    apiFetch.mockImplementation((url: string) => {
      if (url === "/purchasing/orders/o1") return Promise.resolve(order);
      if (url === "/maestros/catalogos/items/p1") return Promise.resolve({ id: "p1", code: "P-1", name: "Arroz" });
      if (url === "/maestros/catalogos/items/p2") return Promise.resolve({ id: "p2", code: "P-2", name: "Harina" });
      return Promise.reject(new Error("no mock"));
    });

    renderLineas();

    await screen.findByRole("cell", { name: "ALM1 · Central" });
    expect(screen.getByText("60.000000")).toBeTruthy();
    expect(screen.getByText("Sin almacén destino: no cuenta en la planificación")).toBeTruthy();
    expect(screen.queryByText(/o1/)).toBeNull();
    expect(screen.queryByText(/l1/)).toBeNull();
  });

  it("posts the chosen warehouse and calls onCambios", async () => {
    apiFetch.mockImplementation((url: string) => {
      if (url === "/purchasing/orders/o1") return Promise.resolve(order);
      if (url === "/maestros/catalogos/items/p1") return Promise.resolve({ id: "p1", code: "P-1", name: "Arroz" });
      if (url === "/maestros/catalogos/items/p2") return Promise.resolve({ id: "p2", code: "P-2", name: "Harina" });
      if (url === "/purchasing/orders/o1/lines/l2/destination") return Promise.resolve(order);
      return Promise.reject(new Error("no mock"));
    });
    const onCambios = vi.fn().mockResolvedValue(undefined);
    renderLineas(onCambios);

    const select = await screen.findByLabelText("Almacén destino de P-2 · Harina");
    await screen.findByRole("option", { name: "ALM2 · Norte" });
    fireEvent.change(select, { target: { value: "wh-2" } });
    fireEvent.click(screen.getByRole("button", { name: "Fijar destino de P-2 · Harina" }));

    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith(
        "/purchasing/orders/o1/lines/l2/destination",
        { method: "POST", body: { warehouse_id: "wh-2" } },
      ),
    );
    await waitFor(() => expect(onCambios).toHaveBeenCalled());
  });

  it("shows alert and does not POST when no warehouse is chosen", async () => {
    apiFetch.mockImplementation((url: string) => {
      if (url === "/purchasing/orders/o1") return Promise.resolve(order);
      if (url === "/maestros/catalogos/items/p1") return Promise.resolve({ id: "p1", code: "P-1", name: "Arroz" });
      if (url === "/maestros/catalogos/items/p2") return Promise.resolve({ id: "p2", code: "P-2", name: "Harina" });
      return Promise.reject(new Error("no mock"));
    });

    renderLineas();
    await screen.findByLabelText("Almacén destino de P-2 · Harina");
    fireEvent.click(screen.getByRole("button", { name: "Fijar destino de P-2 · Harina" }));

    await screen.findByText("Elija el almacén destino.");
    expect(apiFetch).not.toHaveBeenCalledWith(
      "/purchasing/orders/o1/lines/l2/destination",
      expect.anything(),
    );
  });
});
