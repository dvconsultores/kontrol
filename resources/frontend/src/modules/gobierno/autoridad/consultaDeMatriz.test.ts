import { describe, expect, it } from "vitest";

import { consultaDeMatriz } from "@/modules/gobierno/api";

describe("consultaDeMatriz", () => {
  it("CDM-01 · sin filtros ni extra devuelve cadena vacía", () => {
    expect(consultaDeMatriz({})).toBe("");
  });

  it("CDM-02 · usa el orden fecha, unidad, cargo, accion, materia, texto y omite los vacíos", () => {
    expect(
      consultaDeMatriz({
        texto: "  compras ",
        accion: "PAGAR",
        fecha: "2026-02-15",
        unidad_id: "",
        materia: "",
      }),
    ).toBe("?fecha=2026-02-15&accion=PAGAR&texto=compras");
  });

  it("CDM-03 · añade los extra en el orden recibido", () => {
    expect(
      consultaDeMatriz({ cargo_id: "c1" }, { pagina: 2, por_pagina: 50 }),
    ).toBe("?cargo_id=c1&pagina=2&por_pagina=50");
  });

  it("CDM-04 · solo espacios en texto se omiten", () => {
    expect(consultaDeMatriz({ texto: "   " })).toBe("");
  });
});
