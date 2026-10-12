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
    // Cinco guardas de credenciales (que el runner ya satisface) y cuatro omisiones nombradas de
    // ENTORNO-SIN-CLAMSCAN. Una omisión nueva se declara aquí, con su deuda; no entra en silencio.
    expect(sitios(/\btest\.skip\(/g)).toEqual({
      "e2e/accessibility.spec.ts": 1,
      "e2e/documents-a11y.spec.ts": 2,
      "e2e/documents.spec.ts": 4,
      "e2e/uom-a11y.spec.ts": 1,
      "e2e/warehouse-a11y.spec.ts": 1,
    });
    expect(sitios(/\b(test\.fixme|describe\.skip|test\.only|describe\.only)\(/g)).toEqual({});
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
