import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ContratoModificacionesPage } from "./ContratoModificacionesPage";
import type { FichaModificacion, HistoriaModificaciones, NodoModificacion } from "./api";

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

function nodo(over: Partial<NodoModificacion> = {}): NodoModificacion {
  return {
    id: "m1",
    codigo: "CT-2026-0001/AD-001",
    numero: 1,
    tipo: "ADENDA",
    tipo_etiqueta: "Adenda",
    fecha_instrumento: "2026-11-14",
    vigente_desde: "2026-11-14",
    motivo: "Más alcance",
    plazo: null,
    monto: { anterior: "50000.00", delta: "10000.00", nuevo: "60000.00" },
    condiciones: null,
    firmante: { cargo: "Director General", funcionario: null },
    documento: { titulo: "Documento", version: 1, sha256: "abc123" },
    huella: "huella-m1",
    formalizado_en: "2026-11-14T10:00:00Z",
    cobertura_adicional: [],
    ...over,
  };
}

function historia(over: Partial<HistoriaModificaciones> = {}): HistoriaModificaciones {
  return {
    contrato: {
      id: "k1",
      codigo: "CT-2026-0001",
      identificacion: "CT-2026-0001",
      tipo_etiqueta: "Contrato",
      estado: "VIGENTE",
      contratista_nombre: "Constructora Andina",
      objeto: "Construcción",
      moneda: "USD",
    },
    original: {
      monto: "50000.00",
      moneda: "USD",
      fecha_inicio: "2026-05-14",
      fecha_fin: "2027-05-14",
      huella: "huella-original",
    },
    vigente: {
      fecha: "2026-11-14",
      monto: "60000.00",
      fecha_fin: "2027-05-14",
      modificacion_codigo: "CT-2026-0001/AD-001",
      programadas: [],
    },
    ultima: {
      monto: "60000.00",
      fecha_fin: "2027-05-14",
      vigente_desde: "2026-11-14",
      modificacion_codigo: "CT-2026-0001/AD-001",
    },
    historial: [nodo()],
    borrador: null,
    puede_crear: true,
    motivo_no_crear: null,
    ...over,
  };
}

function ficha(over: Partial<FichaModificacion> = {}): FichaModificacion {
  return {
    id: "m2",
    version: 1,
    estado: "BORRADOR",
    estado_etiqueta: "Borrador",
    tipo: "PRORROGA",
    tipo_etiqueta: "Prórroga",
    codigo: null,
    identificacion: "m2",
    contrato: { id: "k1", codigo: "CT-2026-0001" },
    moneda: "USD",
    fecha_instrumento: null,
    vigente_desde: null,
    motivo: null,
    nueva_fecha_fin: null,
    delta_monto: null,
    condiciones: null,
    referencia_instrumento: null,
    documento: null,
    base: { monto: "60000.00", fecha_fin: "2027-05-14", numero: 1 },
    propuesta: { monto_nuevo: null, fecha_fin_nueva: null },
    cobertura: {
      existente_valida: "0.00",
      requerida_adicional: "0.00",
      asignaciones: [],
      total_asignado: "0.00",
      completa: false,
    },
    compromisos: { total: null, moneda: null, permite: true, aplica: false },
    firmante: null,
    formalizado_en: null,
    huella: null,
    opciones: null,
    pendientes: [],
    puede_formalizar: false,
    ...over,
  };
}

function renderizar() {
  const cliente = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={cliente}>
      <MemoryRouter initialEntries={["/gobierno/contratos/k1/modificaciones"]}>
        <Routes>
          <Route path="/gobierno/contratos/:contratoId/modificaciones" element={<ContratoModificacionesPage />} />
          <Route
            path="/gobierno/contratos/:contratoId/modificaciones/:modificacionId"
            element={<p>Ficha abierta</p>}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ContratoModificacionesPage", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    capacidades = new Set(["gobierno_contratos:view", "gobierno_contratos:manage"]);
  });

  it("muestra las condiciones originales, vigentes y el historial", async () => {
    apiFetchMock.mockResolvedValue(historia());
    renderizar();

    expect(await screen.findByText("Condiciones originales")).toBeInTheDocument();
    expect(screen.getByText("Condiciones vigentes al 14/11/2026")).toBeInTheDocument();

    const original = screen.getByRole("heading", { name: "Condiciones originales" }).closest("section");
    expect(original).not.toBeNull();
    expect(within(original as HTMLElement).getByText("50000.00 USD")).toBeInTheDocument();

    const vigentes = screen.getByRole("heading", { name: "Condiciones vigentes al 14/11/2026" }).closest("section");
    expect(vigentes).not.toBeNull();
    expect(within(vigentes as HTMLElement).getByText("60000.00 USD")).toBeInTheDocument();

    expect(screen.getByText("Contrato original")).toBeInTheDocument();
    expect(screen.getByText("CT-2026-0001/AD-001")).toBeInTheDocument();
    expect(screen.queryByText("m1")).toBeNull();
  });

  it("crea una modificación de tipo prórroga y navega a la ficha", async () => {
    apiFetchMock.mockImplementation((ruta: string, opciones?: { method?: string; body?: unknown }) => {
      if (ruta === "/gobierno/contratos/k1/modificaciones" && opciones?.method === "POST") {
        return Promise.resolve(ficha({ id: "m2", tipo: "PRORROGA", tipo_etiqueta: "Prórroga" }));
      }
      return Promise.resolve(historia());
    });
    renderizar();

    await screen.findByRole("button", { name: "Nueva modificación" });
    await userEvent.selectOptions(screen.getByLabelText("Tipo de modificación"), "PRORROGA");
    await userEvent.click(screen.getByRole("button", { name: "Nueva modificación" }));

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith("/gobierno/contratos/k1/modificaciones", {
        method: "POST",
        body: { tipo: "PRORROGA" },
      });
    });
    expect(await screen.findByText("Ficha abierta")).toBeInTheDocument();
  });

  it("muestra el enlace para continuar un borrador existente", async () => {
    apiFetchMock.mockResolvedValue(
      historia({
        borrador: { id: "m3", tipo: "ADENDA", tipo_etiqueta: "Adenda" },
        puede_crear: false,
      }),
    );
    renderizar();

    expect(
      await screen.findByRole("link", { name: "Continuar el borrador (Adenda)" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Nueva modificación" })).toBeNull();
  });

  it("no muestra la sección de nueva modificación sin permiso de gestión", async () => {
    capacidades = new Set(["gobierno_contratos:view"]);
    apiFetchMock.mockResolvedValue(historia());
    renderizar();

    await screen.findByText("Condiciones originales");
    expect(screen.queryByRole("button", { name: "Nueva modificación" })).toBeNull();
  });
});
