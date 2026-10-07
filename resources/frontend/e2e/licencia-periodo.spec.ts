/**
 * ROLLA · Una licencia de período anterior no sustituye a la vigente (LICENCIA-DOWNGRADE-FIRMADO
 * Fase A, FR-010-200..231).
 *
 * Compuertas 1 y 2 delante (sesión + `license:create`; ancla sintética explícita de la corrida).
 * La tercera compara solo el período firmado: anterior → 423 `LICENSE_PERIOD_DOWNGRADE` sin tocar
 * nada; posterior → se aplica; el mismo período → solo la reimportación exacta (idempotente) u otra
 * con `revision` del emisor (`licencia-revision.spec.ts`): otra legacy distinta se rechaza
 * (`LICENCIA-REEMISION-INTRAPERIODO-SIN-ORDEN`, cerrada). El escenario ordenado va en una sola prueba porque
 * la suite corre en paralelo y el período vigente es estado compartido de la corrida: solo avanza,
 * nunca retrocede, y conserva el identificador `LIC-E2E` que otras pruebas afirman. `READ_ONLY` y
 * la carrera se prueban en el backend sobre PostgreSQL (ROLLA-08/09, RACE-01..05).
 */
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";

import { expect, test, type APIRequestContext } from "@playwright/test";

const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";
const PASSWORD = process.env.KONTROL_E2E_PASSWORD ?? "";
const BACKEND = resolve(process.cwd(), "..", "backend");
const QA = resolve(BACKEND, "..", "..", "qa");
const IMPORT = `${API}/license/import`;
const SENSIBLE = /installation_id|KTL-|signature|ed25519|public_key|private|\/tmp|\/home|postgres|tenant_id|company_id/i;

interface Artefacto {
  payload: Record<string, unknown>;
  signature_hex: string;
}

interface Detalle {
  license_id: string;
  mode: string;
  period_start: string;
  period_end: string;
  entitlements: Record<string, unknown>;
}

function entornoDeQA(): NodeJS.ProcessEnv {
  const url = process.env.KONTROL_E2E_DB_URL;
  if (!url) {
    throw new Error("KONTROL_E2E_DB_URL es obligatoria: el ayudante lee la instalación de la base de la corrida");
  }
  return { ...process.env, KONTROL_DB_URL: url, PYTHONPATH: BACKEND };
}

/** Una licencia sintética firmada por el firmante de la corrida (`--anio` = período anual del contrato). */
function licenciaFirmada(licenseId: string, ...opciones: string[]): Artefacto {
  const salida = execFileSync(resolve(BACKEND, ".venv", "bin", "python"), [resolve(QA, "licencia_firmada.py"), licenseId, ...opciones], {
    cwd: BACKEND, env: entornoDeQA(), encoding: "utf8", timeout: 60_000,
  });
  return JSON.parse(salida) as Artefacto;
}

async function token(request: APIRequestContext, usuario: string): Promise<string> {
  const r = await request.post(`${API}/auth/login`, { data: { tenant_code: "DEMO", username: usuario, password: PASSWORD } });
  expect(r.ok(), `login de ${usuario}: ${r.status()}`).toBeTruthy();
  return (await r.json()).access_token as string;
}

async function detalle(request: APIRequestContext, bearer: string): Promise<Detalle> {
  const r = await request.get(`${API}/license/detail`, { headers: { Authorization: `Bearer ${bearer}` } });
  expect(r.status()).toBe(200);
  const c = (await r.json()) as Detalle;
  return { license_id: c.license_id, mode: c.mode, period_start: c.period_start, period_end: c.period_end, entitlements: c.entitlements };
}

/** El año contractual (abril → marzo) en que empieza un instante dado. */
function anioContractual(iso: string): number {
  const d = new Date(iso);
  return d.getUTCMonth() + 1 >= 4 ? d.getUTCFullYear() : d.getUTCFullYear() - 1;
}

test.describe("Licencia · el período no retrocede", () => {
  test("E2E-ROLLA-01..08 · anterior rechazada sin mover nada; reemisión del mismo período aceptada; posterior aceptada; y después la anterior sigue rechazada", async ({ request }) => {
    const admin = await token(request, "admin");
    const cabecera = { Authorization: `Bearer ${admin}` };
    const antes = await detalle(request, admin);
    const anioVigente = anioContractual(antes.period_start);

    // 1-2) Un período claramente anterior al vigente (el administrador, con firma válida): rechazado, y nada cambia.
    const anterior = await request.post(IMPORT, { data: licenciaFirmada("LIC-E2E-VIEJA", "--anio", String(anioVigente - 3)), headers: cabecera });
    expect(anterior.status(), await anterior.text()).toBe(423);
    const rechazo = await anterior.json();
    expect(rechazo.code).toBe("LICENSE_PERIOD_DOWNGRADE");
    expect(await anterior.text()).not.toMatch(SENSIBLE);
    expect(await detalle(request, admin)).toEqual(antes);
    const publico = await request.get(`${API}/license/status`);
    expect((await publico.json()).mode).toBe(antes.mode);

    // 3) Mismo período: el artefacto vigente exacto entra (idempotente); otra legacy distinta del mismo
    //    período, aunque lleve el mismo identificador, ya no (FR-010-330), y nada cambia.
    const exacta = await request.post(IMPORT, { data: licenciaFirmada("--vigente"), headers: cabecera });
    expect(exacta.status(), await exacta.text()).toBe(200);
    expect(await detalle(request, admin)).toEqual(antes);
    const otraLegacy = await request.post(IMPORT, { data: licenciaFirmada(antes.license_id, "--periodo", antes.period_start, antes.period_end), headers: cabecera });
    expect(otraLegacy.status(), await otraLegacy.text()).toBe(423);
    expect((await otraLegacy.json()).code).toBe("LICENSE_LEGACY_REISSUE_REQUIRES_REVISION");
    expect(await otraLegacy.text()).not.toMatch(SENSIBLE);
    expect(await detalle(request, admin)).toEqual(antes);

    // 4) Un período posterior, con el identificador que la corrida comparte: entra y el detalle lo refleja.
    const anioPosterior = anioContractual(antes.period_end) + 2;
    const posterior = await request.post(IMPORT, { data: licenciaFirmada(antes.license_id, "--anio", String(anioPosterior)), headers: cabecera });
    expect(posterior.status(), await posterior.text()).toBe(200);
    const despues = await detalle(request, admin);
    expect(despues.license_id).toBe(antes.license_id);
    expect(anioContractual(despues.period_start)).toBe(anioPosterior);
    expect(despues.mode).toBe("FULL_ACCESS");
    expect((await (await request.get(`${API}/license/status`)).json()).mode).toBe("FULL_ACCESS");

    // 5-6) Volver al período que había antes ya es un retroceso: rechazado, y el posterior se queda.
    const vuelta = await request.post(IMPORT, { data: licenciaFirmada(antes.license_id, "--periodo", antes.period_start, antes.period_end), headers: cabecera });
    expect(vuelta.status()).toBe(423);
    expect((await vuelta.json()).code).toBe("LICENSE_PERIOD_DOWNGRADE");
    expect(await detalle(request, admin)).toEqual(despues);

    // 7) El rechazo quedó auditado con su actor; la licencia vigente no cambió.
    const historial = await request.get(`${API}/license/history`, { headers: cabecera });
    const eventos = (await historial.json()) as Array<{ event_type: string; detail: Record<string, unknown> }>;
    expect(eventos.filter((e) => e.event_type === "LICENSE_PERIOD_DOWNGRADE_REJECTED").length).toBeGreaterThanOrEqual(2);
  });

  test("E2E-ROLLA-09 · sin license:create ni una licencia posterior entra, y el período vigente no cambia", async ({ request }) => {
    const admin = await token(request, "admin");
    const antes = await detalle(request, admin);
    const futura = licenciaFirmada("LIC-E2E-FUTURA", "--anio", String(anioContractual(antes.period_end) + 9));
    expect((await request.post(IMPORT, { data: futura })).status()).toBe(401);
    expect((await request.post(IMPORT, { data: futura, headers: { Authorization: "Bearer no.es.un.token" } })).status()).toBe(401);
    expect((await detalle(request, admin)).period_end).toBe(antes.period_end);
  });

  test("E2E-ROLLA-10 · firma inválida u otra instalación se rechazan antes de comparar períodos", async ({ request }) => {
    const admin = await token(request, "admin");
    const cabecera = { Authorization: `Bearer ${admin}` };
    const antes = await detalle(request, admin);
    const anio = String(anioContractual(antes.period_end) + 9);
    const falsa = await request.post(IMPORT, { data: licenciaFirmada("LIC-E2E-FALSA", "--anio", anio, "--firma-invalida"), headers: cabecera });
    expect(falsa.status()).toBe(423);
    expect((await falsa.json()).code).toBe("LICENSE_SIGNATURE_INVALID");
    const ajena = await request.post(IMPORT, { data: licenciaFirmada("LIC-E2E-AJENA", "--anio", anio, "--otra-instalacion"), headers: cabecera });
    expect(ajena.status()).toBe(423);
    expect((await ajena.json()).code).toBe("LICENSE_INSTALLATION_MISMATCH");
    expect((await detalle(request, admin)).period_end).toBe(antes.period_end);
  });

  test("E2E-ROLLA-11 · el estado público sigue mínimo y los health, públicos", async ({ request }) => {
    const r = await request.get(`${API}/license/status`);
    expect(Object.keys(await r.json()).sort()).toEqual(["license_url", "mode"]);
    expect(await r.text()).not.toMatch(/period|DOWNGRADE/i);
    expect(await (await request.get(`${API}/health/live`)).json()).toEqual({ status: "ok", service: "kontrol-backend" });
  });
});
