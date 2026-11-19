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

import { PoliticasActaPage } from "./PoliticasActaPage";

function renderPage() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/politicas"]}>
        <Routes>
          <Route path="/politicas" element={<PoliticasActaPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const itemBase = {
  id: "p1",
  codigo: "PACT-2024-01",
  numero_version: 2,
  nombre: "Actas de entes territoriales",
  estado: "VIGENTE",
  estado_etiqueta: "Vigente",
  vigente_desde: "2024-01-01",
  vigente_hasta: null,
  total_vinculos: 3,
  total_requisitos: 4,
  version: 2,
};

const listado = {
  items: [itemBase],
  total: 1,
  pagina: 1,
  por_pagina: 20,
};

beforeEach(() => {
  vi.clearAllMocks();
  capacidades.clear();
  capacidades.add("gobierno_actas:view");
  capacidades.add("gobierno_actas:configure");
});

describe("PoliticasActaPage", () => {
  it("LPA-01 pinta filas y el enlace del código", async () => {
    apiFetchMock.mockResolvedValue(listado);

    renderPage();

    await waitFor(() =>
      expect(screen.getByRole("link", { name: "PACT-2024-01" })).toBeInTheDocument(),
    );

    expect(screen.getByRole("link", { name: "PACT-2024-01" })).toHaveAttribute(
      "href",
      "/gobierno/actas-entrega/politicas/p1",
    );

    const tabla = screen.getByRole("table", { name: "Políticas de actas" });
    expect(within(tabla).getByText("v2")).toBeInTheDocument();
    expect(within(tabla).getByText("Actas de entes territoriales")).toBeInTheDocument();
    expect(within(tabla).getByText("Vigente")).toBeInTheDocument();
    expect(within(tabla).getByText("3")).toBeInTheDocument();
    expect(within(tabla).getByText("4")).toBeInTheDocument();
  });

  it("LPA-02 sin configure no hay «Nueva política»", async () => {
    capacidades.delete("gobierno_actas:configure");
    apiFetchMock.mockResolvedValue(listado);

    renderPage();

    await waitFor(() =>
      expect(screen.getByRole("link", { name: "PACT-2024-01" })).toBeInTheDocument(),
    );

    expect(screen.queryByRole("link", { name: /Nueva política/i })).not.toBeInTheDocument();
  });

  it("LPA-03 al elegir Estado=Vigente se pide la lista con estado=VIGENTE", async () => {
    apiFetchMock.mockResolvedValue(listado);

    renderPage();

    await waitFor(() => expect(apiFetchMock).toHaveBeenCalled());

    const select = screen.getByLabelText("Estado");
    await userEvent.selectOptions(select, "VIGENTE");

    await waitFor(() => {
      const calls = apiFetchMock.mock.calls.map((c) => String(c[0]));
      expect(calls.some((u) => u.includes("estado=VIGENTE"))).toBe(true);
    });
  });
});
