import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ControlLimiteAutoridad, ConversionAutoridad, type ControlMonto } from "./ControlLimiteAutoridad";
import { expresionTasa } from "../tesoreria/tasas/api";
import type { ConversionLimite } from "../presupuesto/api";

function base(): ControlMonto {
  return {
    offer_id: "3f2c9a10-8b1e-4c55-9d7a-0e1f2a3b4c5d",
    oferta: "O-01",
    cargo: "Director General",
    estado: "EXCEDE_LIMITE",
    estado_etiqueta: "Excede el límite",
    permite: false,
    mensaje:
      "El total declarado de la oferta (50000.01 USD) excede el límite de aprobación de Director General (50000.00 USD). Use el acto de una autoridad con límite suficiente.",
    monto_oferta: { total_con_tributos: "50000.01", moneda: "USD" },
    limite: {
      cargo: "Director General",
      tipo_limite: "MONTO",
      monto: "50000.00",
      moneda: "USD",
      etiqueta: "50000.00 USD",
    },
  };
}

describe("ControlLimiteAutoridad", () => {
  it("muestra el caso «excede el límite»", () => {
    render(<ControlLimiteAutoridad control={base()} />);

    expect(
      screen.getByRole("region", { name: "Control del límite de autoridad" }),
    ).toBeTruthy();
    expect(screen.getByText("Monto declarado de la oferta", { exact: true })).toBeTruthy();
    expect(screen.getByText("50000.01", { exact: true })).toBeTruthy();
    expect(screen.getByText("USD", { exact: true })).toBeTruthy();
    expect(screen.getByText("Director General", { exact: true })).toBeTruthy();
    expect(screen.getByText("50000.00 USD", { exact: true })).toBeTruthy();
    expect(screen.getByText("Excede el límite", { exact: true })).toBeTruthy();
    expect(
      screen.getByText(
        "El total declarado de la oferta (50000.01 USD) excede el límite de aprobación de Director General (50000.00 USD). Use el acto de una autoridad con límite suficiente.",
        { exact: true },
      ),
    ).toBeTruthy();
    expect(screen.queryByRole("alert")).toBeNull();
    expect(document.body.textContent).not.toContain("3f2c9a10-8b1e-4c55-9d7a-0e1f2a3b4c5d");
  });

  it("muestra el caso «sin límite»", () => {
    const control: ControlMonto = {
      ...base(),
      estado: "SIN_LIMITE",
      estado_etiqueta: "Sin límite",
      permite: true,
      mensaje: "Director General aprueba contrataciones sin límite de monto.",
      monto_oferta: { total_con_tributos: "500000.00", moneda: "USD" },
      limite: {
        cargo: "Director General",
        tipo_limite: "SIN_LIMITE",
        monto: null,
        moneda: null,
        etiqueta: "Sin límite",
      },
    };

    render(<ControlLimiteAutoridad control={control} />);

    expect(screen.getAllByText("Sin límite", { exact: true })).toHaveLength(2);
    expect(
      screen.getByText("Director General aprueba contrataciones sin límite de monto.", { exact: true }),
    ).toBeTruthy();
  });

  it("muestra el caso «monto no declarado»", () => {
    const control: ControlMonto = {
      ...base(),
      monto_oferta: null,
      estado: "MONTO_NO_DECLARADO",
      estado_etiqueta: "Monto no declarado",
      permite: false,
      mensaje:
        "La oferta no tiene monto declarado y Director General tiene un límite de aprobación de 50000.00 USD. Sin el monto no puede verificarse el límite: use una autoridad sin límite.",
    };

    render(<ControlLimiteAutoridad control={control} />);

    expect(screen.getByText("No declarado", { exact: true })).toBeTruthy();
    expect(screen.getByText("—", { exact: true })).toBeTruthy();
    expect(screen.getByText("Monto no declarado", { exact: true })).toBeTruthy();
  });

  it("muestra la tasa oficial y los equivalentes cuando hay conversión", () => {
    const control: ControlMonto = {
      ...base(),
      estado: "DENTRO_LIMITE",
      estado_etiqueta: "Dentro del límite",
      permite: true,
      mensaje: "Dentro con tasa",
      limite: {
        ...base().limite,
        monto: "36123.82",
        moneda: "VES",
        etiqueta: "36123.82 VES",
      },
      conversion: conversionBase(),
      monedas_sin_tasa: [],
    };

    render(<ControlLimiteAutoridad control={control} />);

    expect(
      screen.getByRole("heading", { name: "Tasa oficial BCV utilizada" }),
    ).toBeTruthy();
    expect(screen.getByText("Tasa oficial USD", { exact: true })).toBeTruthy();
    expect(
      screen.getByText((_, el) =>
        el?.tagName === "DD" &&
        (el.textContent ?? "").startsWith(expresionTasa(conversionBase().tasas[0])),
      ),
    ).toBeTruthy();
    expect(
      screen.getByText("BCV · BCV · tipo de cambio oficial de referencia", { exact: true }),
    ).toBeTruthy();
    expect(screen.getByText("Equivalente de la oferta", { exact: true })).toBeTruthy();
    expect(document.body.textContent).not.toContain("9d1e2f30-4a5b-4c6d-8e7f-0a1b2c3d4e5f");
  });

  it("sin tasa: muestra el estado y no muestra conversión", () => {
    const control: ControlMonto = {
      ...base(),
      estado: "SIN_TASA",
      estado_etiqueta: "Sin tasa oficial aprobada",
      permite: false,
      mensaje:
        "No hay tasa oficial BCV aprobada aplicable al 15/11/2026 para USD, EUR: la oferta está en USD y el límite de Director General es 60000.00 EUR. Registre y apruebe la tasa en Tesorería → Tasas oficiales.",
      conversion: null,
      monedas_sin_tasa: ["USD", "EUR"],
    };

    render(<ControlLimiteAutoridad control={control} />);

    expect(screen.getByText("Sin tasa oficial aprobada", { exact: true })).toBeTruthy();
    expect(
      screen.getByText(
        "No hay tasa oficial BCV aprobada aplicable al 15/11/2026 para USD, EUR: la oferta está en USD y el límite de Director General es 60000.00 EUR. Registre y apruebe la tasa en Tesorería → Tasas oficiales.",
        { exact: true },
      ),
    ).toBeTruthy();
    expect(
      screen.queryByRole("heading", { name: "Tasa oficial BCV utilizada" }),
    ).toBeNull();
  });

  it("ConversionAutoridad muestra el título dado", () => {
    render(
      <ConversionAutoridad
        conversion={conversionBase()}
        titulo="Conversión de autoridad de DEC-01"
      />,
    );

    expect(
      screen.getByRole("heading", { name: "Conversión de autoridad de DEC-01" }),
    ).toBeTruthy();
    expect(screen.getByText("Fecha de la autoridad", { exact: true })).toBeTruthy();
    expect(screen.getByText("Equivalente del límite", { exact: true })).toBeTruthy();
  });
});

function conversionBase(): ConversionLimite {
  return {
    requiere_conversion: true,
    moneda_operacion: "USD",
    moneda_limite: "VES",
    fecha: "2026-11-15",
    tasas: [
      {
        tasa_id: "9d1e2f30-4a5b-4c6d-8e7f-0a1b2c3d4e5f",
        moneda: "USD",
        moneda_cotizacion: "VES",
        fecha_efectiva: "2026-11-10",
        valor: "36.123456789012",
        fuente: "BCV",
        fuente_referencia: "BCV · tipo de cambio oficial de referencia",
        version: 2,
        evidencia_sha256: "a".repeat(64),
      },
    ],
    total: "1000.01",
    limite: "36123.82",
    total_ves: "36123.81802357989012",
    limite_ves: "36123.82",
    dentro_del_limite: true,
    resultado: "DENTRO_DEL_LIMITE",
    monedas_sin_tasa: [],
  };
}
