/**
 * Spec 018 · §3: la condición del proceso se muestra tal como la deriva el
 * backend. La pantalla no la recalcula ni traduce códigos por su cuenta.
 */
import { render, screen } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";

import type { ReceiptProcessCondition } from "@/api/types";

import { CondicionDelProceso } from "./CondicionDelProceso";

function condicion(parcial: Partial<ReceiptProcessCondition>): ReceiptProcessCondition {
  return {
    code: "PENDIENTE_DE_VALIDACION",
    label: "Pendiente de validación",
    blocking_incidents: 0,
    incidents: [],
    reason: "Falta confirmar el inventario de la recepción.",
    ...parcial,
  };
}

function montar(elemento: React.JSX.Element) {
  return render(<MemoryRouter>{elemento}</MemoryRouter>);
}

describe("Condición del proceso", () => {
  it("muestra el texto humano que publica el backend, no el código interno", () => {
    montar(<CondicionDelProceso condicion={condicion({})} receiptId="r-1" />);
    expect(screen.getByText("Pendiente de validación")).toBeInTheDocument();
    expect(screen.queryByText(/PENDIENTE_DE_VALIDACION/)).not.toBeInTheDocument();
    expect(screen.getByText("Falta confirmar el inventario de la recepción.")).toBeInTheDocument();
  });

  it("cuando está bloqueada explica por qué y lleva a la incidencia existente", () => {
    montar(
      <CondicionDelProceso
        condicion={condicion({
          code: "BLOQUEADO_POR_INCIDENCIA",
          label: "Bloqueado por incidencia",
          blocking_incidents: 2,
          incidents: [
            { id: "i-1", code: "INC-1" },
            { id: "i-2", code: "INC-2" },
          ],
          reason: "No se puede confirmar el inventario mientras existan incidencias sin resolver.",
        })}
        receiptId="r-9"
        importacionId="imp-3"
      />,
    );
    expect(screen.getByText("Bloqueado por incidencia")).toBeInTheDocument();
    expect(
      screen.getByText("No se puede confirmar el inventario mientras existan incidencias sin resolver."),
    ).toBeInTheDocument();
    const enlace = screen.getByRole("link", { name: "Ver las incidencias" });
    expect(enlace).toHaveAttribute("href", "/compras/incidencias?recepcion=r-9&importacion=imp-3");
    expect(screen.queryByText(/INCIDENTS_UNRESOLVED/)).not.toBeInTheDocument();
  });

  it("una recepción fuera del flujo normal no finge una condición", () => {
    montar(<CondicionDelProceso condicion={null} receiptId="r-2" />);
    expect(screen.getByText("—")).toBeInTheDocument();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });

  it("el componente no reimplementa la tabla de condiciones", () => {
    const fuente = readFileSync(resolve(__dirname, "CondicionDelProceso.tsx"), "utf8");
    for (const texto of ["Pendiente de validación", "Bloqueado por incidencia", "Recibido"]) {
      expect(fuente).not.toContain(`"${texto}"`);
    }
  });
});
