import { describe, expect, it } from "vitest";
import {
  crearIndice,
  evaluar,
  resolver,
  type Conjuntos,
  type Operacion,
} from "./operaciones";

const catalogo: Operacion[] = [
  {
    method: "GET",
    path: "/api/v1/sales/orders",
    capabilities: ["orders:list"],
    scope: "COMPANY",
  },
  {
    method: "GET",
    path: "/api/v1/sales/orders/{order_id}",
    capabilities: ["orders:read"],
    scope: "COMPANY",
  },
  {
    method: "POST",
    path: "/api/v1/sales/orders/{order_id}/submit",
    capabilities: ["orders:submit"],
    scope: "COMPANY",
  },
  {
    method: "GET",
    path: "/api/v1/sales/orders/expire-reservations",
    capabilities: ["orders:expire"],
    scope: "TENANT",
  },
  {
    method: "GET",
    path: "/api/v1/health",
    capabilities: [],
    scope: "GLOBAL",
  },
];

function conjuntos(parcial: Partial<Conjuntos> = {}): Conjuntos {
  return {
    empresa: new Set<string>(),
    tenant: new Set<string>(),
    global: new Set<string>(),
    ...parcial,
  };
}

describe("resolver", () => {
  const indice = crearIndice(catalogo);

  it("resuelve una ruta con plantilla", () => {
    const operacion = resolver(indice, "GET", "/sales/orders/abc");
    expect(operacion?.path).toBe("/api/v1/sales/orders/{order_id}");
  });

  it("descarta la query string", () => {
    const operacion = resolver(
      indice,
      "GET",
      "/sales/orders/abc?expand=items",
    );
    expect(operacion?.path).toBe("/api/v1/sales/orders/{order_id}");
  });

  it("acepta el método en minúsculas", () => {
    const operacion = resolver(indice, "get", "/sales/orders/abc");
    expect(operacion?.path).toBe("/api/v1/sales/orders/{order_id}");
  });

  it("prioriza el literal frente a la plantilla", () => {
    const operacion = resolver(
      indice,
      "GET",
      "/sales/orders/expire-reservations",
    );
    expect(operacion?.path).toBe(
      "/api/v1/sales/orders/expire-reservations",
    );
  });

  it("devuelve null para una ruta desconocida", () => {
    expect(resolver(indice, "GET", "/sales/orders/abc/unknown")).toBeNull();
  });

  it("devuelve null si el número de segmentos es distinto", () => {
    expect(resolver(indice, "GET", "/sales")).toBeNull();
    expect(resolver(indice, "POST", "/sales/orders/abc")).toBeNull();
  });

  it("no trata como plantilla un segmento que solo empieza por llave", () => {
    const catalogoEspecial: Operacion[] = [
      {
        method: "GET",
        path: "/api/v1/a/{id",
        capabilities: [],
        scope: "GLOBAL",
      },
      {
        method: "GET",
        path: "/api/v1/a/{id}",
        capabilities: [],
        scope: "GLOBAL",
      },
    ];
    const indiceEspecial = crearIndice(catalogoEspecial);

    expect(resolver(indiceEspecial, "GET", "/a/{id")?.path).toBe(
      "/api/v1/a/{id",
    );
    expect(resolver(indiceEspecial, "GET", "/a/xyz")?.path).toBe(
      "/api/v1/a/{id}",
    );
  });

  it("distingue una plantilla de un segmento literal con asterisco", () => {
    const catalogoEspecial: Operacion[] = [
      {
        method: "GET",
        path: "/api/v1/a/{id}",
        capabilities: [],
        scope: "GLOBAL",
      },
      {
        method: "GET",
        path: "/api/v1/a/lista",
        capabilities: [],
        scope: "GLOBAL",
      },
    ];
    const indiceEspecial = crearIndice(catalogoEspecial);

    expect(resolver(indiceEspecial, "GET", "/a/*")?.path).toBe(
      "/api/v1/a/{id}",
    );
    expect(resolver(indiceEspecial, "GET", "/a/lista")?.path).toBe(
      "/api/v1/a/lista",
    );
  });
});

describe("evaluar", () => {
  it("deniega una operación desconocida", () => {
    expect(evaluar(null, conjuntos())).toEqual({
      permitido: false,
      motivo: "PERMISSION_DENIED",
      alcance: null,
    });
  });

  it("permite una operación sin capacidades", () => {
    const operacion: Operacion = {
      method: "GET",
      path: "/api/v1/health",
      capabilities: [],
      scope: "GLOBAL",
    };
    expect(evaluar(operacion, conjuntos())).toEqual({
      permitido: true,
      motivo: null,
      alcance: "GLOBAL",
    });
  });

  it("permite una operación COMPANY con la capacidad de empresa", () => {
    const operacion: Operacion = {
      method: "GET",
      path: "/api/v1/sales/orders",
      capabilities: ["orders:list"],
      scope: "COMPANY",
    };
    expect(
      evaluar(
        operacion,
        conjuntos({ empresa: new Set(["orders:list"]) }),
      ),
    ).toEqual({
      permitido: true,
      motivo: null,
      alcance: "COMPANY",
    });
  });

  it("deniega COMPANY si falta una de sus capacidades aunque tenga la otra", () => {
    const operacion: Operacion = {
      method: "POST",
      path: "/api/v1/sales/orders/{order_id}/release",
      capabilities: ["ventas:view", "ventas:approve"],
      scope: "COMPANY",
    };
    expect(
      evaluar(operacion, conjuntos({ empresa: new Set(["ventas:view"]) })),
    ).toEqual({
      permitido: false,
      motivo: "PERMISSION_DENIED",
      alcance: "COMPANY",
    });
    expect(
      evaluar(
        operacion,
        conjuntos({ empresa: new Set(["ventas:view", "ventas:approve"]) }),
      ),
    ).toEqual({
      permitido: true,
      motivo: null,
      alcance: "COMPANY",
    });
  });

  it("deniega COMPANY con la capacidad solo en global", () => {
    const operacion: Operacion = {
      method: "GET",
      path: "/api/v1/sales/orders",
      capabilities: ["orders:list"],
      scope: "COMPANY",
    };
    expect(
      evaluar(
        operacion,
        conjuntos({ global: new Set(["orders:list"]) }),
      ),
    ).toEqual({
      permitido: false,
      motivo: "COMPANY_SCOPE_FORBIDDEN",
      alcance: "COMPANY",
    });
  });

  it("deniega TENANT con la capacidad solo en global", () => {
    const operacion: Operacion = {
      method: "GET",
      path: "/api/v1/sales/orders/expire-reservations",
      capabilities: ["orders:expire"],
      scope: "TENANT",
    };
    expect(
      evaluar(
        operacion,
        conjuntos({ global: new Set(["orders:expire"]) }),
      ),
    ).toEqual({
      permitido: false,
      motivo: "COMPANY_SCOPE_FORBIDDEN",
      alcance: "TENANT",
    });
  });

  it("deniega si la capacidad no está en ningún conjunto", () => {
    const operacion: Operacion = {
      method: "GET",
      path: "/api/v1/sales/orders",
      capabilities: ["orders:list"],
      scope: "COMPANY",
    };
    expect(evaluar(operacion, conjuntos())).toEqual({
      permitido: false,
      motivo: "PERMISSION_DENIED",
      alcance: "COMPANY",
    });
  });

  it("permite GLOBAL con la capacidad en global", () => {
    const operacion: Operacion = {
      method: "GET",
      path: "/api/v1/admin/stats",
      capabilities: ["admin:stats"],
      scope: "GLOBAL",
    };
    expect(
      evaluar(
        operacion,
        conjuntos({ global: new Set(["admin:stats"]) }),
      ),
    ).toEqual({
      permitido: true,
      motivo: null,
      alcance: "GLOBAL",
    });
  });

  it("no autoriza una operación TENANT con capacidad solo de empresa", () => {
    const operacion: Operacion = {
      method: "GET",
      path: "/api/v1/sales/orders/expire-reservations",
      capabilities: ["orders:expire"],
      scope: "TENANT",
    };
    expect(
      evaluar(
        operacion,
        conjuntos({ empresa: new Set(["orders:expire"]) }),
      ),
    ).toEqual({
      permitido: false,
      motivo: "PERMISSION_DENIED",
      alcance: "TENANT",
    });
  });
});
