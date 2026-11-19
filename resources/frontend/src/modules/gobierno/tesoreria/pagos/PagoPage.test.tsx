import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/api/client";
import { PagoPage } from "./PagoPage";
import type { Pago, OpcionesPago } from "./api";

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

const ESTADOS_PAGO: Record<string, string> = {
  BORRADOR: "Borrador",
  PENDIENTE_AUTORIZACION: "Pendiente de autorización",
  AUTORIZADO: "Autorizado",
  REGISTRADO: "Pago registrado",
  RECHAZADO: "Rechazado",
  ANULADO: "Anulado",
};

const ESTAPAS_DOCUMENTO_PAGO: Record<string, string> = {
  PREPARAR: "Preparar",
  AUTORIZAR: "Autorizar",
  REGISTRAR: "Registrar",
  ANULAR: "Anular",
};

function fabricarPago(sobrescribir: Partial<Pago> = {}): Pago {
  return {
    id: "pago-1",
    codigo: "PAGO-0001",
    numero: 1,
    estado: "BORRADOR",
    version: 3,
    concepto: "Pago de servicios",
    moneda: "USD",
    monto: "100.00",
    fecha_pago: "2025-06-01",
    fecha_valor: null,
    referencia_externa: null,
    huella: null,
    duplicado_confirmado: false,
    motivo_duplicado: null,
    orden: {
      id: "orden-1",
      codigo: "OP-0001",
      beneficiario: "Proveedor Uno",
      moneda: "USD",
      fecha_orden: "2025-05-01",
      monto_ordenado: "100.00",
      monto_pagado: "40.00",
      monto_en_tramite: "30.00",
      pendiente_de_pagar: "60.00",
      disponible_para_pago: "30.00",
    },
    politica: {
      id: "politica-1",
      codigo: "POL-01",
      nombre: "Política general",
      numero_version: 1,
    },
    regla: {
      tipo_regla: "BANDA",
      banda: {
        orden: 1,
        monto_desde: "0.00",
        monto_hasta: "1000.00",
        requisitos: [
          { accion: "PAGAR", materia: "TESORERIA", cantidad: 2 },
        ],
      },
      aprobaciones_requeridas: 2,
    },
    cuenta: {
      id: "cuenta-1",
      codigo: "C-01",
      denominacion: "Cuenta principal",
      moneda: "USD",
      numero_enmascarado: "****1234",
    },
    medio: {
      id: "medio-1",
      codigo: "M-01",
      nombre: "Transferencia",
      exige_referencia: true,
      referencia_unica: false,
      patron_referencia: "^[A-Z0-9]{8}$",
    },
    preparador: {
      usuario: "user-prep",
      cargo: "Cargo preparador",
      funcionario: "Funcionario Prep.",
    },
    enviado_por: null,
    enviado_en: null,
    aprobaciones_requeridas: 2,
    aprobaciones: [
      {
        actor: "user-aprob",
        cargo: "Cargo que autoriza",
        unidad: null,
        funcionario: "Funcionario Aprob.",
        requisito_indice: 0,
        requisito: { accion: "PAGAR", materia: "TESORERIA" },
        decision: "APROBADA",
        motivo: null,
        fecha: "2025-06-02T10:00:00Z",
        policy_numero_version: 1,
      },
    ],
    documentos: [
      {
        etapa: "AUTORIZAR",
        document_id: "doc-1",
        titulo: "Comprobante",
        tipo: "application/pdf",
        sha256: null,
      },
    ],
    documentos_preparar: ["doc-1"],
    registrado_por: null,
    registrado_en: null,
    rechazado_por: null,
    rechazado_en: null,
    motivo_rechazo: null,
    anulado_por: null,
    anulado_en: null,
    motivo_anulacion: null,
    historia: [
      {
        evento: "CREACION",
        actor: "user-prep",
        fecha: "2025-06-01T09:00:00Z",
        instantanea: {},
      },
    ],
    ejecucion_externa: false,
    fronteras: {
      retenciones: "Sin retenciones",
      conciliacion: "Sin conciliación",
      reverso: "Sin reverso",
      contabilidad: "Sin contabilidad",
    },
    controles: {
      controles: [
        {
          codigo: "CONTROL_DUPLICADO",
          cumplido: true,
          mensaje: "Cumple: sin duplicado detectado",
        },
      ],
      completo: true,
      banda: {
        orden: 1,
        monto_desde: "0.00",
        monto_hasta: "1000.00",
        requisitos: [
          { accion: "PAGAR", materia: "TESORERIA", cantidad: 2 },
        ],
      },
      aprobaciones_requeridas: 2,
      saldo: {
        monto_ordenado: "100.00",
        monto_pagado: "40.00",
        monto_en_tramite: "30.00",
        pendiente_de_pagar: "60.00",
        disponible_para_pago: "30.00",
      },
    },
    ...sobrescribir,
  };
}

function fabricarOpcionesPago(): OpcionesPago {
  return {
    ordenes: [
      {
        id: "orden-1",
        codigo: "OP-0001",
        beneficiario: "Proveedor Uno",
        moneda: "USD",
        fecha_orden: "2025-05-01",
        year_id: "2025",
        monto_ordenado: "100.00",
        monto_pagado: "40.00",
        monto_en_tramite: "30.00",
        pendiente_de_pagar: "60.00",
        disponible_para_pago: "30.00",
      },
    ],
    politicas: [
      {
        id: "politica-1",
        codigo: "POL-01",
        numero_version: 1,
        nombre: "Política general",
        moneda: "USD",
        permite_pago_parcial: true,
        control_duplicado: "ADVERTIR",
        medios: ["medio-1"],
      },
    ],
    cuentas: [
      {
        id: "cuenta-1",
        codigo: "C-01",
        denominacion: "Cuenta principal",
        moneda: "USD",
        numero_enmascarado: "****1234",
      },
    ],
    medios: [
      {
        id: "medio-1",
        codigo: "M-01",
        nombre: "Transferencia",
        exige_referencia: true,
        referencia_unica: false,
        patron_referencia: "^[A-Z0-9]{8}$",
      },
    ],
    cargos: [
      {
        id: "cargo-1",
        codigo: "CARGO-01",
        nombre: "Tesorero",
        competencias: ["PAGAR:TESORERIA"],
      },
    ],
    documentos: [
      {
        id: "doc-1",
        titulo: "Comprobante",
        tipo: "application/pdf",
        document_type_id: "tipo-doc-1",
      },
    ],
  };
}

function renderConRuta(pago: Pago, opciones: OpcionesPago) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  apiFetchMock.mockImplementation(async (ruta: string, opcionesFetch?: { method?: string }) => {
    const metodo = opcionesFetch?.method ?? "GET";

    if (ruta.includes("/pagos/") && ruta.includes("/opciones") && metodo === "GET") {
      return opciones;
    }

    if (ruta.includes(`/pagos/${pago.id}`) && metodo === "GET") {
      return pago;
    }

    if (ruta.includes("/cargos") && metodo === "GET") {
      return fabricarOpcionesPago().cargos;
    }

    if (ruta.includes(`/pagos/${pago.id}/aprobar`) && metodo === "POST") {
      return { ...pago, estado: "AUTORIZADO", version: pago.version + 1 };
    }

    if (ruta.includes(`/pagos/${pago.id}/enviar`) && metodo === "POST") {
      return { ...pago, estado: "PENDIENTE_AUTORIZACION", version: pago.version + 1 };
    }

    if (ruta.includes(`/pagos/${pago.id}/registrar`) && metodo === "POST") {
      return { ...pago, estado: "REGISTRADO", version: pago.version + 1 };
    }

    if (ruta.includes(`/pagos/${pago.id}/descartar`) && metodo === "DELETE") {
      return { ok: true };
    }

    if (ruta.includes(`/pagos/${pago.id}/rechazar`) && metodo === "POST") {
      return { ...pago, estado: "RECHAZADO", version: pago.version + 1 };
    }

    if (ruta.includes(`/pagos/${pago.id}/anular`) && metodo === "POST") {
      return { ...pago, estado: "ANULADO", version: pago.version + 1 };
    }

    throw new Error(`Ruta no mockeada: ${ruta} ${metodo}`);
  });

  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/gobierno/tesoreria/pagos/${pago.id}`]}>
        <Routes>
          <Route path="/gobierno/tesoreria/pagos/:pagoId" element={<PagoPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );

  return queryClient;
}

describe("PagoPage", () => {
  beforeEach(() => {
    capacidades = new Set<string>();
    apiFetchMock.mockReset();
  });

  it("BORRADOR con manage muestra Enviar y Descartar y no Aprobar", async () => {
    capacidades = new Set(["gobierno_pagos:view", "gobierno_pagos:manage"]);
    const pago = fabricarPago({ estado: "BORRADOR" });
    renderConRuta(pago, fabricarOpcionesPago());

    await screen.findByRole("heading", { name: /Pago/i });

    expect(screen.getByRole("button", { name: /^Enviar/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Descartar/ })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Aprobar/ })).not.toBeInTheDocument();
  });

  it("PENDIENTE_AUTORIZACION con authorize muestra Aprobar y Rechazar, y sin authorize no los muestra", async () => {
    capacidades = new Set(["gobierno_pagos:view", "gobierno_pagos:authorize"]);
    const pago = fabricarPago({ estado: "PENDIENTE_AUTORIZACION" });
    renderConRuta(pago, fabricarOpcionesPago());

    await screen.findByRole("heading", { name: /Pago/i });

    expect(screen.getByRole("button", { name: /^Aprobar/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Rechazar/ })).toBeInTheDocument();

    capacidades = new Set(["gobierno_pagos:view"]);
    apiFetchMock.mockReset();
    renderConRuta(pago, fabricarOpcionesPago());

    await screen.findByRole("heading", { name: /Pago/i });

    expect(screen.queryByRole("button", { name: /^Aprobar/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Rechazar/ })).not.toBeInTheDocument();
  });

  it("al aprobar, apiFetch recibe /aprobar con method POST, ifMatch igual a la version y body con cargo_id y requisito_indice", async () => {
    capacidades = new Set(["gobierno_pagos:view", "gobierno_pagos:authorize"]);
    const pago = fabricarPago({ estado: "PENDIENTE_AUTORIZACION", version: 8 });
    renderConRuta(pago, fabricarOpcionesPago());

    await screen.findByRole("heading", { name: /Pago/i });

    const botonAprobar = screen.getByRole("button", { name: /^Aprobar/ });
    await userEvent.click(botonAprobar);

    await screen.findByText(/Confirme la aprobación del pago/);

    const cargoSelect = screen.getByLabelText(/Cargo que autoriza/);
    await userEvent.click(cargoSelect);
    const cargoOpcion = await screen.findByRole("option", { name: /Tesorero/ });
    await userEvent.click(cargoOpcion);

    const requisitoSelect = screen.getByLabelText(/Requisito/);
    await userEvent.click(requisitoSelect);
    const requisitoOpcion = await screen.findByRole("option", { name: /PAGAR.*TESORERIA/ });
    await userEvent.click(requisitoOpcion);

    const confirmar = screen.getByRole("button", { name: /^Aprobar/ });
    await userEvent.click(confirmar);

    await waitFor(() => {
      const llamada = apiFetchMock.mock.calls.find(
        ([ruta, opciones]: [string, { method?: string }]) =>
          ruta.includes(`/pagos/${pago.id}/aprobar`) && opciones?.method === "POST",
      );
      expect(llamada).toBeTruthy();
      const [, opciones] = llamada as [string, { method?: string; headers?: Record<string, string>; body?: Record<string, unknown> }];
      expect(opciones.headers?.["If-Match"]).toBe("8");
      expect(opciones.body).toMatchObject({
        cargo_id: "cargo-1",
        requisito_indice: 0,
      });
    });
  });

  it("error 409 GOV_PAYMENT_MAKER_CHECKER se muestra en un role alert con el mensaje de la API", async () => {
    capacidades = new Set(["gobierno_pagos:view", "gobierno_pagos:manage"]);
    const pago = fabricarPago({ estado: "BORRADOR" });

    apiFetchMock.mockImplementation(async (ruta: string, opcionesFetch?: { method?: string }) => {
      const metodo = opcionesFetch?.method ?? "GET";

      if (ruta.includes(`/pagos/${pago.id}`) && metodo === "GET") {
        return pago;
      }

      if (ruta.includes(`/pagos/${pago.id}/enviar`) && metodo === "POST") {
        throw new ApiError(
          409,
          "No puede autorizar su propio pago",
          "GOV_PAYMENT_MAKER_CHECKER",
        );
      }

      throw new Error(`Ruta no mockeada: ${ruta} ${metodo}`);
    });

    renderConRuta(pago, fabricarOpcionesPago());

    await screen.findByRole("heading", { name: /Pago/i });

    const botonEnviar = screen.getByRole("button", { name: /^Enviar/ });
    await userEvent.click(botonEnviar);

    await screen.findByText(/Confirme la aprobación del pago/);

    const confirmar = screen.getByRole("button", { name: /^Enviar/ });
    await userEvent.click(confirmar);

    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent("No puede autorizar su propio pago");
  });

  it("AUTORIZADO con execute muestra Registrar y el dialogo exige referencia cuando medio.exige_referencia", async () => {
    capacidades = new Set(["gobierno_pagos:view", "gobierno_pagos:execute"]);
    const pago = fabricarPago({
      estado: "AUTORIZADO",
      medio: {
        id: "medio-1",
        codigo: "M-01",
        nombre: "Transferencia",
        exige_referencia: true,
        referencia_unica: true,
        patron_referencia: "^[A-Z0-9]{8}$",
      },
    });
    renderConRuta(pago, fabricarOpcionesPago());

    await screen.findByRole("heading", { name: /Pago/i });

    const botonRegistrar = screen.getByRole("button", { name: /^Registrar/ });
    await userEvent.click(botonRegistrar);

    await screen.findByText(/Registre aquí un pago/);

    expect(screen.getByLabelText(/Referencia externa/)).toBeInTheDocument();
  });

  it("REGISTRADO no ofrece Anular y muestra el texto de TRE-07", async () => {
    capacidades = new Set(["gobierno_pagos:view", "gobierno_pagos:cancel"]);
    const pago = fabricarPago({ estado: "REGISTRADO" });
    renderConRuta(pago, fabricarOpcionesPago());

    await screen.findByRole("heading", { name: /Pago/i });

    expect(screen.queryByRole("button", { name: /^Anular/ })).not.toBeInTheDocument();
    expect(screen.getByText(/El pago ya no es editable/i)).toBeInTheDocument();
  });

  it("se pintan Ordenado, Pagado, En trámite, Pendiente de pagar y Disponible tal como vienen sin recalcular", async () => {
    capacidades = new Set(["gobierno_pagos:view"]);
    const pago = fabricarPago({
      estado: "BORRADOR",
      orden: {
        id: "orden-1",
        codigo: "OP-0001",
        beneficiario: "Proveedor Uno",
        moneda: "USD",
        fecha_orden: "2025-05-01",
        monto_ordenado: "100.00",
        monto_pagado: "40.00",
        monto_en_tramite: "30.00",
        pendiente_de_pagar: "60.00",
        disponible_para_pago: "30.00",
      },
    });
    renderConRuta(pago, fabricarOpcionesPago());

    await screen.findByRole("heading", { name: /Pago/i });

    expect(screen.getByText("100.00")).toBeInTheDocument();
    expect(screen.getByText("40.00")).toBeInTheDocument();
    expect(screen.getByText("30.00")).toBeInTheDocument();
    expect(screen.getByText("60.00")).toBeInTheDocument();
  });

  it("la regla congelada muestra la banda y N de M autorizaciones", async () => {
    capacidades = new Set(["gobierno_pagos:view"]);
    const pago = fabricarPago({
      estado: "PENDIENTE_AUTORIZACION",
      regla: {
        tipo_regla: "BANDA",
        banda: {
          orden: 1,
          monto_desde: "0.00",
          monto_hasta: "1000.00",
          requisitos: [
            { accion: "PAGAR", materia: "TESORERIA", cantidad: 2 },
          ],
        },
        aprobaciones_requeridas: 2,
      },
    });
    renderConRuta(pago, fabricarOpcionesPago());

    await screen.findByRole("heading", { name: /Pago/i });

    expect(screen.getByText(/0.00/)).toBeInTheDocument();
    expect(screen.getByText(/1000.00/)).toBeInTheDocument();
    expect(screen.getByText(/1 de 2/)).toBeInTheDocument();
  });
});
