/**
 * ROTACION · El cliente elige la clave pública del propietario EXACTAMENTE por el `kid` firmado
 * (LICENCIA-SIN-ROTACION-DE-CLAVE, FR-010-437..466). La corrida tiene dos firmantes sintéticos: A (el que
 * firma la siembra y la Autoridad Central de la corrida) y B; el backend confía en los dos
 * (`KONTROL_LICENSE_PUBLIC_KEY_PEM`+`_KID` para A, `KONTROL_LICENSE_TRUST_KEYS` para A y B): es la fase
 * R1 (pre-stage) del runbook. Proyecto `licencia-rotacion`, tras `licencia-sync`. Dirigida, se corre
 * SOLA con `--no-deps`.
 */
import { resolve } from "node:path";

import { expect, test, type APIRequestContext } from "@playwright/test";

import { ejecutarPython } from "./helpers/python";
import { sesionApi } from "./helpers/sesion";

const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";
const KID_A = process.env.KONTROL_E2E_LICENSE_KID_A ?? "kontrol-lic-2026-01";
const KID_B = process.env.KONTROL_E2E_LICENSE_KID_B ?? "kontrol-lic-2027-01";
const BACKEND = resolve(process.cwd(), "..", "backend");
const QA = resolve(BACKEND, "..", "..", "qa");
const IMPORT = `${API}/license/import`;
const SENSIBLE = /BEGIN (PUBLIC|PRIVATE) KEY|signature_hex|KTL-|\/tmp|\/home|postgres|TRUST_KEYS/i;

interface Artefacto {
  payload: Record<string, unknown>;
  signature_hex: string;
}

interface Detalle {
  license_id: string;
  mode: string;
  period_start: string;
  period_end: string;
  kid: string | null;
}

function entornoDeQA(): NodeJS.ProcessEnv {
  const url = process.env.KONTROL_E2E_DB_URL;
  if (!url) {
    throw new Error("KONTROL_E2E_DB_URL es obligatoria: el ayudante lee la instalación de la base de la corrida");
  }
  return { ...process.env, KONTROL_DB_URL: url, PYTHONPATH: BACKEND };
}

function sintetica(...argumentos: string[]): Artefacto {
  const salida = ejecutarPython([resolve(QA, "licencia_firmada.py"), ...argumentos], { cwd: BACKEND, env: entornoDeQA(), encoding: "utf8", timeout: 60_000 });
  return JSON.parse(salida) as Artefacto;
}

async function token(baseUsuario: string): Promise<string> {
  return (await sesionApi(baseUsuario, { tenant: "DEMO" })).token;
}

async function detalle(request: APIRequestContext, bearer: string): Promise<Detalle> {
  const r = await request.get(`${API}/license/detail`, { headers: { Authorization: `Bearer ${bearer}` } });
  expect(r.status()).toBe(200);
  const c = (await r.json()) as Detalle;
  return { license_id: c.license_id, mode: c.mode, period_start: c.period_start, period_end: c.period_end, kid: c.kid ?? null };
}

function anioContractual(iso: string): number {
  const d = new Date(iso);
  return d.getUTCMonth() + 1 >= 4 ? d.getUTCFullYear() : d.getUTCFullYear() - 1;
}

async function rechazada(request: APIRequestContext, cabecera: Record<string, string>, artefacto: Artefacto, codigo: string): Promise<void> {
  const r = await request.post(IMPORT, { data: artefacto, headers: cabecera });
  expect(r.status(), await r.text()).toBe(423);
  expect((await r.json()).code).toBe(codigo);
  expect(await r.text()).not.toMatch(SENSIBLE);
}

test.describe("Licencia · rotación de la clave del propietario con solapamiento", () => {
  test("E2E-KEYROT-01..08 · A y B entran cada una por su kid; kid desconocido, ausente o cruzado se rechaza; el orden no cambia", async ({ request }) => {
    const admin = await token("admin");
    const cabecera = { Authorization: `Bearer ${admin}` };
    const antes = await detalle(request, admin);
    expect(antes.kid).toBe(KID_A); // lo vigente lo firmó la autoridad de la corrida (A)
    const anio = anioContractual(antes.period_start) + 2;

    // 1) kid desconocido, aunque la firma sea de A: rechazo antes de mirar el período; nada cambia.
    await rechazada(request, cabecera, sintetica("LIC-E2E-KID-X", "--anio", String(anio), "--kid", "kontrol-lic-2099-99"), "LICENSE_SIGNING_KID_UNKNOWN");
    // 2) sin kid: fuera de contrato.
    await rechazada(request, cabecera, sintetica("LIC-E2E-SIN-KID", "--anio", String(anio), "--sin-kid"), "LICENSE_SIGNING_KID_MISSING");
    // 3) kid A con firma de B: firma inválida, aunque B sea de confianza (nunca se prueban todas).
    await rechazada(request, cabecera, sintetica("LIC-E2E-CRUZADA", "--anio", String(anio), "--firmante-b", "--kid", KID_A), "LICENSE_SIGNATURE_INVALID");
    expect(await detalle(request, admin)).toEqual(antes);

    // 4) B con kid B, período posterior: entra; el detalle muestra el kid B.
    const conB = sintetica("LIC-E2E-B", "--anio", String(anio), "--firmante-b", "--kid", KID_B);
    const r = await request.post(IMPORT, { data: conB, headers: cabecera });
    expect(r.status(), await r.text()).toBe(200);
    const trasB = await detalle(request, admin);
    expect(trasB.kid).toBe(KID_B);
    expect(anioContractual(trasB.period_start)).toBe(anio);
    expect(trasB.mode).toBe("FULL_ACCESS");

    // 5) A sigue siendo de confianza (solapamiento): un período aún posterior firmado con A entra con kid A.
    const conA = sintetica("LIC-E2E-A", "--anio", String(anio + 1), "--kid", KID_A);
    expect((await request.post(IMPORT, { data: conA, headers: cabecera })).status()).toBe(200);
    expect((await detalle(request, admin)).kid).toBe(KID_A);

    // 6) El kid no ordena: volver al período de B con la «B más nueva» es un retroceso de período.
    await rechazada(request, cabecera, sintetica("LIC-E2E-B-VIEJA", "--anio", String(anio), "--firmante-b", "--kid", KID_B, "--revision", "9"), "LICENSE_PERIOD_DOWNGRADE");

    // 7) Auditoría con el motivo y sin material; estado público mínimo.
    const historial = (await (await request.get(`${API}/license/history`, { headers: cabecera })).json()) as Array<{ event_type: string; detail: Record<string, unknown> }>;
    const rechazos = historial.filter((e) => e.event_type === "LICENSE_SIGNING_KEY_REJECTED");
    expect(new Set(rechazos.map((e) => e.detail.reason))).toEqual(new Set(["unknown_kid", "kid_missing"]));
    expect(JSON.stringify(historial)).not.toMatch(/BEGIN (PUBLIC|PRIVATE) KEY|signature_hex/);
    const publico = await request.get(`${API}/license/status`);
    expect(Object.keys(await publico.json()).sort()).toEqual(["license_url", "mode"]);
    expect(await publico.text()).not.toMatch(/kid/i);
  });
});
