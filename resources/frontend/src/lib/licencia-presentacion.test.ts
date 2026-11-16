import { describe, expect, it } from "vitest";
import {
  etiquetaDeModo,
  etiquetaDePerfil,
  etiquetaDeModulo,
  modulosDeDerechos,
  perfilDeModulos,
  textosDeActivacion,
  TOKENS_EMPRESARIALES,
} from "@/lib/licencia-presentacion";

describe("etiquetaDeModo", () => {
  it.each([
    ["PENDING", "Pendiente de activación"],
    ["FULL_ACCESS", "Acceso completo"],
    ["RENEWAL_NOTICE", "Renovación próxima"],
    ["CRITICAL_RENEWAL_NOTICE", "Renovación crítica"],
    ["READ_ONLY", "Solo consulta"],
    ["SECURITY_SUSPENSION", "Suspensión de seguridad"],
  ] as const)("traduce %s", (mode, etiqueta) => {
    expect(etiquetaDeModo(mode)).toBe(etiqueta);
  });

  it("desconocido conserva el código con espacios", () => {
    expect(etiquetaDeModo("OTRO_MODO")).toBe("OTRO MODO");
  });
});

describe("etiquetaDePerfil", () => {
  it.each([
    ["GOBIERNO", "KONTROL Gobierno"],
    ["MIXTO", "KONTROL Mixto"],
    ["EMPRESA", "KONTROL Enterprise"],
  ] as const)("traduce %s", (perfil, etiqueta) => {
    expect(etiquetaDePerfil(perfil)).toBe(etiqueta);
  });
});

describe("etiquetaDeModulo", () => {
  it.each([
    ["gobierno", "Gobierno"],
    ["ventas", "Ventas"],
    ["compras", "Compras"],
    ["inventario", "Inventario"],
    ["tesoreria", "Tesorería"],
    ["fiscal", "Fiscal"],
    ["regulatorio", "Regulatorio"],
    ["reportes", "Reportes"],
  ] as const)("traduce %s", (modulo, etiqueta) => {
    expect(etiquetaDeModulo(modulo)).toBe(etiqueta);
  });

  it("desconocido conserva el token", () => {
    expect(etiquetaDeModulo("nomina")).toBe("nomina");
  });
});

describe("modulosDeDerechos", () => {
  it("extrae de array", () => {
    expect(modulosDeDerechos({ modules: ["gobierno", "ventas"] })).toEqual(["gobierno", "ventas"]);
  });

  it("extrae de objeto con valores verdaderos", () => {
    expect(modulosDeDerechos({ modules: { gobierno: true, ventas: false } })).toEqual(["gobierno"]);
  });

  it("sin módulos", () => {
    expect(modulosDeDerechos({})).toEqual([]);
  });

  it("null", () => {
    expect(modulosDeDerechos(null)).toEqual([]);
  });

  it("entrada no estructurada", () => {
    expect(modulosDeDerechos("x")).toEqual([]);
  });

  it("mezcla de tokens válidos e inválidos", () => {
    expect(modulosDeDerechos({ modules: [1, "fiscal"] })).toEqual(["fiscal"]);
  });
});

describe("perfilDeModulos", () => {
  it("solo gobierno", () => {
    expect(perfilDeModulos(["gobierno"])).toBe("GOBIERNO");
  });

  it("gobierno y reportes es mixto", () => {
    expect(perfilDeModulos(["gobierno", "reportes"])).toBe("MIXTO");
  });

  it("solo ventas es empresa", () => {
    expect(perfilDeModulos(["ventas"])).toBe("EMPRESA");
  });

  it("vacío es empresa", () => {
    expect(perfilDeModulos([])).toBe("EMPRESA");
  });

  it("tokens no empresariales no cambian gobierno", () => {
    expect(perfilDeModulos(["gobierno", "nomina"])).toBe("GOBIERNO");
  });
});

describe("textosDeActivacion", () => {
  it.each([
    ["PENDING", "Activar licencia", "Seleccionar archivo de licencia", "Validar y activar licencia", true],
    ["FULL_ACCESS", "Actualizar o reemplazar licencia", "Seleccionar nueva licencia", "Validar y aplicar licencia", false],
    ["RENEWAL_NOTICE", "Renovar licencia", "Seleccionar licencia renovada", "Validar y aplicar licencia", true],
    ["CRITICAL_RENEWAL_NOTICE", "Renovar licencia", "Seleccionar licencia renovada", "Validar y aplicar licencia", true],
    ["READ_ONLY", "Reactivar licencia", "Seleccionar licencia vigente", "Validar y aplicar licencia", true],
    ["SECURITY_SUSPENSION", "Restablecer licencia válida", "Seleccionar licencia válida", "Validar y aplicar licencia", true],
  ] as const)("modo %s", (mode, titulo, seleccionar, aplicar, destacada) => {
    expect(textosDeActivacion(mode)).toEqual(expect.objectContaining({ titulo, seleccionar, aplicar, destacada }));
    expect(textosDeActivacion(mode).descripcion.length).toBeGreaterThan(20);
  });

  it("modo desconocido usa textos de FULL_ACCESS", () => {
    expect(textosDeActivacion("OTRO")).toEqual(textosDeActivacion("FULL_ACCESS"));
  });

  it("TOKENS_EMPRESARIALES incluye los módulos esperados", () => {
    expect([...TOKENS_EMPRESARIALES].sort()).toEqual(
      ["ventas", "compras", "inventario", "tesoreria", "fiscal", "regulatorio", "reportes"].sort(),
    );
  });
});
