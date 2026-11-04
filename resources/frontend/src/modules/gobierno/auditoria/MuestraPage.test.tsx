import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";
import type { AuditoriaMuestraDetalle } from "@/modules/gobierno/api";

const apiFetchMock = vi.fn();
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

const notify = vi.fn();

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify }),
}));

vi.mock("@/app/contexts/CompanyContext", () => ({
  useCompany: () => ({
    activeCompanyId: "c1",
    activeCompany: { id: "c1", legal_name: "Contenedor 1" },
  }),
}));

const { MuestraPage } = await import("./MuestraPage");

const MUESTRA_ALEATORIA: AuditoriaMuestraDetalle = {
  id: "m1",
  codigo: "MU-2026-0001",
  titulo: "Muestra inicial de Gobierno",
  metodo: "ALEATORIA",
  semilla: 42,
  poblacion: 14,
  tamano: 2,
  criterio: "Eventos de aprobación con importe mayor a 1000",
  justificacion: "Revisión trimestral obligatoria de la auditoría institucional",
  filtros: {
    desde: "2026-01-01",
    proceso: "ORG-03",
  },
  registrada_por: "auditor1",
  registrada_en: "2026-01-05T10:30:00Z",
  eventos: [
    {
      id: "ev-1",
      fecha: "2026-01-03T10:15:00Z",
      proceso: "ORG-03",
      proceso_nombre: "Organizaciones",
      accion: "GOV_POSITION_CREATED",
      accion_etiqueta: "Aprobación creada",
      entidad: "Aprobación",
      entidad_id: "AP-1",
      usuario: "ua",
      motivo: "Revisión de control interno",
      request_id: "req-1",
    },
    {
      id: "ev-2",
      fecha: "2026-01-04T09:00:00Z",
      proceso: "ORG-03",
      proceso_nombre: "Organizaciones",
      accion: "GOV_POSITION_UPDATED",
      accion_etiqueta: "Aprobación modificada",
      entidad: "Aprobación",
      entidad_id: "AP-2",
      usuario: "ua",
      motivo: null,
      request_id: null,
    },
  ],
};

const MUESTRA_TODAS: AuditoriaMuestraDetalle = {
  id: "m2",
  codigo: "MU-2026-0002",
  titulo: "Muestra completa de Gobierno",
  metodo: "TODAS",
  semilla: null,
  poblacion: 30,
  tamano: 30,
  criterio: "Toda la actividad registrada",
  justificacion: "Revisión integral del periodo",
  filtros: {},
  registrada_por: "auditor1",
  registrada_en: "2026-01-06T08:00:00Z",
  eventos: [],
};

function configurarRespuestaMuestra(muestra: AuditoriaMuestraDetalle) {
  apiFetchMock.mockImplementation((url: string) => {
    if (url === `/gobierno/auditoria/muestras/${muestra.id}`) {
      return Promise.resolve(muestra);
    }
    return Promise.reject(
      new ApiError(500, { code: "INTERNAL", message: "Error" }),
    );
  });
}

function renderPagina(entrada = "/gobierno/auditoria/muestras/m1") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[entrada]}>
        <Routes>
          <Route
            path="/gobierno/auditoria/muestras/:muestraId"
            element={<MuestraPage />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  apiFetchMock.mockReset();
  descargarArchivoMock.mockReset();
  notify.mockReset();
  capacidades = new Set(["gobierno_auditoria:view"]);
});

describe("MuestraPage", () => {
  it("MUE-01 · sin gobierno_auditoria:view → «Sin acceso» y apiFetch no se llama", async () => {
    capacidades = new Set();
    renderPagina();

    expect(await screen.findByText("Sin acceso")).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("MUE-02 · ALEATORIA con 2 eventos: muestra todos los datos de definición y tabla con 2 filas", async () => {
    configurarRespuestaMuestra(MUESTRA_ALEATORIA);
    renderPagina();

    expect(
      await screen.findByRole("heading", {
        name: "Muestra MU-2026-0001",
      }),
    ).toBeInTheDocument();

    expect(screen.getByText("Selección aleatoria")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText("14 eventos")).toBeInTheDocument();
    expect(screen.getByText("2 partidas")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Eventos de aprobación con importe mayor a 1000",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Revisión trimestral obligatoria de la auditoría institucional",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("Desde: 01/01/2026")).toBeInTheDocument();
    expect(screen.getByText("Proceso: ORG-03")).toBeInTheDocument();
    expect(
      screen.getByText(
        "La muestra es un papel de trabajo inmutable: no se edita ni se borra.",
      ),
    ).toBeInTheDocument();

    const region = screen.getByRole("region", {
      name: "Partidas de la muestra MU-2026-0001",
    });
    const filas = within(region).getAllByRole("row");
    expect(filas).toHaveLength(3);

    expect(
      screen.getByRole("link", {
        name: "Ver evidencia de la partida 1",
      }),
    ).toHaveAttribute("href", "/gobierno/auditoria?evento=ev-1");
  });

  it("MUE-03 · TODAS sin filtros: no se muestra la semilla y aparece el texto de sin filtros", async () => {
    configurarRespuestaMuestra(MUESTRA_TODAS);
    renderPagina("/gobierno/auditoria/muestras/m2");

    expect(
      await screen.findByRole("heading", {
        name: "Muestra MU-2026-0002",
      }),
    ).toBeInTheDocument();

    expect(
      screen.queryByText("Sin filtros: toda la actividad de Gobierno del ente"),
    ).toBeInTheDocument();
    expect(screen.queryByText("Semilla")).not.toBeInTheDocument();
  });

  it("MUE-04 · no hay botones ni enlaces de editar o borrar", async () => {
    configurarRespuestaMuestra(MUESTRA_ALEATORIA);
    renderPagina();

    await screen.findByRole("heading", {
      name: "Muestra MU-2026-0001",
    });

    expect(
      screen.queryByRole("button", { name: /editar|borrar|eliminar/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: /editar|borrar|eliminar/i }),
    ).not.toBeInTheDocument();
  });

  it("MUE-05 · «Exportar CSV» llama a descargarArchivo y notifica éxito; si rechaza, notifica error", async () => {
    configurarRespuestaMuestra(MUESTRA_ALEATORIA);
    descargarArchivoMock.mockResolvedValue(undefined);

    const usuario = userEvent.setup();
    renderPagina();

    await screen.findByRole("heading", {
      name: "Muestra MU-2026-0001",
    });

    await usuario.click(
      screen.getByRole("button", { name: /Exportar CSV/ }),
    );

    await waitFor(() => {
      expect(descargarArchivoMock).toHaveBeenCalledWith(
        "/gobierno/auditoria/muestras/m1/exportar",
        "muestra-MU-2026-0001.csv",
      );
    });
    expect(notify).toHaveBeenCalledWith({
      type: "success",
      title: "Muestra exportada",
    });

    descargarArchivoMock.mockRejectedValue(new Error("fallo descarga"));
    notify.mockReset();

    await usuario.click(
      screen.getByRole("button", { name: /Exportar CSV/ }),
    );

    await waitFor(() => {
      expect(descargarArchivoMock).toHaveBeenCalledTimes(2);
    });
    expect(notify).toHaveBeenCalledWith({
      type: "error",
      title: "No fue posible exportar",
    });
  });

  it("MUE-06 · 404 GOV_AUDIT_SAMPLE_NOT_FOUND → «Muestra no encontrada» con enlace a auditoría", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/auditoria/muestras/m1") {
        return Promise.reject(
          new ApiError(404, {
            code: "GOV_AUDIT_SAMPLE_NOT_FOUND",
            message: "No encontrada",
          }),
        );
      }
      return Promise.reject(
        new ApiError(500, { code: "INTERNAL", message: "Error" }),
      );
    });

    renderPagina();

    expect(
      await screen.findByText("Muestra no encontrada"),
    ).toBeInTheDocument();

    const enlace = screen.getByRole("link", {
      name: "Volver a Auditoría institucional",
    });
    expect(enlace).toHaveAttribute("href", "/gobierno/auditoria");
  });

  it("MUE-07 · MODULE_NOT_ENTITLED → «Módulo no disponible»", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/auditoria/muestras/m1") {
        return Promise.reject(
          new ApiError(403, {
            code: "MODULE_NOT_ENTITLED",
            message: "Sin módulo",
          }),
        );
      }
      return Promise.reject(
        new ApiError(500, { code: "INTERNAL", message: "Error" }),
      );
    });

    renderPagina();

    expect(
      await screen.findByText("Módulo no disponible"),
    ).toBeInTheDocument();
  });

  it("MUE-08 · error 500 → «No fue posible cargar la muestra.» y el botón de reintento vuelve a pedir la URL", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/auditoria/muestras/m1") {
        return Promise.reject(
          new ApiError(500, { code: "INTERNAL", message: "Error" }),
        );
      }
      return Promise.reject(
        new ApiError(500, { code: "INTERNAL", message: "Error" }),
      );
    });

    const usuario = userEvent.setup();
    renderPagina();

    expect(
      await screen.findByText("No fue posible cargar la muestra."),
    ).toBeInTheDocument();

    await usuario.click(screen.getByRole("button", { name: /Reintentar/i }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledTimes(2);
    });
    expect(apiFetchMock).toHaveBeenCalledWith(
      "/gobierno/auditoria/muestras/m1",
    );
  });
});
