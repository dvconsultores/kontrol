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

const { FuentesEjercicio } = await import("./FuentesEjercicio");

import type { EjercicioDetalle, FuentesVista } from "./api";

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

const fuentesBase: FuentesVista = {
  version: 3,
  congelado: false,
  items: [
    {
      id: "f1",
      codigo: "F01",
      denominacion: "Tesoro municipal",
      procedencia: "Recaudación local",
      documento_id: null,
      documento_sha256: null,
      vigente_desde: "2027-01-01",
      vigente_hasta: null,
      restricciones: [
        {
          id: "r1",
          descripcion: "Solo gasto corriente",
          fundamento: "Manual de presupuesto",
          partidas: ["401", "402"],
        },
      ],
    },
  ],
};

function renderizar({
  detalle = detalleBase,
  escribirBloque = vi.fn(),
  fuentes = fuentesBase,
  documentos = [],
}: {
  detalle?: EjercicioDetalle;
  escribirBloque?: ReturnType<typeof vi.fn>;
  fuentes?: FuentesVista;
  documentos?: unknown[];
}) {
  apiFetchMock.mockImplementation((ruta: string) => {
    if (ruta === `/gobierno/presupuesto/ejercicios/${detalle.id}/fuentes`) {
      return Promise.resolve(fuentes);
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
              <FuentesEjercicio
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

describe("FuentesEjercicio", () => {
  it("lista F01 y su restricción", async () => {
    renderizar({});
    expect(await screen.findByText("F01")).toBeInTheDocument();
    expect(
      await screen.findByText(/Solo gasto corriente · Manual de presupuesto/),
    ).toBeInTheDocument();
  });

  it("crear fuente llama a escribirBloque con codigo F02", async () => {
    const escribirBloque = vi.fn().mockResolvedValue(fuentesBase);
    renderizar({ escribirBloque });

    const codigoInput = await screen.findByRole("textbox", { name: "Código (obligatorio)" });
    const denominacionInput = screen.getByRole("textbox", { name: "Denominación (obligatorio)" });
    const procedenciaInput = screen.getByRole("textbox", { name: "Procedencia (obligatorio)" });

    await userEvent.type(codigoInput, "F02");
    await userEvent.type(denominacionInput, "Ingresos corrientes");
    await userEvent.type(procedenciaInput, "Recaudación");

    const boton = screen.getByRole("button", { name: "Crear fuente" });
    await userEvent.click(boton);

    await waitFor(() => {
      expect(escribirBloque).toHaveBeenCalledWith(
        "/fuentes",
        "POST",
        expect.objectContaining({ codigo: "F02" }),
      );
    });
  });

  it("añadir restricción con 401, 402 envía partidas [\"401\",\"402\"]", async () => {
    const escribirBloque = vi.fn().mockResolvedValue(fuentesBase);
    renderizar({ escribirBloque });

    const descripcionInput = await screen.findByRole("textbox", {
      name: "Descripción de la restricción de F01 (obligatorio)",
    });
    const fundamentoInput = screen.getByRole("textbox", {
      name: "Fundamento de la restricción de F01 (obligatorio)",
    });
    const partidasInput = screen.getByRole("textbox", {
      name: "Partidas de egreso de F01",
    });

    await userEvent.type(descripcionInput, "Solo inversión");
    await userEvent.type(fundamentoInput, "Ley orgánica");
    await userEvent.type(partidasInput, "401, 402");

    const boton = screen.getByRole("button", {
      name: "Añadir restricción a F01",
    });
    await userEvent.click(boton);

    await waitFor(() => {
      expect(escribirBloque).toHaveBeenCalledWith(
        "/fuentes/f1/restricciones",
        "POST",
        expect.objectContaining({ partidas: ["401", "402"] }),
      );
    });
  });
});
