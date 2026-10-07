/**
 * REVISION · El cliente consume la `revision` firmada que emite la Autoridad Central y la aplica
 * dentro del mismo período, después del período (LICENCIA-REEMISION-INTRAPERIODO-SIN-ORDEN,
 * FR-010-322..366).
 *
 * Proyecto Playwright `licencia-revision`: corre después de `chromium`, porque el linaje cambia el
 * identificador vigente y deja el estado revisionado para siempre (nada retrocede). El emisor es el
 * real —`qa/autoridad_central.py` levanta `central_authority` sobre una base efímera de la corrida y
 * firma con la clave sintética cuya pública es el ancla del backend de esta corrida—; los artefactos
 * hostiles (otra legacy, `revision` repetida, manipulada o inválida) los firma `qa/licencia_firmada.py`
 * con la misma clave sintética. Un solo escenario ordenado: el estado es uno y solo avanza. Dirigida,
 * se corre SOLA (`qa/e2e-run.py -- e2e/licencia-revision.spec.ts --no-deps`): con `--no-deps` nada
 * impide que otra suite mueva el período a la vez.
 */
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";

import { expect, test, type APIRequestContext } from "@playwright/test";

const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";
const PASSWORD = process.env.KONTROL_E2E_PASSWORD ?? "";
const BACKEND = resolve(process.cwd(), "..", "backend");
const QA = resolve(BACKEND, "..", "..", "qa");
const PYTHON = resolve(BACKEND, ".venv", "bin", "python");
const IMPORT = `${API}/license/import`;
const SENSIBLE = /installation_id|KTL-|signature_hex|ed25519|public_key|private|\/tmp|\/home|postgres|sqlite|tenant_id|company_id/i;

interface Artefacto {
  payload: Record<string, unknown>;
  signature_hex: string;
}

interface Emision extends Artefacto {
  license_id: string;
  revision: number;
}

interface Detalle {
  license_id: string;
  mode: string;
  period_start: string;
  period_end: string;
  entitlements: Record<string, unknown>;
}

interface Evento {
  event_type: string;
  detail: Record<string, unknown>;
}

function entornoDeQA(): NodeJS.ProcessEnv {
  const url = process.env.KONTROL_E2E_DB_URL;
  if (!url) {
    throw new Error("KONTROL_E2E_DB_URL es obligatoria: los ayudantes leen la instalación de la base de la corrida");
  }
  return { ...process.env, KONTROL_DB_URL: url, PYTHONPATH: BACKEND };
}

function ayudante(guion: string, argumentos: string[]): string {
  return execFileSync(PYTHON, [resolve(QA, guion), ...argumentos], { cwd: BACKEND, env: entornoDeQA(), encoding: "utf8", timeout: 120_000 });
}

/** Una legacy sintética firmada por el firmante de la corrida; con `--revision`, una revisionada hostil. */
function sintetica(...argumentos: string[]): Artefacto {
  return JSON.parse(ayudante("licencia_firmada.py", argumentos)) as Artefacto;
}

/** Un usuario de la corrida sin los permisos dados (`qa/rol_sin_permiso.py`), como en `licencia-import.spec.ts`. */
function usuarioSin(...sin: string[]): string {
  const usuario = `sinrev${Date.now().toString(36)}${process.pid.toString(36)}`;
  ayudante("rol_sin_permiso.py", ["DEMO", usuario, "D1", ...sin]);
  return usuario;
}

/** La siguiente `revision` del período, emitida por la Autoridad Central real de la corrida. */
function emite(...argumentos: string[]): Emision {
  return JSON.parse(ayudante("autoridad_central.py", ["emitir", ...argumentos])) as Emision;
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

function anioContractual(iso: string): number {
  const d = new Date(iso);
  return d.getUTCMonth() + 1 >= 4 ? d.getUTCFullYear() : d.getUTCFullYear() - 1;
}

async function importa(request: APIRequestContext, cabecera: Record<string, string>, artefacto: Artefacto) {
  return request.post(IMPORT, { data: { payload: artefacto.payload, signature_hex: artefacto.signature_hex }, headers: cabecera });
}

async function aceptada(request: APIRequestContext, cabecera: Record<string, string>, artefacto: Artefacto): Promise<void> {
  const r = await importa(request, cabecera, artefacto);
  expect(r.status(), await r.text()).toBe(200);
}

async function rechazada(request: APIRequestContext, cabecera: Record<string, string>, artefacto: Artefacto, codigo: string): Promise<void> {
  const r = await importa(request, cabecera, artefacto);
  expect(r.status(), await r.text()).toBe(423);
  expect((await r.json()).code).toBe(codigo);
  expect(await r.text()).not.toMatch(SENSIBLE);
}

test.describe("Licencia · la revisión del emisor ordena dentro del período", () => {
  test("E2E-REV-01..14 · puente legacy, linaje r1→r2→r3 del emisor real, hostiles, otro período y compuertas", async ({ request }) => {
    const admin = await token(request, "admin");
    const cabecera = { Authorization: `Bearer ${admin}` };
    const antes = await detalle(request, admin);
    const periodo = ["--periodo", antes.period_start, antes.period_end];

    // 1) Legacy vigente: el artefacto exacto es idempotente; otra legacy del mismo período no entra.
    const legacyExacta = sintetica("--vigente");
    expect("revision" in legacyExacta.payload).toBeFalsy();
    await aceptada(request, cabecera, legacyExacta);
    expect(await detalle(request, admin)).toEqual(antes);
    await rechazada(request, cabecera, sintetica("LIC-E2E-OTRA-LEGACY", ...periodo), "LICENSE_LEGACY_REISSUE_REQUIRES_REVISION");
    expect(await detalle(request, admin)).toEqual(antes);

    // 2) El emisor real reemite el MISMO período con revision 1: entra y fija el linaje; la legacy ya no vuelve.
    const r1 = emite(...periodo);
    expect(r1.revision).toBe(1);
    await aceptada(request, cabecera, r1);
    const trasR1 = await detalle(request, admin);
    expect(trasR1.license_id).toBe(r1.license_id);
    expect([trasR1.period_start, trasR1.period_end]).toEqual([antes.period_start, antes.period_end]);
    await rechazada(request, cabecera, legacyExacta, "LICENSE_LEGACY_AFTER_REVISION");
    expect(await detalle(request, admin)).toEqual(trasR1);

    // 3) r2 (con menos derechos: los derechos no ordenan) entra; r1 ya es anterior; r3 entra; r2 ya no; r3 exacta, idempotente.
    const r2 = emite(...periodo, "--entitlements", '{"companies": 1}');
    expect(r2.revision).toBe(2);
    await aceptada(request, cabecera, r2);
    expect((await detalle(request, admin)).entitlements).toEqual({ companies: 1 });
    await rechazada(request, cabecera, r1, "LICENSE_REVISION_DOWNGRADE");
    const r3 = emite(...periodo, "--entitlements", '{"companies": 7}');
    expect(r3.revision).toBe(3);
    await aceptada(request, cabecera, r3);
    const trasR3 = await detalle(request, admin);
    expect(trasR3.license_id).toBe(r3.license_id);
    await rechazada(request, cabecera, r2, "LICENSE_REVISION_DOWNGRADE");
    await aceptada(request, cabecera, r3);
    expect(await detalle(request, admin)).toEqual(trasR3);

    // 4) Hostiles firmados con la clave del propietario: misma revisión con otra carga; manipulación; valores inválidos.
    await rechazada(request, cabecera, sintetica("LIC-E2E-CONFLICTO", ...periodo, "--revision", "3"), "LICENSE_REVISION_CONFLICT");
    const manipulada = { payload: { ...r3.payload, revision: 4 }, signature_hex: r3.signature_hex };
    await rechazada(request, cabecera, manipulada, "LICENSE_SIGNATURE_INVALID");
    for (const invalida of ["true", "0", "-1", '"4"', "null"]) {
      await rechazada(request, cabecera, sintetica("LIC-E2E-INVALIDA", ...periodo, "--revision", invalida), "LICENSE_INVALID_REVISION");
    }
    expect(await detalle(request, admin)).toEqual(trasR3);

    // 5) Otro período: su linaje empieza en 1 y entra aunque el vigente vaya por 3; volver al período anterior
    //    con una revisión altísima sigue siendo un retroceso de período.
    const anioSiguiente = anioContractual(antes.period_end) + 3;
    const siguienteR1 = emite("--anio", String(anioSiguiente));
    expect(siguienteR1.revision).toBe(1);
    await aceptada(request, cabecera, siguienteR1);
    const trasSiguiente = await detalle(request, admin);
    expect(anioContractual(trasSiguiente.period_start)).toBe(anioSiguiente);
    expect(trasSiguiente.mode).toBe("FULL_ACCESS");
    await rechazada(request, cabecera, sintetica("LIC-E2E-VIEJA-R999", ...periodo, "--revision", "999"), "LICENSE_PERIOD_DOWNGRADE");
    expect(await detalle(request, admin)).toEqual(trasSiguiente);

    // 6) Las compuertas anteriores siguen delante del orden: sesión y license:create.
    const siguienteR2 = emite("--anio", String(anioSiguiente));
    expect(siguienteR2.revision).toBe(2);
    expect((await request.post(IMPORT, { data: siguienteR2 })).status()).toBe(401);
    const lector = await token(request, usuarioSin("license:create"));
    expect((await importa(request, { Authorization: `Bearer ${lector}` }, siguienteR2)).status()).toBe(403);
    expect(await detalle(request, admin)).toEqual(trasSiguiente);
    await aceptada(request, cabecera, siguienteR2);
    expect((await detalle(request, admin)).license_id).toBe(siguienteR2.license_id);

    // 7) Auditoría con actor y sin material; estado público mínimo; health igual.
    const historial = (await (await request.get(`${API}/license/history`, { headers: cabecera })).json()) as Evento[];
    const rechazos = historial.filter((e) => e.event_type === "LICENSE_REISSUE_REJECTED");
    expect(rechazos.length).toBeGreaterThanOrEqual(5);
    expect(new Set(rechazos.map((e) => e.detail.outcome))).toEqual(
      new Set(["LEGACY_REISSUE_REQUIRES_REVISION", "LEGACY_AFTER_REVISION", "REVISION_DOWNGRADE", "REVISION_CONFLICT"]),
    );
    expect(JSON.stringify(rechazos)).not.toMatch(/signature|payload_hash|PRIVATE/);
    expect(historial.some((e) => e.event_type === "LICENSE_IMPORTED" && e.detail.revision === 3)).toBeTruthy();
    const publico = await request.get(`${API}/license/status`);
    expect(Object.keys(await publico.json()).sort()).toEqual(["license_url", "mode"]);
    expect(await publico.text()).not.toMatch(/revision|period/i);
    expect(await (await request.get(`${API}/health/live`)).json()).toEqual({ status: "ok", service: "kontrol-backend" });
  });
});
