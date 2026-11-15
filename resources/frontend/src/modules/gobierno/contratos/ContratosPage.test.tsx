import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ContratosPage } from "./ContratosPage";
import type { ContratoResumen } from "./api";

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

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify: vi.fn() }),
}));

function crearResumen(over?: Partial<ContratoResumen>): ContratoResumen {
  return {
    id: "k1",
    identificacion: "Borrador · EXP-1 · DEC-01",
    codigo: null,
    estado: "BORRADOR",
    estado_etiqueta: "Borrador",
    tipo: "CONTRATO",
    tipo_etiqueta: "Contrato",
    expediente_numero: "EXP-1",
    decision_referencia: "DEC-01",
    contratista_nombre: "Constructora Andina",
    monto: "50000.00",
    moneda: "USD",
    fecha_inicio: null,
    fecha_fin: null,
    ...over,
  };
}

function renderizar() {
  const cliente = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={cliente}>
      <MemoryRouter>
        <ContratosPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ContratosPage", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    capacidades = new Set(["gobierno_contratos:view"]);
  });

  it("lista filas con identificacion y monto", async () => {
    apiFetchMock.mockResolvedValue({ items: [crearResumen()] });
    renderizar();

    expect(await screen.findByText("Borrador · EXP-1 · DEC-01")).toBeInTheDocument();
    expect(screen.getByText("50000.00 USD")).toBeInTheDocument();
  });

  it("sin permiso muestra «Sin acceso»", async () => {
    capacidades = new Set();
    renderizar();

    expect(await screen.findByText("Sin acceso")).toBeInTheDocument();
  });

  it("al cambiar el filtro de estado se llama a apiFetch con una ruta que contiene estado=FORMALIZADO", async () => {
    apiFetchMock.mockResolvedValue({ items: [] });
    const usuario = userEvent.setup();
    renderizar();

    await screen.findByLabelText("Estado");
    await usuario.selectOptions(screen.getByLabelText("Estado"), "FORMALIZADO");

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(expect.stringContaining("estado=FORMALIZADO"));
    });
  });
});
