/** Spec 001 · POLICY-CLOCK-LOCAL — el navegador deja de decidir el día de negocio. */
import { describe, expect, it } from "vitest";

import { hoyDeNegocio, ZONA_DE_NEGOCIO } from "./fecha-de-negocio";

/** El instante de la auditoría: en UTC es el 17; en Caracas, todavía el 16. */
const INSTANTE = new Date("2026-09-17T02:36:00Z");

describe("hoyDeNegocio", () => {
  it("devuelve el día de Caracas, no el de UTC", () => {
    expect(hoyDeNegocio(INSTANTE)).toBe("2026-09-16");
    // Lo que se enviaba antes: el día en UTC, ya en mañana.
    expect(INSTANTE.toISOString().slice(0, 10)).toBe("2026-09-17");
  });

  it("la frontera del día está donde dice Caracas", () => {
    expect(hoyDeNegocio(new Date("2026-09-17T03:59:00Z"))).toBe("2026-09-16");
    expect(hoyDeNegocio(new Date("2026-09-17T04:00:00Z"))).toBe("2026-09-17");
  });

  it("no depende de la zona del navegador porque la nombra explícitamente", () => {
    expect(ZONA_DE_NEGOCIO).toBe("America/Caracas");
    const enCaracas = new Intl.DateTimeFormat("en-CA", {
      timeZone: "America/Caracas", year: "numeric", month: "2-digit", day: "2-digit",
    }).format(INSTANTE);
    expect(hoyDeNegocio(INSTANTE)).toBe(enCaracas);
  });

  it("da formato ISO de fecha, que es lo que el servidor espera", () => {
    expect(hoyDeNegocio(INSTANTE)).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });
});
