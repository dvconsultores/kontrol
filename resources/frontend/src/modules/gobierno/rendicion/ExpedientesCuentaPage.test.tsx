import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Routes, Route } from "react-router";

const apiFetchMock = vi.fn();
vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
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
  useCompany: () => ({
    activeCompanyId: "c1",
    activeCompany: { id: "c1", legal_name: "Contenedor 1" },
  }),
}));

import { ExpedientesCuentaPage } from "./ExpedientesCuentaPage";

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/gobierno/rendicion"]}>
        <Routes>
          <Route path="/gobierno/rendicion" element={<ExpedientesCuentaPage />} />
          <Route path="/gobierno/rendicion/nuevo" element={<div>NUEVO</div>} />
          <Route path="/gobierno/rendicion/:expedienteId" element={<div>FICHA</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const fichaBase = {
  id: "e1",
  codigo: "EXP-001",
  numero_version: 1,
  version: "v1",
  estado: "EN_FORMACION",
  anterior_id: null,
  sustituido_por_id: null,
  sustitucion_motivo: null,
  denominacion: "Cuenta 2024",
  ejercicio: 2024,
  periodo_desde: "2024-01-01",
  periodo_hasta: "2024-12-31",
  fecha_corte: "2024-12-31",
  observaciones: null,
  ente: "Municipio X",
  responsable: {
    funcionario: "Ana Ruiz",
    funcionario_codigo: "F1",
    cargo: "Directora",
    cargo_codigo: "C1",
    unidad: "Finanzas",
    unidad_codigo: "U1",
    figura: "Responsable",
    asignacion_codigo: "A1",
  },
  piezas: [],
  formado_en: null,
  formado_por: null,
  snapshot_sha256: null,
  informe: null,
  participacion: null,
  plazo_participacion: "2025-02-15",
  calificacion: null,
  fenecimiento: null,
  hallazgos: [],
};

const opciones = {
  responsables: [
    { asignacion_id: "a1", codigo: "A1", funcionario: "Ana Ruiz", cargo: "Directora", unidad: "Finanzas", figura: "Responsable", desde: "2024-01-01", hasta: null, official_id: "off1", unidad_id: "u1" },
  ],
  procesos: [],
  estados: ["EN_FORMACION", "FORMADA"],
};

describe("ExpedientesCuentaPage", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    capacidades = new Set(["gobierno_rendicion:view"]);
  });

  it("lista un item con su codigo y estado", async () => {
    apiFetchMock.mockImplementation((path: string) => {
      if (path.includes("/opciones")) return Promise.resolve(opciones);
      if (path.includes("/expedientes")) return Promise.resolve({ items: [fichaBase], total: 1, pagina: 1, por_pagina: 20 });
      return Promise.reject(new Error("Ruta inesperada"));
    });

    renderPage();

    await waitFor(() => expect(screen.getByText("EXP-001 · v1")).toBeTruthy());
    expect(within(screen.getByRole("listitem")).getByText("En formación")).toBeTruthy();
  });

  it("sin capacidad form no muestra Nuevo expediente", async () => {
    apiFetchMock.mockImplementation((path: string) => {
      if (path.includes("/opciones")) return Promise.resolve(opciones);
      if (path.includes("/expedientes")) return Promise.resolve({ items: [], total: 0, pagina: 1, por_pagina: 20 });
      return Promise.reject(new Error("Ruta inesperada"));
    });

    renderPage();

    await waitFor(() => expect(screen.queryByText("Nuevo expediente")).toBeNull());
  });

  it("con form muestra Nuevo expediente", async () => {
    capacidades.add("gobierno_rendicion:form");
    apiFetchMock.mockImplementation((path: string) => {
      if (path.includes("/opciones")) return Promise.resolve(opciones);
      if (path.includes("/expedientes")) return Promise.resolve({ items: [], total: 0, pagina: 1, por_pagina: 20 });
      return Promise.reject(new Error("Ruta inesperada"));
    });

    renderPage();

    await waitFor(() => expect(screen.getByText("Nuevo expediente")).toBeTruthy());
  });
});
