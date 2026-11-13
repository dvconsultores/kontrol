import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";

const apiFetchMock = vi.fn();
const notifyMock = vi.fn();

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
  useCompany: () => ({ activeCompanyId: "c1", activeCompany: { id: "c1", legal_name: "Contenedor 1" } }),
}));

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify: notifyMock }),
}));

const { EjerciciosPresupuestariosPage } = await import("./EjerciciosPresupuestariosPage");

const listaBase = {
  items: [
    {
      id: "e1",
      anio: 2027,
      moneda_funcional: "VES",
      estado: "BORRADOR",
      version: 1,
      congelado: false,
      reconduccion_definitiva: false,
      precompromiso_activo: true,
    },
    {
      id: "e2",
      anio: 2026,
      moneda_funcional: "VES",
      estado: "APROBADO",
      version: 2,
      congelado: true,
      reconduccion_definitiva: false,
      precompromiso_activo: false,
    },
  ],
  total: 2,
};

function renderizar(ruta = "/gobierno/presupuesto/ejercicios") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[ruta]}>
        <Routes>
          <Route path="/gobierno/presupuesto/ejercicios" element={<EjerciciosPresupuestariosPage />} />
          <Route path="/gobierno/presupuesto/ejercicios/:ejercicioId" element={<div>Detalle</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  apiFetchMock.mockReset();
  notifyMock.mockReset();
  capacidades = new Set<string>();
});

describe("EjerciciosPresupuestariosPage", () => {
  it("muestra los enlaces de cada ejercicio y su estado", async () => {
    capacidades = new Set(["gobierno_presupuesto:view"]);
    apiFetchMock.mockResolvedValue(listaBase);

    renderizar();

    expect(await screen.findByRole("link", { name: "Ejercicio 2027" })).toBeInTheDocument();
    expect(screen.getByText("Borrador")).toBeInTheDocument();
    expect(screen.getByText("Aprobado")).toBeInTheDocument();
  });

  it("sin capacidad manage no aparece «Crear ejercicio»", async () => {
    capacidades = new Set(["gobierno_presupuesto:view"]);
    apiFetchMock.mockResolvedValue(listaBase);

    renderizar();

    await screen.findByRole("link", { name: "Ejercicio 2027" });
    expect(screen.queryByRole("button", { name: "Crear ejercicio" })).not.toBeInTheDocument();
  });

  it("con manage, crear llama a apiFetch con POST y navega al detalle", async () => {
    capacidades = new Set(["gobierno_presupuesto:view", "gobierno_presupuesto:manage"]);
    apiFetchMock.mockImplementation(async (_ruta: string, opciones?: { method?: string; body?: unknown }) => {
      if (opciones?.method === "POST") {
        return { ...listaBase.items[0], id: "nuevo1" };
      }
      return listaBase;
    });

    const usuario = userEvent.setup();
    renderizar();

    const anioInput = await screen.findByLabelText("Año");
    await usuario.clear(anioInput);
    await usuario.type(anioInput, "2028");
    await usuario.click(screen.getByRole("button", { name: "Crear ejercicio" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/presupuesto/ejercicios",
        expect.objectContaining({
          method: "POST",
          body: { anio: 2028 },
        }),
      );
    });
    expect(await screen.findByText("Detalle")).toBeInTheDocument();
    expect(notifyMock).toHaveBeenCalledWith(
      expect.objectContaining({ type: "success", title: "Ejercicio 2028 creado" }),
    );
  });

  it("409 GOV_BUDGET_YEAR_EXISTS muestra «Ya existe el ejercicio de ese año»", async () => {
    capacidades = new Set(["gobierno_presupuesto:view", "gobierno_presupuesto:manage"]);
    apiFetchMock.mockImplementation(async (_ruta: string, opciones?: { method?: string }) => {
      if (opciones?.method === "POST") {
        throw new ApiError(409, {
          code: "GOV_BUDGET_YEAR_EXISTS",
          message: "Ya existe",
        });
      }
      return listaBase;
    });

    const usuario = userEvent.setup();
    renderizar();

    await screen.findByLabelText("Año");
    await usuario.click(screen.getByRole("button", { name: "Crear ejercicio" }));

    expect(await screen.findByText("Ya existe el ejercicio de ese año")).toBeInTheDocument();
  });

  it("lista vacía muestra el EmptyState", async () => {
    capacidades = new Set(["gobierno_presupuesto:view"]);
    apiFetchMock.mockResolvedValue({ items: [], total: 0 });

    renderizar();

    expect(
      await screen.findByText("Aún no hay ejercicios presupuestarios"),
    ).toBeInTheDocument();
  });
});
