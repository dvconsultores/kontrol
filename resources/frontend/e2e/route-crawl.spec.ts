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
    // 66 rutas × carga + networkidle supera el timeout por defecto (30s),
    // especialmente en Firefox/WebKit: timeout ampliado.
    test.setTimeout(240_000);

    // El arranque en frío de un visitante sin sesión pide una restauración que
    // el backend rechaza con 401 `AUTH_REQUIRED`, y hace bien: no hay cookie.
    // La aplicación lo trata correctamente —limpia el estado y muestra el
    // formulario—, pero el navegador lo registra igualmente como recurso
    // fallido. Ese ruido pertenece al login, no al recorrido, así que la
    // escucha empieza **después** de iniciar sesión: es lo que esta prueba dice
    // medir.
    await login(page);

    const consoleErrors: string[] = [];
    const authFailures: string[] = [];
    let currentRoute = "(inicio)";
    page.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(`${currentRoute}: ${msg.text()}`);
    });
    page.on("pageerror", (err) => consoleErrors.push(`${currentRoute}: ${String(err)}`));
    // Comprobación explícita, más estricta que leer la consola: ninguna
    // petición del recorrido puede quedarse sin autenticar ni sin permiso.
    page.on("response", (res) => {
      if (res.url().includes("/api/v1/") && (res.status() === 401 || res.status() === 403)) {
        authFailures.push(
          `${currentRoute}: ${res.status()} ${res.request().method()} ` +
          `${res.url().split("/api/v1")[1]}`);
      }
    });

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
      currentRoute = href;
      await page.goto(href);
      await page.waitForLoadState("networkidle").catch(() => undefined);
      // Abrir una ruta tiene que dejar en esa ruta. Sin esta comprobación, una pantalla
      // que caía al pintarse pasaba el recorrido cada vez que la aplicación acababa en
      // Inicio, que tiene su H1 y ningún error.
      expect(new URL(page.url()).pathname, `ruta ${href}: la aplicación acabó en otra ruta`).toBe(href);
      const body = await page.locator("body").innerText();
      expect(body, `ruta ${href}: mostró 404 (página o menú sin implementar)`).not.toContain("Página no encontrada");
      expect(body, `ruta ${href}: error de carga de datos`).not.toContain("No fue posible cargar");
      await expect(page.locator("h1").first(), `ruta ${href}: sin H1`).toBeVisible();
    }

    expect(authFailures, "peticiones sin autenticar o sin permiso durante el crawl")
      .toEqual([]);
    expect(consoleErrors, "errores de consola durante el crawl").toEqual([]);
  });
});
