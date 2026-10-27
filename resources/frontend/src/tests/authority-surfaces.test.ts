import { describe, expect, it } from "vitest";
import { readdirSync, readFileSync } from "node:fs";
import { join, relative, resolve, sep } from "node:path";
import { crearIndice, resolver, type Operacion } from "@/app/autoridad/operaciones";
import { PANTALLAS } from "@/app/autoridad/pantallas";

const SRC = resolve(__dirname, "..");

const read = (rel: string): string => readFileSync(resolve(SRC, rel), "utf8");

interface InstantaneaOperaciones {
  operations: Operacion[];
  permissions: string[];
}

const instantanea = JSON.parse(
  read("tests/fixtures/operaciones.json"),
) as InstantaneaOperaciones;
const indice = crearIndice(instantanea.operations);

function recogerFuentes(): string[] {
  const resultados: string[] = [];

  const recorrer = (directorio: string): void => {
    for (const entrada of readdirSync(directorio, { withFileTypes: true })) {
      const rutaCompleta = join(directorio, entrada.name);
      if (entrada.isDirectory()) {
        recorrer(rutaCompleta);
      } else if (
        (entrada.name.endsWith(".ts") || entrada.name.endsWith(".tsx")) &&
        !entrada.name.endsWith(".test.ts") &&
        !entrada.name.endsWith(".test.tsx") &&
        !rutaCompleta.includes(`${sep}tests${sep}`)
      ) {
        resultados.push(relative(SRC, rutaCompleta));
      }
    }
  };

  recorrer(SRC);
  return resultados;
}

describe("authority surfaces", () => {
  it("toda hija de AppShell en app/router.tsx tiene clave en PANTALLAS y no sobra ninguna", () => {
    const routerSource = read("app/router.tsx");
    const inicio = routerSource.indexOf("conRequisitos([");
    expect(inicio).toBeGreaterThan(-1);

    const fin = routerSource.indexOf("]),", inicio);
    expect(fin).toBeGreaterThan(inicio);

    const bloque = routerSource.slice(inicio, fin);
    const rutasDeclaradas = new Set<string>([""]);
    const regex = /\{\s*path:\s*"([^"]+)"/g;
    let coincidencia = regex.exec(bloque);
    while (coincidencia !== null) {
      rutasDeclaradas.add(coincidencia[1]);
      coincidencia = regex.exec(bloque);
    }

    const clavesPantallas = new Set(Object.keys(PANTALLAS));
    for (const ruta of rutasDeclaradas) {
      expect(clavesPantallas.has(ruta), `ruta declarada sin pantalla: ${ruta}`).toBe(true);
    }

    for (const clave of clavesPantallas) {
      expect(rutasDeclaradas.has(clave), `pantalla sin ruta declarada: ${clave}`).toBe(true);
    }
  });

  it("cada capacidad de PANTALLAS existe en el catálogo de permisos del backend", () => {
    for (const [ruta, requisito] of Object.entries(PANTALLAS)) {
      if (requisito === null) {
        continue;
      }
      expect(
        instantanea.permissions.includes(requisito.capacidad),
        `capacidad inexistente para ${ruta}: ${requisito.capacidad}`,
      ).toBe(true);
    }
  });

  it("cada operacion de PANTALLAS resuelve en la instantánea y sus capacidades no están vacías", () => {
    for (const [ruta, requisito] of Object.entries(PANTALLAS)) {
      if (requisito === null || requisito.operacion === undefined) {
        continue;
      }

      const [metodo, rutaOperacion] = requisito.operacion;
      const resuelta = resolver(indice, metodo, rutaOperacion);
      expect(resuelta, `operación inexistente para ${ruta}: ${metodo} ${rutaOperacion}`).not.toBeNull();
      expect(resuelta?.capabilities?.length ?? 0).toBeGreaterThan(0);
    }
  });

  it("toda operación o puede() literal en src resuelve en la instantánea", () => {
    const archivos = recogerFuentes();
    const regexOperacion = /operacion=\{\["([A-Z]+)",\s*"([^"$`]+)"\]\}/g;
    const regexPuede = /puede\("([A-Z]+)",\s*"([^"$`]+)"\)/g;

    for (const archivo of archivos) {
      const fuente = read(archivo);

      let coincidencia = regexOperacion.exec(fuente);
      while (coincidencia !== null) {
        const metodo = coincidencia[1];
        const ruta = coincidencia[2];
        expect(
          resolver(indice, metodo, ruta),
          `operación inexistente en ${archivo}: ${metodo} ${ruta}`,
        ).not.toBeNull();
        coincidencia = regexOperacion.exec(fuente);
      }

      coincidencia = regexPuede.exec(fuente);
      while (coincidencia !== null) {
        const metodo = coincidencia[1];
        const ruta = coincidencia[2];
        expect(
          resolver(indice, metodo, ruta),
          `operación inexistente en ${archivo}: ${metodo} ${ruta}`,
        ).not.toBeNull();
        coincidencia = regexPuede.exec(fuente);
      }
    }
  });
});
