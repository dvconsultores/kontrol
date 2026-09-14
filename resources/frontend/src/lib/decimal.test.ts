/** Spec 038 · FLOAT-038-A — el importe se normaliza como texto, nunca como `Number`. */
import { describe, expect, it } from "vitest";

import { toDecimalString } from "./decimal";

describe("toDecimalString", () => {
  it("conserva un importe que un double de JavaScript no puede representar", () => {
    // Lo que haría `Number`: el importe ya no es el que escribió el usuario.
    expect(String(Number("1234567890123456.78"))).toBe("1234567890123456.8");
    expect(toDecimalString("1234567890123456.78")).toBe("1234567890123456.78");
  });

  it("normaliza a dos decimales sin redondear", () => {
    expect(toDecimalString("10")).toBe("10.00");
    expect(toDecimalString("10.5")).toBe("10.50");
    expect(toDecimalString("0.01")).toBe("0.01");
    expect(toDecimalString("001.20")).toBe("1.20");
    expect(toDecimalString("1234,56")).toBe("1234.56");
    expect(toDecimalString(" 7.25 ")).toBe("7.25");
  });

  it("rechaza más decimales que la escala en vez de redondearlos", () => {
    expect(toDecimalString("0.001")).toBeNull();
    expect(toDecimalString("0.005")).toBeNull();
    expect(toDecimalString("10.000")).toBeNull();
  });

  it("rechaza lo que no es un decimal sin signo", () => {
    for (const entrada of ["", "abc", "1e3", "NaN", "Infinity", "-1.00", "+1", "1.000,00", "1 000", ".5"]) {
      expect(toDecimalString(entrada), entrada).toBeNull();
    }
  });
});
