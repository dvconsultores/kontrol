import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type {
  AsignacionesListado,
  CatalogoOcupacion,
} from "@/modules/gobierno/api";

const apiFetchMock = vi.fn();
const notifyMock = vi.fn();
const descargarArchivoMock = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}));

vi.mock("@/api/descargas", () => ({
  descargarArchivo: (...args: unknown[]) => descargarArchivoMock(...args),
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

const { AsignacionesPage } = await import("./AsignacionesPage");

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AsignacionesPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const catalogo: CatalogoOcupacion = {
  figuras: [
    {
      codigo: "TITULAR",
      etiqueta: "Titular",
      grupo: "PERMANENTE",
      base_legal: "Ley",
      descripcion: "Titular del cargo",
    },
    {
      codigo: "SUPLENCIA",
      etiqueta: "Suplencia",
      grupo: "TEMPORAL",
      base_legal: "Ley",
      descripcion: "Suplencia",
    },
  ],
  instrumentos: [],
  situaciones: [],
};

const listadoConFilas: AsignacionesListado = {
  items: [
    {
      id: "a1",
      codigo: "ASG-001",
      figura: "TITULAR",
      figura_etiqueta: "Titular",
      funcionario: {
        id: "f1",
        codigo: "F-001",
        nombre: "Persona Uno",
        documento: "V-******90",
      },
      cargo: {
        id: "cargo-1",
        codigo: "C-001",
        nombre: "Director General",
        unidad_id: "u1",
        unidad: "Dirección General",
        ejercicio: 2024,
      },
      cargo_origen: null,
      acto: {
        id: "acto-1",
        tipo: "DECRETO",
        numero: "123",
        fecha: "2024-01-01",
        status: "ACTIVO",
        fecha_eficacia: "2024-01-01",
        medio: null,
        emisor_cargo_id: "cargo-emi",
        emisor_cargo: "Ministro",
        funcionario: "Persona Uno",
        asunto: "Nombramiento",
      },
      desde: "2024-01-01",
      hasta: null,
      fin_efectivo: null,
      status: "ACTIVO",
      situacion: "VIGENTE",
      version: 1,
    },
  ],
  total: 1,
  pagina: 1,
  por_pagina: 10,
  fecha: "2024-06-15",
};

const listadoVacio: AsignacionesListado = {
  items: [],
  total: 0,
  pagina: 1,
  por_pagina: 10,
  fecha: "2024-06-15",
};

describe("AsignacionesPage", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    notifyMock.mockReset();
    descargarArchivoMock.mockReset();
    capacidades = new Set<string>();

    apiFetchMock.mockImplementation((url: string) => {
      if (url.includes("/gobierno/ocupacion/catalogo")) {
        return Promise.resolve(catalogo);
      }
      if (url.includes("/gobierno/ocupacion/asignaciones")) {
        return Promise.resolve(listadoConFilas);
      }
      return Promise.reject(new Error("URL no esperada: " + url));
    });

    descargarArchivoMock.mockResolvedValue(undefined);
  });

  it("sin acceso", () => {
    renderPage();

    expect(screen.getByText("Sin acceso")).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("lista filas con código, funcionario, figura y situación Vigente", async () => {
    capacidades.add("gobierno_ocupacion:view");

    renderPage();

    expect(await screen.findByText("ASG-001")).toBeInTheDocument();
    expect(screen.getByText("Persona Uno")).toBeInTheDocument();

    const fila = screen.getByText("ASG-001").closest("tr");
    expect(fila).not.toBeNull();
    if (fila) {
      const dentro = within(fila);
      expect(dentro.getByText("Titular")).toBeInTheDocument();
      expect(dentro.getByText("VIGENTE")).toBeInTheDocument();
    }
  });

  it("filtrar por figura repite la consulta con figura=", async () => {
    capacidades.add("gobierno_ocupacion:view");

    renderPage();

    await screen.findByText("ASG-001");

    const selectFigura = screen.getByLabelText(/Figura/);
    await userEvent.selectOptions(selectFigura, "SUPLENCIA");

    await waitFor(() => {
      const llamadas = apiFetchMock.mock.calls;
      expect(
        llamadas.some((call) =>
          String(call[0]).includes("figura=SUPLENCIA"),
        ),
      ).toBe(true);
    });
  });

  it("Exportar CSV llama a descargarArchivo con la cadena de filtros (mock de '@/api/descargas')", async () => {
    capacidades.add("gobierno_ocupacion:view");

    renderPage();

    await screen.findByText("ASG-001");

    const botonExportar = screen.getByRole("button", { name: "Exportar CSV" });
    await userEvent.click(botonExportar);

    await waitFor(() => {
      expect(descargarArchivoMock).toHaveBeenCalledTimes(1);
    });

    const llamada = descargarArchivoMock.mock.calls[0];
    expect(llamada[0]).toContain("/gobierno/ocupacion/asignaciones.csv");
    expect(llamada[1]).toBe("asignaciones.csv");
  });

  it("fallo de exportación notifica error", async () => {
    capacidades.add("gobierno_ocupacion:view");

    descargarArchivoMock.mockRejectedValueOnce(new Error("Fallo"));

    renderPage();

    await screen.findByText("ASG-001");

    const botonExportar = screen.getByRole("button", { name: "Exportar CSV" });
    await userEvent.click(botonExportar);

    await waitFor(() => {
      expect(notifyMock).toHaveBeenCalledWith({
        type: "error",
        title: "No fue posible exportar",
      });
    });
  });

  it("vacío", async () => {
    capacidades.add("gobierno_ocupacion:view");

    apiFetchMock.mockImplementation((url: string) => {
      if (url.includes("/gobierno/ocupacion/catalogo")) {
        return Promise.resolve(catalogo);
      }
      if (url.includes("/gobierno/ocupacion/asignaciones")) {
        return Promise.resolve(listadoVacio);
      }
      return Promise.reject(new Error("URL no esperada: " + url));
    });

    renderPage();

    expect(await screen.findByText("Sin asignaciones")).toBeInTheDocument();
  });

  it("'Nueva asignación' solo con manage", async () => {
    capacidades.add("gobierno_ocupacion:view");

    const view = renderPage();

    await screen.findByText("ASG-001");
    expect(
      screen.queryByRole("link", { name: "Nueva asignación" }),
    ).not.toBeInTheDocument();

    capacidades.add("gobierno_ocupacion:manage");
    view.rerender(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <MemoryRouter>
          <AsignacionesPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(
      await screen.findByRole("link", { name: "Nueva asignación" }),
    ).toBeInTheDocument();
  });
});
