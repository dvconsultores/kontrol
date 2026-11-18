import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/api/client";
import { OrdenPagoPage } from "./OrdenPagoPage";
import type { OrdenPago, Control, OpcionesOrden } from "./api";

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

const CODIGOS_CONTROL = [
  "POLITICA",
  "COMPATIBILIDAD",
  "FALTA_BENEFICIARIO",
  "SALDO_INSUFICIENTE",
  "FALTA_EVIDENCIA",
  "FALTA_DOCUMENTO",
  "FECHA",
  "FALTA_AUTORIDAD",
  "LIMITE",
];

function crearControl(partial: Partial<Control> = {}): Control {
  return {
    codigo: "POLITICA",
    cumplido: true,
    mensaje: "Política vigente",
    ...partial,
  };
}

function controlesCompletos(): Control[] {
  return CODIGOS_CONTROL.map((codigo) => crearControl({ codigo, cumplido: true }));
}

function crearOrden(partial: Partial<OrdenPago> = {}): OrdenPago {
  return {
    id: "o1",
    codigo: "Borrador de orden de pago",
    numero: null,
    estado: "BORRADOR",
    year_id: "y1",
    anio: 2026,
    fecha_orden: "2026-03-01",
    concepto: "Mantenimiento de equipos",
    moneda: "USD",
    monto: "100.00",
    beneficiario: "Proveedor Uno",
    policy: { id: "p1", codigo: "POL-OP-001", nombre: "Política de pagos", version: 1 },
    lineas: [
      {
        cause_id: "c1",
        codigo: "2026-00001",
        compromiso_codigo: "COM-2026-00001",
        beneficiario: "Proveedor Uno",
        fecha_efectiva: "2026-03-01",
        monto_causado: "100.00",
        monto_ordenado: "0.00",
        pendiente_de_ordenar: "100.00",
        monto_asignado: "100.00",
      },
    ],
    documentos: [],
    autoridad: {
      cargo_id: "r1",
      cargo: "Director de Tesorería",
      unidad: "Tesorería",
      funcionario_id: null,
      funcionario: null,
      usuario_id: null,
    },
    emitida_en: null,
    emitida_por: null,
    anulada_en: null,
    motivo_anulacion: null,
    huella: null,
    version: 1,
    monto_pagado: "0.00",
    pendiente_de_pagar: "100.00",
    siguiente_paso: null,
    historia: [{ evento: "BORRADOR_CREADO", fecha: "2026-03-01T10:00:00+00:00", actor: "ord_t03" }],
    controles: { controles: controlesCompletos(), completo: true },
    ...partial,
  };
}

function crearOpciones(partial: Partial<OpcionesOrden> = {}): OpcionesOrden {
  return {
    obligaciones: [],
    politicas: [],
    documentos: [],
    cargos: [{ id: "r1", codigo: "DIR-TES", nombre: "Director de Tesorería" }],
    ...partial,
  };
}

function renderPagina(rutaInicial = "/gobierno/tesoreria/ordenes-pago/o1") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[rutaInicial]}>
        <Routes>
          <Route path="/gobierno/tesoreria/ordenes-pago/:ordenId" element={<OrdenPagoPage />} />
          <Route path="/gobierno/tesoreria/ordenes-pago/:ordenId/editar" element={<div>editar-destino</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );

  return queryClient;
}

const ORDEN_EMITIDA: OrdenPago = crearOrden({
  codigo: "2026-00001",
  numero: 1,
  estado: "EMITIDA",
  version: 2,
  monto: "50.00",
  moneda: "VES",
  beneficiario: "Proveedor Uno C.A.",
  policy: { id: "b47d44d0-9453-46d1-8c4f-240d88cf6bd1", codigo: "OPB0C26DCB4EF7", nombre: "Política de orden de pago de prueba", version: 2 },
  lineas: [
    {
      cause_id: "36d1033f-2e01-4696-9536-bf93e97949ad",
      codigo: "2026-00002",
      compromiso_codigo: "CP-2026-0002",
      beneficiario: "Proveedor Uno C.A.",
      fecha_efectiva: "2026-11-17",
      monto_causado: "50.00",
      monto_ordenado: "10.00",
      pendiente_de_ordenar: "40.00",
      monto_asignado: "10.00",
    },
    {
      cause_id: "70b81d47-294f-4d34-9ac0-c75cbd29002c",
      codigo: "2026-00001",
      compromiso_codigo: "CP-2026-0001",
      beneficiario: "Proveedor Uno C.A.",
      fecha_efectiva: "2026-11-17",
      monto_causado: "100.00",
      monto_ordenado: "40.00",
      pendiente_de_ordenar: "60.00",
      monto_asignado: "40.00",
    },
  ],
  autoridad: {
    cargo_id: "a337dd42-7979-4741-877b-6b1b7da77854",
    cargo: "Cargo ordenar N-0018-167e0a",
    unidad: "Unidad raíz ORG-04",
    funcionario_id: null,
    funcionario: null,
    usuario_id: "d1952956-1ac0-4dd2-ad4f-96db4423254f",
  },
  emitida_en: "2026-11-17T18:45:37.121595Z",
  emitida_por: "ord_t03",
  pendiente_de_pagar: "50.00",
  siguiente_paso: "Pago (TRE-04)",
  historia: [
    { evento: "EMITIDA", fecha: "2026-11-17T18:45:37.099232+00:00", actor: "ord_t03" },
    { evento: "BORRADOR_CREADO", fecha: "2026-11-17T18:45:36.812402+00:00", actor: "ord_t03" },
  ],
  controles: undefined,
});

const ORDEN_ANULADA: OrdenPago = {
  ...ORDEN_EMITIDA,
  estado: "ANULADA",
  version: 3,
  anulada_en: "2026-11-17T18:45:37.481313Z",
  motivo_anulacion: "Anulación de prueba de la orden",
  siguiente_paso: null,
  lineas: ORDEN_EMITIDA.lineas.map((linea) => ({
    ...linea,
    pendiente_de_ordenar: linea.cause_id === "36d1033f-2e01-4696-9536-bf93e97949ad" ? "50.00" : "100.00",
  })),
  historia: [
    { evento: "ANULADA", fecha: "2026-11-17T18:45:37.469486+00:00", actor: "ord_t03" },
    ...ORDEN_EMITIDA.historia,
  ],
};

describe("OrdenPagoPage", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    capacidades = new Set(["gobierno_ordenes_pago:view", "gobierno_ordenes_pago:manage"]);
  });

  it("BORRADOR con 9 controles cumplidos muestra 9 líneas con Cumple y habilita emitir", async () => {
    const orden = crearOrden({ codigo: "Borrador de orden de pago" });
    apiFetchMock.mockImplementation((ruta: string) => {
      if (ruta === "/gobierno/tesoreria/ordenes-pago/o1") {
        return Promise.resolve(orden);
      }
      return Promise.reject(new Error(`Ruta no esperada: GET ${ruta}`));
    });
    capacidades = new Set(["gobierno_ordenes_pago:view", "gobierno_ordenes_pago:manage", "gobierno_ordenes_pago:issue"]);

    renderPagina();

    expect(await screen.findByRole("heading", { level: 1, name: "Borrador de orden de pago" })).toBeInTheDocument();

    const seccionControles = screen.getByRole("region", { name: "Controles" });
    const lineasCumple = within(seccionControles).getAllByText(/· Cumple ·/);
    expect(lineasCumple).toHaveLength(9);

    expect(within(seccionControles).getByText(/Segregación de funciones — Se verifica al emitir \(CTL-01\)/)).toBeInTheDocument();

    const botonEmitir = screen.getByRole("button", { name: "Emitir orden de pago" });
    expect(botonEmitir).toBeEnabled();
  });

  it("controles incompletos muestran Falta y deshabilitan emitir", async () => {
    const controles = controlesCompletos().map((control) =>
      control.codigo === "FALTA_DOCUMENTO" || control.codigo === "LIMITE"
        ? { ...control, cumplido: false, mensaje: "Requisito pendiente" }
        : control,
    );
    const orden = crearOrden({
      codigo: "Borrador de orden de pago",
      controles: { controles, completo: false },
    });
    apiFetchMock.mockImplementation((ruta: string) => {
      if (ruta === "/gobierno/tesoreria/ordenes-pago/o1") {
        return Promise.resolve(orden);
      }
      return Promise.reject(new Error(`Ruta no esperada: GET ${ruta}`));
    });
    capacidades = new Set(["gobierno_ordenes_pago:view", "gobierno_ordenes_pago:manage", "gobierno_ordenes_pago:issue"]);

    renderPagina();

    await screen.findByRole("heading", { level: 1, name: "Borrador de orden de pago" });

    const seccionControles = screen.getByRole("region", { name: "Controles" });
    expect(within(seccionControles).getAllByText(/· Falta ·/)).toHaveLength(2);
    expect(
      within(seccionControles).getByText("Faltan requisitos: el sistema impedirá emitir hasta cumplirlos."),
    ).toBeInTheDocument();

    const botonEmitir = screen.getByRole("button", { name: "Emitir orden de pago" });
    expect(botonEmitir).toBeDisabled();
  });

  it("emite una orden desde el diálogo y muestra el detalle emitido", async () => {
    let ordenActual: OrdenPago = crearOrden({
      codigo: "Borrador de orden de pago",
      version: 1,
    });
    apiFetchMock.mockImplementation((ruta: string, opciones?: { method?: string; ifMatch?: string; body?: unknown }) => {
      if (ruta === "/gobierno/tesoreria/ordenes-pago/o1" && (!opciones?.method || opciones.method === "GET")) {
        return Promise.resolve(ordenActual);
      }
      if (ruta === "/gobierno/tesoreria/ordenes-pago/o1/emitir" && opciones?.method === "POST") {
        expect(opciones.ifMatch).toBe("1");
        ordenActual = { ...ORDEN_EMITIDA, id: "o1", controles: ORDEN_EMITIDA.controles };
        return Promise.resolve(ordenActual);
      }
      if (ruta === "/gobierno/tesoreria/ejercicios/y1/ordenes-pago/opciones") {
        return Promise.resolve(crearOpciones());
      }
      return Promise.reject(new Error(`Ruta no esperada: ${opciones?.method ?? "GET"} ${ruta}`));
    });
    capacidades = new Set(["gobierno_ordenes_pago:view", "gobierno_ordenes_pago:manage", "gobierno_ordenes_pago:issue"]);

    renderPagina();
    const usuario = userEvent.setup();

    await screen.findByRole("heading", { level: 1, name: "Borrador de orden de pago" });
    await usuario.click(screen.getByRole("button", { name: "Emitir orden de pago" }));

    const dialogo = screen.getByRole("dialog", { name: "Emitir orden de pago" });
    expect(within(dialogo).getByText(/Se emitirá una orden de pago de/)).toBeInTheDocument();

    await usuario.click(within(dialogo).getByRole("button", { name: "Emitir" }));

    expect(await screen.findByRole("heading", { level: 1, name: "2026-00001" })).toBeInTheDocument();
    expect(await screen.findByText(/Pago \(TRE-04\)/)).toBeInTheDocument();
  });

  it("bloquea la emisión ante conflicto de segregación de funciones", async () => {
    const orden = crearOrden({ codigo: "Borrador de orden de pago", version: 1 });
    apiFetchMock.mockImplementation((ruta: string, opciones?: { method?: string; body?: unknown }) => {
      if (ruta === "/gobierno/tesoreria/ordenes-pago/o1" && (!opciones?.method || opciones.method === "GET")) {
        return Promise.resolve(orden);
      }
      if (ruta === "/gobierno/tesoreria/ordenes-pago/o1/emitir" && opciones?.method === "POST") {
        return Promise.reject(
          new ApiError(409, {
            code: "GOV_SOD_CONFLICT",
            message: "La regla SOD-0001 lo impide",
            field_errors: {},
            request_id: "r1",
          }),
        );
      }
      return Promise.reject(new Error(`Ruta no esperada: ${opciones?.method ?? "GET"} ${ruta}`));
    });
    capacidades = new Set(["gobierno_ordenes_pago:view", "gobierno_ordenes_pago:manage", "gobierno_ordenes_pago:issue"]);

    renderPagina();
    const usuario = userEvent.setup();

    await screen.findByRole("heading", { level: 1, name: "Borrador de orden de pago" });
    await usuario.click(screen.getByRole("button", { name: "Emitir orden de pago" }));
    await usuario.click(screen.getByRole("button", { name: "Emitir" }));

    const seccionControles = await screen.findByRole("region", { name: "Controles" });
    expect(await within(seccionControles).findByText(/Bloqueado · La regla SOD-0001 lo impide/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "Borrador de orden de pago" })).toBeInTheDocument();
  });

  it("muestra No tiene permiso para esta acción ante 403 al emitir", async () => {
    const orden = crearOrden({ codigo: "Borrador de orden de pago", version: 1 });
    apiFetchMock.mockImplementation((ruta: string, opciones?: { method?: string; body?: unknown }) => {
      if (ruta === "/gobierno/tesoreria/ordenes-pago/o1" && (!opciones?.method || opciones.method === "GET")) {
        return Promise.resolve(orden);
      }
      if (ruta === "/gobierno/tesoreria/ordenes-pago/o1/emitir" && opciones?.method === "POST") {
        return Promise.reject(
          new ApiError(403, {
            code: "GOV_FORBIDDEN",
            message: "Prohibido",
            field_errors: {},
            request_id: "r1",
          }),
        );
      }
      return Promise.reject(new Error(`Ruta no esperada: ${opciones?.method ?? "GET"} ${ruta}`));
    });
    capacidades = new Set(["gobierno_ordenes_pago:view", "gobierno_ordenes_pago:manage", "gobierno_ordenes_pago:issue"]);

    renderPagina();
    const usuario = userEvent.setup();

    await screen.findByRole("heading", { level: 1, name: "Borrador de orden de pago" });
    await usuario.click(screen.getByRole("button", { name: "Emitir orden de pago" }));
    await usuario.click(screen.getByRole("button", { name: "Emitir" }));

    expect(await screen.findByText("No tiene permiso para esta acción")).toBeInTheDocument();
  });

  it("muestra conflicto de versión al emitir", async () => {
    const orden = crearOrden({ codigo: "Borrador de orden de pago", version: 1 });
    apiFetchMock.mockImplementation((ruta: string, opciones?: { method?: string; body?: unknown }) => {
      if (ruta === "/gobierno/tesoreria/ordenes-pago/o1" && (!opciones?.method || opciones.method === "GET")) {
        return Promise.resolve(orden);
      }
      if (ruta === "/gobierno/tesoreria/ordenes-pago/o1/emitir" && opciones?.method === "POST") {
        return Promise.reject(
          new ApiError(409, {
            code: "GOV_PAYMENT_ORDER_VERSION_CONFLICT",
            message: "La orden fue modificada por otro usuario",
            field_errors: {},
            request_id: "r1",
          }),
        );
      }
      return Promise.reject(new Error(`Ruta no esperada: ${opciones?.method ?? "GET"} ${ruta}`));
    });
    capacidades = new Set(["gobierno_ordenes_pago:view", "gobierno_ordenes_pago:manage", "gobierno_ordenes_pago:issue"]);

    renderPagina();
    const usuario = userEvent.setup();

    await screen.findByRole("heading", { level: 1, name: "Borrador de orden de pago" });
    await usuario.click(screen.getByRole("button", { name: "Emitir orden de pago" }));
    await usuario.click(screen.getByRole("button", { name: "Emitir" }));

    expect(await screen.findByText(/^La orden cambió o una regla lo impide/)).toBeInTheDocument();
  });

  it("EMITIDA muestra código, estado, montos e historia y no muestra Controles", async () => {
    apiFetchMock.mockImplementation((ruta: string) => {
      if (ruta === "/gobierno/tesoreria/ordenes-pago/o1") {
        return Promise.resolve(ORDEN_EMITIDA);
      }
      return Promise.reject(new Error(`Ruta no esperada: GET ${ruta}`));
    });
    capacidades = new Set(["gobierno_ordenes_pago:view", "gobierno_ordenes_pago:manage", "gobierno_ordenes_pago:cancel"]);

    renderPagina();

    expect(await screen.findByRole("heading", { level: 1, name: "2026-00001" })).toBeInTheDocument();
    expect(screen.getAllByText("Emitida").length).toBeGreaterThan(0);

    const filaLinea = screen.getByRole("row", { name: /^2026-00002/ });
    expect(within(filaLinea).getAllByRole("cell", { name: "10.00" })).toHaveLength(2);
    expect(within(filaLinea).getByRole("cell", { name: "40.00" })).toBeInTheDocument();

    expect(screen.getByText("EMITIDA")).toBeInTheDocument();
    expect(screen.getByText("BORRADOR_CREADO")).toBeInTheDocument();

    expect(screen.queryByRole("region", { name: "Controles" })).not.toBeInTheDocument();
  });

  it("anula una orden emitida con motivo y cargo válidos", async () => {
    let ordenActual: OrdenPago = ORDEN_EMITIDA;
    let postLlamado = false;
    apiFetchMock.mockImplementation((ruta: string, opciones?: { method?: string; ifMatch?: string; body?: unknown }) => {
      if (ruta === "/gobierno/tesoreria/ordenes-pago/o1" && (!opciones?.method || opciones.method === "GET")) {
        return Promise.resolve(ordenActual);
      }
      if (ruta === "/gobierno/tesoreria/ordenes-pago/o1/anular" && opciones?.method === "POST") {
        postLlamado = true;
        expect(opciones.ifMatch).toBe("2");
        expect(opciones.body).toEqual({ motivo: "Anulación de prueba de la orden", cargo_id: "r1" });
        ordenActual = { ...ORDEN_ANULADA, id: "o1" };
        return Promise.resolve(ordenActual);
      }
      if (ruta === "/gobierno/tesoreria/ejercicios/y1/ordenes-pago/opciones") {
        return Promise.resolve(crearOpciones());
      }
      return Promise.reject(new Error(`Ruta no esperada: ${opciones?.method ?? "GET"} ${ruta}`));
    });
    capacidades = new Set(["gobierno_ordenes_pago:view", "gobierno_ordenes_pago:manage", "gobierno_ordenes_pago:cancel"]);

    renderPagina();
    const usuario = userEvent.setup();

    await screen.findByRole("heading", { level: 1, name: "2026-00001" });
    await usuario.click(screen.getByRole("button", { name: "Anular" }));

    const dialogo = screen.getByRole("dialog", { name: "Anular la orden de pago" });
    expect(
      within(dialogo).getByText("El monto vuelve a quedar pendiente de ordenar en los causados."),
    ).toBeInTheDocument();

    const motivoTextarea = within(dialogo).getByRole("textbox", { name: /^Motivo de la anulación/ });
    await usuario.type(motivoTextarea, "corto");
    await usuario.click(within(dialogo).getByRole("button", { name: "Anular" }));
    expect(within(dialogo).getByText("El motivo debe tener al menos 10 caracteres")).toBeInTheDocument();
    expect(postLlamado).toBe(false);

    await usuario.clear(motivoTextarea);
    await usuario.type(motivoTextarea, "Anulación de prueba de la orden");
    await usuario.selectOptions(within(dialogo).getByRole("combobox", { name: /^Cargo que anula/ }), "r1");
    await usuario.click(within(dialogo).getByRole("button", { name: "Anular" }));

    expect(postLlamado).toBe(true);
    expect(await screen.findByText("Anulada")).toBeInTheDocument();
    expect(await screen.findByText(/Anulación de prueba de la orden/)).toBeInTheDocument();
  });

  it("ANULADA cargada directamente no muestra acciones de emitir ni anular", async () => {
    apiFetchMock.mockImplementation((ruta: string) => {
      if (ruta === "/gobierno/tesoreria/ordenes-pago/o1") {
        return Promise.resolve(ORDEN_ANULADA);
      }
      return Promise.reject(new Error(`Ruta no esperada: GET ${ruta}`));
    });
    capacidades = new Set(["gobierno_ordenes_pago:view", "gobierno_ordenes_pago:manage", "gobierno_ordenes_pago:issue", "gobierno_ordenes_pago:cancel"]);

    renderPagina();

    await screen.findByRole("heading", { level: 1, name: "2026-00001" });
    expect(screen.queryByRole("button", { name: "Emitir orden de pago" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Anular" })).not.toBeInTheDocument();
  });

  it("oculta emitir sin capacidad issue y anular sin capacidad cancel", async () => {
    apiFetchMock.mockImplementation((ruta: string) => {
      if (ruta === "/gobierno/tesoreria/ordenes-pago/o1") {
        return Promise.resolve(ORDEN_EMITIDA);
      }
      return Promise.reject(new Error(`Ruta no esperada: GET ${ruta}`));
    });
    capacidades = new Set(["gobierno_ordenes_pago:view", "gobierno_ordenes_pago:manage"]);

    renderPagina();

    await screen.findByRole("heading", { level: 1, name: "2026-00001" });
    expect(screen.queryByRole("button", { name: "Emitir orden de pago" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Anular" })).not.toBeInTheDocument();
  });

  it("sin capacidad view muestra permiso denegado y no consulta la API", async () => {
    capacidades = new Set<string>();

    renderPagina();

    expect(
      await screen.findByText("No tiene permiso para consultar órdenes de pago"),
    ).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });
});
