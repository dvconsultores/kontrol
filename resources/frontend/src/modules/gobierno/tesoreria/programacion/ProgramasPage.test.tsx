import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";
import { ProgramasPage } from "./ProgramasPage";

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
  useCompany: () => ({
    activeCompanyId: "c1",
    activeCompany: { id: "c1", legal_name: "Contenedor 1" },
  }),
}));

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify: notifyMock }),
}));

const programa = {
  id: "p1",
  codigo: "PG-2026-0001",
  ejercicio: 2026,
  moneda: "USD" as const,
  estado: "BORRADOR" as const,
  version_vigente: 1,
  disponibilidad_inicial: "1200.00",
  version: 1,
};

const listado = {
  items: [programa],
  resumen: { borradores: 1, vigentes: 2, cerrados: 3 },
};

function renderPage(ruta = "/gobierno/tesoreria/programacion") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[ruta]}>
        <Routes>
          <Route
            path="/gobierno/tesoreria/programacion"
            element={<ProgramasPage />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ProgramasPage", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    notifyMock.mockReset();
    capacidades = new Set<string>();

    apiFetchMock.mockImplementation((url: string) => {
      if (url.startsWith("/gobierno/tesoreria/programas")) {
        return Promise.resolve(listado);
      }
      return Promise.reject(new Error(`URL no mockeada: ${url}`));
    });
  });

  it("PP-01 · sin gobierno_caja:view muestra «Sin acceso» y no llama a la API", async () => {
    renderPage();

    expect(await screen.findByText("Sin acceso")).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("PP-02 · con view: tabla con código enlazado, ejercicio, moneda, estado, versión vigente y disponibilidad inicial; sin «Nuevo programa»", async () => {
    capacidades.add("gobierno_caja:view");

    renderPage();

    expect(await screen.findByText("PG-2026-0001")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Abrir el programa PG-2026-0001" }),
    ).toHaveAttribute("href", "/gobierno/tesoreria/programacion/p1");
    expect(screen.getByRole("cell", { name: "2026" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "USD" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "Borrador" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "1" })).toBeInTheDocument();
    expect(
      screen.getByRole("cell", { name: "1.200,00 USD" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Nuevo programa")).not.toBeInTheDocument();
    expect(screen.getByText("Rubros de caja")).toBeInTheDocument();
  });

  it("PP-03 · con manage aparece «Nuevo programa»", async () => {
    capacidades.add("gobierno_caja:view");
    capacidades.add("gobierno_caja:manage");

    renderPage();

    expect(await screen.findByText("Nuevo programa")).toBeInTheDocument();
  });

  it("PP-04 · filtrar por ejercicio y moneda arma la consulta", async () => {
    capacidades.add("gobierno_caja:view");

    renderPage();

    const inputEjercicio = await screen.findByRole("spinbutton", {
      name: "Ejercicio",
    });
    await userEvent.type(inputEjercicio, "2026");

    const selectorMoneda = await screen.findByRole("combobox", {
      name: "Moneda",
    });
    await userEvent.selectOptions(selectorMoneda, "USD");

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/tesoreria/programas?ejercicio=2026&moneda=USD",
      );
    });
  });

  it("PP-05 · lista vacía sin filtros, con manage: «No hay programas» y enlaces «Nuevo programa»", async () => {
    capacidades.add("gobierno_caja:view");
    capacidades.add("gobierno_caja:manage");

    apiFetchMock.mockImplementation((url: string) => {
      if (url.startsWith("/gobierno/tesoreria/programas")) {
        return Promise.resolve({
          items: [],
          resumen: { borradores: 0, vigentes: 0, cerrados: 0 },
        });
      }
      return Promise.reject(new Error(`URL no mockeada: ${url}`));
    });

    renderPage();

    expect(await screen.findByText("No hay programas")).toBeInTheDocument();
    expect(
      screen.getAllByRole("link", { name: "Nuevo programa" }),
    ).toHaveLength(2);
  });

  it("PP-06 · lista vacía con filtro: «No hay programas con estos filtros.»", async () => {
    capacidades.add("gobierno_caja:view");

    apiFetchMock.mockImplementation((url: string) => {
      if (url.startsWith("/gobierno/tesoreria/programas")) {
        return Promise.resolve({
          items: [],
          resumen: { borradores: 0, vigentes: 0, cerrados: 0 },
        });
      }
      return Promise.reject(new Error(`URL no mockeada: ${url}`));
    });

    renderPage();

    const selectorMoneda = await screen.findByRole("combobox", {
      name: "Moneda",
    });
    await userEvent.selectOptions(selectorMoneda, "USD");

    expect(
      await screen.findByText("No hay programas con estos filtros."),
    ).toBeInTheDocument();
  });

  it("PP-07 · módulo no habilitado muestra «Módulo no habilitado»", async () => {
    capacidades.add("gobierno_caja:view");

    apiFetchMock.mockImplementation((url: string) => {
      if (url.startsWith("/gobierno/tesoreria/programas")) {
        return Promise.reject(
          new ApiError(403, {
            code: "MODULE_NOT_ENTITLED",
            message: "Módulo no habilitado",
            field_errors: {},
            details: {},
          }),
        );
      }
      return Promise.reject(new Error(`URL no mockeada: ${url}`));
    });

    renderPage();

    expect(await screen.findByText("Módulo no habilitado")).toBeInTheDocument();
  });
});
