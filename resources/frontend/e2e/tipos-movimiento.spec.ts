import AxeBuilder from "@axe-core/playwright";
import { activarEmpresa } from "./helpers/empresa";
import { type Page } from "@playwright/test";
import { entrar, expect, sesionApi, test } from "./helpers/sesion";

const TENANT = process.env.KONTROL_E2E_TENANT ?? "DEMO";
const USER = process.env.KONTROL_E2E_USER;
const PASSWORD = process.env.KONTROL_E2E_PASSWORD;
const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";
const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

function usuario(): string {
  if (!USER || !PASSWORD) {
    throw new Error("KONTROL_E2E_USER y KONTROL_E2E_PASSWORD son obligatorias: las fija el lanzador qa/e2e-run.py");
  }
  return USER;
}

async function uiLogin(page: Page): Promise<void> {
  await entrar(page, usuario(), { tenant: TENANT });
  await page.locator('nav a[href="/organizacion/empresas"]').first().click();
  await page.waitForURL((u) => u.pathname === "/organizacion/empresas", { timeout: 15000 });
  await page.waitForLoadState("networkidle");
  await activarEmpresa(page);
}

test.describe("tipos de movimiento · alta sin alcance global", () => {
  test("E2E-TMOV-01: alta desde el menú sin selector global", async ({ page }) => {
    await uiLogin(page);

    await page.locator('nav a[href="/inventario/tipos-movimiento"]').first().click();
    await page.waitForURL((u) => u.pathname === "/inventario/tipos-movimiento", { timeout: 15000 });
    await page.waitForLoadState("networkidle");

    await expect(page.getByRole("heading", { name: "Tipos de movimiento" })).toBeVisible();
    await expect(page.getByLabel("Global (todas las empresas)")).toHaveCount(0);

    const formulario = page.locator("form, section").filter({ hasText: "Nuevo tipo" }).first();
    await expect(formulario.getByText("todas las empresas")).toHaveCount(0);

    const codigo = `TM_${Date.now().toString(36).toUpperCase()}`;
    const nombre = `Tipo ${codigo}`;

    await page.getByLabel("Código").fill(codigo);
    await page.getByLabel("Nombre").fill(nombre);
    await page.getByLabel("Dirección").selectOption("IN");

    const [respuesta] = await Promise.all([
      page.waitForResponse(
        (r) =>
          r.url().includes("/api/v1") &&
          r.url().endsWith("/inventory/movement-types") &&
          r.request().method() === "POST",
        { timeout: 15000 },
      ),
      page.getByRole("button", { name: "Crear" }).click(),
    ]);

    expect([200, 201]).toContain(respuesta.status());

    const cuerpoEnviado = respuesta.request().postDataJSON() as Record<string, unknown>;
    expect(cuerpoEnviado).not.toHaveProperty("global_scope");

    await expect(page.getByRole("cell", { name: codigo, exact: true })).toBeVisible();
  });

  test("E2E-TMOV-02: la API directa rechaza global_scope con 403", async ({ page, request }) => {
    await uiLogin(page);

    await page.locator('nav a[href="/inventario/tipos-movimiento"]').first().click();
    await page.waitForURL((u) => u.pathname === "/inventario/tipos-movimiento", { timeout: 15000 });
    await page.waitForLoadState("networkidle");

    const codigoUI = `TM_UI_${Date.now().toString(36).toUpperCase()}`;
    await page.getByLabel("Código").fill(codigoUI);
    await page.getByLabel("Nombre").fill(`Tipo ${codigoUI}`);
    await page.getByLabel("Dirección").selectOption("IN");

    const [respuestaUI] = await Promise.all([
      page.waitForResponse(
        (r) =>
          r.url().includes("/api/v1") &&
          r.url().endsWith("/inventory/movement-types") &&
          r.request().method() === "POST",
        { timeout: 15000 },
      ),
      page.getByRole("button", { name: "Crear" }).click(),
    ]);

    expect([200, 201]).toContain(respuestaUI.status());

    const cabecerasUI = respuestaUI.request().headers();
    const empresa = cabecerasUI["x-kontrol-company"] ?? cabecerasUI["X-Kontrol-Company"];
    expect(empresa).toBeTruthy();

    const { token } = await sesionApi(usuario(), { tenant: TENANT });

    const codigoProhibido = `TM_GLOBAL_${Date.now().toString(36).toUpperCase()}`;
    const respuestaDirecta = await request.post(`${API}/inventory/movement-types`, {
      data: {
        code: codigoProhibido,
        name: "Global prohibido",
        direction: "IN",
        global_scope: true,
      },
      headers: {
        Authorization: `Bearer ${token}`,
        "X-Kontrol-Company": empresa as string,
      },
    });

    expect(respuestaDirecta.status()).toBe(403);
    const cuerpo = (await respuestaDirecta.json()) as { code?: string };
    expect(cuerpo.code).toBe("GLOBAL_SCOPE_FORBIDDEN");

    const listado = await request.get(`${API}/inventory/movement-types`, {
      headers: {
        Authorization: `Bearer ${token}`,
        "X-Kontrol-Company": empresa as string,
      },
    });
    expect(listado.status()).toBe(200);
    const lista = (await listado.json()) as { items?: Array<{ code: string }> };
    const codigos = (lista.items ?? []).map((item) => item.code);
    expect(codigos).not.toContain(codigoProhibido);
  });

  test("E2E-TMOV-03: accesibilidad sin violaciones a 1280 px y 320 px", async ({ page }) => {
    await uiLogin(page);

    await page.locator('nav a[href="/inventario/tipos-movimiento"]').first().click();
    await page.waitForURL((u) => u.pathname === "/inventario/tipos-movimiento", { timeout: 15000 });
    await page.waitForLoadState("networkidle");

    await page.setViewportSize({ width: 1280, height: 800 });
    const resultados1280 = await new AxeBuilder({ page }).include("main").withTags(WCAG_TAGS).analyze();
    expect(resultados1280.violations).toEqual([]);

    await page.setViewportSize({ width: 320, height: 800 });
    const resultados320 = await new AxeBuilder({ page }).include("main").withTags(WCAG_TAGS).analyze();
    expect(resultados320.violations).toEqual([]);

    await expect(page.getByRole("button", { name: "Crear" })).toBeVisible();
  });
});
