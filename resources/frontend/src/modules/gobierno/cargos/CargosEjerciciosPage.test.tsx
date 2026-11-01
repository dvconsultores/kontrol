import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";

const apiFetch = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetch(...args),
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

const notify = vi.fn();

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify }),
}));

vi.mock("@/app/contexts/CompanyContext", () => ({
  useCompany: () => ({
    activeCompanyId: "c1",
    activeCompany: { id: "c1", legal_name: "Contenedor 1" },
  }),
}));

vi.mock("@/modules/documentos/AdjuntosPanel", () => ({
  AdjuntosPanel: (p: { resourceType: string; resourceId: string }) => (
    <div data-testid="adjuntos">{`${p.resourceType}:${p.resourceId}`}</div>
  ),
}));

vi.mock("@/api/descargas", () => ({
  descargarArchivo: () => Promise.resolve("x.csv"),
}));

const { CargosEjerciciosPage } = await import("./CargosEjerciciosPage");

const ESTRUCTURAS = {
  items: [
    {
      id: "s1",
      ejercicio: 2025,
      estado: "CERRADA",
      version: 2,
      publicada_en: "2025-01-10",
      cerrada_en: "2026-01-05",
    },
    {
      id: "s2",
      ejercicio: 2026,
      estado: "VIGENTE",
      version: 3,
      publicada_en: "2026-01-08",
      cerrada_en: null,
    },
  ],
};

function montar(rutaInicial = "/gobierno/cargos"): void {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[rutaInicial]}>
        <Routes>
          <Route path="/gobierno/cargos" element={<CargosEjerciciosPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function responderEstructuras(body: unknown): void {
  apiFetch.mockImplementation((ruta: string) => {
    if (ruta === "/gobierno/estructuras") {
      return Promise.resolve(body);
    }
    return Promise.reject(new Error(`ruta inesperada ${ruta}`));
  });
}

beforeEach(() => {
  apiFetch.mockReset();
  notify.mockReset();
  capacidades = new Set<string>();
});

describe("CargosEjerciciosPage", () => {
  it("GCE-01 · lista ejercicios 2026 y 2025 ordenados descendentemente", async () => {
    capacidades = new Set(["gobierno_cargos:view"]);
    responderEstructuras(ESTRUCTURAS);
    montar();
    const enlaces = await screen.findAllByRole("link", { name: /^Cargos \d{4}$/ });
    expect(enlaces).toHaveLength(2);
    expect(enlaces[0]).toHaveTextContent("Cargos 2026");
    expect(enlaces[1]).toHaveTextContent("Cargos 2025");
    expect(enlaces[0]).toHaveAttribute("href", "/gobierno/cargos/2026");
    expect(enlaces[1]).toHaveAttribute("href", "/gobierno/cargos/2025");
  });

  it("GCE-02 · sin estructuras muestra Aún no hay estructuras y enlace", async () => {
    capacidades = new Set(["gobierno_cargos:view"]);
    responderEstructuras({ items: [] });
    montar();
    expect(await screen.findByText("Aún no hay estructuras")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ir a Estructura organizativa" })).toHaveAttribute(
      "href",
      "/gobierno/estructura",
    );
  });

  it("GCE-03 · 404 GOV_ENTITY_NOT_FOUND muestra configurar ente", async () => {
    capacidades = new Set(["gobierno_cargos:view"]);
    apiFetch.mockImplementation((ruta: string) => {
      if (ruta === "/gobierno/estructuras") {
        return Promise.reject(new ApiError(404, { code: "GOV_ENTITY_NOT_FOUND", message: "x" }));
      }
      return Promise.reject(new Error(`ruta inesperada ${ruta}`));
    });
    montar();
    expect(await screen.findByText("Primero configure el ente")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ir a Configuración del ente" })).toHaveAttribute(
      "href",
      "/gobierno/ente",
    );
  });

  it("GCE-04 · sin gobierno_cargos:view muestra Sin acceso", async () => {
    responderEstructuras(ESTRUCTURAS);
    montar();
    expect(await screen.findByText("Sin acceso")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /^Cargos \d{4}$/ })).toBeNull();
  });
});
