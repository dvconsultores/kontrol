import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
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

vi.mock("@/app/contexts/NotificationContext", () => ({
  useNotifications: () => ({ notify: vi.fn() }),
}));

import { OfertaMonto, type OfertaConMonto } from "./OfertaMonto";

function crearOfertaBase(): OfertaConMonto {
  return {
    id: "of1",
    referencia: "REF-001",
    monto_estado: "NO_DECLARADO",
    monto_estado_etiqueta: "No declarado",
    monto: null,
    monto_bloqueo: null,
    montos_historial: [],
    soportes_monto: [],
  };
}

function renderOfertaMonto(oferta: OfertaConMonto) {
  const queryClient = new QueryClient();
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <OfertaMonto
          oferta={oferta}
          expedienteId="exp1"
          version={7}
          activeCompanyId="c1"
        />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("OfertaMonto", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    capacidades = new Set<string>([
      "gobierno_expedientes:view",
      "gobierno_ofertas:amount",
    ]);
  });

  it("muestra el monto declarado con total, soporte y nota de diferencia", () => {
    const oferta = crearOfertaBase();
    oferta.monto_estado = "DECLARADO";
    oferta.monto_estado_etiqueta = "Declarado";
    oferta.monto = {
      version: 1,
      moneda: "VES",
      monto_sin_iva: "1000.00",
      tributos: "160.00",
      total_con_tributos: "1170.00",
      suma_coincide: false,
      diferencia: "10.00",
      soporte_tipo: "DOCUMENTO_OFERTA",
      soporte_etiqueta: "Oferta firmada",
      soporte_titulo: "oferta.pdf",
      soporte_version: 2,
      soporte_huella: "abc",
      motivo: null,
      registrada_por: "Ana",
      registrada_en: "2025-01-01T10:00:00Z",
    };
    oferta.montos_historial = [oferta.monto];

    renderOfertaMonto(oferta);

    expect(screen.getByText("1170.00 VES")).toBeInTheDocument();
    expect(
      screen.getByText(/Oferta firmada · oferta\.pdf · Versión 2/),
    ).toBeInTheDocument();
    expect(screen.getByRole("note")).toHaveTextContent(
      "La suma declarada no coincide con el total (diferencia 10.00 VES).",
    );
  });

  it("muestra el bloqueo y no muestra botón de declarar/corregir", () => {
    const oferta = crearOfertaBase();
    oferta.monto_bloqueo =
      "La evaluación está concluida: el monto ya no se registra ni se corrige";

    renderOfertaMonto(oferta);

    expect(
      screen.getByText(
        "La evaluación está concluida: el monto ya no se registra ni se corrige",
      ),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Declarar monto de REF-001" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Corregir monto de REF-001" }),
    ).not.toBeInTheDocument();
  });

  it("sin permiso gobierno_ofertas:amount no muestra botón", () => {
    capacidades.delete("gobierno_ofertas:amount");
    const oferta = crearOfertaBase();

    renderOfertaMonto(oferta);

    expect(
      screen.queryByRole("button", { name: "Declarar monto de REF-001" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Corregir monto de REF-001" }),
    ).not.toBeInTheDocument();
  });

  it("declara el monto por primera vez", async () => {
    const oferta = crearOfertaBase();
    oferta.soportes_monto = [
      {
        tipo: "DOCUMENTO_OFERTA",
        etiqueta: "Oferta firmada",
        documento_id: "d1",
        titulo: "oferta.pdf",
        version: 1,
      },
    ];
    apiFetchMock.mockResolvedValue({});

    renderOfertaMonto(oferta);
    const usuario = userEvent.setup();

    await usuario.click(
      screen.getByRole("button", { name: "Declarar monto de REF-001" }),
    );
    await usuario.type(
      screen.getByLabelText("Monto del objeto sin IVA"),
      "1000.00",
    );
    await usuario.type(screen.getByLabelText("Tributos"), "160.00");
    await usuario.type(screen.getByLabelText("Total con tributos"), "1160.00");
    await usuario.selectOptions(
      screen.getByLabelText("Documento soporte"),
      "DOCUMENTO_OFERTA|d1",
    );
    await usuario.click(screen.getByRole("button", { name: "Registrar monto" }));

    expect(apiFetchMock).toHaveBeenCalledWith(
      "/gobierno/contrataciones/expedientes/exp1/ofertas/of1/montos",
      expect.objectContaining({
        method: "POST",
        body: {
          moneda: "VES",
          monto_sin_iva: "1000.00",
          tributos: "160.00",
          total_con_tributos: "1160.00",
          soporte_tipo: "DOCUMENTO_OFERTA",
          soporte_documento_id: "d1",
          motivo: null,
          version_anterior: null,
        },
        ifMatch: "7",
      }),
    );
  });

  it("corrige el monto con motivo y versión anterior", async () => {
    const oferta = crearOfertaBase();
    oferta.monto_estado = "DECLARADO";
    oferta.monto_estado_etiqueta = "Declarado";
    oferta.monto = {
      version: 1,
      moneda: "VES",
      monto_sin_iva: "1000.00",
      tributos: "160.00",
      total_con_tributos: "1160.00",
      suma_coincide: true,
      diferencia: "0.00",
      soporte_tipo: "DOCUMENTO_OFERTA",
      soporte_etiqueta: "Oferta firmada",
      soporte_titulo: "oferta.pdf",
      soporte_version: 1,
      soporte_huella: "abc",
      motivo: null,
      registrada_por: "Ana",
      registrada_en: "2025-01-01T10:00:00Z",
    };
    oferta.soportes_monto = [
      {
        tipo: "DOCUMENTO_OFERTA",
        etiqueta: "Oferta firmada",
        documento_id: "d1",
        titulo: "oferta.pdf",
        version: 2,
      },
    ];
    apiFetchMock.mockResolvedValue({});

    renderOfertaMonto(oferta);
    const usuario = userEvent.setup();

    await usuario.click(
      screen.getByRole("button", { name: "Corregir monto de REF-001" }),
    );
    await usuario.selectOptions(
      screen.getByLabelText("Documento soporte"),
      "DOCUMENTO_OFERTA|d1",
    );
    const botonRegistrar = screen.getByRole("button", {
      name: "Registrar monto",
    });
    expect(botonRegistrar).toBeDisabled();

    await usuario.type(
      screen.getByLabelText("Motivo de la corrección"),
      "Error de transcripción",
    );
    expect(botonRegistrar).toBeEnabled();
    await usuario.click(botonRegistrar);

    expect(apiFetchMock).toHaveBeenCalledWith(
      "/gobierno/contrataciones/expedientes/exp1/ofertas/of1/montos",
      expect.objectContaining({
        method: "POST",
        body: expect.objectContaining({
          motivo: "Error de transcripción",
          version_anterior: 1,
        }),
        ifMatch: "7",
      }),
    );
  });

  it("muestra el historial del monto", () => {
    const oferta = crearOfertaBase();
    oferta.monto_estado = "DECLARADO";
    oferta.monto_estado_etiqueta = "Declarado";
    oferta.monto = {
      version: 2,
      moneda: "VES",
      monto_sin_iva: "1000.00",
      tributos: "160.00",
      total_con_tributos: "1160.00",
      suma_coincide: true,
      diferencia: "0.00",
      soporte_tipo: "DOCUMENTO_OFERTA",
      soporte_etiqueta: "Oferta firmada",
      soporte_titulo: "oferta.pdf",
      soporte_version: 2,
      soporte_huella: "abc",
      motivo: null,
      registrada_por: "Ana",
      registrada_en: "2025-01-02T10:00:00Z",
    };
    oferta.montos_historial = [
      oferta.monto,
      {
        version: 1,
        moneda: "VES",
        monto_sin_iva: "900.00",
        tributos: "144.00",
        total_con_tributos: "1044.00",
        suma_coincide: true,
        diferencia: "0.00",
        soporte_tipo: "DOCUMENTO_OFERTA",
        soporte_etiqueta: "Oferta firmada",
        soporte_titulo: "oferta.pdf",
        soporte_version: 1,
        soporte_huella: "abc",
        motivo: "Error de transcripción",
        registrada_por: "Luis",
        registrada_en: "2025-01-01T10:00:00Z",
      },
    ];

    renderOfertaMonto(oferta);

    expect(screen.getByText("Historial del monto")).toBeInTheDocument();
    expect(
      screen.getByText(/Motivo: Error de transcripción/),
    ).toBeInTheDocument();
  });
});
