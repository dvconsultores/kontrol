/**
 * El gate de tipos valida algo (BUILD-TSC-TESORERIA).
 *
 * `tsconfig.json` de este proyecto es un *solution config*: declara
 * `files: []` y delega en `references`. Eso significa que
 * `tsc --noEmit -p tsconfig.json` **recorre cero ficheros y termina en 0**, así
 * que sirve de evidencia de nada. Se midió: cero ficheros frente a los 193 del
 * repositorio que recorre el proyecto real.
 *
 * No es una hipótesis: un error de tipos real —un parámetro sin usar en una
 * prueba de tesorería— vivió en la rama mientras varios ciclos daban el
 * typecheck por limpio con esa orden. `npm run build` llevaba días fallando.
 *
 * Estas pruebas no comprueban tipos: comprueban que el **gate** siga pudiendo
 * comprobarlos. Miran el contrato de la configuración, que es lo que una
 * ejecución verde no puede demostrar por sí sola:
 *
 *   - que las órdenes del repositorio usen el modo que recorre las referencias;
 *   - que las referencias sigan cubriendo el grafo principal;
 *   - que la severidad que detectó el defecto siga encendida;
 *   - que las pruebas no queden fuera del grafo.
 *
 * `e2e/` estuvo fuera de este grafo hasta `E2E-SIN-TYPECHECK`: cuarenta y ocho
 * suites, sus ayudantes, el `global-setup` y `playwright.config.ts` se
 * transpilaban sin que nadie los comprobara, y un error de tipos real vivió en
 * `notifications.spec.ts` mientras el gate daba verde. Ahora son el tercer
 * proyecto de la solución (`tsconfig.e2e.json`: Node + DOM + Playwright, misma
 * severidad que `src`, sin emitir nada). La segunda mitad de este fichero
 * vigila que siga siendo así: que la referencia exista, que el proyecto recorra
 * **todos** los `.ts` de `e2e/` (una inclusión vacía también termina en 0), que
 * no emita, que no se relaje y que nadie pague el verde con un supresor.
 */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";

import ts from "typescript";
import { describe, expect, it } from "vitest";

const RAIZ = join(__dirname, "..", "..");

function leer(nombre: string): Record<string, unknown> {
  return JSON.parse(readFileSync(join(RAIZ, nombre), "utf8")) as Record<string, unknown>;
}

const paquete = leer("package.json");
const solucion = leer("tsconfig.json");
const guiones = paquete.scripts as Record<string, string>;

describe("el gate de tipos", () => {
  it("la configuración raíz es una solución: por sí sola no comprueba nada", () => {
    // Si algún día dejara de serlo, la advertencia de abajo sobraría y estas
    // pruebas habría que replantearlas. Se afirma para que ese cambio se vea.
    expect(solucion.files, "tsconfig.json debería declarar `files: []`").toEqual([]);
    expect(solucion.include, "una solución no declara `include`").toBeUndefined();
    expect(Array.isArray(solucion.references)).toBe(true);
  });

  it("las órdenes del repositorio recorren las referencias", () => {
    // `-b` es lo que distingue validar de no hacer nada. Sin él, sobre esta
    // configuración raíz, la orden termina en 0 sin mirar un solo fichero.
    for (const guion of ["typecheck", "build"] as const) {
      expect(guiones[guion], `falta el guion ${guion}`).toBeDefined();
      expect(guiones[guion], `${guion} debe validar con \`tsc -b\``).toMatch(/\btsc\s+-b\b/);
      expect(guiones[guion], `${guion} no puede validar con \`tsc -p\``).not.toMatch(/\btsc\s+(--\S+\s+)*-p\b/);
    }
  });

  it("el build encadena la validación de tipos antes del empaquetado", () => {
    expect(guiones.build).toMatch(/\btsc\s+-b\b.*&&.*\bvite build\b/);
  });

  it("las referencias cubren el grafo principal", () => {
    const rutas = (solucion.references as Array<{ path: string }>).map((r) => r.path);
    expect(rutas, "falta el proyecto de la aplicación").toContain("./tsconfig.app.json");
    expect(rutas, "falta el proyecto de herramientas").toContain("./tsconfig.node.json");

    const app = leer("tsconfig.app.json");
    expect(app.include, "el proyecto principal debe cubrir `src`").toEqual(["src"]);
    const node = leer("tsconfig.node.json");
    expect(node.include).toContain("vite.config.ts");
  });

  it("las pruebas del proyecto entran en el grafo", () => {
    // El defecto que originó todo esto vivía en un `.test.tsx`. Excluir las
    // pruebas haría pasar el gate dejando fuera justo donde apareció.
    const app = leer("tsconfig.app.json");
    expect(app.exclude, "el proyecto principal no debe excluir nada").toBeUndefined();
  });

  it("sigue encendida la severidad que detectó el defecto", () => {
    const opciones = (leer("tsconfig.app.json").compilerOptions ?? {}) as Record<string, unknown>;
    for (const regla of ["strict", "noUnusedLocals", "noUnusedParameters"] as const) {
      expect(opciones[regla], `${regla} no puede apagarse para pasar el gate`).toBe(true);
    }
  });
});

/** Todos los `.ts` bajo un directorio, recursivo, en rutas relativas a la raíz del proyecto. */
function tsBajo(directorio: string): string[] {
  const salida: string[] = [];
  for (const nombre of readdirSync(directorio)) {
    const ruta = join(directorio, nombre);
    if (statSync(ruta).isDirectory()) salida.push(...tsBajo(ruta));
    else if (nombre.endsWith(".ts")) salida.push(relative(RAIZ, ruta));
  }
  return salida.sort();
}

/** Los ficheros que `tsc` recorrería con una configuración, resueltos como los resuelve él. */
function recorridosPor(nombre: string): string[] {
  const leido = ts.readConfigFile(join(RAIZ, nombre), ts.sys.readFile);
  expect(leido.error, `${nombre} no se puede leer`).toBeUndefined();
  const proyecto = ts.parseJsonConfigFileContent(leido.config, ts.sys, RAIZ);
  expect(proyecto.errors.map((e) => e.messageText), `${nombre} tiene errores de configuración`).toEqual([]);
  return proyecto.fileNames.map((f) => relative(RAIZ, f)).sort();
}

describe("el gate de tipos cubre e2e", () => {
  const e2e = leer("tsconfig.e2e.json");
  const opciones = (e2e.compilerOptions ?? {}) as Record<string, unknown>;

  it("la solución referencia el proyecto de e2e", () => {
    // Sin la referencia, `tsc -b` no lo visita y volvemos a un verde que no mira e2e.
    const rutas = (solucion.references as Array<{ path: string }>).map((r) => r.path);
    expect(rutas, "falta el proyecto de e2e en las referencias").toContain("./tsconfig.e2e.json");
  });

  it("recorre todos los TypeScript de e2e, el global-setup, los ayudantes y la configuración de Playwright", () => {
    const enDisco = tsBajo(join(RAIZ, "e2e"));
    const recorridos = recorridosPor("tsconfig.e2e.json");
    // Una inclusión vacía o equivocada también termina en 0: se exige volumen real.
    expect(enDisco.length, "e2e/ debería tener suites TypeScript").toBeGreaterThanOrEqual(40);
    const fuera = enDisco.filter((f) => !recorridos.includes(f));
    expect(fuera, "ficheros de e2e que el proyecto no recorre").toEqual([]);
    expect(recorridos, "falta la configuración de Playwright").toContain("playwright.config.ts");
    expect(recorridos, "falta el global-setup").toContain(join("e2e", "global-setup.ts"));
  });

  it("no emite nada ni se mezcla con el empaquetado del producto", () => {
    expect(opciones.noEmit, "el proyecto de e2e solo comprueba").toBe(true);
    expect(opciones.outDir, "el proyecto de e2e no tiene salida").toBeUndefined();
    const app = leer("tsconfig.app.json");
    expect(app.include, "el proyecto principal sigue cubriendo solo `src`").toEqual(["src"]);
  });

  it("tiene el entorno real de Playwright: Node y DOM", () => {
    // `process`, `Buffer` y `node:child_process` en las suites; `document` dentro de `page.evaluate`.
    expect(opciones.types, "las suites usan process, Buffer y node:*").toContain("node");
    expect(opciones.lib, "los callbacks de page.evaluate corren en el navegador").toContain("DOM");
  });

  it("mantiene la misma severidad que el producto", () => {
    const producto = (leer("tsconfig.app.json").compilerOptions ?? {}) as Record<string, unknown>;
    for (const regla of ["strict", "noUnusedLocals", "noUnusedParameters", "noFallthroughCasesInSwitch"] as const) {
      expect(producto[regla], `${regla} no puede apagarse en el producto`).toBe(true);
      expect(opciones[regla], `${regla} no puede apagarse en e2e para pasar el gate`).toBe(true);
    }
    expect(e2e.exclude, "el proyecto de e2e no excluye nada").toBeUndefined();
  });

  it("nadie paga el verde con un supresor de tipos", () => {
    const supresores = /@ts-ignore|@ts-expect-error|\bas any\b|:\s*any\b|as unknown as\b/;
    const culpables = tsBajo(join(RAIZ, "e2e")).filter((f) => supresores.test(readFileSync(join(RAIZ, f), "utf8")));
    expect(culpables, "ficheros de e2e con @ts-ignore, @ts-expect-error o any").toEqual([]);
  });
});
