import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

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

vi.mock("@/app/contexts/CompanyContext", () => ({
  useCompany: () => ({
    activeCompanyId: "c1",
    activeCompany: { id: "c1", legal_name: "Contenedor 1" },
  }),
}));

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify: vi.fn() }),
}));

vi.mock("@/modules/documentos/AdjuntosPanel", () => ({
  AdjuntosPanel: () => <div>Adjuntos</div>,
}));

const { PresupuestoAprobadoEjercicio } = await import(
  "./PresupuestoAprobadoEjercicio"
);

import type { EjercicioDetalle, PresupuestoAprobadoVista } from "./api";

const detalleBase: EjercicioDetalle = {
  id: "e1",
  anio: 2027,
  moneda_funcional: "VED",
  estado: "BORRADOR" as const,
  version: 3,
  congelado: false,
  reconduccion_definitiva: false,
  precompromiso_activo: false,
  precompromiso_desde: null,
  niveles: [
    { orden: 1, nombre: "Programa" },
    { orden: 2, nombre: "Proyecto" },
  ],
  cerrado_en: null,
  motivo_cierre: null,
  clasificador: null,
  categorias: [],
  fundamentos: [],
  faltantes: [],
  historia: [],
  fijado_en: null,
};

const vistaBase: PresupuestoAprobadoVista = {
  version: 3,
  congelado: false,
  moneda: "VED",
  ingresos: [
    {
      id: "ing1",
      partida: {
        id: "prec1",
        codigo: "301",
        denominacion: "Ingresos propios",
      },
      monto: "1000000.00",
    },
  ],
  creditos: [
    {
      id: "cre1",
      categoria: {
        id: "cat1",
        codigo_completo: "01.02",
        denominacion: "Atención primaria",
      },
      unidad: { id: "uni1", codigo: "DESP", nombre: "Despacho" },
      partida: {
        id: "peg1",
        codigo: "401.01",
        denominacion: "Servicios personales",
      },
      fuente: {
        id: "fue1",
        codigo: "F01",
        denominacion: "Tesoro municipal",
      },
      monto: "600000.00",
    },
  ],
  existencias_tesoro: null,
  totales: {
    ingresos: "1000000.00",
    creditos: "600000.00",
    existencias: "0.00",
    holgura_tesoro: "0",
    disponible: "1000000.00",
    diferencia: "400000.00",
    cuadra: true,
  },
  opciones: {
    categorias: [
      {
        id: "cat1",
        codigo_completo: "01.02",
        denominacion: "Atención primaria",
      },
    ],
    partidas_egreso: [
      {
        id: "peg1",
        codigo: "401.01",
        denominacion: "Servicios personales",
      },
      { id: "peg2", codigo: "402", denominacion: "Materiales" },
    ],
    partidas_recurso: [
      {
        id: "prec1",
        codigo: "301",
        denominacion: "Ingresos propios",
      },
    ],
    fuentes: [
      {
        id: "fue1",
        codigo: "F01",
        denominacion: "Tesoro municipal",
        partidas_permitidas: ["401"],
      },
      {
        id: "fue2",
        codigo: "F02",
        denominacion: "Aportes",
        partidas_permitidas: null,
      },
    ],
  },
};

function renderizar({
  detalle = detalleBase,
  escribirBloque = vi.fn(),
  vista = vistaBase,
  documentos = [],
}: {
  detalle?: EjercicioDetalle;
  escribirBloque?: ReturnType<typeof vi.fn>;
  vista?: PresupuestoAprobadoVista;
  documentos?: unknown[];
}) {
  apiFetchMock.mockImplementation((ruta: string) => {
    if (
      ruta ===
      `/gobierno/presupuesto/ejercicios/${detalle.id}/presupuesto-aprobado`
    ) {
      return Promise.resolve(vista);
    }
    if (ruta.includes("/documentos/por-recurso/GovernmentBudgetYear/")) {
      return Promise.resolve(documentos);
    }
    return Promise.reject(new Error(`No mock: ${ruta}`));
  });

  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <Routes>
          <Route
            path="/"
            element={
              <PresupuestoAprobadoEjercicio
                detalle={detalle}
                puedeGestionar={true}
                escribirBloque={escribirBloque}
                erroresServidor={{}}
              />
            }
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  apiFetchMock.mockReset();
  capacidades = new Set<string>();
});

describe("PresupuestoAprobadoEjercicio", () => {
  it("muestra montos, unidad y texto de cuadre", async () => {
    renderizar({});

    await waitFor(() => {
      expect(
        within(
          screen.getByRole("region", { name: "Tabla de ingresos estimados" }),
        ).getByText("1.000.000,00 VED"),
      ).toBeInTheDocument();
      expect(
        within(
          screen.getByRole("region", {
            name: "Tabla de créditos presupuestarios",
          }),
        ).getByText("600.000,00 VED"),
      ).toBeInTheDocument();
      expect(screen.getByText("DESP · Despacho")).toBeInTheDocument();
      expect(
        screen.getByText(
          "El presupuesto cuadra: los créditos no superan los ingresos estimados más la mitad de las existencias del Tesoro.",
        ),
      ).toBeInTheDocument();
    });
  });

  it("edita el monto de un crédito", async () => {
    const escribirBloque = vi.fn().mockResolvedValue(vistaBase);
    renderizar({ escribirBloque });

    const input = await screen.findByLabelText(
      "Nuevo monto del crédito 01.02 · 401.01 · F01",
    );
    await userEvent.clear(input);
    await userEvent.type(input, "650.000,00");
    await userEvent.click(
      screen.getByRole("button", {
        name: "Guardar crédito 01.02 · 401.01 · F01",
      }),
    );

    await waitFor(() => {
      expect(escribirBloque).toHaveBeenCalledWith(
        "/presupuesto-aprobado/creditos/cre1",
        "PATCH",
        { monto: "650000.00" },
      );
    });
  });

  it("registra crédito", async () => {
    const escribirBloque = vi.fn().mockResolvedValue(vistaBase);
    renderizar({ escribirBloque });

    await waitFor(() => {
      expect(screen.getByText("Créditos presupuestarios")).toBeInTheDocument();
    });

    const usuario = userEvent.setup();

    await usuario.selectOptions(
      screen.getByRole("combobox", {
        name: "Categoría programática (obligatorio)",
      }),
      "cat1",
    );
    await usuario.selectOptions(
      screen.getByRole("combobox", {
        name: "Fuente de financiamiento (obligatorio)",
      }),
      "fue2",
    );
    await usuario.selectOptions(
      screen.getByRole("combobox", { name: "Partida de egresos (obligatorio)" }),
      "peg2",
    );
    await usuario.type(
      screen.getByRole("textbox", { name: "Monto del crédito (obligatorio)" }),
      "1.200,50",
    );
    await usuario.click(screen.getByRole("button", { name: "Registrar crédito" }));

    await waitFor(() => {
      expect(escribirBloque).toHaveBeenCalledWith(
        "/presupuesto-aprobado/creditos",
        "POST",
        {
          categoria_id: "cat1",
          partida_id: "peg2",
          fuente_id: "fue2",
          monto: "1200.50",
        },
      );
    });
  });

  it("filtra partidas según restricción de fuente", async () => {
    renderizar({});

    await waitFor(() => {
      expect(screen.getByText("Créditos presupuestarios")).toBeInTheDocument();
    });

    const usuario = userEvent.setup();

    await usuario.selectOptions(
      screen.getByRole("combobox", {
        name: "Fuente de financiamiento (obligatorio)",
      }),
      "fue1",
    );

    await waitFor(() => {
      expect(
        screen.getByText(
          "La fuente F01 solo financia las partidas 401 (restricción de uso).",
        ),
      ).toBeInTheDocument();
    });

    const selectPartida = screen.getByRole("combobox", {
      name: "Partida de egresos (obligatorio)",
    });
    expect(selectPartida).toHaveTextContent("401.01");
    expect(selectPartida).not.toHaveTextContent("402");
  });

  it("no muestra formularios si está aprobado y congelado", async () => {
    const detalleAprobado: EjercicioDetalle = {
      ...detalleBase,
      estado: "APROBADO",
    };
    const vistaCongelada: PresupuestoAprobadoVista = {
      ...vistaBase,
      congelado: true,
    };
    renderizar({ detalle: detalleAprobado, vista: vistaCongelada });

    await waitFor(() => {
      expect(
        screen.getByText(
          "El presupuesto aprobado está fijado y ya no se modifica.",
        ),
      ).toBeInTheDocument();
    });

    expect(
      screen.queryByRole("button", { name: "Registrar crédito" }),
    ).not.toBeInTheDocument();
  });

  it("muestra no cuadra cuando totales.cuadra es false", async () => {
    const vistaNoCuadra: PresupuestoAprobadoVista = {
      ...vistaBase,
      totales: {
        ...vistaBase.totales,
        cuadra: false,
        diferencia: "-100000.00",
      },
    };
    renderizar({ vista: vistaNoCuadra });

    await waitFor(() => {
      expect(
        screen.getByText(
          "No cuadra: los créditos superan el disponible. El ejercicio no podrá aprobarse hasta corregirlo.",
        ),
      ).toBeInTheDocument();
    });
  });
});
