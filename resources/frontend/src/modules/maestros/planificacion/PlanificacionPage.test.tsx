import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";

let mockPuede = true;
const apiFetch = vi.fn();
const notify = vi.fn();
const mockAlmacenes = [{ id: "wh-1", code: "ALM1", name: "Central", status: "ACTIVE" }];

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

import { PlanificacionPage } from "./PlanificacionPage";

const politicaEmpresa = {
  id: "pol-1",
  warehouse_id: null,
  warehouse_code: null,
  code: "POL-EMP",
  name: "Política empresa",
  demand_source: "DISPATCHED_SALES",
  lookback_days: 30,
  horizon_days: 15,
  lead_time_days: 5,
  safety_mode: "NONE",
  safety_value: "0",
  rotation_metric: "DEMAND_VELOCITY",
  status: "ACTIVE",
  valid_from: null,
  valid_to: null,
  version: 1,
};

const politicaAlmacen = {
  ...politicaEmpresa,
  id: "pol-2",
  warehouse_id: "wh-1",
  warehouse_code: "ALM1",
  code: "POL-ALM1",
  name: "Política ALM1",
  version: 2,
};

const banda = {
  id: "band-1",
  code: "BND-1",
  name: "Banda uno",
  metric: "DEMAND_VELOCITY",
  lower_bound: "0",
  upper_bound: "10",
  sort_order: 1,
  status: "ACTIVE",
  version: 3,
};

function renderizar(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
  );
}

function mockRespuestas() {
  apiFetch.mockImplementation((url: string, options?: { method?: string }) => {
    if (url === "/planning/policies") {
      if (options?.method === "POST") return Promise.resolve({});
      return Promise.resolve({ items: [politicaEmpresa, politicaAlmacen] });
    }
    if (url === "/planning/rotation-bands") {
      if (options?.method === "POST") return Promise.resolve({});
      return Promise.resolve({ items: [banda] });
    }
    if (url.startsWith("/planning/policies/") && options?.method === "PATCH") {
      return Promise.resolve({});
    }
    if (url.startsWith("/planning/rotation-bands/") && options?.method === "PATCH") {
      return Promise.resolve({});
    }
    return Promise.reject(new Error(`URL no mockeada: ${url}`));
  });
}

describe("PlanificacionPage", () => {
  beforeEach(() => {
    mockPuede = true;
    apiFetch.mockReset();
    notify.mockReset();
    mockRespuestas();
  });

  it("renderiza los dos h2 y los códigos de las políticas y la banda; Empresa y ALM1 en Alcance", async () => {
    renderizar(<PlanificacionPage />);

    expect(await screen.findByRole("heading", { name: "Políticas de planificación" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Bandas de rotación" })).toBeInTheDocument();

    expect(await screen.findByText("POL-EMP")).toBeInTheDocument();
    expect(screen.getByText("POL-ALM1")).toBeInTheDocument();
    expect(screen.getByText("BND-1")).toBeInTheDocument();
    expect(screen.getByText("Empresa")).toBeInTheDocument();
    expect(screen.getByText("ALM1")).toBeInTheDocument();
  });

  it("crear política de empresa con modo DAYS envía el cuerpo EXACTO", async () => {
    const user = userEvent.setup();
    renderizar(<PlanificacionPage />);

    await screen.findByRole("heading", { name: "Políticas de planificación" });

    await user.type(screen.getByLabelText(/^Código de la política/), "POL-DAYS");
    await user.type(screen.getByLabelText(/^Nombre de la política/), "Poli días");
    await user.selectOptions(screen.getByLabelText("Alcance"), "");
    await user.selectOptions(screen.getByLabelText("Fuente de demanda"), "INVENTORY_ISSUES");
    await user.type(screen.getByLabelText(/^Días de histórico/), "45");
    await user.type(screen.getByLabelText(/^Días de horizonte/), "20");
    await user.type(screen.getByLabelText(/^Plazo de reposición/), "3");
    await user.selectOptions(screen.getByLabelText("Stock de seguridad"), "DAYS");
    await user.type(await screen.findByLabelText(/^Valor de seguridad/), "7.5");
    await user.selectOptions(screen.getByLabelText("Métrica de rotación"), "TURNOVER");

    await user.click(screen.getByRole("button", { name: "Crear política" }));

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/planning/policies",
        expect.objectContaining({
          method: "POST",
          body: {
            code: "POL-DAYS",
            name: "Poli días",
            warehouse_id: null,
            demand_source: "INVENTORY_ISSUES",
            lookback_days: 45,
            horizon_days: 20,
            lead_time_days: 3,
            safety_mode: "DAYS",
            safety_value: "7.5",
            rotation_metric: "TURNOVER",
            status: "ACTIVE",
            valid_from: null,
            valid_to: null,
          },
        }),
      );
    });
  });

  it("con campos vacíos no hay POST y aparece Campo obligatorio", async () => {
    const user = userEvent.setup();
    renderizar(<PlanificacionPage />);

    await screen.findByRole("heading", { name: "Políticas de planificación" });
    await user.click(screen.getByRole("button", { name: "Crear política" }));

    expect(screen.getAllByText("Campo obligatorio").length).toBeGreaterThan(0);
    expect(apiFetch).not.toHaveBeenCalledWith("/planning/policies", expect.objectContaining({ method: "POST" }));
  });

  it("modo NONE oculta Valor de seguridad y envía safety_value 0", async () => {
    const user = userEvent.setup();
    renderizar(<PlanificacionPage />);

    await screen.findByRole("heading", { name: "Políticas de planificación" });

    await user.type(screen.getByLabelText(/^Código de la política/), "POL-NONE");
    await user.type(screen.getByLabelText(/^Nombre de la política/), "Poli none");
    await user.type(screen.getByLabelText(/^Días de histórico/), "30");
    await user.type(screen.getByLabelText(/^Días de horizonte/), "15");
    await user.type(screen.getByLabelText(/^Plazo de reposición/), "2");

    expect(screen.queryByLabelText(/^Valor de seguridad/)).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Crear política" }));

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/planning/policies",
        expect.objectContaining({
          method: "POST",
          body: expect.objectContaining({ safety_mode: "NONE", safety_value: "0" }),
        }),
      );
    });
  });

  it("crear banda con Hasta vacío envía upper_bound null y sort_order 0", async () => {
    const user = userEvent.setup();
    renderizar(<PlanificacionPage />);

    await screen.findByRole("heading", { name: "Bandas de rotación" });

    await user.type(screen.getByLabelText(/^Código de la banda/), "BND-X");
    await user.type(screen.getByLabelText(/^Nombre de la banda/), "Banda sin tope");
    await user.type(screen.getByLabelText(/^Desde \(incluido\)/), "5");

    await user.click(screen.getByRole("button", { name: "Crear banda" }));

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/planning/rotation-bands",
        expect.objectContaining({
          method: "POST",
          body: {
            code: "BND-X",
            name: "Banda sin tope",
            metric: "DEMAND_VELOCITY",
            lower_bound: "5",
            upper_bound: null,
            sort_order: 0,
            status: "ACTIVE",
          },
        }),
      );
    });
  });

  it("Desactivar POL-EMP hace PATCH con expected_version 1 y status INACTIVE", async () => {
    const user = userEvent.setup();
    renderizar(<PlanificacionPage />);

    await screen.findByText("POL-EMP");
    await user.click(screen.getByRole("button", { name: "Desactivar POL-EMP" }));

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/planning/policies/pol-1",
        expect.objectContaining({
          method: "PATCH",
          body: { expected_version: 1, status: "INACTIVE" },
        }),
      );
    });
  });

  it("con mockPuede false no aparecen Crear política ni Crear banda", async () => {
    mockPuede = false;
    renderizar(<PlanificacionPage />);

    await screen.findByRole("heading", { name: "Políticas de planificación" });
    expect(screen.queryByRole("button", { name: "Crear política" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Crear banda" })).not.toBeInTheDocument();
  });
});
