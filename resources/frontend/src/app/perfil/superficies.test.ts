import { describe, expect, it } from "vitest";

import {
  SUPERFICIE_POR_SEGMENTO,
  superficieDeRuta,
  superficieVisible,
} from "./superficies";

describe("superficieDeRuta", () => {
  it("devuelve SHARED para la raíz", () => {
    expect(superficieDeRuta("/")).toBe("SHARED");
  });

  it("devuelve GOVERNMENT para /gobierno/ente", () => {
    expect(superficieDeRuta("/gobierno/ente")).toBe("GOVERNMENT");
  });

  it("devuelve ENTERPRISE para /ventas/ordenes?x=1", () => {
    expect(superficieDeRuta("/ventas/ordenes?x=1")).toBe("ENTERPRISE");
  });

  it("exige coincidencia completa del segmento (/gobiernos → SHARED)", () => {
    expect(superficieDeRuta("/gobiernos")).toBe("SHARED");
  });

  it("devuelve SHARED para rutas del núcleo compartido", () => {
    const compartidas = [
      "/mi-licencia",
      "/alertas",
      "/aprobaciones/bandeja",
      "/documentos",
      "/seguridad/usuarios",
      "/licenciamiento/eventos",
      "/homologacion/actos",
      "/diagnostico",
      "/auditoria",
    ];
    for (const ruta of compartidas) {
      expect(superficieDeRuta(ruta), ruta).toBe("SHARED");
    }
  });

  it("devuelve ENTERPRISE para rutas de empresa", () => {
    const empresa = [
      "/organizacion/empresas",
      "/maestros/terceros",
      "/inventario/kardex",
      "/compras/ordenes",
      "/tesoreria/cajas",
      "/fiscal/emision",
      "/regulatorio/organismos",
      "/comercial/listas-precio",
      "/reportes/centro",
    ];
    for (const ruta of empresa) {
      expect(superficieDeRuta(ruta), ruta).toBe("ENTERPRISE");
    }
  });

  it("todas las claves del mapa son segmentos de empresa o gobierno", () => {
    for (const valor of Object.values(SUPERFICIE_POR_SEGMENTO)) {
      expect(valor === "ENTERPRISE" || valor === "GOVERNMENT").toBe(true);
    }
  });
});

describe("superficieVisible", () => {
  it("SHARED siempre es visible, incluso RESOLVIENDO", () => {
    expect(superficieVisible({ estado: "RESOLVIENDO" }, "SHARED")).toBe(true);
    expect(superficieVisible({ estado: "RESUELTO", perfil: "GOBIERNO" }, "SHARED")).toBe(true);
    expect(superficieVisible({ estado: "RESUELTO", perfil: "MIXTO" }, "SHARED")).toBe(true);
    expect(superficieVisible({ estado: "RESUELTO", perfil: "EMPRESA" }, "SHARED")).toBe(true);
  });

  it("RESOLVIENDO no expone superficies privadas", () => {
    expect(superficieVisible({ estado: "RESOLVIENDO" }, "GOVERNMENT")).toBe(false);
    expect(superficieVisible({ estado: "RESOLVIENDO" }, "ENTERPRISE")).toBe(false);
  });

  it("ERROR es fail-closed: solo SHARED, nunca Enterprise", () => {
    expect(superficieVisible({ estado: "ERROR" }, "SHARED")).toBe(true);
    expect(superficieVisible({ estado: "ERROR" }, "GOVERNMENT")).toBe(false);
    expect(superficieVisible({ estado: "ERROR" }, "ENTERPRISE")).toBe(false);
  });

  it("GOBIERNO solo ve GOVERNMENT", () => {
    expect(superficieVisible({ estado: "RESUELTO", perfil: "GOBIERNO" }, "GOVERNMENT")).toBe(true);
    expect(superficieVisible({ estado: "RESUELTO", perfil: "GOBIERNO" }, "ENTERPRISE")).toBe(false);
  });

  it("MIXTO ve GOVERNMENT y ENTERPRISE", () => {
    expect(superficieVisible({ estado: "RESUELTO", perfil: "MIXTO" }, "GOVERNMENT")).toBe(true);
    expect(superficieVisible({ estado: "RESUELTO", perfil: "MIXTO" }, "ENTERPRISE")).toBe(true);
  });

  it("EMPRESA solo ve ENTERPRISE", () => {
    expect(superficieVisible({ estado: "RESUELTO", perfil: "EMPRESA" }, "GOVERNMENT")).toBe(false);
    expect(superficieVisible({ estado: "RESUELTO", perfil: "EMPRESA" }, "ENTERPRISE")).toBe(true);
  });
});
