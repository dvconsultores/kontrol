/** Spec 001 · POLICY-CLOCK-LOCAL — el navegador deja de decidir el día de negocio. */
import { describe, expect, it } from "vitest";

import {
  FECHA_INVALIDA,
  SIN_VALOR,
  ZONA_DE_NEGOCIO,
  fechaDeNegocioDeInstante,
  finDelDiaDeNegocio,
  formatearFechaDeInstante,
  formatearFechaDeNegocio,
  formatearInstante,
  horaDeCaracasParaInput,
  hoyDeNegocio,
  instanteDesdeHoraDeCaracas,
} from "./fecha-de-negocio";

/** El instante de la auditoría: en UTC es el 17; en Caracas, todavía el 16. */
const INSTANTE = new Date("2026-09-17T02:36:00Z");

/** Fuerza la zona horaria del proceso durante una prueba. */
function bajo(zona: string, fn: () => void): void {
  const previa = process.env.TZ;
  process.env.TZ = zona;
  try {
    fn();
  } finally {
    if (previa === undefined) {
      delete process.env.TZ;
    } else {
      process.env.TZ = previa;
    }
  }
}

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

describe("presentación en Caracas sin depender de la zona del navegador", () => {
  it.each(["UTC", "America/Caracas", "Asia/Tokyo", "Pacific/Kiritimati"])(
    "formatea y convierte en la zona %s",
    (zona) => {
      bajo(zona, () => {
        expect(formatearFechaDeInstante("2026-10-28T03:30:00Z")).toBe(
          "27/10/2026",
        );
        expect(formatearInstante("2026-10-28T03:30:00Z")).toContain(
          "27/10/2026",
        );
        expect(formatearInstante("2026-10-28T03:30:00Z")).toContain("11:30");
        expect(fechaDeNegocioDeInstante("2026-10-28T03:30:00Z")).toBe(
          "2026-10-27",
        );
        expect(instanteDesdeHoraDeCaracas("2026-10-27T23:30")).toBe(
          "2026-10-28T03:30:00.000Z",
        );
        expect(horaDeCaracasParaInput(new Date("2026-10-28T03:30:00Z"))).toBe(
          "2026-10-27T23:30",
        );
        expect(finDelDiaDeNegocio("2026-10-27")).toBe(
          "2026-10-28T03:59:59.999Z",
        );
      });
    },
  );
});

describe("formatearFechaDeNegocio", () => {
  it("convierte fecha de negocio al formato de pantalla", () => {
    expect(formatearFechaDeNegocio("2026-10-27")).toBe("27/10/2026");
  });

  it("devuelve SIN_VALOR para entradas inválidas", () => {
    expect(formatearFechaDeNegocio("")).toBe(SIN_VALOR);
    expect(formatearFechaDeNegocio(null)).toBe(SIN_VALOR);
    expect(formatearFechaDeNegocio("27/10/2026")).toBe(SIN_VALOR);
  });
});

describe("formatearInstante con valores inválidos", () => {
  it("devuelve SIN_VALOR para nulo o vacío", () => {
    expect(formatearInstante(null)).toBe(SIN_VALOR);
    expect(formatearInstante("")).toBe(SIN_VALOR);
  });

  it("devuelve FECHA_INVALIDA para un valor no vacío que no es un instante", () => {
    expect(formatearInstante("no-es-fecha")).toBe(FECHA_INVALIDA);
  });
});

describe("formatearFechaDeInstante con valores inválidos", () => {
  it("devuelve SIN_VALOR para nulo o vacío", () => {
    expect(formatearFechaDeInstante(null)).toBe(SIN_VALOR);
    expect(formatearFechaDeInstante("")).toBe(SIN_VALOR);
  });

  it("devuelve FECHA_INVALIDA para un valor no vacío que no es un instante", () => {
    expect(formatearFechaDeInstante("no-es-fecha")).toBe(FECHA_INVALIDA);
  });
});

describe("fechaDeNegocioDeInstante con valores inválidos", () => {
  it("devuelve SIN_VALOR para nulo o vacío", () => {
    expect(fechaDeNegocioDeInstante(null)).toBe(SIN_VALOR);
    expect(fechaDeNegocioDeInstante("")).toBe(SIN_VALOR);
  });

  it("devuelve FECHA_INVALIDA para un valor no vacío que no es un instante", () => {
    expect(fechaDeNegocioDeInstante("no-es-fecha")).toBe(FECHA_INVALIDA);
  });
});

describe("instanteDesdeHoraDeCaracas", () => {
  it("respeta la transición de hora legal de 2016", () => {
    expect(instanteDesdeHoraDeCaracas("2016-04-30T12:00")).toBe(
      "2016-04-30T16:30:00.000Z",
    );
    expect(instanteDesdeHoraDeCaracas("2016-05-02T12:00")).toBe(
      "2016-05-02T16:00:00.000Z",
    );
  });

  it("rechaza formatos que no son hora local", () => {
    expect(instanteDesdeHoraDeCaracas("2026-10-27")).toBeNull();
    expect(instanteDesdeHoraDeCaracas("27/10/2026 10:00")).toBeNull();
  });

  it("no usa desfase fijo: cubre el cambio de 2007", () => {
    expect(instanteDesdeHoraDeCaracas("2007-12-01T12:00")).toBe(
      "2007-12-01T16:00:00.000Z",
    );
  });
});
