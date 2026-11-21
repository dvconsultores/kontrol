import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { RetencionesPago } from "./RetencionesPago";
import { RetencionesPage } from "./RetencionesPage";
import type { Liquidacion, OpcionesRetencion } from "./api";

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

const liquidacionCalculada: Liquidacion = {
  id: "liq-1",
  payment_id: "pago-1",
  pago_codigo: "PG-001",
  pago_estado: "POR_PAGAR",
  policy_id: "pol-1",
  policy_codigo: "POL-RET-1",
  policy_numero_version: 1,
  estado: "CALCULADA",
  fecha_referencia: "2025-01-15",
  moneda: "VES",
  bruto: "1000.00",
  total_retenido: "150.00",
  neto: "850.00",
  conceptos: ["RET-ISLR"],
  beneficiario: {
    nombre: "Beneficiario Uno",
    identificacion_fiscal: "J-12345678-9",
    tipo_persona: "JURIDICA",
    condiciones: [],
  },
  permite_ajuste: true,
  politica_fuente: {
    tipo_regla: "INSTITUTIONAL_POLICY",
    estado_verificacion: "PENDING_PIN",
    fuente_descripcion: null,
    fuente_referencia: null,
  },
  calculado_por: "usr-1",
  calculado_en: "2025-01-15T10:00:00Z",
  aprobado_por: null,
  aprobado_en: null,
  aprobador_cargo_codigo: null,
  aprobador_cargo_nombre: null,
  aprobador_funcionario_nombre: null,
  aplicado_en: null,
  anulado_por: null,
  anulado_en: null,
  motivo_anulacion: null,
  huella: "abc123",
  version: 1,
  lineas: [
    {
      id: "linea-1",
      orden: 1,
      concepto_codigo: "RET-ISLR",
      concepto_nombre: "ISLR Persona Jurídica",
      clase: "TRIBUTARIA",
      base: "1000.00",
      tasa: "15.00",
      umbral: "0",
      tasa_referencia: null,
      aplica: true,
      motivo_no_aplica: null,
      monto_calculado: "150.00",
      monto_aprobado: "150.00",
      motivo_ajuste: null,
      ajustado_por: null,
      ajustado_en: null,
      exige_comprobante: true,
    },
    {
      id: "linea-2",
      orden: 2,
      concepto_codigo: "RET-OTRO",
      concepto_nombre: "Otro concepto",
      clase: "OTRA",
      base: "1000.00",
      tasa: "5.00",
      umbral: "2000.00",
      tasa_referencia: null,
      aplica: false,
      motivo_no_aplica: "UMBRAL",
      monto_calculado: "0.00",
      monto_aprobado: "0.00",
      motivo_ajuste: null,
      ajustado_por: null,
      ajustado_en: null,
      exige_comprobante: false,
    },
  ],
  comprobantes: [],
};

const opcionesMock: OpcionesRetencion = {
  pago: {
    id: "pago-1",
    codigo: "PG-001",
    estado: "POR_PAGAR",
    moneda: "VES",
    monto: "1000.00",
    fecha_pago: "2025-01-15",
  },
  politicas: [
    {
      id: "pol-1",
      codigo: "POL-RET-1",
      numero_version: 1,
      nombre: "Política de retención estándar",
      permite_ajuste: true,
      conceptos: ["RET-ISLR"],
    },
  ],
  conceptos: [
    {
      id: "con-1",
      tipo: "CONCEPTO",
      codigo: "RET-ISLR",
      nombre: "ISLR Persona Jurídica",
      descripcion: null,
      clase: "TRIBUTARIA",
      serie_comprobante: "SER-1",
      estado: "ACTIVO",
      version: 1,
    },
  ],
  condiciones: [],
  tipos_persona: ["NATURAL", "JURIDICA"],
  liquidacion: null,
};

const cargosOpciones = {
  cargos: [
    {
      id: "cargo-1",
      codigo: "DIR",
      nombre: "Director",
      competencias: ["gobierno_retenciones:approve"],
    },
    {
      id: "cargo-2",
      codigo: "JEF",
      nombre: "Jefe",
      competencias: [],
    },
  ],
};

function renderRetencionesPago(pagoId: string, pagoEstado: string) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <RetencionesPago pagoId={pagoId} pagoEstado={pagoEstado} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function renderRetencionesPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/gobierno/tesoreria/retenciones"]}>
        <Routes>
          <Route path="/gobierno/tesoreria/retenciones" element={<RetencionesPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("RetencionesPago", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    capacidades = new Set([
      "gobierno_retenciones:view",
      "gobierno_retenciones:manage",
      "gobierno_retenciones:calculate",
      "gobierno_retenciones:policy",
      "gobierno_retenciones:approve",
      "gobierno_retenciones:cancel",
    ]);
  });

  afterEach(() => {
    cleanup();
  });

  it("no renderiza la sección sin la capacidad view", async () => {
    capacidades.delete("gobierno_retenciones:view");
    renderRetencionesPago("pago-1", "BORRADOR");

    expect(screen.queryByRole("heading", { name: "Retenciones" })).not.toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("muestra Calcular retenciones y bruto=neto sin liquidación y pago BORRADOR", async () => {
    apiFetchMock.mockImplementation(async (ruta: string) => {
      if (ruta.includes("/pagos/pago-1/liquidacion")) {
        return {
          montos: {
            bruto: "1000.00",
            total_retenido: "0.00",
            neto: "1000.00",
            moneda: "VES",
            liquidacion_id: null,
            estado_liquidacion: null,
            definitivo: false,
          },
          liquidacion: null,
        };
      }
      throw new Error(`Ruta no mockeada: ${ruta}`);
    });

    renderRetencionesPago("pago-1", "BORRADOR");
    const calcularBtn = await screen.findByRole("button", { name: "Calcular retenciones" });
    expect(calcularBtn).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Retenciones" })).toBeInTheDocument();
    expect(screen.getByText("Bruto")).toBeInTheDocument();
    expect(screen.getByText("Neto")).toBeInTheDocument();
    expect(screen.getByText("Preliminar")).toBeInTheDocument();
    const brutoValor = screen.getAllByText("1000.00 VES");
    expect(brutoValor.length).toBeGreaterThan(0);
  });

  it("calcular: abre el formulario y envía POST con body esperado", async () => {
    apiFetchMock.mockImplementation(async (ruta: string, opciones?: { method?: string; body?: unknown }) => {
      const method = opciones?.method ?? "GET";
      if (method === "GET" && ruta.includes("/pagos/pago-1/liquidacion")) {
        return {
          montos: {
            bruto: "1000.00",
            total_retenido: "0.00",
            neto: "1000.00",
            moneda: "VES",
            liquidacion_id: null,
            estado_liquidacion: null,
            definitivo: false,
          },
          liquidacion: null,
        };
      }
      if (method === "GET" && ruta.includes("/opciones")) {
        return opcionesMock;
      }
      if (method === "POST" && ruta.includes("/pagos/pago-1/liquidacion")) {
        return { ...liquidacionCalculada, estado: "CALCULADA" };
      }
      throw new Error(`Ruta no mockeada: ${ruta} ${method}`);
    });

    const user = userEvent.setup();
    renderRetencionesPago("pago-1", "BORRADOR");

    const calcularBtn = await screen.findByRole("button", { name: "Calcular retenciones" });
    await user.click(calcularBtn);

    const politicaSelect = await screen.findByLabelText("Política de retención");
    await user.selectOptions(politicaSelect, "pol-1");

    const conceptoCheckbox = screen.getByLabelText("RET-ISLR · ISLR Persona Jurídica");
    await user.click(conceptoCheckbox);

    const nombreInput = screen.getByLabelText("Nombre");
    await user.type(nombreInput, "Beneficiario Uno");

    const identifInput = screen.getByLabelText("Identificación fiscal");
    await user.type(identifInput, "J-12345678-9");

    const tipoSelect = screen.getByLabelText("Tipo de persona");
    await user.selectOptions(tipoSelect, "JURIDICA");

    const confirmarBtn = screen.getByRole("button", { name: "Calcular" });
    await user.click(confirmarBtn);

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/pagos/pago-1/liquidacion"),
        expect.objectContaining({
          method: "POST",
          body: expect.objectContaining({
            policy_id: "pol-1",
            conceptos: ["RET-ISLR"],
            beneficiario: expect.objectContaining({
              nombre: "Beneficiario Uno",
              identificacion_fiscal: "J-12345678-9",
              tipo_persona: "JURIDICA",
            }),
          }),
        }),
      );
    });
  });

  it("con liquidación CALCULADA muestra la tabla y motivo no aplica", async () => {
    apiFetchMock.mockImplementation(async (ruta: string) => {
      if (ruta.includes("/pagos/pago-1/liquidacion")) {
        return {
          montos: {
            bruto: "1000.00",
            total_retenido: "150.00",
            neto: "850.00",
            moneda: "VES",
            liquidacion_id: "liq-1",
            estado_liquidacion: "CALCULADA",
            definitivo: false,
          },
          liquidacion: liquidacionCalculada,
        };
      }
      throw new Error(`Ruta no mockeada: ${ruta}`);
    });

    renderRetencionesPago("pago-1", "POR_PAGAR");

    const tabla = await screen.findByRole("table", { name: "Retenciones calculadas" });
    expect(tabla).toBeInTheDocument();
    expect(within(tabla).getByText(/ISLR Persona Jurídica/)).toBeInTheDocument();
    expect(within(tabla).getAllByText("1000.00")).toHaveLength(2);
    expect(within(tabla).getByText("15.00")).toBeInTheDocument();
    expect(within(tabla).getAllByText("150.00").length).toBeGreaterThanOrEqual(2);
    expect(within(tabla).getByText("Por debajo del umbral")).toBeInTheDocument();
  });

  it("el resumen muestra bruto, retenciones y neto de montos", async () => {
    apiFetchMock.mockImplementation(async (ruta: string) => {
      if (ruta.includes("/pagos/pago-1/liquidacion")) {
        return {
          montos: {
            bruto: "1000.00",
            total_retenido: "150.00",
            neto: "850.00",
            moneda: "VES",
            liquidacion_id: "liq-1",
            estado_liquidacion: "CALCULADA",
            definitivo: false,
          },
          liquidacion: liquidacionCalculada,
        };
      }
      throw new Error(`Ruta no mockeada: ${ruta}`);
    });

    renderRetencionesPago("pago-1", "POR_PAGAR");

    await screen.findByText("Bruto");
    expect(screen.getByRole("heading", { name: "Retenciones" })).toBeInTheDocument();
    expect(screen.getByText("Neto")).toBeInTheDocument();
    expect(screen.getAllByText("1000.00 VES").length).toBeGreaterThan(0);
    expect(screen.getAllByText("150.00 VES").length).toBeGreaterThan(0);
    expect(screen.getAllByText("850.00 VES").length).toBeGreaterThan(0);
  });

  it("sin permiso approve no aparece Aprobar retenciones", async () => {
    capacidades.delete("gobierno_retenciones:approve");
    apiFetchMock.mockImplementation(async (ruta: string) => {
      if (ruta.includes("/pagos/pago-1/liquidacion")) {
        return {
          montos: {
            bruto: "1000.00",
            total_retenido: "150.00",
            neto: "850.00",
            moneda: "VES",
            liquidacion_id: "liq-1",
            estado_liquidacion: "CALCULADA",
            definitivo: false,
          },
          liquidacion: liquidacionCalculada,
        };
      }
      throw new Error(`Ruta no mockeada: ${ruta}`);
    });

    renderRetencionesPago("pago-1", "POR_PAGAR");

    await screen.findByRole("table", { name: "Retenciones calculadas" });
    expect(screen.queryByRole("button", { name: "Aprobar retenciones" })).not.toBeInTheDocument();
  });

  it("aprobar: lista cargos y envía POST /aprobar con cargo_id e ifMatch", async () => {
    apiFetchMock.mockImplementation(async (ruta: string, opciones?: { method?: string; body?: unknown }) => {
      const method = opciones?.method ?? "GET";
      if (method === "GET" && ruta.includes("/pagos/pago-1/liquidacion")) {
        return {
          montos: {
            bruto: "1000.00",
            total_retenido: "150.00",
            neto: "850.00",
            moneda: "VES",
            liquidacion_id: "liq-1",
            estado_liquidacion: "CALCULADA",
            definitivo: false,
          },
          liquidacion: liquidacionCalculada,
        };
      }
      if (method === "GET" && ruta.startsWith("/gobierno/tesoreria/pagos/opciones")) {
        return cargosOpciones;
      }
      if (method === "GET" && ruta.includes("/politicas/pol-1")) {
        return {
          id: "pol-1",
          codigo: "POL-RET-1",
          numero_version: 1,
          nombre: "Política de retención estándar",
          permite_ajuste: true,
          conceptos: ["RET-ISLR"],
          aprobador_competencia_accion: "APROBAR",
          aprobador_competencia_materia: "TESORERIA",
        };
      }
      if (method === "POST" && ruta.includes("/liquidaciones/liq-1/aprobar")) {
        return { ...liquidacionCalculada, estado: "APROBADA" };
      }
      throw new Error(`Ruta no mockeada: ${ruta} ${method}`);
    });

    const user = userEvent.setup();
    renderRetencionesPago("pago-1", "POR_PAGAR");

    const aprobarBtn = await screen.findByRole("button", { name: "Aprobar retenciones" });
    await user.click(aprobarBtn);

    const dialogo = await screen.findByRole("dialog", { name: "Aprobar retenciones" });
    const cargoSelect = within(dialogo).getByLabelText("Cargo que aprueba");
    await user.selectOptions(cargoSelect, "cargo-1");

    const confirmarBtn = within(dialogo).getByRole("button", { name: "Aprobar" });
    await user.click(confirmarBtn);

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/liquidaciones/liq-1/aprobar"),
        expect.objectContaining({
          method: "POST",
          ifMatch: "1",
          body: expect.objectContaining({ cargo_id: "cargo-1" }),
        }),
      );
    });
  });

  it("ajuste con motivo corto muestra alerta y no llama a la API", async () => {
    apiFetchMock.mockImplementation(async (ruta: string) => {
      if (ruta.includes("/pagos/pago-1/liquidacion")) {
        return {
          montos: {
            bruto: "1000.00",
            total_retenido: "150.00",
            neto: "850.00",
            moneda: "VES",
            liquidacion_id: "liq-1",
            estado_liquidacion: "CALCULADA",
            definitivo: false,
          },
          liquidacion: { ...liquidacionCalculada, permite_ajuste: true },
        };
      }
      throw new Error(`Ruta no mockeada: ${ruta}`);
    });

    const user = userEvent.setup();
    renderRetencionesPago("pago-1", "POR_PAGAR");

    const ajustarBtn = await screen.findByRole("button", { name: /Ajustar/ });
    await user.click(ajustarBtn);

    const dialogo = await screen.findByRole("dialog", { name: "Ajustar línea de retención" });
    const montoInput = within(dialogo).getByLabelText("Monto aprobado");
    await user.clear(montoInput);
    await user.type(montoInput, "100.00");

    const motivoInput = within(dialogo).getByLabelText("Motivo del ajuste");
    await user.type(motivoInput, "corto");

    const guardarBtn = within(dialogo).getByRole("button", { name: "Ajustar" });
    await user.click(guardarBtn);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });
    const putCalls = apiFetchMock.mock.calls.filter(([, opciones]) => opciones?.method === "PUT");
    expect(putCalls.length).toBe(0);
  });

  it("ajuste con motivo válido llama PUT con ifMatch", async () => {
    apiFetchMock.mockImplementation(async (ruta: string, opciones?: { method?: string; body?: unknown }) => {
      const method = opciones?.method ?? "GET";
      if (method === "GET" && ruta.includes("/pagos/pago-1/liquidacion")) {
        return {
          montos: {
            bruto: "1000.00",
            total_retenido: "150.00",
            neto: "850.00",
            moneda: "VES",
            liquidacion_id: "liq-1",
            estado_liquidacion: "CALCULADA",
            definitivo: false,
          },
          liquidacion: { ...liquidacionCalculada, permite_ajuste: true },
        };
      }
      if (method === "PUT" && ruta.includes("/liquidaciones/liq-1/lineas/linea-1")) {
        return {
          ...liquidacionCalculada.lineas[0],
          monto_aprobado: "100.00",
          motivo_ajuste: "Motivo válido de ajuste",
        };
      }
      throw new Error(`Ruta no mockeada: ${ruta} ${method}`);
    });

    const user = userEvent.setup();
    renderRetencionesPago("pago-1", "POR_PAGAR");

    const ajustarBtn = await screen.findByRole("button", { name: /Ajustar/ });
    await user.click(ajustarBtn);

    const dialogo = await screen.findByRole("dialog", { name: "Ajustar línea de retención" });
    const montoInput = within(dialogo).getByLabelText("Monto aprobado");
    await user.clear(montoInput);
    await user.type(montoInput, "100.00");

    const motivoInput = within(dialogo).getByLabelText("Motivo del ajuste");
    await user.type(motivoInput, "Motivo válido de ajuste");

    const guardarBtn = within(dialogo).getByRole("button", { name: "Ajustar" });
    await user.click(guardarBtn);

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/liquidaciones/liq-1/lineas/linea-1"),
        expect.objectContaining({
          method: "PUT",
          ifMatch: "1",
          body: expect.objectContaining({
            monto_aprobado: "100.00",
            motivo: "Motivo válido de ajuste",
          }),
        }),
      );
    });
  });

  it("error 422 de cálculo se muestra con role alert", async () => {
    const { ApiError } = await import("@/api/client");
    apiFetchMock.mockImplementation(async (ruta: string, opciones?: { method?: string }) => {
      const method = opciones?.method ?? "GET";
      if (method === "GET" && ruta.includes("/pagos/pago-1/liquidacion")) {
        return {
          montos: {
            bruto: "1000.00",
            total_retenido: "0.00",
            neto: "1000.00",
            moneda: "VES",
            liquidacion_id: null,
            estado_liquidacion: null,
            definitivo: false,
          },
          liquidacion: null,
        };
      }
      if (method === "GET" && ruta.includes("/opciones")) {
        return opcionesMock;
      }
      if (method === "POST" && ruta.includes("/pagos/pago-1/liquidacion")) {
        throw new ApiError(422, {
          code: "VALIDATION_ERROR",
          message: "Error de validación",
          field_errors: { "beneficiario.nombre": ["El nombre es obligatorio"] },
        });
      }
      throw new Error(`Ruta no mockeada: ${ruta} ${method}`);
    });

    const user = userEvent.setup();
    renderRetencionesPago("pago-1", "BORRADOR");

    const calcularBtn = await screen.findByRole("button", { name: "Calcular retenciones" });
    await user.click(calcularBtn);

    const politicaSelect = await screen.findByLabelText("Política de retención");
    await user.selectOptions(politicaSelect, "pol-1");

    const confirmarBtn = screen.getByRole("button", { name: "Calcular" });
    await user.click(confirmarBtn);

    await waitFor(() => {
      expect(
        screen.getAllByRole("alert").some((a) => a.textContent?.includes("El nombre es obligatorio")),
      ).toBe(true);
    });
    expect(
      screen.getAllByRole("alert").some((a) => a.textContent?.includes("Error de validación")),
    ).toBe(true);
  });
});

describe("RetencionesPage", () => {
  const liquidacionesPage = [
    {
      id: "liq-1",
      payment_id: "pago-1",
      pago_codigo: "PG-001",
      policy_codigo: "POL-RET-1",
      policy_numero_version: 1,
      estado: "CALCULADA",
      fecha_referencia: "2025-01-15",
      moneda: "VES",
      bruto: "1000.00",
      total_retenido: "150.00",
      neto: "850.00",
      beneficiario_nombre: "Beneficiario Uno",
      comprobantes: 0,
    },
  ];

  const comprobantesPage = [
    {
      id: "comp-1",
      codigo: "COMP-001",
      numero: "00001",
      serie: "SER-1",
      estado: "EMITIDO",
      settlement_id: null,
      payment_id: "pago-1",
      pago_codigo: "PG-001",
      concepto_codigo: "RET-ISLR",
      concepto_nombre: "ISLR Persona Jurídica",
      clase: "TRIBUTARIA",
      beneficiario_nombre: "Beneficiario Uno",
      identificacion_fiscal: "J-12345678-9",
      monto: "150.00",
      moneda: "VES",
      fecha_emision: "2025-01-15",
      emitido_en: "2025-01-15T10:00:00Z",
      anulado_en: null,
      motivo_anulacion: null,
      sustituye_a_id: null,
      sustituido_por_id: null,
      huella: "comp-hash",
      snapshot: null,
    },
  ];

  beforeEach(() => {
    apiFetchMock.mockReset();
    capacidades = new Set([
      "gobierno_retenciones:view",
      "gobierno_retenciones:manage",
      "gobierno_retenciones:calculate",
      "gobierno_retenciones:policy",
      "gobierno_retenciones:approve",
      "gobierno_retenciones:cancel",
    ]);
  });

  afterEach(() => {
    cleanup();
  });

  it("pestaña Comprobantes muestra tabla y anular con sustituto envía body esperado", async () => {
    apiFetchMock.mockImplementation(async (ruta: string, opciones?: { method?: string; body?: unknown }) => {
      const method = opciones?.method ?? "GET";
      if (method === "GET" && ruta.includes("/liquidaciones")) {
        return liquidacionesPage;
      }
      if (method === "GET" && ruta.includes("/comprobantes")) {
        return comprobantesPage;
      }
      if (method === "POST" && ruta.includes("/comprobantes/comp-1/anular")) {
        return { ...comprobantesPage[0], estado: "ANULADO" };
      }
      throw new Error(`Ruta no mockeada: ${ruta} ${method}`);
    });

    const user = userEvent.setup();
    renderRetencionesPage();

    const comprobantesTab = await screen.findByRole("tab", { name: "Comprobantes" });
    await user.click(comprobantesTab);

    const tabla = await screen.findByRole("table", { name: "Comprobantes de retención" });
    expect(within(tabla).getByText("COMP-001")).toBeInTheDocument();
    expect(within(tabla).getByText("RET-ISLR · ISLR Persona Jurídica")).toBeInTheDocument();

    const anularBtn = within(tabla).getByRole("button", { name: /Anular/ });
    await user.click(anularBtn);

    const dialogo = await screen.findByRole("dialog", { name: "Anular comprobante de retención" });
    const motivoInput = within(dialogo).getByLabelText("Motivo");
    await user.type(motivoInput, "Error en datos");

    const sustitutoCheckbox = within(dialogo).getByLabelText(/Emitir un comprobante sustituto/);
    await user.click(sustitutoCheckbox);

    const nombreCorregido = within(dialogo).getByLabelText("Nombre corregido");
    await user.clear(nombreCorregido);
    await user.type(nombreCorregido, "Beneficiario Corregido");

    const identifCorregida = within(dialogo).getByLabelText("Identificación fiscal corregida");
    await user.clear(identifCorregida);
    await user.type(identifCorregida, "J-98765432-1");

    const confirmarBtn = within(dialogo).getByRole("button", { name: /Confirmar|Anular/ });
    await user.click(confirmarBtn);

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/comprobantes/comp-1/anular"),
        expect.objectContaining({
          method: "POST",
          body: expect.objectContaining({
            motivo: "Error en datos",
            sustituir: true,
            beneficiario: expect.objectContaining({
              nombre: "Beneficiario Corregido",
              identificacion_fiscal: "J-98765432-1",
            }),
          }),
        }),
      );
    });
  });

  it("pestaña Liquidaciones muestra filas y enlace al pago", async () => {
    apiFetchMock.mockImplementation(async (ruta: string, opciones?: { method?: string; body?: unknown }) => {
      const method = opciones?.method ?? "GET";
      if (method === "GET" && ruta.includes("/liquidaciones")) {
        return liquidacionesPage;
      }
      if (method === "GET" && ruta.includes("/comprobantes")) {
        return comprobantesPage;
      }
      throw new Error(`Ruta no mockeada: ${ruta} ${method}`);
    });

    renderRetencionesPage();

    const tabla = await screen.findByRole("table", { name: "Liquidaciones de retenciones" });
    expect(within(tabla).getByText("PG-001")).toBeInTheDocument();
    expect(within(tabla).getByText("Calculada")).toBeInTheDocument();
    expect(within(tabla).getByText("Beneficiario Uno")).toBeInTheDocument();

    const enlacePago = within(tabla).getByRole("link", { name: /PG-001/ });
    expect(enlacePago).toBeInTheDocument();
    expect(enlacePago).toHaveAttribute("href", expect.stringContaining("pago-1"));
  });
});
