import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

beforeAll(async () => {
  await Promise.all([
    import("../requisiciones/RequisicionNuevaPage"),
    import("../requisiciones/RequisicionDetallePage"),
    import("./NecesidadesPage"),
    import("./NecesidadDetallePage"),
  ]);
});

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createMemoryRouter, RouterProvider } from "react-router";

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

const needBase = {
  id: "need-1",
  status: "ACTIVE",
  trigger_method: "POLICY",
  triggered_at: "2025-01-01T10:00:00",
  resolved_at: null,
  resolution_reason: null,
  last_evaluated_at: "2025-01-02T10:00:00",
  product: { id: "p-1", code: "P-1", name: "Producto 1" },
  warehouse: { id: "wh-1", code: "ALM1", name: "Central" },
  trigger: {
    policy_id: "pol-1",
    policy_code: "POL-1",
    policy_version: 2,
    available: "7.000000",
    on_hand: "8.000000",
    reserved: "1.000000",
    reorder_point: "20.000000",
    projected_demand: "46.666662",
    avg_daily_demand: "3.333333",
    safety_stock: "10.000000",
    recommended_quantity: "12.000000",
    rotation_band_code: "RB-1",
    calculated_at: "2025-01-01T10:00:00",
  },
  current: {
    policy_version: 2,
    available: "7.000000",
    reorder_point: "20.000000",
    projected_demand: "46.666662",
    recommended_quantity: "12.000000",
    rotation_band_code: "RB-1",
  },
  alert_id: "alert-1",
  trigger_snapshot: {},
  requisitions: [],
};

const detalleRequisicionBase = {
  id: "req-1",
  code: "REQ-1",
  status: "DRAFT",
  warehouse_id: "wh-1",
  warehouse_code: "ALM1",
  need_date: null,
  lines: [],
};

function crearRouter(rutaInicial: string) {
  return createMemoryRouter(
    [
      {
        path: "/compras/planificacion/necesidades",
        lazy: async () => {
          const { NecesidadesPage } = await import("./NecesidadesPage");
          return { Component: NecesidadesPage };
        },
      },
      {
        path: "/compras/planificacion/necesidades/:needId",
        lazy: async () => {
          const { NecesidadDetallePage } = await import("./NecesidadDetallePage");
          return { Component: NecesidadDetallePage };
        },
      },
      {
        path: "/compras/requisiciones/nueva",
        lazy: async () => {
          const { RequisicionNuevaPage } = await import("../requisiciones/RequisicionNuevaPage");
          return { Component: RequisicionNuevaPage };
        },
      },
      {
        path: "/compras/requisiciones/:requisitionId",
        lazy: async () => {
          const { RequisicionDetallePage } = await import("../requisiciones/RequisicionDetallePage");
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

describe("Necesidades de reposición", () => {
  it("1 lista: muestra producto, estado, sugerido y Ver; el filtro Resueltas pide status=RESOLVED", async () => {
    apiFetch.mockImplementation((url: string) => {
      if (url.includes("/planning/replenishment-needs")) {
        return Promise.resolve({ items: [needBase], total: 1, page: 1, page_size: 20 });
      }
      return Promise.reject(new Error("no mock"));
    });

    const user = userEvent.setup();
    renderizar("/compras/planificacion/necesidades");

    await screen.findByText("P-1 · Producto 1");
    expect(screen.getByText("Necesita reposición")).toBeTruthy();
    expect(screen.getByText("12.000000")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Ver" })).toBeTruthy();

    expect(apiFetch).toHaveBeenCalledWith(expect.stringContaining("status=ACTIVE"));

    await user.selectOptions(screen.getByLabelText(/^Estado/), "RESOLVED");
    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(expect.stringContaining("status=RESOLVED"));
    });
  });

  it("2 detalle: muestra la frase exacta y Crear requisición; sin permiso no aparece", async () => {
    apiFetch.mockImplementation((url: string) => {
      if (url.includes("/planning/replenishment-needs/need-1")) {
        return Promise.resolve(needBase);
      }
      return Promise.reject(new Error("no mock"));
    });

    const primero = renderizar("/compras/planificacion/necesidades/need-1");

    await screen.findByText(
      "Se generó porque el disponible (7.000000) era menor o igual que el punto de reorden (20.000000), con la política POL-1 v2.",
    );
    expect(screen.getByText("Crear requisición")).toBeTruthy();

    primero.unmount();
    mockPuede = false;
    renderizar("/compras/planificacion/necesidades/need-1");
    await screen.findByText("Por qué se generó");
    expect(screen.queryByText("Crear requisición")).toBeNull();
  });

  it("3 detalle RESOLVED: muestra motivo y no muestra Crear requisición", async () => {
    apiFetch.mockImplementation((url: string) => {
      if (url.includes("/planning/replenishment-needs/need-1")) {
        return Promise.resolve({
          ...needBase,
          status: "RESOLVED",
          resolution_reason: "CONDITION_CLEARED",
          resolved_at: "2025-01-03T10:00:00",
        });
      }
      return Promise.reject(new Error("no mock"));
    });

    renderizar("/compras/planificacion/necesidades/need-1");

    await screen.findByText(/^Resuelta: La condición dejó de cumplirse/);
    expect(screen.queryByText("Crear requisición")).toBeNull();
  });

  it("4 Crear requisición: preselecciona almacén, muestra aviso y crea con ?necesidad", async () => {
    apiFetch.mockImplementation((url: string) => {
      if (url.includes("/planning/replenishment-needs/need-1")) {
        return Promise.resolve(needBase);
      }
      if (url.includes("/purchasing/requisitions")) {
        return Promise.resolve({ id: "req-1" });
      }
      if (url.includes("/planning/requisitions/req-1")) {
        return Promise.resolve(detalleRequisicionBase);
      }
      return Promise.reject(new Error("no mock"));
    });

    const user = userEvent.setup();
    renderizar(`/compras/requisiciones/nueva?necesidad=${needBase.id}`);

    await screen.findByText(
      `Desde la necesidad de reposición de ${needBase.product.code} · ${needBase.product.name} en ${needBase.warehouse.code}.`,
    );
    expect(screen.getByLabelText(/^Almacén/)).toHaveValue("wh-1");

    await user.type(screen.getByLabelText(/^Código/), "REQ-1");
    await user.click(screen.getByText("Crear requisición"));

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith("/purchasing/requisitions", {
        method: "POST",
        body: { code: "REQ-1", warehouse_id: "wh-1", need_date: null },
      });
    });
    await screen.findByText("Requisición REQ-1");
  });

  it("5 detalle de requisición con ?necesidad: precarga producto y cantidad; envía replenishment_need_id", async () => {
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

    apiFetch.mockImplementation((url: string, options?: { method?: string; body?: unknown }) => {
      if (url.includes("/planning/replenishment-needs/need-1")) {
        return Promise.resolve(needBase);
      }
      if (url.includes("/planning/plan")) {
        return Promise.resolve(planOK);
      }
      if (url.includes("/planning/requisitions/req-1")) {
        if (options?.method === "POST") {
          return Promise.resolve({});
        }
        return Promise.resolve(detalleRequisicionBase);
      }
      return Promise.reject(new Error("no mock"));
    });

    const user = userEvent.setup();
    renderizar(`/compras/requisiciones/req-1?necesidad=${needBase.id}`);

    await screen.findByText("Línea para la necesidad de reposición de P-1. Puedes cambiar la cantidad.");
    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith(expect.stringContaining("/planning/plan?")));

    await waitFor(() => {
      const selector = screen.getByTestId("selector-articulo") as HTMLInputElement;
      expect(selector.value).toBe("p-1");
    });
    expect(screen.getByLabelText(/^Cantidad en unidad base/)).toHaveValue(12);

    await user.click(screen.getByText("Agregar con esta cantidad"));

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith("/planning/requisitions/req-1/lines", {
        method: "POST",
        body: {
          product_id: "p-1",
          quantity: "12",
          use_recommendation: false,
          expected_policy_version: 2,
          replenishment_need_id: "need-1",
        },
      });
    });
  });

  it("6 notificaciones: destinoDeEnlace para replenishment_need", async () => {
    const { destinoDeEnlace } = await import("@/modules/notificaciones/api");
    const destino = destinoDeEnlace({
      route_key: "replenishment_need",
      source_id: "need-1",
    } as never);
    expect(destino).toEqual({
      ruta: "/compras/planificacion/necesidades/need-1",
      permiso: "compras:view",
    });
  });
});
