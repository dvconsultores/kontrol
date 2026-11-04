import { describe, expect, it } from "vitest";

import {
  consultaDeAuditoria,
  filtrosLimpios,
} from "@/modules/gobierno/api";

describe("consultaDeAuditoria", () => {
  it("CDA-01 · sin filtros ni paginación devuelve cadena vacía", () => {
    expect(consultaDeAuditoria({})).toBe("");
  });

  it("CDA-02 · usa el orden desde, hasta, proceso, accion, usuario, texto y omite los vacíos", () => {
    expect(
      consultaDeAuditoria({
        texto: "  cargo ",
        proceso: "ORG-03",
        desde: "2026-01-01",
        accion: "",
        usuario: " ua ",
      }),
    ).toBe("?desde=2026-01-01&proceso=ORG-03&usuario=ua&texto=cargo");
  });

  it("CDA-03 · añade la paginación en el orden recibido", () => {
    expect(
      consultaDeAuditoria(
        { hasta: "2026-01-31" },
        { pagina: 2, por_pagina: 50 },
      ),
    ).toBe("?hasta=2026-01-31&pagina=2&por_pagina=50");
  });

  it("CDA-04 · solo espacios en texto y usuario se omiten", () => {
    expect(consultaDeAuditoria({ texto: "   ", usuario: "  " })).toBe("");
  });

  it("CDA-05 · filtrosLimpios conserva solo las claves no vacías y recorta texto", () => {
    expect(
      filtrosLimpios({ desde: "2026-01-01", proceso: "", texto: "  x " }),
    ).toEqual({ desde: "2026-01-01", texto: "x" });
  });
});
