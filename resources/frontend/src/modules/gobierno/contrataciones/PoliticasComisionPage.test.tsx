import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
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

import { PoliticasComisionPage } from "./PoliticasComisionPage";

function renderPage(initialEntries: string[] = ["/politicas"]) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={initialEntries}>
        <Routes>
          <Route path="/politicas" element={<PoliticasComisionPage />} />
          <Route
            path="/gobierno/contrataciones/politicas-comision/:politicaId"
            element={
              <div>
                Ficha de política: política <span>p1</span>
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
  codigo: "PC-2024-01",
  numero_version: 2,
  nombre: "Política de Licitaciones",
  tipo_comision: "ADJUDICACION",
  base_normativa: "LCP_ART14",
  estado: "BORRADOR",
  vigente_desde: "2024-01-01",
  vigente_hasta: null,
  aplica_apertura: true,
  aplica_recomendacion: false,
  version: 1,
  comisiones: 3,
};

const catalogo = {
  estados: [
    { codigo: "BORRADOR", etiqueta: "Borrador" },
    { codigo: "VIGENTE", etiqueta: "Vigente" },
    { codigo: "CERRADA", etiqueta: "Cerrada" },
  ],
  tipos_comision: [{ codigo: "ADJUDICACION", etiqueta: "Adjudicación" }],
  bases_normativas: [{ codigo: "LCP_ART14", etiqueta: "LCP art. 14" }],
  tipos_mayoria: [],
  bases_decision: [],
  funciones: [],
  condiciones: [],
  tipos_requisito: [],
  areas: [],
  etapas: [],
  medios: [],
  acciones_competencia: [],
  materias_competencia: [],
  piso_lcp: {},
};

beforeEach(() => {
  vi.clearAllMocks();
  capacidades.clear();
  capacidades.add("gobierno_comisiones:view");
  capacidades.add("gobierno_comisiones:configure");
});

describe("PoliticasComisionPage", () => {
  it("(a) muestra la fila con enlace al código y «v2»", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url.includes("/catalogo")) return Promise.resolve(catalogo);
      return Promise.resolve({ items: [itemBase], total: 1 });
    });

    renderPage();

    await waitFor(() =>
      expect(screen.getByRole("link", { name: "PC-2024-01" })).toBeInTheDocument(),
    );

    expect(screen.getByRole("link", { name: "PC-2024-01" })).toHaveAttribute(
      "href",
      "/gobierno/contrataciones/politicas-comision/p1",
    );
    expect(screen.getByText("v2")).toBeInTheDocument();
  });

  it("(b) estado vacío con «Nueva política» si configure", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url.includes("/catalogo")) return Promise.resolve(catalogo);
      return Promise.resolve({ items: [], total: 0 });
    });

    renderPage();

    await waitFor(() =>
      expect(screen.getByText("No hay políticas de comisión")).toBeInTheDocument(),
    );

    expect(
      screen.getAllByRole("link", { name: /Nueva política/i }).length,
    ).toBeGreaterThan(0);
  });

  it("(c) filtro de estado incluido en la URL pedida a apiFetch", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url.includes("/catalogo")) return Promise.resolve(catalogo);
      return Promise.resolve({ items: [], total: 0 });
    });

    renderPage();

    await waitFor(() => expect(apiFetchMock).toHaveBeenCalled());

    const select = screen.getByLabelText("Estado");
    await userEvent.selectOptions(select, "BORRADOR");

    await waitFor(() => {
      const calls = apiFetchMock.mock.calls.map((c) => String(c[0]));
      expect(calls.some((u) => u.includes("estado=BORRADOR"))).toBe(true);
    });
  });

  it("(d) sin permiso view → «Sin acceso»", async () => {
    capacidades.clear();

    renderPage();

    expect(screen.getByText("Sin acceso")).toBeInTheDocument();
  });

  it("(e) sin configure no se ofrece «Nueva política»", async () => {
    capacidades.clear();
    capacidades.add("gobierno_comisiones:view");

    apiFetchMock.mockImplementation((url: string) => {
      if (url.includes("/catalogo")) return Promise.resolve(catalogo);
      return Promise.resolve({ items: [], total: 0 });
    });

    renderPage();

    await waitFor(() =>
      expect(screen.getByText("No hay políticas de comisión")).toBeInTheDocument(),
    );

    expect(screen.queryByRole("link", { name: /Nueva política/i })).not.toBeInTheDocument();
  });
});
