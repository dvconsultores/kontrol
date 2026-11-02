import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";
import {
  nombreDeActo,
  type ActoDeNotificacion,
  type ListaNotificaciones,
  type NotificacionResumen,
} from "@/modules/gobierno/api";

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

vi.mock("@/modules/documentos/AdjuntosPanel", () => ({
  AdjuntosPanel: (p: { resourceType: string; resourceId: string }) => (
    <div data-testid="adjuntos">{`${p.resourceType}:${p.resourceId}`}</div>
  ),
}));

vi.mock("@/lib/fecha-de-negocio", async (original) => ({
  ...(await original<typeof import("@/lib/fecha-de-negocio")>()),
  hoyDeNegocio: () => "2026-10-30",
}));

const { NotificacionesPage } = await import("./NotificacionesPage");

const ACTO: ActoDeNotificacion = {
  id: "a1",
  tipo: "RESOLUCION",
  denominacion_tipo: null,
  numero: "DA-001-2026",
  fecha: "2026-03-10",
  estado: "EMITIDO",
};

const N1_BASE: NotificacionResumen = {
  id: "n1",
  acto: ACTO,
  tipo_persona: "NATURAL",
  nombre: "Pedro Pérez",
  identificacion: "V-12345678",
  estado: "NOTIFICADA",
  intentos: 1,
  fecha_notificacion: "2026-03-12",
  medio_notificacion: "PERSONAL",
};

const N2_BASE: NotificacionResumen = {
  id: "n2",
  acto: ACTO,
  tipo_persona: "JURIDICA",
  nombre: "Comercial Ejemplo C.A.",
  identificacion: "J-12345678-9",
  estado: "PENDIENTE",
  intentos: 0,
  fecha_notificacion: null,
  medio_notificacion: null,
};

const N1_PRENSA: NotificacionResumen = {
  ...N1_BASE,
  medio_notificacion: "PRENSA",
};

const LISTA_2026: ListaNotificaciones = {
  anio: 2026,
  items: [N1_BASE, N2_BASE],
  total: 2,
};

const LISTA_2026_PRENSA: ListaNotificaciones = {
  anio: 2026,
  items: [N1_PRENSA, N2_BASE],
  total: 2,
};

const LISTA_2026_SIN_DATOS: ListaNotificaciones = {
  anio: 2026,
  items: [],
  total: 0,
};

const LISTA_2025: ListaNotificaciones = {
  anio: 2025,
  items: [],
  total: 0,
};

function configurarRespuestaLista(lista: ListaNotificaciones) {
  apiFetchMock.mockImplementation((url: string) => {
    if (url === "/gobierno/notificaciones?anio=2026") {
      return Promise.resolve(lista);
    }
    if (url === "/gobierno/notificaciones?anio=2025") {
      return Promise.resolve(LISTA_2025);
    }
    return Promise.reject(
      new ApiError(500, { code: "INTERNAL", message: "Error" }),
    );
  });
}

function renderPagina() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/gobierno/notificaciones"]}>
        <Routes>
          <Route
            path="/gobierno/notificaciones"
            element={<NotificacionesPage />}
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
  capacidades = new Set(["gobierno_notificaciones:view"]);
  configurarRespuestaLista(LISTA_2026);
});

describe("NotificacionesPage", () => {
  it("NTL-01 · sin gobierno_notificaciones:view muestra Sin acceso y no llama a apiFetch", async () => {
    capacidades = new Set();
    renderPagina();

    expect(await screen.findByText("Sin acceso")).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("NTL-02 · con view pide la lista 2026 y muestra enlaces, tipo de persona, identificación y estados", async () => {
    renderPagina();

    expect(await screen.findByText("Pedro Pérez")).toBeInTheDocument();

    expect(apiFetchMock).toHaveBeenCalledWith(
      "/gobierno/notificaciones?anio=2026",
    );

    const enlacesActo = screen.getAllByRole("link", { name: `Abrir el acto ${nombreDeActo(ACTO)}` });
    expect(enlacesActo).toHaveLength(2);
    const enlaceActo = enlacesActo[0];
    expect(enlaceActo).toHaveAttribute("href", "/gobierno/actos/a1");
    expect(
      within(enlaceActo).getByText("Resolución Nº DA-001-2026"),
    ).toBeInTheDocument();

    const enlacePersona = screen.getByRole("link", {
      name: "Abrir la notificación a Pedro Pérez",
    });
    expect(enlacePersona).toHaveAttribute("href", "/gobierno/notificaciones/n1");
    expect(within(enlacePersona).getByText("Pedro Pérez")).toBeInTheDocument();

    expect(screen.getByText("Persona natural")).toBeInTheDocument();
    expect(screen.getByText("V-12345678")).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: /^Notificada$/ })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: /^Pendiente$/ })).toBeInTheDocument();
    expect(screen.getByText("2 de 2 notificaciones")).toBeInTheDocument();
  });

  it("NTL-03 · fecha con medio PRENSA añade sufijo y fecha nula muestra guion", async () => {
    configurarRespuestaLista(LISTA_2026_PRENSA);
    renderPagina();

    expect(await screen.findByText("Pedro Pérez")).toBeInTheDocument();

    const filaPedro = screen
      .getByText("Pedro Pérez")
      .closest("tr") as HTMLTableRowElement;
    expect(
      within(filaPedro).getByText("12/03/2026 (prensa)"),
    ).toBeInTheDocument();

    const filaJuridica = screen
      .getByText("Comercial Ejemplo C.A.")
      .closest("tr") as HTMLTableRowElement;
    expect(within(filaJuridica).getByText("—")).toBeInTheDocument();
  });

  it("NTL-04 · filtro Estado Pendiente y búsqueda por identificación depuran la tabla", async () => {
    const usuario = userEvent.setup();
    renderPagina();

    expect(await screen.findByText("Pedro Pérez")).toBeInTheDocument();

    await usuario.selectOptions(screen.getByLabelText("Estado"), "PENDIENTE");

    expect(screen.queryByText("Pedro Pérez")).not.toBeInTheDocument();
    expect(screen.getByText("Comercial Ejemplo C.A.")).toBeInTheDocument();
    expect(screen.getByText("1 de 2 notificaciones")).toBeInTheDocument();

    await usuario.selectOptions(screen.getByLabelText("Estado"), "");
    await usuario.type(screen.getByLabelText("Buscar"), "12345678-9");

    expect(screen.queryByText("Pedro Pérez")).not.toBeInTheDocument();
    expect(screen.getByText("Comercial Ejemplo C.A.")).toBeInTheDocument();
    expect(screen.getByText("1 de 2 notificaciones")).toBeInTheDocument();

    await usuario.clear(screen.getByLabelText("Buscar"));
    await usuario.type(screen.getByLabelText("Buscar"), "zzz");

    expect(
      await screen.findByText("Ninguna notificación coincide con los filtros"),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("Comercial Ejemplo C.A."),
    ).not.toBeInTheDocument();
  });

  it("NTL-05 · año sin datos muestra estado vacío con enlace a actos y conserva el selector Año", async () => {
    configurarRespuestaLista(LISTA_2026_SIN_DATOS);
    renderPagina();

    expect(
      await screen.findByText("Sin notificaciones en 2026"),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("link", { name: "Ir a Actos administrativos" }),
    ).toHaveAttribute("href", "/gobierno/actos");
    expect(screen.getByLabelText("Año")).toBeInTheDocument();
  });

  it("NTL-06 · cambiar Año a 2025 consulta /gobierno/notificaciones?anio=2025", async () => {
    const usuario = userEvent.setup();
    renderPagina();

    expect(await screen.findByText("Pedro Pérez")).toBeInTheDocument();

    await usuario.selectOptions(screen.getByLabelText("Año"), "2025");
    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/notificaciones?anio=2025",
      );
    });
  });

  it("NTL-07 · Exportar CSV descarga archivo y notifica éxito; error de descarga notifica error", async () => {
    const usuario = userEvent.setup();
    renderPagina();

    expect(await screen.findByText("Pedro Pérez")).toBeInTheDocument();

    descargarArchivoMock.mockResolvedValue(undefined);
    await usuario.click(screen.getByRole("button", { name: "Exportar CSV" }));

    await waitFor(() => {
      expect(descargarArchivoMock).toHaveBeenCalledWith(
        "/gobierno/notificaciones/exportar?anio=2026",
        "notificaciones-2026.csv",
      );
    });
    expect(notify).toHaveBeenCalledWith({
      type: "success",
      title: "Notificaciones exportadas",
    });

    descargarArchivoMock.mockRejectedValue(new Error("error"));
    await usuario.click(screen.getByRole("button", { name: "Exportar CSV" }));

    await waitFor(() => {
      expect(notify).toHaveBeenCalledWith({
        type: "error",
        title: "No fue posible exportar",
      });
    });
  });

  it("NTL-08a · 404 GOV_ENTITY_NOT_FOUND muestra Primero configure el ente", async () => {
    apiFetchMock.mockRejectedValue(
      new ApiError(404, {
        code: "GOV_ENTITY_NOT_FOUND",
        message: "No existe",
      }),
    );
    renderPagina();

    expect(
      await screen.findByText("Primero configure el ente"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Ir a Configuración del ente" }),
    ).toHaveAttribute("href", "/gobierno/ente");
  });

  it("NTL-08b · 403 MODULE_NOT_ENTITLED muestra Módulo no disponible", async () => {
    apiFetchMock.mockRejectedValue(
      new ApiError(403, {
        code: "MODULE_NOT_ENTITLED",
        message: "Sin modulo",
      }),
    );
    renderPagina();

    expect(
      await screen.findByText("Módulo no disponible"),
    ).toBeInTheDocument();
  });

  it("NTL-08c · 500 muestra error genérico", async () => {
    apiFetchMock.mockRejectedValue(
      new ApiError(500, { code: "INTERNAL", message: "Error" }),
    );
    renderPagina();

    expect(
      await screen.findByText("No fue posible cargar las notificaciones."),
    ).toBeInTheDocument();
  });
});
