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

const notifyMock = vi.fn();
vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({
    notify: notifyMock,
  }),
}));

import { ApiError } from "@/api/client";
import { ReporteContratacionesPage } from "./ReporteContratacionesPage";

function crearDatosBase() {
  return {
    periodo: { desde: "2025-01-01", hasta: "2025-01-31" },
    generado_en: "2025-02-01T10:00:00Z",
    totales: {
      expedientes: 10,
      abiertos: 4,
      cerrados: 5,
      descartados: 1,
    },
    por_modalidad: [
      { codigo: "MOD1", etiqueta: "Concurso abierto", total: 6 },
      { codigo: "MOD2", etiqueta: "Contratación directa", total: 4 },
    ],
    por_estado: [
      { codigo: "ABIERTO", etiqueta: "Abierto", total: 4 },
      { codigo: "CERRADO", etiqueta: "Cerrado", total: 5 },
      { codigo: "DESCARTADO", etiqueta: "Descartado", total: 1 },
    ],
    por_tipo: [
      { codigo: "OBRA", etiqueta: "Obra", total: 3 },
      { codigo: "SERVICIO", etiqueta: "Servicio", total: 7 },
    ],
    por_unidad: [
      { unidad_id: "u1", unidad_nombre: "Unidad de compras", total: 8 },
      { unidad_id: "u2", unidad_nombre: "Unidad de TI", total: 2 },
    ],
    resultados: [
      { codigo: "ADJUDICADO", etiqueta: "Adjudicado", total: 5 },
      { codigo: "DESIERTO", etiqueta: "Desierto", total: 5 },
    ],
    proveedores: [
      {
        documento: "V-12345678-9",
        nombre: "Proveedor Uno C.A.",
        ofertas: 3,
        adjudicaciones: 1,
      },
      {
        documento: "J-98765432-1",
        nombre: "Proveedor Dos S.A.",
        ofertas: 5,
        adjudicaciones: 4,
      },
    ],
    tiempos: {
      por_modalidad: [
        {
          codigo: "MOD1",
          etiqueta: "Concurso abierto",
          expedientes: 6,
          inicio_recepcion: 10.5,
          recepcion_evaluacion: 5.2,
          evaluacion_decision: 3.1,
          inicio_cierre: 18.8,
        },
        {
          codigo: "MOD2",
          etiqueta: "Contratación directa",
          expedientes: 4,
          inicio_recepcion: null,
          recepcion_evaluacion: 2.0,
          evaluacion_decision: null,
          inicio_cierre: 7.3,
        },
      ],
      global: {
        inicio_recepcion: 9.4,
        recepcion_evaluacion: 4.1,
        evaluacion_decision: 3.0,
        inicio_cierre: 16.5,
      },
    },
    desviaciones: {
      a_tiempo: 8,
      con_atraso: 1,
      vencidos: 1,
      hitos: [
        {
          expediente_id: "exp-1",
          expediente_numero: "EXP-001",
          hito: "Recepción de ofertas",
          fecha_prevista: "2025-01-10",
          fecha_real: "2025-01-15",
          estado: "CON_ATRASO",
          dias: 5,
        },
        {
          expediente_id: "exp-2",
          expediente_numero: "EXP-002",
          hito: "Decisión",
          fecha_prevista: "2025-01-20",
          fecha_real: null,
          estado: "VENCIDO",
          dias: 10,
        },
      ],
    },
    monto: {
      disponible: false,
      motivo: "Módulo de montos no disponible",
      nota: "Nota de monto",
      por_moneda: [],
      adjudicaciones_con_monto: 0,
      adjudicaciones_sin_monto: 0,
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
        <ReporteContratacionesPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  apiFetchMock.mockReset();
  descargarArchivoMock.mockReset();
  notifyMock.mockReset();
  capacidades = new Set<string>(["gobierno_expedientes:view"]);
});

describe("ReporteContratacionesPage", () => {
  it("pinta las tarjetas del resumen y la tabla de proveedores", async () => {
    apiFetchMock.mockResolvedValue(crearDatosBase());
    renderPagina();

    expect(
      await screen.findByRole("region", { name: "Resumen" }),
    ).toBeInTheDocument();

    const resumen = screen.getByRole("region", { name: "Resumen" });
    expect(within(resumen).getByText("Expedientes")).toBeInTheDocument();
    expect(within(resumen).getByText("Abiertos")).toBeInTheDocument();
    expect(within(resumen).getByText("Cerrados")).toBeInTheDocument();
    expect(within(resumen).getByText("Descartados")).toBeInTheDocument();

    expect(
      await screen.findByRole("region", {
        name: "Ofertas y adjudicaciones por proveedor",
      }),
    ).toBeInTheDocument();

    const tablaProveedores = screen.getByRole("region", {
      name: "Ofertas y adjudicaciones por proveedor",
    });
    expect(within(tablaProveedores).getByText("V-12345678-9")).toBeInTheDocument();
    expect(within(tablaProveedores).getByText("Proveedor Uno C.A.")).toBeInTheDocument();
    expect(within(tablaProveedores).getByText("Proveedor Dos S.A.")).toBeInTheDocument();
  });

  it("el enlace del hito lleva a /gobierno/contrataciones/expedientes/<id>", async () => {
    apiFetchMock.mockResolvedValue(crearDatosBase());
    renderPagina();

    const enlace = await screen.findByRole("link", { name: "EXP-001" });
    expect(enlace).toHaveAttribute(
      "href",
      "/gobierno/contrataciones/expedientes/exp-1",
    );
  });

  it("null en tiempos se muestra '—'", async () => {
    apiFetchMock.mockResolvedValue(crearDatosBase());
    renderPagina();

    const tablaTiempos = await screen.findByRole("region", {
      name: "Días promedio por modalidad",
    });

    expect(within(tablaTiempos).getAllByText("—").length).toBeGreaterThan(0);
  });

  it("muestra el motivo del monto", async () => {
    apiFetchMock.mockResolvedValue(crearDatosBase());
    renderPagina();

    expect(
      await screen.findByText("Módulo de montos no disponible"),
    ).toBeInTheDocument();
  });

  it("muestra el monto declarado por moneda", async () => {
    const datos = {
      ...crearDatosBase(),
      monto: {
      disponible: true,
      motivo: null,
      nota: "Nota de monto",
      por_moneda: [
        {
          moneda: "VES",
          total_con_tributos: "1160.00",
          monto_sin_iva: "1000.00",
          adjudicaciones: 1,
        },
      ],
      adjudicaciones_con_monto: 1,
      adjudicaciones_sin_monto: 2,
      },
    };
    apiFetchMock.mockResolvedValue(datos);
    renderPagina();

    expect(
      await screen.findByRole("region", {
        name: "Monto declarado por moneda",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("1160.00 VES")).toBeInTheDocument();
    expect(
      screen.getByText("Adjudicaciones sin monto declarado: 2"),
    ).toBeInTheDocument();
  });

  it("al pulsar Aplicar con fechas pide la URL con ?desde=...&hasta=...", async () => {
    apiFetchMock.mockResolvedValue(crearDatosBase());
    const usuario = userEvent.setup();
    renderPagina();

    await screen.findByRole("region", { name: "Resumen" });

    await usuario.type(screen.getByLabelText("Desde"), "2025-02-01");
    await usuario.type(screen.getByLabelText("Hasta"), "2025-02-28");
    await usuario.click(screen.getByRole("button", { name: "Aplicar" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenLastCalledWith(
        "/gobierno/contrataciones/reporte?desde=2025-02-01&hasta=2025-02-28",
      );
    });
  });

  it("tras un reporte correcto, un 422 conserva el campo 'Desde' y muestra el mensaje", async () => {
    apiFetchMock.mockResolvedValueOnce(crearDatosBase());
    apiFetchMock.mockRejectedValueOnce(
      new ApiError(422, {
        code: "INVALID_DATE_RANGE",
        message: "La fecha inicial no puede ser posterior a la fecha final",
        field_errors: {
          desde: ["La fecha inicial no puede ser posterior a la fecha final"],
        },
      }),
    );

    renderPagina();

    const usuario = userEvent.setup();
    await screen.findByRole("region", { name: "Resumen" });

    await usuario.type(screen.getByLabelText("Desde"), "2025-03-01");
    await usuario.type(screen.getByLabelText("Hasta"), "2025-02-01");
    await usuario.click(screen.getByRole("button", { name: /aplicar/i }));

    expect(
      await screen.findByText(
        "La fecha inicial no puede ser posterior a la fecha final",
      ),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Desde")).toBeInTheDocument();
  });
});