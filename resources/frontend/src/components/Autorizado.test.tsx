import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AutoridadContext } from "@/app/autoridad/AutoridadContext";
import type { AutoridadValue } from "@/app/autoridad/AutoridadContext";
import { Autorizado } from "@/components/Autorizado";

function crearAutoridad(
  puede: (metodo: string, ruta: string) => boolean,
): AutoridadValue {
  return {
    estado: "LISTA",
    puede,
    motivo: () => null,
    tiene: () => true,
    motivoDeCapacidad: () => null,
  };
}

describe("Autorizado", () => {
  it("pinta children cuando la operación está permitida", () => {
    const autoridad = crearAutoridad(() => true);

    render(
      <AutoridadContext.Provider value={autoridad}>
        <Autorizado operacion={["GET", "/empresas"]}>Contenido permitido</Autorizado>
      </AutoridadContext.Provider>,
    );

    expect(screen.getByText("Contenido permitido")).toBeTruthy();
  });

  it("oculta children cuando la operación no está permitida", () => {
    const autoridad = crearAutoridad(() => false);

    render(
      <AutoridadContext.Provider value={autoridad}>
        <Autorizado operacion={["POST", "/empresas"]}>Contenido prohibido</Autorizado>
      </AutoridadContext.Provider>,
    );

    expect(screen.queryByText("Contenido prohibido")).toBeNull();
  });

  it("muestra el fallback cuando la operación no está permitida", () => {
    const autoridad = crearAutoridad(() => false);

    render(
      <AutoridadContext.Provider value={autoridad}>
        <Autorizado
          operacion={["DELETE", "/empresas"]}
          fallback={<span>Fallback visible</span>}
        >
          Contenido prohibido
        </Autorizado>
      </AutoridadContext.Provider>,
    );

    expect(screen.getByText("Fallback visible")).toBeTruthy();
    expect(screen.queryByText("Contenido prohibido")).toBeNull();
  });
});
