/**
 * Accesibilidad y responsive de las pantallas de la Spec 008.
 *
 * Alcance acotado a lo que 008 crea o modifica (§43 y §61 del encargo): los
 * defectos preexistentes de otras Specs se escalan, no se corrigen aquí.
 */
import AxeBuilder from "@axe-core/playwright";
import { activarEmpresa } from "./helpers/empresa";
import { expect, test, type Page } from "@playwright/test";

const TENANT = process.env.KONTROL_E2E_TENANT ?? "DEMO";
const USER = process.env.KONTROL_E2E_USER;
const PASSWORD = process.env.KONTROL_E2E_PASSWORD;
const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";

const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];
const VIEWPORTS = [320, 375, 768, 1024, 1280, 1440];

test.skip(!USER || !PASSWORD, "KONTROL_E2E_USER / KONTROL_E2E_PASSWORD no configurados");

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

/** Navegación por menú: un `goto` recargaría y perdería el token en memoria. */
async function goto(page: Page, href: string): Promise<void> {
  await page.locator(`nav a[href="${href}"]`).first().click();
  await page.waitForURL((u) => u.pathname === href, { timeout: 15000 });
}

async function expectNoSeriousViolations(page: Page, label: string): Promise<void> {
  const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
  const serious = results.violations.filter(
    (v) => v.impact === "critical" || v.impact === "serious");
  const summary = serious.map((v) => ({ id: v.id, impact: v.impact, nodes: v.nodes.length }));
  expect(serious, `${label}: ${JSON.stringify(summary, null, 2)}`).toEqual([]);
}

test("almacenes y ubicaciones: sin violaciones serias de WCAG 2.2 AA", async ({ page }) => {
  await uiLogin(page);
  for (const href of ["/organizacion/almacenes", "/organizacion/ubicaciones"]) {
    await goto(page, href);
    await page.waitForLoadState("networkidle");
    await expectNoSeriousViolations(page, href);
  }
});

test("detalle de almacén: sin violaciones serias de WCAG 2.2 AA", async ({ page, request }) => {
  const login = await request.post(`${API}/auth/login`, {
    data: { tenant_code: TENANT, username: USER, password: PASSWORD },
  });
  const token = (await login.json()).access_token as string;
  const headers = { Authorization: `Bearer ${token}` };
  const companies = await (await request.get(`${API}/organization/companies`, { headers })).json();
  const company = (Array.isArray(companies) ? companies : companies.items)[0].id;
  const code = `A11Y-${Date.now().toString(36).toUpperCase()}`;
  const created = await request.post(`${API}/organization/warehouses`, {
    headers,
    data: { company_id: company, code, name: `Almacén ${code}`,
            structure_levels: { zone: true, aisle: true } },
  });
  expect(created.ok()).toBeTruthy();

  await uiLogin(page);
  await goto(page, "/organizacion/almacenes");
  await page.getByLabel("Buscar almacén por código o nombre").fill(code);
  await page.getByRole("link", { name: `Ver el almacén ${code}` }).click();
  await page.waitForURL(/\/organizacion\/almacenes\/[0-9a-f-]+$/, { timeout: 15000 });
  await page.waitForLoadState("networkidle");
  await expectNoSeriousViolations(page, "detalle de almacén");

  // Operable solo con teclado: las pestañas de tramo se alcanzan tabulando.
  await page.keyboard.press("Tab");
  const focused = await page.evaluate(() => document.activeElement?.tagName ?? "");
  expect(["A", "BUTTON", "INPUT", "SELECT"]).toContain(focused);
});

test("responsive: sin scroll horizontal entre 320 y 1440", async ({ page }) => {
  await uiLogin(page);
  for (const href of ["/organizacion/almacenes", "/organizacion/ubicaciones"]) {
    await goto(page, href);
    for (const width of VIEWPORTS) {
      await page.setViewportSize({ width, height: 900 });
      await page.waitForTimeout(150);
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      expect(overflow, `${href} a ${width}px desborda ${overflow}px`).toBeLessThanOrEqual(1);
    }
  }
});
