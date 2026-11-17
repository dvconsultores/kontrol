import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/api/client";
import { CausadoPage } from "./CausadoPage";
import type { Causado } from "./api";

const apiFetchMock = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
  ApiError: (await original<typeof import("@/api/client")>()).ApiError,
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
  useCompany: () => ({ activeCompanyId: "c1", activeCompany: { id: "c1", legal_name: "Ente 1" } }),
}));

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify: vi.fn() }),
}));

function crearCausado(partial: Partial<Causado> = {}): Causado {
  return {
    id: "c1",
    codigo: null,
    numero: null,
    estado: "BORRADOR",
    version: 3,
    year_id: "y1",
    anio: "2026",
    compromiso: {
      id: "k1",
      codigo: "COM-2026-001",
      concepto: "Mantenimiento de equipos",
      total: "100.00",
      causado: "0.00",
      pendiente: "100.00",
    },
    politica: {
      id: "p1",
      codigo: "POL-CAU-001",
      nombre: "Política de servicios",
      tipo_gasto: "Servicios",
      disparador: "DOCUMENTARY",
      version: 1,
    },
    fecha_efectiva: "2026-02-10",
    registrado_en: "2026-02-10T10:00:00Z",
    moneda: "VES",
    monto: "40.00",
    concepto: "Mantenimiento preventivo de equipos",
    beneficiario: "Proveedor Uno",
    fuente_tipo: null,
    fuente_id: null,
    autoridad_cargo_id: null,
    autoridad: null,
    lineas: [
      {
        id: "lc1",
        linea_compromiso_id: "l1",
        linea: "Línea 1",
        partida: "4.02.01.01.001",
        categoria: "Servicios",
        comprometido: "100.00",
        causado_otros: "0.00",
        monto: "40.00",
        pendiente_tras: "60.00",
      },
    ],
    evidencias: [],
    formalizado_en: null,
    formalizado_por: null,
    anulado_en: null,
    motivo_anulacion: null,
    huella: null,
    monto_ordenado: "0.00",
    pendiente_de_ordenar: "40.00",
    controles: [],
    historia: [],
    ...partial,
  };
}

function renderPagina() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/gobierno/presupuesto/causados/c1"]}>
        <Routes>
          <Route path="/gobierno/presupuesto/causados/:causadoId" element={<CausadoPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return queryClient;
}

beforeEach(() => {
  apiFetchMock.mockReset();
  capacidades = new Set(["gobierno_presupuesto:view", "gobierno_presupuesto:cause"]);
});

describe("CausadoPage", () => {
  it("formaliza un borrador", async () => {
    const usuario = userEvent.setup();
    apiFetchMock.mockImplementation(async (ruta: string, opciones?: { method?: string; ifMatch?: string }) => {
      if (ruta === "/gobierno/presupuesto/causados/c1") {
        return crearCausado({ controles: [{ codigo: "CONTROL_OK", cumplido: true, mensaje: "Cumple" }] });
      }
      if (ruta === "/gobierno/presupuesto/causados/c1/formalizar" && opciones?.method === "POST") {
        return crearCausado({ estado: "FORMALIZADO", codigo: "CAU-2026-001" });
      }
      throw new Error(`Ruta no esperada: ${ruta}`);
    });

    renderPagina();
    await usuario.click(await screen.findByRole("button", { name: "Formalizar" }));

    const dialogo = await screen.findByRole("dialog");
    await usuario.click(within(dialogo).getByRole("button", { name: "Formalizar" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/presupuesto/causados/c1/formalizar",
        { method: "POST", ifMatch: "3" },
      );
    });
  });

  it("muestra controles pendientes y mensaje de requisitos", async () => {
    apiFetchMock.mockResolvedValue(
      crearCausado({
        controles: [
          { codigo: "EVIDENCIA_DISPARADOR", cumplido: false, mensaje: "Falta la recepción conforme" },
        ],
      }),
    );
    renderPagina();

    expect(await screen.findByText("✗ Pendiente · Falta la recepción conforme")).toBeInTheDocument();
    expect(screen.getByText(/Faltan requisitos/)).toBeInTheDocument();
  });

  it("muestra 409 al formalizar", async () => {
    const usuario = userEvent.setup();
    apiFetchMock.mockImplementation(async (ruta: string, opciones?: { method?: string }) => {
      if (ruta === "/gobierno/presupuesto/causados/c1") {
        return crearCausado({ controles: [{ codigo: "CONTROL_OK", cumplido: true, mensaje: "Cumple" }] });
      }
      if (ruta === "/gobierno/presupuesto/causados/c1/formalizar" && opciones?.method === "POST") {
        throw new ApiError(409, {
          code: "GOV_BUDGET_CAUSE_STALE",
          message: "El causado cambió",
        });
      }
      throw new Error(`Ruta no esperada: ${ruta}`);
    });

    renderPagina();
    await usuario.click(await screen.findByRole("button", { name: "Formalizar" }));
    const dialogo = await screen.findByRole("dialog");
    await usuario.click(within(dialogo).getByRole("button", { name: "Formalizar" }));

    expect(await screen.findByText("El causado cambió")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Recargar" })).toBeInTheDocument();
  });

  it("muestra 422 al formalizar", async () => {
    const usuario = userEvent.setup();
    apiFetchMock.mockImplementation(async (ruta: string, opciones?: { method?: string }) => {
      if (ruta === "/gobierno/presupuesto/causados/c1") {
        return crearCausado({ controles: [{ codigo: "CONTROL_OK", cumplido: true, mensaje: "Cumple" }] });
      }
      if (ruta === "/gobierno/presupuesto/causados/c1/formalizar" && opciones?.method === "POST") {
        throw new ApiError(422, {
          code: "GOV_BUDGET_CAUSE_OVER_COMMITMENT",
          message: "El monto supera el pendiente de la línea del compromiso",
        });
      }
      throw new Error(`Ruta no esperada: ${ruta}`);
    });

    renderPagina();
    await usuario.click(await screen.findByRole("button", { name: "Formalizar" }));
    const dialogo = await screen.findByRole("dialog");
    await usuario.click(within(dialogo).getByRole("button", { name: "Formalizar" }));

    expect(await screen.findByText("El monto supera el pendiente de la línea del compromiso")).toBeInTheDocument();
  });

  it("valida el motivo y anula un formalizado", async () => {
    const usuario = userEvent.setup();
    apiFetchMock.mockImplementation(async (ruta: string, opciones?: { method?: string; ifMatch?: string; body?: unknown }) => {
      if (ruta === "/gobierno/presupuesto/causados/c1") {
        return crearCausado({ estado: "FORMALIZADO", codigo: "CAU-2026-001" });
      }
      if (ruta === "/gobierno/presupuesto/causados/c1/anular" && opciones?.method === "POST") {
        return crearCausado({ estado: "ANULADO", codigo: "CAU-2026-001", motivo_anulacion: "Motivo válido de anulación" });
      }
      throw new Error(`Ruta no esperada: ${ruta}`);
    });

    renderPagina();
    await usuario.click(await screen.findByRole("button", { name: "Anular" }));

    const dialogo = await screen.findByRole("dialog");
    await usuario.type(within(dialogo).getByLabelText("Motivo"), "corto");
    await usuario.click(within(dialogo).getByRole("button", { name: "Anular" }));

    expect(await screen.findByText("El motivo debe tener al menos 10 caracteres")).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalledWith(
      "/gobierno/presupuesto/causados/c1/anular",
      expect.anything(),
    );

    await usuario.clear(within(dialogo).getByLabelText("Motivo"));
    await usuario.type(within(dialogo).getByLabelText("Motivo"), "Motivo válido de anulación");
    await usuario.click(within(dialogo).getByRole("button", { name: "Anular" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/presupuesto/causados/c1/anular",
        expect.objectContaining({
          method: "POST",
          ifMatch: "3",
          body: { motivo: "Motivo válido de anulación" },
        }),
      );
    });
  });

  it("muestra pendiente de orden de pago y 404", async () => {
    apiFetchMock.mockImplementation(async (ruta: string) => {
      if (ruta === "/gobierno/presupuesto/causados/c1") {
        return crearCausado({ estado: "FORMALIZADO", codigo: "CAU-2026-001", pendiente_de_ordenar: "15.00" });
      }
      throw new Error(`Ruta no esperada: ${ruta}`);
    });
    renderPagina();
    expect(await screen.findByText(/Pendiente de orden de pago: 15.00 VES/)).toBeInTheDocument();
  });

  it("muestra no encontrado con error 404", async () => {
    apiFetchMock.mockImplementation(async () => {
      throw new ApiError(404, { message: "No existe" });
    });
    renderPagina();
    expect(await screen.findByText("Causado no encontrado")).toBeInTheDocument();
  });

  it("no muestra Formalizar sin capacidad cause", async () => {
    capacidades = new Set(["gobierno_presupuesto:view"]);
    apiFetchMock.mockResolvedValue(crearCausado());
    renderPagina();
    await screen.findByText("Mantenimiento preventivo de equipos");
    expect(screen.queryByRole("button", { name: "Formalizar" })).not.toBeInTheDocument();
  });
});
