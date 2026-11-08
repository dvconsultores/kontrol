import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type {
  VinculosListado,
  CatalogoIdentidad,
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

const { VinculosPage } = await import("./VinculosPage");

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <VinculosPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const catalogo: CatalogoIdentidad = {
  categorias: [],
  situaciones: ["BORRADOR", "DESCARTADA", "FUTURA", "VIGENTE", "VENCIDA", "CERRADA", "REVOCADA"],
  estados: ["BORRADOR", "ACTIVO", "CERRADO", "REVOCADO", "DESCARTADO"],
};

const listadoConFilas: VinculosListado = {
  items: [
    {
      id: "v1",
      codigo: "VIN-001",
      cuenta: {
        id: "c1",
        usuario: "analista.prueba",
        estado: "ACTIVO",
      },
      funcionario: {
        id: "f1",
        codigo: "F-001",
        nombre: "Funcionario de Prueba",
        documento: "V-******90",
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

const listadoVacio: VinculosListado = {
  items: [],
  total: 0,
  pagina: 1,
  por_pagina: 10,
  fecha: "2024-06-15",
};

describe("VinculosPage", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    notifyMock.mockReset();
    descargarArchivoMock.mockReset();
    capacidades = new Set<string>();

    apiFetchMock.mockImplementation((url: string) => {
      if (url.includes("/gobierno/identidad/catalogo")) {
        return Promise.resolve(catalogo);
      }
      if (url.includes("/gobierno/identidad/vinculos")) {
        return Promise.resolve(listadoConFilas);
      }
      return Promise.reject(new Error("URL no esperada: " + url));
    });

    descargarArchivoMock.mockResolvedValue(undefined);
  });

  it("sin capacidad gobierno_identidad:view muestra 'Sin acceso'", () => {
    renderPage();

    expect(screen.getByText("Sin acceso")).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("con view carga catálogo y listado; la tabla muestra código como enlace, cuenta, funcionario con documento enmascarado, estado y situación con sus etiquetas", async () => {
    capacidades.add("gobierno_identidad:view");

    renderPage();

    expect(await screen.findByText("VIN-001")).toBeInTheDocument();
    expect(screen.getByText("analista.prueba")).toBeInTheDocument();

    const enlaceCodigo = screen.getByRole("link", { name: "VIN-001" });
    expect(enlaceCodigo).toHaveAttribute("href", "/gobierno/identidad/vinculos/v1");

    const fila = screen.getByText("VIN-001").closest("tr");
    expect(fila).not.toBeNull();
    if (fila) {
      const dentro = within(fila);
      expect(dentro.getByText("analista.prueba")).toBeInTheDocument();
      expect(dentro.getByText("Funcionario de Prueba")).toBeInTheDocument();
      expect(dentro.getByText("V-******90")).toBeInTheDocument();
      expect(dentro.getByText("Activo")).toBeInTheDocument();
      expect(dentro.getByText("Vigente")).toBeInTheDocument();
    }
  });

  it("sin manage no aparece el enlace 'Nuevo vínculo'; con manage sí, con href /gobierno/identidad/vinculos/nuevo", async () => {
    capacidades.add("gobierno_identidad:view");

    renderPage();

    await screen.findByText("VIN-001");
    expect(
      screen.queryByRole("link", { name: "Nuevo vínculo" }),
    ).not.toBeInTheDocument();

    capacidades.add("gobierno_identidad:manage");
    const nuevaQueryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const { rerender } = renderPage();
    rerender(
      <QueryClientProvider client={nuevaQueryClient}>
        <MemoryRouter>
          <VinculosPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    const enlaceNuevo = await screen.findByRole("link", { name: "Nuevo vínculo" });
    expect(enlaceNuevo).toHaveAttribute("href", "/gobierno/identidad/vinculos/nuevo");
  });

  it("cambiar el filtro de estado vuelve a consultar con ?estado=ACTIVO y no envía company_id ni ente", async () => {
    capacidades.add("gobierno_identidad:view");

    renderPage();

    await screen.findByText("VIN-001");

    const selectEstado = screen.getByLabelText(/Estado/);
    await userEvent.selectOptions(selectEstado, "ACTIVO");

    await waitFor(() => {
      const llamadas = apiFetchMock.mock.calls;
      expect(
        llamadas.some((call) => {
          const url = String(call[0]);
          return url.includes("?estado=ACTIVO") &&
                 !url.includes("company_id") &&
                 !url.includes("ente");
        }),
      ).toBe(true);
    });
  });

  it("listado vacío muestra 'Sin vínculos'", async () => {
    capacidades.add("gobierno_identidad:view");

    apiFetchMock.mockImplementation((url: string) => {
      if (url.includes("/gobierno/identidad/catalogo")) {
        return Promise.resolve(catalogo);
      }
      if (url.includes("/gobierno/identidad/vinculos")) {
        return Promise.resolve(listadoVacio);
      }
      return Promise.reject(new Error("URL no esperada: " + url));
    });

    renderPage();

    expect(await screen.findByText("Sin vínculos")).toBeInTheDocument();
  });

  it("error del listado muestra el estado de error con 'Reintentar'", async () => {
    capacidades.add("gobierno_identidad:view");

    apiFetchMock.mockImplementation((url: string) => {
      if (url.includes("/gobierno/identidad/catalogo")) {
        return Promise.resolve(catalogo);
      }
      if (url.includes("/gobierno/identidad/vinculos")) {
        return Promise.reject(new Error("Fallo"));
      }
      return Promise.reject(new Error("URL no esperada: " + url));
    });

    renderPage();

    expect(await screen.findByText("No fue posible cargar los vínculos.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reintentar" })).toBeInTheDocument();
  });

  it("'Exportar CSV' llama a descargarArchivo con la ruta /gobierno/identidad/vinculos.csv y el nombre 'vinculos.csv'", async () => {
    capacidades.add("gobierno_identidad:view");

    renderPage();

    await screen.findByText("VIN-001");

    const botonExportar = screen.getByRole("button", { name: "Exportar CSV" });
    await userEvent.click(botonExportar);

    await waitFor(() => {
      expect(descargarArchivoMock).toHaveBeenCalledTimes(1);
    });

    const llamada = descargarArchivoMock.mock.calls[0];
    expect(llamada[0]).toContain("/gobierno/identidad/vinculos.csv");
    expect(llamada[1]).toBe("vinculos.csv");
  });
});
