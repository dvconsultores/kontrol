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
 * `e2e/` está deliberadamente fuera de este grafo y sigue sin comprobarse: es la
 * deuda `E2E-SIN-TYPECHECK`, que este fichero **no** cierra.
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";

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
