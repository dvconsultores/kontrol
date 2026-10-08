/**
 * TASA · El endpoint de desafío de la Autoridad Central real de la corrida tiene límite de tasa global
 * (CENTRAL-SYNC-SIN-LIMITE-DE-TASA, FR-010-538..576). El runner la levanta con capacidad reducida
 * (`KONTROL_CENTRAL_SYNC_CHALLENGE_RATE_LIMIT_CAPACITY`, ventana de 60 s); esta suite inunda el endpoint y
 * comprueba el 429 genérico con `Retry-After`, que lo rechazado no deja fila (la tabla queda acotada: la
 * capacidad entera se agota exactamente una vez) y que el health sigue mínimo. Proyecto `licencia-tasa`, el
 * último: nada corre después dentro de la misma ventana. Dirigida, se corre SOLA con `--no-deps`.
 */
import { expect, test } from "@playwright/test";

const CENTRAL = process.env.KONTROL_E2E_CENTRAL_URL ?? "http://127.0.0.1:8010";
const CAPACIDAD = Number(process.env.KONTROL_E2E_CENTRAL_RATE_CAPACITY ?? "40");
const VENTANA = 60;
const SENSIBLE = /BEGIN (PUBLIC|PRIVATE) KEY|nonce_sha256|KTL-|created_at|capacity|cla_sync|postgres|sqlite|\/tmp|\/home/i;

test.describe("licencia · límite de tasa del desafío (autoridad real de la corrida)", () => {
  test("E2E-RATE-01..04 · la inundación recibe 429 genérico con Retry-After, no supera la capacidad y el health sigue", async ({ request }) => {
    const estados: number[] = [];
    const rechazos: Array<{ retryAfter: string | undefined; cuerpo: string }> = [];
    for (let i = 0; i < CAPACIDAD + 12; i += 1) {
      const r = await request.post(`${CENTRAL}/v1/license/sync/challenge`, {
        data: { installation_id: `KTL-XX-E2E-TASA-${String(i).padStart(3, "0")}` },
        headers: { "Content-Type": "application/json" },
      });
      estados.push(r.status());
      if (r.status() === 429) rechazos.push({ retryAfter: r.headers()["retry-after"], cuerpo: await r.text() });
    }
    // E2E-RATE-01: solo dos respuestas posibles y al menos las doce de más son rechazos.
    expect(estados.every((s) => s === 200 || s === 429)).toBe(true);
    expect(estados.filter((s) => s === 200).length).toBeLessThanOrEqual(CAPACIDAD);
    expect(rechazos.length).toBeGreaterThanOrEqual(12);
    // E2E-RATE-02: una vez llena la ventana, todo lo demás es 429 (lo rechazado no crea fila ni libera hueco).
    const primerRechazo = estados.indexOf(429);
    expect(estados.slice(primerRechazo).every((s) => s === 429)).toBe(true);
    // E2E-RATE-03: 429 genérico, con Retry-After determinista dentro de la ventana y sin nada del registro ni del límite.
    for (const rechazo of rechazos) {
      const espera = Number(rechazo.retryAfter);
      expect(Number.isInteger(espera) && espera >= 1 && espera <= VENTANA, `Retry-After=${rechazo.retryAfter}`).toBe(true);
      expect(JSON.parse(rechazo.cuerpo)).toEqual({ code: "SYNC_RATE_LIMITED", message: expect.any(String) });
      expect(rechazo.cuerpo).not.toMatch(SENSIBLE);
    }
    // E2E-RATE-04: el health no se limita ni cuenta nada del límite.
    const live = await request.get(`${CENTRAL}/health/live`);
    expect(live.status()).toBe(200);
    expect(await live.json()).toEqual({ status: "ok", service: "kontrol-central-authority" });
    const ready = await request.get(`${CENTRAL}/health/ready`);
    expect(ready.status()).toBe(200);
    expect(Object.keys(await ready.json()).sort()).toEqual(["database", "service", "status"]);
  });
});
