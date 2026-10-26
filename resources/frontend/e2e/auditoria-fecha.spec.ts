/**
 * AUDITORIA-CREATED-AT · la columna «Fecha» de Auditoría, en un navegador real.
 *
 * El servidor publica `event_time`; la columna leía `created_at` y decía
 * «Invalid Date» en todas las filas. Aquí se genera un evento controlado —un
 * inicio de sesión por API, cuyo `X-Request-ID` devuelve el servidor— se lee
 * su `event_time` por API, y se comprueba que la fila lo muestra con la
 * convención del producto (`toLocaleString("es-VE")` en la zona del navegador),
 * y que ninguna fila de la primera página dice «Invalid Date».
 */
import { type APIRequestContext, type Page } from "@playwright/test";
import { entrar as entrarConSesion, expect, identidad, iniciarSesion, test } from "./helpers/sesion";

const API = process.env.KONTROL_E2E_API ?? "http://127.0.0.1:8000/api/v1";

interface Evento { request_id: string | null; event_time: string; action: string }

async function loginConRastro(_request: APIRequestContext, tenant: string, usuario: string) {
  const s = await iniciarSesion(identidad(usuario), { tenant });
  return { rastro: s.rastro, token: s.token };
}

async function eventoDelRastro(request: APIRequestContext, token: string, rastro: string): Promise<Evento> {
  const r = await request.get(`${API}/audit/events?page_size=100&action=LOGIN_SUCCESS`, { headers: { Authorization: `Bearer ${token}` } });
  expect(r.ok()).toBeTruthy();
  const { items } = (await r.json()) as { items: Evento[] };
  const evento = items.find((i) => i.request_id === rastro);
  expect(evento, "el login queda en la bitácora con su rastro").toBeTruthy();
  return evento!;
}

async function entrar(page: Page): Promise<void> {
  await entrarConSesion(page, "admin", { tenant: "DEMO" });
  await page.waitForLoadState("networkidle");
  const compuerta = page.getByTestId(/^elegir-empresa-/);
  if (await compuerta.count()) {
    await compuerta.first().click();
    await page.waitForLoadState("networkidle");
  }
  await page.locator('nav a[href="/auditoria"]').first().click();
  await page.waitForURL((u) => u.pathname === "/auditoria", { timeout: 15000 });
  await page.waitForLoadState("networkidle");
}

test.describe("AUDITORIA-CREATED-AT · la columna Fecha muestra event_time", () => {
  test("DATE-01/02/03 · la fila del evento controlado enseña su event_time con la convención del producto", async ({ page, request }) => {
    const { rastro, token } = await loginConRastro(request, "DEMO", "admin");
    const evento = await eventoDelRastro(request, token, rastro);
    expect(evento.event_time).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?[+-]\d{2}:\d{2}$/);

    let sobre: { items: Evento[] } | null = null;
    page.on("response", async (r) => { if (r.url().includes("/api/v1/audit/events")) sobre = await r.json(); });
    await entrar(page);
    await expect.poll(() => sobre !== null).toBeTruthy();

    // Cada fila de la primera página muestra el event_time de su item, formateado
    // como lo hace el propio navegador con la convención del producto.
    const filas = page.locator("table tbody tr");
    const primeros = sobre!.items.slice(0, 10);
    await expect(filas).toHaveCount(primeros.length);
    for (const [i, item] of primeros.entries()) {
      const esperado = await page.evaluate((iso) => new Date(iso).toLocaleString("es-VE"), item.event_time);
      const celda = (await filas.nth(i).innerText()).split("\t")[0];
      expect(celda, `fila ${i}`).not.toBe("Invalid Date");
      expect(celda, `fila ${i}`).toBe(esperado);
    }
    // Y la del evento controlado, si cayó en esta página, dice exactamente su instante.
    if (primeros.some((i) => i.request_id === rastro)) {
      const esperado = await page.evaluate((iso) => new Date(iso).toLocaleString("es-VE"), evento.event_time);
      await expect(
        page.getByRole("row", { name: new RegExp(rastro) }).filter({ hasText: "LOGIN_SUCCESS" }),
      ).toContainText(esperado);
    }
  });
});
