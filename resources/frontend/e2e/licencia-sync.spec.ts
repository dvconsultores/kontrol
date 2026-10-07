/**
 * SYNC · El cliente sincroniza con la Autoridad Central REAL de la corrida autenticando a la
 * instalación (desafío-respuesta Ed25519; `CENTRAL-SYNC-AUTHORITY-UNDEFINED`, FR-010-400..415).
 *
 * Proyecto Playwright `licencia-sync`: corre tras `licencia-revision`, sobre el estado que deja. El
 * lanzador (`qa/e2e-run.py`) levanta `central_authority.main:app` en el puerto 8010 con su base SQLite
 * efímera y la clave sintética de la corrida como clave del propietario; `qa/autoridad_central.py` emite
 * sobre esa misma base. El cliente se configura contra `http://127.0.0.1:8010` (HTTP solo porque la
 * corrida es `local`; en `prod` se exige HTTPS) y `POST /licensing/sync` hace el protocolo completo: la
 * licencia que llega pasa por la importación con todas sus compuertas. Dirigida, se corre SOLA con
 * `--no-deps`.
 */
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";

import { expect, test, type APIRequestContext } from "@playwright/test";

const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";
const CENTRAL = process.env.KONTROL_E2E_CENTRAL_URL ?? "http://127.0.0.1:8010";
const PASSWORD = process.env.KONTROL_E2E_PASSWORD ?? "";
const BACKEND = resolve(process.cwd(), "..", "backend");
const QA = resolve(BACKEND, "..", "..", "qa");
const PYTHON = resolve(BACKEND, ".venv", "bin", "python");
const SENSIBLE = /BEGIN (PUBLIC|PRIVATE) KEY|signature_hex|nonce_sha256|sqlite|postgres|\/tmp|\/home|customer_id|contract_id/i;
/** La corrida guarda el cuerpo v1 (lleva la licencia vigente, legible para `license:view`); lo que nunca puede llevar es material. */
const MATERIAL = /BEGIN (PUBLIC|PRIVATE) KEY|X-Kontrol-Signature|signature_hex|nonce|sqlite|postgres|\/tmp|\/home/i;

interface Emision {
  license_id: string;
  revision: number;
}

interface Detalle {
  license_id: string;
  mode: string;
  period_start: string;
  period_end: string;
}

interface Evento {
  event_type: string;
  detail: Record<string, unknown>;
}

interface Corridas {
  items: Array<{ status: string; request: Record<string, unknown> }>;
  total: number;
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

function emite(...argumentos: string[]): Emision {
  return JSON.parse(ayudante("autoridad_central.py", ["emitir", ...argumentos])) as Emision;
}

function usuarioSin(...sin: string[]): string {
  const usuario = `sinsync${Date.now().toString(36)}${process.pid.toString(36)}`;
  ayudante("rol_sin_permiso.py", ["DEMO", usuario, "D1", ...sin]);
  return usuario;
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
  return { license_id: c.license_id, mode: c.mode, period_start: c.period_start, period_end: c.period_end };
}

function anioContractual(iso: string): number {
  const d = new Date(iso);
  return d.getUTCMonth() + 1 >= 4 ? d.getUTCFullYear() : d.getUTCFullYear() - 1;
}

test.describe("Licencia · sincronización autenticada con la Autoridad Central real", () => {
  test("E2E-SYNC-01..08 · configurar, sincronizar, importar, idempotencia, compuertas locales y la autoridad no habla sin prueba", async ({ request }) => {
    const admin = await token(request, "admin");
    const cabecera = { Authorization: `Bearer ${admin}` };
    const antes = await detalle(request, admin);

    // 1) La autoridad de la corrida está viva y su health no cuenta nada.
    const vivo = await request.get(`${CENTRAL}/health/live`);
    expect(await vivo.json()).toEqual({ status: "ok", service: "kontrol-central-authority" });
    expect((await request.get(`${CENTRAL}/docs`)).status()).toBe(404);

    // 2) El administrador configura la autoridad (HTTP local: la corrida es `local`, no `prod`).
    const configurada = await request.put(`${API}/licensing/central-config`, {
      data: { server_url: CENTRAL, public_key: null, sync_policy: { mode: "MANUAL" }, grace_days: 7, enabled: true },
      headers: cabecera,
    });
    expect(configurada.status(), await configurada.text()).toBe(200);

    // 3) El vendor emite en la autoridad un período posterior al vigente; el cliente sincroniza: desafío, firma, importación.
    const anio = anioContractual(antes.period_end) + 2;
    const emitida = emite("--anio", String(anio), "--entitlements", '{"companies": 4, "modules": {"ventas": true}}');
    expect(emitida.revision).toBe(1);
    const sync = await request.post(`${API}/licensing/sync`, { headers: cabecera });
    expect(sync.status(), await sync.text()).toBe(200);
    const resultado = await sync.json();
    expect(resultado.status).toBe("SUCCESS");
    expect(resultado.idempotent).toBe(false);
    expect(resultado.response.status).toBe("LICENSE");
    expect(resultado.response.license_id).toBe(emitida.license_id);
    const despues = await detalle(request, admin);
    expect(despues.license_id).toBe(emitida.license_id);
    expect(anioContractual(despues.period_start)).toBe(anio); // el fin (31 mar 23:59 Caracas) ya es abril en UTC
    expect(despues.mode).toBe("FULL_ACCESS");

    // 4) Historial: la licencia entró por la importación (con su revisión) y el sync quedó anotado.
    const historial = (await (await request.get(`${API}/license/history`, { headers: cabecera })).json()) as Evento[];
    expect(historial.some((e) => e.event_type === "LICENSE_IMPORTED" && e.detail.revision === 1 && e.detail.license_id === emitida.license_id)).toBeTruthy();
    expect(historial.some((e) => e.event_type === "LICENSE_SYNCED" && e.detail.license_id === emitida.license_id)).toBeTruthy();
    const corridas = (await (await request.get(`${API}/licensing/sync-runs`, { headers: cabecera })).json()) as Corridas;
    expect(corridas.items[0].status).toBe("SUCCESS");
    expect(JSON.stringify(corridas.items[0].request)).not.toMatch(MATERIAL);

    // 5) Un segundo sync tras cambiar la licencia vuelve a contactar (la clave de idempotencia lleva la licencia
    //    vigente) y recibe el mismo artefacto: idempotente en el estado. El tercero, ya idéntico, no contacta.
    const repetido = await request.post(`${API}/licensing/sync`, { headers: cabecera });
    expect(repetido.status(), await repetido.text()).toBe(200);
    expect((await repetido.json()).response.license_id).toBe(emitida.license_id);
    expect(await detalle(request, admin)).toEqual(despues);
    const tercero = await request.post(`${API}/licensing/sync`, { headers: cabecera });
    expect((await tercero.json()).idempotent).toBe(true);
    const total = ((await (await request.get(`${API}/licensing/sync-runs`, { headers: cabecera })).json()) as Corridas).total;
    expect(total).toBe(corridas.total + 1);

    // 6) Compuertas locales: sin sesión y sin `license:create`, no.
    expect((await request.post(`${API}/licensing/sync`)).status()).toBe(401);
    const lector = await token(request, usuarioSin("license:create"));
    expect((await request.post(`${API}/licensing/sync`, { headers: { Authorization: `Bearer ${lector}` } })).status()).toBe(403);

    // 7) La autoridad no habla sin prueba: el desafío solo da lo necesario, el sync sin credenciales es 401 y nada se filtra.
    const desafio = await request.post(`${CENTRAL}/v1/license/sync/challenge`, { data: { installation_id: "KTL-XX-NADIE" } });
    expect(desafio.status()).toBe(200);
    expect(Object.keys(await desafio.json()).sort()).toEqual(["challenge_id", "expires_at", "nonce", "protocol_version"]);
    expect(await desafio.text()).not.toMatch(SENSIBLE);
    const sinPrueba = await request.post(`${CENTRAL}/v1/license/sync`, { data: { installation_id: "KTL-XX-NADIE" } });
    expect(sinPrueba.status()).toBe(401);
    expect((await sinPrueba.json()).code).toBe("SYNC_AUTH_INVALID");
    expect(await sinPrueba.text()).not.toMatch(SENSIBLE);
    const versionRara = await request.post(`${CENTRAL}/v1/license/sync`, {
      data: { installation_id: "KTL-XX-NADIE" },
      headers: { "X-Kontrol-Sync-Protocol": "9", "X-Kontrol-Installation": "KTL-XX-NADIE", "X-Kontrol-Challenge": "x", "X-Kontrol-Nonce": "y", "X-Kontrol-Signature": "00" },
    });
    expect(versionRara.status()).toBe(400);
    expect((await versionRara.json()).code).toBe("SYNC_PROTOCOL_UNSUPPORTED");
    expect((await request.get(`${CENTRAL}/v1/license/sync`)).status()).toBe(405);

    // 8) El estado público del cliente sigue mínimo.
    const publico = await request.get(`${API}/license/status`);
    expect(Object.keys(await publico.json()).sort()).toEqual(["license_url", "mode"]);
  });
});
