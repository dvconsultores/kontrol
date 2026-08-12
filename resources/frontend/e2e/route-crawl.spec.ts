/**
 * Crawler de rutas (T-11 de la auditoría 012) — Gate "no 404 en navegación".
 *
 * Inicia sesión con un usuario QA, recorre TODAS las rutas del menú lateral y
 * verifica que ninguna termine en "Página no encontrada", sin errores de
 * consola y con H1 presente.
 *
 * REQUIERE backend + frontend levantados (compose.dev) con licencia válida y
 * credenciales QA. Variables: KONTROL_E2E_TENANT / KONTROL_E2E_USERNAME /
 * KONTROL_E2E_PASSWORD (valores por defecto para dev).
 */
import { expect, test, type Page } from "@playwright/test";

const TENANT = process.env.KONTROL_E2E_TENANT ?? "DEMO";
const USER = process.env.KONTROL_E2E_USERNAME ?? "admin";
const PASS = process.env.KONTROL_E2E_PASSWORD ?? "Kontrol2026Segura!";

async function login(page: Page): Promise<void> {
  await page.goto("/login");
  await page.getByLabel(/Empresa \(código\)/).fill(TENANT);
  await page.getByLabel(/Usuario/).fill(USER);
  await page.getByLabel(/Contraseña/).fill(PASS);
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await expect(page).toHaveURL(/\/$/, { timeout: 15_000 });
}

test.describe("Crawler de rutas", () => {
  test("recorre el menú sin 404, sin errores de consola y con H1", async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    });
    page.on("pageerror", (err) => consoleErrors.push(String(err)));

    await login(page);

    // esperar el render del Sidebar antes de recolectar enlaces (evita el race
    // KAUD-010: el nav puede tardar tras el login)
    await expect(page.locator("nav a[href^='/']").first()).toBeVisible({ timeout: 15_000 });

    // extraer rutas del menú lateral (nav) — únicas, internas
    const links = await page.locator('nav a[href^="/"]').evaluateAll((els) =>
      [...new Set(
        els
          .map((e) => e.getAttribute("href") ?? "")
          .filter((h) => h.length > 1 && h !== "/login" && h !== "/setup"),
      )],
    );
    expect(links.length, "debería haber rutas de menú para recorrer").toBeGreaterThan(20);

    for (const href of links) {
      await page.goto(href);
      await page.waitForLoadState("networkidle").catch(() => undefined);
      const body = await page.locator("body").innerText();
      expect(body, `ruta ${href}: mostró 404 (página o menú sin implementar)`).not.toContain("Página no encontrada");
      expect(body, `ruta ${href}: error de carga de datos`).not.toContain("No fue posible cargar");
      await expect(page.locator("h1").first(), `ruta ${href}: sin H1`).toBeVisible();
    }

    expect(consoleErrors, "errores de consola durante el crawl").toEqual([]);
  });
});
