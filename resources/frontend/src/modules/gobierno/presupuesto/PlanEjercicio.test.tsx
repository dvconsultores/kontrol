import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
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

const { PlanEjercicio } = await import("./PlanEjercicio");

import type { EjercicioDetalle, PlanVista } from "./api";

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

const planConEstructura: PlanVista = {
  version: 3,
  congelado: false,
  plan: { denominacion: "Plan 2027", documento_id: null, documento_sha256: null },
  objetivos: [{ id: "o1", codigo: "OBJ-1", descripcion: "Primer objetivo" }],
  vinculos: [
    {
      categoria_id: "c1",
      codigo_completo: "01",
      denominacion: "Programa A",
      unidad: { id: "u1", codigo: "U1", nombre: "Unidad 1" },
      objetivo: { id: "o1", codigo: "OBJ-1" },
    },
  ],
  metas: [],
  unidades_disponibles: [
    { id: "u1", codigo: "U1", nombre: "Unidad 1" },
    { id: "u2", codigo: "U2", nombre: "Unidad 2" },
  ],
  estructura_organizativa: { estado: "VIGENTE" },
};

const planSinEstructura = {
  ...planConEstructura,
  estructura_organizativa: null,
};

function renderizar({
  detalle = detalleBase,
  escribirBloque = vi.fn(),
  plan = planConEstructura,
  documentos = [],
}: {
  detalle?: EjercicioDetalle;
  escribirBloque?: ReturnType<typeof vi.fn>;
  plan?: PlanVista | null;
  documentos?: unknown[];
}) {
  apiFetchMock.mockImplementation((ruta: string) => {
    if (ruta === `/gobierno/presupuesto/ejercicios/${detalle.id}/plan`) {
      return Promise.resolve(plan);
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
              <PlanEjercicio
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
  capacidades = new Set(["gobierno_presupuesto:manage"]);
});

describe("PlanEjercicio", () => {
  it("sin estructura vigente muestra el aviso", async () => {
    renderizar({ plan: planSinEstructura });
    expect(
      await screen.findByText(
        /No hay una estructura organizativa vigente para 2027/,
      ),
    ).toBeInTheDocument();
  });

  it("con manage, guardar el vínculo de 01 llama a escribirBloque", async () => {
    const escribirBloque = vi.fn().mockResolvedValue(planConEstructura);
    renderizar({ escribirBloque });

    const boton = await screen.findByRole("button", {
      name: "Guardar vínculo de 01",
    });
    await userEvent.click(boton);

    await waitFor(() => {
      expect(escribirBloque).toHaveBeenCalledWith(
        "/categorias/c1/vinculo",
        "PUT",
        { unidad_id: "u1", objetivo_id: "o1" },
      );
    });
  });

  it("detalle APROBADO no muestra «Nuevo objetivo»", async () => {
    renderizar({ detalle: { ...detalleBase, estado: "APROBADO" } });
    await screen.findByRole("heading", { name: "Plan operativo y metas" });
    expect(screen.queryByText("Nuevo objetivo")).not.toBeInTheDocument();
  });
});
