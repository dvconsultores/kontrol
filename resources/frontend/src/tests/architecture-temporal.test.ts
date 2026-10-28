/**
 * Pruebas de arquitectura de fechas (ADR-020, FR-001-256).
 *
 * Impiden reintroducir, fuera del módulo central de fechas, el formateo o la
 * conversión implícitos que dependen de la zona del navegador o que cortan el
 * ISO. Esas llamadas no fallan: muestran otra fecha, o la misma con otro día.
 *
 * No comprueban nombres de variables ni comentarios: un comentario correcto se
 * puede escribir encima de un defecto.
 */
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";

import { describe, expect, it } from "vitest";

const RAIZ = join(__dirname, "..");
const MODULO_CENTRAL = "lib/fecha-de-negocio.ts";

function fuentes(dir: string = RAIZ): string[] {
  const salida: string[] = [];
  for (const entrada of readdirSync(dir)) {
    if (entrada === "node_modules" || entrada.startsWith(".")) continue;
    const ruta = join(dir, entrada);
    if (statSync(ruta).isDirectory()) {
      salida.push(...fuentes(ruta));
    } else if (/\.tsx?$/.test(entrada) && !/\.test\.tsx?$/.test(entrada)) {
      salida.push(ruta);
    }
  }
  return salida;
}

/**
 * Usos legítimos, con el motivo escrito. Una entrada sin motivo no es una
 * excepción: es el defecto otra vez, escondido. Claude decide lo que la
 * ejecución demuestre legítimo; aquí solo se deja lo que la tarea autoriza.
 */
const PERMITIDOS: Record<string, string> = {};

interface Regla {
  id: string;
  patron: RegExp;
  motivo: string;
}

/** Cada regla con su expresión regular, aplicada por línea. */
const REGLAS: Regla[] = [
  {
    id: "R1",
    patron: /toLocaleDateString\(|toLocaleTimeString\(/,
    motivo: "formatea una fecha con la zona del navegador",
  },
  {
    id: "R2",
    patron: /new Date\(.*\)\.toLocaleString\(/,
    motivo: "formatea una fecha con la zona del navegador",
  },
  {
    id: "R3",
    patron: /Intl\.DateTimeFormat\(/,
    motivo: "formatea una fecha con la zona del navegador",
  },
  {
    id: "R4",
    patron: /\.toISOString\(\)/,
    motivo: "convierte la fecha a UTC en vez de a la zona de negocio",
  },
  {
    id: "R5",
    patron: /(_at|date|_from|_to|expires\w*|getValue\(\)!?)\??\)?\.slice\(0, ?(10|16|19)\)/,
    motivo: "corta el ISO en vez de formatearlo con la zona de negocio",
  },
  {
    id: "R6",
    patron: /\.getFullYear\(|\.getMonth\(|\.getDate\(|\.getHours\(/,
    motivo: "lee componentes locales del navegador",
  },
];

const ARCHIVOS = fuentes()
  .map((ruta) => ({ ruta, relativa: relative(RAIZ, ruta), texto: readFileSync(ruta, "utf8") }))
  .filter(({ relativa }) => {
    const normalizada = relativa.replace(/\\/g, "/");
    return normalizada !== MODULO_CENTRAL && !normalizada.startsWith("tests/");
  });

function esComentario(linea: string): boolean {
  const limpia = linea.trimStart();
  return limpia.startsWith("//") || limpia.startsWith("*");
}

describe("arquitectura de fechas", () => {
  it("las fechas se formatean y convierten solo en el módulo central", () => {
    // La zona del navegador no es la de negocio: un `toLocaleDateString` en una
    // pantalla enseña el día anterior a partir de las 20:00 de Caracas, y un
    // `toISOString` guarda el día siguiente a partir de la misma hora.
    const ofensas: string[] = [];
    for (const { relativa, texto } of ARCHIVOS) {
      const ruta = relativa.replace(/\\/g, "/");
      const lineas = texto.split("\n");
      for (let i = 0; i < lineas.length; i++) {
        const linea = lineas[i];
        if (esComentario(linea)) continue;
        for (const regla of REGLAS) {
          if (!regla.patron.test(linea)) continue;
          const clave = `${ruta}:${regla.id}`;
          if (PERMITIDOS[clave]) continue;
          ofensas.push(`${ruta}:${i + 1} (${regla.id}) ${regla.motivo}`);
        }
      }
    }
    expect(
      ofensas,
      `Las fechas se formatean y convierten solo en src/lib/fecha-de-negocio.ts (ADR-020, FR-001-256):\n${ofensas.join("\n")}`,
    ).toEqual([]);
  });

  it("el módulo central existe y nombra la zona de negocio", () => {
    const central = readFileSync(join(RAIZ, MODULO_CENTRAL), "utf8");
    expect(central).toContain("timeZone: ZONA_DE_NEGOCIO");
    expect(central).toContain('export const ZONA_DE_NEGOCIO = "America/Caracas"');
  });
});
