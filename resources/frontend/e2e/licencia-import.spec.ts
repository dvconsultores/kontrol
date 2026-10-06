/**
 * LICIMP · Importar una licencia firmada exige autoridad (LICENCIA-IMPORT-SIN-SESION,
 * FR-010-125..146).
 *
 * `POST /license/activate` e `/import` respondían a cualquiera. Ahora el llamador necesita sesión
 * y `license:create` —la autoridad de activar que ya tenía `/licensing/sync`—, y la firma del
 * propietario sigue siendo la otra compuerta. El artefacto sintético lo firma
 * `qa/licencia_firmada.py` con la clave de la instalación de la corrida (el ancla de confianza
 * cuando no hay clave del propietario configurada, como en esta corrida); los usuarios sin
 * autoridad los fabrica `qa/rol_sin_permiso.py`. Primera activación y renovación en solo lectura
 * se prueban en backend sobre PostgreSQL (LICIMP-11/12): la siembra siempre activa y mover
 * fechas rompería a los demás trabajadores.
 */
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";

import { expect, test, type APIRequestContext } from "@playwright/test";

const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";
const PASSWORD = process.env.KONTROL_E2E_PASSWORD ?? "";
const BACKEND = resolve(process.cwd(), "..", "backend");
const QA = resolve(BACKEND, "..", "..", "qa");
const ACTIVATE = `${API}/license/activate`;
const IMPORT = `${API}/license/import`;
//: Lo que un rechazo de autorización nunca puede llevar.
const SENSIBLE = /installation_id|license_id|LIC-|KTL-|signature|firma|ed25519|public_key|private|\/tmp|\/home|postgres|tenant_id|company_id/i;

const marca = (): string => Date.now().toString(36) + Math.random().toString(36).slice(2, 6);

function entornoDeQA(): NodeJS.ProcessEnv {
  const url = process.env.KONTROL_E2E_DB_URL;
  if (!url) {
    throw new Error("KONTROL_E2E_DB_URL es obligatoria: los ayudantes escriben y leen la base de la corrida");
  }
  return { ...process.env, KONTROL_DB_URL: url, PYTHONPATH: BACKEND };
}

/** Un usuario de DEMO/D1 con todo el catálogo menos `sin`, escrito en la base de la corrida. */
function usuarioSin(...sin: string[]): string {
  const usuario = `sinimp${marca()}`;
  execFileSync(resolve(BACKEND, ".venv", "bin", "python"), [resolve(QA, "rol_sin_permiso.py"), "DEMO", usuario, "D1", ...sin], {
    cwd: BACKEND, env: entornoDeQA(), encoding: "utf8", timeout: 60_000,
  });
  return usuario;
}

interface Artefacto {
  payload: Record<string, unknown>;
  signature_hex: string;
}

/** Una licencia sintética firmada para la instalación de la corrida (o adulterada, según las opciones). */
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

/** Lo observable de la licencia vigente: identificador y modo. Las fechas las reescribe la
 * reimportación legítima de E2E-LICIMP-04, que corre en paralelo con el mismo identificador. */
async function detalle(request: APIRequestContext, bearer: string): Promise<{ license_id: string; mode: string }> {
  const r = await request.get(`${API}/license/detail`, { headers: { Authorization: `Bearer ${bearer}` } });
  expect(r.status()).toBe(200);
  const cuerpo = (await r.json()) as { license_id: string; mode: string };
  return { license_id: cuerpo.license_id, mode: cuerpo.mode };
}

test.describe("Licencia · importar exige autoridad", () => {
  test("E2E-LICIMP-01 · anónimo con un artefacto válido: 401, sin fuga, y la licencia sigue igual", async ({ request }) => {
    const admin = await token(request, "admin");
    const antes = await detalle(request, admin);
    const artefacto = licenciaFirmada("LIC-E2E-ANONIMA");
    for (const ruta of [ACTIVATE, IMPORT]) {
      const r = await request.post(ruta, { data: artefacto });
      expect(r.status(), ruta).toBe(401);
      expect((await r.json()).code).toBe("AUTH_REQUIRED");
      expect(await r.text()).not.toMatch(SENSIBLE);
      const inventado = await request.post(ruta, { data: artefacto, headers: { Authorization: "Bearer no.es.un.token" } });
      expect(inventado.status(), ruta).toBe(401);
    }
    expect(await detalle(request, admin)).toEqual(antes);
  });

  test("E2E-LICIMP-02 · un usuario sin permisos de licencia: 403 y nada cambia", async ({ request }) => {
    const admin = await token(request, "admin");
    const antes = await detalle(request, admin);
    const comun = await token(request, usuarioSin("license:view", "license:create", "license:edit", "license:approve"));
    const r = await request.post(ACTIVATE, { data: licenciaFirmada("LIC-E2E-COMUN"), headers: { Authorization: `Bearer ${comun}` } });
    expect(r.status()).toBe(403);
    expect((await r.json()).code).toBe("PERMISSION_DENIED");
    expect(await r.text()).not.toMatch(SENSIBLE);
    expect(await detalle(request, admin)).toEqual(antes);
  });

  test("E2E-LICIMP-03 · license:view sin license:create lee pero no importa: 403 y nada cambia", async ({ request }) => {
    const admin = await token(request, "admin");
    const antes = await detalle(request, admin);
    const lector = await token(request, usuarioSin("license:create"));
    expect(await detalle(request, lector)).toEqual(antes);
    const r = await request.post(IMPORT, { data: licenciaFirmada("LIC-E2E-LECTOR"), headers: { Authorization: `Bearer ${lector}` } });
    expect(r.status()).toBe(403);
    expect((await r.json()).code).toBe("PERMISSION_DENIED");
    expect(await detalle(request, admin)).toEqual(antes);
  });

  test("E2E-LICIMP-04 · el administrador importa un artefacto válido y el detalle lo refleja", async ({ request }) => {
    const admin = await token(request, "admin");
    // Mismo identificador y mismo contenido que la siembra: el estado observable no cambia para
    // los demás trabajadores de la corrida.
    const r = await request.post(ACTIVATE, { data: licenciaFirmada("LIC-E2E"), headers: { Authorization: `Bearer ${admin}` } });
    expect(r.status(), await r.text()).toBe(200);
    expect(await r.json()).toEqual({ ok: true, license_id: "LIC-E2E", mode: "FULL_ACCESS" });
    const despues = await detalle(request, admin);
    expect(despues.license_id).toBe("LIC-E2E");
    expect(despues.mode).toBe("FULL_ACCESS");
    const historial = await request.get(`${API}/license/history`, { headers: { Authorization: `Bearer ${admin}` } });
    const eventos = (await historial.json()) as Array<{ event_type: string }>;
    expect(eventos.some((e) => e.event_type === "LICENSE_IMPORTED")).toBeTruthy();
  });

  test("E2E-LICIMP-05 · el administrador con firma inválida: 423 y la licencia sigue igual", async ({ request }) => {
    const admin = await token(request, "admin");
    const antes = await detalle(request, admin);
    const r = await request.post(ACTIVATE, { data: licenciaFirmada("LIC-E2E-FALSA", "--firma-invalida"), headers: { Authorization: `Bearer ${admin}` } });
    expect(r.status()).toBe(423);
    expect((await r.json()).code).toBe("LICENSE_SIGNATURE_INVALID");
    expect(await detalle(request, admin)).toEqual(antes);
  });

  test("E2E-LICIMP-06 · el administrador con una licencia de otra instalación: 423 y la licencia sigue igual", async ({ request }) => {
    const admin = await token(request, "admin");
    const antes = await detalle(request, admin);
    const r = await request.post(IMPORT, { data: licenciaFirmada("LIC-E2E-AJENA", "--otra-instalacion"), headers: { Authorization: `Bearer ${admin}` } });
    expect(r.status()).toBe(423);
    expect((await r.json()).code).toBe("LICENSE_INSTALLATION_MISMATCH");
    expect(await detalle(request, admin)).toEqual(antes);
  });

  test("E2E-LICIMP-09 · el estado público sigue anónimo y mínimo", async ({ request }) => {
    const r = await request.get(`${API}/license/status`);
    expect(r.status()).toBe(200);
    expect(Object.keys(await r.json()).sort()).toEqual(["license_url", "mode"]);
    expect(await r.text()).not.toMatch(SENSIBLE);
  });

  test("E2E-LICIMP-10 · el diagnóstico sigue con sesión y license:view; los health, públicos y mínimos", async ({ request }) => {
    expect((await request.get(`${API}/system/diagnostics`)).status()).toBe(401);
    const lector = await token(request, usuarioSin("license:create"));
    expect((await request.get(`${API}/system/diagnostics`, { headers: { Authorization: `Bearer ${lector}` } })).status()).toBe(200);
    expect(await (await request.get(`${API}/health/live`)).json()).toEqual({ status: "ok", service: "kontrol-backend" });
    expect(await (await request.get(`${API}/health/ready`)).json()).toEqual({ status: "ok", service: "kontrol-backend", database: "ok" });
  });
});
