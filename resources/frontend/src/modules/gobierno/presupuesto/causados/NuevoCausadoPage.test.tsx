import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/api/client";
import { NuevoCausadoPage } from "./NuevoCausadoPage";
import type { Causado, OpcionesCausado, PoliticaCausado } from "./api";

const apiFetchMock = vi.fn();

vi.mock("@/api/client", async (original) => ({
  ...(await original<typeof import("@/api/client")>()),
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
  ApiError: (await original<typeof import("@/api/client")>()).ApiError,
}));

vi.mock("@/modules/documentos/AdjuntosPanel", () => ({
  AdjuntosPanel: () => <div>adjuntos</div>,
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

function crearPolitica(partial: Partial<PoliticaCausado> = {}): PoliticaCausado {
  return {
    id: "p1",
    codigo: "POL-CAU-001",
    tipo_gasto: "Servicios",
    nombre: "Política de servicios",
    descripcion: null,
    disparador: "DOCUMENTARY",
    requiere_recepcion: false,
    requiere_valuacion: false,
    requiere_conformidad: false,
    competencia_accion: "CAUSAR",
    competencia_materia: "PRESUPUESTO",
    vigente_desde: "2026-01-01",
    vigente_hasta: null,
    fundamento: null,
    act_id: null,
    acto: null,
    tipo_regla: "INSTITUTIONAL_POLICY",
    estado: "VIGENTE",
    version: 1,
    activada_en: null,
    cerrada_en: null,
    motivo_cierre: null,
    documentos: [],
    ...partial,
  };
}

function crearOpciones(partial: Partial<OpcionesCausado> = {}): OpcionesCausado {
  return {
    anio: "2026",
    moneda: "VES",
    compromisos: [
      {
        id: "k1",
        codigo: "COM-2026-001",
        concepto: "Mantenimiento de equipos",
        fecha: "2026-01-05",
        moneda: "VES",
        total: "100.00",
        causado: "0.00",
        pendiente: "100.00",
        lineas: [
          {
            id: "l1",
            linea: "Línea 1",
            partida: "4.02.01.01.001",
            categoria: "Servicios",
            unidad: "Operaciones",
            comprometido: "100.00",
            causado: "0.00",
            pendiente: "100.00",
          },
        ],
      },
    ],
    politicas: [crearPolitica()],
    cargos: [{ id: "cargo1", etiqueta: "Director de Administración", competencias: [] }],
    evidencias: [
      {
        tipo: "CONTRACT_RECEIPT",
        id: "r1",
        etiqueta: "Recepción conforme",
        estado: "APROBADA",
        fecha: "2026-02-01",
        valida: true,
      },
    ],
    documentos: [],
    ...partial,
  };
}

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
    evidencias: [
      {
        id: "e1",
        tipo: "CONTRACT_RECEIPT",
        recurso_id: "r1",
        etiqueta: "Recepción conforme",
        estado: "APROBADA",
        fecha: "2026-02-01",
        sha256: "abc123",
      },
    ],
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

function renderPagina(entrada: string) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[entrada]}>
        <Routes>
          <Route path="/gobierno/presupuesto/causados/nuevo" element={<NuevoCausadoPage />} />
          <Route path="/gobierno/presupuesto/causados/:causadoId/editar" element={<NuevoCausadoPage />} />
          <Route path="/gobierno/presupuesto/causados/:causadoId" element={<div>detalle</div>} />
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

describe("NuevoCausadoPage", () => {
  it("guarda un borrador y navega al detalle", async () => {
    const usuario = userEvent.setup();
    apiFetchMock.mockImplementation(async (ruta: string, opciones?: { method?: string; body?: unknown }) => {
      if (ruta.startsWith("/gobierno/presupuesto/ejercicios/y1/causados/opciones")) {
        return crearOpciones();
      }
      if (ruta === "/gobierno/presupuesto/ejercicios/y1/causados" && opciones?.method === "POST") {
        return crearCausado();
      }
      throw new Error(`Ruta no esperada: ${ruta}`);
    });

    renderPagina("/gobierno/presupuesto/causados/nuevo?ejercicio=y1");

    await screen.findByRole("heading", { name: "Nuevo causado" });
    await usuario.selectOptions(screen.getByRole("combobox", { name: "Compromiso" }), "k1");
    await screen.findByLabelText("Monto a causar 4.02.01.01.001");
    await usuario.type(screen.getByLabelText("Monto a causar 4.02.01.01.001"), "40.00");
    await usuario.selectOptions(screen.getByLabelText("Política"), "p1");
    await usuario.type(screen.getByRole("textbox", { name: "Concepto (obligatorio)" }), "Mantenimiento preventivo de equipos");
    await usuario.click(screen.getByRole("checkbox", { name: /Recepción conforme/ }));
    await usuario.click(screen.getByRole("button", { name: "Guardar borrador" }));

    await waitFor(() => expect(screen.getByText("detalle")).toBeInTheDocument());

    expect(apiFetchMock).toHaveBeenCalledWith(
      "/gobierno/presupuesto/ejercicios/y1/causados",
      expect.objectContaining({
        method: "POST",
        body: expect.objectContaining({
          lineas: [{ linea_compromiso_id: "l1", monto: "40.00" }],
          evidencias: [{ tipo: "CONTRACT_RECEIPT", id: "r1" }],
        }),
      }),
    );
  });

  it("muestra el pendiente tras este causado correctamente", async () => {
    const usuario = userEvent.setup();
    apiFetchMock.mockImplementation(async (ruta: string) => {
      if (ruta.startsWith("/gobierno/presupuesto/ejercicios/y1/causados/opciones")) {
        return crearOpciones();
      }
      throw new Error(`Ruta no esperada: ${ruta}`);
    });
    renderPagina("/gobierno/presupuesto/causados/nuevo?ejercicio=y1");
    await screen.findByRole("heading", { name: "Nuevo causado" });
    await usuario.selectOptions(screen.getByRole("combobox", { name: "Compromiso" }), "k1");
    await usuario.type(await screen.findByLabelText("Monto a causar 4.02.01.01.001"), "40.00");
    expect(screen.getByText("60.00")).toBeInTheDocument();
  });

  it("deshabilita Guardar con concepto corto", async () => {
    const usuario = userEvent.setup();
    apiFetchMock.mockImplementation(async (ruta: string) => {
      if (ruta.startsWith("/gobierno/presupuesto/ejercicios/y1/causados/opciones")) {
        return crearOpciones();
      }
      throw new Error(`Ruta no esperada: ${ruta}`);
    });
    renderPagina("/gobierno/presupuesto/causados/nuevo?ejercicio=y1");
    await screen.findByRole("heading", { name: "Nuevo causado" });
    await usuario.selectOptions(screen.getByRole("combobox", { name: "Compromiso" }), "k1");
    await usuario.type(await screen.findByLabelText("Monto a causar 4.02.01.01.001"), "40.00");
    await usuario.selectOptions(screen.getByLabelText("Política"), "p1");
    await usuario.type(screen.getByRole("textbox", { name: "Concepto (obligatorio)" }), "corto");
    expect(screen.getByRole("button", { name: "Guardar borrador" })).toBeDisabled();
  });

  it("avisa cuando el monto supera el pendiente y deshabilita Guardar", async () => {
    const usuario = userEvent.setup();
    apiFetchMock.mockImplementation(async (ruta: string) => {
      if (ruta.startsWith("/gobierno/presupuesto/ejercicios/y1/causados/opciones")) {
        return crearOpciones();
      }
      throw new Error(`Ruta no esperada: ${ruta}`);
    });
    renderPagina("/gobierno/presupuesto/causados/nuevo?ejercicio=y1");
    await screen.findByRole("heading", { name: "Nuevo causado" });
    await usuario.selectOptions(screen.getByRole("combobox", { name: "Compromiso" }), "k1");
    await usuario.type(await screen.findByLabelText("Monto a causar 4.02.01.01.001"), "150.00");
    await usuario.selectOptions(screen.getByLabelText("Política"), "p1");
    await usuario.type(screen.getByRole("textbox", { name: "Concepto (obligatorio)" }), "Mantenimiento preventivo de equipos");
    expect(screen.getByText("Supera el pendiente de la línea")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Guardar borrador" })).toBeDisabled();
  });

  it("muestra los errores 422 de evidencias", async () => {
    const usuario = userEvent.setup();
    apiFetchMock.mockImplementation(async (ruta: string, opciones?: { method?: string }) => {
      if (ruta.startsWith("/gobierno/presupuesto/ejercicios/y1/causados/opciones")) {
        return crearOpciones();
      }
      if (ruta === "/gobierno/presupuesto/ejercicios/y1/causados" && opciones?.method === "POST") {
        throw new ApiError(422, {
          code: "GOV_BUDGET_CAUSE_EVIDENCE_MISSING",
          message: "Falta la evidencia exigida por la política",
          field_errors: { evidencias: ["Falta CONTRACT_RECEIPT"] },
        });
      }
      throw new Error(`Ruta no esperada: ${ruta}`);
    });
    renderPagina("/gobierno/presupuesto/causados/nuevo?ejercicio=y1");
    await screen.findByRole("heading", { name: "Nuevo causado" });
    await usuario.selectOptions(screen.getByRole("combobox", { name: "Compromiso" }), "k1");
    await usuario.type(await screen.findByLabelText("Monto a causar 4.02.01.01.001"), "40.00");
    await usuario.selectOptions(screen.getByLabelText("Política"), "p1");
    await usuario.type(screen.getByRole("textbox", { name: "Concepto (obligatorio)" }), "Mantenimiento preventivo de equipos");
    await usuario.click(screen.getByRole("button", { name: "Guardar borrador" }));

    expect(await screen.findByText("Falta la evidencia exigida por la política")).toBeInTheDocument();
    expect(screen.getByText("Falta CONTRACT_RECEIPT")).toBeInTheDocument();
  });

  it("muestra 409 al editar y recarga", async () => {
    const usuario = userEvent.setup();
    apiFetchMock.mockImplementation(async (ruta: string, opciones?: { method?: string; ifMatch?: string }) => {
      if (ruta === "/gobierno/presupuesto/causados/c1" && opciones?.method === "PUT") {
        throw new ApiError(409, {
          code: "GOV_BUDGET_CAUSE_STALE",
          message: "El causado cambió",
        });
      }
      if (ruta === "/gobierno/presupuesto/causados/c1") {
        return crearCausado();
      }
      if (ruta.startsWith("/gobierno/presupuesto/ejercicios/y1/causados/opciones")) {
        return crearOpciones();
      }
      throw new Error(`Ruta no esperada: ${ruta}`);
    });
    renderPagina("/gobierno/presupuesto/causados/c1/editar");
    await screen.findByRole("heading", { name: "Editar borrador de causado" });
    await usuario.type(screen.getByRole("textbox", { name: "Concepto (obligatorio)" }), "Mantenimiento preventivo de equipos");
    await usuario.click(screen.getByRole("button", { name: "Guardar borrador" }));

    expect(await screen.findByText("El causado cambió")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Recargar" })).toBeInTheDocument();

    expect(apiFetchMock).toHaveBeenCalledWith(
      "/gobierno/presupuesto/causados/c1",
      expect.objectContaining({ method: "PUT", ifMatch: "3" }),
    );
  });

  it("indica Falta el ejercicio sin query param", async () => {
    renderPagina("/gobierno/presupuesto/causados/nuevo");
    expect(await screen.findByText("Falta el ejercicio")).toBeInTheDocument();
  });

  it("las tablas están en contenedores responsive", async () => {
    const usuario = userEvent.setup();
    apiFetchMock.mockImplementation(async (ruta: string) => {
      if (ruta.startsWith("/gobierno/presupuesto/ejercicios/y1/causados/opciones")) {
        return crearOpciones();
      }
      throw new Error(`Ruta no esperada: ${ruta}`);
    });
    renderPagina("/gobierno/presupuesto/causados/nuevo?ejercicio=y1");
    await screen.findByRole("heading", { name: "Nuevo causado" });
    await usuario.selectOptions(screen.getByRole("combobox", { name: "Compromiso" }), "k1");
    const tabla = await screen.findByRole("table");
    expect(tabla.closest(".overflow-x-auto")).not.toBeNull();
  });
});
