/**
 * Spec 047 · ninguna cadena visible nueva fuera del catálogo (FR-047-053).
 *
 * Busca en las pantallas de la 047 texto escrito directamente en JSX y en los
 * atributos que el usuario lee. Los valores que llegan del servidor y las clases
 * de estilo no cuentan.
 */
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const RAIZ = join(__dirname, "..");
const MODULO = join(RAIZ, "modules", "notificaciones");

function fuentes(dir: string): string[] {
  return readdirSync(dir).flatMap((entrada) => {
    const ruta = join(dir, entrada);
    if (statSync(ruta).isDirectory()) return fuentes(ruta);
    return /\.tsx?$/.test(entrada) && !/\.test\.tsx?$/.test(entrada) ? [ruta] : [];
  });
}

/**
 * Texto entre etiquetas JSX que empieza por una letra. El `>` de una flecha
 * (`=> apiFetch<T>(…)`) no es el cierre de una etiqueta.
 */
const TEXTO_JSX = /(?<!=)>\s*([A-Za-zÁÉÍÓÚÜÑáéíóúüñ¿¡][^<>{}]*?)\s*</g;
/** Atributos que el usuario lee, con un literal. */
const ATRIBUTO = /\b(aria-label|title|placeholder|label|description|message|loadingText|emptyTitle|emptyDescription)="([^"]*[A-Za-zÁÉÍÓÚáéíóúñ][^"]*)"/g;

describe("Spec 047 · cadenas visibles", () => {
  const archivos = fuentes(MODULO);

  it("hay pantallas que revisar", () => {
    expect(archivos.length).toBeGreaterThanOrEqual(8);
  });

  it.each(archivos.map((a) => [a.slice(RAIZ.length + 1)]))("%s no escribe texto visible a mano", (relativa) => {
    const codigo = readFileSync(join(RAIZ, relativa), "utf8")
      .replace(/\/\*[\s\S]*?\*\//g, "")
      .replace(/^\s*\/\/.*$/gm, "");
    const textos = [...codigo.matchAll(TEXTO_JSX)].map((m) => m[1]);
    const atributos = [...codigo.matchAll(ATRIBUTO)].map((m) => `${m[1]}="${m[2]}"`);
    expect([...textos, ...atributos]).toEqual([]);
  });
});
