import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

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

import { ActasEntregaPage } from "./ActasEntregaPage";

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/gobierno/actas-entrega"]}>
        <Routes>
          <Route path="/gobierno/actas-entrega" element={<ActasEntregaPage />} />
          <Route path="/gobierno/actas-entrega/nueva" element={<div>NUEVA</div>} />
          <Route path="/gobierno/actas-entrega/:actaId" element={<div>FICHA</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const actaBase = {
  id: "a1",
  codigo: "ACT-001",
  estado: "BORRADOR",
  ambito: "UNIDAD",
  unidad: "Finanzas",
  saliente: {
    funcionario: "Ana Ruiz",
    funcionario_codigo: "F1",
    cargo: "Directora",
    cargo_codigo: "C1",
    unidad: "Finanzas",
    unidad_codigo: "U1",
    figura: "Responsable",
    asignacion_codigo: "A1",
  },
  receptor: {
    funcionario: "Luis Pérez",
    funcionario_codigo: "F2",
  },
  fecha_corte: "2024-12-31",
  fecha_suscripcion: null,
};

const opciones = {
  ocupaciones: [],
  funcionarios: [],
  anexos: [],
  nivel_territorial: null,
};

describe("ActasEntregaPage", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    capacidades = new Set(["gobierno_actas:view"]);
  });

  it("lista un item con su codigo y estado", async () => {
    apiFetchMock.mockImplementation((path: string) => {
      if (path.includes("/opciones")) return Promise.resolve(opciones);
      if (path.includes("/actas")) return Promise.resolve({ items: [actaBase], total: 1, pagina: 1, por_pagina: 20 });
      return Promise.reject(new Error("Ruta inesperada"));
    });

    renderPage();

    await waitFor(() => expect(screen.getByText("ACT-001")).toBeTruthy());
    expect(screen.getByRole("cell", { name: "Borrador" })).toBeTruthy();
  });

  it("sin capacidad manage no muestra Nueva acta", async () => {
    apiFetchMock.mockImplementation((path: string) => {
      if (path.includes("/opciones")) return Promise.resolve(opciones);
      if (path.includes("/actas")) return Promise.resolve({ items: [], total: 0, pagina: 1, por_pagina: 20 });
      return Promise.reject(new Error("Ruta inesperada"));
    });

    renderPage();

    await waitFor(() => expect(screen.queryByText("Nueva acta")).toBeNull());
  });

  it("con manage muestra Nueva acta", async () => {
    capacidades.add("gobierno_actas:manage");
    apiFetchMock.mockImplementation((path: string) => {
      if (path.includes("/opciones")) return Promise.resolve(opciones);
      if (path.includes("/actas")) return Promise.resolve({ items: [], total: 0, pagina: 1, por_pagina: 20 });
      return Promise.reject(new Error("Ruta inesperada"));
    });

    renderPage();

    await waitFor(() => expect(screen.getByText("Nueva acta")).toBeTruthy());
  });

  it("muestra estado vacio sin items", async () => {
    apiFetchMock.mockImplementation((path: string) => {
      if (path.includes("/opciones")) return Promise.resolve(opciones);
      if (path.includes("/actas")) return Promise.resolve({ items: [], total: 0, pagina: 1, por_pagina: 20 });
      return Promise.reject(new Error("Ruta inesperada"));
    });

    renderPage();

    await waitFor(() => expect(screen.getByText("Sin actas")).toBeTruthy());
  });
});
