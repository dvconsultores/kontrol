import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/api/client";
import { NuevaOrdenPagoPage } from "./NuevaOrdenPagoPage";
import type { ObligacionElegible, OpcionesOrden, OrdenPago } from "./api";

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

function crearObligacion(partial: Partial<ObligacionElegible> = {}): ObligacionElegible {
  return {
    id: "c1",
    codigo: "CAU-2026-00001",
    compromiso_codigo: "COM-2026-00001",
    beneficiario: "Proveedor Uno",
    moneda: "USD",
    fecha_efectiva: "2026-03-01",
    monto_causado: "100.00",
    monto_ordenado: "0.00",
    pendiente_de_ordenar: "100.00",
    tipo_gasto: "SERVICIOS",
    elegible: true,
    motivo: null,
    ...partial,
  };
}

function crearOpciones(partial: Partial<OpcionesOrden> = {}): OpcionesOrden {
  return {
    obligaciones: [crearObligacion()],
    politicas: [
      {
        id: "p1",
        codigo: "POL-OP-001",
        nombre: "Política de pagos",
        tipo_gasto: "Servicios",
        documentos: [],
      },
    ],
    cargos: [{ id: "r1", codigo: "DIR-TES", nombre: "Director de Tesorería" }],
    documentos: [{ id: "d1", titulo: "Factura", tipo: "PDF", document_type_id: "t1" }],
    ...partial,
  };
}

function renderPagina(rutaInicial = "/gobierno/tesoreria/ordenes-pago/nueva?ejercicio=y1") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[rutaInicial]}>
        <Routes>
          <Route path="/gobierno/tesoreria/ordenes-pago/nueva" element={<NuevaOrdenPagoPage />} />
          <Route path="/gobierno/tesoreria/ordenes-pago/:ordenId" element={<div>detalle-destino</div>} />
          <Route path="/gobierno/tesoreria/ordenes-pago/:ordenId/editar" element={<NuevaOrdenPagoPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  apiFetchMock.mockReset();
  capacidades = new Set(["gobierno_ordenes_pago:manage", "gobierno_ordenes_pago:view"]);
  vi.spyOn(console, "error").mockImplementation(() => {});
});

describe("NuevaOrdenPagoPage", () => {
  it("lista obligaciones elegibles y deshabilita no elegibles con su motivo", async () => {
    const opciones = crearOpciones({
      obligaciones: [
        crearObligacion({ id: "c1", codigo: "CAU-2026-00001" }),
        crearObligacion({
          id: "c2",
          codigo: "CAU-2026-00002",
          pendiente_de_ordenar: "0.00",
          elegible: false,
          motivo: "Sin pendiente de ordenar",
        }),
      ],
    });

    apiFetchMock.mockResolvedValueOnce(opciones);

    renderPagina();

    const checkbox1 = await screen.findByRole("checkbox", { name: "Seleccionar causado CAU-2026-00001" });
    const checkbox2 = await screen.findByRole("checkbox", { name: "Seleccionar causado CAU-2026-00002" });

    expect(checkbox1).toBeEnabled();
    expect(checkbox2).toBeDisabled();
    expect(screen.getByText("Sin pendiente de ordenar")).toBeInTheDocument();
  });

  it("prellena monto con el pendiente y calcula saldo parcial y total", async () => {
    apiFetchMock.mockResolvedValueOnce(crearOpciones());

    renderPagina();
    const usuario = userEvent.setup();

    const checkbox = await screen.findByRole("checkbox", { name: "Seleccionar causado CAU-2026-00001" });
    await usuario.click(checkbox);

    const montoInput = await screen.findByRole("textbox", { name: "Monto a ordenar de CAU-2026-00001" });
    expect(montoInput).toHaveValue("100.00");
    expect(screen.getByText("Pendiente tras esta orden")).toBeInTheDocument();
    expect(screen.getByText("TOTAL DE LA ORDEN: 100.00 USD")).toBeInTheDocument();

    await usuario.clear(montoInput);
    await usuario.type(montoInput, "40.00");

    expect(screen.getByText("60.00")).toBeInTheDocument();
    expect(screen.getByText("TOTAL DE LA ORDEN: 40.00 USD")).toBeInTheDocument();
  });

  it("muestra error de exceso y deshabilita guardar cuando el monto supera el pendiente", async () => {
    apiFetchMock.mockResolvedValueOnce(crearOpciones());

    renderPagina();
    const usuario = userEvent.setup();

    const checkbox = await screen.findByRole("checkbox", { name: "Seleccionar causado CAU-2026-00001" });
    await usuario.click(checkbox);

    const montoInput = await screen.findByRole("textbox", { name: "Monto a ordenar de CAU-2026-00001" });
    await usuario.clear(montoInput);
    await usuario.type(montoInput, "150.00");

    expect(await screen.findByText("Supera el pendiente de la línea")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Guardar borrador" })).toBeDisabled();
  });

  it("suma el total de dos causados compatibles sin aviso", async () => {
    const opciones = crearOpciones({
      obligaciones: [
        crearObligacion({ id: "c1", codigo: "CAU-2026-00001", pendiente_de_ordenar: "60.00" }),
        crearObligacion({ id: "c2", codigo: "CAU-2026-00002", pendiente_de_ordenar: "40.00" }),
      ],
    });

    apiFetchMock.mockResolvedValueOnce(opciones);

    renderPagina();
    const usuario = userEvent.setup();

    const checkbox1 = await screen.findByRole("checkbox", { name: "Seleccionar causado CAU-2026-00001" });
    const checkbox2 = await screen.findByRole("checkbox", { name: "Seleccionar causado CAU-2026-00002" });
    await usuario.click(checkbox1);
    await usuario.click(checkbox2);

    expect(screen.getByText("TOTAL DE LA ORDEN: 100.00 USD")).toBeInTheDocument();
    expect(screen.queryByText("Las obligaciones seleccionadas tienen beneficiarios distintos")).not.toBeInTheDocument();
    expect(screen.queryByText("Las obligaciones seleccionadas tienen monedas distintas")).not.toBeInTheDocument();
  });

  it("muestra aviso de beneficiarios distintos y deshabilita guardar", async () => {
    const opciones = crearOpciones({
      obligaciones: [
        crearObligacion({ id: "c1", codigo: "CAU-2026-00001", beneficiario: "Proveedor Uno" }),
        crearObligacion({ id: "c2", codigo: "CAU-2026-00002", beneficiario: "Proveedor Dos" }),
      ],
    });

    apiFetchMock.mockResolvedValueOnce(opciones);

    renderPagina();
    const usuario = userEvent.setup();

    const checkbox1 = await screen.findByRole("checkbox", { name: "Seleccionar causado CAU-2026-00001" });
    const checkbox2 = await screen.findByRole("checkbox", { name: "Seleccionar causado CAU-2026-00002" });
    await usuario.click(checkbox1);
    await usuario.click(checkbox2);

    expect(screen.getByText("Las obligaciones seleccionadas tienen beneficiarios distintos")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Guardar borrador" })).toBeDisabled();
  });

  it("muestra aviso de monedas distintas", async () => {
    const opciones = crearOpciones({
      obligaciones: [
        crearObligacion({ id: "c1", codigo: "CAU-2026-00001", moneda: "USD" }),
        crearObligacion({ id: "c2", codigo: "CAU-2026-00002", moneda: "EUR" }),
      ],
    });

    apiFetchMock.mockResolvedValueOnce(opciones);

    renderPagina();
    const usuario = userEvent.setup();

    const checkbox1 = await screen.findByRole("checkbox", { name: "Seleccionar causado CAU-2026-00001" });
    const checkbox2 = await screen.findByRole("checkbox", { name: "Seleccionar causado CAU-2026-00002" });
    await usuario.click(checkbox1);
    await usuario.click(checkbox2);

    expect(screen.getByText("Las obligaciones seleccionadas tienen monedas distintas")).toBeInTheDocument();
  });

  it("guarda borrador y navega al detalle", async () => {
    const opciones = crearOpciones();
    const ordenGuardada: OrdenPago = {
      id: "o1",
      codigo: "BORRADOR-OP-0001",
      numero: null,
      huella: null,
      monto_pagado: "0.00",
      estado: "BORRADOR",
      version: 1,
      year_id: "y1",
      anio: 2026,
      fecha_orden: "2026-03-01",
      beneficiario: "Proveedor Uno",
      moneda: "USD",
      monto: "100.00",
      concepto: "Mantenimiento de equipos",
      policy: { id: "p1", codigo: "POL-OP-001", nombre: "Política de pagos", version: 1 },
      lineas: [],
      autoridad: {
        cargo_id: "r1",
        cargo: null,
        unidad: null,
        funcionario_id: null,
        funcionario: null,
        usuario_id: null,
      },
      documentos: [],
      controles: { controles: [], completo: false },
      historia: [],
      pendiente_de_pagar: "100.00",
      siguiente_paso: null,
      emitida_en: null,
      emitida_por: null,
      anulada_en: null,
      motivo_anulacion: null,
    };

    apiFetchMock.mockImplementation((ruta: string, opcionesFetch?: { method?: string; body?: unknown }) => {
      if (opcionesFetch?.method === "POST" && ruta === "/gobierno/tesoreria/ejercicios/y1/ordenes-pago") {
        return Promise.resolve(ordenGuardada);
      }
      if (ruta === "/gobierno/tesoreria/ejercicios/y1/ordenes-pago/opciones") {
        return Promise.resolve(opciones);
      }
      return Promise.reject(new Error(`Ruta no esperada: ${ruta}`));
    });

    renderPagina();
    const usuario = userEvent.setup();

    const checkbox = await screen.findByRole("checkbox", { name: "Seleccionar causado CAU-2026-00001" });
    await usuario.click(checkbox);

    await usuario.selectOptions(screen.getByLabelText("Política"), "p1");
    await usuario.type(screen.getByRole("textbox", { name: /^Concepto/ }), "Mantenimiento de equipos");
    await usuario.selectOptions(screen.getByLabelText("Cargo que ordena el pago"), "r1");
    await usuario.click(screen.getByLabelText("Documento Factura"));

    const botonGuardar = screen.getByRole("button", { name: "Guardar borrador" });
    expect(botonGuardar).toBeEnabled();
    await usuario.click(botonGuardar);

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        "/gobierno/tesoreria/ejercicios/y1/ordenes-pago",
        expect.objectContaining({
          method: "POST",
          body: expect.objectContaining({
            policy_id: "p1",
            concepto: "Mantenimiento de equipos",
            lineas: [{ cause_id: "c1", monto: "100.00" }],
            autoridad_cargo_id: "r1",
            documentos: ["d1"],
          }),
        }),
      );
    });

    expect(await screen.findByText("detalle-destino")).toBeInTheDocument();
  });

  it("muestra errores 422 del campo lineas", async () => {
    const opciones = crearOpciones();

    apiFetchMock.mockImplementation((ruta: string, opcionesFetch?: { method?: string }) => {
      if (opcionesFetch?.method === "POST" && ruta === "/gobierno/tesoreria/ejercicios/y1/ordenes-pago") {
        return Promise.reject(
          new ApiError(422, {
            code: "GOV_PAYMENT_ORDER_OVER_ORDER",
            message: "El monto de la línea del causado 2026-00001 supera el pendiente de ordenar",
            request_id: "r1",
            field_errors: { lineas: ["Pendiente de 2026-00001: 60.00"] },
          }),
        );
      }
      if (ruta === "/gobierno/tesoreria/ejercicios/y1/ordenes-pago/opciones") {
        return Promise.resolve(opciones);
      }
      return Promise.reject(new Error(`Ruta no esperada: ${ruta}`));
    });

    renderPagina();
    const usuario = userEvent.setup();

    const checkbox = await screen.findByRole("checkbox", { name: "Seleccionar causado CAU-2026-00001" });
    await usuario.click(checkbox);
    await usuario.selectOptions(screen.getByLabelText("Política"), "p1");
    await usuario.type(screen.getByRole("textbox", { name: /^Concepto/ }), "Mantenimiento de equipos");
    await usuario.selectOptions(screen.getByLabelText("Cargo que ordena el pago"), "r1");
    await usuario.click(screen.getByRole("button", { name: "Guardar borrador" }));

    expect(await screen.findByText("El monto de la línea del causado 2026-00001 supera el pendiente de ordenar")).toBeInTheDocument();
    expect(screen.getByText("Pendiente de 2026-00001: 60.00")).toBeInTheDocument();
  });

  it("muestra No tiene permiso para preparar órdenes de pago ante 403", async () => {
    apiFetchMock.mockImplementation((ruta: string, opcionesFetch?: { method?: string }) => {
      if (opcionesFetch?.method === "POST" && ruta === "/gobierno/tesoreria/ejercicios/y1/ordenes-pago") {
        return Promise.reject(
          new ApiError(403, {
            code: "GOV_FORBIDDEN",
            message: "Prohibido",
            request_id: "r1",
          }),
        );
      }
      if (ruta === "/gobierno/tesoreria/ejercicios/y1/ordenes-pago/opciones") {
        return Promise.resolve(crearOpciones());
      }
      return Promise.reject(new Error(`Ruta no esperada: ${ruta}`));
    });

    renderPagina();
    const usuario = userEvent.setup();

    const checkbox = await screen.findByRole("checkbox", { name: "Seleccionar causado CAU-2026-00001" });
    await usuario.click(checkbox);
    await usuario.selectOptions(screen.getByLabelText("Política"), "p1");
    await usuario.type(screen.getByRole("textbox", { name: /^Concepto/ }), "Mantenimiento de equipos");
    await usuario.selectOptions(screen.getByLabelText("Cargo que ordena el pago"), "r1");
    await usuario.click(screen.getByRole("button", { name: "Guardar borrador" }));

    expect(await screen.findByText("No tiene permiso para preparar órdenes de pago")).toBeInTheDocument();
  });

  it("muestra permiso denegado sin pedir opciones cuando falta manage", async () => {
    capacidades = new Set(["gobierno_ordenes_pago:view"]);

    renderPagina();

    expect(await screen.findByText("No tiene permiso para preparar órdenes de pago")).toBeInTheDocument();
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("lista documentos exigidos de la política al elegirla", async () => {
    const opciones = crearOpciones({
      politicas: [
        {
          id: "p2",
          codigo: "POL-OP-002",
          nombre: "Política con documentos",
          tipo_gasto: "Servicios",
          documentos: [
            {
              document_type_id: "dt1",
              nombre: "Documento exigido A",
              tipo: "factura",
              obligatorio: true,
              etapa: "previa",
            },
          ],
        },
      ],
    });

    apiFetchMock.mockResolvedValueOnce(opciones);

    renderPagina();
    const usuario = userEvent.setup();

    await screen.findByLabelText("Política");
    await usuario.selectOptions(screen.getByLabelText("Política"), "p2");

    expect(await screen.findByText("Documentos exigidos")).toBeInTheDocument();
    expect(screen.getByText(/Documento exigido A/)).toBeInTheDocument();
  });
});
