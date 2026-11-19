import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiFetchMock = vi.fn();
vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}));

vi.mock("@/app/contexts/CompanyContext", () => ({
  useCompany: () => ({
    activeCompanyId: "c1",
    activeCompany: { id: "c1", legal_name: "Contenedor 1" },
  }),
}));

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({
    notify: vi.fn(),
  }),
}));

const capacidades = new Set<string>();

vi.mock("@/app/autoridad/AutoridadContext", () => ({
  useAutoridad: () => ({
    estado: "LISTA",
    tiene: (c: string) => capacidades.has(c),
    puede: () => true,
    motivo: () => null,
    motivoDeCapacidad: () => null,
  }),
}));

import { PoliticasAsignacionPage } from "./PoliticasAsignacionPage";

function renderPage(initialEntries: string[] = ["/politicas"]) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={initialEntries}>
        <Routes>
          <Route path="/politicas" element={<PoliticasAsignacionPage />} />
          <Route
            path="/gobierno/ocupacion/politicas/:politicaId"
            element={
              <div>
                Ficha de política: <span>p1</span>
              </div>
            }
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const itemBase = {
  id: "p1",
  codigo: "PA-2024-01",
  numero_version: 1,
  nombre: "Política de Suplencias",
  figura: "SUPLENCIA",
  figura_etiqueta: "Suplencia",
  estado: "VIGENTE",
  estado_etiqueta: "Vigente",
  vigente_desde: "2024-01-01",
  vigente_hasta: null,
  version: 1,
  asignaciones: 2,
};

const catalogo = {
  figuras: [
    { codigo: "SUPLENCIA", etiqueta: "Suplencia" },
    { codigo: "ENCARGADURIA", etiqueta: "Encargaduría" },
  ],
  estados: [
    { codigo: "BORRADOR", etiqueta: "Borrador" },
    { codigo: "VIGENTE", etiqueta: "Vigente" },
    { codigo: "CERRADA", etiqueta: "Cerrada" },
  ],
  medios: [],
  emisor_tipos: [],
  ambitos: [],
  etapas: [],
  acciones: [],
  materias: [],
};

beforeEach(() => {
  vi.clearAllMocks();
  capacidades.clear();
  capacidades.add("gobierno_ocupacion:view");
  capacidades.add("gobierno_ocupacion:configure");
});

describe("PoliticasAsignacionPage", () => {
  it("(1) pinta filas con código, figura y «v1»", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url.includes("/catalogo")) return Promise.resolve(catalogo);
      return Promise.resolve({ items: [itemBase], total: 1 });
    });

    renderPage();

    await waitFor(() =>
      expect(screen.getByRole("link", { name: "PA-2024-01" })).toBeInTheDocument(),
    );

    expect(screen.getByRole("link", { name: "PA-2024-01" })).toHaveAttribute(
      "href",
      "/gobierno/ocupacion/politicas/p1",
    );
    const tabla = screen.getByRole("table", { name: "Tabla de políticas de asignación" });
    expect(within(tabla).getByText("Suplencia")).toBeInTheDocument();
    expect(screen.getByText("v1")).toBeInTheDocument();
  });

  it("(2) oculta «Nueva política» sin permiso configure", async () => {
    capacidades.delete("gobierno_ocupacion:configure");

    apiFetchMock.mockImplementation((url: string) => {
      if (url.includes("/catalogo")) return Promise.resolve(catalogo);
      return Promise.resolve({ items: [itemBase], total: 1 });
    });

    renderPage();

    await waitFor(() =>
      expect(screen.getByRole("link", { name: "PA-2024-01" })).toBeInTheDocument(),
    );

    expect(screen.queryByRole("link", { name: /Nueva política/i })).not.toBeInTheDocument();
  });

  it("(3) muestra el estado vacío con el texto de pisos legales", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url.includes("/catalogo")) return Promise.resolve(catalogo);
      return Promise.resolve({ items: [], total: 0 });
    });

    renderPage();

    await waitFor(() =>
      expect(screen.getByText("No hay políticas de asignación")).toBeInTheDocument(),
    );

    expect(
      screen.getByText(/Sin política, cada asignación aplica solo los pisos legales del régimen del ente/i),
    ).toBeInTheDocument();
  });

  it("(4) filtrar por figura llama a la URL con `figura=SUPLENCIA`", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url.includes("/catalogo")) return Promise.resolve(catalogo);
      return Promise.resolve({ items: [], total: 0 });
    });

    renderPage();

    await waitFor(() => expect(apiFetchMock).toHaveBeenCalled());

    const select = screen.getByLabelText("Figura");
    await screen.findByRole("option", { name: "Suplencia" });
    await userEvent.selectOptions(select, "SUPLENCIA");

    await waitFor(() => {
      const calls = apiFetchMock.mock.calls.map((c) => String(c[0]));
      expect(calls.some((u) => u.includes("figura=SUPLENCIA"))).toBe(true);
    });
  });
});
