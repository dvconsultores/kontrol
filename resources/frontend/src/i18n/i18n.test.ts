/** Localización de la interfaz (Spec 047 · OQ-047-02). */
import { describe, expect, it } from "vitest";

import { es } from "./es";
import { formatearFecha, IDIOMA, IDIOMAS_DISPONIBLES, t, tValor } from "./index";

describe("t", () => {
  it("compone el texto en español con sus parámetros", () => {
    expect(t("campana.etiqueta", { count: 3 })).toBe("Notificaciones sin leer: 3");
  });

  it("un parámetro que falta deja su marcador a la vista, siempre igual", () => {
    expect(t("campana.etiqueta")).toBe("Notificaciones sin leer: {count}");
  });

  it("un parámetro sobrante no cambia nada", () => {
    expect(t("centro.titulo", { extra: "x" })).toBe("Notificaciones");
  });
});

describe("tValor", () => {
  it("traduce un valor conocido del servidor y no inventa uno desconocido", () => {
    expect(tValor("tareas.estado", "OPEN")).toBe("Abierta");
    expect(tValor("tareas.estado", "NUEVO_ESTADO")).toBeNull();
  });
});

describe("catálogo", () => {
  it("el inglés está diferido: solo existe `es`", () => {
    expect(IDIOMA).toBe("es");
    expect(IDIOMAS_DISPONIBLES).toEqual(["es"]);
  });

  it("ninguna entrada está vacía", () => {
    expect(Object.entries(es).filter(([, v]) => !v.trim())).toEqual([]);
  });

  it("una fecha ausente se muestra como raya", () => {
    expect(formatearFecha(null)).toBe("—");
  });
});
