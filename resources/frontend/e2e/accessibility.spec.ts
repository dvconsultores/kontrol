/**
 * T-12 · Accesibilidad (axe-core / WCAG 2.2 AA) — requiere stack levantado.
 *
 * - Página pública: login sin violaciones serias/críticas.
 * - Páginas autenticadas: requiere KONTROL_E2E_USER / KONTROL_E2E_PASSWORD
 *   (si no se configuran, los tests se omiten).
 * Uso: npm run test:e2e -- --project=chromium e2e/accessibility.spec.ts
 */
import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const USER = process.env.KONTROL_E2E_USER;
const PASSWORD = process.env.KONTROL_E2E_PASSWORD;
const TENANT = process.env.KONTROL_E2E_TENANT ?? "DEMO";

const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

async function expectNoSeriousViolations(page: import("@playwright/test").Page): Promise<void> {
  const results = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
  const serious = results.violations.filter((v) => v.impact === "critical" || v.impact === "serious");
  const summary = results.violations.map((v) => ({ id: v.id, impact: v.impact, nodes: v.nodes.length }));
  expect(serious, JSON.stringify(summary, null, 2)).toEqual([]);
}

test("login: sin violaciones serias de accesibilidad", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByRole("button", { name: "Iniciar sesión" })).toBeVisible();
  await expectNoSeriousViolations(page);
});

test.describe("páginas autenticadas (requiere credenciales E2E)", () => {
  test.skip(!USER || !PASSWORD, "KONTROL_E2E_USER / KONTROL_E2E_PASSWORD no configurados");

  const pages = [
    "/",
    "/organizacion/empresas",
    "/organizacion/sucursales",
    "/maestros/terceros",
    "/maestros/productos",
    "/maestros/atributos",
    "/ventas/facturas",
    "/ventas/ordenes",
    "/compras/facturas",
    "/compras/cotizaciones",
    "/inventario/existencias",
    "/inventario/movimientos",
    "/inventario/seriales",
    "/inventario/reservas",
    "/inventario/tipos-movimiento",
    "/fiscal/lotes-declaracion",
    "/seguridad/usuarios",
    "/regulatorio/aprobaciones",
    // Spec 045 — motor transversal de aprobaciones
    "/aprobaciones/bandeja",
    "/aprobaciones/politicas",
    "/aprobaciones/delegaciones",
  ];

  for (const path of pages) {
    test(`accesibilidad: ${path}`, async ({ page }) => {
      await page.goto("/login");
      await page.getByLabel(/Empresa \(código\)/).fill(TENANT);
      await page.getByLabel(/Usuario/).fill(USER!);
      await page.getByLabel(/Contraseña/).fill(PASSWORD!);
      await page.getByRole("button", { name: "Iniciar sesión" }).click();
      await page.goto(path);
      await page.waitForLoadState("networkidle");
      await expectNoSeriousViolations(page);
    });
  }
});
