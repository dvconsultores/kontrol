import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/api/client";
import { CausadosPage } from "./CausadosPage";
import type { CausadoResumen, CausadosListado } from "./api";

const apiFetchMock = vi.fn();
const descargarArchivoMock = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
  ApiError: (await original<typeof import("@/api/client")>()).ApiError,
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
  useCompany: () => ({ activeCompanyId: "c1", activeCompany: { id: "c1", legal_name: "Ente 1" } }),
}));

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify: vi.fn() }),
}));

interface Ejercicio {
  id: string;
  anio: string;
  moneda_funcional: string;
  estado: "BORRADOR" | "APROBADO" | "RECONDUCIDO" | "CERRADO";
  version: number;
}

interface EjerciciosRespuesta {
  items: Ejercicio[];
  total: number;
}

function crearEjercicio(partial: Partial<Ejercicio> = {}): Ejercicio {
  return {
    id: "y1",
    anio: "2026",
    moneda_funcional: "VES",
    estado: "APROBADO",
    version: 1,
    ...partial,
  };
}

function crearCausado(partial: Partial<CausadoResumen> = {}): CausadoResumen {
  return {
    id: "c1",
    codigo: "CAU-2026-001",
    estado: "FORMALIZADO",
    fecha_efectiva: "2026-02-10",
    compromiso_id: "k1",
    compromiso_codigo: "COM-2026-001",
    beneficiario: "Proveedor Uno",
    concepto: "Servicio de mantenimiento",
    monto: "40.00",
    moneda: "VES",
    pendiente_compromiso: "60.00",
    unidad: "Operaciones",
    responsable: "Analista Uno",
    ...partial,
  };
}

function renderPagina() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/gobierno/presupuesto/causados"]}>
        <Routes>
          <Route path="/gobierno/presupuesto/causados" element={<CausadosPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return queryClient;
}

async function responderBase() {
  apiFetchMock.mockImplementation((ruta: string) => {
    if (ruta === "/gobierno/presupuesto/ejercicios") {
      return Promise.resolve<EjerciciosRespuesta>({
        items: [crearEjercicio()],
        total: 1,
      });
    }
    if (ruta.startsWith("/gobierno/presupuesto/ejercicios/y1/causados")) {
      return Promise.resolve<CausadosListado>({
        items: [crearCausado()],
        total: 1,
      });
    }
    return Promise.reject(new Error(`Ruta no esperada: ${ruta}`));
  });
}

beforeEach(() => {
  apiFetchMock.mockReset();
  descargarArchivoMock.mockReset();
  capacidades = new Set(["gobierno_presupuesto:view", "gobierno_presupuesto:cause"]);
});

describe("CausadosPage", () => {
  it("muestra loading mientras se cargan los ejercicios", async () => {
    apiFetchMock.mockImplementation(() => new Promise(() => {}));
    renderPagina();
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("muestra vacío sin ejercicios aprobados", async () => {
    apiFetchMock.mockImplementation((ruta: string) => {
      if (ruta === "/gobierno/presupuesto/ejercicios") {
        return Promise.resolve<EjerciciosRespuesta>({
          items: [crearEjercicio({ estado: "BORRADOR" })],
          total: 1,
        });
      }
      return Promise.reject(new Error(`Ruta no esperada: ${ruta}`));
    });
    renderPagina();
    expect(await screen.findByText("No hay ejercicios aprobados")).toBeInTheDocument();
  });

  it("muestra vacío con ejercicio aprobado sin causados", async () => {
    apiFetchMock.mockImplementation((ruta: string) => {
      if (ruta === "/gobierno/presupuesto/ejercicios") {
        return Promise.resolve<EjerciciosRespuesta>({
          items: [crearEjercicio()],
          total: 1,
        });
      }
      if (ruta.startsWith("/gobierno/presupuesto/ejercicios/y1/causados")) {
        return Promise.resolve<CausadosListado>({ items: [], total: 0 });
      }
      return Promise.reject(new Error(`Ruta no esperada: ${ruta}`));
    });
    renderPagina();
    expect(await screen.findByText("Aún no hay causados en este ejercicio")).toBeInTheDocument();
  });

  it("muestra error al fallar la lista", async () => {
    apiFetchMock.mockImplementation(async (ruta: string) => {
      if (ruta === "/gobierno/presupuesto/ejercicios") {
        return { items: [crearEjercicio()], total: 1 } satisfies EjerciciosRespuesta;
      }
      if (ruta.startsWith("/gobierno/presupuesto/ejercicios/y1/causados")) {
        throw new ApiError(500, { message: "Fallo del servidor" });
      }
      throw new Error(`Ruta no esperada: ${ruta}`);
    });
    renderPagina();
    expect(await screen.findByRole("heading", { name: "No se pudieron cargar los causados" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reintentar" })).toBeInTheDocument();
  });

  it("lista un borrador y un formalizado con sus detalles", async () => {
    apiFetchMock.mockImplementation((ruta: string) => {
      if (ruta === "/gobierno/presupuesto/ejercicios") {
        return Promise.resolve<EjerciciosRespuesta>({
          items: [crearEjercicio()],
          total: 1,
        });
      }
      if (ruta.startsWith("/gobierno/presupuesto/ejercicios/y1/causados")) {
        return Promise.resolve<CausadosListado>({
          items: [
            crearCausado({ id: "c-borrador", codigo: null, estado: "BORRADOR" }),
            crearCausado(),
          ],
          total: 2,
        });
      }
      return Promise.reject(new Error(`Ruta no esperada: ${ruta}`));
    });
    renderPagina();

    expect(await screen.findByText("CAU-2026-001")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Borrador" })).toBeInTheDocument();
    expect(screen.getAllByText("Formalizado").length).toBeGreaterThan(0);


    const enlaces = screen.getAllByRole("link");
    expect(enlaces.some((enlace) => enlace.getAttribute("href") === "/gobierno/presupuesto/causados/c-borrador")).toBe(true);
    expect(enlaces.some((enlace) => enlace.getAttribute("href") === "/gobierno/presupuesto/causados/c1")).toBe(true);
  });

  it("muestra sin acceso sin capacidad de view", async () => {
    capacidades = new Set(["gobierno_presupuesto:cause"]);
    renderPagina();
    expect(await screen.findByText("Sin acceso")).toBeInTheDocument();
  });

  it("muestra mensaje del error 403 de la lista", async () => {
    apiFetchMock.mockImplementation(async (ruta: string) => {
      if (ruta === "/gobierno/presupuesto/ejercicios") {
        return { items: [crearEjercicio()], total: 1 } satisfies EjerciciosRespuesta;
      }
      if (ruta.startsWith("/gobierno/presupuesto/ejercicios/y1/causados")) {
        throw new ApiError(403, { code: "FORBIDDEN", message: "No tiene permiso" });
      }
      throw new Error(`Ruta no esperada: ${ruta}`);
    });
    renderPagina();
    expect(await screen.findByText("No tiene permiso")).toBeInTheDocument();
  });

  it("muestra Nuevo causado solo con capacidad cause", async () => {
    capacidades = new Set(["gobierno_presupuesto:view"]);
    await responderBase();
    renderPagina();
    await screen.findByText("CAU-2026-001");
    expect(screen.queryByRole("link", { name: "Nuevo causado" })).not.toBeInTheDocument();
  });

  it("descarga CSV con filtros y nombre correcto", async () => {
    const usuario = userEvent.setup();
    await responderBase();
    renderPagina();
    await screen.findByText("CAU-2026-001");

    await usuario.selectOptions(screen.getByLabelText("Estado"), "FORMALIZADO");
    await usuario.click(screen.getByRole("button", { name: "Descargar CSV" }));

    await waitFor(() => {
      expect(descargarArchivoMock).toHaveBeenCalledWith(
        "/gobierno/presupuesto/ejercicios/y1/causados/reporte.csv?estado=FORMALIZADO",
        "causados-2026.csv",
      );
    });
  });

  it("la tabla está dentro de un contenedor responsive", async () => {
    await responderBase();
    renderPagina();
    await screen.findByText("CAU-2026-001");
    const tabla = screen.getByRole("table");
    expect(tabla.closest(".overflow-x-auto")).not.toBeNull();
  });
});
