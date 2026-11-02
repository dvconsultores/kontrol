import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";
import { formatearFecha } from "@/i18n";
import type { Notificacion as NotificacionTipo, VersionesNotificacion } from "@/modules/gobierno/api";
import type { IntentoEntrada } from "@/modules/gobierno/api";
import type { DatosDestinatario } from "./DestinatarioFormulario";

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

vi.mock("@/api/descargas", () => ({
  descargarAdjunto: vi.fn(),
}));

const { INTENTO, DESTINATARIO } = vi.hoisted(() => ({
  INTENTO: {
    medio: "PERSONAL",
    resultado: "ENTREGADA",
    fecha: "2026-10-29",
    documento_oficio_id: "d1",
    documento_id: "d2",
    receptor_nombre: "María Gil",
    receptor_identificacion: "V-7654321",
    motivo_fallo: null,
    diario: null,
    referencia: null,
  } as IntentoEntrada,
  DESTINATARIO: {
    tipo_persona: "NATURAL",
    nombre: "Pedro Pérez",
    identificacion: "V-12345678",
    domicilio: "Calle 9",
    apoderado_nombre: null,
    apoderado_identificacion: null,
    recursos: "Reconsideración en 15 días hábiles",
  } as DatosDestinatario,
}));

vi.mock("./RegistrarIntento", () => ({
  RegistrarIntento: (p: {
    onConfirmar: (datos: IntentoEntrada) => Promise<void>;
    erroresServidor: Record<string, string[]>;
    modo: string;
  }) => (
    <>
      <button
        type="button"
        onClick={() => void p.onConfirmar({ ...INTENTO })}
      >
        Confirmar intento falso
      </button>
      <output data-testid="modo">{p.modo}</output>
      <output data-testid="errores">
        {JSON.stringify(p.erroresServidor)}
      </output>
    </>
  ),
}));

vi.mock("./DestinatarioFormulario", () => ({
  DestinatarioFormulario: (p: {
    onConfirmar: (datos: DatosDestinatario) => Promise<void>;
    erroresServidor: Record<string, string[]>;
  }) => (
    <>
      <button
        type="button"
        onClick={() => void p.onConfirmar({ ...DESTINATARIO })}
      >
        Guardar destinatario falso
      </button>
      <output data-testid="errores-destinatario">
        {JSON.stringify(p.erroresServidor)}
      </output>
    </>
  ),
}));

vi.mock("./AnularNotificacion", () => ({
  AnularNotificacion: (p: {
    onConfirmar: (motivo: string) => Promise<void>;
    erroresServidor: Record<string, string[]>;
  }) => (
    <>
      <button
        type="button"
        onClick={() => void p.onConfirmar("Registrado por error")}
      >
        Confirmar anulación falsa
      </button>
      <output data-testid="errores-anular">
        {JSON.stringify(p.erroresServidor)}
      </output>
    </>
  ),
}));

const { NotificacionPage } = await import("./NotificacionPage");

const NOTIFICACION_BASE: NotificacionTipo = {
  id: "n1",
  acto: {
    id: "a1",
    tipo: "RESOLUCION",
    denominacion_tipo: null,
    numero: "DA-001-2026",
    fecha: "2026-03-10",
    estado: "EMITIDO",
  },
  tipo_persona: "NATURAL",
  nombre: "Pedro Pérez",
  identificacion: "V-12345678",
  domicilio: "Calle 1",
  apoderado_nombre: null,
  apoderado_identificacion: null,
  recursos: "Reconsideración en 15 días hábiles",
  documento_oficio_id: null,
  estado: "PENDIENTE",
  fecha_notificacion: null,
  medio_notificacion: null,
  motivo_anulacion: null,
  intentos: [],
  puede_publicar_en_prensa: false,
  version: 3,
  creado_en: "2026-03-10T12:00:00Z",
};

const VERSIONES_BASE: VersionesNotificacion = {
  items: [
    {
      version: 1,
      estado: "PENDIENTE",
      motivo: "Alta",
      actor: "ua",
      creado_en: "2026-03-10T12:00:00Z",
      instantanea: {},
    },
  ],
  total: 1,
};

type Escritura = (url: string, o: { method?: string; body?: unknown; ifMatch?: string }) => Promise<unknown>;

function crearCliente() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
}

function montar(
  notificacion: NotificacionTipo = NOTIFICACION_BASE,
  opciones?: {
    versiones?: VersionesNotificacion;
    lectura?: () => Promise<NotificacionTipo>;
    escritura?: Escritura;
  },
) {
  const { versiones = VERSIONES_BASE, lectura, escritura } = opciones ?? {};

  apiFetchMock.mockImplementation((url: string, o?: { method?: string; body?: unknown; ifMatch?: string }) => {
    if (url.startsWith("/gobierno/notificaciones/") && url.endsWith("/versiones")) {
      return Promise.resolve(versiones);
    }

    if (o?.method) {
      if (escritura) {
        return escritura(url, o);
      }

      if (o.method === "POST" && url.endsWith("/intentos")) {
        return Promise.resolve({
          ...notificacion,
          intentos: [
            ...notificacion.intentos,
            { numero: notificacion.intentos.length + 1, ...(o.body as object) },
          ],
        });
      }

      if (o.method === "POST" && url.endsWith("/anular")) {
        return Promise.resolve({
          ...notificacion,
          estado: "ANULADA",
          motivo_anulacion: (o.body as { motivo: string }).motivo,
          version: notificacion.version + 1,
        });
      }

      if (o.method === "PATCH") {
        return Promise.resolve({
          ...notificacion,
          ...(o.body as object),
          version: notificacion.version + 1,
        });
      }
    }

    if (url.endsWith("/gobierno/notificaciones/n1")) {
      return lectura ? lectura() : Promise.resolve(notificacion);
    }

    return Promise.reject(new Error(`URL inesperada: ${url}`));
  });

  const queryClient = crearCliente();

  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/gobierno/notificaciones/n1"]}>
        <Routes>
          <Route path="/gobierno/notificaciones/:notificacionId" element={<NotificacionPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );

  return { queryClient };
}

function permisos(...codigos: string[]) {
  capacidades = new Set(codigos);
}

describe("NotificacionPage", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    notify.mockReset();
    capacidades = new Set([
      "gobierno_notificaciones:view",
      "gobierno_notificaciones:edit",
      "gobierno_notificaciones:record",
    ]);
  });

  it("NTP-01 · sin view → «Sin acceso» y apiFetch no se llama", async () => {
    permisos("gobierno_actos:view");
    montar();

    await screen.findByText("Sin acceso");

    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("NTP-02 · PENDIENTE con view+edit+record muestra el estado, acciones esperadas y adjuntos", async () => {
    montar();

    await screen.findByText("Calle 1");

    expect(
      screen.getByRole("heading", { level: 1, name: "Notificación a Pedro Pérez" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Pendiente de notificar.")).toBeInTheDocument();

    expect(screen.getByRole("button", { name: "Registrar entrega" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Registrar intento fallido" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Corregir datos" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Anular" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Publicar en prensa" })).toBeNull();

    expect(screen.getByText("Sin intentos registrados.")).toBeInTheDocument();
    expect(screen.getByTestId("adjuntos")).toHaveTextContent("GovernmentNotification:n1");
  });

  it("NTP-03 · con intento FALLIDA y puede_publicar_en_prensa true muestra «Publicar en prensa», oculta «Corregir datos» y muestra la tabla", async () => {
    const notificacion: NotificacionTipo = {
      ...NOTIFICACION_BASE,
      puede_publicar_en_prensa: true,
      intentos: [
        {
          numero: 1,
          medio: "PERSONAL",
          resultado: "FALLIDA",
          fecha: "2026-03-11",
          documento_id: "d2",
          receptor_nombre: null,
          receptor_identificacion: null,
          motivo_fallo: "Domicilio cerrado",
          diario: null,
          referencia: null,
          registrado_por: "ua",
          creado_en: "2026-03-11T12:00:00Z",
        },
      ],
    };

    montar(notificacion);

    await screen.findByText("Domicilio cerrado");

    expect(screen.getByRole("button", { name: "Publicar en prensa" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Corregir datos" })).toBeNull();
    expect(
      screen.getByText(/Tras el intento fallido puede publicarse en prensa \(LOPA art\. 76\)\./),
    ).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "Intento fallido" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "Domicilio cerrado" })).toBeInTheDocument();
  });

  it("NTP-04 · solo view → ninguno de los cinco botones", async () => {
    permisos("gobierno_notificaciones:view");
    montar();

    await screen.findByText("Calle 1");

    expect(screen.queryByRole("button", { name: "Registrar entrega" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Registrar intento fallido" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Publicar en prensa" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Corregir datos" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Anular" })).toBeNull();
  });

  it("NTP-05a · NOTIFICADA por PRENSA muestra «Se entiende notificada el» y sin acciones", async () => {
    const notificadaPrensa: NotificacionTipo = {
      ...NOTIFICACION_BASE,
      estado: "NOTIFICADA",
      medio_notificacion: "PRENSA",
      fecha_notificacion: "2026-03-27",
    };
    montar(notificadaPrensa);

    await screen.findByText("Calle 1");

    expect(screen.getByText(/Se entiende notificada el/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Registrar entrega" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Anular" })).toBeNull();
  });

  it("NTP-05b · NOTIFICADA por PERSONAL muestra «Notificada el …» y sin acciones", async () => {
    const notificadaPersonal: NotificacionTipo = {
      ...NOTIFICACION_BASE,
      estado: "NOTIFICADA",
      medio_notificacion: "PERSONAL",
      fecha_notificacion: "2026-03-27",
    };
    montar(notificadaPersonal);

    await screen.findByText("Calle 1");

    expect(screen.getByText(/^Notificada el /)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Registrar entrega" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Anular" })).toBeNull();
  });

  it("NTP-05c · ANULADA muestra «Anulada. Motivo: Duplicado» y sin acciones", async () => {
    const anulada: NotificacionTipo = {
      ...NOTIFICACION_BASE,
      estado: "ANULADA",
      motivo_anulacion: "Duplicado",
    };
    montar(anulada);

    await screen.findByText("Calle 1");

    expect(screen.getByText("Anulada. Motivo: Duplicado")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Anular" })).toBeNull();
  });

  it("NTP-06 · PENDIENTE con acto EFICAZ muestra aviso y sin botones de intento", async () => {
    const notificacion: NotificacionTipo = {
      ...NOTIFICACION_BASE,
      acto: {
        ...NOTIFICACION_BASE.acto,
        estado: "EFICAZ",
      },
    };
    montar(notificacion);

    await screen.findByText("Calle 1");

    expect(
      screen.getByText(/El acto ya no admite notificaciones \(estado: Eficaz\)\./),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Registrar entrega" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Registrar intento fallido" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Publicar en prensa" })).toBeNull();
  });

  it("NTP-07 · Registrar entrega abre el panel y confirma con la llamada correcta", async () => {
    montar();

    await screen.findByText("Calle 1");

    await userEvent.click(screen.getByRole("button", { name: "Registrar entrega" }));

    expect(screen.getByTestId("modo")).toHaveTextContent("ENTREGADA");

    await userEvent.click(screen.getByRole("button", { name: "Confirmar intento falso" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/notificaciones/n1/intentos",
        { method: "POST", body: INTENTO, ifMatch: "3" },
      );
    });

    await waitFor(() => {
      expect(notify).toHaveBeenCalledWith({ type: "success", title: "Entrega registrada" });
    });
  });

  it("NTP-08 · escritura rechazada con GOV_NOTIFICATION_STALE muestra conflicto de concurrencia", async () => {
    montar(NOTIFICACION_BASE, {
      escritura: (_url, _o) =>
        Promise.reject(new ApiError(409, { code: "GOV_NOTIFICATION_STALE" })),
    });

    await screen.findByText("Calle 1");

    await userEvent.click(screen.getByRole("button", { name: "Registrar entrega" }));
    await userEvent.click(screen.getByRole("button", { name: "Confirmar intento falso" }));

    await screen.findByText("Conflicto de concurrencia");
    expect(
      screen.getByText(/Otra persona cambió la notificación mientras trabajaba/),
    ).toBeInTheDocument();
  });

  it("NTP-09a · errores de validación 422 se muestran en el panel", async () => {
    montar(NOTIFICACION_BASE, {
      escritura: (_url, _o) =>
        Promise.reject(
          new ApiError(422, {
            code: "VALIDATION_ERROR",
            field_errors: { fecha: ["No puede ser futura"] },
          }),
        ),
    });

    await screen.findByText("Calle 1");

    await userEvent.click(screen.getByRole("button", { name: "Registrar entrega" }));
    await userEvent.click(screen.getByRole("button", { name: "Confirmar intento falso" }));

    await waitFor(() => {
      expect(screen.getByTestId("errores")).toHaveTextContent("No puede ser futura");
    });
  });

  it("NTP-09b · GOV_NOTIFICATION_INVALID_STATE notifica el mensaje del servidor", async () => {
    montar(NOTIFICACION_BASE, {
      escritura: (_url, _o) =>
        Promise.reject(
          new ApiError(409, {
            code: "GOV_NOTIFICATION_INVALID_STATE",
            message: "Ya notificada",
          }),
        ),
    });

    await screen.findByText("Calle 1");

    await userEvent.click(screen.getByRole("button", { name: "Registrar entrega" }));
    await userEvent.click(screen.getByRole("button", { name: "Confirmar intento falso" }));

    await waitFor(() => {
      expect(notify).toHaveBeenCalledWith({
        type: "error",
        title: "No fue posible completar la operación",
        description: "Ya notificada",
      });
    });
  });

  it("NTP-10 · Anular + confirmar llama al endpoint de anulación correctamente", async () => {
    montar();

    await screen.findByText("Calle 1");

    await userEvent.click(screen.getByRole("button", { name: "Anular" }));
    await userEvent.click(screen.getByRole("button", { name: "Confirmar anulación falsa" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/notificaciones/n1/anular",
        { method: "POST", body: { motivo: "Registrado por error" }, ifMatch: "3" },
      );
    });

    await waitFor(() => {
      expect(notify).toHaveBeenCalledWith({ type: "success", title: "Notificación anulada" });
    });
  });

  it("NTP-11 · Corregir datos + confirmar llama al PATCH correctamente", async () => {
    montar();

    await screen.findByText("Calle 1");

    await userEvent.click(screen.getByRole("button", { name: "Corregir datos" }));
    await userEvent.click(screen.getByRole("button", { name: "Guardar destinatario falso" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/notificaciones/n1",
        { method: "PATCH", body: DESTINATARIO, ifMatch: "3" },
      );
    });

    await waitFor(() => {
      expect(notify).toHaveBeenCalledWith({ type: "success", title: "Datos corregidos" });
    });
  });

  it("NTP-12 · 404 GOV_NOTIFICATION_NOT_FOUND muestra notificación no encontrada con enlace", async () => {
    montar(NOTIFICACION_BASE, {
      lectura: () =>
        Promise.reject(new ApiError(404, { code: "GOV_NOTIFICATION_NOT_FOUND" })),
    });

    await screen.findByText("Notificación no encontrada");

    expect(
      screen.getByRole("link", { name: "Volver a Notificaciones administrativas" }),
    ).toHaveAttribute("href", "/gobierno/notificaciones");
  });

  it("NTP-13 · enlace del acto y el historial muestran la versión 1 con motivo «Alta»", async () => {
    montar();

    await screen.findByText("Calle 1");

    expect(
      screen.getByRole("link", { name: "Resolución Nº DA-001-2026" }),
    ).toHaveAttribute("href", "/gobierno/actos/a1");

    const historial = screen.getByRole("region", {
      name: "Historial de la notificación a Pedro Pérez",
    });
    expect(within(historial).getByText("1")).toBeInTheDocument();
    expect(within(historial).getByText("Alta")).toBeInTheDocument();
  });

  it("NTP-14 · la tabla de intentos muestra la columna «Registrado el» con el cuándo del intento", async () => {
    const notificacion: NotificacionTipo = {
      ...NOTIFICACION_BASE,
      puede_publicar_en_prensa: true,
      intentos: [
        {
          numero: 1,
          medio: "PERSONAL",
          resultado: "FALLIDA",
          fecha: "2026-03-11",
          documento_id: "d2",
          receptor_nombre: null,
          receptor_identificacion: null,
          motivo_fallo: "Domicilio cerrado",
          diario: null,
          referencia: null,
          registrado_por: "ua",
          creado_en: "2026-03-11T12:00:00Z",
        },
      ],
    };

    montar(notificacion);

    await screen.findByText("Domicilio cerrado");

    expect(screen.getByRole("columnheader", { name: "Registrado el" })).toBeInTheDocument();
    expect(
      screen.getByRole("cell", { name: formatearFecha("2026-03-11T12:00:00Z") }),
    ).toBeInTheDocument();
  });
});
