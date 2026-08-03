import { describe, expect, it } from "vitest";

import { formatMoney, toScaledInt } from "./format";

describe("formatMoney", () => {
  it("aplica separador de miles y decimales", () => {
    expect(formatMoney("1234567.89")).toBe("1.234.567,89");
  });

  it("maneja enteros", () => {
    expect(formatMoney("1000")).toBe("1.000");
  });
});

describe("toScaledInt", () => {
  it("convierte string decimal a entero de escala sin flotantes", () => {
    expect(toScaledInt("123.45")).toBe(12345);
    expect(toScaledInt("0.01")).toBe(1);
  });

  it("trunca decimales extra", () => {
    expect(toScaledInt("1.9999", 2)).toBe(199);
  });
});
