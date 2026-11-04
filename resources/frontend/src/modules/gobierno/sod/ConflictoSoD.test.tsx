import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";

import { ConflictoSoD, detalleDeConflictoSod } from "./ConflictoSoD";

describe("detalleDeConflictoSod", () => {
  it("CSD-01 · devuelve null para un Error común, ApiError 409 con otro code y ApiError 422 con code GOV_SOD_CONFLICT", () => {
    expect(detalleDeConflictoSod(new Error("boom"))).toBeNull();
    expect(
      detalleDeConflictoSod(
        new ApiError(409, { code: "OTRO_CODE", message: "otro" }),
      ),
    ).toBeNull();
    expect(
      detalleDeConflictoSod(
        new ApiError(422, { code: "GOV_SOD_CONFLICT", message: "otro" }),
      ),
    ).toBeNull();
  });

  it("CSD-02 · extrae regla_codigo y valores string; ignora objeto_id no string y claves ausentes", () => {
    const detalle = detalleDeConflictoSod(
      new ApiError(409, {
        code: "GOV_SOD_CONFLICT",
        message: "conflicto",
        details: {
          regla_codigo: "SOD-2026-0001",
          regla_nombre: "Registro y recomendación",
          accion_etiqueta: "Añadir una recomendación",
          accion_previa_etiqueta: "Registrar el hallazgo",
          objeto_id: 7,
        },
      }),
    );

    expect(detalle?.regla_codigo).toBe("SOD-2026-0001");
    expect(detalle?.objeto_id).toBe("");
    expect(detalle?.accion).toBe("");
    expect(detalle?.previa_en).toBe("");
  });
});

describe("ConflictoSoD", () => {
  it("CSD-03 · muestra el alert con el detalle y el botón Entendido llama a onCerrar una vez", async () => {
    const onCerrar = vi.fn();
    const detalle = {
      regla_codigo: "SOD-2026-0001",
      regla_nombre: "Registro y recomendación",
      accion: "",
      accion_etiqueta: "Añadir una recomendación",
      accion_previa: "",
      accion_previa_etiqueta: "Registrar el hallazgo",
      objeto_tipo: "",
      objeto_id: "",
      previa_en: "",
    };

    render(<ConflictoSoD detalle={detalle} onCerrar={onCerrar} />);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(
      "Operación bloqueada por segregación de funciones",
    );
    expect(alert).toHaveTextContent("Registrar el hallazgo");
    expect(alert).toHaveTextContent("SOD-2026-0001");
    expect(alert).toHaveTextContent("Pida a otro usuario autorizado");

    await userEvent.click(screen.getByRole("button", { name: "Entendido" }));
    expect(onCerrar).toHaveBeenCalledTimes(1);
  });
});
