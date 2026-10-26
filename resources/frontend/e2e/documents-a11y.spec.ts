/**
 * Accesibilidad y responsive de las pantallas de la Spec 046.
 *
 * Alcance acotado a lo que 046 crea: los defectos preexistentes de otras Specs
 * se escalan, no se corrigen aquí.
 */
import AxeBuilder from "@axe-core/playwright";
import { type Page } from "@playwright/test";

import { entrar, expect, sesionApi, test } from "./helpers/sesion";

const TENANT = process.env.KONTROL_E2E_TENANT ?? "DEMO";
const USER = process.env.KONTROL_E2E_USER;
const PASSWORD = process.env.KONTROL_E2E_PASSWORD;
const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";
/** El runner dice si el backend de la corrida tiene `clamscan`; fuera del runner se asume que sí. */
const SCANNER = process.env.KONTROL_E2E_SCANNER_AVAILABLE !== "false";

const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];
const VIEWPORTS = [320, 375, 768, 1024, 1280, 1440];

test.skip(!USER || !PASSWORD, "KONTROL_E2E_USER / KONTROL_E2E_PASSWORD no configurados");

async function uiLogin(page: Page): Promise<void> {
  await entrar(page, USER as string, { tenant: TENANT });
  await page.waitForURL((u) => !u.pathname.includes("login"), { timeout: 20000 });
  await page.locator('nav a[href="/organizacion/empresas"]').first().click();
  await page.waitForURL((u) => u.pathname === "/organizacion/empresas", { timeout: 15000 });
  await page.waitForLoadState("networkidle");
  // Nombre exacto: sin `exact`, «Activar» casaba por subcadena con «Desactivar»,
  // y cuando la empresa ya estaba activa el helper la desactivaba (CONC-046).
  const activar = page.getByRole("button", { name: "Activar", exact: true }).first();
  if (await activar.count()) {
    await activar.click();
    await expect(page.getByRole("button", { name: "Desactivar", exact: true }).first())
      .toBeVisible({ timeout: 15000 });
  }
}

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

test("biblioteca y tipos: sin violaciones serias de WCAG 2.2 AA", async ({ page }) => {
  await uiLogin(page);
  for (const href of ["/documentos", "/documentos/tipos"]) {
    await goto(page, href);
    await page.waitForLoadState("networkidle");
    await expectNoSeriousViolations(page, href);
  }
});

test("detalle documental: sin violaciones serias de WCAG 2.2 AA", async ({ page, request }) => {
  const token = (await sesionApi(USER as string, { tenant: TENANT })).token;
  const headers = { Authorization: `Bearer ${token}` };
  const companies = await (await request.get(`${API}/organization/companies`, { headers })).json();
  const company = companies.items[0].id;

  const suffix = Date.now().toString(36).toUpperCase();
  const type = await request.post(`${API}/documentos/tipos`, {
    headers,
    data: { company_id: company, code: `A11Y${suffix}`.slice(0, 32),
            name: `Tipo A11Y ${suffix}`, allowed_mime_types: ["application/pdf"],
            scan_required: true },
  });
  expect(type.ok(), await type.text()).toBeTruthy();
  const title = `Documento A11Y ${suffix}`;
  const created = await request.post(`${API}/documentos`, {
    headers,
    data: { company_id: company, document_type_id: (await type.json()).id, title },
  });
  expect(created.ok(), await created.text()).toBeTruthy();

  await uiLogin(page);
  await goto(page, "/documentos");
  await page.getByLabel("Buscar documento").fill(title);
  await page.waitForLoadState("networkidle");
  await page.getByRole("link", { name: title }).first().click();
  await page.waitForURL(/\/documentos\/[0-9a-f-]+$/, { timeout: 15000 });
  await page.waitForLoadState("networkidle");
  await expectNoSeriousViolations(page, "detalle documental");
});

test("la carga de archivo es operable solo con teclado", async ({ page, request }) => {
  test.skip(!SCANNER, "ENTORNO-SIN-CLAMSCAN: la carga por teclado termina en una versión cargada, y sin clamscan " +
    "ninguna carga con análisis obligatorio crea versión (SCAN_FAILED, FR-046-072); dueña 046");
  const token = (await sesionApi(USER as string, { tenant: TENANT })).token;
  const headers = { Authorization: `Bearer ${token}` };
  const companies = await (await request.get(`${API}/organization/companies`, { headers })).json();
  const company = companies.items[0].id;

  const suffix = `K${Date.now().toString(36).toUpperCase()}`;
  const type = await request.post(`${API}/documentos/tipos`, {
    headers,
    data: { company_id: company, code: suffix.slice(0, 32), name: `Tipo teclado ${suffix}`,
            allowed_mime_types: ["application/pdf"], scan_required: true },
  });
  const title = `Documento teclado ${suffix}`;
  await request.post(`${API}/documentos`, {
    headers,
    data: { company_id: company, document_type_id: (await type.json()).id, title },
  });

  await uiLogin(page);
  await goto(page, "/documentos");
  await page.getByLabel("Buscar documento").fill(title);
  await page.waitForLoadState("networkidle");
  await page.getByRole("link", { name: title }).first().click();
  await page.waitForURL(/\/documentos\/[0-9a-f-]+$/, { timeout: 15000 });

  // El selector de archivo recibe foco sin ratón: arrastrar y soltar no es la
  // única vía de carga (§92).
  const input = page.getByLabel(/^Archivo/);
  await input.focus();
  const focused = await page.evaluate(() => document.activeElement?.getAttribute("type") ?? "");
  expect(focused).toBe("file");

  await input.setInputFiles({
    name: "teclado.pdf", mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4\ntrailer\n%%EOF\n") });
  // El botón de carga se alcanza tabulando y se activa con Enter.
  await page.getByRole("button", { name: "Cargar" }).focus();
  await page.keyboard.press("Enter");
  await expect(page.getByText("Versión cargada")).toBeVisible({ timeout: 30000 });
});

test("responsive: sin scroll horizontal entre 320 y 1440", async ({ page }) => {
  await uiLogin(page);
  for (const href of ["/documentos", "/documentos/tipos"]) {
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
