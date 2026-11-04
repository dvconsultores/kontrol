import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";

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

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify: vi.fn() }),
}));

const { HallazgosPage } = await import("./HallazgosPage");

const LISTADO_BASE = {
  total: 1,
  pagina: 1,
  por_pagina: 20,
  resumen: {
    abiertos: 3,
    acciones_vencidas: 2,
    pendientes_verificacion: 1,
    cerrados: 4,
  },
  items: [
    {
      id: "h1",
      codigo: "HLL-001",
      titulo: "Falta de controles en adquisiciones",
      riesgo: "ALTO" as const,
      estado: "ABIERTO" as const,
      origen: "AUDITORIA" as const,
      acciones_total: 5,
      acciones_vencidas: 2,
      created_at: "2026-02-01T10:00:00Z",
    },
  ],
};

function renderHallazgos() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/gobierno/hallazgos"]}>
        <HallazgosPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  apiFetchMock.mockReset();
  apiFetchMock.mockImplementation((url: string) => {
    if (url.startsWith("/gobierno/hallazgos")) {
      return Promise.resolve(LISTADO_BASE);
    }
    return Promise.reject(
      new ApiError(500, { code: "INTERNAL", message: "Error" }),
    );
  });
  capacidades = new Set(["gobierno_hallazgos:view", "gobierno_hallazgos:manage"]);
});

describe("HallazgosPage", () => {
  it("HLL-01 · con datos: pinta el resumen (4 indicadores con sus números), la tabla con código como enlace a /gobierno/hallazgos/{id} y el aviso «vencidas» cuando acciones_vencidas > 0", async () => {
    renderHallazgos();

    expect(await screen.findByText("Abiertos")).toBeInTheDocument();
    expect(screen.getByText("Acciones vencidas")).toBeInTheDocument();
    expect(screen.getByText("Pendientes de verificación")).toBeInTheDocument();
    expect(screen.getByText("Cerrados")).toBeInTheDocument();

    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByText("1")).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument();

    const enlace = screen.getByRole("link", { name: "Abrir el hallazgo HLL-001" });
    expect(enlace).toHaveAttribute("href", "/gobierno/hallazgos/h1");

    expect(screen.getByText("2 vencidas")).toBeInTheDocument();
  });

  it("HLL-02 · sin gobierno_hallazgos:manage no aparece «Registrar hallazgo»; con manage sí", async () => {
    capacidades = new Set(["gobierno_hallazgos:view"]);
    renderHallazgos();

    await screen.findByText("Abiertos");
    expect(
      screen.queryByRole("link", { name: "Registrar hallazgo" }),
    ).not.toBeInTheDocument();

    capacidades = new Set(["gobierno_hallazgos:view", "gobierno_hallazgos:manage"]);
    renderHallazgos();

    expect(
      await screen.findByRole("link", { name: "Registrar hallazgo" }),
    ).toBeInTheDocument();
  });

  it("HLL-03 · pulsar «Acciones vencidas» pide la consulta con vencidas=true (comprobar la URL llamada a apiFetch)", async () => {
    const usuario = userEvent.setup();
    renderHallazgos();

    const boton = await screen.findByRole("button", { name: /Acciones vencidas/ });
    await usuario.click(boton);

    await waitFor(() => {
      const urls = apiFetchMock.mock.calls.map((call) => call[0] as string);
      expect(urls.some((url) => url.includes("vencidas=true"))).toBe(true);
    });
  });

  it("HLL-04 · 403 MODULE_NOT_ENTITLED muestra «Módulo no habilitado»; lista vacía sin filtros muestra «Aún no hay hallazgos registrados»", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url.startsWith("/gobierno/hallazgos")) {
        return Promise.reject(
          new ApiError(403, {
            code: "MODULE_NOT_ENTITLED",
            message: "No habilitado",
          }),
        );
      }
      return Promise.reject(
        new ApiError(500, { code: "INTERNAL", message: "Error" }),
      );
    });

    renderHallazgos();

    expect(
      await screen.findByText("Módulo no habilitado"),
    ).toBeInTheDocument();

    apiFetchMock.mockImplementation((url: string) => {
      if (url.startsWith("/gobierno/hallazgos")) {
        return Promise.resolve({
          total: 0,
          pagina: 1,
          por_pagina: 20,
          resumen: {
            abiertos: 0,
            acciones_vencidas: 0,
            pendientes_verificacion: 0,
            cerrados: 0,
          },
          items: [],
        });
      }
      return Promise.reject(
        new ApiError(500, { code: "INTERNAL", message: "Error" }),
      );
    });

    renderHallazgos();

    expect(
      await screen.findByText("Aún no hay hallazgos registrados"),
    ).toBeInTheDocument();
  });
});
