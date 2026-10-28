/**
 * El arnés E2E no se relaja para tapar un fallo (E2E-PANTALLA-SIN-PINTAR).
 *
 * Un fallo de «formulario sin pintar» solo se puede clasificar si queda rastro: con `retries` 0,
 * `trace: on-first-retry` nunca capturaba el primer fallo y cuatro fallos del 2026-10-12 se quedaron
 * sin explicar. La captura se retiene al fallar y nada más cambia. Estas pruebas vigilan el contrato
 * de la configuración canónica, que una ejecución verde no demuestra: ni el tiempo de espera ni los
 * reintentos ni los trabajadores se tocan para «quedar en verde», la traza y la captura siguen
 * encendidas al fallar, y el inventario de omisiones y de esperas fijas de `e2e/` no crece en silencio.
 */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";

import { describe, expect, it } from "vitest";

import config from "../../playwright.config";

const RAIZ = join(__dirname, "..", "..");

function tsBajo(directorio: string): string[] {
  const salida: string[] = [];
  for (const nombre of readdirSync(directorio)) {
    const ruta = join(directorio, nombre);
    if (statSync(ruta).isDirectory()) salida.push(...tsBajo(ruta));
    else if (nombre.endsWith(".ts")) salida.push(relative(RAIZ, ruta));
  }
  return salida.sort();
}

function sitios(patron: RegExp): Record<string, number> {
  const cuenta: Record<string, number> = {};
  for (const f of tsBajo(join(RAIZ, "e2e"))) {
    const n = (readFileSync(join(RAIZ, f), "utf8").match(patron) ?? []).length;
    if (n) cuenta[f] = n;
  }
  return cuenta;
}

describe("el arnés E2E no se relaja", () => {
  it("el tiempo de espera, los reintentos y los trabajadores son los canónicos", () => {
    expect(config.timeout, "no se amplía el tiempo global para tapar un fallo").toBeUndefined();
    expect(config.expect?.timeout, "ni el de las aserciones").toBeUndefined();
    expect(config.use?.actionTimeout, "ni el de las acciones").toBeUndefined();
    expect(config.use?.navigationTimeout, "ni el de la navegación").toBeUndefined();
    expect(config.retries, "sin reintentos fuera de CI").toBe(process.env.CI ? 2 : 0);
    expect(config.workers, "los trabajadores no se fijan (workers=1 fue solo medición)").toBeUndefined();
    expect(config.fullyParallel).toBe(true);
  });

  it("un fallo deja rastro: traza y captura se retienen al fallar", () => {
    expect(config.use?.trace).toBe("retain-on-failure");
    expect(config.use?.screenshot).toBe("only-on-failure");
  });

  it("el inventario de omisiones de e2e/ es el declarado", () => {
    // Seis guardas de credenciales (que el runner ya satisface) y cinco omisiones nombradas de
    // ENTORNO-SIN-CLAMSCAN. Una omisión nueva se declara aquí, con su deuda; no entra en silencio.
    expect(sitios(/\btest\.skip\(/g)).toEqual({
      "e2e/accessibility.spec.ts": 1,
      "e2e/audit-catalog.spec.ts": 2,
      "e2e/documents-a11y.spec.ts": 2,
      "e2e/documents.spec.ts": 4,
      "e2e/uom-a11y.spec.ts": 1,
      "e2e/warehouse-a11y.spec.ts": 1,
    });
    expect(sitios(/\b(test\.fixme|describe\.skip|test\.only|describe\.only)\(/g)).toEqual({});
  });

  it("el ayudante de empresa decide con una lectura esperada, no con una fotografía ni con networkidle", () => {
    // E2E-HELPER-EMPRESA-CARRERA-DE-PINTADO: la decisión se toma sobre la lectura que satisface la
    // espera con auto-repetición; ni `networkidle`, ni esperas fijas, ni un tiempo mayor del de siempre.
    const ayudante = readFileSync(join(RAIZ, "e2e/helpers/empresa.ts"), "utf8");
    const approvals = readFileSync(join(RAIZ, "e2e/approvals.spec.ts"), "utf8");
    const activar = (fuente: string): string =>
      fuente.slice(fuente.indexOf("async function activarEmpresa("), fuente.indexOf("\n}\n", fuente.indexOf("async function activarEmpresa(")));
    for (const cuerpo of [activar(ayudante), activar(approvals)]) {
      expect(cuerpo, "la decisión espera a un estado determinable").toMatch(/esperarEstadoDeEmpresa\(/);
      expect(cuerpo, "networkidle no es autoridad de preparación").not.toMatch(/waitForLoadState\("networkidle"\)/);
      expect(cuerpo, "sin esperas fijas").not.toMatch(/waitForTimeout|setTimeout/);
      expect(cuerpo, "la decisión no vuelve a contar por su cuenta").not.toMatch(/yaActiva|\(await desactivar\.count\(\)\) > 0/);
      expect(cuerpo, "la postcondición sigue: exactamente una empresa activa").toMatch(/await expect\(desactivar\)\.toHaveCount\(1, \{ timeout: 15000 \}\);\s+await expect\(activa\)\.toHaveCount\(1\);/);
    }
    const controles = ayudante.slice(ayudante.indexOf("export function controlesDeEmpresa("), ayudante.indexOf("export type EstadoDeEmpresa"));
    expect(controles.match(/name: "(Activar|Desactivar|Activa)" \}/g) ?? [], "los tres localizadores siguen siendo exactos").toEqual([]);
    // La espera devuelve la misma lectura que la satisfizo: no hay relectura instantánea después (sin TOCTOU).
    const espera = ayudante.slice(ayudante.indexOf("export async function esperarEstadoDeEmpresa("), ayudante.indexOf("export async function emitirLaTablaTarde("));
    expect(espera).toMatch(/return lectura as LecturaDeEmpresa;/);
    expect(espera.match(/leerEstadoDeEmpresa\(/g) ?? []).toHaveLength(1);
    expect(ayudante).toMatch(/export const ESPERA_DEL_AYUDANTE_MS = 15000;/);
    expect(ayudante.match(/timeout: \d+/g) ?? [], "ningún tiempo distinto del de siempre").toEqual(
      Array.from({ length: (ayudante.match(/timeout: 15000/g) ?? []).length }, () => "timeout: 15000"),
    );
    expect(ayudante).toMatch(/expect\s*\.poll\(/);
    // La única espera temporal del fichero es la sonda que reproduce la carrera, no una decisión del ayudante.
    const sonda = ayudante.slice(ayudante.indexOf("export async function emitirLaTablaTarde("), ayudante.indexOf("export async function activarEmpresa("));
    expect((ayudante.match(/setTimeout/g) ?? []).length).toBe((sonda.match(/setTimeout/g) ?? []).length);
    expect(ayudante.match(/exact: true/g) ?? []).toHaveLength(3);
  });

  it("no entran esperas fijas nuevas", () => {
    // Seis preexistentes (reflujo tras cambiar el tamaño de la ventana y dos de N6): anotadas, no se amplían.
    expect(sitios(/waitForTimeout\(/g)).toEqual({
      "e2e/documents-a11y.spec.ts": 1,
      "e2e/n6-multicompany.spec.ts": 2,
      "e2e/uom-a11y.spec.ts": 2,
      "e2e/warehouse-a11y.spec.ts": 1,
    });
  });
});
