import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { DesactivarUnidad } from "./DesactivarUnidad";
import { Unidad } from "@/modules/gobierno/api";

const DA: Unidad = {
  id: "da",
  codigo: "DA-01",
  denominacion: "Dirección Administrativa",
  tipo: "UNIDAD_ADMINISTRATIVA",
  nivel: 1,
  estado: "ACTIVA",
  version: 1,
  unidad_superior_id: "desp",
  vigente_desde: "2026-01-01",
  vigente_hasta: null,
};

function montar() {
  const onConfirmar = vi.fn().mockResolvedValue(undefined);
  const onCancelar = vi.fn();
  render(
    <DesactivarUnidad
      unidad={DA}
      ejercicio={2026}
      onConfirmar={onConfirmar}
      onCancelar={onCancelar}
      erroresServidor={{}}
    />,
  );
  return { onConfirmar, onCancelar };
}

describe("DesactivarUnidad · estructura organizativa (GOV-0-02)", () => {
  it("GDU-01 · sin motivo no confirma y muestra el error", async () => {
    const { onConfirmar } = montar();
    await userEvent.click(
      screen.getByRole("button", { name: "Desactivar unidad" }),
    );
    expect(onConfirmar).not.toHaveBeenCalled();
    expect(
      screen.getByText("Indique el motivo (de 5 a 255 caracteres)"),
    ).toBeInTheDocument();
  });

  it("GDU-02 · con motivo confirma con la fecha por defecto de fin de ejercicio", async () => {
    const { onConfirmar } = montar();
    await userEvent.type(
      screen.getByLabelText(/^Motivo/),
      "Supresión del centro",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Desactivar unidad" }),
    );
    expect(onConfirmar).toHaveBeenCalledWith(
      "2026-12-31",
      "Supresión del centro",
    );
  });
});
