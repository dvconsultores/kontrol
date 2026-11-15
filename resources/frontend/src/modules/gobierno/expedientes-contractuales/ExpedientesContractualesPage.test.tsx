import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ExpedientesContractualesPage } from "./ExpedientesContractualesPage";
import type { ListaExpedientes } from "./api";

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

function lista(over: Partial<ListaExpedientes> = {}): ListaExpedientes {
  return {
    items: [
      {
        id: "k1",
        codigo: "CT-2026-0001",
        tipo: "CONTRATO",
        tipo_etiqueta: "Contrato",
        contratista: { nombre: "Constructora Andina", documento: "1790012345001" },
        objeto: "Construcción de puente",
        monto_original: "50000.00",
        monto_vigente: "60000.00",
        moneda: "USD",
        fecha_inicio: "2026-01-01",
        fecha_fin_original: "2026-06-30",
        fecha_fin_vigente: "2026-07-30",
        vigencia: "EN_PLAZO",
        vigencia_etiqueta: "En plazo",
        supervisor: { nombre: "María Pérez", cargo: "Directora" },
        expediente: { id: "e1", numero: "EXP-2026-0001" },
        fecha_formalizacion: "2026-01-10",
        modificaciones: 2,
        ultimo_paquete: { codigo: "EC-2026-0001", generado_en: "2026-02-01T10:00:00Z", verificacion: "VALIDO" },
        ultima_actuacion: { fecha: "2026-02-01", titulo: "Paquete generado", proceso: "CNT-08" },
      },
    ],
    total: 1,
    limit: 25,
    offset: 0,
    ...over,
  };
}

function renderConProvider() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/gobierno/expedientes-contractuales"]}>
        <ExpedientesContractualesPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return queryClient;
}

beforeEach(() => {
  apiFetchMock.mockReset();
  capacidades = new Set(["gobierno_contratos:view"]);
});

describe("ExpedientesContractualesPage", () => {
  it("muestra la tabla con el código como enlace y el resumen de paginación", async () => {
    apiFetchMock.mockResolvedValue(lista());
    renderConProvider();

    const enlace = await screen.findByRole("link", { name: "CT-2026-0001" });
    expect(enlace).toHaveAttribute("href", "/gobierno/contratos/k1/expediente");
    expect(screen.getByText("Mostrando 1–1 de 1")).toBeInTheDocument();
  });

  it("al filtrar por contratista y Buscar la llamada incluye contratista y offset=0", async () => {
    apiFetchMock.mockResolvedValue(lista());
    const user = userEvent.setup();
    renderConProvider();

    await user.type(await screen.findByLabelText("Contratista"), "Andina");
    await user.click(screen.getByRole("button", { name: "Buscar" }));

    await waitFor(() => {
      const llamada = [...apiFetchMock.mock.calls].reverse().find(([ruta]) =>
        String(ruta).includes("/gobierno/expedientes-contractuales?"),
      );
      expect(llamada).toBeTruthy();
      expect(String(llamada?.[0])).toContain("contratista=Andina");
      expect(String(llamada?.[0])).toContain("offset=0");
    });
  });

  it("sin permiso muestra Sin acceso", async () => {
    capacidades = new Set();
    renderConProvider();
    expect(await screen.findByText("Sin acceso")).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });
});
