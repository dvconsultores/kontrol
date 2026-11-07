import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router";
import { apiFetch, ApiError } from "@/api/client";
import { useAutoridad } from "@/app/autoridad/AutoridadContext";
import { useCompany } from "@/app/contexts/CompanyContext";
import { useNotifications } from "@/app/contexts/NotificationContext";
import { ProgramaPage } from "./ProgramaPage";
import type { ProgramaDetalle } from "@/modules/gobierno/api";

vi.mock("@/api/client", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/api/client")>();
  return {
    ...original,
    apiFetch: vi.fn(),
  };
});

vi.mock("@/app/autoridad/AutoridadContext", () => ({
  useAutoridad: vi.fn(),
}));

vi.mock("@/app/contexts/CompanyContext", () => ({
  useCompany: vi.fn(),
}));

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: vi.fn(),
}));

vi.mock("./DeclaracionesPrograma", () => ({
  DeclaracionesPrograma: () => <div data-testid="declaraciones-programa" />,
}));

vi.mock("./LineasPrograma", () => ({
  LineasPrograma: () => <div data-testid="lineas-programa" />,
}));

const mockedApiFetch = vi.mocked(apiFetch);
const mockedUseAutoridad = vi.mocked(useAutoridad);
const mockedUseCompany = vi.mocked(useCompany);
const mockedUseNotifications = vi.mocked(useNotifications);

const programaFixture: ProgramaDetalle = {
  id: "prog-1",
  codigo: "P-001",
  ejercicio: 2025,
  moneda: "USD",
  mes_inicial: 1,
  estado: "BORRADOR",
  version: 1,
  version_vigente: null,
  version_vista: 1,
  borrador_numero: 1,
  disponibilidad_inicial: "10000.00",
  cerrado_por: null,
  cerrado_en: null,
  motivo_cierre: null,
  registrado_por: "usuario@example.com",
  registrado_en: "2025-01-01T00:00:00Z",
  declaraciones: [],
  lineas: [],
  meses: [
    {
      mes: 1,
      inicial: "10000.00",
      ingresos: "5000.00",
      desembolsos: "3000.00",
      final: "12000.00",
      deficit: false,
    },
  ],
  hay_deficit: false,
  versiones: [
    {
      numero: 1,
      estado: "BORRADOR",
      motivo: null,
      activada_por: null,
      activada_en: null,
      registrado_por: "usuario@example.com",
      registrado_en: "2025-01-01T00:00:00Z",
    },
  ],
  historia: [],
};

let detalleActual: ProgramaDetalle;
let respuestaEscritura: (() => Promise<ProgramaDetalle>) | null;

function configurarDominio() {
  detalleActual = programaFixture;
  respuestaEscritura = null;

  mockedUseCompany.mockReturnValue({
    activeCompanyId: "company-1",
  } as unknown as ReturnType<typeof useCompany>);

  mockedUseNotifications.mockReturnValue({
    notify: vi.fn(),
  } as unknown as ReturnType<typeof useNotifications>);

  mockedUseAutoridad.mockReturnValue({
    tiene: (permiso: string) => {
      if (permiso === "gobierno_caja:view") return true;
      if (permiso === "gobierno_caja:manage") return true;
      if (permiso === "gobierno_caja:activate") return true;
      return false;
    },
  } as unknown as ReturnType<typeof useAutoridad>);

  mockedApiFetch.mockImplementation(
    async <T,>(_ruta: string, opciones?: { method?: string; body?: unknown; ifMatch?: string }): Promise<T> => {
      if (opciones?.method === "POST") {
        if (respuestaEscritura) {
          return respuestaEscritura() as Promise<T>;
        }
        return detalleActual as T;
      }
      return detalleActual as T;
    },
  );
}

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/gobierno/tesoreria/programacion/prog-1"]}>
        <Routes>
          <Route path="/gobierno/tesoreria/programacion/:programaId" element={<ProgramaPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ProgramaPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    configurarDominio();
  });

  it("muestra detalle: encabezado, aviso de semántica y datos del programa", async () => {
    renderPage();

    expect(await screen.findByRole("heading", { name: "Programa P-001" })).toBeInTheDocument();
    expect(
      screen.getByText(
        "Disponibilidad de caja proyectada. No es disponibilidad presupuestaria ni saldo bancario.",
      ),
    ).toBeInTheDocument();

    const seccionDatos = screen.getByRole("heading", { name: "Datos del programa" }).closest("section");
    expect(seccionDatos).not.toBeNull();

    const dentroDeDatos = within(seccionDatos as HTMLElement);
    expect(dentroDeDatos.getByText("Ejercicio")).toBeInTheDocument();
    expect(dentroDeDatos.getByText("2025")).toBeInTheDocument();
    expect(dentroDeDatos.getByText("Moneda")).toBeInTheDocument();
    expect(dentroDeDatos.getByText("USD")).toBeInTheDocument();

    expect(screen.getByTestId("declaraciones-programa")).toBeInTheDocument();
    expect(screen.getByTestId("lineas-programa")).toBeInTheDocument();
  });

  it("muestra la tabla de disponibilidad mensual y el aviso de déficit", async () => {
    detalleActual = {
      ...programaFixture,
      meses: [
        {
          mes: 1,
          inicial: "10000.00",
          ingresos: "1000.00",
          desembolsos: "5000.00",
          final: "6000.00",
          deficit: true,
        },
      ],
      hay_deficit: true,
    };

    renderPage();

    expect(await screen.findByRole("heading", { name: "Programa P-001" })).toBeInTheDocument();
    expect(
      within(screen.getByRole("region", { name: "Tabla de disponibilidad mensual del programa" })).getByText("Enero")
    ).toBeInTheDocument();
    expect(screen.getByText("Déficit proyectado")).toBeInTheDocument();
    expect(screen.getByText("El programa puede activarse igualmente.")).toBeInTheDocument();
  });

  it("envía solicitud de activación con ifMatch", async () => {
    const notify = vi.fn();
    mockedUseNotifications.mockReturnValue({
      notify,
    } as unknown as ReturnType<typeof useNotifications>);

    const programaVigente: ProgramaDetalle = {
      ...programaFixture,
      estado: "VIGENTE",
      version: 2,
      version_vigente: 1,
      borrador_numero: 2,
      version_vista: 2,
    };
    detalleActual = programaVigente;

    renderPage();

    const botonActivar = await screen.findByRole("button", { name: "Activar versión" });
    await userEvent.click(botonActivar);

    await waitFor(() => {
      expect(mockedApiFetch).toHaveBeenCalledWith(
        "/gobierno/tesoreria/programas/prog-1/activar",
        {
          method: "POST",
          body: {},
          ifMatch: "2",
        },
      );
    });

    await waitFor(() => {
      expect(notify).toHaveBeenCalledWith({ type: "success", title: "Versión activada" });
    });
  });

  it("traduce faltantes de activación en error 409 NOT_READY", async () => {
    const programaConBorrador: ProgramaDetalle = {
      ...programaFixture,
      estado: "VIGENTE",
      version: 2,
      version_vigente: 1,
      borrador_numero: 2,
      version_vista: 2,
    };
    detalleActual = programaConBorrador;

    respuestaEscritura = () =>
      Promise.reject(
        new ApiError(409, {
          code: "GOV_CASH_PROGRAM_NOT_READY",
          message: "Faltan requisitos",
          field_errors: {},
          details: { faltan: ["declaracion", "linea"] },
        }),
      );

    renderPage();

    const botonActivar = await screen.findByRole("button", { name: "Activar versión" });
    await userEvent.click(botonActivar);

    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent(
      "Para continuar el programa necesita: al menos una declaración de disponibilidad, al menos una línea de programación.",
    );

    expect(mockedApiFetch).toHaveBeenCalledWith(
      "/gobierno/tesoreria/programas/prog-1/activar",
      {
        method: "POST",
        body: {},
        ifMatch: "2",
      },
    );
  });

  it("reprograma enviando el motivo y pide versión del borrador", async () => {
    const notify = vi.fn();
    mockedUseNotifications.mockReturnValue({
      notify,
    } as unknown as ReturnType<typeof useNotifications>);

    const programaVigente: ProgramaDetalle = {
      ...programaFixture,
      estado: "VIGENTE",
      version: 3,
      version_vigente: 3,
      borrador_numero: null,
      version_vista: 3,
    };

    const programaReprogramado: ProgramaDetalle = {
      ...programaVigente,
      borrador_numero: 4,
      estado: "VIGENTE",
      version: 4,
      version_vista: 4,
    };

    detalleActual = programaVigente;
    respuestaEscritura = () => {
      detalleActual = programaReprogramado;
      return Promise.resolve(programaReprogramado);
    };

    renderPage();

    const botonReprogramar = await screen.findByRole("button", { name: "Reprogramar" });
    await userEvent.click(botonReprogramar);

    const textarea = screen.getByLabelText(/^Motivo/);
    await userEvent.type(textarea, "corto");

    const botonConfirmar = screen.getByRole("button", {
      name: "Confirmar reprogramación",
    });
    expect(botonConfirmar).toBeDisabled();

    await userEvent.clear(textarea);
    await userEvent.type(textarea, "Motivo suficientemente largo para reprogramar");

    expect(botonConfirmar).toBeEnabled();
    await userEvent.click(botonConfirmar);

    await waitFor(() => {
      expect(mockedApiFetch).toHaveBeenCalledWith(
        "/gobierno/tesoreria/programas/prog-1/reprogramar",
        {
          method: "POST",
          body: { motivo: "Motivo suficientemente largo para reprogramar" },
          ifMatch: "3",
        },
      );
    });

    expect(await screen.findByRole("button", { name: "Activar versión" })).toBeInTheDocument();
    await waitFor(() => {
      expect(mockedApiFetch).toHaveBeenCalledWith("/gobierno/tesoreria/programas/prog-1?version=4");
    });
  });

  it("oculta acciones de activar y cerrar cuando no hay permiso de activate", async () => {
    mockedUseAutoridad.mockReturnValue({
      tiene: (permiso: string) => {
        if (permiso === "gobierno_caja:view") return true;
        if (permiso === "gobierno_caja:manage") return true;
        return false;
      },
    } as unknown as ReturnType<typeof useAutoridad>);

    renderPage();

    const seccionDatos = await screen.findByText("Disponibilidad inicial");
    expect(seccionDatos).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Activar versión" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Cerrar programa" })).not.toBeInTheDocument();
  });

  it("muestra aviso de solo lectura para versiones anteriores", async () => {
    detalleActual = {
      ...programaFixture,
      estado: "VIGENTE",
      version: 3,
      version_vista: 1,
      version_vigente: 3,
      borrador_numero: null,
      mes_inicial: 1,
      meses: [
        {
          mes: 1,
          inicial: "10000.00",
          ingresos: "5000.00",
          desembolsos: "3000.00",
          final: "12000.00",
          deficit: false,
        },
      ],
    };

    renderPage();

    expect(await screen.findByText("Esta versión es de solo lectura.")).toBeInTheDocument();
  });

  it("muestra aviso de conflicto de versión STALE", async () => {
    const programaVigente: ProgramaDetalle = {
      ...programaFixture,
      estado: "VIGENTE",
      version: 2,
      version_vigente: 1,
      borrador_numero: 2,
      version_vista: 2,
    };
    detalleActual = programaVigente;

    respuestaEscritura = () =>
      Promise.reject(
        new ApiError(409, {
          code: "GOV_CASH_PROGRAM_STALE",
          message: "Versión obsoleta",
          field_errors: {},
          details: null,
        }),
      );

    renderPage();

    const botonActivar = await screen.findByRole("button", { name: "Activar versión" });
    await userEvent.click(botonActivar);

    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent(
      "El programa cambió desde que lo abrió. Se recargaron los datos; revise y vuelva a intentarlo.",
    );

    expect(mockedApiFetch).toHaveBeenCalledWith(
      "/gobierno/tesoreria/programas/prog-1/activar",
      {
        method: "POST",
        body: {},
        ifMatch: "2",
      },
    );
  });

  it("muestra conflicto de SoD", async () => {
    const programaVigente: ProgramaDetalle = {
      ...programaFixture,
      estado: "VIGENTE",
      version: 2,
      version_vigente: 1,
      borrador_numero: 2,
      version_vista: 2,
    };
    detalleActual = programaVigente;

    respuestaEscritura = () =>
      Promise.reject(
        new ApiError(409, {
          code: "GOV_SOD_CONFLICT",
          message: "Conflicto de segregación de funciones",
          field_errors: {},
          details: {
            regla_codigo: "R-1",
            regla_nombre: "No puede activar y aprobar",
            accion: "activar",
            accion_etiqueta: "Activar",
            accion_previa: "aprobar",
            accion_previa_etiqueta: "Aprobar",
            objeto_tipo: "programa",
            objeto_id: "prog-1",
            previa_en: "2025-01-01T00:00:00Z",
          },
        }),
      );

    renderPage();

    const botonActivar = await screen.findByRole("button", { name: "Activar versión" });
    await userEvent.click(botonActivar);

    expect(
      await screen.findByText("Operación bloqueada por segregación de funciones"),
    ).toBeInTheDocument();

    expect(mockedApiFetch).toHaveBeenCalledWith(
      "/gobierno/tesoreria/programas/prog-1/activar",
      {
        method: "POST",
        body: {},
        ifMatch: "2",
      },
    );
  });

  it("muestra el panel de bloqueo material al cerrar", async () => {
    const programaVigente: ProgramaDetalle = {
      ...programaFixture,
      estado: "VIGENTE",
      version: 2,
      version_vigente: 1,
      borrador_numero: null,
      version_vista: 1,
    };
    detalleActual = programaVigente;

    respuestaEscritura = () =>
      Promise.reject(
        new ApiError(409, {
          code: "GOV_MATERIAL_CLOSE_BLOCKED",
          message: "x",
          details: {
            politica_codigo: "PC-001",
            politica_nombre: "Política de prueba",
            proceso: "TRE02_CERRAR_PROGRAMA",
            objeto_codigo: "PF-2026-VES",
            total: 1,
            dueno: "Control Interno",
            controles: [],
          },
        }),
      );

    renderPage();
    const cerrar = await screen.findByRole("button", { name: "Cerrar programa" });
    await userEvent.click(cerrar);
    await userEvent.type(screen.getByLabelText(/^Motivo/), "Motivo de cierre válido");
    await userEvent.click(screen.getByRole("button", { name: "Confirmar cierre" }));
    expect(await screen.findByText("Cierre bloqueado por control material")).toBeInTheDocument();
    expect(screen.getByText(/PC-001/)).toBeInTheDocument();
  });

  it("muestra programa cerrado sin acciones y con datos del cierre", async () => {
    detalleActual = {
      ...programaFixture,
      estado: "CERRADO",
      version: 3,
      version_vigente: 3,
      borrador_numero: null,
      cerrado_por: "usuario@example.com",
      cerrado_en: "2025-02-01T00:00:00Z",
      motivo_cierre: "Se cerró por fin de ejercicio",
    };

    renderPage();

    expect(await screen.findByText("Un programa cerrado no se reabre.")).toBeInTheDocument();
    expect(screen.getByText("Datos del cierre")).toBeInTheDocument();
    expect(screen.getByText("Se cerró por fin de ejercicio")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Activar versión" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Reprogramar" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Descartar borrador" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Cerrar programa" })).not.toBeInTheDocument();
  });

  it("ver versión solicita la versión indicada", async () => {
    const versiones: ProgramaDetalle["versiones"] = [
      {
        numero: 1,
        estado: "VIGENTE",
        motivo: null,
        activada_por: "usuario@example.com",
        activada_en: "2025-01-01T00:00:00Z",
        registrado_por: "usuario@example.com",
        registrado_en: "2025-01-01T00:00:00Z",
      },
      {
        numero: 2,
        estado: "SUPERADA",
        motivo: null,
        activada_por: "usuario@example.com",
        activada_en: "2025-01-02T00:00:00Z",
        registrado_por: "usuario@example.com",
        registrado_en: "2025-01-02T00:00:00Z",
      },
      {
        numero: 3,
        estado: "VIGENTE",
        motivo: null,
        activada_por: "usuario@example.com",
        activada_en: "2025-01-03T00:00:00Z",
        registrado_por: "usuario@example.com",
        registrado_en: "2025-01-03T00:00:00Z",
      },
    ];

    detalleActual = {
      ...programaFixture,
      versiones,
    };

    renderPage();

    const botonVerVersion1 = await screen.findByRole("button", { name: "Ver versión 1" });
    await userEvent.click(botonVerVersion1);

    await waitFor(() => {
      expect(mockedApiFetch).toHaveBeenCalledWith(
        "/gobierno/tesoreria/programas/prog-1?version=1",
      );
    });
  });
});
