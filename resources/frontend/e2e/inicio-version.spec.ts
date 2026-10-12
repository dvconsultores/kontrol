/**
 * VER · Inicio muestra la versión del producto que publica el diagnóstico, solo a quien puede verla, y
 * la publicación de la versión no sale de ahí (PANEL-VERSION-VACIA; FR-001-084, FR-001-042). Antes la
 * tarjeta leía `/health/ready`, que nunca la trajo («—» siempre). Proyecto `chromium`, con la siembra de
 * la corrida; el usuario sin permiso lo fabrica `qa/rol_sin_permiso.py` en la base de la corrida.
 */
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";

import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";
const PASSWORD = process.env.KONTROL_E2E_PASSWORD ?? "";
const BACKEND = resolve(process.cwd(), "..", "backend");
const SEMVER = /^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$/;

const marca = (): string => Date.now().toString(36) + Math.random().toString(36).slice(2, 6);

/** Un usuario de DEMO/D1 con todo el catálogo menos `license:view`, escrito en la base de la corrida. */
function usuarioSinPermiso(): string {
  const url = process.env.KONTROL_E2E_DB_URL;
  if (!url) {
    throw new Error("KONTROL_E2E_DB_URL es obligatoria: el usuario sin permiso se escribe en la base de la corrida");
  }
  const usuario = `sinver${marca()}`;
  execFileSync(
    resolve(BACKEND, ".venv", "bin", "python"),
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
  await expect(page.getByRole("heading", { level: 1, name: "Inicio" })).toBeVisible({ timeout: 15_000 });
}

/** La tarjeta de Inicio cuya etiqueta es exactamente `etiqueta`, y su valor. */
function tarjeta(page: Page, etiqueta: string) {
  return page.locator("div", { has: page.getByText(etiqueta, { exact: true }) }).last();
}

test.describe("inicio · tarjeta «Versión»", () => {
  test("E2E-VER-01 · con permiso la tarjeta pinta la versión del diagnóstico, no un hueco", async ({ page, request }) => {
    const bearer = await token(request, "admin");
    const diagnostico = await request.get(`${API}/system/diagnostics`, { headers: { Authorization: `Bearer ${bearer}` } });
    expect(diagnostico.status()).toBe(200);
    const version = ((await diagnostico.json()) as { version: string }).version;
    expect(version).toMatch(SEMVER);

    await entrar(page, "admin");
    const laTarjeta = tarjeta(page, "Versión");
    await expect(laTarjeta.getByText(version, { exact: true })).toBeVisible({ timeout: 15_000 });
    await expect(laTarjeta.getByText("—", { exact: true })).toHaveCount(0);
  });

  test("E2E-VER-02 · sin `license:view` la tarjeta no existe y el navegador no pide el diagnóstico", async ({ page }) => {
    const usuario = usuarioSinPermiso();
    let pedidas = 0;
    page.on("request", (q) => {
      if (q.url().includes("/system/diagnostics")) pedidas += 1;
    });
    await entrar(page, usuario);
    await expect(page.getByText("Empresa activa", { exact: true })).toBeVisible();
    await expect(page.getByText("Versión", { exact: true })).toHaveCount(0);
    expect(pedidas).toBe(0);
  });

  test("E2E-VER-04 · health y raíz siguen mínimos y sin versión; el diagnóstico exige sesión", async ({ request }) => {
    const live = await request.get(`${API}/health/live`);
    expect(await live.json()).toEqual({ status: "ok", service: "kontrol-backend" });
    const ready = await request.get(`${API}/health/ready`);
    expect(Object.keys(await ready.json()).sort()).toEqual(["database", "service", "status"]);
    expect(await ready.text()).not.toContain("version");
    const raiz = await request.get(`${API.replace(/\/api\/v1$/, "")}/`);
    expect(Object.keys(await raiz.json()).sort()).toEqual(["service", "status"]);
    expect((await request.get(`${API}/system/diagnostics`)).status()).toBe(401);
  });
});
