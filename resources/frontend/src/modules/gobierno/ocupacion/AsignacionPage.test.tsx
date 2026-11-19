import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
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

const { AsignacionPage } = await import("./AsignacionPage");

const asignacionActiva = {
  id: "asig-1",
  codigo: "ASIG-2025-001",
  figura: "TITULAR",
  figura_etiqueta: "Titular",
  funcionario: {
    id: "func-1",
    codigo: "F-001",
    nombre: "Persona Uno",
    documento: "V-12345690",
  },
  cargo: {
    id: "cargo-1",
    codigo: "C-001",
    nombre: "Director General",
    unidad_id: "unidad-1",
    unidad: "Dirección General",
    ejercicio: 2025,
  },
  cargo_origen: null,
  acto: {
    id: "acto-1",
    tipo: "Decreto",
    numero: "123-A",
    fecha: "2025-01-15",
    status: "FIRME",
    fecha_eficacia: null,
    medio: "Gaceta Oficial",
    emisor_cargo_id: "cargo-2",
    emisor_cargo: "Máxima Autoridad",
    funcionario: "Persona Emisor",
    asunto: "Nombramiento",
  },
  desde: "2025-01-20",
  hasta: null,
  fin_efectivo: null,
  status: "ACTIVO",
  situacion: "VIGENTE",
  version: 3,
  fundamento: "Artículo 100 de la Ley",
  rendicion: null,
  maxima_autoridad: false,
  autorizacion_especial: null,
  regla: {
    origen: "PISO_LEGAL",
    origen_etiqueta: "Regla legal base, sin política institucional",
    politica: null,
    regla_version: "Pisos legales",
    figura: "TITULAR",
    nivel_territorial: "ESTADAL",
    pisos: [],
    fundamentos: [],
    exige_fin: false,
    limites: [],
    acto_medio: null,
    emisor: { regla: "OTRO_CARGO", tipo: "CUALQUIERA", position_id: null, accion: null, materia: null },
    autorizaciones: [],
    competencias_permitidas: null,
    admite_avocacion: false,
    documentos: [],
  },
  regla_congelada: true,
  declara_delegable: false,
  acto_revocacion: null,
  motivo_fin: null,
  competencias: [],
  autoridad: [
    {
      accion: "APROBAR",
      materia: "PRESUPUESTO",
      tipo_limite: "SIN_LIMITE",
      monto: null,
      moneda: null,
    },
  ],
  ejerce: true,
  registrada_por: "admin@example.com",
  activada_por: "activador@example.com",
  activada_en: "2025-01-21T10:00:00Z",
  terminada_por: null,
  terminada_en: null,
  historia: [
    {
      id: "hist-1",
      tipo: "REGISTRO",
      detalle: null,
      actor: "admin@example.com",
      creado_en: "2025-01-20T09:00:00Z",
    },
    {
      id: "hist-2",
      tipo: "ACTIVACION",
      detalle: null,
      actor: "activador@example.com",
      creado_en: "2025-01-21T10:00:00Z",
    },
  ],
  avocaciones: [],
};

const asignacionBorrador = {
  ...asignacionActiva,
  id: "asig-borrador",
  codigo: "ASIG-2025-BORRADOR",
  status: "BORRADOR",
  situacion: "BORRADOR",
  version: 1,
  activada_por: null,
  activada_en: null,
  ejerce: false,
  desde: "2025-02-01",
  historia: [
    {
      id: "hist-b1",
      tipo: "REGISTRO",
      detalle: null,
      actor: "admin@example.com",
      creado_en: "2025-01-25T09:00:00Z",
    },
  ],
};

const asignacionDelegacion = {
  ...asignacionActiva,
  id: "asig-delegacion",
  codigo: "ASIG-2025-DELEG",
  figura: "DELEGACION_ATRIBUCIONES",
  figura_etiqueta: "Delegación de Atribuciones",
  regla: {
    ...asignacionActiva.regla,
    figura: "DELEGACION_ATRIBUCIONES",
    pisos: [{ codigo: "LOAP_DELEGACION", fuente: "LOAP (G.O. 6.147 Ext., 17-11-2014), arts. 2, 34, 35, 40 y 41", version: "LOAP-2014" }],
    fundamentos: ["LOAP (G.O. 6.147 Ext., 17-11-2014), arts. 2, 34, 35, 40 y 41"],
    acto_medio: { medio: "GACETA", mensaje: "La delegación debe estar publicada en gaceta (LOAP art. 40)" },
    emisor: { regla: "DELEGANTE", tipo: "CUALQUIERA", position_id: null, accion: null, materia: null },
    admite_avocacion: true,
  },
  competencias: [
    {
      accion: "APROBAR",
      materia: "CONTRATACIONES",
      tipo_limite: "MONTO",
      monto: "500000",
      moneda: "USD",
    },
  ],
};

const opciones = {
  funcionarios: [],
  cargos: [],
  actos: [
    {
      id: "acto-rev-1",
      numero: "456-B",
      tipo: "Resolución",
      fecha: "2025-02-10",
      fecha_eficacia: null,
      medio: null,
      emisor_cargo_id: "cargo-3",
      emisor_cargo: "Director de Recursos",
      asunto: "Revocación",
    },
    {
      id: "acto-avo-1",
      numero: "789-C",
      tipo: "Decreto",
      fecha: "2025-02-11",
      fecha_eficacia: null,
      medio: "Gaceta Oficial",
      emisor_cargo_id: "cargo-4",
      emisor_cargo: "Máxima Autoridad",
      asunto: "Avocación",
    },
  ],
};

function renderPage(asignacionId = "asig-1") {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/gobierno/ocupacion/asignaciones/${asignacionId}`]}>
        <Routes>
          <Route
            path="/gobierno/ocupacion/asignaciones/:asignacionId"
            element={<AsignacionPage />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("AsignacionPage", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    notifyMock.mockReset();
    capacidades = new Set<string>();
  });

  it("AP-01 · sin gobierno_ocupacion:view muestra Sin acceso", async () => {
    renderPage();

    expect(await screen.findByText("Sin acceso")).toBeInTheDocument();
    expect(
      screen.getByText("No tiene permiso para ver esta sección."),
    ).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("AP-02 · 404 muestra Asignación no encontrada", async () => {
    capacidades.add("gobierno_ocupacion:view");

    apiFetchMock.mockImplementation((ruta: string) => {
      if (ruta.includes("/gobierno/ocupacion/asignaciones/asig-1")) {
        return Promise.reject(
          new ApiError(404, { code: "GOV_ASSIGNMENT_NOT_FOUND", message: "No existe" }),
        );
      }
      return Promise.resolve(null);
    });

    renderPage();

    expect((await screen.findAllByText("Asignación no encontrada")).length).toBeGreaterThan(0);
    expect(screen.getByText("La asignación solicitada no existe.")).toBeInTheDocument();
  });

  it("AP-03 · detalle ACTIVO muestra funcionario, acto, fundamento, autoridad, historia", async () => {
    capacidades.add("gobierno_ocupacion:view");

    apiFetchMock.mockImplementation((ruta: string) => {
      if (ruta.includes("/gobierno/ocupacion/asignaciones/asig-1")) {
        return Promise.resolve(asignacionActiva);
      }
      return Promise.resolve(null);
    });

    renderPage();

    expect(await screen.findByText("Persona Uno")).toBeInTheDocument();
    expect(screen.getByText("V-12345690")).toBeInTheDocument();
    expect(screen.getByText("Director General")).toBeInTheDocument();
    expect(screen.getAllByText("Titular · Persona Uno").length).toBeGreaterThan(0);
    expect(screen.getByText("Decreto 123-A")).toBeInTheDocument();
    expect(screen.getByText("Artículo 100 de la Ley")).toBeInTheDocument();
    expect(screen.getByText("APROBAR")).toBeInTheDocument();
    expect(screen.getByText("PRESUPUESTO")).toBeInTheDocument();
    expect(screen.getByText("Quién y qué cargo")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Historia" })).toBeInTheDocument();
    expect(screen.getAllByText("admin@example.com").length).toBeGreaterThan(0);
    expect(screen.getByText("activador@example.com")).toBeInTheDocument();
  });

  it("AP-04 · BORRADOR con activate muestra Activar y al pulsar hace POST .../activar con ifMatch de la versión", async () => {
    capacidades.add("gobierno_ocupacion:view");
    capacidades.add("gobierno_ocupacion:manage");
    capacidades.add("gobierno_ocupacion:activate");

    apiFetchMock.mockImplementation((ruta: string, opcionesFetch: { method?: string; body?: unknown; ifMatch?: string }) => {
      if (ruta.includes("/gobierno/ocupacion/asignaciones/asig-borrador/activar")) {
        expect(opcionesFetch.method).toBe("POST");
        expect(opcionesFetch.ifMatch).toBe("1");
        return Promise.resolve({
          ...asignacionBorrador,
          status: "ACTIVO",
          situacion: "VIGENTE",
          version: 2,
        });
      }
      if (ruta.includes("/gobierno/ocupacion/asignaciones/asig-borrador")) {
        return Promise.resolve(asignacionBorrador);
      }
      return Promise.resolve(null);
    });

    const usuario = userEvent.setup();
    renderPage("asig-borrador");

    const botonActivar = await screen.findByRole("button", { name: "Activar" });
    expect(botonActivar).toBeInTheDocument();

    await usuario.click(botonActivar);

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/ocupacion/asignaciones/asig-borrador/activar",
        expect.objectContaining({
          method: "POST",
          body: {},
          ifMatch: "1",
        }),
      );
      expect(notifyMock).toHaveBeenCalledWith({
        type: "success",
        title: "Asignación activada",
      });
    });
  });

  it("AP-05 · sin activate no existe Activar", async () => {
    capacidades.add("gobierno_ocupacion:view");
    capacidades.add("gobierno_ocupacion:manage");

    apiFetchMock.mockImplementation((ruta: string) => {
      if (ruta.includes("/gobierno/ocupacion/asignaciones/asig-borrador")) {
        return Promise.resolve(asignacionBorrador);
      }
      return Promise.resolve(null);
    });

    renderPage("asig-borrador");

    await screen.findByText("Quién y qué cargo");
    expect(screen.queryByRole("button", { name: "Activar" })).not.toBeInTheDocument();
  });

  it("AP-06 · Descartar exige motivo de 10 caracteres y envía { motivo }", async () => {
    capacidades.add("gobierno_ocupacion:view");
    capacidades.add("gobierno_ocupacion:manage");

    apiFetchMock.mockImplementation((ruta: string, opcionesFetch: { method?: string; body?: Record<string, unknown>; ifMatch?: string }) => {
      if (ruta.includes("/gobierno/ocupacion/asignaciones/asig-borrador/descartar")) {
        expect(opcionesFetch.method).toBe("POST");
        expect(opcionesFetch.body).toEqual({ motivo: "Motivo suficientemente largo para descartar" });
        expect(opcionesFetch.ifMatch).toBe("1");
        return Promise.resolve({
          ...asignacionBorrador,
          status: "DESCARTADO",
          situacion: "DESCARTADA",
          version: 2,
        });
      }
      if (ruta.includes("/gobierno/ocupacion/asignaciones/asig-borrador")) {
        return Promise.resolve(asignacionBorrador);
      }
      return Promise.resolve(null);
    });

    const usuario = userEvent.setup();
    renderPage("asig-borrador");

    const botonDescartarPanel = await screen.findByRole("button", { name: "Descartar" });
    await usuario.click(botonDescartarPanel);

    const panelDescartar = await screen.findByText("Descartar asignación");
    const seccionDescartar = panelDescartar.closest("section") ?? panelDescartar;

    const inputMotivo = within(seccionDescartar as HTMLElement).getByLabelText("Motivo");
    const botonEnviar = within(seccionDescartar as HTMLElement).getByRole("button", { name: "Descartar" });

    expect(botonEnviar).toBeDisabled();

    await usuario.type(inputMotivo, "corto");
    expect(botonEnviar).toBeDisabled();

    await usuario.clear(inputMotivo);
    await usuario.type(inputMotivo, "Motivo suficientemente largo para descartar");
    expect(botonEnviar).toBeEnabled();

    await usuario.click(botonEnviar);

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/ocupacion/asignaciones/asig-borrador/descartar",
        expect.objectContaining({
          method: "POST",
          body: { motivo: "Motivo suficientemente largo para descartar" },
          ifMatch: "1",
        }),
      );
      expect(notifyMock).toHaveBeenCalledWith({
        type: "success",
        title: "Asignación descartada",
      });
    });
  });

  it("AP-07 · ACTIVO con revoke: panel Revocar envía acto_id, fecha y motivo", async () => {
    capacidades.add("gobierno_ocupacion:view");
    capacidades.add("gobierno_ocupacion:revoke");

    apiFetchMock.mockImplementation((ruta: string, opcionesFetch: { method?: string; body?: Record<string, unknown>; ifMatch?: string }) => {
      if (ruta.includes("/gobierno/ocupacion/asignaciones/asig-1/revocar")) {
        expect(opcionesFetch.method).toBe("POST");
        expect(opcionesFetch.body).toEqual({
          acto_id: "acto-rev-1",
          fecha: "2025-02-15",
          motivo: "Motivo de revocación válido y largo",
        });
        expect(opcionesFetch.ifMatch).toBe("3");
        return Promise.resolve({
          ...asignacionActiva,
          status: "REVOCADO",
          situacion: "REVOCADA",
          version: 4,
        });
      }
      if (ruta.includes("/gobierno/ocupacion/opciones")) {
        return Promise.resolve(opciones);
      }
      if (ruta.includes("/gobierno/ocupacion/asignaciones/asig-1")) {
        return Promise.resolve(asignacionActiva);
      }
      return Promise.resolve(null);
    });

    const usuario = userEvent.setup();
    renderPage();

    const botonRevocar = await screen.findByRole("button", { name: "Revocar" });
    await usuario.click(botonRevocar);

    const panelRevocar = await screen.findByText("Revocar asignación");
    const seccionRevocar = panelRevocar.closest("section") ?? panelRevocar;

    const selectActo = within(seccionRevocar as HTMLElement).getByLabelText("Acto de revocación");
    const inputFecha = within(seccionRevocar as HTMLElement).getByLabelText("Fecha");
    const inputMotivo = within(seccionRevocar as HTMLElement).getByLabelText("Motivo");

    await usuario.selectOptions(selectActo, "acto-rev-1");
    await usuario.type(inputFecha, "2025-02-15");
    await usuario.type(inputMotivo, "Motivo de revocación válido y largo");

    const botonEnviar = within(seccionRevocar as HTMLElement).getByRole("button", { name: "Revocar" });
    expect(botonEnviar).toBeEnabled();

    await usuario.click(botonEnviar);

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/ocupacion/asignaciones/asig-1/revocar",
        expect.objectContaining({
          method: "POST",
          body: {
            acto_id: "acto-rev-1",
            fecha: "2025-02-15",
            motivo: "Motivo de revocación válido y largo",
          },
          ifMatch: "3",
        }),
      );
      expect(notifyMock).toHaveBeenCalledWith({
        type: "success",
        title: "Asignación revocada",
      });
    });
  });

  it("AP-08 · sin revoke no hay Revocar ni Finalizar", async () => {
    capacidades.add("gobierno_ocupacion:view");

    apiFetchMock.mockImplementation((ruta: string) => {
      if (ruta.includes("/gobierno/ocupacion/asignaciones/asig-1")) {
        return Promise.resolve(asignacionActiva);
      }
      return Promise.resolve(null);
    });

    renderPage();

    await screen.findByText("Persona Uno");
    expect(screen.queryByRole("button", { name: "Revocar" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Finalizar" })).not.toBeInTheDocument();
  });

  it("AP-09 · Finalizar envía fecha y motivo", async () => {
    capacidades.add("gobierno_ocupacion:view");
    capacidades.add("gobierno_ocupacion:revoke");

    apiFetchMock.mockImplementation((ruta: string, opcionesFetch: { method?: string; body?: Record<string, unknown>; ifMatch?: string }) => {
      if (ruta.includes("/gobierno/ocupacion/asignaciones/asig-1/finalizar")) {
        expect(opcionesFetch.method).toBe("POST");
        expect(opcionesFetch.body).toEqual({
          fecha: "2025-03-01",
          motivo: "Finalización por cumplimiento de período",
        });
        expect(opcionesFetch.ifMatch).toBe("3");
        return Promise.resolve({
          ...asignacionActiva,
          status: "FINALIZADO",
          situacion: "FINALIZADA",
          version: 4,
        });
      }
      if (ruta.includes("/gobierno/ocupacion/asignaciones/asig-1")) {
        return Promise.resolve(asignacionActiva);
      }
      return Promise.resolve(null);
    });

    const usuario = userEvent.setup();
    renderPage();

    const botonFinalizar = await screen.findByRole("button", { name: "Finalizar" });
    await usuario.click(botonFinalizar);

    const panelFinalizar = await screen.findByText("Finalizar asignación");
    const seccionFinalizar = panelFinalizar.closest("section") ?? panelFinalizar;

    const inputFecha = within(seccionFinalizar as HTMLElement).getByLabelText("Fecha");
    const inputMotivo = within(seccionFinalizar as HTMLElement).getByLabelText("Motivo");

    await usuario.type(inputFecha, "2025-03-01");
    await usuario.type(inputMotivo, "Finalización por cumplimiento de período");

    const botonEnviar = within(seccionFinalizar as HTMLElement).getByRole("button", { name: "Finalizar" });
    expect(botonEnviar).toBeEnabled();

    await usuario.click(botonEnviar);

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/ocupacion/asignaciones/asig-1/finalizar",
        expect.objectContaining({
          method: "POST",
          body: {
            fecha: "2025-03-01",
            motivo: "Finalización por cumplimiento de período",
          },
          ifMatch: "3",
        }),
      );
      expect(notifyMock).toHaveBeenCalledWith({
        type: "success",
        title: "Asignación finalizada",
      });
    });
  });

  it("AP-10 · Avocar solo en delegaciones", async () => {
    capacidades.add("gobierno_ocupacion:view");
    capacidades.add("gobierno_ocupacion:revoke");

    apiFetchMock.mockImplementation((ruta: string) => {
      if (ruta.includes("/gobierno/ocupacion/opciones")) {
        return Promise.resolve(opciones);
      }
      if (ruta.includes("/gobierno/ocupacion/asignaciones/asig-delegacion")) {
        return Promise.resolve(asignacionDelegacion);
      }
      if (ruta.includes("/gobierno/ocupacion/asignaciones/asig-1")) {
        return Promise.resolve(asignacionActiva);
      }
      return Promise.resolve(null);
    });

    const { unmount } = renderPage("asig-delegacion");

    const botonAvocar = await screen.findByRole("button", { name: "Avocar" });
    expect(botonAvocar).toBeInTheDocument();

    unmount();

    renderPage();

    await screen.findByText("Persona Uno");
    expect(screen.queryByRole("button", { name: "Avocar" })).not.toBeInTheDocument();
  });

  it("AP-12 · muestra la regla aplicada congelada y la autorización con la etiqueta de la regla", async () => {
    capacidades.add("gobierno_ocupacion:view");
    const conPolitica = {
      ...asignacionActiva,
      autorizacion_especial: "Acta N.º 7 del Consejo Directivo",
      regla: {
        ...asignacionActiva.regla,
        origen: "POLITICA",
        origen_etiqueta: "Política institucional",
        politica: { id: "p1", codigo: "POL-SUP", numero_version: 2, nombre: "Suplencias del instituto" },
        regla_version: "POL-SUP v2",
        autorizaciones: [
          { etiqueta: "Autorización del Consejo Directivo", ambito: "TODAS", mas_de_dias: 10, fuente: "política POL-SUP v2" },
        ],
      },
    };
    apiFetchMock.mockImplementation((ruta: string) => {
      if (ruta.includes("/gobierno/ocupacion/opciones")) return Promise.resolve(opciones);
      if (ruta.includes("/gobierno/ocupacion/asignaciones/asig-1")) return Promise.resolve(conPolitica);
      return Promise.resolve(null);
    });
    renderPage();

    const seccion = await screen.findByRole("region", { name: "Regla aplicada" });
    expect(within(seccion).getByText(/Política POL-SUP v2 · Suplencias del instituto/)).toBeInTheDocument();
    expect(within(seccion).getByText("Congelada al activarse: no cambia aunque cambie la política.")).toBeInTheDocument();
    expect(screen.getByText("Autorización del Consejo Directivo")).toBeInTheDocument();
    expect(screen.getByText("Acta N.º 7 del Consejo Directivo")).toBeInTheDocument();
    expect(screen.queryByText(/Concejo/)).not.toBeInTheDocument();
  });

  it("AP-13 · la delegación cuya regla prohíbe avocar no ofrece «Avocar»", async () => {
    capacidades.add("gobierno_ocupacion:view");
    capacidades.add("gobierno_ocupacion:revoke");
    const sinAvocacion = { ...asignacionDelegacion, regla: { ...asignacionDelegacion.regla, admite_avocacion: false } };
    apiFetchMock.mockImplementation((ruta: string) => {
      if (ruta.includes("/gobierno/ocupacion/opciones")) return Promise.resolve(opciones);
      if (ruta.includes("/gobierno/ocupacion/asignaciones/asig-delegacion")) return Promise.resolve(sinAvocacion);
      return Promise.resolve(null);
    });
    renderPage("asig-delegacion");

    await screen.findByRole("region", { name: "Regla aplicada" });
    expect(screen.getByText("No admite avocación")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Avocar" })).not.toBeInTheDocument();
  });

  it("AP-11 · 409 GOV_ASSIGNMENT_STALE muestra el aviso de recargar", async () => {
    capacidades.add("gobierno_ocupacion:view");
    capacidades.add("gobierno_ocupacion:manage");
    capacidades.add("gobierno_ocupacion:activate");

    apiFetchMock.mockImplementation((ruta: string) => {
      if (ruta.includes("/gobierno/ocupacion/asignaciones/asig-borrador/activar")) {
        return Promise.reject(
          new ApiError(409, {
            code: "GOV_ASSIGNMENT_STALE",
            message: "Versión obsoleta",
          }),
        );
      }
      if (ruta.includes("/gobierno/ocupacion/asignaciones/asig-borrador")) {
        return Promise.resolve(asignacionBorrador);
      }
      return Promise.resolve(null);
    });

    const usuario = userEvent.setup();
    renderPage("asig-borrador");

    const botonActivar = await screen.findByRole("button", { name: "Activar" });
    await usuario.click(botonActivar);

    expect(
      await screen.findByText("Otra persona cambió esta asignación. Recargue la página."),
    ).toBeInTheDocument();
  });

  it("AP-12 · 403 GOV_ASSIGNMENT_SELF_ACTIVATION muestra su mensaje", async () => {
    capacidades.add("gobierno_ocupacion:view");
    capacidades.add("gobierno_ocupacion:manage");
    capacidades.add("gobierno_ocupacion:activate");

    apiFetchMock.mockImplementation((ruta: string) => {
      if (ruta.includes("/gobierno/ocupacion/asignaciones/asig-borrador/activar")) {
        return Promise.reject(
          new ApiError(403, {
            code: "GOV_ASSIGNMENT_SELF_ACTIVATION",
            message: "No puede autoactivar",
          }),
        );
      }
      if (ruta.includes("/gobierno/ocupacion/asignaciones/asig-borrador")) {
        return Promise.resolve(asignacionBorrador);
      }
      return Promise.resolve(null);
    });

    const usuario = userEvent.setup();
    renderPage("asig-borrador");

    const botonActivar = await screen.findByRole("button", { name: "Activar" });
    await usuario.click(botonActivar);

    expect(
      await screen.findByText("Quien registró la asignación no puede activarla."),
    ).toBeInTheDocument();
  });

  it("AP-13 · los paneles no son modales: no existe role=dialog", async () => {
    capacidades.add("gobierno_ocupacion:view");
    capacidades.add("gobierno_ocupacion:manage");

    apiFetchMock.mockImplementation((ruta: string) => {
      if (ruta.includes("/gobierno/ocupacion/asignaciones/asig-borrador")) {
        return Promise.resolve(asignacionBorrador);
      }
      return Promise.resolve(null);
    });

    const usuario = userEvent.setup();
    renderPage("asig-borrador");

    const botonDescartar = await screen.findByRole("button", { name: "Descartar" });
    await usuario.click(botonDescartar);

    await screen.findByText("Descartar asignación");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
