import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

beforeAll(async () => {
  await Promise.all([
    import("./RequisicionesPage"),
    import("./RequisicionNuevaPage"),
    import("./RequisicionDetallePage"),
  ]);
});

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createMemoryRouter, RouterProvider } from "react-router";
import { ApiError } from "@/api/client";

let mockPuede = true;
const apiFetch = vi.fn();
const notify = vi.fn();
let mockAlmacenes: Array<{ id: string; code: string; name: string; status: string }> = [];

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
}));

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify, dismiss: vi.fn(), notifications: [] }),
}));

vi.mock("@/app/contexts/CompanyContext", () => ({
  useCompany: () => ({ activeCompany: { id: "emp-1" } }),
}));

vi.mock("@/modules/organizacion/almacenes/useAlmacenesDeEmpresa", () => ({
  useAlmacenesDeEmpresa: () => ({
    data: { items: mockAlmacenes },
    isSuccess: true,
    isLoading: false,
    isError: false,
  }),
}));

vi.mock("@/app/autoridad/AutoridadContext", () => ({
  useAutoridad: () => ({
    estado: "LISTA",
    tiene: () => true,
    puede: () => mockPuede,
    motivo: () => null,
    motivoDeCapacidad: () => null,
  }),
}));

vi.mock("@/modules/maestros/catalogo/SelectorDeArticulo", () => ({
  SelectorDeArticulo: ({ value, onChange }: { value: string; onChange: (id: string) => void }) => (
    <input
      aria-label="Producto"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      data-testid="selector-articulo"
    />
  ),
}));

const detalleBase = {
  id: "req-1",
  code: "REQ-1",
  status: "DRAFT",
  warehouse_id: "wh-1",
  warehouse_code: "ALM1",
  need_date: null,
  lines: [],
};

const planOK = {
  status: "OK",
  policy: { id: "pol-1", code: "POL-1", version: 2 },
  demand_source: null,
  window_start: null,
  window_end: null,
  lookback_days: 30,
  horizon_days: 14,
  lead_time_days: 7,
  history_partial: null,
  observed_history_days: null,
  net_demand: "50.000000",
  avg_daily_demand: "3.333333",
  projected_demand: "46.666662",
  safety_stock: "10.000000",
  reorder_point: "20.000000",
  on_hand: "8.000000",
  reserved: "1.000000",
  available: "7.000000",
  open_supply_available: false,
  rotation_metric: "0.416667",
  demand_velocity: "3.333333",
  turnover: "0.416667",
  rotation_band: { id: "rb-1", code: "RB-1", name: "Baja" },
  coverage_days: 3,
  recommended_quantity: "12.000000",
  product_code: "P-1",
  product_name: "Producto 1",
  warehouse_code: "ALM1",
};

function crearRouter(rutaInicial: string) {
  return createMemoryRouter(
    [
      {
        path: "/compras/requisiciones",
        lazy: async () => {
          const { RequisicionesPage } = await import("./RequisicionesPage");
          return { Component: RequisicionesPage };
        },
      },
      {
        path: "/compras/requisiciones/nueva",
        lazy: async () => {
          const { RequisicionNuevaPage } = await import("./RequisicionNuevaPage");
          return { Component: RequisicionNuevaPage };
        },
      },
      {
        path: "/compras/requisiciones/:requisitionId",
        lazy: async () => {
          const { RequisicionDetallePage } = await import("./RequisicionDetallePage");
          return { Component: RequisicionDetallePage };
        },
      },
    ],
    { initialEntries: [rutaInicial] },
  );
}

function renderizar(rutaInicial: string) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const router = crearRouter(rutaInicial);
  return render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  apiFetch.mockReset();
  notify.mockReset();
  mockPuede = true;
  mockAlmacenes = [{ id: "wh-1", code: "ALM1", name: "Central", status: "ACTIVE" }];
});

describe("Requisiciones", () => {
  it("1 · Nueva: sin almacén muestra alerta y no hace POST", async () => {
    apiFetch.mockImplementation((url: string) => {
      if (url === "/purchasing/requisitions") return Promise.reject(new Error("no debe llamarse"));
      return Promise.resolve({ items: [] });
    });

    renderizar("/compras/requisiciones/nueva");

    const codigo = await screen.findByLabelText(/^Código/);
    await userEvent.type(codigo, "REQ-1");

    await userEvent.click(screen.getByRole("button", { name: /crear requisición/i }));

    expect(screen.getByRole("alert")).toHaveTextContent("Indica el código y el almacén.");
    const llamadasPost = apiFetch.mock.calls.filter(
      (args) => args[0] === "/purchasing/requisitions" && args[1]?.method === "POST",
    );
    expect(llamadasPost).toHaveLength(0);
  });

  it("2 · Nueva: envía cuerpo exacto y navega al detalle", async () => {
    apiFetch.mockImplementation((url: string, options?: { method?: string; body?: unknown }) => {
      if (url === "/purchasing/requisitions" && options?.method === "POST") {
        return Promise.resolve({ id: "req-1", code: "REQ-1", status: "DRAFT", warehouse_id: "wh-1" });
      }
      if (url === "/planning/requisitions/req-1") {
        return Promise.resolve({ ...detalleBase });
      }
      return Promise.resolve({ items: [] });
    });

    renderizar("/compras/requisiciones/nueva");

    const codigo = await screen.findByLabelText(/^Código/);
    await userEvent.type(codigo, "REQ-1");

    const almacen = screen.getByLabelText(/^Almacén/);
    await userEvent.selectOptions(almacen, "wh-1");

    await userEvent.click(screen.getByRole("button", { name: /crear requisición/i }));

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith("/purchasing/requisitions", {
        method: "POST",
        body: { code: "REQ-1", warehouse_id: "wh-1", need_date: null },
      });
    });

    expect(await screen.findByText("Requisición REQ-1")).toBeInTheDocument();
    expect(notify).toHaveBeenCalledWith(
      expect.objectContaining({ type: "success", title: "Requisición creada" }),
    );
  });

  it("3 · Detalle: muestra la línea guardada con su instantánea", async () => {
    apiFetch.mockImplementation((url: string) => {
      if (url === "/planning/requisitions/req-1") {
        return Promise.resolve({
          ...detalleBase,
          lines: [
            {
              id: "line-1",
              product_id: "p-1",
              product_code: "P-1",
              product_name: "Producto 1",
              quantity: "12.000000",
              unit_id: "u-1",
              notes: null,
              plan: {
                status: "OK",
                policy_code: "POL-1",
                policy_version: 2,
                recommended_quantity: "12.000000",
                requested_base_quantity: "12.000000",
                difference: "0.000000",
                accepted_recommendation: true,
                calculated_at: "2025-01-15T10:00:00Z",
              },
            },
          ],
        });
      }
      return Promise.resolve({ items: [] });
    });

    renderizar("/compras/requisiciones/req-1");

    expect(await screen.findByText("Requisición REQ-1")).toBeInTheDocument();
    expect(screen.getByText("Sugerencia aceptada")).toBeInTheDocument();
    expect(screen.getByText("POL-1 v2")).toBeInTheDocument();
    expect(screen.getAllByText("12.000000")).toHaveLength(2);
  });

  it("4 · Detalle: usar cantidad sugerida envía el cuerpo esperado", async () => {
    apiFetch.mockImplementation((url: string, options?: { method?: string; body?: unknown }) => {
      if (url === "/planning/requisitions/req-1") {
        return Promise.resolve({ ...detalleBase });
      }
      if (url === "/planning/requisitions/req-1/lines" && options?.method === "POST") {
        return Promise.resolve({ line_id: "line-1", plan: {} });
      }
      if (url === "/planning/plan?warehouse_id=wh-1&product_id=p-1") {
        return Promise.resolve(planOK);
      }
      return Promise.resolve({ items: [] });
    });

    renderizar("/compras/requisiciones/req-1");

    await screen.findByText("Requisición REQ-1");
    await userEvent.type(screen.getByTestId("selector-articulo"), "p-1");

    expect(await screen.findByText("Cantidad sugerida: 12.000000")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /usar cantidad sugerida/i }));

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith("/planning/requisitions/req-1/lines", {
        method: "POST",
        body: {
          product_id: "p-1",
          use_recommendation: true,
          expected_policy_version: 2,
        },
      });
    });
  });

  it("5 · Detalle: cantidad manual envía el cuerpo esperado", async () => {
    apiFetch.mockImplementation((url: string, options?: { method?: string; body?: unknown }) => {
      if (url === "/planning/requisitions/req-1") {
        return Promise.resolve({ ...detalleBase });
      }
      if (url === "/planning/requisitions/req-1/lines" && options?.method === "POST") {
        return Promise.resolve({ line_id: "line-1", plan: {} });
      }
      if (url === "/planning/plan?warehouse_id=wh-1&product_id=p-1") {
        return Promise.resolve(planOK);
      }
      return Promise.resolve({ items: [] });
    });

    renderizar("/compras/requisiciones/req-1");

    await screen.findByText("Requisición REQ-1");
    await userEvent.type(screen.getByTestId("selector-articulo"), "p-1");

    await screen.findByText("Cantidad sugerida: 12.000000");
    await userEvent.type(screen.getByLabelText("Cantidad en unidad base"), "50");
    await userEvent.click(screen.getByRole("button", { name: /agregar con esta cantidad/i }));

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith("/planning/requisitions/req-1/lines", {
        method: "POST",
        body: {
          product_id: "p-1",
          quantity: "50",
          use_recommendation: false,
          expected_policy_version: 2,
        },
      });
    });
  });

  it("6 · Detalle: PLAN_NOT_CONFIGURED muestra aviso y deshabilita sugerencia", async () => {
    apiFetch.mockImplementation((url: string) => {
      if (url === "/planning/requisitions/req-1") {
        return Promise.resolve({ ...detalleBase });
      }
      if (url === "/planning/plan?warehouse_id=wh-1&product_id=p-1") {
        return Promise.resolve({
          ...planOK,
          status: "PLAN_NOT_CONFIGURED",
          policy: null,
          recommended_quantity: null,
        });
      }
      return Promise.resolve({ items: [] });
    });

    renderizar("/compras/requisiciones/req-1");

    await screen.findByText("Requisición REQ-1");
    await userEvent.type(screen.getByTestId("selector-articulo"), "p-1");

    expect(
      await screen.findByText("Sin política de planificación para este almacén: escribe la cantidad a mano."),
    ).toBeInTheDocument();

    const boton = screen.getByRole("button", { name: /usar cantidad sugerida/i });
    expect(boton).toBeDisabled();
  });

  it("7 · Detalle: 409 PLANNING_POLICY_STALE notifica y vuelve a pedir /planning/plan", async () => {
    let contadorPlan = 0;
    apiFetch.mockImplementation((url: string, options?: { method?: string; body?: unknown }) => {
      if (url === "/planning/requisitions/req-1") {
        return Promise.resolve({ ...detalleBase });
      }
      if (url === "/planning/requisitions/req-1/lines" && options?.method === "POST") {
        return Promise.reject(new ApiError(409, { code: "PLANNING_POLICY_STALE", message: "cambió" }));
      }
      if (url === "/planning/plan?warehouse_id=wh-1&product_id=p-1") {
        contadorPlan += 1;
        return Promise.resolve(planOK);
      }
      return Promise.resolve({ items: [] });
    });

    renderizar("/compras/requisiciones/req-1");

    await screen.findByText("Requisición REQ-1");
    await userEvent.type(screen.getByTestId("selector-articulo"), "p-1");

    await screen.findByText("Cantidad sugerida: 12.000000");
    await userEvent.click(screen.getByRole("button", { name: /usar cantidad sugerida/i }));

    await waitFor(() => {
      expect(notify).toHaveBeenCalledWith(
        expect.objectContaining({ description: "Revisa la nueva sugerencia." }),
      );
    });

    await waitFor(() => {
      expect(contadorPlan).toBeGreaterThan(1);
    });
  });

  it("8 · Detalle: APPROVED no muestra Agregar línea", async () => {
    apiFetch.mockImplementation((url: string) => {
      if (url === "/planning/requisitions/req-1") {
        return Promise.resolve({ ...detalleBase, status: "APPROVED" });
      }
      return Promise.resolve({ items: [] });
    });

    renderizar("/compras/requisiciones/req-1");

    await screen.findByText("Requisición REQ-1");
    expect(screen.queryByText("Agregar línea")).not.toBeInTheDocument();
  });
});
