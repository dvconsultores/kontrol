/**
 * BUSINESS-DATE-E2E · la fecha de negocio y la presentación de instantes son las
 * de America/Caracas, cualquiera que sea la zona horaria del navegador.
 *
 * Verifica en navegador real, bajo tres zonas horarias distintas, que:
 * - la bitácora muestra los instantes en America/Caracas (no en la zona local);
 * - «Hasta» de una delegación vence al final del día D en Caracas;
 * - la vigencia de una tasa se envía como instante de Caracas convertido a UTC;
 * - el período del Centro exige AAAA-MM con mes 01–12 y aplica el período pedido;
 * - en 320 px el error del período sigue siendo visible y accesible.
 */
import AxeBuilder from "@axe-core/playwright";
import { type Page, type Route } from "@playwright/test";

import { ctx, marca, post } from "./helpers/ventas";
import { entrar, expect, test } from "./helpers/sesion";

const TENANT = "DEMO";

async function irA(page: Page, ruta: string): Promise<void> {
  await page.locator(`nav a[href="${ruta}"]`).first().click();
  await page.waitForURL((u) => u.pathname === ruta, { timeout: 20_000 });
}

async function entrarComoAdmin(page: Page): Promise<void> {
  await entrar(page, "admin", { tenant: TENANT });
  await expect(page).toHaveURL(/\/$/, { timeout: 20_000 });
  await page.waitForLoadState("networkidle");
  const compuerta = page.getByTestId(/^elegir-empresa-/);
  if (await compuerta.count()) {
    await compuerta.first().click();
    await page.waitForLoadState("networkidle");
  }
}

async function enCaracas(page: Page, iso: string): Promise<string> {
  return page.evaluate((valor) => new Date(valor).toLocaleString("es-VE", { timeZone: "America/Caracas" }), iso);
}

async function interceptar(page: Page, patron: string): Promise<() => unknown> {
  let capturado: unknown;
  await page.route(`**/api/v1${patron}`, (route: Route) => {
    if (route.request().method() === "POST") {
      capturado = route.request().postDataJSON();
      void route.fulfill({
        status: 422,
        contentType: "application/json",
        body: JSON.stringify({ code: "E2E_INTERCEPTADA", message: "Interceptada por la prueba" }),
      });
      return;
    }
    void route.continue();
  });
  return () => capturado;
}

for (const zona of ["UTC", "Asia/Tokyo", "America/Caracas"]) {
  test.describe(`fecha de negocio · navegador en ${zona}`, () => {
    test.use({ timezoneId: zona });

    test("BD-E2E-01 · la bitácora muestra la hora de Caracas", async ({ page }) => {
      let sobre: { items: Array<{ event_time: string }> } | null = null;
      page.on("response", async (r) => {
        if (r.url().includes("/api/v1/audit/events")) sobre = await r.json();
      });

      await entrar(page, "admintenant", { tenant: TENANT });
      await expect(page).toHaveURL(/\/$/, { timeout: 20_000 });
      await page.waitForLoadState("networkidle");
      const compuerta = page.getByTestId(/^elegir-empresa-/);
      if (await compuerta.count()) {
        await compuerta.first().click();
        await page.waitForLoadState("networkidle");
      }
      await irA(page, "/auditoria");
      await expect.poll(() => sobre !== null).toBeTruthy();

      const filas = page.locator("table tbody tr");
      const primeros = sobre!.items.slice(0, 10);
      expect(primeros.length, "la bitácora debe tener eventos que comparar").toBeGreaterThan(0);
      await expect(filas).toHaveCount(primeros.length);
      for (const [i, filaItem] of primeros.entries()) {
        const esperado = await enCaracas(page, filaItem.event_time);
        const celda = (await filas.nth(i).innerText()).split("\t")[0];
        expect(celda, `fila ${i}`).toBe(esperado);
        if (zona !== "America/Caracas" && i === 0) {
          const local = await page.evaluate((iso) => new Date(iso).toLocaleString("es-VE"), filaItem.event_time);
          if (local !== esperado) expect(celda, `fila ${i} local`).not.toBe(local);
        }
      }
    });

    test("BD-E2E-02 · «Hasta» D vence al final de D en Caracas", async ({ page }) => {
      const cuerpo = await interceptar(page, "/approvals/delegations");
      await entrarComoAdmin(page);
      await irA(page, "/aprobaciones/delegaciones");
      await page.getByLabel(/^Delega \(usuario\)/).fill("u-e2e-1");
      await page.getByLabel(/^En \(usuario\)/).fill("u-e2e-2");
      await page.getByLabel(/^Hasta/).fill("2026-10-27");
      await page.getByRole("button", { name: "Crear delegación" }).click();
      await expect.poll(() => (cuerpo() as { valid_to?: string } | undefined)?.valid_to).toBe("2026-10-28T03:59:59.999Z");
    });

    test("BD-E2E-03 · la vigencia de una tasa es hora de Caracas", async ({ page, request }) => {
      const cuerpo = await interceptar(page, "/treasury/exchange-rates/observations");

      const c = await ctx(request);
      const m1 = `X${marca().slice(-3)}`;
      const m2 = `Y${marca().slice(-3)}`;
      await post(request, c, "/treasury/currencies", { code: m1, name: m1 });
      await post(request, c, "/treasury/currencies", { code: m2, name: m2 });

      await entrarComoAdmin(page);
      await irA(page, "/tesoreria/tasas");
      await expect(page.getByRole("heading", { level: 1, name: "Tasas de cambio" })).toBeVisible();

      const fmt = new Intl.DateTimeFormat("en-CA", {
        timeZone: "America/Caracas",
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        hourCycle: "h23",
      });
      const antes = fmt.format(new Date()).replace(", ", "T");
      const vigente = await page.getByLabel(/^Vigente desde/).inputValue();
      const despues = fmt.format(new Date()).replace(", ", "T");
      expect([antes, despues]).toContain(vigente);

      await page.getByLabel(/^Vigente desde/).fill("2026-10-27T23:30");
      await page.getByLabel(/^Moneda base/).selectOption(m1);
      await page.getByLabel(/^Moneda cotizada/).selectOption(m2);
      await page.getByLabel(/^Tasa\s*\*/).fill("40.000000");
      await page.getByRole("button", { name: "Registrar" }).click();
      await expect.poll(() => (cuerpo() as { effective_at?: string } | undefined)?.effective_at).toBe("2026-10-28T03:30:00.000Z");
    });

    test("BD-E2E-04 · el período del Centro es AAAA-MM y se aplica", async ({ page }) => {
      const urls: string[] = [];
      await entrarComoAdmin(page);
      page.on("request", (x) => {
        if (x.url().includes("/api/v1/reporting/reports/")) urls.push(x.url());
      });
      await irA(page, "/reportes/centro");

      await page.getByPlaceholder("2026-01").fill("2026-13");
      await expect(page.getByText("Formato AAAA-MM, mes 01 a 12.")).toBeVisible();
      expect(urls.some((u) => u.includes("period=2026-13"))).toBe(false);

      await page.getByPlaceholder("2026-01").fill("2026-10");
      const r = await page.waitForResponse((x) => x.url().includes("/api/v1/reporting/reports/") && x.url().includes("period=2026-10"));
      expect(((await r.json()) as { period_applied: boolean }).period_applied).toBe(true);
    });

    if (zona === "America/Caracas") {
      test("BD-E2E-05 · 320 px: el período con error sigue siendo usable y accesible", async ({ page }) => {
        await page.setViewportSize({ width: 320, height: 800 });
        await entrarComoAdmin(page);
        await irA(page, "/reportes/centro");
        await page.getByPlaceholder("2026-01").fill("2026-13");
        await expect(page.getByText("Formato AAAA-MM, mes 01 a 12.")).toBeVisible();
        expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(321);
        const axe = await new AxeBuilder({ page }).include("main").analyze();
        expect(axe.violations.filter((v) => v.impact === "critical" || v.impact === "serious")).toEqual([]);
      });
    }
  });
}
