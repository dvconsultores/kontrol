import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";
import {
  ETIQUETA_ESTADO_NOTIFICACION,
  ETIQUETA_TIPO_PERSONA,
  type Acto,
  type ListaNotificaciones,
  type NotificacionResumen,
  type NotificacionesDelActo as ResumenDelActo,
} from "@/modules/gobierno/api";
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

const { DESTINATARIO } = vi.hoisted(() => ({
  DESTINATARIO: {
    tipo_persona: "NATURAL",
    nombre: "Pedro Pérez",
    identificacion: "V-12345678",
    domicilio: "Calle 1, casa 2, Caracas",
    apoderado_nombre: null,
    apoderado_identificacion: null,
    recursos:
      "Reconsideración ante el mismo órgano en 15 días hábiles (LOPA art. 94)",
  } satisfies DatosDestinatario,
}));

vi.mock("./DestinatarioFormulario", () => ({
  DestinatarioFormulario: (p: {
    titulo: string;
    textoConfirmar: string;
    erroresServidor: Record<string, string[]>;
    onConfirmar: (datos: DatosDestinatario) => void;
    onCancelar: () => void;
  }) => (
    <div data-testid="formulario-destinatario">
      <button type="button" onClick={() => p.onConfirmar(DESTINATARIO)}>
        Confirmar destinatario falso
      </button>
      <output data-testid="errores">{JSON.stringify(p.erroresServidor)}</output>
    </div>
  ),
}));

const { NotificacionesDelActo } = await import("./NotificacionesDelActo");

const RESUMEN_CERO: ResumenDelActo = {
  total: 0,
  notificadas: 0,
  pendientes: 0,
};

const RESUMEN_DOS: ResumenDelActo = {
  total: 2,
  notificadas: 1,
  pendientes: 1,
};

function construirActo(overrides: Partial<Acto> = {}): Acto {
  return {
    id: "a1",
    tipo: "RESOLUCION",
    denominacion_tipo: null,
    numero: "DA-001-2026",
    fecha: "2026-01-01",
    lugar: "Caracas",
    cargo: {
      id: "c1",
      codigo: "C-01",
      denominacion: "Cargo de ejemplo",
      unidad_codigo: "U-01",
      unidad_denominacion: "Unidad de ejemplo",
    },
    competencia: { accion: "APROBAR", materia: "CONTRATACIONES" },
    fundamento_competencia: "Reglamento interno, art. 12",
    funcionario: "Funcionaria de prueba",
    titularidad: "TITULAR",
    delegacion_numero: null,
    delegacion_fecha: null,
    caracter: "PARTICULAR",
    simple_tramite: false,
    destinatario: "Proveedor de prueba",
    asunto: "Asunto de prueba",
    hechos: "Hechos",
    fundamentos: "Fundamentos",
    decision: "Decisión",
    estado: "EMITIDO",
    faltantes_para_emitir: [],
    documento_acto_id: "d-acto",
    medio: null,
    referencia_publicacion: null,
    fecha_publicacion_notificacion: null,
    documento_eficacia_id: null,
    fecha_eficacia: null,
    notificaciones: RESUMEN_CERO,
    revocado_por: null,
    anulado_por: null,
    revoca_a: [],
    anula_a: [],
    version: 1,
    emitido_en: "2026-01-01T12:00:00Z",
    emitido_por: "ua",
    creado_en: "2026-01-01T10:00:00Z",
    ...overrides,
  };
}

const N1: NotificacionResumen = {
  id: "n1",
  acto: {
    id: "a1",
    tipo: "RESOLUCION",
    denominacion_tipo: null,
    numero: "DA-001-2026",
    fecha: "2026-01-01",
    estado: "EMITIDO",
  },
  tipo_persona: "NATURAL",
  nombre: "Pedro Pérez",
  identificacion: "V-12345678",
  estado: "NOTIFICADA",
  intentos: 1,
  fecha_notificacion: "2026-01-05",
  medio_notificacion: "PERSONAL",
};

const N2: NotificacionResumen = {
  id: "n2",
  acto: {
    id: "a1",
    tipo: "RESOLUCION",
    denominacion_tipo: null,
    numero: "DA-001-2026",
    fecha: "2026-01-01",
    estado: "EMITIDO",
  },
  tipo_persona: "JURIDICA",
  nombre: "Comercial Ejemplo C.A.",
  identificacion: "J-12345678-9",
  estado: "PENDIENTE",
  intentos: 0,
  fecha_notificacion: null,
  medio_notificacion: null,
};

const LISTA_VACIA: ListaNotificaciones = {
  anio: 2026,
  items: [],
  total: 0,
};

const LISTA_DOS: ListaNotificaciones = {
  anio: 2026,
  items: [N1, N2],
  total: 2,
};

function renderConRespuesta(
  acto: Acto,
  lista: ListaNotificaciones = LISTA_VACIA,
) {
  apiFetchMock.mockImplementation((url: string) => {
    if (url === "/gobierno/notificaciones?anio=2026&acto_id=a1") {
      return Promise.resolve(lista);
    }
    return Promise.reject(new Error(`URL inesperada: ${url}`));
  });

  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/actos/a1"]}>
        <Routes>
          <Route
            path="/actos/a1"
            element={<NotificacionesDelActo acto={acto} />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  apiFetchMock.mockReset();
  notify.mockReset();
  capacidades = new Set<string>();
});

describe("NotificacionesDelActo", () => {
  it("NDA-01 sin gobierno_notificaciones:view muestra permiso denegado y no llama apiFetch", async () => {
    capacidades = new Set<string>();

    renderConRespuesta(construirActo());

    expect(
      screen.getByText(
        "No tiene permiso para ver las notificaciones del acto.",
      ),
    ).toBeInTheDocument();
    await waitFor(() => expect(apiFetchMock).not.toHaveBeenCalled());
  });

  it("NDA-02 pide exactamente la URL con anio extraído del texto de la fecha", async () => {
    capacidades = new Set(["gobierno_notificaciones:view"]);

    renderConRespuesta(construirActo());

    await screen.findByText(
      "Agregue a cada interesado para notificarle el acto (LOPA art. 73).",
    );
    expect(apiFetchMock).toHaveBeenCalledExactlyOnceWith(
      "/gobierno/notificaciones?anio=2026&acto_id=a1",
    );
  });

  it("NDA-03 acto EMITIDO sin destinatarios muestra aviso y no muestra tabla", async () => {
    capacidades = new Set(["gobierno_notificaciones:view"]);

    renderConRespuesta(construirActo(), LISTA_VACIA);

    expect(
      await screen.findByText(
        "Agregue a cada interesado para notificarle el acto (LOPA art. 73).",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("NDA-04 EMITIDO con dos notificaciones muestra resumen y fila de Pedro Pérez", async () => {
    capacidades = new Set(["gobierno_notificaciones:view"]);

    renderConRespuesta(
      construirActo({ notificaciones: RESUMEN_DOS }),
      LISTA_DOS,
    );

    expect(
      await screen.findByText("Faltan 1 por notificar de 2."),
    ).toBeInTheDocument();

    const tabla = screen.getByRole("table");
    const fila = within(tabla).getByText("Pedro Pérez").closest("tr");
    expect(fila).not.toBeNull();

    const enlace = within(fila as HTMLTableRowElement).getByRole("link", {
      name: "Pedro Pérez",
    });
    expect(enlace).toHaveAttribute("href", "/gobierno/notificaciones/n1");
    expect(
      within(fila as HTMLTableRowElement).getByText(
        ETIQUETA_TIPO_PERSONA.NATURAL,
      ),
    ).toBeInTheDocument();
    expect(
      within(fila as HTMLTableRowElement).getByText("V-12345678"),
    ).toBeInTheDocument();
    expect(
      within(fila as HTMLTableRowElement).getByText(
        ETIQUETA_ESTADO_NOTIFICACION.NOTIFICADA,
      ),
    ).toBeInTheDocument();
  });

  it("NDA-05 acto EFICAZ muestra todos notificados y no muestra botón agregar aunque tenga edit", async () => {
    capacidades = new Set([
      "gobierno_notificaciones:view",
      "gobierno_notificaciones:edit",
    ]);

    renderConRespuesta(construirActo({ estado: "EFICAZ" }), LISTA_VACIA);

    expect(
      await screen.findByText("Todos los destinatarios están notificados."),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Agregar destinatario" }),
    ).not.toBeInTheDocument();
  });

  it("NDA-06 sin gobierno_notificaciones:edit no muestra botón Agregar destinatario", async () => {
    capacidades = new Set(["gobierno_notificaciones:view"]);

    renderConRespuesta(construirActo(), LISTA_VACIA);

    await screen.findByText(
      "Agregue a cada interesado para notificarle el acto (LOPA art. 73).",
    );
    expect(
      screen.queryByRole("button", { name: "Agregar destinatario" }),
    ).not.toBeInTheDocument();
  });

  it("NDA-07 con edit agrega destinatario correctamente y cierra el formulario", async () => {
    capacidades = new Set([
      "gobierno_notificaciones:view",
      "gobierno_notificaciones:edit",
    ]);

    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/notificaciones?anio=2026&acto_id=a1") {
        return Promise.resolve(LISTA_VACIA);
      }
      if (url === "/gobierno/notificaciones") {
        return Promise.resolve({});
      }
      return Promise.reject(new Error(`URL inesperada: ${url}`));
    });

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });

    const user = userEvent.setup();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/actos/a1"]}>
          <Routes>
            <Route
              path="/actos/a1"
              element={<NotificacionesDelActo acto={construirActo()} />}
            />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await user.click(
      await screen.findByRole("button", { name: "Agregar destinatario" }),
    );
    await user.click(
      screen.getByRole("button", { name: "Confirmar destinatario falso" }),
    );

    await waitFor(() =>
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/notificaciones",
        {
          method: "POST",
          body: {
            acto_id: "a1",
            ...DESTINATARIO,
          },
        },
      ),
    );

    await waitFor(() =>
      expect(notify).toHaveBeenCalledWith({
        type: "success",
        title: "Destinatario agregado",
      }),
    );

    await waitFor(() =>
      expect(
        screen.queryByTestId("formulario-destinatario"),
      ).not.toBeInTheDocument(),
    );
  });

  it("NDA-08 POST rechazado con duplicado muestra errores en formulario y no notifica", async () => {
    capacidades = new Set([
      "gobierno_notificaciones:view",
      "gobierno_notificaciones:edit",
    ]);

    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/notificaciones?anio=2026&acto_id=a1") {
        return Promise.resolve(LISTA_VACIA);
      }
      if (url === "/gobierno/notificaciones") {
        return Promise.reject(
          new ApiError(409, {
            code: "GOV_NOTIFICATION_RECIPIENT_DUPLICATE",
            message: "Ya está registrado",
          }),
        );
      }
      return Promise.reject(new Error(`URL inesperada: ${url}`));
    });

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });

    const user = userEvent.setup();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/actos/a1"]}>
          <Routes>
            <Route
              path="/actos/a1"
              element={<NotificacionesDelActo acto={construirActo()} />}
            />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await user.click(
      await screen.findByRole("button", { name: "Agregar destinatario" }),
    );
    await user.click(
      screen.getByRole("button", { name: "Confirmar destinatario falso" }),
    );

    const salidaErrores = await screen.findByTestId("errores");
    await waitFor(() =>
      expect(salidaErrores.textContent).toContain(
        '{"identificacion":["Ya está registrado"]}',
      ),
    );
    expect(notify).not.toHaveBeenCalled();
  });

  it("NDA-09a rechazo 422 con field_errors muestra errores de nombre", async () => {
    capacidades = new Set([
      "gobierno_notificaciones:view",
      "gobierno_notificaciones:edit",
    ]);

    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/notificaciones?anio=2026&acto_id=a1") {
        return Promise.resolve(LISTA_VACIA);
      }
      if (url === "/gobierno/notificaciones") {
        return Promise.reject(
          new ApiError(422, {
            code: "VALIDATION_ERROR",
            message: "Datos inválidos",
            field_errors: { nombre: ["Campo obligatorio"] },
          }),
        );
      }
      return Promise.reject(new Error(`URL inesperada: ${url}`));
    });

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });

    const user = userEvent.setup();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/actos/a1"]}>
          <Routes>
            <Route
              path="/actos/a1"
              element={<NotificacionesDelActo acto={construirActo()} />}
            />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await user.click(
      await screen.findByRole("button", { name: "Agregar destinatario" }),
    );
    await user.click(
      screen.getByRole("button", { name: "Confirmar destinatario falso" }),
    );

    const salidaErrores = await screen.findByTestId("errores");
    await waitFor(() =>
      expect(salidaErrores.textContent).toContain(
        '{"nombre":["Campo obligatorio"]}',
      ),
    );
  });

  it("NDA-09b rechazo 403 notifica permiso denegado", async () => {
    capacidades = new Set([
      "gobierno_notificaciones:view",
      "gobierno_notificaciones:edit",
    ]);

    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/notificaciones?anio=2026&acto_id=a1") {
        return Promise.resolve(LISTA_VACIA);
      }
      if (url === "/gobierno/notificaciones") {
        return Promise.reject(
          new ApiError(403, {
            code: "FORBIDDEN",
            message: "Prohibido",
          }),
        );
      }
      return Promise.reject(new Error(`URL inesperada: ${url}`));
    });

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });

    const user = userEvent.setup();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/actos/a1"]}>
          <Routes>
            <Route
              path="/actos/a1"
              element={<NotificacionesDelActo acto={construirActo()} />}
            />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await user.click(
      await screen.findByRole("button", { name: "Agregar destinatario" }),
    );
    await user.click(
      screen.getByRole("button", { name: "Confirmar destinatario falso" }),
    );

    await waitFor(() =>
      expect(notify).toHaveBeenCalledWith({
        type: "error",
        title: "No tiene permiso para esta acción",
      }),
    );
  });

  it("NDA-09c rechazo 409 acto no emitido notifica error con descripción", async () => {
    capacidades = new Set([
      "gobierno_notificaciones:view",
      "gobierno_notificaciones:edit",
    ]);

    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/notificaciones?anio=2026&acto_id=a1") {
        return Promise.resolve(LISTA_VACIA);
      }
      if (url === "/gobierno/notificaciones") {
        return Promise.reject(
          new ApiError(409, {
            code: "GOV_NOTIFICATION_ACT_NOT_EMITTED",
            message: "Acto no emitido",
          }),
        );
      }
      return Promise.reject(new Error(`URL inesperada: ${url}`));
    });

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });

    const user = userEvent.setup();
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={["/actos/a1"]}>
          <Routes>
            <Route
              path="/actos/a1"
              element={<NotificacionesDelActo acto={construirActo()} />}
            />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await user.click(
      await screen.findByRole("button", { name: "Agregar destinatario" }),
    );
    await user.click(
      screen.getByRole("button", { name: "Confirmar destinatario falso" }),
    );

    await waitFor(() =>
      expect(notify).toHaveBeenCalledWith({
        type: "error",
        title: "No fue posible completar la operación",
        description: "Acto no emitido",
      }),
    );
  });
});
