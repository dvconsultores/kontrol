import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";
import type {
  AuditoriaEventos,
  AuditoriaFiltros,
  AuditoriaMuestras,
} from "@/modules/gobierno/api";

const apiFetchMock = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}));

vi.mock("@/api/descargas", () => ({
  descargarArchivo: (...args: unknown[]) => descargarArchivoMock(...args),
}));

const descargarArchivoMock = vi.fn();

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

vi.mock("./EvidenciaEvento", () => ({
  EvidenciaEvento: ({ eventoId }: { eventoId: string }) => (
    <div>Evidencia {eventoId}</div>
  ),
}));

vi.mock("./RegistrarMuestra", () => ({
  RegistrarMuestra: ({
    filtros,
    seleccion,
  }: {
    filtros: Record<string, unknown>;
    seleccion: string[];
  }) => (
    <div>
      Registro {JSON.stringify(filtros)} {seleccion.join(",")}
    </div>
  ),
}));

const FILTROS: AuditoriaFiltros = {
  procesos: [
    { codigo: "ORG", nombre: "Organización" },
    { codigo: "ORG-03", nombre: "Actualización de órganos" },
  ],
  acciones: [
    {
      codigo: "APROBAR",
      entidad: "Órgano",
      etiqueta: "Aprobar",
      proceso: "ORG",
    },
    {
      codigo: "RECHAZAR",
      entidad: "Órgano",
      etiqueta: "Rechazar",
      proceso: "ORG",
    },
    {
      codigo: "ACTUALIZAR_ORGANO",
      entidad: "Órgano",
      etiqueta: "Actualizar órgano",
      proceso: "ORG-03",
    },
  ],
};

const EVENTOS: AuditoriaEventos = {
  items: [
    {
      id: "e1",
      fecha: "2026-02-10T09:30:00Z",
      proceso: "ORG",
      proceso_nombre: "Organización",
      accion: "APROBAR",
      accion_etiqueta: "Aprobar",
      entidad: "Órgano",
      entidad_id: "ORG-01",
      usuario: "ua",
      motivo: "Solicitud aprobada",
      request_id: null,
    },
    {
      id: "e2",
      fecha: "2026-02-11T10:15:00Z",
      proceso: "ORG-03",
      proceso_nombre: "Actualización de órganos",
      accion: "ACTUALIZAR_ORGANO",
      accion_etiqueta: "Actualizar órgano",
      entidad: "Órgano",
      entidad_id: "ORG-03",
      usuario: "auditor1",
      motivo: "Datos corregidos",
      request_id: null,
    },
  ],
  total: 2,
  pagina: 1,
  por_pagina: 50,
};

const MUESTRAS: AuditoriaMuestras = {
  items: [
    {
      id: "m1",
      codigo: "MU-2026-0001",
      titulo: "Muestra enero 2026",
      criterio: "Muestreo de enero",
      justificacion: "Control rutinario",
      metodo: "ALEATORIA",
      semilla: 42,
      tamano: 3,
      poblacion: 14,
      filtros: {
        desde: "2026-01-01",
        hasta: "2026-01-31",
        proceso: "ORG",
      },
      registrada_por: "auditor1",
      registrada_en: "2026-02-15T11:00:00Z",
    },
  ],
};

const { AuditoriaInstitucionalPage } = await import(
  "./AuditoriaInstitucionalPage"
);

function configurarRespuestasBase() {
  apiFetchMock.mockImplementation((url: string) => {
    if (url === "/gobierno/auditoria/filtros") {
      return Promise.resolve(FILTROS);
    }
    if (url === "/gobierno/auditoria/eventos?pagina=1&por_pagina=50") {
      return Promise.resolve(EVENTOS);
    }
    if (url === "/gobierno/auditoria/muestras") {
      return Promise.resolve(MUESTRAS);
    }
    return Promise.reject(
      new ApiError(500, { code: "INTERNAL", message: "Error" }),
    );
  });
}

function renderPagina(entrada = "/gobierno/auditoria") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[entrada]}>
        <Routes>
          <Route
            path="/gobierno/auditoria"
            element={<AuditoriaInstitucionalPage />}
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
  configurarRespuestasBase();
});

describe("AuditoriaInstitucionalPage", () => {
  it("AUD-01 · sin gobierno_auditoria:view muestra Sin acceso y no llama a apiFetch", async () => {
    capacidades = new Set();
    renderPagina();

    expect(await screen.findByText("Sin acceso")).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("AUD-02 · muestra heading, nota, población con 2 filas y sin controles de muestreo sin :sample", async () => {
    renderPagina();

    expect(
      screen.getByRole("heading", { name: "Auditoría institucional" }),
    ).toBeInTheDocument();

    expect(
      screen.getByText(/Vista de solo lectura: la bitácora no se modifica/),
    ).toBeInTheDocument();

    expect(
      await screen.findByText("2 eventos en la población"),
    ).toBeInTheDocument();

    const region = screen.getByRole("region", {
      name: /Población de eventos/,
    });
    const filas = within(region).getAllByRole("row");
    // 1 de cabecera + 2 de datos
    expect(filas).toHaveLength(3);

    expect(
      screen.queryByRole("checkbox", {
        name: /Marcar el evento Aprobar/,
      }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Registrar muestra" }),
    ).not.toBeInTheDocument();
  });

  it("AUD-03 · elegir Proceso ORG-03 pide eventos filtrados y la lista de Acción solo trae las de ORG-03", async () => {
    const usuario = userEvent.setup();
    renderPagina();

    await screen.findByRole("region", { name: /Población de eventos/ });
    await screen.findByRole("option", { name: /ORG-03/ });

    await usuario.selectOptions(
      screen.getByLabelText("Proceso"),
      "ORG-03",
    );

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/auditoria/eventos?proceso=ORG-03&pagina=1&por_pagina=50",
      );
    });

    const selectAccion = screen.getByLabelText("Acción") as HTMLSelectElement;
    const opciones = Array.from(selectAccion.options).map(
      (opcion) => opcion.value,
    );
    expect(opciones).toEqual(["", "ACTUALIZAR_ORGANO"]);
  });

  it("AUD-04 · fechas inicial > final por URL muestra Rango de fechas inválido y no pide población", async () => {
    renderPagina(
      "/gobierno/auditoria?desde=2026-02-10&hasta=2026-02-01",
    );

    expect(
      await screen.findByText("Rango de fechas inválido"),
    ).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalledWith(
      expect.stringContaining(
        "/gobierno/auditoria/eventos?desde=2026-02-10&hasta=2026-02-01",
      ),
    );
  });

  it("AUD-05 · Buscar con texto con espacios pide eventos con texto sin espacios", async () => {
    const usuario = userEvent.setup();
    renderPagina();

    await screen.findByRole("region", { name: /Población de eventos/ });

    const inputBuscar = screen.getByRole("textbox", { name: "Buscar" });
    await usuario.type(inputBuscar, " cargo ");
    await usuario.click(screen.getByRole("button", { name: "Buscar" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/auditoria/eventos?texto=cargo&pagina=1&por_pagina=50",
      );
    });
  });

  it("AUD-06 · Ver evidencia del evento abre el mock Evidencia con el id del evento", async () => {
    const usuario = userEvent.setup();
    renderPagina();

    await screen.findByRole("region", { name: /Población de eventos/ });

    const verEvidencia = screen.getByRole("button", {
      name: /^Ver evidencia del evento Aprobar/,
    });
    await usuario.click(verEvidencia);

    expect(await screen.findByText("Evidencia e1")).toBeInTheDocument();
  });

  it("AUD-07 · con :sample, marcar 2 casillas muestra contador, Registrar muestra pinta mock con selección y Desmarcar todas restablece", async () => {
    capacidades = new Set([
      "gobierno_auditoria:view",
      "gobierno_auditoria:sample",
    ]);
    const usuario = userEvent.setup();
    renderPagina();

    await screen.findByRole("region", { name: /Población de eventos/ });

    const casilla1 = screen.getByRole("checkbox", {
      name: /^Marcar el evento Aprobar/,
    });
    const casilla2 = screen.getByRole("checkbox", {
      name: /^Marcar el evento Actualizar órgano/,
    });

    await usuario.click(casilla1);
    await usuario.click(casilla2);

    expect(
      await screen.findByText("2 partidas marcadas"),
    ).toBeInTheDocument();

    await usuario.click(screen.getByRole("button", { name: "Registrar muestra" }));

    expect(
      await screen.findByText(/Registro .*e1,e2/),
    ).toBeInTheDocument();

    await usuario.click(screen.getByRole("button", { name: "Desmarcar todas" }));

    await waitFor(() => {
      expect(
        screen.queryByText("2 partidas marcadas"),
      ).not.toBeInTheDocument();
    });
    expect(
      screen.queryByText("1 partida marcada"),
    ).not.toBeInTheDocument();
  });

  it("AUD-08 · población vacía muestra mensaje según haya filtros o no", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/auditoria/filtros") {
        return Promise.resolve(FILTROS);
      }
      if (
        url === "/gobierno/auditoria/eventos?pagina=1&por_pagina=50"
      ) {
        return Promise.resolve({
          items: [],
          total: 0,
          pagina: 1,
          por_pagina: 50,
        } satisfies AuditoriaEventos);
      }
      if (
        url === "/gobierno/auditoria/eventos?proceso=ORG&pagina=1&por_pagina=50"
      ) {
        return Promise.resolve({
          items: [],
          total: 0,
          pagina: 1,
          por_pagina: 50,
        } satisfies AuditoriaEventos);
      }
      if (url === "/gobierno/auditoria/muestras") {
        return Promise.resolve(MUESTRAS);
      }
      return Promise.reject(
        new ApiError(500, { code: "INTERNAL", message: "Error" }),
      );
    });

    const { unmount } = renderPagina();

    expect(
      await screen.findByText(
        "Sin actividad de Gobierno registrada en este ente",
      ),
    ).toBeInTheDocument();

    unmount();

    renderPagina("/gobierno/auditoria?proceso=ORG");

    expect(
      await screen.findByText(
        "Ninguna actividad de Gobierno coincide con los filtros",
      ),
    ).toBeInTheDocument();
  });

  it("AUD-09 · MODULE_NOT_ENTITLED en eventos muestra Módulo no disponible", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/auditoria/filtros") {
        return Promise.resolve(FILTROS);
      }
      if (url === "/gobierno/auditoria/eventos?pagina=1&por_pagina=50") {
        return Promise.reject(
          new ApiError(403, {
            code: "MODULE_NOT_ENTITLED",
            message: "Módulo no disponible",
          }),
        );
      }
      if (url === "/gobierno/auditoria/muestras") {
        return Promise.resolve(MUESTRAS);
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

  it("AUD-10 · Muestras guardadas lista MU-2026-0001 con enlace y 3 de 14; vacía muestra Aún no hay muestras registradas", async () => {
    const { unmount } = renderPagina();

    expect(
      await screen.findByRole("region", { name: "Tabla de muestras guardadas" }),
    ).toBeInTheDocument();

    const enlace = await screen.findByRole("link", { name: "MU-2026-0001" });
    expect(enlace).toHaveAttribute(
      "href",
      "/gobierno/auditoria/muestras/m1",
    );
    expect(screen.getByText("Selección aleatoria")).toBeInTheDocument();
    expect(screen.getByText("3 de 14")).toBeInTheDocument();

    unmount();

    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/auditoria/filtros") {
        return Promise.resolve(FILTROS);
      }
      if (url === "/gobierno/auditoria/eventos?pagina=1&por_pagina=50") {
        return Promise.resolve(EVENTOS);
      }
      if (url === "/gobierno/auditoria/muestras") {
        return Promise.resolve({ items: [] } satisfies AuditoriaMuestras);
      }
      return Promise.reject(
        new ApiError(500, { code: "INTERNAL", message: "Error" }),
      );
    });

    renderPagina();

    expect(
      await screen.findByText("Aún no hay muestras registradas"),
    ).toBeInTheDocument();
  });

  it("AUD-11 · con total 120, Siguiente pide eventos pagina=2&por_pagina=50", async () => {
    const eventosGrande: AuditoriaEventos = {
      items: [...EVENTOS.items],
      total: 120,
      pagina: 1,
      por_pagina: 50,
    };

    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/auditoria/filtros") {
        return Promise.resolve(FILTROS);
      }
      if (url === "/gobierno/auditoria/eventos?pagina=1&por_pagina=50") {
        return Promise.resolve(eventosGrande);
      }
      if (
        url === "/gobierno/auditoria/eventos?pagina=2&por_pagina=50"
      ) {
        return Promise.resolve({
          ...eventosGrande,
          pagina: 2,
        });
      }
      if (url === "/gobierno/auditoria/muestras") {
        return Promise.resolve(MUESTRAS);
      }
      return Promise.reject(
        new ApiError(500, { code: "INTERNAL", message: "Error" }),
      );
    });

    const usuario = userEvent.setup();
    renderPagina();

    await screen.findByRole("region", { name: /Población de eventos/ });
    const botonSiguiente = await screen.findByRole("button", { name: "Siguiente" });
    expect(botonSiguiente).toBeEnabled();

    await usuario.click(botonSiguiente);

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/auditoria/eventos?pagina=2&por_pagina=50",
      );
    });
  });
});
