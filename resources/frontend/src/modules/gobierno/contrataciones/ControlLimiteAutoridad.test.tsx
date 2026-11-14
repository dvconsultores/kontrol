import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ControlLimiteAutoridad, type ControlMonto } from "./ControlLimiteAutoridad";

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
});
