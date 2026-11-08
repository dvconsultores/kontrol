import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi, beforeEach } from "vitest";

const apiFetchMock = vi.fn();
vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}));
vi.mock("@/api/descargas", () => ({ descargarArchivo: vi.fn() }));
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
vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify: vi.fn() }),
}));

import { ComisionesPage } from "./ComisionesPage";

function renderPage() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <ComisionesPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const itemBase = {
  id: "com-1",
  codigo: "COM-2024-01",
  nombre: "Comisión de Licitaciones",
  tipo: "PERMANENTE",
  status: "BORRADOR",
  situacion: "EN_VIGOR",
  desde: "2024-01-01",
  hasta: null,
  acto: {
    id: "acto-1",
    etiqueta: "Resolución 001",
    medio: null,
    fecha_eficacia: "2024-01-01",
    emisor: null,
  },
  miembros_principales: 3,
  miembros_total: 8,
  version: 1,
};

beforeEach(() => {
  vi.clearAllMocks();
  capacidades = new Set(["gobierno_comisiones:view", "gobierno_comisiones:manage"]);
});

describe("ComisionesPage", () => {
  it("(a) muestra la fila con código enlazado a la ficha, período, acto y «3 principales · 8 en total»", async () => {
    apiFetchMock.mockResolvedValue({
      items: [itemBase],
      total: 1,
      pagina: 1,
      por_pagina: 10,
    });

    renderPage();

    await waitFor(() =>
      expect(
        screen.getByRole("link", { name: "COM-2024-01" }),
      ).toBeInTheDocument(),
    );

    expect(
      screen.getByRole("link", { name: "COM-2024-01" }),
    ).toHaveAttribute("href", "/gobierno/contrataciones/comisiones/com-1");

    expect(screen.getByText("Comisión de Licitaciones")).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "Permanente" })).toBeInTheDocument();
    expect(screen.getAllByRole("cell", { name: "En preparación" }).length).toBeGreaterThan(0);
    expect(screen.getByRole("cell", { name: "En vigor" })).toBeInTheDocument();
    expect(screen.getByText(/Sin fecha final/)).toBeInTheDocument();
    expect(screen.getByText("Resolución 001")).toBeInTheDocument();
    expect(
      screen.getByText("3 principales · 8 en total"),
    ).toBeInTheDocument();
  });

  it("(b) al cambiar Vigencia, la última URL incluye situacion=EN_VIGOR", async () => {
    apiFetchMock.mockResolvedValue({
      items: [],
      total: 0,
      pagina: 1,
      por_pagina: 10,
    });

    renderPage();

    await waitFor(() => expect(apiFetchMock).toHaveBeenCalled());

    const select = screen.getByLabelText("Vigencia");
    await userEvent.selectOptions(select, "EN_VIGOR");

    await waitFor(() => {
      const ids = screen.getAllByLabelText?.("Vigencia") ?? [];
      expect(ids.length).toBeGreaterThan(0);
    });

    const lastCall = apiFetchMock.mock.calls.at(-1)?.[0] as string;
    expect(lastCall).toContain("situacion=EN_VIGOR");
  });

  it("(c) sin gobierno_comisiones:manage no aparece «Nueva comisión»", async () => {
    capacidades = new Set(["gobierno_comisiones:view"]);
    apiFetchMock.mockResolvedValue({
      items: [itemBase],
      total: 1,
      pagina: 1,
      por_pagina: 10,
    });

    renderPage();

    await waitFor(() =>
      expect(
        screen.getByRole("link", { name: "COM-2024-01" }),
      ).toBeInTheDocument(),
    );

    expect(
      screen.queryByRole("link", { name: "Nueva comisión" }),
    ).not.toBeInTheDocument();
  });

  it("(d) sin :view muestra «Sin acceso» y no llama a la API", async () => {
    capacidades = new Set();

    renderPage();

    expect(screen.getByText("Sin acceso")).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });
});
