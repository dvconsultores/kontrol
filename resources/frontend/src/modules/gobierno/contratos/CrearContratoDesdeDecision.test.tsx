import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CrearContratoDesdeDecision } from "./CrearContratoDesdeDecision";

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

function renderizar(
  props: {
    expedienteId: string;
    contrato: { id: string; identificacion: string; estado: string } | null;
    onCreado?: () => void;
  },
) {
  const cliente = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={cliente}>
      <MemoryRouter>
        <CrearContratoDesdeDecision {...props} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("CrearContratoDesdeDecision", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    capacidades = new Set(["gobierno_contratos:manage"]);
  });

  it("con contrato muestra Link «Ver contrato u orden»", () => {
    renderizar({
      expedienteId: "e1",
      contrato: { id: "k1", identificacion: "Borrador · EXP-1 · DEC-01", estado: "BORRADOR" },
    });

    expect(screen.getByRole("link", { name: "Ver contrato u orden" })).toBeInTheDocument();
  });

  it("sin contrato y con manage el botón hace POST /gobierno/contratos con expediente_id e1", async () => {
    apiFetchMock.mockResolvedValue({ id: "k1" });
    const usuario = userEvent.setup();
    renderizar({ expedienteId: "e1", contrato: null, onCreado: vi.fn() });

    await usuario.click(screen.getByRole("button", { name: "Crear contrato u orden" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/contratos",
        expect.objectContaining({ method: "POST", body: { expediente_id: "e1" } }),
      );
    });
  });

  it("sin permiso muestra el texto informativo", () => {
    capacidades = new Set();
    renderizar({ expedienteId: "e1", contrato: null });

    expect(screen.getByText("El contrato u orden lo crea la Unidad Contratante desde aquí.")).toBeInTheDocument();
  });
});
