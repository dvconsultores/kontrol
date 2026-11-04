import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";
import type { HallazgoDetalle } from "@/modules/gobierno/api";

const apiFetchMock = vi.fn();
const navigateMock = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}));

vi.mock("react-router", async (original) => ({
  ...(await original<typeof import("react-router")>()),
  useNavigate: () => navigateMock,
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
  AdjuntosPanel: () => <div data-testid="adjuntos-panel" />,
}));

const { PlanDeAccion } = await import("./PlanDeAccion");

const DETALLE_BASE: HallazgoDetalle = {
  id: "h1",
  codigo: "H-001",
  titulo: "Hallazgo de prueba",
  condicion: "Condición del hallazgo",
  criterio: "Criterio del hallazgo",
  causa: "Causa del hallazgo",
  efecto: "Efecto del hallazgo",
  riesgo: "MEDIO",
  origen: "MUESTRA",
  origen_descripcion: null,
  muestra: null,
  partidas: [],
  estado: "ABIERTO",
  version: 3,
  presentado_por: null,
  presentado_en: null,
  verificado_por: null,
  verificado_en: null,
  nota_verificacion: null,
  created_by: "Usuario A",
  created_at: "2026-02-15T10:30:00Z",
  recomendaciones: [
    {
      id: "r1",
      orden: 1,
      texto: "Recomendación número uno para pruebas",
      created_by: "Usuario A",
      created_at: "2026-02-15T10:30:00Z",
    },
  ],
  acciones: [
    {
      id: "a1",
      recomendacion_id: "r1",
      orden: 1,
      descripcion: "Acción correctiva número uno para pruebas",
      cargo_id: "cargo1",
      cargo_codigo: "C-01",
      cargo_denominacion: "Cargo Uno",
      unidad_id: "u1",
      unidad_nombre: "Unidad Uno",
      ejercicio: 2026,
      fecha_objetivo: "2025-12-31",
      porcentaje: 20,
      estado: "EN_CURSO",
      vencida: true,
      documentos: ["d1"],
      avances: [],
    },
  ],
  historia: [],
};

function renderPlanDeAccion(
  detalle: HallazgoDetalle = DETALLE_BASE,
  onActualizado: (detalle: HallazgoDetalle) => void = vi.fn(),
  onError: (e: unknown) => void = vi.fn(),
) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/gobierno/hallazgos/h1"]}>
        <PlanDeAccion
          hallazgo={detalle}
          onActualizado={onActualizado}
          onError={onError}
        />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  navigateMock.mockReset();
  apiFetchMock.mockReset();
  apiFetchMock.mockImplementation((url: string) => {
    if (url === "/gobierno/hallazgos/cargos-responsables") {
      return Promise.resolve({
        items: [
          {
            id: "cargo1",
            codigo: "C-01",
            denominacion: "Cargo Uno",
            unidad_nombre: "Unidad Uno",
            ejercicio: 2026,
          },
        ],
      });
    }
    return Promise.reject(
      new ApiError(500, { code: "INTERNAL", message: "Error" }),
    );
  });
  capacidades = new Set([
    "gobierno_hallazgos:manage",
    "gobierno_hallazgos:view",
  ]);
});

describe("PlanDeAccion", () => {
  it("PDA-01 · ABIERTO con manage: muestra «Recomendaciones» y «Plan de acción», y los formularios de añadir recomendación y acción", async () => {
    renderPlanDeAccion();

    expect(
      screen.getByRole("heading", { name: "Recomendaciones" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Plan de acción" }),
    ).toBeInTheDocument();

    expect(
      await screen.findByRole("button", { name: "Añadir recomendación" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Añadir acción correctiva" }),
    ).toBeInTheDocument();
  });

  it("PDA-02 · añadir recomendación hace POST /gobierno/hallazgos/{id}/recomendaciones con {texto} e ifMatch String(version) y llama a onActualizado con la respuesta", async () => {
    const respuesta: HallazgoDetalle = {
      ...DETALLE_BASE,
      version: 4,
      recomendaciones: [
        ...DETALLE_BASE.recomendaciones,
        {
          id: "r2",
          orden: 2,
          texto: "Segunda recomendación para pruebas",
          created_by: "Usuario A",
          created_at: "2026-02-15T11:00:00Z",
        },
      ],
    };
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/hallazgos/cargos-responsables") {
        return Promise.resolve({ items: [] });
      }
      if (url === "/gobierno/hallazgos/h1/recomendaciones") {
        return Promise.resolve(respuesta);
      }
      return Promise.reject(
        new ApiError(500, { code: "INTERNAL", message: "Error" }),
      );
    });
    const onActualizado = vi.fn();
    renderPlanDeAccion(DETALLE_BASE, onActualizado);

    const region = await screen.findByRole("region", { name: "Recomendaciones" });
    const textarea = await within(region).findByLabelText(/^Recomendación/);
    await userEvent.type(
      textarea,
      "Recomendación nueva de prueba con suficiente longitud",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Añadir recomendación" }),
    );

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/hallazgos/h1/recomendaciones",
        {
          method: "POST",
          body: {
            texto: "Recomendación nueva de prueba con suficiente longitud",
          },
          ifMatch: "3",
        },
      );
      expect(onActualizado).toHaveBeenCalledWith(respuesta);
    });
  });

  it("PDA-03 · acción vencida muestra el texto «Vencida»", async () => {
    renderPlanDeAccion();

    expect(
      await screen.findByText("Vencida", { exact: false }),
    ).toBeInTheDocument();
  });

  it("PDA-04a · EN_REMEDIACION con manage muestra el formulario «Registrar avance»", async () => {
    const detalleRemediacion: HallazgoDetalle = {
      ...DETALLE_BASE,
      estado: "EN_REMEDIACION",
    };
    renderPlanDeAccion(detalleRemediacion);

    expect(
      await screen.findByRole("button", { name: "Registrar avance" }),
    ).toBeInTheDocument();
  });

  it("PDA-04b · EN_REMEDIACION sin manage no muestra el formulario «Registrar avance»", async () => {
    capacidades = new Set(["gobierno_hallazgos:view"]);
    const detalleRemediacion: HallazgoDetalle = {
      ...DETALLE_BASE,
      estado: "EN_REMEDIACION",
    };
    renderPlanDeAccion(detalleRemediacion);

    await waitFor(() => {
      expect(
        screen.queryByRole("button", { name: "Registrar avance" }),
      ).not.toBeInTheDocument();
    });
  });

  it("PDA-05 · 409 GOV_FINDING_STALE llama a onError", async () => {
    apiFetchMock.mockImplementation((url: string) => {
      if (url === "/gobierno/hallazgos/cargos-responsables") {
        return Promise.resolve({ items: [] });
      }
      return Promise.reject(
        new ApiError(409, {
          code: "GOV_FINDING_STALE",
          message: "Versión obsoleta",
        }),
      );
    });
    const onError = vi.fn();
    renderPlanDeAccion(DETALLE_BASE, vi.fn(), onError);

    const region = await screen.findByRole("region", { name: "Recomendaciones" });
    const textarea = await within(region).findByLabelText(/^Recomendación/);
    await userEvent.type(
      textarea,
      "Recomendación nueva de prueba con suficiente longitud",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Añadir recomendación" }),
    );

    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith(
        expect.objectContaining({
          status: 409,
          code: "GOV_FINDING_STALE",
        }),
      );
    });
  });
});
