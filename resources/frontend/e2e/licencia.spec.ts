/**
 * LIC · La licencia antes de la sesión y sin permiso (LICENCIA-STATUS-SIN-SESION,
 * LICENCIA-LECTURA-SIN-PERMISO, HEALTH-LIVE-VERSION; FR-010-102..121).
 *
 * `GET /license/status` sigue siendo público, pero mínimo: `mode` y `license_url`, nada de la
 * identidad ni de la licencia. El detalle (`GET /license/detail`) y toda lectura de
 * licenciamiento exigen sesión y `license:view` en el backend —que es la autoridad— y lo
 * respetan la pantalla «Mi licencia», su entrada de menú y el enlace del aviso. `/health/live`
 * ya no publica la versión. El usuario sin permiso lo fabrica `qa/rol_sin_permiso.py` en la
 * base de la corrida.
 */
import { resolve } from "node:path";

import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

import { ejecutarPython } from "./helpers/python";

const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";
const PASSWORD = process.env.KONTROL_E2E_PASSWORD ?? "";
const BACKEND = resolve(process.cwd(), "..", "backend");
const STATUS = `${API}/license/status`;
const DETAIL = `${API}/license/detail`;
const LECTURAS = [
  "/license/history",
  "/license/installation-request",
  "/licensing/central-config",
  "/licensing/entitlements",
  "/licensing/overview",
  "/licensing/renewal-requests",
];
//: Lo que nunca sale por el estado público ni por un rechazo.
const SENSIBLE = /installation_id|license_id|"kid"|period_|read_only_start|entitlements|minimum_version|KTL-|LIC-E2E|postgres|password|tenant_id|company_id/i;
const ETIQUETAS = ["Instalación", "Modo", "Período pagado", "Modo solo consulta desde"];

const marca = (): string => Date.now().toString(36) + Math.random().toString(36).slice(2, 6);

/** Un usuario de DEMO/D1 con todo el catálogo menos `license:view`, escrito en la base de la corrida. */
function usuarioSinPermiso(): string {
  const url = process.env.KONTROL_E2E_DB_URL;
  if (!url) {
    throw new Error("KONTROL_E2E_DB_URL es obligatoria: el usuario sin permiso se escribe en la base de la corrida");
  }
  const usuario = `sinlic${marca()}`;
  ejecutarPython(
    [resolve(BACKEND, "..", "..", "qa", "rol_sin_permiso.py"), "DEMO", usuario, "D1", "license:view"],
    { cwd: BACKEND, env: { ...process.env, KONTROL_DB_URL: url, PYTHONPATH: BACKEND }, encoding: "utf8", timeout: 60_000 },
  );
  return usuario;
}

async function token(request: APIRequestContext, usuario: string): Promise<string> {
  const r = await request.post(`${API}/auth/login`, { data: { tenant_code: "DEMO", username: usuario, password: PASSWORD } });
  expect(r.ok(), `login de ${usuario}: ${r.status()}`).toBeTruthy();
  return (await r.json()).access_token as string;
}

async function entrar(page: Page, usuario: string): Promise<void> {
  await page.goto("/login");
  await page.getByLabel(/Empresa \(código\)/).fill("DEMO");
  await page.getByLabel(/Usuario/).fill(usuario);
  await page.getByLabel(/Contraseña/).fill(PASSWORD);
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await expect(page).toHaveURL(/\/$/, { timeout: 20_000 });
  await expect(page.locator("nav a[href^='/']").first()).toBeVisible({ timeout: 15_000 });
}

/** Cuenta las peticiones al detalle de la licencia que hace el navegador desde ahora. */
function vigilarDetalle(page: Page): () => number {
  let pedidas = 0;
  page.on("request", (q) => {
    if (q.url().includes("/license/detail")) pedidas += 1;
  });
  return () => pedidas;
}

test.describe("Licencia · frontera de lectura", () => {
  test("E2E-LIC-01 · sin sesión, el estado público trae exactamente modo y enlace, y nada de la identidad", async ({ request }) => {
    const r = await request.get(STATUS);
    expect(r.status()).toBe(200);
    const cuerpo = await r.json();
    expect(Object.keys(cuerpo).sort()).toEqual(["license_url", "mode"]);
    expect(cuerpo.mode).toBe("FULL_ACCESS");
    expect(cuerpo.license_url).toBe("/mi-licencia");
    expect(await r.text()).not.toMatch(SENSIBLE);
  });

  test("E2E-LIC-02 · sin sesión o con token inventado, el detalle es 401 y sin fuga", async ({ request }) => {
    const anonimo = await request.get(DETAIL);
    expect(anonimo.status()).toBe(401);
    expect((await anonimo.json()).code).toBe("AUTH_REQUIRED");
    expect(await anonimo.text()).not.toMatch(SENSIBLE);
    const inventado = await request.get(DETAIL, { headers: { Authorization: "Bearer no.es.un.token" } });
    expect(inventado.status()).toBe(401);
    expect((await inventado.json()).code).toBe("AUTH_INVALID_TOKEN");
    for (const ruta of LECTURAS) expect((await request.get(`${API}${ruta}`)).status(), ruta).toBe(401);
  });

  test("E2E-LIC-03 · con sesión pero sin permiso, el detalle y toda lectura de licenciamiento son 403", async ({ request }) => {
    const cabecera = { Authorization: `Bearer ${await token(request, usuarioSinPermiso())}` };
    const detalle = await request.get(DETAIL, { headers: cabecera });
    expect(detalle.status()).toBe(403);
    expect((await detalle.json()).code).toBe("PERMISSION_DENIED");
    expect(await detalle.text()).not.toMatch(SENSIBLE);
    for (const ruta of LECTURAS) {
      const r = await request.get(`${API}${ruta}`, { headers: cabecera });
      expect(r.status(), ruta).toBe(403);
    }
    // El estado público no cambia con la sesión: un solo contrato.
    const publico = await request.get(STATUS, { headers: cabecera });
    expect(Object.keys(await publico.json()).sort()).toEqual(["license_url", "mode"]);
  });

  test("E2E-LIC-04 · sin permiso en el navegador: sin entrada de menú, acceso prohibido y ninguna petición al detalle", async ({ page }) => {
    const usuario = usuarioSinPermiso();
    await entrar(page, usuario);
    await expect(page.locator('nav a[href="/mi-licencia"]')).toHaveCount(0);
    await expect(page.locator('nav a[href="/"]')).toBeVisible();

    const pedidas = vigilarDetalle(page);
    await page.goto("/mi-licencia");
    await expect(page.getByRole("heading", { level: 1, name: "Acceso prohibido" })).toBeVisible({ timeout: 15_000 });
    expect(new URL(page.url()).pathname).toBe("/mi-licencia");
    await page.waitForLoadState("networkidle").catch(() => undefined);
    for (const etiqueta of ETIQUETAS) await expect(page.getByText(etiqueta, { exact: true })).toHaveCount(0);
    expect(pedidas()).toBe(0);
  });

  test("E2E-LIC-05 · el administrador ve la entrada y la pantalla con identificador, modo y período", async ({ page }) => {
    await entrar(page, "admin");
    const entrada = page.locator('nav a[href="/mi-licencia"]');
    await expect(entrada).toBeVisible();
    await entrada.click();
    await expect(page).toHaveURL(/\/mi-licencia$/);
    for (const etiqueta of ETIQUETAS) await expect(page.getByText(etiqueta, { exact: true })).toBeVisible({ timeout: 15_000 });
    const principal = await page.locator("main").innerText();
    expect(principal).toContain("FULL ACCESS");
    expect(principal).toMatch(/KTL-/);
    await expect(page.getByRole("heading", { level: 1, name: "Acceso prohibido" })).toHaveCount(0);
  });

  test("E2E-LIC-06 · recargar con permiso mantiene la ruta y el contenido", async ({ page }) => {
    await entrar(page, "admin");
    await page.goto("/mi-licencia");
    await expect(page.getByText("Instalación", { exact: true })).toBeVisible({ timeout: 15_000 });
    await page.reload();
    await expect(page).toHaveURL(/\/mi-licencia$/, { timeout: 15_000 });
    for (const etiqueta of ETIQUETAS) await expect(page.getByText(etiqueta, { exact: true })).toBeVisible({ timeout: 15_000 });
  });

  test("E2E-LIC-07 · el administrador lee el historial y el detalle por la API, con el mismo modo que el público", async ({ request }) => {
    const cabecera = { Authorization: `Bearer ${await token(request, "admin")}` };
    const detalle = await request.get(DETAIL, { headers: cabecera });
    expect(detalle.status()).toBe(200);
    const cuerpo = await detalle.json();
    expect(cuerpo.installation_id).toMatch(/^KTL-/);
    expect(cuerpo.license_id).toBe("LIC-E2E");
    expect(cuerpo.mode).toBe((await (await request.get(STATUS)).json()).mode);
    for (const ruta of LECTURAS) expect((await request.get(`${API}${ruta}`, { headers: cabecera })).status(), ruta).toBe(200);
  });

  test("E2E-LIC-08 · sin sesión, la URL directa de Mi licencia lleva al acceso y no pide el detalle", async ({ page }) => {
    const pedidas = vigilarDetalle(page);
    await page.goto("/mi-licencia");
    await expect(page).toHaveURL(/\/login$/, { timeout: 15_000 });
    await page.waitForLoadState("networkidle").catch(() => undefined);
    for (const etiqueta of ETIQUETAS) await expect(page.getByText(etiqueta, { exact: true })).toHaveCount(0);
    expect(pedidas()).toBe(0);
  });

  test("E2E-LIC-09 · los health siguen públicos: live sin versión, ready igual", async ({ request }) => {
    const live = await request.get(`${API}/health/live`);
    const ready = await request.get(`${API}/health/ready`);
    expect(live.status()).toBe(200);
    expect(await live.json()).toEqual({ status: "ok", service: "kontrol-backend" });
    expect(await live.text()).not.toMatch(/version/i);
    expect(await ready.json()).toEqual({ status: "ok", service: "kontrol-backend", database: "ok" });
  });

  test("E2E-LIC-10 · el aviso pre-sesión funciona: el navegador pide el estado público al arrancar y en FULL_ACCESS no hay aviso", async ({ page }) => {
    const pedidas: string[] = [];
    page.on("request", (q) => {
      if (q.url().includes("/license/")) pedidas.push(new URL(q.url()).pathname);
    });
    await page.goto("/login");
    await expect(page.getByRole("button", { name: "Iniciar sesión" })).toBeVisible({ timeout: 15_000 });
    await page.waitForLoadState("networkidle").catch(() => undefined);
    expect(pedidas.some((p) => p.endsWith("/license/status"))).toBeTruthy();
    expect(pedidas.some((p) => p.endsWith("/license/detail"))).toBeFalsy();
    await expect(page.getByRole("status")).toHaveCount(0);
  });
});
