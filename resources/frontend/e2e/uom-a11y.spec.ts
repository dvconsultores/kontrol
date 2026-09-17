/** Accesibilidad y responsive de las pantallas de la Spec 011.
 *
 * Alcance acotado a lo que 011 crea (§89, §90). Los defectos preexistentes de
 * otras Specs se escalan, no se corrigen aquí; pero ninguna pantalla nueva
 * puede introducirlos.
 */
import AxeBuilder from "@axe-core/playwright";
import { activarEmpresa } from "./helpers/empresa";
import { expect, test, type Page } from "@playwright/test";

const TENANT = process.env.KONTROL_E2E_TENANT ?? "DEMO";
const USER = process.env.KONTROL_E2E_USER;
const PASSWORD = process.env.KONTROL_E2E_PASSWORD;
const WCAG = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];
const VIEWPORTS = [320, 375, 768, 1024, 1280, 1440, 1920];

test.skip(!USER || !PASSWORD, "credenciales E2E no configuradas");

async function uiLogin(page: Page): Promise<void> {
  await page.goto("/login");
  await page.getByLabel(/Empresa \(código\)/).fill(TENANT);
  await page.getByLabel(/Usuario/).fill(USER as string);
  await page.getByLabel(/Contraseña/).fill(PASSWORD as string);
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await page.waitForURL((u) => !u.pathname.includes("login"), { timeout: 20000 });
  await page.locator('nav a[href="/organizacion/empresas"]').first().click();
  await page.waitForURL((u) => u.pathname === "/organizacion/empresas", { timeout: 15000 });
  await page.waitForLoadState("networkidle");
  await activarEmpresa(page);
}

async function goto(page: Page, href: string): Promise<void> {
  await page.locator(`nav a[href="${href}"]`).first().click();
  await page.waitForURL((u) => u.pathname === href, { timeout: 15000 });
}

test("unidades: sin violaciones serias de WCAG 2.2 AA", async ({ page }) => {
  await uiLogin(page);
  await goto(page, "/maestros/unidades");
  await page.waitForLoadState("networkidle");
  const results = await new AxeBuilder({ page }).withTags(WCAG).analyze();
  const serious = results.violations.filter(
    (v) => v.impact === "critical" || v.impact === "serious");
  expect(serious, JSON.stringify(
    serious.map((v) => ({ id: v.id, nodes: v.nodes.length })), null, 2)).toEqual([]);
});

test("unidades: operable con teclado", async ({ page }) => {
  await uiLogin(page);
  await goto(page, "/maestros/unidades");
  await page.keyboard.press("Tab");
  const focused = await page.evaluate(() => document.activeElement?.tagName ?? "");
  expect(["A", "BUTTON", "INPUT", "SELECT"]).toContain(focused);
});

test("unidades: sin scroll horizontal entre 320 y 1920", async ({ page }) => {
  await uiLogin(page);
  await goto(page, "/maestros/unidades");
  for (const width of VIEWPORTS) {
    await page.setViewportSize({ width, height: 900 });
    await page.waitForTimeout(150);
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow, `a ${width}px desborda ${overflow}px`).toBeLessThanOrEqual(1);
  }
});

test("unidades: legible con zoom al 150%", async ({ page }) => {
  await uiLogin(page);
  await goto(page, "/maestros/unidades");
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.evaluate(() => { document.documentElement.style.zoom = "150%"; });
  await page.waitForTimeout(200);
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(2);
});
