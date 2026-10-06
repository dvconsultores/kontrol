/**
 * DIAG · El diagnóstico de la instalación exige sesión y permiso (DIAGNOSTICO-SIN-SESION,
 * FR-001-226..240).
 *
 * `GET /system/diagnostics` respondía a cualquiera; ahora lo gobierna `license:view`, en el
 * backend —que es la autoridad— y en la pantalla y el menú, que lo respetan. Los health checks
 * públicos siguen públicos y mínimos. El usuario sin permiso lo fabrica `qa/rol_sin_permiso.py`
 * en la base de la corrida: no hay API de alta de roles con permisos.
 */
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";

import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";
const PASSWORD = process.env.KONTROL_E2E_PASSWORD ?? "";
const BACKEND = resolve(process.cwd(), "..", "backend");
const DIAGNOSTICO = `${API}/system/diagnostics`;
const FILAS = ["Entorno", "Base de datos", "Instalación", "Identificador", "Licencia"];

const marca = (): string => Date.now().toString(36) + Math.random().toString(36).slice(2, 6);

/** Un usuario de DEMO/D1 con todo el catálogo menos `license:view`, escrito en la base de la corrida. */
function usuarioSinPermiso(): string {
  const url = process.env.KONTROL_E2E_DB_URL;
  if (!url) {
    throw new Error("KONTROL_E2E_DB_URL es obligatoria: el usuario sin permiso se escribe en la base de la corrida");
  }
  const usuario = `sindiag${marca()}`;
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
  await expect(page.locator("nav a[href^='/']").first()).toBeVisible({ timeout: 15_000 });
}

/** Cuenta las peticiones al diagnóstico que hace el navegador desde ahora. */
function vigilarDiagnostico(page: Page): () => number {
  let pedidas = 0;
  page.on("request", (q) => {
    if (q.url().includes("/system/diagnostics")) pedidas += 1;
  });
  return () => pedidas;
}

test.describe("Diagnóstico · acceso", () => {
  test("E2E-DIAG-01 · sin sesión, la URL directa lleva al acceso y no pinta nada del diagnóstico", async ({ page }) => {
    const pedidas = vigilarDiagnostico(page);
    await page.goto("/diagnostico");
    await expect(page).toHaveURL(/\/login$/, { timeout: 15_000 });
    await page.waitForLoadState("networkidle").catch(() => undefined);
    for (const fila of FILAS) await expect(page.getByText(fila, { exact: true })).toHaveCount(0);
    expect(pedidas()).toBe(0);
  });

  test("E2E-DIAG-06 · sin sesión, el backend responde 401 y nada del diagnóstico", async ({ request }) => {
    const r = await request.get(DIAGNOSTICO);
    expect(r.status()).toBe(401);
    const cuerpo = await r.json();
    expect(cuerpo.code).toBe("AUTH_REQUIRED");
    for (const clave of ["environment", "installation", "license", "storage"]) expect(cuerpo).not.toHaveProperty(clave);
    const invalido = await request.get(DIAGNOSTICO, { headers: { Authorization: "Bearer no.es.un.token" } });
    expect(invalido.status()).toBe(401);
    expect((await invalido.json()).code).toBe("AUTH_INVALID_TOKEN");
  });

  test("E2E-DIAG-02 · con sesión pero sin permiso: sin entrada de menú, acceso prohibido, sin petición y 403 en la API", async ({ page, request }) => {
    const usuario = usuarioSinPermiso();
    const directa = await request.get(DIAGNOSTICO, { headers: { Authorization: `Bearer ${await token(request, usuario)}` } });
    expect(directa.status()).toBe(403);
    expect((await directa.json()).code).toBe("PERMISSION_DENIED");
    expect(await directa.text()).not.toContain("installation");

    await entrar(page, usuario);
    await expect(page.locator('nav a[href="/diagnostico"]')).toHaveCount(0);
    await expect(page.locator('nav a[href="/auditoria"]')).toBeVisible();

    const pedidas = vigilarDiagnostico(page);
    await page.goto("/diagnostico");
    await expect(page.getByRole("heading", { level: 1, name: "Acceso prohibido" })).toBeVisible({ timeout: 15_000 });
    expect(new URL(page.url()).pathname).toBe("/diagnostico");
    await page.waitForLoadState("networkidle").catch(() => undefined);
    for (const fila of FILAS) await expect(page.getByText(fila, { exact: true })).toHaveCount(0);
    expect(pedidas()).toBe(0);
  });

  test("E2E-DIAG-03 y 05 · el administrador ve la entrada y la pantalla, sin rutas del servidor", async ({ page }) => {
    await entrar(page, "admin");
    const entrada = page.locator('nav a[href="/diagnostico"]');
    await expect(entrada).toBeVisible();
    await entrada.click();
    await expect(page).toHaveURL(/\/diagnostico$/);
    for (const fila of FILAS) await expect(page.getByText(fila, { exact: true })).toBeVisible({ timeout: 15_000 });
    const principal = await page.locator("main").innerText();
    expect(principal).toContain("FULL_ACCESS");
    expect(principal).not.toMatch(/\/tmp|\/data|\/home|storage/);
  });

  test("E2E-DIAG-04 · recargar con permiso mantiene la ruta y el contenido", async ({ page }) => {
    await entrar(page, "admin");
    await page.goto("/diagnostico");
    await expect(page.getByText("Identificador", { exact: true })).toBeVisible({ timeout: 15_000 });
    await page.reload();
    await expect(page).toHaveURL(/\/diagnostico$/, { timeout: 15_000 });
    for (const fila of FILAS) await expect(page.getByText(fila, { exact: true })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole("heading", { level: 1, name: "Acceso prohibido" })).toHaveCount(0);
  });

  test("E2E-DIAG-07 y 08 · los health siguen públicos, con su contrato mínimo y sin nada del diagnóstico", async ({ request }) => {
    const live = await request.get(`${API}/health/live`);
    const ready = await request.get(`${API}/health/ready`);
    expect(live.status()).toBe(200);
    expect(ready.status()).toBe(200);
    expect(Object.keys(await live.json()).sort()).toEqual(["service", "status"]); // sin versión (FR-010-116)
    expect(await ready.json()).toEqual({ status: "ok", service: "kontrol-backend", database: "ok" });
    for (const texto of [await live.text(), await ready.text()]) {
      expect(texto).not.toMatch(/installation|license|environment|storage|\/tmp|\/data|postgres|password|tenant_id|company_id/i);
    }
  });
});
