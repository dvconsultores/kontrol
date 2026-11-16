import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router";

import { ApiError } from "@/api/client";

import { AlertasContrato } from "./AlertasContrato";

const apiFetchMock = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
  ApiError: (await original<typeof import("@/api/client")>()).ApiError,
}));

let capacidades = new Set<string>();

vi.mock("@/app/autoridad/AutoridadContext", () => ({
  useAutoridad: () => ({
    estado: "LISTA",
    tiene: (c: string) => capacidades.has(c),
    puede: () => true,
    motivo: () => null,
    motivoDeCapacidad: () => null,
  }),
}));

vi.mock("@/app/contexts/CompanyContext", () => ({
  useCompany: () => ({ activeCompanyId: "c1", activeCompany: { id: "c1", legal_name: "Ente 1" } }),
}));

function renderComponente(): void {
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter>
        <AlertasContrato contratoId="c1" />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  apiFetchMock.mockReset();
  capacidades = new Set(["gobierno_contratos:view", "alertas:view", "gobierno_expedientes:view"]);
});

describe("AlertasContrato", () => {
  it("muestra las alertas activas del contrato", async () => {
    apiFetchMock.mockResolvedValue({
      contrato_id: "c1",
      activas: 1,
      items: [
        {
          id: "a1",
          severity: "WARNING",
          status: "ACTIVE",
          category: "gov.milestone.deadline",
          created_at: "2026-11-16T10:00:00Z",
          message: { text: "El hito HIT-01 del contrato CT-2026-0001 vence hoy (16/11/2026)." },
          link: {
            source_type: "GovernmentContractMilestone",
            source_id: "c1",
            source_item_id: "h1",
            route_key: "gov_contract_execution",
          },
        },
      ],
    });

    renderComponente();

    expect(screen.getByRole("heading", { name: "Alertas de vencimiento" })).toBeTruthy();
    await waitFor(() => expect(screen.getByText("Alertas activas: 1")).toBeTruthy());
    expect(screen.getByText("El hito HIT-01 del contrato CT-2026-0001 vence hoy (16/11/2026).")).toBeTruthy();
    expect(screen.getByText("Advertencia")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Abrir origen" }).getAttribute("href")).toBe("/gobierno/contratos/c1/ejecucion");
    expect(apiFetchMock).toHaveBeenCalledWith("/gobierno/contratos/c1/alertas");
  });

  it("muestra cero alertas activas si no hay items", async () => {
    apiFetchMock.mockResolvedValue({ contrato_id: "c1", activas: 0, items: [] });

    renderComponente();

    await waitFor(() => expect(screen.getByText("Alertas activas: 0")).toBeTruthy());
    expect(screen.getByText("Sin alertas activas.")).toBeTruthy();
  });

  it("muestra mensaje de error si la consulta falla", async () => {
    apiFetchMock.mockRejectedValue(new ApiError(404, { code: "GOV_CONTRACT_NOT_FOUND", message: "x" }));

    renderComponente();

    await waitFor(() =>
      expect(screen.getByRole("alert").textContent).toContain("No fue posible consultar las alertas del contrato."),
    );
  });

  it("no muestra el enlace a todas las alertas sin la capacidad alertas:view", async () => {
    capacidades = new Set(["gobierno_contratos:view", "gobierno_expedientes:view"]);
    apiFetchMock.mockResolvedValue({ contrato_id: "c1", activas: 0, items: [] });

    renderComponente();

    await waitFor(() => expect(screen.getByText("Alertas activas: 0")).toBeTruthy());
    expect(screen.queryByRole("link", { name: "Ver todas las alertas" })).toBeNull();
  });
});
