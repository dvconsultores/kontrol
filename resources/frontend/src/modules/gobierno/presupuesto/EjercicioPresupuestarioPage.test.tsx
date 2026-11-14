import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";

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

const { EjercicioPresupuestarioPage } = await import(
  "./EjercicioPresupuestarioPage"
);

const detalleBase = {
  id: "e1",
  anio: 2027,
  moneda_funcional: "VED",
  estado: "BORRADOR",
  version: 3,
  congelado: false,
  reconduccion_definitiva: false,
  precompromiso_activo: false,
  precompromiso_desde: null,
  niveles: [
    { orden: 1, nombre: "Programa" },
    { orden: 2, nombre: "Proyecto" },
  ],
  categorias: [
    {
      id: "cat1",
      nivel_orden: 1,
      nivel_nombre: "Programa",
      parent_id: null,
      codigo: "P1",
      codigo_completo: "P1",
      denominacion: "Salud",
    },
  ],
  clasificador: {
    edicion: "2027",
    fecha_edicion: "2027-01-10",
    procedencia: "Contraloría Municipal",
    documento_id: null,
    documento_sha256: "ab12cd34ef56ab12cd34ef56ab12cd34ef56ab12",
    partidas_recurso: 0,
    partidas_egreso: 0,
  },
  fundamentos: [],
  faltantes: [],
  historia: [
    {
      tipo: "CREADO",
      detalle: null,
      registrado_por: "ua",
      registrado_en: "2027-01-05T12:00:00Z",
    },
  ],
  fijado_en: null,
  cerrado_en: null,
  motivo_cierre: null,
} as const;

function renderizar() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter
        initialEntries={["/gobierno/presupuesto/ejercicios/e1"]}
      >
        <Routes>
          <Route
            path="/gobierno/presupuesto/ejercicios/:ejercicioId"
            element={<EjercicioPresupuestarioPage />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function responderConDetalle(detalle: unknown) {
  apiFetchMock.mockImplementation(async (ruta: string) => {
    if (ruta === "/gobierno/presupuesto/ejercicios/e1") {
      return detalle;
    }
    if (ruta === "/gobierno/presupuesto/ejercicios/e1/plan") {
      return {
        version: 3,
        congelado: false,
        plan: null,
        objetivos: [],
        vinculos: [],
        metas: [],
        unidades_disponibles: [],
        estructura_organizativa: null,
      };
    }
    if (ruta === "/gobierno/presupuesto/ejercicios/e1/fuentes") {
      return {
        version: 3,
        congelado: false,
        items: [],
      };
    }
    if (ruta.includes("/clasificador/partidas")) {
      return { items: [], total: 0 };
    }
    if (ruta.startsWith("/documentos/por-recurso/")) {
      return [];
    }
    return detalle;
  });
}

beforeEach(() => {
  apiFetchMock.mockReset();
  capacidades = new Set<string>();
});

describe("EjercicioPresupuestarioPage", () => {
  it("muestra la cabecera, la estructura y el clasificador sin la palabra «oficial»", async () => {
    responderConDetalle(detalleBase);

    renderizar();

    expect(
      await screen.findByText("Ejercicio presupuestario 2027"),
    ).toBeInTheDocument();
    expect(screen.getByText("Estructura programática")).toBeInTheDocument();
    expect(
      screen.getByText("Clasificador registrado por el ente"),
    ).toBeInTheDocument();
    expect(document.body.textContent).not.toContain("oficial");
  });

  it("con gobierno_presupuesto:manage muestra «Agregar categoría» y la agrega con ifMatch", async () => {
    capacidades = new Set(["gobierno_presupuesto:manage"]);
    responderConDetalle(detalleBase);

    const usuario = userEvent.setup();
    renderizar();

    const botonAgregar = await screen.findByRole("button", {
      name: "Agregar categoría",
    });
    expect(botonAgregar).toBeInTheDocument();
    const seccionEstructura = screen
      .getByRole("heading", { name: "Estructura programática" })
      .closest("section")!;
    const estructura = within(seccionEstructura);

    await usuario.selectOptions(
      estructura.getByRole("combobox", { name: "Nivel" }),
      estructura.getByRole("option", { name: "1. Programa" }),
    );
    await usuario.type(estructura.getByLabelText("Código"), "P2");
    await usuario.type(estructura.getByLabelText("Denominación"), "Educación");
    await usuario.click(botonAgregar);

    await waitFor(() => {
      const llamada = apiFetchMock.mock.calls.find(([ruta]) =>
        String(ruta).endsWith("/e1/categorias"),
      );
      expect(llamada).toBeDefined();
      expect(llamada?.[0]).toBe(
        "/gobierno/presupuesto/ejercicios/e1/categorias",
      );
      expect(llamada?.[1]).toMatchObject({
        method: "POST",
        ifMatch: "3",
        body: expect.objectContaining({ codigo: "P2" }),
      });
    });
  });

  it("con approve, elegir reconducción cambia etiqueta y botón", async () => {
    capacidades = new Set(["gobierno_presupuesto:approve"]);
    responderConDetalle(detalleBase);

    const usuario = userEvent.setup();
    renderizar();

    const radioReconduccion = await screen.findByRole("radio", {
      name: /Reconducción del presupuesto anterior/,
    });
    await usuario.click(radioReconduccion);

    expect(
      screen.getByText("Fecha de publicación del reconducido"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Reconducir ejercicio" }),
    ).toBeInTheDocument();
  });

  it("con detalle APROBADO muestra congelación y no muestra «Agregar categoría»", async () => {
    const detalleAprobado = {
      ...detalleBase,
      estado: "APROBADO",
      congelado: true,
      precompromiso_activo: true,
      precompromiso_desde: "2027-01-15",
    };
    responderConDetalle(detalleAprobado);

    renderizar();

    expect(
      await screen.findByText(/El ejercicio está fijado/),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Agregar categoría" }),
    ).not.toBeInTheDocument();
  });

  it("con 409 GOV_BUDGET_YEAR_STALE al agregar muestra el aviso de cambio", async () => {
    capacidades = new Set(["gobierno_presupuesto:manage"]);
    let primera = true;
    apiFetchMock.mockImplementation(async (ruta: string) => {
      if (ruta === "/gobierno/presupuesto/ejercicios/e1") {
        return detalleBase;
      }
      if (ruta === "/gobierno/presupuesto/ejercicios/e1/plan") {
        return {
          version: 3,
          congelado: false,
          plan: null,
          objetivos: [],
          vinculos: [],
          metas: [],
          unidades_disponibles: [],
          estructura_organizativa: null,
        };
      }
      if (ruta === "/gobierno/presupuesto/ejercicios/e1/fuentes") {
        return {
          version: 3,
          congelado: false,
          items: [],
        };
      }
      if (ruta.endsWith("/e1/categorias")) {
        if (primera) {
          primera = false;
          throw new ApiError(409, {
            code: "GOV_BUDGET_YEAR_STALE",
            message: "Cambio",
          });
        }
        return detalleBase;
      }
      if (ruta.includes("/clasificador/partidas")) {
        return { items: [], total: 0 };
      }
      if (ruta.startsWith("/documentos/por-recurso/")) {
        return [];
      }
      return detalleBase;
    });

    const usuario = userEvent.setup();
    renderizar();

    const botonAgregar = await screen.findByRole("button", {
      name: "Agregar categoría",
    });
    const seccionEstructura = screen
      .getByRole("heading", { name: "Estructura programática" })
      .closest("section")!;
    const estructura = within(seccionEstructura);
    await usuario.selectOptions(
      estructura.getByRole("combobox", { name: "Nivel" }),
      estructura.getByRole("option", { name: "1. Programa" }),
    );
    await usuario.type(estructura.getByLabelText("Código"), "P2");
    await usuario.type(estructura.getByLabelText("Denominación"), "Educación");
    await usuario.click(botonAgregar);

    expect(
      await screen.findByText(/El ejercicio cambió desde que lo abrió/),
    ).toBeInTheDocument();
  });
});
