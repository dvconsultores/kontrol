import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";

const apiFetchMock = vi.fn();
vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}));



const descargarArchivoMock = vi.fn();
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
  useCompany: () => ({
    activeCompanyId: "c1",
    activeCompany: { id: "c1", legal_name: "Contenedor 1" },
  }),
}));

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({
    notify: notifyMock,
  }),
}));

const notifyMock = vi.fn();

import { ApiError } from "@/api/client";
import { ReporteControlInternoPage } from "./ReporteControlInternoPage";

function crearDatosBase() {
  return {
    periodo: { desde: "2025-01-01", hasta: "2025-01-31" },
    generado_en: "2025-02-01T10:00:00Z",
    conflictos_sod: {
      total: 2,
      por_regla: [
        {
          regla_codigo: "SOD-001",
          regla_nombre: "Conflicto de pagos",
          proceso: "pago",
          proceso_etiqueta: "Pagos",
          total: 2,
        },
      ],
      eventos: [
        {
          evento_id: "evt-1",
          fecha: "2025-01-15T10:00:00Z",
          usuario: "usuario1",
          regla_codigo: "SOD-001",
          regla_nombre: "Conflicto de pagos",
          proceso: "pago",
          proceso_etiqueta: "Pagos",
          accion_etiqueta: "Autorizar pago",
          accion_previa_etiqueta: "Crear pago",
        },
      ],
    },
    bloqueos_identidad: {
      total: 1,
      por_motivo: [{ codigo: "M1", etiqueta: "Falta identidad", total: 1 }],
      eventos: [],
    },
    bloqueos_cierre: {
      total: 0,
      por_politica: [],
      eventos: [],
    },
    hallazgos: {
      disponible: true,
      motivo: null as string | null,
      por_estado: { ABIERTO: 1 },
      por_riesgo: { ALTO: 1 },
      acciones_por_estado: { PENDIENTE: 1 },
      acciones_vencidas: [
        {
          hallazgo_id: "h-1",
          hallazgo_codigo: "H-001",
          hallazgo_titulo: "Hallazgo de prueba",
          accion_orden: 1,
          descripcion: "Corregir procedimiento",
          cargo: "Gerente",
          unidad: "Finanzas",
          fecha_objetivo: "2025-01-10",
          porcentaje: 40,
          dias_atraso: 3,
        },
      ],
    },
    overrides: { disponible: false, motivo: "Módulo de overrides no disponible" },
    operaciones_duplicadas: {
      disponible: false,
      motivo: "Módulo de duplicadas no disponible",
    },
  };
}

function renderPagina() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ReporteControlInternoPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  apiFetchMock.mockReset();
  descargarArchivoMock.mockReset();
  notifyMock.mockReset();
  capacidades = new Set<string>(["gobierno_auditoria:view"]);
});

describe("ReporteControlInternoPage", () => {
  it("pinta las cuatro tarjetas y conflictos recientes con enlace a la bitácora", async () => {
    apiFetchMock.mockResolvedValue(crearDatosBase());
    renderPagina();

    expect(
      await screen.findByText("Conflictos de segregación"),
    ).toBeInTheDocument();

    expect(screen.getByText("Bloqueos de identidad")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "Bloqueos de cierre" })).toBeInTheDocument();
    expect(within(screen.getByRole("region", { name: "Resumen" })).getByText("Acciones vencidas")).toBeInTheDocument();

    const enlace = await screen.findByRole("link", {
      name: "Ver en la bitácora",
    });
    expect(enlace).toHaveAttribute("href", "/gobierno/bitacora/evt-1");
  });

  it("con hallazgos.disponible false muestra el motivo y la tarjeta '—'", async () => {
    const datos = crearDatosBase();
    datos.hallazgos.disponible = false;
    datos.hallazgos.motivo = "Sin hallazgos disponibles" as string | null;
    datos.hallazgos.acciones_vencidas = [];
    apiFetchMock.mockResolvedValue(datos);
    renderPagina();

    expect(await screen.findByText("Sin hallazgos disponibles")).toBeInTheDocument();
    const tarjeta = screen.getByText("Acciones vencidas").closest("div");
    expect(tarjeta).toBeInTheDocument();
    expect(within(tarjeta as HTMLElement).getByText("—")).toBeInTheDocument();
  });

  it("muestra el enlace del hallazgo vencido y 3 días de atraso", async () => {
    apiFetchMock.mockResolvedValue(crearDatosBase());
    renderPagina();

    const enlace = await screen.findByRole("link", { name: "H-001" });
    expect(enlace).toHaveAttribute("href", "/gobierno/hallazgos/h-1");
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("muestra los motivos de overrides y operaciones duplicadas", async () => {
    apiFetchMock.mockResolvedValue(crearDatosBase());
    renderPagina();

    expect(
      await screen.findByText("Módulo de overrides no disponible"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Módulo de duplicadas no disponible"),
    ).toBeInTheDocument();
  });

  it("al pulsar Aplicar con fechas pide la URL con ?desde=...&hasta=...", async () => {
    apiFetchMock.mockResolvedValue(crearDatosBase());
    const usuario = userEvent.setup();
    renderPagina();

    await screen.findByText("Conflictos de segregación");

    await usuario.type(screen.getByLabelText("Desde"), "2025-02-01");
    await usuario.type(screen.getByLabelText("Hasta"), "2025-02-28");
    await usuario.click(screen.getByRole("button", { name: "Aplicar" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenLastCalledWith(
        "/gobierno/control-interno/reporte?desde=2025-02-01&hasta=2025-02-28",
      );
    });
  });

  it("tras un reporte correcto, un 422 conserva los filtros y muestra el mensaje", async () => {
    apiFetchMock.mockResolvedValueOnce(crearDatosBase());
    apiFetchMock.mockRejectedValueOnce(
      new ApiError(422, {
        code: "INVALID_DATE_RANGE",
        message: "La fecha inicial no puede ser posterior a la fecha final",
        field_errors: { desde: ["La fecha inicial no puede ser posterior a la fecha final"] },
      }),
    );

    renderPagina();

    const usuario = userEvent.setup();
    await screen.findByText("Conflictos de segregación");

    await usuario.type(screen.getByLabelText("Desde"), "2025-03-01");
    await usuario.type(screen.getByLabelText("Hasta"), "2025-02-01");
    await usuario.click(screen.getByRole("button", { name: /aplicar/i }));

    expect(await screen.findByText("La fecha inicial no puede ser posterior a la fecha final")).toBeInTheDocument();
    expect(screen.getByLabelText("Desde")).toBeInTheDocument();
  });


});
