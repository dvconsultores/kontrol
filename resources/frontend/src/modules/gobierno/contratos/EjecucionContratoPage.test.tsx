import { beforeEach, describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ApiError } from "@/api/client";
import { EjecucionContratoPage } from "./EjecucionContratoPage";
import type { EjecucionContrato, OpcionesEjecucion } from "./api";

const apiFetchMock = vi.fn();

vi.mock("@/api/client", async (original) => {
  const actual = await original<typeof import("@/api/client")>();
  return {
    ...actual,
    apiFetch: (...args: unknown[]) => apiFetchMock(...args),
    ApiError: actual.ApiError,
  };
});

vi.mock("@/api/descargas", () => ({
  descargarArchivo: vi.fn().mockResolvedValue("ok"),
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
    activeCompany: { id: "c1", legal_name: "Ente 1" },
  }),
}));

const documentos = [
  { id: "doc-inicio", titulo: "Acta de inicio", version: "1" },
  { id: "doc-soporte", titulo: "Soporte de valuación", version: "1" },
];

const opciones: OpcionesEjecucion = {
  hoy: "2026-11-15",
  documentos,
  representantes: [{ id: "rep-1", codigo: "R-001", nombre: "Representante Uno" }],
};

function ejecucion(parcial: Partial<EjecucionContrato> = {}): EjecucionContrato {
  return {
    contrato: {
      id: "k1",
      codigo: "CTR-2026-001",
      objeto: "Obra de ejemplo",
      contratista: "Contratista S.A.",
      estado: "FORMALIZADO",
      tipo_contratacion: "OBRA",
      flujo: "OBRAS",
      moneda: "USD",
      expediente_id: "exp-1",
    },
    terminos: {
      monto_original: "100000.00",
      monto_efectivo: "100000.00",
      moneda: "USD",
      fecha_inicio: "2026-10-01",
      fecha_fin: "2026-12-31",
      fuente: "Contrato",
    },
    resumen: {
      estado_ejecucion: "EN_EJECUCION",
      estado_etiqueta: "En ejecución",
      valuado_conformado: "50000.00",
      valuado_presentado: "0.00",
      saldo: "50000.00 USD",
      facturado: "0.00",
      hitos_total: 1,
      hitos_cumplidos: 0,
      entregables_pendientes: 0,
      supervisor: {
        asignacion_id: "a1",
        referencia: "SUP-001",
        nombre: "Supervisor Uno",
        cargo: "Jefe de Obra",
      },
    },
    inicio: null,
    terminacion: null,
    cierre: null,
    hitos: [],
    entregables: [],
    valuaciones: [],
    recepciones: [],
    facturas: [],
    cronologia: [],
    acciones: {
      iniciar: true,
      registrar: true,
      registrar_hechos: true,
      terminar: true,
      recepcion_parcial: true,
      recepcion_provisional: true,
      recepcion_definitiva: true,
      cerrar: true,
    },
    soy_supervisor: true,
    ...parcial,
  };
}

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/gobierno/contratos/k1/ejecucion"]}>
        <Routes>
          <Route path="/gobierno/contratos/:contratoId/ejecucion" element={<EjecucionContratoPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );

  return queryClient;
}

function mockRutas(base: EjecucionContrato) {
  apiFetchMock.mockImplementation((ruta: string, init?: { method?: string; body?: unknown }) => {
    const url = String(ruta);
    if (url.endsWith("/opciones") && url.includes("/ejecucion/opciones")) {
      return Promise.resolve(opciones);
    }
    if (url.includes("/ejecucion/inicio") && init?.method === "POST") {
      return Promise.resolve(base);
    }
    if (url.includes("/ejecucion/valuaciones") && init?.method === "POST") {
      return Promise.resolve(base);
    }
    if (url.includes("/ejecucion") && url.endsWith("/ejecucion")) {
      return Promise.resolve(base);
    }
    return Promise.reject(new Error(`Ruta no mockeada: ${url}`));
  });
}

describe("EjecucionContratoPage", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    capacidades = new Set(["gobierno_contratos:view", "gobierno_contratos:execute"]);
    apiFetchMock.mockImplementation((ruta: string) => {
      const url = String(ruta);
      if (url.endsWith("/opciones")) {
        return Promise.resolve(opciones);
      }
      if (url.endsWith("/ejecucion")) {
        return Promise.resolve(ejecucion());
      }
      return Promise.reject(new Error(`Ruta no mockeada: ${url}`));
    });
  });

  it("a. sin capacidad view muestra Sin acceso", async () => {
    capacidades = new Set();
    renderPage();
    expect(await screen.findByText("Sin acceso")).toBeTruthy();
  });

  it("b. con view y execute, soy_supervisor true: resumen, saldo y registro de inicio", async () => {
    const base = ejecucion();
    mockRutas(base);
    renderPage();

    expect(await screen.findByRole("heading", { name: "Resumen de la ejecución" })).toBeTruthy();
    expect(screen.getByText("50000.00 USD")).toBeTruthy();

    const select = await screen.findByLabelText(/^Acta de inicio/);
    fireEvent.change(select, { target: { value: "doc-inicio" } });

    fireEvent.click(screen.getByRole("button", { name: "Registrar inicio" }));
    fireEvent.click(await screen.findByRole("button", { name: "Confirmar" }));

    await waitFor(() => {
      expect(
        apiFetchMock.mock.calls.some(
          ([ruta, init]) =>
            String(ruta).endsWith("/ejecucion/inicio") &&
            (init as { method?: string }).method === "POST",
        ),
      ).toBe(true);
    });

    expect(await screen.findByText("Inicio de la ejecución registrado.")).toBeTruthy();
  });

  it("c. soy_supervisor false: botón de inicio deshabilitado y aviso visible", async () => {
    const base = ejecucion({ soy_supervisor: false });
    mockRutas(base);
    renderPage();

    expect(await screen.findByText("Solo el supervisor del contrato puede registrar el inicio.")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Registrar inicio" }).getAttribute("disabled")).toBeDefined();
  });

  it("d. error de API al presentar valuación muestra alerta", async () => {
    const base = ejecucion({
      inicio: {
        id: "ini-1",
        fecha: "2026-10-01",
        observacion: null,
        supervisor: "Supervisor Uno",
        documento: { id: "doc-inicio", titulo: "Acta de inicio" },
      },
      hitos: [
        {
          id: "h1",
          referencia: "H-001",
          descripcion: "Hito 1",
          fecha_prevista: "2026-11-01",
          monto_previsto: "100000.00",
          porcentaje_previsto: null,
          obligatorio: true,
          estado: "VIGENTE",
          cumplido: false,
          recepcion: null,
          valuado_conformado: "0.00",
          facturado: "0.00",
          motivo_anulacion: null,
        },
      ],
      acciones: {
        iniciar: true,
        registrar: true,
        registrar_hechos: true,
        terminar: true,
        recepcion_parcial: true,
        recepcion_provisional: true,
        recepcion_definitiva: true,
        cerrar: true,
      },
    });

    apiFetchMock.mockImplementation((ruta: string, init?: { method?: string }) => {
      const url = String(ruta);
      if (url.endsWith("/opciones")) {
        return Promise.resolve(opciones);
      }
      if (url.endsWith("/ejecucion")) {
        return Promise.resolve(base);
      }
      if (url.includes("/ejecucion/valuaciones") && init?.method === "POST") {
        return Promise.reject(
          new ApiError(422, {
            code: "GOV_CONTRACT_EXEC_VALUATION_EXCEEDS_CONTRACT",
            message: "La valuación supera el saldo del contrato",
          }),
        );
      }
      return Promise.reject(new Error(`Ruta no mockeada: ${url}`));
    });

    renderPage();

    await screen.findByRole("heading", { name: "Valuaciones" });

    const hitoSelect = document.getElementById("valuacion-hito") as HTMLSelectElement;
    fireEvent.change(hitoSelect, { target: { value: "h1" } });

    fireEvent.change(document.getElementById("valuacion-desde") as HTMLInputElement, {
      target: { value: "2026-11-01" },
    });
    fireEvent.change(document.getElementById("valuacion-hasta") as HTMLInputElement, {
      target: { value: "2026-11-15" },
    });
    fireEvent.change(document.getElementById("valuacion-fecha") as HTMLInputElement, {
      target: { value: "2026-11-15" },
    });
    fireEvent.change(document.getElementById("valuacion-monto") as HTMLInputElement, {
      target: { value: "60000.00" },
    });

    const soporteSelect = document.getElementById("valuacion-soporte") as HTMLSelectElement;
    fireEvent.change(soporteSelect, { target: { value: "doc-soporte" } });

    fireEvent.click(screen.getByRole("button", { name: "Presentar valuación" }));
    fireEvent.click(await screen.findByRole("button", { name: "Confirmar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "La valuación supera el saldo del contrato",
    );
  });

  it("e. contrato no FORMALIZADO muestra Contrato no formalizado", async () => {
    const base = ejecucion({ contrato: { ...ejecucion().contrato, estado: "BORRADOR" } });
    mockRutas(base);
    renderPage();

    expect(await screen.findByText("Contrato no formalizado")).toBeTruthy();
  });
});
