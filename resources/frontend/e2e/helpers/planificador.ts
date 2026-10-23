/**
 * El planificador de plataforma, desde el E2E (Spec 047 · ADR-D0-015).
 *
 * En producción lo invoca el temporizador del sistema; aquí se invoca la misma
 * orden canónica contra la base del E2E. No hay atajo: es el mismo tick.
 *
 * Este módulo no contiene pruebas; Playwright solo recoge `*.spec.ts`.
 */
import { resolve } from "node:path";

import { ejecutarPython } from "./python";

const BACKEND = resolve(process.cwd(), "..", "backend");

export function tick(): void {
  const url = process.env.KONTROL_E2E_DB_URL;
  if (!url) {
    throw new Error("KONTROL_E2E_DB_URL es obligatoria: el planificador corre contra la base del E2E");
  }
  ejecutarPython(["-m", "app.modules.scheduler", "tick"], {
    cwd: BACKEND,
    env: { ...process.env, KONTROL_DB_URL: url },
    encoding: "utf8",
    timeout: 120_000,
  });
}

/**
 * Ejecuta ticks hasta que la condición se cumpla.
 *
 * Tres navegadores corren a la vez contra la misma base: un tick que coincide con
 * otro queda `SKIPPED_OVERLAP`, que es lo correcto, y el efecto llega en el
 * siguiente. Se reintenta un número acotado de veces y, si no llega, falla.
 */
export async function hastaQue(condicion: () => Promise<boolean>, intentos = 20): Promise<void> {
  for (let i = 0; i < intentos; i++) {
    tick();
    if (await condicion()) return;
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error("el planificador no produjo el efecto esperado");
}
